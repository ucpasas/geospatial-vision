---
tags: [environment, python, gdal, numpy, install, rules]
created: 2026-04-22
updated: 2026-04-22
status: active
type: environment
related: [[gdal]], [[pdal]], [[conda-lidar-env]], [[wsl2-setup]]
---

# Python Install Rules

Critical constraints. Deviating from these breaks ABI compatibility and causes silent runtime failures.

---

## The Rules

| Package | Method | Why |
|---|---|---|
| `gdal` / `osgeo` | **apt only** (`python3-gdal`) | Must match the C library ABI of `libgdal-dev` |
| `numpy` | **apt only** (`python3-numpy`) | Must match GDAL's compiled numpy ABI |
| `pdal` / `python-pdal` | **conda-forge only** (`lidar` env) | apt package missing on Ubuntu 24.04; pip incompatible with system PDAL 2.6.2 |
| `pytest`, `fastapi`, `uvicorn`, etc. | `pip` inside venv | No ABI constraints |

---

## Never Do This

```bash
# WILL BREAK GDAL
pip install gdal
pip install GDAL

# WILL BREAK GDAL
pip install numpy

# WILL FAIL — PyPI pdal requires PDAL C++ 2.7, system has 2.6.2
pip install pdal
```

---

## Correct Venv Setup (Geoprocessor)

```bash
python3 -m venv .venv --system-site-packages   # inherits apt gdal + numpy
source .venv/bin/activate
pip install pytest                              # pip packages only
```

`--system-site-packages` is the key flag — it exposes the apt-installed `osgeo` and `numpy` to the venv.

---

## Correct Pipeline Setup

See [[conda-lidar-env]].

---

## Background

Ubuntu 24.04 (Noble) dropped `python3-pdal` from apt. The PDAL team recommends conda-forge for this OS version. This is documented in [[conda-lidar-env]].
