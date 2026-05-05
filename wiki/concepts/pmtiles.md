---
tags: [concept, pmtiles, vector-tiles, cloud, http-range]
created: 2026-05-05
updated: 2026-05-05
status: active
type: concept
related: [[cog]], [[copc]], [[map-viewer]], [[geo-viz]], [[r2-setup]]
---

# PMTiles

A single-file archive format for map tiles (raster or vector) that supports HTTP range requests. Created by [Protomaps](https://protomaps.com/). The tile equivalent of [[cog]] for rasters and [[copc]] for point clouds — no tile server required.

---

## Key Properties

- **Single file** — entire tile pyramid in one `.pmtiles` file
- **HTTP range-request friendly** — clients fetch only the tiles needed for the current viewport
- **No tile server** — serve directly from R2, S3, or any static host
- **Vector or raster** — used here for ABS Mesh Block vector tiles
- **Efficient** — `mesh_blocks.geojson` (953 MB) compresses to `mesh_blocks_v2.pmtiles` (165 MB)

---

## Browser Integration (MapLibre GL)

Register the protocol handler once before creating the map:

```js
import { Protocol } from 'pmtiles';

const protocol = new Protocol();
maplibregl.addProtocol('pmtiles', protocol.tile.bind(protocol));
```

Then reference the file with the `pmtiles://` prefix:

```js
map.addSource('mesh-blocks', {
  type: 'vector',
  url: 'pmtiles://https://<r2-endpoint>/pmtiles/mesh_blocks_v2.pmtiles',
});
```

Access a source layer by name (set at creation time):

```js
'source-layer': 'mesh_blocks'
```

---

## Creating PMTiles

This project used `go-pmtiles` CLI to convert GeoJSON → PMTiles:

```bash
# go-pmtiles binary at repo root (gitignored after use)
./go-pmtiles convert mesh_blocks.geojson mesh_blocks_v2.pmtiles
```

For larger or more complex conversions, `tippecanoe` is the standard tool — it handles simplification, feature dropping by zoom level, and attribute filtering.

---

## Storage in This Project

| File | R2 Path | Size |
|---|---|---|
| `mesh_blocks_v2.pmtiles` | `pmtiles/mesh_blocks_v2.pmtiles` | 165 MB |

Accessed via R2 public URL. Raw source files (`mesh_blocks.geojson`, `mesh_blocks_v2.pmtiles`) are gitignored — too large for GitHub.

---

## Relation to COG and COPC

All three formats solve the same problem for different data types:

| Format | Data type | Index type | Use in this project |
|---|---|---|---|
| [[cog]] | Raster (GeoTIFF) | Internal tile pyramid + overviews | Melbourne DTM, COG served via TiTiler |
| [[copc]] | Point cloud (LAZ) | Spatial octree VLR | USGS/Melbourne LiDAR via Giro3D |
| PMTiles | Vector/raster tiles | Hilbert-curve tile index | ABS Mesh Blocks via MapLibre |
