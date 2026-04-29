---
tags: [concept, postgis, postgresql, spatial, raster]
created: 2026-04-22
updated: 2026-04-22
status: active
type: concept
related: [[fastapi-spatial-api]], [[dtm-postgis]], [[postgis-vs-titiler]]
---

# PostGIS

PostgreSQL spatial extension. Adds geometry/geography types, spatial indexes (GIST), and raster support (`raster` type via PostGIS Raster).

---

## Databases in Use

| Database | Purpose | Key Table |
|---|---|---|
| `census` | ABS Mesh Blocks for [[fastapi-spatial-api]] | `public.mesh_blocks` |
| `geodb` | ELVIS DTM raster for [[dtm-postgis]] | `dtm.elevation` |

---

## Key Functions Used

### Geometry (census / FastAPI)

| Function | Purpose |
|---|---|
| `ST_Intersects(geom, bbox)` | Spatial filter |
| `ST_Transform(geom, srid)` | Reproject geometry |
| `ST_AsGeoJSON(geom)` | Serialize to GeoJSON |

### Raster (geodb / DTM)

| Function | Purpose |
|---|---|
| `ST_MetaData(rast)` | Raster metadata (size, CRS, pixel size) |
| `ST_Value(rast, point)` | Elevation at a single point |
| `ST_SummaryStats(rast)` | min, max, mean, stddev, count |
| `ST_MapAlgebra(rast, ...)` | Per-pixel reclassification |
| `ST_Intersects(rast, geom)` | Spatial filter for raster tiles |

---

## Loading Rasters

Use `raster2pgsql` — see [[dtm-postgis]] for the exact command and path quirks.  
Tile size: 256×256. Always pass `-s <srid>` and `schema.table` explicitly.

---

## Connection (psycopg2)

```python
psycopg2.pool.SimpleConnectionPool(1, 10,
    host="localhost", port=5432, dbname="census", user="postgres"
)
```
