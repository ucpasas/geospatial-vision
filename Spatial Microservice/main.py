import os
import logging
from contextlib import asynccontextmanager
import json

import psycopg2
import psycopg2.pool
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware

# For Proj9 implementation
from typing import Optional
from pyproj import Transformer, CRS
from pyproj.aoi import AreaOfInterest
from pyproj.exceptions import CRSError

FEATURES_SQL = """
SELECT jsonb_build_object(
    'type',     'FeatureCollection',
    'features', COALESCE(jsonb_agg(feat), '[]'::jsonb)
) AS geojson
FROM (
    SELECT jsonb_build_object(
        'type',       'Feature',
        'geometry',   ST_AsGeoJSON(ST_Transform(geom, 4326))::jsonb,
        'properties', jsonb_build_object(
            'mb_code21',          mb_code21,
            'mb_category_name_2021', mb_category_name_2021,
            'state_name_2021',       state_name_2021,
            'area_albers_sqkm',      area_albers_sqkm,
            'dwelling',              dwelling,
            'person',                person
        )
    ) AS feat
    FROM mesh_blocks
    WHERE ST_Intersects(
        geom,
        ST_Transform(
            ST_MakeEnvelope(%(minx)s, %(miny)s, %(maxx)s, %(maxy)s, 4326),
            7844
        )
    )
    LIMIT %(limit)s
) sub
"""

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DB_CONFIG = dict(
    host=os.getenv("PG_HOST", "localhost"),
    port=int(os.getenv("PG_PORT", "5432")),
    dbname=os.getenv("PG_DBNAME", "census"),
    user=os.getenv("PG_USER", "postgres"),
    password=os.getenv("PG_PASSWORD", ""),
)

pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    log.info("Connecting to PostGIS at %(host)s:%(port)s/%(dbname)s ...", DB_CONFIG)
    pool = psycopg2.pool.SimpleConnectionPool(minconn=1, maxconn=10, **DB_CONFIG)
    log.info("Connection pool ready.")
    yield
    if pool:
        pool.closeall()
        log.info("Connection pool closed.")

