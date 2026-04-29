// ─── config.js ────────────────────────────────────────────────────────────────
// All environment-specific values live here.
// One file, all tunables. Nothing else needs to change for a data source swap.
// ──────────────────────────────────────────────────────────────────────────────

// COG DTM — served directly from R2, read via geotiff.js range requests.
// Replace with your R2 public URL.
export const COG_URL = 'https://pub-729a4f32b70f473abbf23bf25daf2899.r2.dev/cog/USGS_LPC_TX_Central_B1_2017_stratmap17_50cm_2996011a1_LAS_2019_dtm_cog.tif';

// GeoJSON roads/infrastructure — Phase 2, source TBD.
export const GEOJSON_URL = 'https://pub-729a4f32b70f473abbf23bf25daf2899.r2.dev/vector/roads/TX_Central_B1.geojson';

// COG sampling — geotiff.js picks the best overview to satisfy these dimensions.
// 400x400 = 160k pixels, well within GPU budget, good spatial coverage at z14.
export const SAMPLE_WIDTH  = 400;
export const SAMPLE_HEIGHT = 400;

// Nodata sentinel — must match what PDAL wrote into the COG.
export const NODATA = -9999;

// Initial view — zoom, pitch, bearing only.
// MAP_CENTER is derived at runtime from COG bounding box in cog.js.
export const INITIAL_ZOOM    = 14;
export const INITIAL_PITCH   = 45;
export const INITIAL_BEARING = -20;

// ScatterplotLayer
export const SCATTER_RADIUS = 3;  // metres per point

export const HEX_RADIUS          = 30;   // was 20 — slightly larger bins, less noise
export const HEX_ELEVATION_RANGE = [0, 300];  // was [0, 150]
export const HEX_ELEVATION_SCALE = 4;    // was 1 — exaggerate the relief
export const HEX_COVERAGE        = 0.72; // was 0.88 — gaps between bins, less blocky
// Stats panel
export const SHOW_STATS = true;