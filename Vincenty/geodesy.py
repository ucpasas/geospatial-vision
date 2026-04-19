"""
geodesy.py — Vincenty (1975) direct and inverse on the GRS80 ellipsoid,
with validation against PROJ 9 (pyproj) and Karney (geographiclib).

GRS80 ellipsoid parameters
---------------------------
Semi-major axis      a = 6 378 137.0 m          (exact, by definition)
Inverse flattening   1/f = 298.257 223 563       (exact, by definition)
Semi-minor axis      b = a(1 − f) ≈ 6 356 752.314 140 m
First eccentricity²  e² = 2f − f²

These are the parameters used by GDA94, GDA2020, and ETRS89. They differ
from WGS84 only in the inverse-flattening digit beyond the 9th decimal place —
for practical geodesy they are interchangeable.

Vincenty vs Karney — when each is appropriate
----------------------------------------------
Vincenty (1975) is an iterative method that solves the geodetic inverse and
direct problems to sub-millimetre accuracy for the vast majority of inputs.
Its λ-iteration converges when the angular separation between points is well
away from 180°.  The algorithm fails — oscillates without converging — for
near-antipodal inputs, specifically when both of the following hold:

    1.  The angular separation approaches 180° (cos²α → 0).
    2.  The two points lie close to the equator (sinU₁ · sinU₂ → 0).

The exact failure boundary is not a single threshold; it is a region in
(Δlat, Δlon) space where the number of iterations required grows without
bound.  Empirically, inputs with Δlon > 179.9° and |lat| < 1° can require
thousands of iterations before the method gives up, and the converged result
(if any) may carry multi-metre error.

Karney (2013) — implemented in the geographiclib library and used internally
by PROJ 9 — solves the same problems using a series expansion in the third
flattening n = (a−b)/(a+b).  It converges for all inputs including exact
antipodal points, is accurate to a few nanometres, and handles the equatorial
and near-equatorial degenerate cases correctly.  PROJ 9's pyproj.Geod.inv()
and .fwd() call Karney's C++ implementation via libproj, so pyproj results
are taken as ground truth throughout this module.

References
----------
Vincenty, T. (1975). Direct and inverse solutions of geodesics on the
    ellipsoid with application of nested equations. Survey Review, 23(176),
    88–93.  https://doi.org/10.1179/sre.1975.23.176.88

Karney, C. F. F. (2013). Algorithms for geodesics. Journal of Geodesy,
    87(1), 43–55.  https://doi.org/10.1007/s00190-012-0578-z

PROJ contributors (2024). PROJ coordinate transformation software library.
    https://proj.org
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import NamedTuple

# ---------------------------------------------------------------------------
# GRS80 ellipsoid constants
# ---------------------------------------------------------------------------

_A: float = 6_378_137.0                  # semi-major axis, metres
_F: float = 1.0 / 298.257_223_563        # flattening
_B: float = _A * (1.0 - _F)             # semi-minor axis, metres

# Vincenty iteration controls
_MAX_ITER: int = 1_000
_CONVERGENCE_THRESHOLD: float = 1e-12   # radians; ~0.006 mm on Earth surface


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ConvergenceError(RuntimeError):
    """Raised when Vincenty's λ-iteration does not converge.

    This occurs for near-antipodal inputs where the angular separation
    between the two points approaches 180°.  See the module docstring for
    a full explanation.  Use ``vincenty_inverse_karney`` (geographiclib) or
    ``pyproj.Geod.inv`` for inputs that may be near-antipodal.
    """


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


class InverseResult(NamedTuple):
    """Result of a geodetic inverse computation.

    Attributes
    ----------
    distance_m:
        Ellipsoidal distance between the two points, in metres.
    azimuth12_deg:
        Forward azimuth from point 1 to point 2, clockwise from north,
        in decimal degrees in the range [0, 360).
    azimuth21_deg:
        Back azimuth from point 2 to point 1, clockwise from north,
        in decimal degrees in the range [0, 360).
    iterations:
        Number of λ-iterations required for convergence.  Values close to
        ``_MAX_ITER`` indicate a near-antipodal input.
    """

    distance_m: float
    azimuth12_deg: float
    azimuth21_deg: float
    iterations: int


class DirectResult(NamedTuple):
    """Result of a geodetic direct computation.

    Attributes
    ----------
    lat2_deg:
        Latitude of the destination point, in decimal degrees.
        Positive north, negative south.
    lon2_deg:
        Longitude of the destination point, in decimal degrees.
        Positive east, negative west.
    azimuth21_deg:
        Back azimuth from the destination back to the start point,
        clockwise from north, in decimal degrees in the range [0, 360).
    iterations:
        Number of λ-iterations required for convergence.
    """

    lat2_deg: float
    lon2_deg: float
    azimuth21_deg: float
    iterations: int


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalise_azimuth(az_rad: float) -> float:
    """Return azimuth in degrees, normalised to [0, 360)."""
    deg = math.degrees(az_rad) % 360.0
    return deg if deg >= 0.0 else deg + 360.0


# ---------------------------------------------------------------------------
# Vincenty inverse
# ---------------------------------------------------------------------------


def vincenty_inverse(
    lat1_deg: float,
    lon1_deg: float,
    lat2_deg: float,
    lon2_deg: float,
) -> InverseResult:
    """Compute the geodetic inverse problem on the GRS80 ellipsoid (Vincenty 1975).

    Given two points on the ellipsoid, return the ellipsoidal distance and
    the forward and back azimuths.  Accurate to better than 0.1 mm for
    non-antipodal inputs.

    Parameters
    ----------
    lat1_deg:
        Latitude of point 1, decimal degrees.  Positive north.
    lon1_deg:
        Longitude of point 1, decimal degrees.  Positive east.
    lat2_deg:
        Latitude of point 2, decimal degrees.  Positive north.
    lon2_deg:
        Longitude of point 2, decimal degrees.  Positive east.

    Returns
    -------
    InverseResult
        Named tuple with ``distance_m``, ``azimuth12_deg``,
        ``azimuth21_deg``, and ``iterations``.

    Raises
    ------
    ConvergenceError
        If the λ-iteration does not converge within ``_MAX_ITER`` steps.
        This typically indicates a near-antipodal input (angular separation
        close to 180°).  Switch to ``vincenty_inverse_karney`` or
        ``pyproj.Geod.inv`` for such inputs.

    Example
    -------
    >>> r = vincenty_inverse(-37.8136, 144.9631, -33.8688, 151.2093)
    >>> round(r.distance_m, 3)
    714109.078
    >>> round(r.azimuth12_deg, 6)
    49.176788
    """
    # Convert inputs to radians
    lat1 = math.radians(lat1_deg)
    lon1 = math.radians(lon1_deg)
    lat2 = math.radians(lat2_deg)
    lon2 = math.radians(lon2_deg)

    # Reduced latitudes (latitude on the auxiliary sphere)
    U1 = math.atan((1.0 - _F) * math.tan(lat1))
    U2 = math.atan((1.0 - _F) * math.tan(lat2))

    sinU1, cosU1 = math.sin(U1), math.cos(U1)
    sinU2, cosU2 = math.sin(U2), math.cos(U2)

    L = lon2 - lon1          # difference in longitude on the ellipsoid
    lam = L                  # initial approximation for λ (longitude on sphere)

    for iteration in range(1, _MAX_ITER + 1):
        sin_lam = math.sin(lam)
        cos_lam = math.cos(lam)

        sin_sigma = math.hypot(
            cosU2 * sin_lam,
            cosU1 * sinU2 - sinU1 * cosU2 * cos_lam,
        )
        cos_sigma = sinU1 * sinU2 + cosU1 * cosU2 * cos_lam

        # Coincident points
        if sin_sigma == 0.0:
            return InverseResult(0.0, 0.0, 0.0, iteration)

        sigma = math.atan2(sin_sigma, cos_sigma)

        sin_alpha = cosU1 * cosU2 * sin_lam / sin_sigma
        cos2_alpha = 1.0 - sin_alpha ** 2

        # cos(2σm): equatorial line has cos²α = 0 → set cos2_sigma_m = 0
        cos2_sigma_m = (
            cos_sigma - 2.0 * sinU1 * sinU2 / cos2_alpha
            if cos2_alpha != 0.0
            else 0.0
        )

        C = _F / 16.0 * cos2_alpha * (4.0 + _F * (4.0 - 3.0 * cos2_alpha))

        lam_prev = lam
        lam = L + (1.0 - C) * _F * sin_alpha * (
            sigma
            + C
            * sin_sigma
            * (cos2_sigma_m + C * cos_sigma * (-1.0 + 2.0 * cos2_sigma_m ** 2))
        )

        if abs(lam - lam_prev) <= _CONVERGENCE_THRESHOLD:
            break
    else:
        raise ConvergenceError(
            f"Vincenty inverse did not converge after {_MAX_ITER} iterations. "
            f"Input is likely near-antipodal: "
            f"({lat1_deg}°, {lon1_deg}°) → ({lat2_deg}°, {lon2_deg}°). "
            f"Use vincenty_inverse_karney() or pyproj.Geod.inv() instead."
        )

    # Final distance and azimuths
    u2 = cos2_alpha * (_A ** 2 - _B ** 2) / _B ** 2
    A_coeff = 1.0 + u2 / 16384.0 * (4096.0 + u2 * (-768.0 + u2 * (320.0 - 175.0 * u2)))
    B_coeff = u2 / 1024.0 * (256.0 + u2 * (-128.0 + u2 * (74.0 - 47.0 * u2)))

    delta_sigma = B_coeff * sin_sigma * (
        cos2_sigma_m
        + B_coeff
        / 4.0
        * (
            cos_sigma * (-1.0 + 2.0 * cos2_sigma_m ** 2)
            - B_coeff
            / 6.0
            * cos2_sigma_m
            * (-3.0 + 4.0 * sin_sigma ** 2)
            * (-3.0 + 4.0 * cos2_sigma_m ** 2)
        )
    )

    distance = _B * A_coeff * (sigma - delta_sigma)

    az12 = math.atan2(cosU2 * sin_lam, cosU1 * sinU2 - sinU1 * cosU2 * cos_lam)
    az21 = math.atan2(cosU1 * sin_lam, -sinU1 * cosU2 + cosU1 * sinU2 * cos_lam)

    return InverseResult(
        distance_m=distance,
        azimuth12_deg=_normalise_azimuth(az12),
        azimuth21_deg=_normalise_azimuth(az21),
        iterations=iteration,
    )


# ---------------------------------------------------------------------------
# Vincenty direct
# ---------------------------------------------------------------------------


def vincenty_direct(
    lat1_deg: float,
    lon1_deg: float,
    azimuth12_deg: float,
    distance_m: float,
) -> DirectResult:
    """Compute the geodetic direct problem on the GRS80 ellipsoid (Vincenty 1975).

    Given a start point, forward azimuth, and distance, return the
    destination coordinates and the back azimuth.

    Parameters
    ----------
    lat1_deg:
        Latitude of the start point, decimal degrees.  Positive north.
    lon1_deg:
        Longitude of the start point, decimal degrees.  Positive east.
    azimuth12_deg:
        Forward azimuth from start to destination, clockwise from north,
        decimal degrees.
    distance_m:
        Ellipsoidal distance to travel, in metres.  Must be non-negative.

    Returns
    -------
    DirectResult
        Named tuple with ``lat2_deg``, ``lon2_deg``, ``azimuth21_deg``,
        and ``iterations``.

    Raises
    ------
    ConvergenceError
        If the iteration does not converge.  This is rare for the direct
        problem but can occur for very long lines crossing near-antipodal
        geometry.
    ValueError
        If ``distance_m`` is negative.

    Example
    -------
    >>> r = vincenty_direct(-37.8136, 144.9631, 49.176788, 714109.078)
    >>> round(r.lat2_deg, 4)
    -33.8688
    >>> round(r.lon2_deg, 4)
    151.2093
    """
    if distance_m < 0.0:
        raise ValueError(f"distance_m must be non-negative, got {distance_m}")

    lat1 = math.radians(lat1_deg)
    lon1 = math.radians(lon1_deg)
    az12 = math.radians(azimuth12_deg)

    sin_az12, cos_az12 = math.sin(az12), math.cos(az12)

    U1 = math.atan((1.0 - _F) * math.tan(lat1))
    sinU1, cosU1 = math.sin(U1), math.cos(U1)

    sigma1 = math.atan2(sinU1, cos_az12 * cosU1)
    sin_alpha = cosU1 * sin_az12
    cos2_alpha = 1.0 - sin_alpha ** 2

    u2 = cos2_alpha * (_A ** 2 - _B ** 2) / _B ** 2
    A_coeff = 1.0 + u2 / 16384.0 * (4096.0 + u2 * (-768.0 + u2 * (320.0 - 175.0 * u2)))
    B_coeff = u2 / 1024.0 * (256.0 + u2 * (-128.0 + u2 * (74.0 - 47.0 * u2)))

    sigma = distance_m / (_B * A_coeff)   # initial approximation

    for iteration in range(1, _MAX_ITER + 1):
        cos2_sigma_m = math.cos(2.0 * sigma1 + sigma)
        sin_sigma = math.sin(sigma)
        cos_sigma = math.cos(sigma)

        delta_sigma = B_coeff * sin_sigma * (
            cos2_sigma_m
            + B_coeff
            / 4.0
            * (
                cos_sigma * (-1.0 + 2.0 * cos2_sigma_m ** 2)
                - B_coeff
                / 6.0
                * cos2_sigma_m
                * (-3.0 + 4.0 * sin_sigma ** 2)
                * (-3.0 + 4.0 * cos2_sigma_m ** 2)
            )
        )

        sigma_new = distance_m / (_B * A_coeff) + delta_sigma

        if abs(sigma_new - sigma) <= _CONVERGENCE_THRESHOLD:
            sigma = sigma_new
            break
        sigma = sigma_new
    else:
        raise ConvergenceError(
            f"Vincenty direct did not converge after {_MAX_ITER} iterations."
        )

    # Recompute final trig values with converged σ
    cos2_sigma_m = math.cos(2.0 * sigma1 + sigma)
    sin_sigma = math.sin(sigma)
    cos_sigma = math.cos(sigma)

    lat2 = math.atan2(
        sinU1 * cos_sigma + cosU1 * sin_sigma * cos_az12,
        (1.0 - _F)
        * math.hypot(
            sin_alpha,
            sinU1 * sin_sigma - cosU1 * cos_sigma * cos_az12,
        ),
    )

    lam = math.atan2(
        sin_sigma * sin_az12,
        cosU1 * cos_sigma - sinU1 * sin_sigma * cos_az12,
    )

    C = _F / 16.0 * cos2_alpha * (4.0 + _F * (4.0 - 3.0 * cos2_alpha))

    L = lam - (1.0 - C) * _F * sin_alpha * (
        sigma
        + C
        * sin_sigma
        * (cos2_sigma_m + C * cos_sigma * (-1.0 + 2.0 * cos2_sigma_m ** 2))
    )

    lon2 = lon1 + L

    az21 = math.atan2(
        sin_alpha,
        -sinU1 * sin_sigma + cosU1 * cos_sigma * cos_az12,
    )

    return DirectResult(
        lat2_deg=math.degrees(lat2),
        lon2_deg=math.degrees(lon2),
        azimuth21_deg=_normalise_azimuth(az21),
        iterations=iteration,
    )


# ---------------------------------------------------------------------------
# Karney / geographiclib wrapper (optional dependency)
# ---------------------------------------------------------------------------


def vincenty_inverse_karney(
    lat1_deg: float,
    lon1_deg: float,
    lat2_deg: float,
    lon2_deg: float,
) -> InverseResult:
    """Compute geodetic inverse using Karney's algorithm (geographiclib).

    Wraps ``geographiclib.geodesic.Geodesic`` with GRS80 parameters.
    Accurate to ~5 nanometres for all inputs including near-antipodal cases
    where Vincenty fails.  PROJ 9 uses this algorithm internally.

    Parameters
    ----------
    lat1_deg, lon1_deg:
        Coordinates of point 1, decimal degrees.
    lat2_deg, lon2_deg:
        Coordinates of point 2, decimal degrees.

    Returns
    -------
    InverseResult
        Same structure as ``vincenty_inverse``.  ``iterations`` is always
        0 (Karney uses a series expansion, not an iterative loop).

    Raises
    ------
    ImportError
        If geographiclib is not installed.  Install with:
        ``pip install geographiclib``

    Example
    -------
    >>> r = vincenty_inverse_karney(-37.8136, 144.9631, -33.8688, 151.2093)
    >>> round(r.distance_m, 3)
    714109.078
    """
    try:
        from geographiclib.geodesic import Geodesic
    except ImportError as exc:
        raise ImportError(
            "geographiclib is required for vincenty_inverse_karney(). "
            "Install it with: pip install geographiclib"
        ) from exc

    geod = Geodesic(_A, _F)
    result = geod.Inverse(lat1_deg, lon1_deg, lat2_deg, lon2_deg)

    az12 = result["azi1"] % 360.0
    az21 = result["azi2"] % 360.0

    return InverseResult(
        distance_m=result["s12"],
        azimuth12_deg=az12 if az12 >= 0.0 else az12 + 360.0,
        azimuth21_deg=az21 if az21 >= 0.0 else az21 + 360.0,
        iterations=0,
    )


# ---------------------------------------------------------------------------
# Validation suite
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """One row in the validation report."""

    label: str
    vincenty_dist: float | str       # str when ConvergenceError
    karney_dist: float | None
    proj_dist: float | None
    residual_vincenty_m: float | str
    residual_karney_m: float | None
    vincenty_iterations: int | str = 0


def run_validation(verbose: bool = True) -> list[ValidationResult]:
    """Run the full validation suite and return results.

    Tests include:
    - Melbourne → Sydney (standard case, ~714 km)
    - Round-trip consistency (inverse → direct → inverse)
    - Near-antipodal cases at increasing severity

    Parameters
    ----------
    verbose:
        If True, print a formatted report to stdout.

    Returns
    -------
    list[ValidationResult]
        One entry per test case.
    """
    test_cases = [
        ("Melbourne → Sydney",        -37.8136, 144.9631, -33.8688, 151.2093),
        ("Sydney → Perth",            -33.8688, 151.2093, -31.9505, 115.8605),
        ("Near-antipodal mild",         0.5,     0.0,      -0.5,    179.5),
        ("Near-antipodal moderate",     0.1,     0.0,      -0.1,    179.9),
        ("Near-antipodal severe",       0.01,    0.0,      -0.01,   179.99),
        ("Near-antipodal extreme",      0.001,   0.0,      -0.001,  179.999),
    ]

    # Optional dependencies
    try:
        from pyproj import Geod as _Geod
        _proj_geod = _Geod(ellps="GRS80")
    except ImportError:
        _proj_geod = None

    try:
        from geographiclib.geodesic import Geodesic as _Geodesic
        _karney_geod = _Geodesic(_A, _F)
    except ImportError:
        _karney_geod = None

    results: list[ValidationResult] = []

    for label, lat1, lon1, lat2, lon2 in test_cases:
        # Vincenty
        try:
            vr = vincenty_inverse(lat1, lon1, lat2, lon2)
            v_dist: float | str = vr.distance_m
            v_iter: int | str = vr.iterations
        except ConvergenceError as exc:
            v_dist = f"ConvergenceError"
            v_iter = f">{_MAX_ITER}"

        # PROJ reference
        if _proj_geod is not None:
            _, _, p_dist = _proj_geod.inv(lon1, lat1, lon2, lat2)
        else:
            p_dist = None

        # Karney
        if _karney_geod is not None:
            k_res = _karney_geod.Inverse(lat1, lon1, lat2, lon2)
            k_dist: float | None = k_res["s12"]
        else:
            k_dist = None

        # Residuals
        if isinstance(v_dist, float) and p_dist is not None:
            res_v: float | str = abs(v_dist - p_dist)
        elif isinstance(v_dist, str):
            res_v = v_dist
        else:
            res_v = "n/a"

        res_k = abs(k_dist - p_dist) if (k_dist is not None and p_dist is not None) else None

        results.append(ValidationResult(
            label=label,
            vincenty_dist=v_dist,
            karney_dist=k_dist,
            proj_dist=p_dist,
            residual_vincenty_m=res_v,
            residual_karney_m=res_k,
            vincenty_iterations=v_iter,
        ))

    if verbose:
        _print_report(results)

    return results


def _print_report(results: list[ValidationResult]) -> None:
    """Print a human-readable validation table."""
    W = 80
    print("=" * W)
    print("geodesy.py — validation report")
    print(f"GRS80  a={_A} m   1/f={1/_F:.9f}")
    print(f"Convergence threshold: {_CONVERGENCE_THRESHOLD:.0e} rad")
    print("=" * W)

    for r in results:
        print(f"\n  {r.label}")
        print(f"    PROJ 9 distance   : {r.proj_dist:.4f} m" if r.proj_dist else
              "    PROJ 9            : not available (pyproj not installed)")

        if isinstance(r.vincenty_dist, float):
            print(f"    Vincenty distance : {r.vincenty_dist:.4f} m  ({r.vincenty_iterations} iters)")
        else:
            print(f"    Vincenty          : {r.vincenty_dist}  ({r.vincenty_iterations} iters)")

        if r.karney_dist is not None:
            print(f"    Karney distance   : {r.karney_dist:.4f} m")

        if isinstance(r.residual_vincenty_m, float):
            flag = "  OK" if r.residual_vincenty_m < 1e-4 else "  FAIL (> 0.1 mm)"
            print(f"    |Vincenty − PROJ| : {r.residual_vincenty_m:.6e} m{flag}")
        else:
            print(f"    |Vincenty − PROJ| : {r.residual_vincenty_m}")

        if r.residual_karney_m is not None:
            print(f"    |Karney − PROJ|   : {r.residual_karney_m:.6e} m")

    print("\n" + "=" * W)

    # Round-trip test
    print("\nRound-trip test: Melbourne → Sydney (inverse → direct → inverse)")
    try:
        r1 = vincenty_inverse(-37.8136, 144.9631, -33.8688, 151.2093)
        d1 = vincenty_direct(-37.8136, 144.9631, r1.azimuth12_deg, r1.distance_m)
        r2 = vincenty_inverse(-37.8136, 144.9631, d1.lat2_deg, d1.lon2_deg)
        residual = abs(r1.distance_m - r2.distance_m)
        print(f"  Inverse dist:     {r1.distance_m:.6f} m")
        print(f"  Recovered lat2:   {d1.lat2_deg:.8f}° (expected -33.86880000°)")
        print(f"  Recovered lon2:   {d1.lon2_deg:.8f}° (expected 151.20930000°)")
        print(f"  Round-trip Δdist: {residual:.6e} m  {'OK' if residual < 1e-4 else 'FAIL'}")
    except ConvergenceError as exc:
        print(f"  ConvergenceError: {exc}")

    print("=" * W)


# ---------------------------------------------------------------------------
# Module entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    run_validation(verbose=True)
