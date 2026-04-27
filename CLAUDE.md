# CLAUDE.md — Project Context for Claude Code

> Consolidated reference for all active subprojects. Read this before touching any code.

---

## Projects at a Glance

| Project | Status | Primary Tech |
|---|---|---|
| **Geoprocessor** | Active — tests passing | Python, GDAL, pytest, Docker |
| **Pipeline System** | Phase 2 in progress | Python, PDAL, conda, COG/COPC |
| **FastAPI Spatial API** | Phase 4 complete, Phase 5 next | FastAPI, PostGIS, psycopg2 |
| **DTM → PostGIS** | Phase 3 in progress | raster2pgsql, PostGIS raster, ST_MapAlgebra |

---

## Environment — Critical Rules

### OS & Shell
- Dev: **WSL2 (Ubuntu 24.04)** on Windows, VS Code Remote WSL
- Production target: **Docker on Ubuntu 22.04**
- Windows-side tooling (QGIS/OSGeo4W, psql, PowerShell) is used for PostGIS/DB work only

### Python installs — DO NOT DEVIATE
```
NEVER pip install gdal
NEVER pip install numpy
```
Both must come from **apt** to stay ABI-matched to native GDAL libs.

| Package | Install method |
|---|---|
| GDAL 3.8.4 | `apt` (`python3-gdal`, `gdal-bin`, `libgdal-dev`) |
| numpy | `apt` (`python3-numpy`) |
| pytest, fastapi, uvicorn, etc. | `pip` inside venv |
| pdal / python-pdal | **conda-forge only** (see below) |

### Venv (Geoprocessor project)
```bash
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install pytest
```

### conda env — `lidar` (Pipeline project only)
```bash
conda activate lidar
# One-time setup:
# conda create -n lidar python=3.12 -y
# conda install -c conda-forge pdal python-pdal pytest -y
```
PDAL version in conda env: **3.5.3**. The lidar env and the Geoprocessor venv are **completely separate** — they do not interact.

---

## Project 1 — Geoprocessor

**File:** `Geoprocessor/geoprocessor.py`

### Design rules
1. `gdal.UseExceptions()` at **module level** — never inside a class or function
2. `_open()` is the **only** entry point for dataset access
3. All GDAL calls wrapped in `try/except` — re-raise as `RuntimeError` with a consistent message
4. Datasets never stored on `self` — open per-method, use, release
5. Explicit `None` check after every GDAL call (some drivers fail silently despite `UseExceptions()`)

### Methods
| Method | Signature | Notes |
|---|---|---|
| `reproject` | `(output_path, epsg)` | Uses `CoordinateTransformation` to convert resolution units before `gdal.Warp` |
| `clip_to_bbox` | `(output_path, bbox)` | bbox = `(min_x, min_y, max_x, max_y)` |
| `convert_to_cog` | `(output_path)` | Two-step: intermediate TIF → overviews → COG Translate |
| `get_stats` | `(band=1)` | Returns `{min, max, mean, stddev}` |

### Known pitfalls
- `targetAlignedPixels=True` requires explicit `xRes`/`yRes` — always pass both
- Passing source resolution in metres to a geographic CRS (degrees) causes `Warp` to hang — convert units first via `CoordinateTransformation`
- `srs.AutoIdentifyEPSG()` hangs on some GDAL/PROJ versions — use `IsSame()` for CRS comparison in tests

### Test fixture
- 10×10 single-band GeoTIFF, EPSG:32755, 10m/pixel, nodata=-9999
- Pixel values 0–99 row-major → min=0.0, max=99.0, mean=49.5 (exact)
- `scope="session"` — created once per run

### Open TODOs
- `_estimate_output_resolution()` — upgrade from single centre-point to 5×5 grid sampling
- `convert_to_cog()` — migrate to `format="COG"` driver (GDAL 3.1+)
- `convert_to_cog()` — add `validate_cog()` helper
- Next method: `clip_and_reproject()` (clip before warp for efficiency)
- Wrap in FastAPI: `/reproject`, `/stats`, `/clip`, `/cog`

---

## Project 2 — Pipeline System

**File:** `Geoprocessor/pipeline/run_pipeline.py`

### Current phase: Phase 2 — Dual pipeline execution
Hardcoded JSON pipelines, no templates yet. Two pipelines run in sequence against the same `.laz` input.

### Key design decisions
- Use `pdal.Pipeline(json_string).execute()` — **NOT subprocess**
- SRS always read from file at runtime via throwaway reader pipeline (never hardcoded)
- `override_srs` passed explicitly to both pipelines to prevent silent CRS failures
- DTM uses ground-only points (Classification 2) via `filters.smrf` → `filters.range`
- COPC preserves all returns — no filtering

### DTM pipeline stages
1. `readers.las` — reads .laz, all points downstream
2. `filters.smrf` — stamps Classification 2 on ground points (does not remove). Params: `slope=0.15, window=18.0, threshold=0.5, scalar=1.25`
3. `filters.range` — drops all non-ground (keeps `Classification[2:2]`). Point count drops to ~20–30%
4. `writers.gdal` — IDW interpolation to 0.5m GeoTIFF with `COMPRESS=DEFLATE,TILED=YES`

