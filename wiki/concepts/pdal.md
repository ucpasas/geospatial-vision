---
tags: [concept, pdal, lidar, pointcloud, pipeline]
created: 2026-04-22
updated: 2026-04-22
status: active
type: concept
related: [[copc]], [[smrf]], [[pipeline-system]], [[conda-lidar-env]], [[python-install-rules]]
---

# PDAL

Point Data Abstraction Library. JSON-defined pipelines for reading, filtering, and writing point cloud data.

**Version in use:** 3.5.3 (conda-forge, `lidar` env)  
**Install:** conda-forge only — see [[conda-lidar-env]] and [[python-install-rules]]

---

## Core Usage Pattern

```python
import pdal
import json

pipeline_def = json.dumps({ "pipeline": [...] })
pipeline = pdal.Pipeline(pipeline_def)
pipeline.execute()

arrays = pipeline.arrays        # point data as numpy arrays
metadata = pipeline.metadata    # JSON metadata string
schema = pipeline.schema        # field definitions
```

Always use `pdal.Pipeline(json_string).execute()` — never subprocess.

---

## Readers

| Reader | Use |
|---|---|
| `readers.las` | Read .las/.laz files. Pass `override_srs` as WKT to avoid silent CRS failures. |

---

## Filters Used in This Project

| Filter | Purpose |
|---|---|
| `filters.smrf` | Ground classification — stamps Classification 2. See [[smrf]]. |
| `filters.range` | Keep/drop points by attribute. Used to keep only `Classification[2:2]`. |

---

## Writers

| Writer | Use |
|---|---|
| `writers.gdal` | Interpolate points to raster (IDW, mean, etc.). Outputs GeoTIFF. |
| `writers.copc` | Write Cloud-Optimised Point Cloud. See [[copc]]. |

---

## SRS Handling

Never hardcode SRS. Read from file at runtime:

```python
reader = pdal.Pipeline(json.dumps({
    "pipeline": [{"type": "readers.las", "filename": str(path)}]
}))
reader.execute()
wkt = json.loads(reader.metadata)["metadata"]["readers.las"][0]["srs"]["wkt"]
```

Then pass `"override_srs": wkt` to both the DTM and COPC pipelines.

---

## Performance

Phase 1 POC: 18,991,582 points read in 3.32s from a real USGS .laz tile.
