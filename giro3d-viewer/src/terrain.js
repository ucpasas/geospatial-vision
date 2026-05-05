// src/terrain.js
// ─────────────────────────────────────────────────────────────────────────────
// Terrain layer — Map entity + ElevationLayer.
//
// Phase 3 swap: replace TERRAIN_URL and format in config.js.
// If TiTiler serves EPSG:28355 natively, also update the XYZ projection.
//
// This module is intentionally thin — all config lives in config.js,
// all Giro3D wiring is isolated here so terrain can be swapped or
// removed without touching any other module.
// ─────────────────────────────────────────────────────────────────────────────

import XYZ from "ol/source/XYZ.js";

import Extent from "@giro3d/giro3d/core/geographic/Extent.js";
import ElevationLayer from "@giro3d/giro3d/core/layer/ElevationLayer.js";
import Map from "@giro3d/giro3d/entities/Map.js";
import MapboxTerrainFormat from "@giro3d/giro3d/formats/MapboxTerrainFormat.js";
import TiledImageSource from "@giro3d/giro3d/sources/TiledImageSource.js";

import { TERRAIN_PROJECTION, TERRAIN_URL } from "./config.js";

// ─── Extent ───────────────────────────────────────────────────────────────────

/**
 * Derives a terrain extent from the point cloud bounding volume.
 * Adds a relative margin so terrain extends beyond the point cloud edges.
 *
 * @param {object} crs - CRS from source metadata
 * @param {Box3} volume - bounding box from entity.getBoundingBox()
 * @param {number} margin - relative margin, default 1.2 (20% each side)
 * @returns {Extent}
 */
export function extentFromVolume(crs, volume, margin = 1.2) {
  return Extent.fromBox3(crs, volume).withRelativeMargin(margin);
}

// ─── Terrain ─────────────────────────────────────────────────────────────────

/**
 * Creates a Map entity with an ElevationLayer and adds it to the instance.
 *
 * Phase 3 — TiTiler swap:
 *   1. Update TERRAIN_URL in config.js to your TiTiler tile URL template
 *   2. If TiTiler serves terrain-rgb: keep MapboxTerrainFormat
 *      If TiTiler serves raw elevation: swap format accordingly
 *   3. Update TERRAIN_PROJECTION in config.js if serving EPSG:28355 natively
 *
 * @param {Instance} instance
 * @param {Extent} extent
 * @returns {Map}
 */
export function loadTerrain(instance, extent) {
  const map = new Map({ extent });
  instance.add(map);

  const elevationLayer = new ElevationLayer({
    extent,
    resolutionFactor: 0.25,
    source: new TiledImageSource({
      format: new MapboxTerrainFormat(),
      source: new XYZ({
        url: TERRAIN_URL,
        projection: TERRAIN_PROJECTION,
      }),
    }),
  });

  map.addLayer(elevationLayer);
  return map;
}

/**
 * Toggles terrain visibility.
 * @param {Map} map
 * @param {Instance} instance
 * @param {boolean} visible
 */
export function setTerrainVisible(instance, map, visible) {
  map.visible = visible;
  instance.notifyChange(map);
}