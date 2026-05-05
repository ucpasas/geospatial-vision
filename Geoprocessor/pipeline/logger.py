"""
pipeline/logger.py
==================
CSV logger — one row per tile/pipeline, one file per run.

File naming: pipeline/output/logs/run_YYYYMMDD_HHMMSS.csv
A new file is created per run — no append. This prevents corruption
from external edits or schema changes between runs.
"""

import csv
import os
from datetime import datetime


COLUMNS = [
    "filename",
    "mode",
    "input_points",
    "output_points",
    "density_ppsm",
    "dtm_elapsed_s",
    "secondary_elapsed_s",
    "total_elapsed_s",
    "output_valid",
    "status",
]


def create_log_file(base_dir: str) -> str:
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path  = os.path.join(log_dir, f"run_{timestamp}.csv")

    with open(log_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()

    return log_path


def log_tile(
    log_path:            str,
    filename:            str,
    mode:                str,
    input_points:        int,
    output_points:       int,
    density_ppsm:        float | None,
    dtm_elapsed_s:       float,
    secondary_elapsed_s: float,
    output_valid:        bool,
    status:              str,
):
    total_elapsed = dtm_elapsed_s + secondary_elapsed_s

    with open(log_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writerow({
            "filename":            filename,
            "mode":                mode,
            "input_points":        input_points,
            "output_points":       output_points,
            "density_ppsm":        round(density_ppsm, 4) if density_ppsm is not None else "",
            "dtm_elapsed_s":       round(dtm_elapsed_s, 2),
            "secondary_elapsed_s": round(secondary_elapsed_s, 2),
            "total_elapsed_s":     round(total_elapsed, 2),
            "output_valid":        output_valid,
            "status":              status,
        })
