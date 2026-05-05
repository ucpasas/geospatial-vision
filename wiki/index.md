---
type: index
created: 2026-04-22
updated: 2026-05-05
---

# geospatial-vision Wiki — Index

Master catalog. Read this first before any query or code session.
See [[WIKI_SCHEMA]] for conventions and workflows.

---

## Projects

| Page | Status | Summary |
|---|---|---|
| [[geoprocessor]] | active | Python/GDAL raster operations library — reproject, clip, COG conversion, stats |
| [[pipeline-system]] | complete | PDAL multi-mode pipeline: DTM (COG) + COPC/LAZ. 5 phases done. Configurable density threshold. COPC directory merge blocked (writers.copc not streamable) — use `--mode laz` for large datasets. |
| [[giro3d-viewer]] | complete | Giro3D WebGL COPC viewer with EDL, ASPRS classification, COG terrain. All 4 phases live on GitHub Pages. |
| [[geo-viz]] | complete | deck.gl v9 density analytics viewer — COG range requests direct to browser, ScatterplotLayer + HexagonLayer + GeoJsonLayer. All 3 phases live on GitHub Pages. |
| [[map-viewer]] | complete | MapLibre GL v5 + PMTiles — ABS Mesh Blocks 2021 vector (10 categories) + Melbourne DTM COG raster. Category filters, zoom-to-CBD. Live on GitHub Pages. |
| [[fastapi-spatial-api]] | active | FastAPI + PostGIS bbox query over ABS Mesh Blocks. Phase 5 (QGIS load) next. |
| [[dtm-postgis]] | in-progress | raster2pgsql load of ELVIS DTM tile into PostGIS. Phase 3 queries in progress. |

---

## Concepts

| Page | Summary |
|---|---|
| [[gdal]] | Geospatial Data Abstraction Library — raster/vector I/O, reprojection, format conversion |
| [[pdal]] | Point Data Abstraction Library — LiDAR pipeline execution, filters, writers |
| [[cog]] | Cloud-Optimised GeoTIFF — tiled, overviewed, HTTP range-request friendly |
| [[copc]] | Cloud-Optimised Point Cloud — spatially indexed LAZ with VLR header |
| [[postgis]] | PostgreSQL spatial extension — geometry types, spatial indexes, raster support |
| [[smrf]] | Simple Morphological Filter — ground point classification for DTM generation |
| [[pmtiles]] | PMTiles single-file vector/raster tile archive — HTTP range-request friendly, no tile server required |

---

## Environment

| Page | Summary |
|---|---|
| [[wsl2-setup]] | Dev environment: WSL2 Ubuntu 24.04, VS Code Remote WSL, apt/conda/venv split |
| [[conda-lidar-env]] | `lidar` conda env with PDAL 3.5.3 from conda-forge — pipeline project only |
| [[python-install-rules]] | Critical: never pip install gdal or numpy — apt only. PDAL via conda-forge only. |
| [[r2-setup]] | Cloudflare R2 via AWS CLI `--profile r2`; bucket `geospatial-vision`; COPC under `copc/` |

---

## Decisions

| Page | Status | Summary |
|---|---|---|
| [[postgis-vs-titiler]] | pending | Trade-off analysis: PostGIS raster queries vs COG + TiTiler for DTM serving |

---

## Recent Log

See [[log]] for full session history.
