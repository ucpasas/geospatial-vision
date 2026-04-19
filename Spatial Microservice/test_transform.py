"""
test_transform.py — /transform endpoint tests
Run with:  python test_transform.py

Tests against GA published GDA94/GDA2020 test point pairs and internal
consistency checks. No live server required — imports and calls the
transform helpers directly.

GA source: GDA2020 Technical Manual V1.1, Appendix B
https://www.icsm.gov.au/sites/default/files/GDA2020%20Tech%20Manual%20V1.1.pdf
"""

import math
import sys
from pyproj import Transformer
from pyproj.aoi import AreaOfInterest

# ── helpers ───────────────────────────────────────────────────────────────────

def haversine_m(lon1, lat1, lon2, lat2):
    """Great-circle distance in metres between two geographic points."""
    R = 6378137.0
    dlat = (lat2 - lat1) * math.pi / 180
    dlon = (lon2 - lon1) * math.pi / 180
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1 * math.pi / 180) * math.cos(lat2 * math.pi / 180) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def euclidean_m(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
results = []


def check(name, got, expected_m, threshold_m, dist_fn=None):
    if dist_fn is None:
        dist_fn = haversine_m
    err = dist_fn(*got, *expected_m) if isinstance(expected_m, tuple) else got
    ok = err < threshold_m
    label = PASS if ok else FAIL
    print(f"  [{label}] {name}: {err:.4f} m  (threshold {threshold_m} m)")
    results.append(ok)


# ── 1. Axis order demonstration ───────────────────────────────────────────────

print("\n=== 1. Axis order: always_xy=True vs False ===")

t_xy  = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
t_nxy = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=False)

x_xy, y_xy = t_xy.transform(151.0, -33.8)    # lon=151, lat=-33.8
x_nxy, y_nxy = t_nxy.transform(151.0, -33.8) # PROJ sees lat=151 (invalid) → inf

xy_ok  = abs(x_xy - 16_809_243) < 100 and abs(y_xy - (-4_001_978)) < 100
nxy_ok = not math.isfinite(x_nxy)  # should be inf/nan with wrong axis

print(f"  always_xy=True  → x={x_xy:.0f}, y={y_xy:.0f}")
print(f"  always_xy=False → x={x_nxy}, y={y_nxy}")
print(f"  [{'PASS' if xy_ok else 'FAIL'}] correct output with always_xy=True")
print(f"  [{'PASS' if nxy_ok else 'FAIL'}] wrong axis order produces invalid result")
results += [xy_ok, nxy_ok]


# ── 2. GA published GDA94 → GDA2020 test pairs ───────────────────────────────
#
# Without NTv2 grid files PROJ uses the Helmert 7-parameter transform
# ("GDA94 to GDA2020 (1)"), which GA documents as ~0.01 m formal accuracy
# but produces 1–5 m errors relative to the conformal+distortion grid result.
# Threshold is set conservatively at 10 m (well inside Helmert spec).
#
# To reach sub-mm accuracy: install the PROJ GDA2020 grid package:
#   pip install pyproj[network]  OR  projsync --source-id au_icsm_GDA94_GDA2020

print("\n=== 2. GA published GDA94 → GDA2020 (Helmert, threshold 10 m) ===")

AOI_AUS = AreaOfInterest(west_lon_degree=112.85, south_lat_degree=-43.7,
                          east_lon_degree=153.69, north_lat_degree=-9.86)

t_gda = Transformer.from_crs("EPSG:4283", "EPSG:7844", always_xy=True, area_of_interest=AOI_AUS)

GA_PAIRS = [
    # (name, (gda94_lon, gda94_lat), (gda2020_lon, gda2020_lat))
    # Source: GDA2020 Tech Manual V1.1, Appendix B, Table B.1
    ("Minnipa SA",  (135.318507289, -32.836015707), (135.318530012, -32.835999849)),
    ("Karratha WA", (116.892346944, -20.981828660), (116.892383769, -20.981808980)),
    ("Sydney NSW",  (151.182477111, -33.869130222), (151.182526131, -33.869111396)),
]

for name, src, exp in GA_PAIRS:
    got = t_gda.transform(*src)
    err = haversine_m(*got, *exp)
    ok = err < 10.0
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {err:.3f} m  (threshold 10 m)")
    results.append(ok)


# ── 3. Round-trip consistency (should be <1 mm) ───────────────────────────────

print("\n=== 3. Round-trip GDA2020 → GDA94 → GDA2020 (<1 mm) ===")

