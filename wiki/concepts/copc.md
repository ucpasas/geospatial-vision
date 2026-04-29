---
tags: [concept, copc, lidar, pointcloud, cloud]
created: 2026-04-22
updated: 2026-04-22
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
