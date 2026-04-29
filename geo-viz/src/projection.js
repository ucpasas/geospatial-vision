// ─── projection.js ────────────────────────────────────────────────────────────
// Owns: proj4, geotiff-geokeys-to-proj4
// Responsibility: derive a CRS transformer from a GeoTIFF image's own metadata.
// No hardcoded CRS strings — the file describes itself.
// Output is always WGS84 (EPSG:4326) — what deck.gl expects.
// ──────────────────────────────────────────────────────────────────────────────

import proj4 from 'proj4';
import { toProj4, convertCoordinates } from 'geotiff-geokeys-to-proj4';

// Target CRS — deck.gl's coordinate system.
const WGS84 = 'EPSG:4326';

/**
 * Build a transformer that converts native CRS coordinates → WGS84 (EPSG:4326).
 * CRS is derived entirely from the GeoTIFF's embedded geokeys — no hardcoding.
 *
 * @param   {GeoTIFFImage} image  — from geotiff.js tiff.getImage()
 * @returns {Function}            — toWGS84(x, y) => [lon, lat]
 */
export function buildToWGS84Transformer(image) {
  const geokeys = image.getGeoKeys();
  const projObj  = toProj4(geokeys);
  const transformer = proj4(projObj.proj4, WGS84);

return function toWGS84(x, y) {
  const coords = projObj.coordinatesConversionParameters
    ? convertCoordinates(x, y, 0, projObj.coordinatesConversionParameters)
    : [x, y];
  const result = transformer.forward(coords);
  // proj4 can return either {x, y} or [x, y] depending on input format
  return Array.isArray(result) ? result : [result.x, result.y];
};
}