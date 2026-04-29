---
tags: [concept, cog, raster, cloud, geotiff]
created: 2026-04-22
updated: 2026-04-29
status: active
type: concept
related: [[gdal]], [[geoprocessor]], [[pipeline-system]], [[geo-viz]], [[postgis-vs-titiler]]
---

# COG — Cloud-Optimised GeoTIFF

A GeoTIFF with internal tiling and overview pyramid arranged so HTTP range requests can read any spatial subset or zoom level without downloading the full file. Standard format for cloud-hosted rasters.

---

## Key Properties

- **Tiled:** internal tiles (typically 256×256 or 512×512) — random access by spatial location
- **Overviews:** pre-computed downsampled pyramids — fast rendering at any zoom
- **Single file:** headers at front so range requests can find data offsets immediately

---

## Creating a COG (current method in [[geoprocessor]])

Two-step process:
1. Write intermediate GeoTIFF
2. `gdal.BuildOverviews()` on intermediate
3. `gdal.Translate()` with `COPY_SRC_OVERVIEWS=YES`, `TILED=YES`, `COMPRESS=DEFLATE`

**TODO:** Migrate to `format="COG"` driver (GDAL 3.1+) — single step, no intermediate file needed.

---

## COG from PDAL (in [[pipeline-system]])

`writers.gdal` with `COMPRESS=DEFLATE,TILED=YES` produces a tiled, compressed GeoTIFF. Full COG (overviews) requires an additional `BuildOverviews` step — planned for Phase 4.

---

## Validation

`gdal_cog_validate` (gdal-bin) or the GDAL Python validator confirms COG compliance. A `validate_cog()` helper is a TODO in [[geoprocessor]].

---

## Browser-Side COG Reading (in [[geo-viz]])

COGs can be read directly in the browser via HTTP range requests using [geotiff.js](https://geotiffjs.github.io/), bypassing any tile server entirely.

```js
import { fromUrl } from 'geotiff';
const tiff  = await fromUrl(COG_URL);          // opens with a HEAD + range request for IFD
const image = await tiff.getImage();
const [band] = await image.readRasters({
  width: 400, height: 400,                     // geotiff picks the best overview
  resampleMethod: 'nearest',
  fillValue: NODATA,
});
```

- `readRasters({ width, height })` — geotiff.js selects the overview whose resolution is closest to the requested dimensions; no manual overview index needed
- `nearest` resampling avoids nodata interpolation artifacts at tile boundaries
- CRS is read from the image's embedded geokeys via `geotiff-geokeys-to-proj4` — no hardcoded proj strings required
- **CORS:** The R2 bucket must have CORS configured to allow `GET` and range request headers from the browser origin

This pattern requires no tile server (no TiTiler, no GDAL server). The tradeoff: the full tile IFD is fetched on open, and large areas at full resolution require many range requests — suitable for overview-level visualisation, not pixel-perfect queries.

---

## Serving via Tile Server

COGs served from S3 via TiTiler produce pre-rendered image tiles. See [[postgis-vs-titiler]] for the trade-off analysis. Used by [[giro3d-viewer]] for terrain tiles.
