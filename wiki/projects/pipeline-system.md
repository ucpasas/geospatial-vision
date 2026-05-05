---
tags: [project, pdal, lidar, cog, copc, pipeline]
created: 2026-04-22
updated: 2026-05-05
status: active
type: project
related: [[pdal]], [[cog]], [[copc]], [[smrf]], [[conda-lidar-env]], [[python-install-rules]]
---

# Pipeline System

Multi-mode [[pdal]] pipeline producing COG DTM, [[copc]], and/or compressed LAZ from a single `.laz/.las` file or a directory of tiles. Runs in the `lidar` conda env — see [[conda-lidar-env]].

**Source:** `Geoprocessor/pipeline/`  
**Output dir:** `Geoprocessor/pipeline/output/` (binaries gitignored)  
**Env:** `conda activate lidar` (see [[conda-lidar-env]] for full activation sequence)

---

## Phase Status

| Phase | Status | Description |
|---|---|---|
| 1 | ✅ Done | pdal bindings POC — 18.99M points read in 3.32s |
| 2 | ✅ Done | Dual pipeline execution, SRS read at runtime, both outputs verified |
| 3 | ✅ Done | Validation: point count, density ≥ 4.0 ppsm, COPC VLR via readers.copc |
| 4 | ✅ Done | Template system (dict injection), stage whitelist + driver validation, CSV logger |
| 5 | ✅ Done | Multi-mode, directory input, tile processing, GDAL merge → COG |

---

## CLI

```bash
python run_pipeline.py <input> [--output-dir DIR] [--mode {dtm+copc,dtm+laz,copc,laz}] [--density-threshold PPSM]
```

`input` accepts a single file or a flat directory of uniform `.las`/`.laz` files.  
`--mode` defaults to `dtm+copc`.  
`--density-threshold` sets the minimum ground point density for DTM validation (default `4.0` ppsm). Use a lower value for urban datasets — Melbourne 2018 typically yields ~3 ppsm after SMRF.

---

## Behaviour Matrix

| Input | Mode | DTM | Secondary |
|---|---|---|---|
| File | `dtm+copc` | single DTM | single COPC |
| File | `dtm+laz` | single DTM | single LAZ |
| File | `copc` | — | single COPC |
| File | `laz` | — | single LAZ |
| Directory | `dtm+copc` | per-tile → merged COG | single merged COPC |
| Directory | `dtm+laz` | per-tile → merged COG | single merged LAZ |
| Directory | `copc` | — | single merged COPC |
| Directory | `laz` | — | single merged LAZ |

**Directory DTM note:** SMRF is not streaming — it loads all points in RAM per tile. Directory DTM runs one tile at a time (`run_dtm_tiles()`), then merges all GeoTIFFs into a single COG via `gdal.BuildVRT` + `gdal.Translate`. Tile files are deleted after a successful merge.

**Directory COPC/LAZ note:** `writers.las` accepts a glob pattern as input — PDAL merges all tiles in one streaming pipeline run. Memory-light, no SMRF involved.

**COPC directory merge caveat:** `writers.copc` is **not streamable** — it must hold the full octree in RAM to build the spatial index. For large datasets (Melbourne: ~300M points ≈ 20–30 GB), this causes OOM on WSL2. Use `--mode laz` or `--mode dtm+laz` for large directory inputs. See [[copc]] for the full trade-off analysis and the `untwine` alternative.

---

## Output Structure (directory + `dtm+copc`)

```
output/
├── CoM_Point_Cloud_2018_LAS_dtm.tif    ← merged COG DTM (DEFLATE, OVERVIEWS=AUTO)
├── CoM_Point_Cloud_2018_LAS.copc.laz   ← single merged COPC
└── logs/run_YYYYMMDD_HHMMSS.csv        ← one row per DTM tile + one row for COPC
```

Individual DTM tile files are written to `output/tiles/` during processing and deleted after a successful merge. If the merge fails, tiles are preserved and the path is reported.

---

## Confirmed Run Output

Single tile run against USGS Central Texas data (Phase 4):

```
filename,mode,input_points,output_points,density_ppsm,dtm_elapsed_s,secondary_elapsed_s,total_elapsed_s,output_valid,status
USGS_LPC_TX_Central_B1_2017_stratmap17_50cm_2996011a1_LAS_2019.laz,dtm+copc,18991582,14668865,5.4249,19.26,30.6,49.87,True,PASS
```

