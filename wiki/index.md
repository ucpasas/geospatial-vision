---
type: index
created: 2026-04-22
updated: 2026-04-29
---

# geospatial-vision Wiki — Index

Master catalog. Read this first before any query or code session.
See [[WIKI_SCHEMA]] for conventions and workflows.

---

## Projects

| Page | Status | Summary |
|---|---|---|
| [[geoprocessor]] | active | Python/GDAL raster operations library — reproject, clip, COG conversion, stats |
| [[pipeline-system]] | complete | PDAL dual pipeline: DTM (COG) + COPC from .laz input. All 4 phases done. Backlog: COG overviews, batch, remote LAZ indexing. |
| [[giro3d-viewer]] | complete | Giro3D WebGL COPC viewer with EDL, ASPRS classification, COG terrain. All 4 phases live on GitHub Pages. |
| [[geo-viz]] | complete | deck.gl v9 density analytics viewer — COG range requests direct to browser, ScatterplotLayer + HexagonLayer + GeoJsonLayer. All 3 phases live on GitHub Pages. |
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
