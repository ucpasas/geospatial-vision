---
tags: [environment, conda, pdal, lidar, python]
created: 2026-04-22
updated: 2026-04-22
status: active
type: environment
related: [[pdal]], [[pipeline-system]], [[python-install-rules]], [[wsl2-setup]]
---

# conda `lidar` Environment

Dedicated conda environment for the [[pipeline-system]] project. Contains [[pdal]] Python bindings from conda-forge.

**Completely separate from the Geoprocessor `.venv` — they do not interact.**

---

## Why conda?

`python3-pdal` is not available via apt on Ubuntu 24.04 (Noble). PyPI pdal 3.x requires PDAL C++ 2.7 but the system has 2.6.2 — no matching pip package. conda-forge ships both the C++ library and Python bindings together at the correct versions.

---

## Setup (one-time)

```bash
# Accept Anaconda ToS first (required before first env create)
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r

# Create env and install
conda create -n lidar python=3.12 -y
conda activate lidar
conda install -c conda-forge pdal python-pdal pytest gdal -y
```

---

## Versions

| Package | Version |
|---|---|
| Python | 3.12 |
| pdal (C++) | 3.5.3 |
| python-pdal | 3.5.3 |
| gdal (osgeo) | conda-forge latest |
| pytest | latest |

---

## Daily Use

Three environments must be active simultaneously: `(lidar)` `(.venv)` `(base)`. Order matters:

```bash
cd Geoprocessor/pipeline/
conda activate lidar
cd /home/kisar/src/geospatial-vision
source .venv/bin/activate
cd Geoprocessor/pipeline/
python run_pipeline.py <input.laz>
```

This is convoluted by design — backlog item 9 in [[pipeline-system]] tracks a `run.sh` wrapper to hide this.

---

## Notes

- This env is **local dev only** — the Dockerfile will use apt or an internal conda install
- GDAL (`osgeo`) is installed here via conda-forge because conda's Python is the active interpreter in the combined environment — the apt-installed `python3-gdal` is only reachable from system Python, which gets shadowed by conda in the activation sequence
