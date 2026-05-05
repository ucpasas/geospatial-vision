---
tags: [concept, copc, lidar, pointcloud, cloud]
created: 2026-04-22
updated: 2026-05-04
status: active
type: concept
related: [[pdal]], [[pipeline-system]], [[cog]]
---

# COPC — Cloud-Optimised Point Cloud

A LAZ file with a spatial index VLR (Variable Length Record) that enables HTTP range requests to fetch any spatial region without downloading the full file. The point cloud equivalent of [[cog]].

---

## Key Properties

- **Format:** LAZ (compressed LAS) with an additional spatial index VLR
- **All returns:** preserves all point returns, classifications, intensities
- **Single file:** HTTP range-request friendly; TiTiler and QGIS can stream it directly
- **VLR header:** `copc=true` in metadata confirms spatial index is present

---

## Creating COPC (in [[pipeline-system]])

```json
{
  "pipeline": [
    { "type": "readers.las", "filename": "<input.laz>", "override_srs": "<wkt>" },
    { "type": "writers.copc", "filename": "<stem>.copc.laz" }
  ]
}
```

`writers.copc` in [[pdal]] reindexes all points into the COPC spatial hierarchy. No filtering — all returns preserved.

---

## Validation (Phase 3)

Check `copc=true` in pipeline metadata after writing:

```python
meta = json.loads(pipeline.metadata)
copc_valid = meta["metadata"]["writers.copc"][0].get("copc", False)
```

---

## Output Naming

```
{stem}.copc.laz
```

---

## writers.copc Limitations

### Not Streaming-Compatible

`writers.copc` is **not a streaming stage**. It must hold the entire octree in memory to compute the spatial hierarchy before writing. Attempting to use it with `execute_streaming()` raises:

```
Attempting to use stream mode with a non-streamable stage.
```

This is a PDAL architectural constraint — the COPC spatial index (the VLR) must reference byte offsets for every node in the tree, which cannot be determined until all points are processed.

### Memory Ceiling

| Dataset | Points | RAM Required (approx) |
|---|---|---|
| Single USGS tile | ~19M | ~700 MB |
| 10 Melbourne tiles | ~100M | ~3.6 GB |
| Full Melbourne dataset (215 tiles) | ~300M | ~20–30 GB |

The ~36 bytes/point estimate includes point data, octree node metadata, and PDAL internal buffers. WSL2 with 11 GB RAM + 4 GB swap cannot hold the full Melbourne dataset — attempting the merge causes OOM.

### LAZ merge → COPC is no better

Merging tiles into a single LAZ first, then converting that LAZ to COPC, does not help — the COPC conversion still requires the same in-memory octree. The sequence `LAZ merge → COPC` avoids the merge OOM (LAZ writers are streaming), but the final COPC conversion hits the same ceiling.

### Purpose-built Alternative: untwine ✅ Installed & Used

`untwine` is a purpose-built COPC indexer that works on-disk rather than in-RAM. It streams points into a tile structure, builds the octree incrementally, and handles datasets that would OOM with `writers.copc`.

**Install (lidar conda env):**
```bash
conda install -c conda-forge untwine
```

**Usage:**
```bash
untwine --input <input.las_or_dir> --output <output.copc.laz>
```

**Confirmed on Melbourne 2018:** 353,634,995 points from a 4 GB source LAS zip — processed without RAM overflow on WSL2 (11 GB). Output: `Melbourne_2018.laz.copc` (`.laz.copc` extension, note: differs from PDAL convention).

---

## Preprocessing Trade-offs

COPC creation is a **separate, expensive preprocessing step** — not a write-through.

| Approach | RAM | Streaming | Notes |
|---|---|---|---|
| `writers.copc` (single tile) | ~700 MB | ✗ | Fine for single tiles, impractical at scale |
| `writers.copc` (directory merge) | ~20–30 GB | ✗ | OOM on 11 GB WSL2 for 215-tile dataset |
| `untwine` | Disk-bounded | ✓ | ✅ Installed via conda-forge; used for Melbourne 2018 (353M pts) |
| Raw LAZ + sidecar index | Minimal | ✓ | Research item — no file modification, proxy serves range requests |

**Implication for [[pipeline-system]]:** The pipeline produces COPC only for single-file input or small batches that fit in RAM. For the Melbourne dataset (215 tiles), `--mode laz` produces a merged LAZ; COPC conversion runs separately via `untwine`. This is now the confirmed workflow — `untwine` is installed in the `lidar` conda env and has been validated on the full Melbourne dataset.

**Urban vs. rural data compounds the issue.** Urban datasets (all Class 0) must run SMRF per tile before COPC can be built from ground-classified data. That is two full passes through the data — SMRF consumes RAM per tile and COPC construction consumes RAM for the merge. The per-tile sequential DTM strategy in [[pipeline-system]] addresses the SMRF constraint but leaves the COPC merge constraint unsolved.
