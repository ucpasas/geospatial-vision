---
tags: [project, gdal, raster, python, docker]
created: 2026-04-22
updated: 2026-04-22
status: active
type: project
related: [[gdal]], [[cog]], [[python-install-rules]], [[pipeline-system]]
---

# Geoprocessor

Python library for raster operations built on [[gdal]]. Tests passing. Wraps `gdal` in a clean class interface with strict error handling.

**Source:** `Geoprocessor/geoprocessor.py`  
**Tests:** `Geoprocessor/tests/`  
**Env:** `.venv` with `--system-site-packages` (see [[python-install-rules]])

---

## Design Rules

1. `gdal.UseExceptions()` at **module level only** — never inside a class or function
2. `_open()` is the only entry point for dataset access
3. All GDAL calls wrapped in `try/except` — re-raise as `RuntimeError`
4. Datasets never stored on `self` — open per-method, use, release
5. Explicit `None` check after every GDAL call (some drivers fail silently)

---

## Methods

| Method | Signature | Notes |
|---|---|---|
| `reproject` | `(output_path, epsg)` | Converts resolution units via `CoordinateTransformation` before `gdal.Warp` |
| `clip_to_bbox` | `(output_path, bbox)` | bbox = `(min_x, min_y, max_x, max_y)` |
| `convert_to_cog` | `(output_path)` | Two-step: intermediate TIF → overviews → COG Translate. See [[cog]]. |
| `get_stats` | `(band=1)` | Returns `{min, max, mean, stddev}` |

---

## Test Fixture

- 10×10 single-band GeoTIFF, EPSG:32755, 10m/pixel, nodata=-9999
- Pixel values 0–99 row-major → min=0.0, max=99.0, mean=49.5 (exact)
- `scope="session"` — created once per run

---

## Known Pitfalls

- `targetAlignedPixels=True` requires explicit `xRes`/`yRes` — always pass both
- Source resolution in metres passed to a geographic CRS (degrees) causes `Warp` to hang — convert units first via `CoordinateTransformation`
- `srs.AutoIdentifyEPSG()` hangs on some GDAL/PROJ versions — use `IsSame()` for CRS comparison in tests

---

## Open TODOs

- [ ] `_estimate_output_resolution()` — upgrade from single centre-point to 5×5 grid sampling
- [ ] `convert_to_cog()` — migrate to `format="COG"` driver (GDAL 3.1+)
- [ ] `convert_to_cog()` — add `validate_cog()` helper
- [ ] Next method: `clip_and_reproject()` (clip before warp for efficiency)
- [ ] Wrap in FastAPI: `/reproject`, `/stats`, `/clip`, `/cog`

---

## Running Tests

```bash
cd Geoprocessor
source .venv/bin/activate
pytest tests/
```
