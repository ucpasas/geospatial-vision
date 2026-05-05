import argparse
import glob
import json
import os
import sys
import pdal
from osgeo import gdal
from pathlib import Path
from time import time
from validate import validate
from logger import create_log_file, log_tile

gdal.UseExceptions()

RESOLUTION = 0.5  # metres

SUPPORTED_STAGES = {
    "readers.las",
    "readers.copc",
    "filters.smrf",
    "filters.range",
    "filters.outlier",
    "writers.gdal",
    "writers.copc",
    "writers.las",
}

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


def get_pdal_drivers() -> set:
    return {d["name"] for d in pdal.drivers()}


def validate_stages(pipeline_json: str):
    """
    Two-layer stage validation:
      1. Whitelist check — stage must be in SUPPORTED_STAGES
      2. PDAL driver check — stage must exist in pdal --drivers output
    """
    pdal_drivers = None
    stages = json.loads(pipeline_json).get("pipeline", [])

    for stage in stages:
        stage_type = stage.get("type")
        if not stage_type:
            continue
        if stage_type in SUPPORTED_STAGES:
            continue
        if pdal_drivers is None:
            pdal_drivers = get_pdal_drivers()
        if stage_type not in pdal_drivers:
            raise ValueError(
                f"Unknown PDAL stage: '{stage_type}'. "
                f"Run 'pdal --drivers' to see all available stages."
            )
        else:
            raise ValueError(
                f"Stage '{stage_type}' is a valid PDAL driver but is not "
                f"in the supported stage list for this pipeline system. "
                f"Supported stages: {sorted(SUPPORTED_STAGES)}"
            )


def load_pipeline(template_path: str, variables: dict) -> str:
    """
    Load a pipeline template, inject variables at the dict level, validate stages.

    Raises:
        FileNotFoundError — template file not found
        KeyError          — a required variable is missing
        ValueError        — a stage is unsupported or unknown
    """
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Pipeline template not found: {template_path!r}")

    with open(template_path) as f:
        data = json.load(f)

    required = {"input_path", "output_path"}
    missing = required - variables.keys()
    if missing:
        raise KeyError(f"Missing required variables: {sorted(missing)}")

    for stage in data.get("pipeline", []):
        stage_type = stage.get("type", "")
        if stage_type.startswith("readers."):
            stage["filename"] = variables["input_path"]
            if "srs" in variables:
                stage["override_srs"] = variables["srs"]
        elif stage_type.startswith("writers."):
            stage["filename"] = variables["output_path"]
            if "resolution" in variables and "resolution" in stage:
                stage["resolution"] = variables["resolution"]

    result = json.dumps(data)
    validate_stages(result)
    return result


def resolve_input(raw_input: str) -> tuple[str, str, str, list[str]]:
    """
    Resolve a file path or directory to pipeline inputs.

    Returns:
        pipeline_input — single file path or glob string
        srs_file       — single file path for SRS reading
        stem           — output filename stem
        file_list      — individual files for DTM batch ([] for single file)

    Raises:
        FileNotFoundError — path does not exist
        ValueError        — directory has no .las/.laz files, or mixed extensions
    """
    path = os.path.abspath(raw_input)

    if os.path.isfile(path):
        return path, path, Path(path).stem, []

    if os.path.isdir(path):
        las_files = sorted(glob.glob(os.path.join(path, "*.las")))
        laz_files = sorted(glob.glob(os.path.join(path, "*.laz")))

        if las_files and laz_files:
            raise ValueError(
                f"Mixed .las and .laz files in {path!r}. "
                "Use a directory with uniform extensions."
            )
        if laz_files:
            ext, files, sample = "laz", laz_files, laz_files[0]
        elif las_files:
            ext, files, sample = "las", las_files, las_files[0]
        else:
            raise ValueError(f"No .las or .laz files found in {path!r}")

        return os.path.join(path, f"*.{ext}"), sample, Path(path).name, files

    raise FileNotFoundError(f"Input not found: {path!r}")


