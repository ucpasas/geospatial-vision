---
tags: [project, maplibre, pmtiles, cog, vector, github-pages]
created: 2026-05-05
updated: 2026-05-05
status: complete
type: project
related: [[pmtiles]], [[cog]], [[r2-setup]], [[pipeline-system]], [[geo-viz]]
---

# Map Viewer

2D web map overlaying ABS Mesh Blocks 2021 (vector) and Melbourne DTM 2018 (raster COG) with interactive category filtering. Built with MapLibre GL v5 and [[pmtiles]]. Deployed to GitHub Pages.

**Live viewer:** https://ucpasas.github.io/geospatial-vision/map-viewer/  
**Source dir:** `map-viewer/`  
**Stack:** MapLibre GL v5.24, PMTiles v4.4, Vite 5

---

## What It Shows

| Layer | Type | Source | Notes |
|---|---|---|---|
| ABS Mesh Blocks 2021 | Vector fill + outline | PMTiles from R2 | 10 land-use categories, colored by `mb_category_name_2021` |
| Melbourne DTM 2018 | Raster COG | TiTiler on Render → R2 | Terrain colourmap, 30% opacity overlay, zoom 12–14 |
| Basemap | Raster | OpenFreeMap | Dark style, no API key required |

---

## Data Sources

| Data | File | Location |
|---|---|---|
| ABS Mesh Blocks 2021 | `mesh_blocks_v2.pmtiles` | R2: `pmtiles/mesh_blocks_v2.pmtiles` (165 MB) |
| Melbourne DTM COG | `Melbourne_2018_dtm_f32_v2.tif` | R2: `cog/Melbourne_2018_dtm_f32_v2.tif` |

Original source: `mesh_blocks.geojson` (953 MB) → converted to PMTiles via `go-pmtiles`. The raw files are gitignored; only the hosted versions are used at runtime.

---

## Module Structure

| File | Role |
|---|---|
| `config.js` | `PMTILES_URL`, `COG_TILES_URL`, `CATEGORY_COLOURS`, `CATEGORIES` |
| `map.js` | `initProtocol()` — registers `pmtiles://` handler; `createMap()` — MapLibre init with OpenFreeMap basemap |
| `layers.js` | `addMeshBlockLayer()` — fill + outline from PMTiles; `addCOGLayer()` — raster DTM via TiTiler |
| `ui.js` | `initUI()` — layer toggles, category filters with colour swatches, zoom-to-CBD action, attribution |
| `main.js` | Entry point — wires protocol, map, layers, UI |

---

## Category Colours

Ten Mesh Block land-use categories rendered with fixed colours:

| Category | Colour |
|---|---|
| Residential | `#a8c5e8` |
| Commercial | `#f4a460` |
| Industrial | `#b8a0c8` |
| Parkland | `#90c490` |
| Education | `#f7d080` |
| Hospital/Medical | `#f08080` |
| Transport | `#c0c0c0` |
| Primary Production | `#d4b896` |
| Other | `#e0e0e0` |
| SHIPPING | `#80b4c8` |

Water bodies are excluded via a layer filter (`!= 'Water'`).

---

## UI Controls

- **Layer toggles** — show/hide DTM Terrain, MB Fill, MB Outline independently
- **Category toggles** — per-category checkboxes with colour swatches; updates `setFilter()` on both fill and outline layers in real time
- **Zoom to CBD** — `flyTo` Melbourne CBD: centre `[144.9631, -37.8136]`, zoom 13, pitch 45°, bearing −17°

---

## COG Layer Details

```js
tileSize: 256,
minzoom: 12,
maxzoom: 14,
bounds: [144.891, -37.854, 144.996, -37.771]  // Melbourne extent
```

Served by TiTiler on Render with `colormap_name=terrain` and `rescale=-5,100`. COG file: `Melbourne_2018_dtm_f32_v2.tif` (float32, v2 reprocessing of Melbourne 2018 pipeline output).

---

## Data Pipeline

### PMTiles (vector) — full build process

```
PostGIS (367k ABS Mesh Block polygons, EPSG:7844)
    ↓ ogr2ogr -t_srs EPSG:4326
mesh_blocks.geojson (952 MB)
    ↓ tippecanoe --minimum-zoom=6 --maximum-zoom=13 --simplification=10
                 --coalesce-densest-as-needed --drop-densest-as-needed
mesh_blocks_v2.pmtiles (164 MB)
    ↓ aws s3 cp --profile r2
R2: geospatial-vision/pmtiles/mesh_blocks_v2.pmtiles
    ↓ pmtiles:// protocol (browser)
```

