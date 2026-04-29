---
tags: [concept, gdal, raster, python, geospatial]
created: 2026-04-22
updated: 2026-04-22
status: active
type: concept
related: [[cog]], [[geoprocessor]], [[python-install-rules]]
---

# GDAL

Geospatial Data Abstraction Library. Handles raster (GDAL) and vector (OGR) I/O, format conversion, reprojection, and raster math.

**Version in use:** 3.8.4 (via apt)  
**Install:** `apt install python3-gdal gdal-bin libgdal-dev` — see [[python-install-rules]]

---

## Key APIs Used in This Project

| API | Used for |
|---|---|
| `gdal.Open()` | Open raster datasets |
| `gdal.Warp()` | Reproject, clip, resample |
| `gdal.Translate()` | Format conversion (e.g. → COG) |
| `gdal.BuildOverviews()` | Generate overview pyramid for [[cog]] |
| `osr.SpatialReference` | CRS operations, EPSG lookup |
| `osr.CoordinateTransformation` | Convert resolution units between CRS |
| `band.GetStatistics()` | min, max, mean, stddev |

---

## Rules (from [[geoprocessor]])

- `gdal.UseExceptions()` at module level — enables Python exceptions instead of silent failures
- Always do an explicit `None` check after `gdal.Open()` — some drivers fail silently even with `UseExceptions()`
- Do not store datasets on `self` — open, use, release per method

---

## Known Gotchas

- `targetAlignedPixels=True` in `gdal.Warp()` requires explicit `xRes`/`yRes`
- Passing resolution in metres to a geographic CRS (degrees) causes `Warp` to hang
- `srs.AutoIdentifyEPSG()` hangs on some GDAL/PROJ builds — use `IsSame()` for comparison
