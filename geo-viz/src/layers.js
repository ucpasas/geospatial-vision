// ─── layers.js ────────────────────────────────────────────────────────────────
// Owns: deck.gl
// Responsibility: all layer constructors.
// ONLY this file imports from 'deck.gl'.
// ──────────────────────────────────────────────────────────────────────────────

import { ScatterplotLayer, HexagonLayer, GeoJsonLayer } from 'deck.gl';
import {
  SCATTER_RADIUS,
  HEX_RADIUS,
  HEX_ELEVATION_RANGE,
  HEX_ELEVATION_SCALE,
  HEX_COVERAGE,
} from './config.js';

// ── Height range calibration ──────────────────────────────────────────────────

/**
 * Derive min/max height from the point array.
 * Returns a range object — no module-level state.
 *
 * @param   {Array<{lon, lat, height}>} points
 * @returns {{ min: number, max: number }}
 */
export function calibrateHeightRange(points) {
  let min = Infinity;
  let max = -Infinity;
  for (const p of points) {
    if (p.height < min) min = p.height;
    if (p.height > max) max = p.height;
  }
  return { min, max };
}

// ── Height → colour ramp ──────────────────────────────────────────────────────

function heightToColour(height, min, max) {
  const t = Math.max(0, Math.min(1, (height - min) / (max - min || 1)));
  const r = Math.round(t < 0.5 ? t * 2 * 50 : 50 + (t - 0.5) * 2 * 205);
  const g = Math.round(t < 0.5 ? 100 + t * 2 * 100 : 200 - (t - 0.5) * 2 * 100);
  const b = Math.round(t < 0.5 ? 180 - t * 2 * 100 : 80 - (t - 0.5) * 2 * 80);
  return [r, g, b, 200];
}

// ── Road type → colour ────────────────────────────────────────────────────────

const ROAD_COLOURS = {
  motorway:    [255, 80,  80,  220],
  trunk:       [255, 140, 60,  200],
  primary:     [255, 200, 80,  200],
  secondary:   [180, 220, 80,  180],
  tertiary:    [120, 200, 140, 160],
  residential: [80,  160, 200, 140],
  service:     [60,  120, 180, 120],
  default:     [100, 100, 120, 100],
};

function roadColour(highway) {
  return ROAD_COLOURS[highway] || ROAD_COLOURS.default;
}

// ── Layer factories ───────────────────────────────────────────────────────────

/**
 * @param {Array<{lon, lat, height}>} data
 * @param {boolean} visible
 * @param {{ min: number, max: number }} heightRange
 */
export function makeScatterLayer(data, visible, heightRange) {
  const { min, max } = heightRange;
  return new ScatterplotLayer({
    id: 'scatter',
    data,
    visible,
    pickable: true,
    opacity: 0.8,
    stroked: false,
    filled: true,
    radiusMinPixels: 1,
    radiusMaxPixels: 6,
    radiusScale: SCATTER_RADIUS,
    getPosition: d => [d.lon, d.lat, d.height],
    getFillColor: d => heightToColour(d.height, min, max),
    updateTriggers: {
      getFillColor: [min, max],
    },
  });
}

/**
 * @param {Array<{lon, lat, height}>} data
 * @param {boolean} visible
 */
export function makeHexLayer(data, visible) {
  return new HexagonLayer({
    id: 'hex',
    data,
    visible,
    pickable: true,
    extruded: true,
    radius: HEX_RADIUS,
    elevationRange: HEX_ELEVATION_RANGE,
    elevationScale: HEX_ELEVATION_SCALE,
    coverage: HEX_COVERAGE,
    getPosition: d => [d.lon, d.lat],
    getColorWeight: d => d.height,
    colorAggregation: 'MEAN',
    colorRange: [
      [1,  152, 189, 200],
      [73, 227, 206, 200],
      [216,254, 181, 200],
      [254,237, 177, 200],
      [254,173, 84,  200],
      [209,55,  78,  200],
    ],
    material: {
      ambient: 0.64,
      diffuse: 0.6,
      shininess: 32,
      specularColor: [51, 51, 51],
    },
  });
}

/**
 * @param {string} url
 * @param {boolean} visible
 */
export function makeGeoJsonLayer(url, visible) {
  return new GeoJsonLayer({
    id: 'geojson',
    data: url,
    visible,
    pickable: true,
    stroked: true,
    filled: true,
    lineWidthMinPixels: 1,
    lineWidthScale: 2,
    getLineColor: f => roadColour(f.properties?.highway),
    getLineWidth: f => {
      const hw = f.properties?.highway;
      if (hw === 'motorway' || hw === 'trunk') return 4;
      if (hw === 'primary' || hw === 'secondary') return 2;
      return 1;
    },
    getFillColor: [160, 160, 180, 80],
    getPointRadius: 4,
  });
}