def get_srs_from_file(input_path: str) -> str:
    pipeline_json = json.dumps({
        "pipeline": [{"type": "readers.las", "filename": input_path}]
    })
    pipeline = pdal.Pipeline(pipeline_json)
    pipeline.execute()

    raw = pipeline.metadata
    meta = raw if isinstance(raw, dict) else json.loads(raw)

    for key, val in meta.get("metadata", {}).items():
        if "readers" not in key:
            continue
        entry = val if isinstance(val, dict) else (val[0] if val else None)
        if entry is None:
            continue
        wkt = entry.get("srs", {}).get("wkt", "")
        if wkt:
            return wkt

    raise RuntimeError("Could not read SRS from file.")


def run_pipeline(label: str, pipeline_json: str, streaming: bool = False) -> tuple[int, float, dict]:
    suffix = " (streaming)" if streaming else ""
    print(f"  [..] Running {label} pipeline{suffix} ...")
    t0 = time()
    try:
        pipeline = pdal.Pipeline(pipeline_json)
        count = pipeline.execute_streaming() if streaming else pipeline.execute()
    except Exception as e:
        raise RuntimeError(f"{label} pipeline failed: {e}") from e

    elapsed = time() - t0
    raw = pipeline.metadata
    meta = raw if isinstance(raw, dict) else json.loads(raw)
    count_str = f"{count:,}" if count > 0 else "N/A (streaming)"
    print(f"  [OK] {label} complete — {count_str} points in {elapsed:.1f}s")
    return count, elapsed, meta


def _extract_bounds(meta: dict) -> dict:
    for key, val in meta.get("metadata", {}).items():
        if "readers" not in key:
            continue
        entry = val if isinstance(val, dict) else (val[0] if val else None)
        if entry is None:
            continue
        if all(k in entry for k in ("minx", "maxx", "miny", "maxy")):
            return {k: entry[k] for k in ("minx", "maxx", "miny", "maxy")}
    raise RuntimeError("Could not extract bounds from pipeline metadata.")


def assert_output_exists(path: str, label: str):
    if not os.path.exists(path):
        raise RuntimeError(
            f"{label} output not found at {path!r}. "
            "Pipeline may have exited without writing."
        )
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"  [OK] {label} output exists: {path}  ({size_mb:.1f} MB)")


def run_dtm_tiles(
    files: list[str],
    dtm_template: str,
    tiles_dir: str,
    srs_wkt: str,
    log_path: str,
    mode: str,
    density_threshold: float = 4.0,
) -> list[str]:
    """
    Run DTM pipeline on each file individually.
    Logs one row per tile. Returns paths of successfully written DTM tiles.
    """
    os.makedirs(tiles_dir, exist_ok=True)
    successful = []

    for i, file_path in enumerate(files, 1):
        tile_stem = Path(file_path).stem
        tile_dtm_path = os.path.join(tiles_dir, f"{tile_stem}_dtm.tif")
        print(f"\n  [{i}/{len(files)}] {tile_stem}")

        variables = {
            "input_path":  file_path,
            "output_path": tile_dtm_path,
            "srs":         srs_wkt,
            "resolution":  RESOLUTION,
        }

        try:
            dtm_json = load_pipeline(dtm_template, variables)
            count, elapsed, meta = run_pipeline("DTM", dtm_json)
            assert_output_exists(tile_dtm_path, "DTM")
            bounds = _extract_bounds(meta)
            result = validate(count, bounds, tile_dtm_path, mode="dtm", density_threshold=density_threshold)
            result.report()

            log_tile(
                log_path            = log_path,
                filename            = os.path.basename(file_path),
                mode                = mode,
                input_points        = count,
                output_points       = count,
                density_ppsm        = result.density_ppsm,
                dtm_elapsed_s       = elapsed,
                secondary_elapsed_s = 0.0,
                output_valid        = result.output_valid,
                status              = "PASS" if result.passed else "FAIL",
            )

            if result.passed:
                successful.append(tile_dtm_path)

        except RuntimeError as e:
            print(f"  [FAIL] {e}")
            log_tile(
                log_path            = log_path,
                filename            = os.path.basename(file_path),
                mode                = mode,
                input_points        = 0,
                output_points       = 0,
                density_ppsm        = None,
                dtm_elapsed_s       = 0.0,
                secondary_elapsed_s = 0.0,
                output_valid        = False,
                status              = "FAIL",
            )

    return successful


