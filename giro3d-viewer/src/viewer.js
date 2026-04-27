// src/viewer.js
// ─────────────────────────────────────────────────────────────────────────────
// Instance creation, rendering options, and camera placement.
// This is the most viewer-specific module — if you swap Giro3D for another
// renderer, this is the primary file that changes.
// ─────────────────────────────────────────────────────────────────────────────

import { MathUtils, Vector3 } from "three";
import { MapControls } from "three/examples/jsm/controls/MapControls.js";

import CoordinateSystem from "@giro3d/giro3d/core/geographic/CoordinateSystem.js";
import Instance from "@giro3d/giro3d/core/Instance.js";
import { setLazPerfPath } from "@giro3d/giro3d/sources/las/config.js";

// ─── CRS registration ────────────────────────────────────────────────────────
// Must be called before createInstance().
// Hardcoded for EPSG:6343 — no epsg.io fetch needed.
// If your data changes CRS, update the proj4 string here.

/**
 * Registers EPSG:6343 with proj4js.
 * Call once at module load time, before any Instance is created.
 */
export function registerCRS() {
  // EPSG:6343 — NAD83(2011) / UTM zone 14N (USGS Central Texas COPC)
  CoordinateSystem.register(
    "EPSG:6343",
    "+proj=utm +zone=14 +ellps=GRS80 +units=m +no_defs +type=crs",
  );
}

// ─── WASM ────────────────────────────────────────────────────────────────────

/**
 * Sets the path where laz-perf.wasm can be found.
 * Must be called before any COPCSource is constructed.
 * @param {string} path - e.g. "/assets/wasm"
 */
export function initWasm(path) {
  setLazPerfPath(path);
}

// ─── Instance ────────────────────────────────────────────────────────────────

/**
 * Creates and returns a Giro3D Instance attached to the #view element.
 * @param {object} crs - CRS object from source metadata
 * @returns {Instance}
 */
export function createInstance(crs) {
  const instance = new Instance({
    target: "view",
    crs,
    backgroundColor: 0x0d1117,
  });

  return instance;
}

// ─── EDL ─────────────────────────────────────────────────────────────────────
// Eye Dome Lighting — makes point cloud edges readable by darkening
// points whose neighbours are further away. Purely a render effect,
// no impact on the data.

const EDL_DEFAULTS = {
  enabled:  true,
  radius:   0.6,
  strength: 5,
};

/**
 * Applies EDL settings to an instance.
 * @param {Instance} instance
 * @param {object} opts - override EDL_DEFAULTS
 */
export function setEDL(instance, opts = {}) {
  const { enabled, radius, strength } = { ...EDL_DEFAULTS, ...opts };
  instance.renderingOptions.enableEDL      = enabled;
  instance.renderingOptions.EDLRadius      = radius;
  instance.renderingOptions.EDLStrength    = strength;
  instance.notifyChange();
}

/**
 * Toggles EDL on/off without changing radius/strength.
 * @param {Instance} instance
 * @param {boolean} enabled
 */
export function toggleEDL(instance, enabled) {
  instance.renderingOptions.enableEDL = enabled;
  instance.notifyChange();
}

/**
 * Toggles inpainting — fills gaps between sparse points.
 * @param {Instance} instance
 * @param {boolean} enabled
 */
export function toggleInpainting(instance, enabled) {
  instance.renderingOptions.enableInpainting          = enabled;
  instance.renderingOptions.enablePointCloudOcclusion = enabled;
  instance.notifyChange();
}

// ─── Camera ──────────────────────────────────────────────────────────────────
// Places the camera above the dataset bounding box so the full
// point cloud is visible on load. Uses MapControls (pan/zoom/tilt)
// rather than full orbit — appropriate for geographic data.

/**
 * Places camera above the dataset and sets up MapControls.
 * @param {Instance} instance
 * @param {Box3} volume - bounding box from entity.getBoundingBox()
 */
export function placeCameraOnTop(instance, volume) {
  const center = volume.getCenter(new Vector3());
  const size   = volume.getSize(new Vector3());
  const camera = instance.view.camera;
  const hFov   = MathUtils.degToRad(camera.fov) / 2;

  const altitude =
    (Math.max(size.x / camera.aspect, size.y) / Math.tan(hFov)) * 0.5;

  camera.position.set(center.x, center.y - 1, altitude + volume.max.z);
  camera.lookAt(center);

  const controls = new MapControls(camera, instance.domElement);
  controls.target.copy(center);
  controls.enableDamping  = true;
  controls.dampingFactor  = 0.25;

  instance.view.setControls(controls);
  instance.notifyChange(camera);
}