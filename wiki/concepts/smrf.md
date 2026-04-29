---
tags: [concept, smrf, lidar, ground-classification, pdal]
created: 2026-04-22
updated: 2026-04-22
status: active
type: concept
related: [[pdal]], [[pipeline-system]]
---

# SMRF — Simple Morphological Filter

Ground point classification algorithm for LiDAR data. Used in [[pipeline-system]] to identify ground returns before DTM generation.

---

## What It Does

SMRF analyses the point cloud morphology to identify ground points and stamps them with **Classification 2**. It does **not remove** any points — it only updates the Classification attribute. A subsequent `filters.range` step removes non-ground points.

---

## Parameters (tuned for Central Texas / USGS lidar)

| Parameter | Value | Effect |
|---|---|---|
| `slope` | 0.15 | Maximum slope between ground points (radians/metre) |
| `window` | 18.0 | Maximum window size for morphological opening (metres) |
| `threshold` | 0.5 | Height threshold above ground surface (metres) |
| `scalar` | 1.25 | Slope scalar — increases tolerance on steeper terrain |

---

## Pipeline Usage

```json
{ "type": "filters.smrf", "slope": 0.15, "window": 18.0, "threshold": 0.5, "scalar": 1.25 },
{ "type": "filters.range", "limits": "Classification[2:2]" }
```

After `filters.range`, point count drops to ~20–30% of input (ground-only).

---

## Notes

- Parameters should be exposed as CLI args in Phase 4 of [[pipeline-system]]
- Different terrain types (urban, forested, flat) may require parameter tuning
- USGS Central Texas dataset uses 0.5m native point spacing — 0.5m DTM resolution is appropriate
