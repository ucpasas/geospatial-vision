"""
pipeline/validate.py
====================
Phase 3 — Validation stage.

Three checks per tile:
  1. Point count > 0
  2. Density >= threshold (points per square metre)
  3. COPC VLR present in output file

Returns a ValidationResult dataclass so run_pipeline.py
can consume results cleanly and pass them to the CSV logger in Phase 4.
"""

import json
from dataclasses import dataclass

import pdal

DENSITY_THRESHOLD = 4.0  # points per square metre


@dataclass
class ValidationResult:
    point_count_valid: bool
    density_ppsm: float
    density_valid: bool
    copc_valid: bool

    @property
    def passed(self) -> bool:
        return self.point_count_valid and self.density_valid and self.copc_valid

    def report(self):
        status = "PASS" if self.passed else "FAIL"
        print(f"  [{'OK' if self.point_count_valid else 'FAIL'}] Point count > 0")
        print(f"  [{'OK' if self.density_valid else 'FAIL'}] Density: "
              f"{self.density_ppsm:.2f} ppsm  (threshold: {DENSITY_THRESHOLD})")
        print(f"  [{'OK' if self.copc_valid else 'FAIL'}] COPC VLR present")
        print(f"  [{status}] Overall")


def check_point_count(point_count: int) -> bool:
    return point_count > 0


def check_density(point_count: int, bounds: dict) -> float:
    """
    Calculate density as ground points per square metre.
    Area is derived from the pipeline bounds (minx/maxx/miny/maxy from readers.las metadata).
    """
    area = (bounds["maxx"] - bounds["minx"]) * (bounds["maxy"] - bounds["miny"])
    if area <= 0:
        raise RuntimeError(f"Invalid bounds for density calculation: {bounds}")
    return point_count / area


def check_copc_vlr(copc_path: str) -> bool:
    """
    Read the COPC output via readers.copc (not readers.las).
    readers.copc fails hard if the VLR is missing or malformed —
    a clean execute() confirms the file is a valid COPC.
    """
    pipeline_json = json.dumps({
        "pipeline": [
            {
                "type": "readers.copc",
                "filename": copc_path
            }
        ]
    })
    try:
        pipeline = pdal.Pipeline(pipeline_json)
        pipeline.execute()
        raw = pipeline.metadata
        meta = raw if isinstance(raw, dict) else json.loads(raw)

        # Walk metadata stages looking for the copc reader entry
        for key, val in meta.get("metadata", {}).items():
            if "copc" not in key:
                continue
            entry = val if isinstance(val, dict) else (val[0] if val else None)
            if entry and entry.get("copc", False):
                return True

        # readers.copc executed cleanly — VLR is present even if
        # metadata key structure differs across PDAL versions
        return True

    except Exception:
        return False


def validate(
    point_count: int,
    bounds: dict,
    copc_path: str,
) -> ValidationResult:
    """
    Run all three validation checks and return a ValidationResult.
    Designed to be called from run_pipeline.py after both pipelines complete.
    """
    count_valid = check_point_count(point_count)

    try:
        density = check_density(point_count, bounds)
    except RuntimeError as e:
        print(f"  [FAIL] Density check error: {e}")
        density = 0.0

    density_valid = density >= DENSITY_THRESHOLD
    copc_valid    = check_copc_vlr(copc_path)

    return ValidationResult(
        point_count_valid=count_valid,
        density_ppsm=density,
        density_valid=density_valid,
        copc_valid=copc_valid,
    )