app = FastAPI(
    title="Mesh Block Spatial API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

def get_conn():
    return pool.getconn()

def release_conn(conn):
    if pool and conn:
        pool.putconn(conn)

@app.get("/health")
def health():
    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM mesh_blocks;")
            total = cur.fetchone()[0]
        return {"status": "ok", "mesh_blocks_total": total}
    except Exception as exc:
        log.error("Health check failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"Database error: {exc}")
    finally:
        release_conn(conn)

@app.get("/features")
def get_features(
    bbox: str = Query(..., example="150.8,-33.9,151.3,-33.7"),
    limit: int = Query(default=1000, ge=1, le=5000),
):
    minx, miny, maxx, maxy = parse_bbox(bbox)
    log.info("bbox=(%.4f,%.4f,%.4f,%.4f) limit=%d", minx, miny, maxx, maxy, limit)

    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(FEATURES_SQL, {
                "minx": minx, "miny": miny,
                "maxx": maxx, "maxy": maxy,
                "limit": limit,
            })
            row = cur.fetchone()

        geojson = row[0] if row else {"type": "FeatureCollection", "features": []}
        log.info("Returning %d features.", len(geojson.get("features", [])))
        return Response(
            content=json.dumps(geojson),
            media_type="application/geo+json",
        )

    except HTTPException:
        raise
    except Exception as exc:
        log.error("Query failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Spatial query error: {exc}")
    finally:
        release_conn(conn)

def parse_aoi(raw: Optional[str]) -> Optional[AreaOfInterest]:
    """Parse optional 'minLon,minLat,maxLon,maxLat' into a pyproj AreaOfInterest."""
    if raw is None:
        return None
    try:
        parts = [float(v.strip()) for v in raw.split(",")]
    except ValueError:
        raise HTTPException(status_code=422, detail="area_of_interest values must be numeric.")
    if len(parts) != 4:
        raise HTTPException(
            status_code=422,
            detail="area_of_interest must have exactly 4 values: minLon,minLat,maxLon,maxLat.",
        )
    west, south, east, north = parts
    return AreaOfInterest(west_lon_degree=west, south_lat_degree=south,
                          east_lon_degree=east, north_lat_degree=north)

def make_transformer(source_crs: str, target_crs: str, area_of_interest: Optional[AreaOfInterest] = None) -> Transformer:
    """
    Build a pyproj Transformer with always_xy=True.

    Why always_xy=True:
      PROJ 9 respects the official EPSG axis order, which for geographic CRS
      (e.g. EPSG:4326, EPSG:4283, EPSG:7844) is latitude-first. GeoJSON however
      mandates longitude-first (x, y) per RFC 7946. always_xy=True forces PROJ
      to treat all CRS as (longitude, latitude) / (easting, northing) consistently.

    area_of_interest:
      Passed to PROJ as a hint when multiple candidate operations exist.
      For Australia: AreaOfInterest(112.85, -43.7, 153.69, -9.86) ensures PROJ
      selects the GDA94 <-> GDA2020 regional grid over a global Helmert fallback
      when NTv2 grid files are installed.
    """
    try:
        CRS(source_crs)
    except CRSError as exc:
        raise HTTPException(status_code=422, detail=f"Unknown source CRS '{source_crs}': {exc}")
    try:
        CRS(target_crs)
    except CRSError as exc:
        raise HTTPException(status_code=422, detail=f"Unknown target CRS '{target_crs}': {exc}")

    try:
        return Transformer.from_crs(
            source_crs,
            target_crs,
            always_xy=True,
            area_of_interest=area_of_interest,
        )
    except CRSError as exc:
        raise HTTPException(status_code=422, detail=f"Cannot build transform '{source_crs}' → '{target_crs}': {exc}")
    
def transform_geometry(geom: dict, transformer: Transformer) -> dict:
    """Recursively reproject a GeoJSON geometry dict. Preserves Z values."""
    gtype = geom.get("type")
    coords = geom.get("coordinates")

    def reproject_coord(c):
        x, y = transformer.transform(c[0], c[1])
        return [x, y] + list(c[2:])  # preserve Z if present

    def reproject_ring(ring):
        return [reproject_coord(c) for c in ring]

    if gtype == "Point":
        new_coords = reproject_coord(coords)
    elif gtype in ("MultiPoint", "LineString"):
        new_coords = [reproject_coord(c) for c in coords]
    elif gtype in ("MultiLineString", "Polygon"):
        new_coords = [reproject_ring(ring) for ring in coords]
    elif gtype == "MultiPolygon":
        new_coords = [[reproject_ring(ring) for ring in poly] for poly in coords]
    elif gtype == "GeometryCollection":
        return {
            "type": "GeometryCollection",
            "geometries": [transform_geometry(g, transformer) for g in geom["geometries"]],
        }
    else:
        raise HTTPException(status_code=422, detail=f"Unsupported geometry type: {gtype!r}")

    return {"type": gtype, "coordinates": new_coords}

@app.post("/transform")
def transform_features(body: dict = Body(...)):
    # validate required fields
    missing = [f for f in ("source_crs", "target_crs", "geojson") if f not in body]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required field(s): {missing}. "
                   f"Expected: {{source_crs, target_crs, geojson[, area_of_interest]}}",
        )

    source_crs = body["source_crs"]
    target_crs = body["target_crs"]
    geojson    = body["geojson"]
    raw_aoi    = body.get("area_of_interest")

    # validate geojson has a type
    if not isinstance(geojson, dict) or "type" not in geojson:
        raise HTTPException(
            status_code=422,
            detail=(
                "The 'geojson' field must be a GeoJSON object with a 'type' property. "
                "Note: GeoJSON does not carry a CRS — supply source_crs separately."
            ),
        )

    aoi = parse_aoi(raw_aoi)
    transformer = make_transformer(source_crs, target_crs, area_of_interest=aoi)
    log.info("Transform %s → %s%s", source_crs, target_crs, f" aoi={raw_aoi}" if aoi else "")

    try:
        gtype = geojson["type"]

        if gtype == "FeatureCollection":
            features = []
            for f in geojson.get("features", []):
                if not isinstance(f.get("geometry"), dict):
                    raise HTTPException(status_code=422, detail="Feature missing a 'geometry' object.")
                features.append({**f, "geometry": transform_geometry(f["geometry"], transformer)})
            result = {**geojson, "features": features}

        elif gtype == "Feature":
            if not isinstance(geojson.get("geometry"), dict):
                raise HTTPException(status_code=422, detail="Feature missing a 'geometry' object.")
            result = {**geojson, "geometry": transform_geometry(geojson["geometry"], transformer)}

        else:
            # bare geometry — Point, Polygon, MultiPolygon, etc.
            result = transform_geometry(geojson, transformer)

    except HTTPException:
        raise
    except Exception as exc:
        log.error("Transform failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Reprojection error: {exc}")

    return Response(content=json.dumps(result), media_type="application/geo+json")
    
def parse_bbox(raw: str) -> tuple[float, float, float, float]:
    try:
        parts = [float(v.strip()) for v in raw.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="bbox values must be numeric.")
    if len(parts) != 4:
        raise HTTPException(status_code=400, detail="bbox must have exactly 4 values: minLon,minLat,maxLon,maxLat.")
    minx, miny, maxx, maxy = parts
    if minx >= maxx:
        raise HTTPException(status_code=400, detail="bbox: minx must be less than maxx.")
    if miny >= maxy:
        raise HTTPException(status_code=400, detail="bbox: miny must be less than maxy.")
    return minx, miny, maxx, maxy

@app.get("/")
def root():
    return {"status": "ok", "service": "Mesh Block Spatial API"}
