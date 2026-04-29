---
tags: [project, pdal, lidar, cog, copc, pipeline]
created: 2026-04-22
updated: 2026-04-24
status: complete
type: project
related: [[pdal]], [[cog]], [[copc]], [[smrf]], [[conda-lidar-env]], [[python-install-rules]]
---

# Pipeline System

Dual [[pdal]] pipeline producing a COG DTM and [[copc]] from a `.laz` input tile. Runs in the `lidar` conda env — see [[conda-lidar-env]].

**Source:** `Geoprocessor/pipeline/`  
**Output dir:** `Geoprocessor/pipeline/output/` (binaries gitignored)  
**Env:** `conda activate lidar`

---

## Phase Status

| Phase | Status | Description |
|---|---|---|
| 1 | ✅ Done | pdal bindings POC — 18.99M points read in 3.32s |
| 2 | ✅ Done | Dual pipeline execution, SRS read at runtime, both outputs verified |
| 3 | ✅ Done | Validation: point count, density ≥ 4.0 ppsm, COPC VLR via readers.copc |
| 4 | ✅ Done | Template system (dict injection), stage whitelist + driver validation, CSV logger |

---

## Confirmed Run Output

Single tile run against USGS Central Texas data:

```
filename,input_points,output_points,density_ppsm,dtm_elapsed_s,copc_elapsed_s,total_elapsed_s,copc_valid,status
USGS_LPC_TX_Central_B1_2017_stratmap17_50cm_2996011a1_LAS_2019.laz,18991582,14668865,5.4249,19.26,30.6,49.87,True,PASS
```

- Ground classification ratio: ~77% (low vegetation, flat terrain — as expected)
- Density: 5.42 ppsm (threshold: 4.0 ppsm) ✅

---

## Module Responsibilities

### `run_pipeline.py` — Orchestration
1. Reads SRS from file via throwaway reader pipeline
2. Loads and validates both pipeline templates (`load_pipeline`)
3. Executes DTM pipeline → `(count, elapsed, metadata)`
4. Executes COPC pipeline → `(count, elapsed, metadata)`
5. Checks output files exist + size
6. Calls `validate()`
7. Calls `log_tile()`
8. Prints summary

### `validate.py` — Validation
Returns `ValidationResult` dataclass. Three checks:
- `check_point_count` — `point_count > 0`
- `check_density` — derives area from DTM pipeline metadata bounds (no osgeo dependency)
- `check_copc_vlr` — uses `readers.copc`, fails hard on invalid or missing VLR

### `logger.py` — CSV Logger
- `create_log_file(base_dir)` — creates `logs/` dir, writes CSV header, returns path
- `log_tile(...)` — appends one row after each tile (pass or fail)
- One new file per run (timestamped) — no append between runs
- Columns: `filename | input_points | output_points | density_ppsm | dtm_elapsed_s | copc_elapsed_s | total_elapsed_s | copc_valid | status`

---

## Key Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| PDAL bindings install | conda-forge | apt unavailable on Noble, pip version mismatch |
| Pipeline execution | `pdal.Pipeline().execute()` | No subprocess anywhere |
| Driver validation | `pdal.drivers()` | No subprocess anywhere |
| Template injection | Dict-level after `json.load()` | Handles escaping automatically; string.Template fragile on JSON with WKT |
| Template syntax | dict injection (not string.Template, not Jinja2) | string.Template broke on WKT quotes; Jinja2 overkill for 4 variables |
| Density calculation | DTM pipeline metadata bounds | Removes osgeo dependency from validate.py |
| CSV strategy | New file per run, timestamped | Append breaks on external edits or schema changes |

---

## Template System

Templates are valid JSON files with empty-string/default-value placeholders. Variables are injected at the dict level after `json.load()` — NOT string substitution. This means WKT strings, paths, and special characters never need escaping.

```python
def load_pipeline(template_path: str, variables: dict) -> str:
    with open(template_path) as f:
        data = json.load(f)
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
```

