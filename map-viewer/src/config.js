export const PMTILES_URL = 'pmtiles://https://pub-729a4f32b70f473abbf23bf25daf2899.r2.dev/pmtiles/mesh_blocks_v2.pmtiles';
export const COG_TILES_URL = 'https://geospatial-titiler.onrender.com/cog/tiles/WebMercatorQuad/{z}/{x}/{y}?url=https://pub-729a4f32b70f473abbf23bf25daf2899.r2.dev/cog/Melbourne_2018_dtm_f32_v2.tif&colormap_name=terrain&rescale=-5,100';
export const INITIAL_CENTER = [133.0, -27.0]; // centre of Australia
export const INITIAL_ZOOM = 4;

export const CATEGORY_COLOURS = {
  'Residential':       '#a8c5e8',
  'Commercial':        '#f4a460',
  'Industrial':        '#b8a0c8',
  'Parkland':          '#90c490',
  'Education':         '#f7d080',
  'Hospital/Medical':  '#f08080',
  'Transport':         '#c0c0c0',
  'Primary Production':'#d4b896',
  'Other':             '#e0e0e0',
  'SHIPPING':          '#80b4c8',
};

export const CATEGORIES = Object.keys(CATEGORY_COLOURS);