- Ground classification ratio: ~77% (low vegetation, flat terrain — as expected)
- Density: 5.42 ppsm (threshold: 4.0 ppsm) ✅

---

## Source Data

### USGS Central Texas (test tile)
- File: `USGS_LPC_TX_Central_B1_2017_stratmap17_50cm_2996011a1_LAS_2019.laz`
- Point count: ~19M per tile
- Ground ratio: ~77%, Density: 5.42 ppsm
- Classification: pre-classified (Classification 2 = ground)

### City of Melbourne 2018 (`CoM_Point_Cloud_2018_LAS/LAS/`)
- 215 tiles, 25–36 MB each, ~8.6 GB total uncompressed
- All points in Class 0 (unclassified) — SMRF required for ground extraction
- Ground ratio: ~53% after SMRF (urban scene), yielding ~3 ppsm — use `--density-threshold 2.5` or lower
- Processing constraint: SMRF cannot merge all tiles on 11 GB RAM — directory mode runs per-tile DTM, then merges with GDAL
- COPC constraint: ~300M total points × 36 bytes ≈ 20–30 GB RAM for octree construction — OOM on WSL2. Use `--mode dtm+laz` for this dataset. COPC conversion requires `untwine` or a machine with ≥32 GB RAM.

**Confirmed R2 outputs (Melbourne 2018):**
- COG DTM: `cog/Melbourne_2018_dtm_f32_v2.tif` — float32, v2 reprocessing, in use by all three viewers
- COPC: `copc/Melbourne_2018.laz.copc` — note `.laz.copc` extension (differs from pipeline output convention `{stem}.copc.laz` — renamed on upload)

---

## Module Responsibilities

### `run_pipeline.py` — Orchestration

Key functions:

| Function | Role |
|---|---|
| `resolve_input(raw)` | Returns `(glob_or_path, srs_file, stem, file_list)` — detects file vs directory, validates uniform extensions |
| `load_pipeline(template, vars)` | Dict-level variable injection + stage validation |
| `get_srs_from_file(path)` | Throwaway `readers.las` pipeline to extract WKT at runtime |
| `run_pipeline(label, json)` | Executes a PDAL pipeline, returns `(count, elapsed, metadata)` |
| `run_dtm_tiles(files, ...)` | Sequential per-tile DTM runs; logs each; returns successful DTM paths |
| `merge_dtm_to_cog(paths, out)` | `gdal.BuildVRT` → `gdal.Translate(format="COG")`; cleans up temp VRT |
| `cleanup_dtm_tiles(paths)` | Deletes tile files after successful merge; removes `tiles/` dir if empty |
| `validate_stages(json)` | Two-layer stage check: whitelist → `pdal.drivers()` fallback |

### `validate.py` — Validation

Returns `ValidationResult` dataclass. Checks vary by mode:

| Mode | Checks |
|---|---|
| `dtm+copc`, `dtm+laz`, `dtm` | point count, density ≥ threshold ppsm, output valid |
| `copc`, `laz` | point count, output valid (density = N/A — no SMRF) |

- `density_ppsm` and `density_valid` are `None` when mode has no DTM
- `ValidationResult.passed` ignores density when `None`
- `density_threshold` stored on `ValidationResult` and printed in `report()` — visible in output
- Default threshold: `4.0` ppsm; overridden by `--density-threshold` CLI arg
- COPC valid: `readers.copc` execute — fails hard on missing/malformed VLR
- LAZ valid: file exists + size > 0

### `logger.py` — CSV Logger

- `create_log_file(base_dir)` — creates `logs/` dir, writes CSV header, returns path
- `log_tile(...)` — appends one row after each tile (pass or fail)
- One new file per run (timestamped) — no append between runs
- Columns: `filename | mode | input_points | output_points | density_ppsm | dtm_elapsed_s | secondary_elapsed_s | total_elapsed_s | output_valid | status`

---

