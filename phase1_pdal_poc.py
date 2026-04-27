"""
Phase 1 — pdal Python Bindings Proof of Concept
================================================
Run this against a real .laz file to verify:
  1. import pdal works
  2. pdal.Pipeline(json).execute() runs without error
  3. Point count is readable from the pipeline
  4. Basic metadata (SRS, schema fields) is accessible

Usage:
    python phase1_pdal_poc.py /path/to/your/input.laz

Install requirements (conda recommended):
    conda install -c conda-forge pdal python-pdal
  or (if PDAL C++ libs already installed system-wide):
    pip install pdal
"""

import sys
import json
import time

# ── 1. Import check ──────────────────────────────────────────────────────────
try:
    import pdal
    print(f"[OK] import pdal  →  version {pdal.__version__}")
except ImportError as e:
    print(f"[FAIL] import pdal failed: {e}")
    print("       Install via:  conda install -c conda-forge pdal python-pdal")
    sys.exit(1)

# ── 2. Input file ────────────────────────────────────────────────────────────
if len(sys.argv) < 2:
    print("[FAIL] Provide a .laz path:  python phase1_pdal_poc.py input.laz")
    sys.exit(1)

input_path = sys.argv[1]
print(f"[..] Input: {input_path}")

# ── 3. Minimal reader pipeline (no write, no filter) ─────────────────────────
# This is the simplest possible pipeline — just read the file and count points.
# If this works, the bindings are functional.
pipeline_json = json.dumps({
    "pipeline": [
        {
            "type": "readers.las",
            "filename": input_path
        }
    ]
})

print("[..] Building pipeline ...")
t0 = time.time()

try:
    pipeline = pdal.Pipeline(pipeline_json)
    pipeline.execute()
    elapsed = time.time() - t0
    print(f"[OK] pipeline.execute() completed in {elapsed:.2f}s")
except Exception as e:
    print(f"[FAIL] pipeline.execute() raised: {e}")
    sys.exit(1)

# ── 4. Point count ───────────────────────────────────────────────────────────
try:
    arrays = pipeline.arrays
    total_points = sum(len(a) for a in arrays)
    print(f"[OK] Total points read: {total_points:,}")
    if total_points == 0:
        print("[WARN] Point count is 0 — check the file path or format.")
except Exception as e:
    print(f"[FAIL] Could not read arrays: {e}")
    sys.exit(1)

# ── 5. Metadata ──────────────────────────────────────────────────────────────
try:
    metadata = pipeline.metadata
    meta = json.loads(metadata)

    # Pull the first stage's metadata (the reader)
    stages = meta.get("metadata", {})
    # metadata is keyed by stage type — find the reader entry
    reader_meta = None
    for key, val in stages.items():
        if "readers" in key:
            reader_meta = val if isinstance(val, dict) else (val[0] if val else None)
            break

    if reader_meta:
        srs = reader_meta.get("srs", {}).get("wkt", "(no SRS found)")
        compressed = reader_meta.get("compressed", "unknown")
        point_format = reader_meta.get("dataformat_id", "unknown")
        print(f"[OK] SRS (truncated):     {str(srs)[:80]} ...")
        print(f"[OK] Compressed:          {compressed}")
        print(f"[OK] LAS point format ID: {point_format}")
    else:
        print("[WARN] Could not find reader metadata key — raw keys:")
        print("       ", list(stages.keys())[:10])

except Exception as e:
    print(f"[WARN] Metadata read failed (non-fatal): {e}")

# ── 6. Schema / field names ──────────────────────────────────────────────────
try:
    schema = pipeline.schema
    fields = [f["name"] for f in schema.get("schema", {}).get("dimensions", [])]
    print(f"[OK] Dimensions ({len(fields)}): {fields}")
except Exception as e:
    print(f"[WARN] Schema read failed (non-fatal): {e}")

# ── 7. Summary ───────────────────────────────────────────────────────────────
print()
print("=" * 60)
print("Phase 1 result: PASS — bindings operational.")
print(f"  Points: {total_points:,}  |  Time: {elapsed:.2f}s")
print("=" * 60)
print()
print("Next: Phase 2 — execute COG DTM + COPC pipelines in sequence.")
