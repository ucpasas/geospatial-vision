// src/pointcloud.js
// ─────────────────────────────────────────────────────────────────────────────
// COPCSource, PointCloud entity, and colour map.
//
// This is the module to replace when swapping viewers:
//   - Giro3D → Potree: replace COPCSource + PointCloud
//   - On-the-fly LAZ:  replace COPCSource with WebWorker+laz-perf pipeline,
//                      replace PointCloud with THREE.Points
//
// Everything this module returns is plain data (Box3, attribute list)
// or Giro3D objects wrapped behind a consistent interface so callers
// don't need to know the internals.
// ─────────────────────────────────────────────────────────────────────────────

import { Color } from "three";
import colormap from "colormap";

import ColorMap from "@giro3d/giro3d/core/ColorMap.js";
import PointCloud from "@giro3d/giro3d/entities/PointCloud.js";
import COPCSource from "@giro3d/giro3d/sources/COPCSource.js";

// ─── Colour ramps ─────────────────────────────────────────────────────────────
// Uses the colormap package — same presets as the official Giro3D example.
// Returns an array of THREE.Color, which is what ColorMap expects.

/**
 * Builds a colour ramp from a colormap preset name.
 * @param {string} preset - e.g. "viridis", "bathymetry", "jet"
 * @returns {Color[]}
 */
export function makeColorRamp(preset) {
  const values = colormap({ colormap: preset, nshades: 256, format: "hex" });
  return values.map((v) => new Color(v));
}

// ─── Source ───────────────────────────────────────────────────────────────────

/**
 * Creates a COPCSource and initialises it (fetches COPC header from R2).
 * Reports load progress via onProgress callback.
 *
 * Returns the initialised source and its metadata.
 * Metadata contains: crs, attributes (name, min, max, type), bounds.
 *
 * @param {string} url - public COPC URL on R2
 * @param {function} onProgress - called with 0–1 as octree loads
 * @returns {Promise<{ source: COPCSource, metadata: object }>}
 */
export async function createSource(url, onProgress = () => {}) {
  const source = new COPCSource({ url });

  source.addEventListener("progress", () => onProgress(source.progress));

  await source.initialize();
  const metadata = await source.getMetadata();

  return { source, metadata };
}

// ─── Colour map ───────────────────────────────────────────────────────────────

/**
 * Creates a ColorMap initialised to the Z extent of the dataset.
 * One ColorMap instance is shared across all attributes — it gets
 * mutated when the user changes ramp or adjusts bounds.
 *
 * @param {Box3} volume - bounding box from entity.getBoundingBox()
 * @param {string} preset - initial colour ramp preset
 * @returns {ColorMap}
 */
export function createColorMap(volume, preset = "bathymetry") {
  return new ColorMap({
    colors: makeColorRamp(preset),
    min: volume.min.z,
    max: volume.max.z,
  });
}

// ─── Entity ───────────────────────────────────────────────────────────────────

/**
 * Creates a PointCloud entity from a source, adds it to the instance,
 * then wires up the colour map across all attributes.
 *
 * Returns the entity and its bounding volume.
 * Callers use volume for camera placement, terrain extent, and filter bounds
 * — they never need to reach into the entity directly for these.
 *
 * @param {Instance} instance
 * @param {COPCSource} source
 * @param {object[]} attributes - from metadata.attributes
 * @param {ColorMap} colorMap
 * @returns {Promise<{ entity: PointCloud, volume: Box3 }>}
 */
export async function createPointCloud(instance, source, attributes, colorMap) {
  const entity = new PointCloud({ source });
  await instance.add(entity);

  const volume = entity.getBoundingBox();

  // Wire colour map to every attribute in the file
  entity.elevationColorMap = colorMap;
  for (const attr of attributes) {
    entity.setAttributeColorMap(attr.name, colorMap);
  }

  // Default to first attribute (usually Z/position)
  entity.setColoringMode("attribute");
  entity.setActiveAttribute(attributes[0].name);

  return { entity, volume };
}

/**
 * Sets the active attribute for colouring.
 * @param {PointCloud} entity
 * @param {Instance} instance
 * @param {string} attributeName
 */
export function setActiveAttribute(entity, instance, attributeName) {
  entity.setActiveAttribute(attributeName);
  instance.notifyChange(entity);
}

/**
 * Sets point size. 0 = auto.
 * @param {PointCloud} entity
 * @param {Instance} instance
 * @param {number} size
 */
export function setPointSize(entity, instance, size) {
  entity.pointSize = size;
  instance.notifyChange(entity);
}

/**
 * Pushes the current filter spec to the source.
 * Pass null to disable all filters.
 * @param {COPCSource} source
 * @param {Instance} instance
 * @param {object[]|null} filters
 */
export function applyFilters(source, instance, filters) {
  source.filters = filters;
  instance.notifyChange();
}

/**
 * Returns live point counts from the entity.
 * Called on every update-end event to keep the UI stats current.
 * @param {PointCloud} entity
 * @returns {{ total: number, displayed: number }}
 */
export function getPointCounts(entity) {
  return {
    total:     entity.pointCount,
    displayed: entity.displayedPointCount,
  };
}