**Known limitation:** `load_pipeline()` has to know which fields to inject per stage prefix. Fine for two templates — add a convention-based approach if templates grow significantly (see Backlog #5).

---

## Stage Validation (Two Layers)

```python
SUPPORTED_STAGES = {
    "readers.las", "readers.copc",
    "filters.smrf", "filters.range", "filters.outlier",
    "writers.gdal", "writers.copc",
}
```

- Layer 1 — whitelist: stage in `SUPPORTED_STAGES` → pass immediately
- Layer 2 — fallback: if not in whitelist, check `pdal.drivers()` (lazy fetch)
  - In drivers but not whitelist → `ValueError` (valid but unsupported)
  - In neither → `ValueError` (unknown stage)

---

## DTM Pipeline (`templates/dtm_template.json`)

```json
{
    "pipeline": [
        { "type": "readers.las", "filename": "" },
        { "type": "filters.smrf", "slope": 0.15, "window": 18.0, "threshold": 0.5, "scalar": 1.25 },
        { "type": "filters.range", "limits": "Classification[2:2]" },
        { "type": "writers.gdal", "filename": "", "resolution": 0.5,
          "output_type": "idw", "gdaldriver": "GTiff", "gdalopts": "COMPRESS=DEFLATE,TILED=YES" }
    ]
}
```

- `readers.las` — all points; `override_srs` injected at runtime
- `filters.smrf` — stamps Classification 2 on ground points (see [[smrf]]); params tuned for Central Texas
- `filters.range` — keeps `Classification[2:2]` only; point count drops to ~20–30%
- `writers.gdal` — IDW interpolation, 0.5m, DEFLATE+TILED (COG-friendly; full overviews pending — see Backlog)

---

## COPC Pipeline (`templates/copc_template.json`)

```json
{
    "pipeline": [
        { "type": "readers.las", "filename": "" },
        { "type": "writers.copc", "filename": "" }
    ]
}
```

- All returns preserved; `override_srs` injected at runtime
- COPC VLR confirmed by `readers.copc` in validation stage

---

## Output Naming

```
{stem}_dtm.tif                  ← COG DTM (tiled + compressed; overviews pending)
{stem}.copc.laz                 ← COPC
output/logs/run_YYYYMMDD_HHMMSS.csv  ← per-run CSV log (gitignored)
```

---

## Source Data

- Source: USGS LiDAR, Central Texas
- File: `USGS_LPC_TX_Central_B1_2017_stratmap17_50cm_2996011a1_LAS_2019.laz` (repo root)
- Point count: ~19M per tile
- SRS: confirmed at runtime — not hardcoded
- DTM resolution: 0.5m (matches native capture resolution)
- Ground ratio: ~77% (low vegetation, flat terrain)
- Density: 5.42 ppsm observed (threshold 4.0 ppsm)

---

## Backlog

1. **COG overviews** — Add `BuildOverviews()` after `writers.gdal` for fully valid COG. Requires osgeo back in `run_pipeline.py` for this step only.
2. **Batch processing** — Loop over a tile directory; one CSV row per tile, all rows in one timestamped file per batch.
3. **Remote LAZ indexing** *(priority research)* — Generate a COPC-compatible spatial index as a sidecar file alongside unmodified LAZ on S3. No file modification. Serve via lightweight range-request proxy. Approach: extract octree index from `writers.copc`, serialise as external file.
4. **Dockerfile** — Determine apt vs conda for PDAL in container. Ubuntu 22.04 may have `python3-pdal` — check before defaulting to conda.
5. **Template injection scaling** — Current `load_pipeline()` uses prefix matching per stage. Fine for two templates; move to convention-based injection if templates grow beyond ~5.
6. **SMRF parameter exposure** — Expose `slope/window/threshold/scalar` as CLI args for terrain-specific tuning (urban vs forest vs flat).
7. ~~**Point cloud viewer**~~ — ✅ Done. [[giro3d-viewer]] built and live on GitHub Pages. COPC served directly from R2.
8. **`__init__.py`** — Not yet in repo. Required if running as `python -m pipeline.run_pipeline`. Currently run as direct script.
