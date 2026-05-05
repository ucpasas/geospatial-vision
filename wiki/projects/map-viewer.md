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
| Melbourne DTM COG | `Melbourne_2018_dtm.tif` | R2: `cog/Melbourne_2018_dtm.tif` |

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

Served by TiTiler on Render with `colormap_name=terrain` and `rescale=-5,100`.

---

## Deployment

Built and deployed via the shared `deploy.yaml` GitHub Actions workflow on every push to `main`. Output assembled to `dist/map-viewer/` under the Pages root.

See [[giro3d-viewer]] and [[geo-viz]] for the other viewers in the same workflow.
