---
tags: [environment, wsl2, ubuntu, vscode, setup]
created: 2026-04-22
updated: 2026-04-22
status: active
type: environment
related: [[python-install-rules]], [[conda-lidar-env]]
---

# WSL2 Setup

Development environment for geospatial-vision.

---

## Specs

| Component | Detail |
|---|---|
| OS | WSL2 — Ubuntu 24.04 (Noble) |
| Kernel | 6.6.87.2-microsoft-standard-WSL2 |
| Editor | VS Code with Remote WSL extension |
| Python | 3.12.3 (system) |
| GDAL | 3.8.4 (apt) |
| PDAL | 2.6.2 (apt, C++ only — Python bindings via conda) |

---

## Tool Split

| Tool / Operation | Where it runs |
|---|---|
| Python / GDAL / PDAL pipelines | WSL2 (Ubuntu 24.04) |
| PostGIS / psql queries | Windows side (OSGeo4W or native psql) |
| QGIS | Windows side |
| raster2pgsql | Windows side (`C:\Program Files\PostgreSQL\16\bin\`) |

---

## Production Target

Docker on **Ubuntu 22.04**. Dev WSL2 environment mirrors production as closely as possible.  
COGs served from S3 via TiTiler.

---

## Key Paths

| Path | Purpose |
|---|---|
| `/home/kisar/src/geospatial-vision/` | Main repo |
| `/home/kisar/src/wiki/geospatial-vision/` | This wiki vault |
| `Geoprocessor/.venv/` | Geoprocessor project venv |
| `~/miniconda3/` | Conda base installation |
