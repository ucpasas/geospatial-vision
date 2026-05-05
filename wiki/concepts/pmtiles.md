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

### tippecanoe (recommended for vector tiles)

`tippecanoe` handles simplification, feature dropping by zoom level, and attribute filtering. Install via apt:

```bash
sudo apt install tippecanoe
```

Command used for ABS Mesh Blocks (367k polygons, 952 MB GeoJSON):

```bash
tippecanoe \
  --minimum-zoom=6 --maximum-zoom=13 \
  --simplification=10 \
  --coalesce-densest-as-needed \
  --drop-densest-as-needed \
  -o mesh_blocks_v2.pmtiles \
  mesh_blocks.geojson
```

**Key decisions:**
- `--maximum-zoom=13` — mesh blocks are suburb-scale; z16 produced 1.12 GB (larger than source GeoJSON)
- `--simplification=10` + `--drop-densest-as-needed` — reduced from 1.12 GB to 164 MB; acceptable quality at target zoom levels
- Output: 164 MB from 952 MB input

### go-pmtiles CLI (inspection)

Binary from GitHub releases — used for inspecting PMTiles metadata, not conversion:

```bash
# Download (version must be explicit in URL)
wget https://github.com/protomaps/go-pmtiles/releases/download/v1.30.0/go-pmtiles_1.30.0_Linux_x86_64.tar.gz
tar xf go-pmtiles_1.30.0_Linux_x86_64.tar.gz

# Inspect a PMTiles file
./pmtiles show mesh_blocks_v2.pmtiles
```

Note: the release filename format is `go-pmtiles_<version>_Linux_x86_64.tar.gz` — omitting the version from the URL causes a 404.

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