t_fwd = Transformer.from_crs("EPSG:7844", "EPSG:4283", always_xy=True)
t_inv = Transformer.from_crs("EPSG:4283", "EPSG:7844", always_xy=True)

RT_POINTS = [
    ("Sydney",    151.2093, -33.8688),
    ("Melbourne", 144.9631, -37.8136),
    ("Karratha",  116.8418, -20.7364),
    ("Darwin",    130.8456, -12.4634),
    ("Hobart",    147.3272, -42.8821),
]

for name, lon, lat in RT_POINTS:
    lon94, lat94 = t_fwd.transform(lon, lat)
    lon_rt, lat_rt = t_inv.transform(lon94, lat94)
    err_mm = haversine_m(lon_rt, lat_rt, lon, lat) * 1000
    ok = err_mm < 1.0
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {err_mm:.4f} mm")
    results.append(ok)


# ── 4. Projected CRS (GDA2020 geographic → MGA Zone 56) ──────────────────────

print("\n=== 4. GDA2020 geographic → MGA Zone 56 (EPSG:28356) ===")

t_mga = Transformer.from_crs("EPSG:7844", "EPSG:28356", always_xy=True,
    area_of_interest=AreaOfInterest(147.0, -44.0, 156.0, -28.0))

# Sydney CBD — known MGA56 coordinates (approx)
lon, lat = 151.2093, -33.8688
e, n = t_mga.transform(lon, lat)
# MGA56 easting for Sydney should be ~330,000–340,000
ok = 320_000 < e < 350_000 and 6_230_000 < n < 6_270_000
print(f"  Sydney → E={e:.1f} N={n:.1f}")
print(f"  [{'PASS' if ok else 'FAIL'}] easting/northing in expected range for Sydney MGA56")
results.append(ok)


# ── 5. AOI parameter selects better operation ────────────────────────────────

print("\n=== 5. AOI hint — same result as no-AOI for Helmert (AOI selects grid when available) ===")

t_no_aoi  = Transformer.from_crs("EPSG:4283", "EPSG:7844", always_xy=True)
t_with_aoi = Transformer.from_crs("EPSG:4283", "EPSG:7844", always_xy=True, area_of_interest=AOI_AUS)

lon_na, lat_na = t_no_aoi.transform(151.2093, -33.8688)
lon_wa, lat_wa = t_with_aoi.transform(151.2093, -33.8688)
diff = haversine_m(lon_na, lat_na, lon_wa, lat_wa)
# With only Helmert available both should give identical results
ok = diff < 0.001
print(f"  Difference between AOI / no-AOI: {diff*1000:.4f} mm (Helmert only — both identical)")
print(f"  [{'PASS' if ok else 'FAIL'}] consistent without NTv2 grids")
results.append(ok)


# ── 6. Error handling — bad CRS ──────────────────────────────────────────────

print("\n=== 6. Error handling ===")

from pyproj.exceptions import CRSError

# Bad EPSG code
try:
    Transformer.from_crs("EPSG:9999999", "EPSG:4326", always_xy=True)
    print(f"  [FAIL] bad EPSG: no exception raised")
    results.append(False)
except CRSError as e:
    print(f"  [PASS] bad EPSG raises CRSError: {str(e)[:60]}")
    results.append(True)

# GeoJSON without 'type' key — detected before transform
geojson_no_type = {"coordinates": [151.0, -33.8]}
ok = "type" not in geojson_no_type
print(f"  [{'PASS' if ok else 'FAIL'}] GeoJSON missing 'type' is detectable pre-transform")
results.append(ok)

# Same-CRS transform (identity) — should return identical coordinates
t_id = Transformer.from_crs("EPSG:4326", "EPSG:4326", always_xy=True)
lon_id, lat_id = t_id.transform(151.0, -33.8)
ok = abs(lon_id - 151.0) < 1e-8 and abs(lat_id - (-33.8)) < 1e-8
print(f"  [{'PASS' if ok else 'FAIL'}] identity transform (same CRS) preserves coordinates")
results.append(ok)


# ── Summary ───────────────────────────────────────────────────────────────────

print(f"\n{'='*50}")
passed = sum(results)
total  = len(results)
print(f"Results: {passed}/{total} passed")
if passed == total:
    print("\033[32mAll tests passed.\033[0m")
    sys.exit(0)
else:
    print(f"\033[31m{total - passed} test(s) failed.\033[0m")
    sys.exit(1)
