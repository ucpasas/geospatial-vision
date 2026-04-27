// src/main.js
// ─────────────────────────────────────────────────────────────────────────────
// Orchestrator — calls modules in sequence, passes state between them.
// No Giro3D imports. No DOM manipulation.
// If you need to understand what the app does, read this file first.
// ─────────────────────────────────────────────────────────────────────────────

import { COPC_URL, LAZ_PERF_PATH } from "./config.js";

import {
  registerCRS,
  initWasm,
  createInstance,
  setEDL,
  toggleEDL,
  toggleInpainting,
  placeCameraOnTop,
} from "./viewer.js";

import {
  createSource,
  createColorMap,
  createPointCloud,
  setActiveAttribute,
  setPointSize,
  applyFilters,
  getPointCounts,
} from "./pointcloud.js";

import {
  extentFromVolume,
  loadTerrain,
} from "./terrain.js";

import {
  createHiddenSet,
  buildClassificationFilter,
} from "./filters.js";

import {
  setProgress,
  setProgressVisible,
  setStatus,
  showError,
  showInfoPanel,
  updatePointCounts,
  populateAttributes,
  buildClassificationPanel,
  wireUI,
} from "./ui.js";

// ─── Boot — runs once ─────────────────────────────────────────────────────────
// initWasm before any COPCSource is constructed.
// registerCRS before any Instance is created.
initWasm(LAZ_PERF_PATH);
registerCRS();

// ─── Load sequence ────────────────────────────────────────────────────────────
async function load() {
  setProgressVisible(true);
  setStatus("Loading COPC metadata…");

  // ── 1. Source — fetches COPC header from R2
  let source, metadata;
  try {
    ({ source, metadata } = await createSource(COPC_URL, setProgress));
  } catch (err) {
    showError(`Failed to load COPC: ${err.message}`);
    setProgressVisible(false);
    console.error(err);
    return;
  }

  // ── 2. Instance — created in the file's own CRS
  const instance = createInstance(metadata.crs);
  setEDL(instance);

  // ── 3. Colour map — placeholder bounds, updated after entity loads
  const colorMap = createColorMap(
    { min: { z: 0 }, max: { z: 1 } },
    "bathymetry",
  );

  // ── 4. Point cloud entity
  const { entity, volume } = await createPointCloud(
    instance,
    source,
    metadata.attributes,
    colorMap,
  );

  // Update colour map bounds from real data extent
  colorMap.min = volume.min.z;
  colorMap.max = volume.max.z;
  instance.notifyChange(entity);

  // ── 5. Classification filter — class 18 hidden by default
  const hiddenClasses = createHiddenSet([18]);
  applyFilters(source, instance, buildClassificationFilter(hiddenClasses));

  // ── 6. Terrain — Mapbox placeholder until TiTiler is live (Phase 3)
  setStatus("Loading terrain…");
  const extent = extentFromVolume(metadata.crs, volume);
  loadTerrain(instance, extent);

  // ── 7. UI
  populateAttributes(metadata.attributes);
  showInfoPanel();

  const classifications = entity.getAttributeClassifications("Classification");
  const presentCodes = Object.keys(classifications).map(Number);

  buildClassificationPanel(
    hiddenClasses,
    presentCodes,
    (filters) => applyFilters(source, instance, filters),
  );

  instance.addEventListener("update-end", () => {
    updatePointCounts(getPointCounts(entity));
  });

  wireUI({
    instance,
    entity,
    source,
    colorMap,
    hiddenClasses,
    onEDL:         (v) => toggleEDL(instance, v),
    onInpainting:  (v) => toggleInpainting(instance, v),
    onPointSize:   (v) => setPointSize(entity, instance, v),
    onAttribute:   (v) => setActiveAttribute(entity, instance, v),
    onClassFilter: (filters) => applyFilters(source, instance, filters),
  });

  // ── 8. Camera
  placeCameraOnTop(instance, volume);

  setProgressVisible(false);
  setStatus("Ready");
  instance.notifyChange();
}

// ─── Boot ─────────────────────────────────────────────────────────────────────
load().catch((err) => {
  console.error(err);
  showError(String(err));
});