## Key Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| PDAL bindings install | conda-forge | apt unavailable on Noble, pip version mismatch |
| Pipeline execution | `pdal.Pipeline().execute()` | No subprocess anywhere |
| Driver validation | `pdal.drivers()` | No subprocess anywhere |
| Template injection | Dict-level after `json.load()` | Handles escaping automatically; string.Template fragile on JSON with WKT |
| Density calculation | DTM pipeline metadata bounds | Removes osgeo dependency from validate.py |
| Density threshold | CLI arg `--density-threshold` (default 4.0) | Urban datasets yield lower post-SMRF ratios — Melbourne ~3 ppsm vs Texas ~5.4 ppsm |
| CSV strategy | New file per run, timestamped | Append breaks on external edits or schema changes |
| Directory DTM | Per-tile sequential + GDAL merge | SMRF not streaming; 11 GB RAM can't hold 215 merged tiles |
| Directory LAZ | Single streaming PDAL run with glob input | writers.las streaming; memory-light, no SMRF |
| Directory COPC | OOM for large datasets; use `--mode laz` instead | writers.copc not streamable — octree requires full RAM load; see [[copc]] |
| DTM tile cleanup | Delete after successful merge | Tiles are intermediates; only the merged COG is the deliverable |
| COG merge | BuildVRT → Translate(format="COG") | VRT reads headers only (instant); COG driver streams tile-by-tile (bounded RAM) |

---

## Template System

Templates are valid JSON files with empty-string/default-value placeholders. Variables injected at dict level after `json.load()` — no string substitution, no escaping needed.

### `dtm_template.json`

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

### `copc_template.json`

```json
{
    "pipeline": [
        { "type": "readers.las", "filename": "" },
        { "type": "writers.copc", "filename": "" }
    ]
}
```

### `laz_template.json`

```json
{
    "pipeline": [
        { "type": "readers.las", "filename": "" },
        { "type": "writers.las", "filename": "", "compression": true }
    ]
}
```

All templates accept a glob pattern as `filename` for directory merge runs.

---

## Stage Validation (Two Layers)

```python
SUPPORTED_STAGES = {
    "readers.las", "readers.copc",
    "filters.smrf", "filters.range", "filters.outlier",
    "writers.gdal", "writers.copc", "writers.las",
}
```

- Layer 1 — whitelist: stage in `SUPPORTED_STAGES` → pass immediately
- Layer 2 — fallback: if not in whitelist, check `pdal.drivers()` (lazy fetch)
  - In drivers but not whitelist → `ValueError` (valid but unsupported)
  - In neither → `ValueError` (unknown stage)

---

## Output Naming

```
{stem}_dtm.tif               ← COG DTM (single file or merged)
{stem}.copc.laz              ← COPC (single file or merged)
{stem}.laz                   ← LAZ (single file or merged)
output/tiles/{tile}_dtm.tif  ← per-tile intermediates (deleted after successful merge)
output/logs/run_YYYYMMDD_HHMMSS.csv
```

For directory input, `stem` is derived from the directory name.

---

## Backlog

1. ~~**COG overviews**~~ — ✅ Done. `merge_dtm_to_cog()` uses `OVERVIEWS=AUTO` via GDAL COG driver.
2. ~~**Tile processing**~~ — ✅ Done. `run_dtm_tiles()` + GDAL merge.
3. **Large dataset COPC** — ✅ Solved with `untwine` v1.5.1 (`conda install -c conda-forge untwine`). Run outside the pipeline after `--mode laz` merge. Validated on Melbourne 2018 (353M points, full 4 GB source, no OOM). Separate from remote LAZ indexing below.
   **Remote LAZ indexing** *(still pending)* — Generate a COPC-compatible spatial index as a sidecar alongside unmodified LAZ on S3 for serving without full COPC rebuild.
4. **Dockerfile** — Determine apt vs conda for PDAL in container. Ubuntu 22.04 may have `python3-pdal` — check before defaulting to conda.
5. **Template injection scaling** — Current `load_pipeline()` uses prefix matching per stage. Fine for current templates; move to convention-based injection if templates grow beyond ~5.
6. **SMRF parameter exposure** — Expose `slope/window/threshold/scalar` as CLI args for terrain-specific tuning (urban vs forest vs flat).
7. ~~**Point cloud viewer**~~ — ✅ Done. [[giro3d-viewer]] built and live on GitHub Pages.
8. **`__init__.py`** — Not yet in repo. Required if running as `python -m pipeline.run_pipeline`.
9. **Environment activation wrapper** — Running requires a non-obvious 3-step sequence. Add `run.sh` at `Geoprocessor/pipeline/` so the user just runs `./run.sh <input> [--mode dtm+laz]`.
10. **Concurrent tile processing** — `run_dtm_tiles()` is sequential. `ProcessPoolExecutor` with a worker cap (3–4) would reduce ~35 min Melbourne batch to ~10 min without OOM risk.