### COPC pipeline stages
1. `readers.las` — all returns, no filtering
2. `writers.copc` — reindexes with spatial index VLR, all returns preserved

### Output naming
```
{stem}_dtm.tif       # COG DTM
{stem}.copc.laz      # COPC
```

### Source data
- USGS lidar, Central Texas, ~19M points/tile
- Expected SRS: EPSG:6343 or EPSG:26914 — **confirm at runtime**

### Phases roadmap
| Phase | Status | Description |
|---|---|---|
| 1 | ✅ Done | pdal bindings POC — 18.99M points in 3.32s |
| 2 | ⬅ In progress | Dual pipeline execution, hardcoded JSON |
| 3 | Pending | Validation: file exists, point count > 0, density > threshold, COPC VLR present |
| 4 | Pending | Template system (`string.Template`), CSV logging per tile |

### Open TODOs
- Complete Phase 2 — run against real tile, confirm both outputs
- Phase 3 validation stage
- Phase 4 template system + CSV logging
- Dockerfile — determine apt vs conda for PDAL in container
- Expose SMRF parameters as CLI args (Phase 4)
- Add `BuildOverviews` step after `writers.gdal` for full COG (Phase 4)

---

## Project 3 — FastAPI Spatial API

**Files:** `main.py`, `.env`

### What it does
`GET /features?bbox=minLon,minLat,maxLon,maxLat&limit=1000`
Returns ABS 2021 Mesh Block boundaries as GeoJSON from PostGIS.

### Database
- DB: `census` on `localhost:5432`, user `postgres`
- Table: `public.mesh_blocks`
- Geometry: `geom geometry(MultiPolygon, 7844)` — GDA2020
- GIST index on `geom`
- ~367k rows

### Architecture
- `psycopg2.pool.SimpleConnectionPool` (1–10 connections)
- Lifespan context manager for pool init/teardown
- SQL uses `ST_Intersects` + `ST_Transform` (geom stored as 7844, bbox input as 4326)
- Response: `application/geo+json` via `fastapi.responses.Response`

### Endpoints
| Endpoint | Description |
|---|---|
| `GET /` | Service info |
| `GET /health` | DB connectivity + row count |
| `GET /features` | Spatial bbox query, returns FeatureCollection |

### Running
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### PowerShell note
Use `curl.exe` not `curl` — PowerShell aliases `curl` to `Invoke-WebRequest`.

### Phase 5 — next step
Load in QGIS: Layer › Add Layer › Add Vector Layer › Protocol (HTTP)
URI: `http://localhost:8000/features?bbox=150.8,-33.9,151.3,-33.7&limit=2000`

---

## Project 4 — DTM → PostGIS

### Goal
Load ELVIS DTM tile into PostGIS, query with `ST_Value`, `ST_SummaryStats`, `ST_MapAlgebra`. Produce decision note: PostGIS raster vs COG + TiTiler.

### Environment quirks
- `raster2pgsql` is **not** in OSGeo4W PATH — use: `"C:\Program Files\PostgreSQL\16\bin\raster2pgsql.exe"`
- Always pass `schema.table` explicitly to `raster2pgsql` — missing it causes the filename to be parsed as the schema name

### Source data
- File: `vmelev_dem10m.tif` (ELVIS tile, 10m resolution)
- CRS: EPSG:7855 (GDA2020 / MGA zone 55)
- DB: `geodb`, schema: `dtm`, table: `dtm.elevation`

### Load command (correct form)
```bash
raster2pgsql -s 7855 -t 256x256 -I -C -M -N -9999 \
  "C:\path\to\vmelev_dem10m.tif" \
  dtm.elevation > dtm_load.sql

psql -h localhost -p 5432 -U postgres -d geodb -f dtm_load.sql
```

### Current phase: Phase 3 — queries in progress
- Verify load with `ST_MetaData`
- `ST_Value` at a known point
- `ST_SummaryStats` on full raster and clipped region
- `ST_MapAlgebra` reclassification (class breaks TBD from actual min/max)

### Open TODOs
1. Confirm raster loaded correctly
2. Run `ST_Value` and `ST_SummaryStats` with `\timing`
3. Run `ST_MapAlgebra` — adjust class breaks to actual elevation range
4. Record timings and table sizes
5. Write PostGIS raster vs COG + TiTiler decision note

---

## Shared Infrastructure

### PostGIS databases
| Database | Purpose |
|---|---|
| `census` | ABS Mesh Blocks (FastAPI API) |
| `geodb` | DTM raster analysis |

### Deployment target
Docker on Ubuntu 22.04. COGs served from S3 via TiTiler.

### Project structure
```
Geoprocessor/
├── geoprocessor.py
├── requirements.txt          # numpy, pytest — gdal from apt
├── Dockerfile
├── .gitignore
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_geoprocessor.py
└── pipeline/
    ├── __init__.py
    ├── run_pipeline.py       # Phase 2 in progress
    ├── .gitignore
    └── output/
        └── .gitkeep          # binaries are gitignored
```

### .gitignore for pipeline/output
```
pipeline/output/*.tif
pipeline/output/*.laz
pipeline/output/*.copc.laz
!pipeline/output/.gitkeep
```
