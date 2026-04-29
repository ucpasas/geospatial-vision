---
tags: [decision, postgis, cog, titiler, raster, architecture]
created: 2026-04-22
updated: 2026-04-22
status: pending
type: decision
related: [[postgis]], [[cog]], [[dtm-postgis]]
---

# Decision: PostGIS Raster vs COG + TiTiler

Trade-off analysis for serving the DTM. To be written after Phase 3 of [[dtm-postgis]] is complete.

---

## Context

The ELVIS DTM tile has been loaded into [[postgis]] (`dtm.elevation`, EPSG:7855, 10m resolution). The same data could be served as a [[cog]] from S3 via TiTiler. Phase 3 benchmarks will inform this decision.

---

## Dimensions to Evaluate

| Dimension | PostGIS Raster | COG + TiTiler |
|---|---|---|
| Point query (`ST_Value`) | Fast for indexed tiles | Requires HTTP range request + decode |
| Area stats (`ST_SummaryStats`) | Native SQL aggregation | Client-side computation or TiTiler statistics API |
| Reclassification (`ST_MapAlgebra`) | In-database, no data movement | Not natively supported — requires custom processing |
| Spatial joins with vector data | Natural via PostGIS | Requires separate pipeline |
| Tile serving (XYZ/WMTS) | Complex — requires pg_tileserv or manual | Native — TiTiler handles this |
| Storage | ~3–5× larger than COG (uncompressed raster tiles) | Compact, compressed, single file |
| Scalability | Vertical (bigger Postgres) | Horizontal (S3 + Lambda/container) |
| Setup complexity | Already done | S3 upload + TiTiler deployment |

---

## Pending Benchmarks (Phase 3)

- `ST_Value` at a single point — record ms
- `ST_SummaryStats` on full raster — record ms + table size
- `ST_MapAlgebra` reclassification — record ms

---

## Decision

*To be written after Phase 3 benchmarks.*
