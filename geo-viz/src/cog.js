// ─── cog.js ───────────────────────────────────────────────────────────────────
// Owns: geotiff
// Responsibility: open COG via range requests, read raster at target dimensions,
// convert pixels to WGS84 points, derive map centre from bounding box.
// Returns structured data to main.js — no deck.gl, no DOM.
// ──────────────────────────────────────────────────────────────────────────────

import { fromUrl } from 'geotiff';
import { buildToWGS84Transformer } from './projection.js';
import { COG_URL, SAMPLE_WIDTH, SAMPLE_HEIGHT, NODATA } from './config.js';

/**
 * Load the COG and return points + map centre.
 *
 * @returns {Promise<{
 *   points: Array<{lon, lat, height}>,
 *   center: [lon, lat]
 * }>}
 */
export async function loadCOG() {
  const tiff  = await fromUrl(COG_URL);
  const image = await tiff.getImage();

  const toWGS84 = buildToWGS84Transformer(image);

  // Bounding box in native CRS (UTM metres for EPSG:6343)
  const bbox = image.getBoundingBox();  // [xmin, ymin, xmax, ymax]

  const sw = toWGS84(bbox[0], bbox[1]);
  const ne = toWGS84(bbox[2], bbox[3]);
  console.log(`Bounding box (WGS84): ${sw[1]},${sw[0]},${ne[1]},${ne[0]}`);

  // Derive map centre from bounding box — no hardcoding
  const centreX = (bbox[0] + bbox[2]) / 2;
  const centreY = (bbox[1] + bbox[3]) / 2;
  const center  = toWGS84(centreX, centreY);

  // Read raster at target dimensions — geotiff picks the best overview
  const [elevation] = await image.readRasters({
    width:          SAMPLE_WIDTH,
    height:         SAMPLE_HEIGHT,
    resampleMethod: 'nearest',
    fillValue:      NODATA,
  });

  // Step size in UTM metres at the resampled dimensions
  const xStep = (bbox[2] - bbox[0]) / SAMPLE_WIDTH;
  const yStep = (bbox[3] - bbox[1]) / SAMPLE_HEIGHT;

  const points = [];

  for (let i = 0; i < elevation.length; i++) {
    const h = elevation[i];
    if (h === NODATA || !isFinite(h)) continue;

    const col = i % SAMPLE_WIDTH;
    const row = Math.floor(i / SAMPLE_WIDTH);

    // Pixel centre → UTM
    const x = bbox[0] + (col + 0.5) * xStep;
    const y = bbox[3] - (row + 0.5) * yStep;  // y inverted — row 0 is top of raster

    const [lon, lat] = toWGS84(x, y);
    points.push({ lon, lat, height: h });
  }

  return { points, center };
}