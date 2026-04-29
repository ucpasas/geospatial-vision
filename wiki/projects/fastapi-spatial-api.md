---
tags: [project, fastapi, postgis, geojson, api]
created: 2026-04-22
updated: 2026-04-22
status: active
type: project
related: [[postgis]], [[wsl2-setup]]
---

# FastAPI Spatial API

`GET /features` endpoint returning ABS 2021 Mesh Block boundaries as GeoJSON from [[postgis]].

**Source:** `main.py`, `.env`  
**DB:** `census` on `localhost:5432`  
**Phase 4 complete. Phase 5 (QGIS load) is next.**

---

## Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Service info |
| `GET /health` | DB connectivity + row count |
| `GET /features?bbox=minLon,minLat,maxLon,maxLat&limit=1000` | Spatial bbox query → GeoJSON FeatureCollection |

---

## Database

- DB: `census`, user: `postgres`, port: `5432`
- Table: `public.mesh_blocks`
- Geometry: `geom geometry(MultiPolygon, 7844)` — GDA2020 (EPSG:7844)
- GIST index on `geom`
- ~367k rows

---

## Architecture

- `psycopg2.pool.SimpleConnectionPool` (1–10 connections)
- Lifespan context manager for pool init/teardown
- `ST_Intersects` + `ST_Transform` — geom stored as 7844, bbox input as 4326
- Response: `application/geo+json` via `fastapi.responses.Response`

---

## Running

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**PowerShell note:** use `curl.exe` not `curl` (PowerShell aliases `curl` to `Invoke-WebRequest`).

---

## Phase 5 — Next Step

Load in QGIS:  
Layer › Add Layer › Add Vector Layer › Protocol (HTTP)  
URI: `http://localhost:8000/features?bbox=150.8,-33.9,151.3,-33.7&limit=2000`

---

## Open TODOs

- [ ] Phase 5 — verify QGIS WFS load
- [ ] Consider pagination for large bbox queries
