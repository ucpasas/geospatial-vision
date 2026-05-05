---
tags: [project, deck.gl, webgl, cog, osm, github-pages]
created: 2026-04-29
updated: 2026-05-05
status: complete
type: project
related: [[pipeline-system]], [[giro3d-viewer]], [[cog]], [[r2-setup]]
---

# Geo-Viz — deck.gl Density Analytics Viewer

GPU-accelerated geospatial density viewer built on [deck.gl](https://deck.gl/) v9. Reads a COG DTM directly from Cloudflare R2 via HTTP range requests, reprojects to WGS84 in the browser, and renders point, hexagon, and vector layers with full tooltips and layer toggles. Hosted on GitHub Pages.

**Repo:** `ucpasas/geospatial-vision`  
**Live viewer:** https://ucpasas.github.io/geospatial-vision/geo-viz/  
**Portfolio:** https://ucpasas.github.io/geospatial-vision/  
**Source dir:** `geo-viz/`

---

## Phase Status

| Phase | Status | Description |
|---|---|---|
| 1 | ✅ Done | Scaffold + ScatterplotLayer — COG → WGS84 points, height colour ramp, FPS counter |
| 2 | ✅ Done | HexagonLayer + GeoJsonLayer — OSM roads from R2, tooltips, layer toggle panel |
| 3 | ✅ Done | GitHub Pages deployment — added to shared Actions workflow alongside giro3d-viewer |

---

## Architecture

### Module layout

```
geo-viz/
├── src/
│   ├── config.js        ← all environment-specific values and tunables
│   ├── cog.js           ← geotiff.js, range requests, pixel → WGS84
│   ├── projection.js    ← proj4 + geotiff-geokeys-to-proj4, WGS84 transformer
│   ├── layers.js        ← deck.gl layer constructors (only file importing deck.gl)
│   ├── tooltip.js       ← pure tooltip logic, no imports
│   ├── ui.js            ← DOM only, no renderer imports
│   └── main.js          ← thin orchestrator
├── scripts/
│   └── sample_dsm.py    ← COG metadata inspection + bbox printer
├── public/assets/       ← placeholder for local data files (gitignored)
├── index.html
├── vite.config.js
└── package.json
```

### Module ownership rule

Only `layers.js` imports from `deck.gl`. Only `cog.js` imports from `geotiff`. Only `projection.js` imports from `proj4` and `geotiff-geokeys-to-proj4`. All other modules are renderer-agnostic.

### Data flow

```
COG DTM (.tif) on Cloudflare R2
    ↓ HTTP range requests via geotiff.js
Browser reads overview at 600×600 (geotiff picks best overview)
    ↓ pixel → UTM → WGS84 via proj4 (CRS from embedded geokeys)
Array<{lon, lat, height}>
    ↓ fed to
ScatterplotLayer + HexagonLayer (deck.gl / WebGL2)
GeoJSON roads → GeoJsonLayer (R2)
    ↓
GitHub Pages
```

---

## Phase 1 — Scaffold + ScatterplotLayer

- Vite project: `deck.gl` v9, `geotiff`, `geotiff-geokeys-to-proj4`, `proj4`
- COG loaded from Cloudflare R2 via HTTP range requests — **no tile server**
- CRS derived at runtime from COG's embedded geokeys — no hardcoded proj strings
- Map centre derived from COG bounding box at runtime — no hardcoded coordinates
- Raster read at 600×600 via `readRasters({ width, height })` — geotiff picks best overview
- `nearest` resampling — avoids nodata interpolation artifacts at tile boundaries
- Nodata filter: exact `NODATA = -9999` match + `!isFinite(h)` guard
- 191k points rendered via `ScatterplotLayer` at 144 FPS
- Height colour ramp calibrated to dataset min/max at load time
- FPS counter via `requestAnimationFrame` polling `deck.metrics`
- Bbox printed to browser console on load (for Overpass query alignment)

---

## Phase 2 — HexagonLayer + GeoJsonLayer

- `HexagonLayer` — GPU aggregation over same point array, colour by mean height, extruded
- `GeoJsonLayer` — Melbourne OSM roads fetched from R2 (`vector/roads/Melbourne.geojson`), styled by highway type
- OSM data exported via Overpass API, clipped to Melbourne COG bounding box; denser urban coverage vs previous Texas data
- Roads render flat at z=0 — no terrain draping (known limitation, see below)
- All three layers toggleable via panel switches
- Tooltips on all layers: point coords/height, hex bin count/mean, road type/name
- City of Melbourne + OSM attributions in panel footer

---

## Phase 3 — GitHub Pages Deployment

- `deploy.yml` updated: `geo-viz` build step added alongside `giro3d-viewer`
- `cache-dependency-path` expanded to include `geo-viz/package-lock.json`
- `vite.config.js` base: `/geospatial-vision/geo-viz/` — matches `dist/geo-viz/` assembly in CI
- Portfolio card added to `portfolio/index.html`
- R2 URLs hardcoded in `config.js` — public, no secrets needed

---

## Key Config Values (`config.js`)

```js
COG_URL         // Cloudflare R2 public URL for COG DTM (.tif) — currently Melbourne_2018_dtm_f32_v2.tif
GEOJSON_URL     // Cloudflare R2 public URL for OSM roads (.geojson) — currently Melbourne.geojson
SAMPLE_WIDTH    // 600 — raster read width
SAMPLE_HEIGHT   // 600 — raster read height
NODATA          // -9999 — must match what PDAL wrote into the COG
INITIAL_ZOOM    // 14
INITIAL_PITCH   // 45
INITIAL_BEARING // -20
SCATTER_RADIUS  // 3 m per point
HEX_RADIUS      // 30 m bins
HEX_ELEVATION_SCALE // 4 — vertical exaggeration
```

---

## Source Data

| Property | Value |
|---|---|
| Elevation | City of Melbourne 2018 DTM COG (`Melbourne_2018_dtm_f32_v2.tif`) |
| COG CRS | EPSG:28355 (GDA94 / MGA zone 55) — derived at runtime from embedded geokeys |
| Point sample | 600×600 → 191k points |
| Roads | Melbourne OSM via Overpass API (`Melbourne.geojson`), ODbL licence |
| License | CC BY 4.0 (elevation); ODbL (roads) |

---

## Infrastructure

| Service | Role | Notes |
|---|---|---|
| Cloudflare R2 | Hosts COG DTM + roads GeoJSON | Public R2.dev URLs, CORS open |
| GitHub Pages | Hosts viewer + portfolio | Source: GitHub Actions |

No tile server required — geotiff.js reads COG directly via range requests.

---

## Key Technical Decisions

| Decision | Choice | Reason |
|---|---|---|
| Data format | COG direct via range requests | No CSV, no tile server, no derived artifacts |
| CRS handling | geotiff-geokeys-to-proj4 | Reads CRS from file metadata — no hardcoding |
| Reprojection | proj4 | Transitive dep of giro3d-viewer — stack consistent |
| Resampling | nearest | Avoids nodata interpolation at tile boundaries |
| Map centre | Derived from COG bbox | No hardcoded coordinates |
| Vite chunks | deckgl + cogtools | cogtools (geotiff, proj4) loaded once at startup only |
| FPS display | `deck.metrics` via RAF | `onAfterRender({ metrics })` is undefined in deck.gl v9 |
| Class used | `Deck` (not `DeckGL`) | `DeckGL` is the React component in `@deck.gl/react` |

### deck.gl v9 Gotchas

- **`DeckGL` → `Deck`** — `DeckGL` is the React component; vanilla JS uses `new Deck({...})`
- **Metrics** — `onAfterRender({ metrics })` is `undefined` in v9; access via `deck.metrics` in a `requestAnimationFrame` loop
- **`geotiff-geokeys-to-proj4`** — named exports: `{ toProj4, convertCoordinates }`, not a default export
- **`proj4().forward()`** — may return `{x, y}` object or `[x, y]` array depending on input format; normalise: `Array.isArray(r) ? r : [r.x, r.y]`

---

## Known Limitations

### Roads at z=0
`GeoJsonLayer` renders flat at ground level — roads are not draped onto terrain. Fix: sample DTM height at each road vertex and inject into GeoJSON coordinates. Preprocessing step, not a deck.gl feature.

### HexagonLayer with uniform grid
`HexagonLayer` is designed for density clustering. A uniform 400×400 grid produces near-equal bin counts, so extrusion shows mean elevation rather than density. Best data: raw classified LiDAR returns, GPS traces, event data.

### draw calls metric
`deck.metrics.renderCount` shows `—` — property name may differ in deck.gl v9. FPS confirmed working.

---

## Backlog

1. **Terrain draping for roads** — sample DTM at road vertices; inject Z into GeoJSON before upload to R2
2. **Raw LiDAR scatter** — load COPC returns via `@loaders.gl/las` for true density visualisation (dependency already in `package.json`)
3. **Overpass query automation** — `scripts/` directory houses `sample_dsm.py`; add Overpass fetch script keyed to COG bbox
4. **Multi-tile support** — extend `config.js` to support multiple COG URLs with a tile-selector UI

---

## Deployment

Built and deployed via the shared `deploy.yaml` GitHub Actions workflow on every push to `main`. Output assembled to `dist/geo-viz/` under the Pages root.

See [[giro3d-viewer]] and [[map-viewer]] for the other viewers in the same workflow.
