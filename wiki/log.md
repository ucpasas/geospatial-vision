---
type: log
created: 2026-04-22
updated: 2026-04-29
---

# Session Log

Append-only. One entry per session. Most recent at top.

---

## 2026-04-29 — Geo-Viz deck.gl viewer wiki page created

**Action:** Ingest  
**Summary:** Ingested `GEO_VIZ_CONTEXT.md` (all 3 viewer phases complete). Created `projects/geo-viz.md`. Updated `index.md` (added geo-viz row), `concepts/cog.md` (added browser-side COG reading section), and `WIKI_SCHEMA.md` (directory listing brought up to date with giro3d-viewer and r2-setup additions from prior sessions).

**Key facts:**
- Geo-Viz live at https://ucpasas.github.io/geospatial-vision/geo-viz/
- COG read directly in browser via geotiff.js range requests — no tile server required
- CRS derived at runtime from embedded geokeys via `geotiff-geokeys-to-proj4`
- 153k WGS84 points from 400×400 COG overview sample, rendered at 144 FPS
- deck.gl v9 gotchas captured: `Deck` not `DeckGL`; `deck.metrics` via RAF not `onAfterRender`; proj4 return format normalisation
- `@loaders.gl/las` in `package.json` but not yet wired up — reserved for future raw LiDAR scatter layer
- `SHOW_STATS` exported from `config.js` but unused — noted, left in place intentionally
- CI: geo-viz build added to shared `deploy.yml` workflow alongside giro3d-viewer

---

## 2026-04-27 — Giro3D viewer wiki page created; git history cleaned

**Action:** Ingest + fix  
**Summary:** Ingested `GIRO3D_CONTEXT.md` (all 4 viewer phases complete) and created `projects/giro3d-viewer.md`. Fixed GitHub push failure caused by large files in commits: `git reset --mixed 37bec07` rewound HEAD to the last clean push while keeping all files on disk. Root cause: `.gitignore` files were created after files were already committed. Post-reset git status confirmed large files (COPC, DTM TIF, COG TIF, Miniconda installer, `.venv`) suppressed by gitignores.

**Key facts:**
- Giro3D viewer live at https://ucpasas.github.io/geospatial-vision/giro3d-viewer/
- COPC + COG both confirmed on R2 and aligned spatially
- TiTiler on Render serving terrain tiles (placeholder — Cloudflare Worker planned)
- `git reset --mixed` is safe: moves HEAD only, working tree untouched
- Known issue: `MapboxTerrainFormat` vs raw elevation tiles mismatch — terrain values incorrect until Worker is built

---

## 2026-04-26 — R2 setup documented; COG DTM built; ui.js bugs fixed

**Action:** Update + Ingest  
**Summary:** Reconstructed R2/Cloudflare setup from `~/.aws/` config files. Documented as `environment/r2-setup.md`. Built proper COG DTM (`_dtm_cog.tif`) with 3 overview levels via `gdal_translate -of COG`. Fixed three bugs in `giro3d-viewer/src/ui.js`: missing `ASPRS_CLASSES` import, `buildClassificationPanel` nested inside `wireUI` with illegal `export`, dead `onRamp` handler.  
**Key facts:**
- R2 bucket: `geospatial-vision`, profile: `r2`, COPC at `copc/` prefix
- ListBuckets denied by token — always address bucket directly
- COG DTM: 512×512 blocks, 3 overview levels, DEFLATE compressed
- Root `.venv` missing `--system-site-packages` — needs recreating to access `python3-gdal`

---

## 2026-04-24 — Pipeline Phases 2–4 validated; template system refactored

**Action:** Update + Ingest  
**Summary:** Read `PIPELINE_CONTEXT_NEW.md` from Claude chat. Compared against wiki and updated `pipeline-system.md` to reflect all four phases complete.  
**Key changes this session:**
- Template system refactored from `string.Template` (fragile on WKT/JSON) to dict-level injection after `json.load()` — templates are now valid JSON files
- `logger.py` added: timestamped CSV, one file per run, columns include `total_elapsed_s` computed internally
- Stage whitelist (`SUPPORTED_STAGES`) + `pdal.drivers()` fallback validation added to `load_pipeline`
- Confirmed run: 18,991,582 input points → 14,668,865 ground points, 5.42 ppsm, PASS, 49.87s total
- Bugs fixed during session: wrong import path (`from pipeline.logger` → `from logger`), missing `Template` import, missing pipeline execution step in `__main__`

**Notes:** `__init__.py` not yet in repo — currently running as direct script, not `python -m pipeline.run_pipeline`. Remote LAZ indexing added to backlog as priority research item.

---

## 2026-04-22 — Wiki initialised

**Action:** Ingest  
**Summary:** Read CLAUDE.md and PIPELINE_CONTEXT.md. Initialised wiki vault from scratch.  
**Pages created:**
- `index.md`, `log.md`, `WIKI_SCHEMA.md`
- `projects/`: geoprocessor, pipeline-system, fastapi-spatial-api, dtm-postgis
- `concepts/`: gdal, pdal, cog, copc, postgis, smrf
- `environment/`: wsl2-setup, conda-lidar-env, python-install-rules
- `decisions/`: postgis-vs-titiler (pending)

**Notes:** Pipeline Phase 2 (`run_pipeline.py`) not yet written — `pipeline/` directory does not exist in repo. Next session: create pipeline directory structure and implement Phase 2.
