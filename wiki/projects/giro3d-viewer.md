---
tags: [project, giro3d, copc, cog, webgl, three.js, github-pages]
created: 2026-04-27
updated: 2026-04-27
status: complete
type: project
related: [[pipeline-system]], [[copc]], [[cog]], [[r2-setup]]
---

# Giro3D COPC Viewer

WebGL point cloud viewer built on [Giro3D](https://giro3d.org/) v2.0.2. Loads a COPC file from Cloudflare R2, drapes a COG DTM terrain underneath, and exposes ASPRS classification filtering and Eye-Dome Lighting. Hosted on GitHub Pages.

**Repo:** `ucpasas/geospatial-vision`  
**Live viewer:** https://ucpasas.github.io/geospatial-vision/giro3d-viewer/  
**Portfolio:** https://ucpasas.github.io/geospatial-vision/  
**Source dir:** `giro3d-viewer/`

---

## Phase Status

| Phase | Status | Description |
|---|---|---|
| 1 | ✅ Done | Scaffold + COPC load + Eye-Dome Lighting |
| 2 | ✅ Done | ASPRS classification panel + colour-by-attribute |
| 3 | ✅ Done | COG terrain via TiTiler ElevationLayer |
| 4 | ✅ Done | GitHub Pages deployment via GitHub Actions |

---

## Architecture

### Module layout

```
giro3d-viewer/
├── src/
│   ├── config.js        ← all env-specific values (URLs, paths)
│   ├── main.js          ← thin orchestrator
│   ├── viewer.js        ← Giro3D Instance, EDL, camera
│   ├── pointcloud.js    ← COPCSource, PointCloud, colour map
│   ├── terrain.js       ← Map, ElevationLayer
│   ├── filters.js       ← pure filter logic, no renderer imports
│   └── ui.js            ← DOM only, no renderer imports
├── public/assets/wasm/  ← laz-perf.wasm (copied at build time)
├── index.html
├── vite.config.js
└── package.json
```

### Layered design rule (CesiumJS pattern)

Only `viewer.js`, `pointcloud.js`, and `terrain.js` import from `@giro3d/giro3d`. `filters.js` and `ui.js` are renderer-agnostic — they can be reused if the renderer is swapped for Potree or CesiumJS.

### Data flow

```
USGS LAZ → PDAL pipeline → COG DTM + COPC → Cloudflare R2
  COG → TiTiler (Render) → terrain tiles → Giro3D ElevationLayer
  COPC → COPCSource → point stream → Giro3D PointCloud
  → Browser (EPSG:6343, Three.js, laz-perf WASM) → GitHub Pages
```

---

## Phase 1 — Scaffold + COPC + EDL

- Vite project with `@giro3d/giro3d` v2.0.2
- COPC loaded from Cloudflare R2 via `COPCSource`
- Rendered natively in **EPSG:6343** (NAD83(2011) / UTM zone 14N) — hardcoded, no epsg.io fetch at runtime
- `CoordinateSystem.register("EPSG:6343", proj4_string)` called before `Instance` creation
- Eye-Dome Lighting enabled by default: radius 0.6, strength 5
- laz-perf WASM path set via `setLazPerfPath()` in `config.js`; handles localhost vs Pages subdirectory automatically

---

## Phase 2 — Classification Filtering + Colouring

- Full ASPRS panel (all 19 classes, 0–18)
- Classes present in the file: active checkboxes; absent: greyed out/disabled
- Class 18 (high noise) hidden by default
- Filters operate at `source.filters` level — filtered classes are never decoded (saves bandwidth + GPU memory)
- Colour by attribute: Z, Intensity, ReturnNumber, etc.
- Colour ramp selector: Bathymetry, Viridis, Jet, Magma, Greys
- Uses `colormap` npm package (same as official Giro3D example), 256-shade precision

---

## Phase 3 — COG Terrain via TiTiler

- COG DTM produced by the [[pipeline-system]] and uploaded to R2 under `cog/` prefix
- TiTiler deployed on Render (free tier, Docker image `ghcr.io/developmentseed/titiler:latest`)
- Terrain served as `WebMercatorQuad` tiles; Giro3D `ElevationLayer` consumes them
- COG confirmed: EPSG:6343, 3076×3517, overviews [2,4,8], nodata -9999
- COPC and COG spatially aligned — confirmed visually (ground points sit on terrain surface when class 2 only is displayed)
- **Known issue:** `MapboxTerrainFormat` expects terrain-RGB encoded tiles but TiTiler `/cog/tiles/` serves raw elevation. Terrain values are incorrect. Will be resolved when the Cloudflare Worker COG proxy is built (see Backlog).

---

## Phase 4 — GitHub Pages Deployment

- GitHub Actions workflow at `.github/workflows/deploy.yml`
- Builds viewer with Vite (`base: "./"`, `target: "esnext"`); copies laz-perf WASM in CI before build
- Assembles `dist/` with viewer + portfolio landing page
- Deploys to `ucpasas.github.io/geospatial-vision`

---

## Key Config Values (`config.js`)

```js
COPC_URL        // Cloudflare R2 public URL for .copc.laz
LAZ_PERF_PATH   // /assets/wasm on localhost; /geospatial-vision/giro3d-viewer/assets/wasm on Pages
TERRAIN_URL     // TiTiler WebMercatorQuad tile endpoint pointing at COG on R2
TERRAIN_PROJECTION  // "EPSG:3857"
```

No secrets in `config.js` — all URLs are public R2.dev or public Render endpoints.

---

## Source Data

| Property | Value |
|---|---|
| File | `USGS_LPC_TX_Central_B1_2017_stratmap17_50cm_2996011a1_LAS_2019.laz` |
| Points | ~19M per tile |
| CRS | EPSG:6343 (NAD83(2011) / UTM zone 14N) |
| Ground ratio | ~77% |
| Density | 5.42 ppsm |
| DTM resolution | 0.5m |
| License | US Government Public Domain |
| Attribution | "U.S. Geological Survey, National Geospatial Program (3DEP)" |

---

## Infrastructure

| Service | Role | Notes |
|---|---|---|
| Cloudflare R2 | Hosts COPC + COG | Public R2.dev URLs, CORS open |
| TiTiler on Render | Serves terrain tiles | Free tier — spins down after idle (~30s cold start). Temporary. |
| GitHub Pages | Hosts viewer + portfolio | Source: GitHub Actions |

---

## Key Technical Decisions

| Decision | Choice | Reason |
|---|---|---|
| CRS | EPSG:6343 hardcoded | Matches USGS source; no epsg.io fetch at runtime |
| WASM | laz-perf (peer dep of giro3d) | Ships with `@giro3d/giro3d`, LASzip C++ via Emscripten |
| Classification filter | `source.filters` (not visibility) | Filtered classes never decoded — saves bandwidth + memory |
| Colour ramp | `colormap` npm package | Same as official Giro3D example |
| Terrain | TiTiler on Render | Fastest path to live; swap `TERRAIN_URL` when Worker is ready |
| Bundler | Vite 5 | Fast dev HMR, Rollup for prod, `esnext` target |
| Architecture | Layered (CesiumJS pattern) | `filters.js` + `ui.js` renderer-agnostic — validated against Cesium/Esri |

---

## Backlog

1. **Cloudflare Worker — COG tile proxy** *(priority)* — Replace TiTiler on Render with a Worker that proxies COG range requests from R2. Investigate `geotiff.js` / `georaster` for COG decoding in Worker (128MB memory + CPU time limits — test with float64 tiles first). Only change needed in app: update `TERRAIN_URL` in `config.js`.
2. **Fix terrain-RGB mismatch** — `MapboxTerrainFormat` expects terrain-RGB encoding. Either find a terrain-RGB TiTiler endpoint or swap the format class. Blocked until Worker or alternative endpoint is available.
3. **On-the-fly LAZ rendering** — Stream raw LAZ without pre-converting to COPC. Replace `pointcloud.js` only; other modules unchanged. Requires WebWorker + laz-perf + browser-side octree build. Build COG Worker first to learn the range-request pattern.
4. **Potree comparison** — Same COPC data + classification filter, different renderer. Validates the modular architecture (`filters.js`, `ui.js`, `terrain.js` should be reusable unchanged).
5. **Multi-tile support** — When batch pipeline processing is added, the viewer needs to handle multiple COPC files. `COPCSource` is single-URL — investigate Giro3D multi-source or tile-switching UI.
6. **CRS migration to EPSG:7855** — When Australian data is added, update `viewer.js` registration and `index.html` panel label. Currently EPSG:6343 throughout.
