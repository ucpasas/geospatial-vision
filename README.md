# geospatial-vision

A collection of geospatial processing and visualisation projects working with LiDAR point clouds, raster terrain, and vector data. Data source: City of Melbourne 2018 3D Point Cloud (CC BY 4.0) + ABS Mesh Blocks 2021.

**Portfolio:** https://ucpasas.github.io/geospatial-vision/

---

## Projects

### Geoprocessor
`Geoprocessor/geoprocessor.py`

Python class wrapping GDAL for raster operations. Designed with strict error handling — `UseExceptions()` at module level, explicit `None` checks after every GDAL call, datasets never stored on `self`.

| Method | What it does |
|---|---|
| `reproject(output_path, epsg)` | Warps to target CRS; converts resolution units via `CoordinateTransformation` before passing to `gdal.Warp` to avoid the hang-on-geographic-CRS bug |
| `clip_to_bbox(output_path, bbox)` | Clips to `(min_x, min_y, max_x, max_y)` in source CRS units |
| `convert_to_cog(output_path)` | Intermediate TIF → `BuildOverviews` → `Translate(COPY_SRC_OVERVIEWS=YES)` |
| `get_stats(band)` | `ComputeStatistics(False)` — exact, not approximate |

```bash
cd Geoprocessor
source .venv/bin/activate   # --system-site-packages for apt gdal/numpy
pytest tests/
```

---

### Pipeline System
`Geoprocessor/pipeline/`

PDAL-based LiDAR processing pipeline. Takes a `.las`/`.laz` file or a flat directory of tiles and produces a COG DTM, COPC, and/or compressed LAZ depending on mode.

```bash
python run_pipeline.py <input> [--mode dtm+copc|dtm+laz|copc|laz] [--density-threshold PPSM]
```

**What it does under the hood:**
- Reads SRS from file at runtime via a throwaway `readers.las` pipeline — never hardcoded
- DTM: `filters.smrf` (ground classification) → `filters.range` (keep Class 2) → `writers.gdal` (0.5m IDW)
- Directory input: per-tile sequential DTM (SMRF is not streaming), then `gdal.BuildVRT` + `gdal.Translate(format="COG")` to merge
- COPC/LAZ directory merge: single PDAL run with glob input; LAZ uses `execute_streaming()` for bounded RAM
- `writers.copc` is not streamable — for large datasets (Melbourne: ~300M pts) use `--mode laz`, then convert with `untwine`

**Environment:** requires the `lidar` conda env (PDAL 3.5.3 from conda-forge) + the root `.venv` active simultaneously. See `wiki/environment/conda-lidar-env.md`.

---

### FastAPI Spatial API
`Spatial Microservice/main.py`

Single-endpoint spatial query service over ABS Mesh Blocks stored in PostGIS.

```
GET /features?bbox=minLon,minLat,maxLon,maxLat&limit=1000
```

Returns a GeoJSON `FeatureCollection`. Uses `ST_Intersects` + `ST_Transform` (geometries stored as EPSG:7844, bbox input as EPSG:4326). Connection pooling via `psycopg2.pool.SimpleConnectionPool`.

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

### DTM → PostGIS
Loads a COG DTM into PostGIS via `raster2pgsql` for `ST_Value`, `ST_SummaryStats`, and `ST_MapAlgebra` queries. Decision note pending: PostGIS raster vs COG + TiTiler for serving.

---

### giro3d-viewer
`giro3d-viewer/` · [Live](https://ucpasas.github.io/geospatial-vision/giro3d-viewer/)

3D point cloud viewer using [Giro3D](https://giro3d.org/) v2. Loads the Melbourne 2018 COPC (353M points) from Cloudflare R2 via HTTP range requests, drapes a COG DTM terrain underneath via TiTiler.

- COPC rendered natively in **EPSG:28355** (GDA94 / MGA zone 55) — proj4 string hardcoded, no runtime fetch
- LAZ decompression in-browser via `laz-perf` WASM
- ASPRS classification panel: 19 classes; filters at `source.filters` level so filtered classes are never decoded
- Eye-Dome Lighting enabled by default
- Terrain known issue: `MapboxTerrainFormat` expects terrain-RGB tiles; TiTiler serves raw elevation — values are wrong, visual is acceptable

```bash
cd giro3d-viewer && npm install && npm run dev
```

---

### geo-viz
`geo-viz/` · [Live](https://ucpasas.github.io/geospatial-vision/geo-viz/)

GPU-accelerated density analytics viewer using [deck.gl](https://deck.gl/) v9. Reads the Melbourne DTM COG directly from R2 via `geotiff.js` range requests — no tile server.

- CRS derived at runtime from COG embedded geokeys via `geotiff-geokeys-to-proj4` — no hardcoded proj strings
- Raster sampled at 600×600 → 191k WGS84 points; `nearest` resampling to avoid nodata interpolation at tile edges
- Three layers: `ScatterplotLayer` (points coloured by elevation), `HexagonLayer` (mean elevation per bin), `GeoJsonLayer` (Melbourne OSM roads)
- COG must be **float32** — float64 causes a typed array allocation error in geotiff.js for large rasters

```bash
cd geo-viz && npm install && npm run dev
```

---

### map-viewer
`map-viewer/` · [Live](https://ucpasas.github.io/geospatial-vision/map-viewer/)

2D map overlaying ABS Mesh Blocks (vector) and Melbourne DTM (raster) using MapLibre GL v5 and PMTiles. No tile server for the vector layer — PMTiles served directly from R2 via HTTP range requests.

- ABS Mesh Blocks: 367k polygons → tippecanoe → 164 MB PMTiles (`--max-zoom=13`, z16 produced a file larger than the source GeoJSON)
- COG DTM via TiTiler on Render (note: free tier cold starts cause ~30s delay on first load)
- 10 land-use categories with colour swatches; `setFilter()` on toggle
- `pmtiles://` URL prefix required — plain `https://` silently loads the source but `queryRenderedFeatures` returns empty

```bash
cd map-viewer && npm install && npm run dev
```

---

## Infrastructure

| Service | Role |
|---|---|
| Cloudflare R2 | Hosts COPC, COG, PMTiles, GeoJSON — public read, zero egress cost |
| TiTiler on Render | Serves COG terrain tiles (free tier, cold starts) |
| GitHub Pages | Hosts all three web viewers + portfolio |
| GitHub Actions | `deploy.yaml` builds all three Vite apps and assembles `dist/` on push to `main` |

---

## Environment

Dev: WSL2 Ubuntu 24.04. Three environments in play:

| Env | Activate | Used for |
|---|---|---|
| `.venv` | `source .venv/bin/activate` (from repo root) | Geoprocessor, pytest |
| `lidar` | `conda activate lidar` | Pipeline (PDAL 3.5.3, untwine, gdal) |
| Node 20 | system / nvm | All three web viewers |

**Critical:** never `pip install gdal` or `pip install numpy` — both must come from apt to stay ABI-matched. PDAL must come from conda-forge (not apt, not pip). See `wiki/environment/python-install-rules.md`.

---

## Wiki

`wiki/` — persistent knowledge base following the [llm-wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). Covers all projects, concepts (COG, COPC, PMTiles, SMRF), environment setup, and design decisions.

Start at `wiki/index.md`.
