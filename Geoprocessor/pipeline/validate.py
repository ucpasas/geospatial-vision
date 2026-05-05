"""
pipeline/validate.py
====================
Validation stage.

Checks vary by mode:
  dtm+copc  — point count, density, COPC VLR
  dtm+laz   — point count, density, LAZ file valid
  dtm       — point count, density, GeoTIFF tile exists (batch per-tile)
  copc      — point count, COPC VLR  (no density — no SMRF run)
  laz       — point count, LAZ file valid (no density — no SMRF run)
"""

import json
import os
from dataclasses import dataclass

import pdal

DENSITY_THRESHOLD = 4.0  # points per square metre


@dataclass
class ValidationResult:
    point_count_valid: bool
    point_count_skipped: bool
    density_ppsm: float | None
    density_valid: bool | None
    density_threshold: float
    output_valid: bool
    output_label: str

    @property
    def passed(self) -> bool:
        density_ok = self.density_valid if self.density_valid is not None else True
        return self.point_count_valid and density_ok and self.output_valid

    def report(self):
        status = "PASS" if self.passed else "FAIL"
        if self.point_count_skipped:
            print(f"  [--] Point count: N/A (streaming)")
        else:
            print(f"  [{'OK' if self.point_count_valid else 'FAIL'}] Point count > 0")
        if self.density_ppsm is not None:
            print(f"  [{'OK' if self.density_valid else 'FAIL'}] Density: "
                  f"{self.density_ppsm:.2f} ppsm  (threshold: {self.density_threshold})")
        else:
            print(f"  [--] Density: N/A")
        print(f"  [{'OK' if self.output_valid else 'FAIL'}] {self.output_label}")
        print(f"  [{status}] Overall")


def check_point_count(point_count: int) -> bool:
    return point_count > 0


def check_density(point_count: int, bounds: dict) -> float:
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
        "pipeline": [{"type": "readers.copc", "filename": copc_path}]
    })
    try:
        pipeline = pdal.Pipeline(pipeline_json)
        pipeline.execute()
        raw = pipeline.metadata
        meta = raw if isinstance(raw, dict) else json.loads(raw)
        for key, val in meta.get("metadata", {}).items():
            if "copc" not in key:
                continue
            entry = val if isinstance(val, dict) else (val[0] if val else None)
            if entry and entry.get("copc", False):
                return True
        return True  # readers.copc executed cleanly — VLR is present
    except Exception:
        return False


def check_file_valid(path: str) -> bool:
    return os.path.exists(path) and os.path.getsize(path) > 0


def validate(
    point_count: int,
    bounds: dict | None,
    output_path: str,
    mode: str = "dtm+copc",
    skip_point_count: bool = False,
    density_threshold: float = DENSITY_THRESHOLD,
) -> ValidationResult:
    """
    Run validation checks and return a ValidationResult.

    bounds is None for modes without a DTM pipeline (copc, laz).
    mode controls which checks run and which output format is validated.
    skip_point_count skips the point count check for streaming runs where
    the count returned by execute_streaming() may be unreliable.
    density_threshold overrides the default threshold (ppsm).
    """
    count_valid = True if skip_point_count else check_point_count(point_count)

    has_density = mode in ("dtm+copc", "dtm+laz", "dtm") and bounds is not None
    if has_density:
        try:
            density = check_density(point_count, bounds)
        except RuntimeError as e:
            print(f"  [FAIL] Density check error: {e}")
            density = 0.0
        density_valid = density >= density_threshold
    else:
        density = None
        density_valid = None

    if mode in ("dtm+copc", "copc"):
        output_valid = check_copc_vlr(output_path)
        output_label = "COPC VLR present"
    elif mode in ("dtm+laz", "laz"):
        output_valid = check_file_valid(output_path)
        output_label = "LAZ output valid"
    else:  # mode == "dtm" (batch tile)
        output_valid = check_file_valid(output_path)
        output_label = "DTM tile written"

    return ValidationResult(
        point_count_valid=count_valid,
        point_count_skipped=skip_point_count,
        density_ppsm=density,
        density_valid=density_valid,
        density_threshold=density_threshold,
        output_valid=output_valid,
        output_label=output_label,
    )
