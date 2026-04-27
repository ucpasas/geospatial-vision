import argparse
import json
import os
import sys
import pdal
from pathlib import Path
from time import time
from validate import validate
from logger import create_log_file, log_tile


RESOLUTION = 0.5  # metres

# Stages explicitly tested and supported in this pipeline system.
# Add new stages here only after testing — do not expand casually.
SUPPORTED_STAGES = {
    "readers.las",
    "readers.copc",
    "filters.smrf",
    "filters.range",
    "filters.outlier",
    "writers.gdal",
    "writers.copc",
}


def get_pdal_drivers() -> set:
    return {d["name"] for d in pdal.drivers()}


def validate_stages(pipeline_json: str):
    """
    Two-layer stage validation:
      1. Whitelist check — stage must be in SUPPORTED_STAGES
      2. PDAL driver check — stage must exist in pdal --drivers output

    Layer 1 runs first. If a stage passes the whitelist it is assumed
    valid and layer 2 is skipped for that stage. Layer 2 only runs for
    stages not in the whitelist, giving a clear error before PDAL does.
    """
    pdal_drivers = None  # lazy — only fetched if needed
    stages = json.loads(pipeline_json).get("pipeline", [])

    for stage in stages:
        stage_type = stage.get("type")
        if not stage_type:
            continue

        if stage_type in SUPPORTED_STAGES:
            continue  # whitelist pass — skip layer 2

        # Not in whitelist — fetch PDAL drivers once and check
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
    Load a pipeline template JSON file, inject variables at the dict level,
    validate stages, and return the completed JSON string.

    Templates are valid JSON files with empty-string or default-value
    placeholders. Variables are injected by walking pipeline stages —
    no string substitution, so WKT and paths never need escaping.

    Raises:
        FileNotFoundError — template file not found
        KeyError          — a required variable is missing from variables dict
        ValueError        — a stage is unsupported or unknown
    """
    if not os.path.exists(template_path):
        raise FileNotFoundError(
            f"Pipeline template not found: {template_path!r}"
        )

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

def get_srs_from_file(input_path: str) -> str:
    pipeline_json = json.dumps({
        "pipeline": [{"type": "readers.las", "filename": input_path}]
    })
    pipeline = pdal.Pipeline(pipeline_json)
    pipeline.execute()

    raw = pipeline.metadata
    meta = raw if isinstance(raw, dict) else json.loads(raw)
    stages = meta.get("metadata", {})

    for key, val in stages.items():
        if "readers" not in key:
            continue
        entry = val if isinstance(val, dict) else (val[0] if val else None)
        if entry is None:
            continue
        wkt = entry.get("srs", {}).get("wkt", "")
        if wkt:
            return wkt

    raise RuntimeError("Could not read SRS from file.")


def run_pipeline(label: str, pipeline_json: str) -> tuple[int, float, dict]:
    print(f"  [..] Running {label} pipeline ...")
    t0 = time()

    try:
        pipeline = pdal.Pipeline(pipeline_json)
        count = pipeline.execute()
    except Exception as e:
        raise RuntimeError(f"{label} pipeline failed: {e}") from e

    elapsed = time() - t0
    raw = pipeline.metadata
    meta = raw if isinstance(raw, dict) else json.loads(raw)
    print(f"  [OK] {label} complete — {count:,} points in {elapsed:.1f}s")
    return count, elapsed, meta


def _extract_bounds(meta: dict) -> dict:
    stages = meta.get("metadata", {})
    for key, val in stages.items():
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run DTM (COG) and COPC pipelines against a .laz tile."
    )
    parser.add_argument("input", help="Path to input .laz file")
    parser.add_argument(
        "--output-dir", default=None,
        help="Output directory (default: pipeline/output/ next to this script)"
    )
    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    if not os.path.exists(input_path):
        print(f"[FAIL] Input file not found: {input_path}")
        sys.exit(1)

    if args.output_dir:
        output_dir = os.path.abspath(args.output_dir)
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, "output")

    os.makedirs(output_dir, exist_ok=True)

    stem = Path(input_path).stem
    dtm_path = os.path.join(output_dir, f"{stem}_dtm.tif")
    copc_path = os.path.join(output_dir, f"{stem}.copc.laz")

    log_path = create_log_file(output_dir)

    print(f"\n{'='*60}")
    print(f"Input:      {input_path}")
    print(f"Output dir: {output_dir}")
    print(f"Log:        {log_path}")
    print(f"{'='*60}\n")

    # Step 1: Read SRS
    print("[1/4] Reading SRS from file ...")
    try:
        srs_wkt = get_srs_from_file(input_path)
        print(f"  [OK] SRS: {srs_wkt[:80]} ...")
    except RuntimeError as e:
        print(f"  [FAIL] {e}")
        sys.exit(1)

    # Paths to templates — relative to repo root
    dtm_template  = os.path.join(os.path.dirname(__file__), "templates", "dtm_template.json")
    copc_template = os.path.join(os.path.dirname(__file__), "templates", "copc_template.json")

    variables_dtm = {
        "input_path":  input_path,
        "output_path": dtm_path,
        "srs":         srs_wkt,
        "resolution":  RESOLUTION
    }

    variables_copc = {
        "input_path":  input_path,
        "output_path": copc_path,
        "srs":         srs_wkt,
    }

    print("\n[2/4] Loading and validating pipeline templates ...")
    try:
        dtm_json  = load_pipeline(dtm_template,  variables_dtm)
        copc_json = load_pipeline(copc_template, variables_copc)
        print("  [OK] dtm_template.json")
        print("  [OK] copc_template.json")
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as e:
        print(f"  [FAIL] {e}")
        sys.exit(1)

    # Step 3: Run pipelines
    print("\n[3/4] Running pipelines ...")
    try:
        dtm_count, dtm_elapsed, dtm_meta = run_pipeline("DTM", dtm_json)
        assert_output_exists(dtm_path, "DTM")
        copc_count, copc_elapsed, _ = run_pipeline("COPC", copc_json)
        assert_output_exists(copc_path, "COPC")
    except RuntimeError as e:
        print(f"  [FAIL] {e}")
        sys.exit(1)

    # Step 4: Validation
    print("\n[4/4] Validation ...")
    try:
        bounds = _extract_bounds(dtm_meta)
    except RuntimeError as e:
        print(f"  [FAIL] {e}")
        sys.exit(1)
    result = validate(dtm_count, bounds, copc_path)
    result.report()

    log_tile(
        log_path       = log_path,
        filename       = os.path.basename(input_path),
        input_points   = copc_count,
        output_points  = dtm_count,
        density_ppsm   = result.density_ppsm,
        dtm_elapsed_s  = dtm_elapsed,
        copc_elapsed_s = copc_elapsed,
        copc_valid     = result.copc_valid,
        status         = "PASS" if result.passed else "FAIL",
    )
    print(f"  [OK] Tile logged → {log_path}")


    print("=" * 60)
    print(f"  Phase 2+3 result: {'PASS' if result.passed else 'FAIL'}")
    print(f"  DTM:     {dtm_count:,} ground points  |  {dtm_elapsed:.1f}s")
    print(f"  COPC:    {copc_count:,} points         |  {copc_elapsed:.1f}s")
    print(f"  Density: {result.density_ppsm:.2f} ppsm")
    print(f"  COPC VLR: {'valid' if result.copc_valid else 'INVALID'}")
    print("=" * 60)