def merge_dtm_to_cog(dtm_paths: list[str], output_path: str):
    """
    Merge individual DTM GeoTIFFs into a single COG via an in-memory VRT.
    Raises RuntimeError on failure.
    """
    vrt_path = output_path.replace(".tif", "_temp.vrt")
    try:
        vrt = gdal.BuildVRT(vrt_path, dtm_paths)
        if vrt is None:
            raise RuntimeError("gdal.BuildVRT returned None — check input paths")
        vrt.FlushCache()
        vrt = None

        ds = gdal.Translate(
            output_path,
            vrt_path,
            format="COG",
            creationOptions=["COMPRESS=DEFLATE", "BIGTIFF=IF_SAFER", "OVERVIEWS=AUTO"],
        )
        if ds is None:
            raise RuntimeError("gdal.Translate to COG failed")
        ds.FlushCache()
        ds = None
    finally:
        if os.path.exists(vrt_path):
            os.remove(vrt_path)


def cleanup_dtm_tiles(dtm_paths: list[str]):
    """
    Delete individual DTM tile files after a successful merge.
    Removes the tiles/ directory if it is empty afterward.
    """
    for path in dtm_paths:
        try:
            os.remove(path)
        except OSError as e:
            print(f"  [WARN] Could not delete {path}: {e}")

    if dtm_paths:
        tiles_dir = os.path.dirname(dtm_paths[0])
        try:
            os.rmdir(tiles_dir)
        except OSError:
            pass  # not empty — other files remain


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run DTM and COPC/LAZ pipelines against a .laz/.las file or directory."
    )
    parser.add_argument(
        "input",
        help="Path to input .laz/.las file, or a directory of uniform .laz/.las files"
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Output directory (default: pipeline/output/ next to this script)"
    )
    parser.add_argument(
        "--mode",
        choices=["dtm+copc", "dtm+laz", "copc", "laz"],
        default="dtm+copc",
        help="Output mode (default: dtm+copc)"
    )
    parser.add_argument(
        "--density-threshold", type=float, default=4.0, metavar="PPSM",
        help="Minimum ground point density in points/m² for DTM validation (default: 4.0)"
    )
    args = parser.parse_args()

    try:
        pipeline_input, srs_file, stem, file_list = resolve_input(args.input)
    except (FileNotFoundError, ValueError) as e:
        print(f"[FAIL] {e}")
        sys.exit(1)

    is_dir    = len(file_list) > 0
    has_dtm   = args.mode.startswith("dtm")
    mode      = args.mode

    if args.output_dir:
        output_dir = os.path.abspath(args.output_dir)
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    # Output paths
    dtm_path = os.path.join(output_dir, f"{stem}_dtm.tif")
    if mode in ("dtm+copc", "copc"):
        secondary_path     = os.path.join(output_dir, f"{stem}.copc.laz")
        secondary_label    = "COPC"
        secondary_template = os.path.join(TEMPLATES_DIR, "copc_template.json")
    else:
        secondary_path     = os.path.join(output_dir, f"{stem}.laz")
        secondary_label    = "LAZ"
        secondary_template = os.path.join(TEMPLATES_DIR, "laz_template.json")

    dtm_template = os.path.join(TEMPLATES_DIR, "dtm_template.json")
    log_path     = create_log_file(output_dir)

    total_steps = 5 if (is_dir and has_dtm) else 4 if has_dtm else 3
    step        = 0

    def next_step(label):
        global step
        step += 1
        print(f"\n[{step}/{total_steps}] {label}")

    print(f"\n{'='*60}")
    print(f"Input:      {pipeline_input}")
    print(f"Mode:       {mode}")
    if is_dir:
        print(f"Tiles:      {len(file_list)}")
    print(f"Output dir: {output_dir}")
    print(f"Log:        {log_path}")
    print(f"{'='*60}")

    # ── Step: Read SRS ────────────────────────────────────────────
    next_step("Reading SRS from file ...")
    try:
        srs_wkt = get_srs_from_file(srs_file)
        print(f"  [OK] SRS: {srs_wkt[:80]} ...")
    except RuntimeError as e:
        print(f"  [FAIL] {e}")
        sys.exit(1)

    # ── Step: Load templates ──────────────────────────────────────
    next_step("Loading and validating pipeline templates ...")
    try:
        if has_dtm:
            load_pipeline(dtm_template, {
                "input_path": srs_file, "output_path": "/dev/null",
                "srs": srs_wkt, "resolution": RESOLUTION,
            })
            print("  [OK] dtm_template.json")
        load_pipeline(secondary_template, {
            "input_path": srs_file, "output_path": "/dev/null", "srs": srs_wkt,
        })
        print(f"  [OK] {os.path.basename(secondary_template)}")
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as e:
        print(f"  [FAIL] {e}")
        sys.exit(1)

    # ══════════════════════════════════════════════════════════════
    # DIRECTORY INPUT
    # ══════════════════════════════════════════════════════════════
    if is_dir:

        # ── Step: Secondary merge (single PDAL run, glob input) ──
        next_step(f"Running {secondary_label} merge pipeline ...")
        secondary_json = load_pipeline(secondary_template, {
            "input_path":  pipeline_input,
            "output_path": secondary_path,
            "srs":         srs_wkt,
        })
        try:
            sec_count, sec_elapsed, _ = run_pipeline(secondary_label, secondary_json, streaming=True)
            assert_output_exists(secondary_path, secondary_label)
        except RuntimeError as e:
            print(f"  [FAIL] {e}")
            sys.exit(1)

        sec_result = validate(sec_count, None, secondary_path, mode=mode if not has_dtm else secondary_label.lower(), skip_point_count=True)
        sec_result.report()
        log_tile(
            log_path            = log_path,
            filename            = f"{stem}_merged",
            mode                = mode,
            input_points        = sec_count,
            output_points       = 0,
            density_ppsm        = None,
            dtm_elapsed_s       = 0.0,
            secondary_elapsed_s = sec_elapsed,
            output_valid        = sec_result.output_valid,
            status              = "PASS" if sec_result.passed else "FAIL",
        )

        if not has_dtm:
            print(f"\n{'='*60}")
            print(f"  Result: {'PASS' if sec_result.passed else 'FAIL'}  [{mode}]")
            print(f"  {secondary_label}: {sec_count:,} points  |  {sec_elapsed:.1f}s")
            print(f"  {sec_result.output_label}: {'valid' if sec_result.output_valid else 'INVALID'}")
            print(f"{'='*60}")
            sys.exit(0 if sec_result.passed else 1)

        # ── Step: DTM batch ───────────────────────────────────────
        next_step(f"Running DTM batch ({len(file_list)} tiles) ...")
        tiles_dir = os.path.join(output_dir, "tiles")
        successful_dtm_paths = run_dtm_tiles(
            files             = file_list,
            dtm_template      = dtm_template,
            tiles_dir         = tiles_dir,
            srs_wkt           = srs_wkt,
            log_path          = log_path,
            mode              = mode,
            density_threshold = args.density_threshold,
        )

        failed = len(file_list) - len(successful_dtm_paths)
        print(f"\n  [OK] Batch complete — {len(successful_dtm_paths)}/{len(file_list)} tiles passed")
        if failed:
            print(f"  [WARN] {failed} tile(s) failed — see log for details")

        if not successful_dtm_paths:
            print("  [FAIL] No DTM tiles to merge — aborting")
            sys.exit(1)

        # ── Step: GDAL merge → COG + cleanup ─────────────────────
        next_step(f"Merging {len(successful_dtm_paths)} DTM tiles → COG ...")
        try:
            t0 = time()
            merge_dtm_to_cog(successful_dtm_paths, dtm_path)
            merge_elapsed = time() - t0
            assert_output_exists(dtm_path, "Merged DTM COG")
        except RuntimeError as e:
            print(f"  [FAIL] {e}")
            print(f"  [INFO] DTM tiles preserved in {tiles_dir}")
            sys.exit(1)

        print(f"  [OK] Merge complete in {merge_elapsed:.1f}s")
        print(f"  [..] Cleaning up {len(successful_dtm_paths)} tile files ...")
        cleanup_dtm_tiles(successful_dtm_paths)
        print(f"  [OK] Tile files deleted")

        size_mb = os.path.getsize(dtm_path) / (1024 * 1024)
        print(f"\n{'='*60}")
        print(f"  Result: {'PASS' if sec_result.passed else 'WARN — secondary failed'}  [{mode}]")
        print(f"  DTM COG:      {dtm_path}  ({size_mb:.1f} MB)")
        print(f"  {secondary_label}:          {secondary_path}")
        print(f"  DTM tiles:    {len(successful_dtm_paths)}/{len(file_list)} passed  |  merged in {merge_elapsed:.1f}s")
        if failed:
            print(f"  Failed tiles: {failed} — check log")
        print(f"{'='*60}")

    # ══════════════════════════════════════════════════════════════
    # SINGLE FILE INPUT
    # ══════════════════════════════════════════════════════════════
    else:
        next_step("Running pipelines ...")

        variables_dtm = {
            "input_path":  pipeline_input,
            "output_path": dtm_path,
            "srs":         srs_wkt,
            "resolution":  RESOLUTION,
        }
        variables_secondary = {
            "input_path":  pipeline_input,
            "output_path": secondary_path,
            "srs":         srs_wkt,
        }

        try:
            if has_dtm:
                dtm_json = load_pipeline(dtm_template, variables_dtm)
                dtm_count, dtm_elapsed, dtm_meta = run_pipeline("DTM", dtm_json)
                assert_output_exists(dtm_path, "DTM")
            else:
                dtm_count, dtm_elapsed, dtm_meta = 0, 0.0, {}

            secondary_json = load_pipeline(secondary_template, variables_secondary)
            sec_count, sec_elapsed, _ = run_pipeline(secondary_label, secondary_json)
            assert_output_exists(secondary_path, secondary_label)
        except RuntimeError as e:
            print(f"  [FAIL] {e}")
            sys.exit(1)

        next_step("Validation ...")
        bounds = None
        if has_dtm:
            try:
                bounds = _extract_bounds(dtm_meta)
            except RuntimeError as e:
                print(f"  [FAIL] {e}")
                sys.exit(1)

        result = validate(
            point_count       = dtm_count if has_dtm else sec_count,
            bounds            = bounds,
            output_path       = secondary_path,
            mode              = mode,
            density_threshold = args.density_threshold,
        )
        result.report()

        log_tile(
            log_path            = log_path,
            filename            = os.path.basename(args.input),
            mode                = mode,
            input_points        = sec_count,
            output_points       = dtm_count,
            density_ppsm        = result.density_ppsm,
            dtm_elapsed_s       = dtm_elapsed,
            secondary_elapsed_s = sec_elapsed,
            output_valid        = result.output_valid,
            status              = "PASS" if result.passed else "FAIL",
        )
        print(f"  [OK] Logged → {log_path}")

        density_str = f"{result.density_ppsm:.2f} ppsm" if result.density_ppsm is not None else "N/A"
        print(f"\n{'='*60}")
        print(f"  Result:  {'PASS' if result.passed else 'FAIL'}  [{mode}]")
        if has_dtm:
            print(f"  DTM:     {dtm_count:,} ground points  |  {dtm_elapsed:.1f}s")
        print(f"  {secondary_label:<8} {sec_count:,} points  |  {sec_elapsed:.1f}s")
        print(f"  Density: {density_str}")
        print(f"  {result.output_label}: {'valid' if result.output_valid else 'INVALID'}")
        print(f"{'='*60}")
