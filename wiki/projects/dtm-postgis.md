---
tags: [project, postgis, raster, dtm, raster2pgsql]
created: 2026-04-22
updated: 2026-04-22
status: in-progress
type: project
related: [[postgis]], [[cog]], [[postgis-vs-titiler]], [[wsl2-setup]]
---

# DTM → PostGIS

Load an ELVIS DTM tile into [[postgis]], run spatial queries, and produce a decision note on PostGIS raster vs COG + TiTiler.

**DB:** `geodb`, schema: `dtm`, table: `dtm.elevation`  
**Phase 3 — queries in progress.**

---

## Source Data

- File: `vmelev_dem10m.tif` (ELVIS tile, 10m resolution)
- CRS: EPSG:7855 (GDA2020 / MGA zone 55)

---

## Environment Quirk

`raster2pgsql` is **not** in OSGeo4W PATH. Use the full path:

```
"C:\Program Files\PostgreSQL\16\bin\raster2pgsql.exe"
```

Always pass `schema.table` explicitly — omitting it causes the filename to be parsed as the schema name.

---

## Load Command

```bash
raster2pgsql -s 7855 -t 256x256 -I -C -M -N -9999 \
  "C:\path\to\vmelev_dem10m.tif" \
  dtm.elevation > dtm_load.sql

psql -h localhost -p 5432 -U postgres -d geodb -f dtm_load.sql
```

---

## Phase 3 Queries

```sql
-- Verify load
SELECT ST_MetaData(rast) FROM dtm.elevation LIMIT 1;

-- Value at a known point
SELECT ST_Value(rast, ST_SetSRID(ST_MakePoint(lon, lat), 7855))
FROM dtm.elevation
WHERE ST_Intersects(rast, ST_SetSRID(ST_MakePoint(lon, lat), 7855));

-- Summary stats
SELECT (ST_SummaryStats(rast)).* FROM dtm.elevation;

-- ST_MapAlgebra reclassification (class breaks TBD from actual min/max)
```

---

## Phase Status

| Phase | Status | Description |
|---|---|---|
| 1–2 | ✅ Done | Data sourced, raster2pgsql load command confirmed |
| 3 | ⬅ In progress | `ST_MetaData`, `ST_Value`, `ST_SummaryStats`, `ST_MapAlgebra` |
| 4 | Pending | Write PostGIS raster vs COG + TiTiler decision note |

---

## Open TODOs

- [ ] Confirm raster loaded correctly via `ST_MetaData`
- [ ] Run `ST_Value` at a known point
- [ ] Run `ST_SummaryStats` on full raster and clipped region (with `\timing`)
- [ ] Run `ST_MapAlgebra` — adjust class breaks to actual elevation range
- [ ] Record timings and table sizes
- [ ] Write [[postgis-vs-titiler]] decision note