Max zoom capped at 13 — z16 produced 1.12 GB (larger than source GeoJSON). See [[pmtiles]] for full tippecanoe command.

### COG (raster) — float32 rebuild

```
Melbourne_2018_dtm.tif (float64, 18001×18001, 1.6 GB, EPSG:28355)
    ↓ gdal_translate -ot Float32 -of COG (overviews to level 64)
Melbourne_2018_dtm_f32_v2.tif (float32, 715 MB, 6 overview levels)
    ↓ aws s3 cp --profile r2
R2: geospatial-vision/cog/Melbourne_2018_dtm_f32_v2.tif
    ↓ TiTiler on Render → WebMercatorQuad tiles
```

float64 caused array buffer allocation errors in geotiff.js. See [[cog]] for the float32 vs float64 compatibility note.

---

## Bugs Encountered

### PMTiles protocol not intercepting requests
**Symptom:** `SyntaxError: Unexpected token 'P', "PMTiles..."` — MapLibre received raw binary.  
**Cause:** Markdown renderer mangled `new maplibregl.Map({` into a hyperlink on copy-paste from Claude chat.  
**Fix:** Manually corrected `map.js` in editor.  
**Lesson:** Always inspect files after pasting code from a markdown source — dot-notation can be silently mangled.

### PMTiles URL missing protocol prefix
**Symptom:** Source loaded (`_loaded: true`) but `queryRenderedFeatures` returned empty.  
**Cause:** `PMTILES_URL` in `config.js` was a plain `https://` URL — the `pmtiles://` prefix is required for the protocol handler to intercept requests.  
**Fix:** Added `pmtiles://` prefix to `PMTILES_URL`.

### TiTiler 422 (Unprocessable Content)
**Cause 1:** `COG_TILES_URL` already contained the full tile path; `layers.js` appended the path again — duplicate URL.  
**Cause 2:** TiTiler free tier on Render spins down after inactivity; first requests fail with 422 while the instance wakes (~30s cold start). Error can look like a CORS failure.  
**Fix:** Set `COG_TILES_URL` to the complete tile URL template in `config.js`; no path construction in `layers.js`.

### COG bounds mismatch
**Symptom:** TiTiler returning "outside bounds" for Melbourne tiles.  
**Cause:** Approximate WGS84 bounds used in MapLibre raster source instead of exact corners from `gdalinfo`.  
**Fix:** Used exact bounds from `gdalinfo`: `[144.891, -37.854, 144.996, -37.771]`.

---

## Known Limitations

| Issue | Detail |
|---|---|
| TiTiler cold start | Render free tier spins down after inactivity; first tile requests fail (~30s) while waking. Looks like CORS failure. |
| PMTiles tile boundary artefacts | `--drop-densest-as-needed` causes patchiness at zoom transition boundaries. Less noticeable with category colouring. |
| Water outline | Water mesh blocks filtered from fill (`!= 'Water'`) but outline still renders over Port Phillip Bay. Minor visual issue. |
| giro3d-viewer terrain mismatch | Pre-existing: `MapboxTerrainFormat` expects terrain-RGB tiles but TiTiler serves raw elevation. Values incorrect but visual is acceptable. |

---

## Licensing & Attribution

| Dataset | Licence | Attribution |
|---|---|---|
| ABS Mesh Blocks 2021 | CC BY | © Australian Bureau of Statistics |
| City of Melbourne DTM 2018 | CC BY 4.0 | City of Melbourne, 3D Point Cloud 2018 |
| OpenFreeMap | MIT | © OpenFreeMap |
| OpenStreetMap | ODbL | © OpenStreetMap contributors |

OpenFreeMap attribution must be added manually in `ui.js` — MapLibre injects OSM attribution automatically but not OpenFreeMap.

---

## Deployment

Built and deployed via the shared `deploy.yaml` GitHub Actions workflow on every push to `main`. Output assembled to `dist/map-viewer/` under the Pages root.

See [[giro3d-viewer]] and [[geo-viz]] for the other viewers in the same workflow.
