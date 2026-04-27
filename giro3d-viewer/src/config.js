export const COPC_URL = "https://pub-729a4f32b70f473abbf23bf25daf2899.r2.dev/copc/USGS_LPC_TX_Central_B1_2017_stratmap17_50cm_2996011a1_LAS_2019.copc.laz";

const isLocalhost =
  typeof window !== "undefined" &&
  (window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1");

export const LAZ_PERF_PATH = isLocalhost
  ? "/assets/wasm"
  : "/geospatial-vision/giro3d-viewer/assets/wasm";

export const TERRAIN_URL = "https://geospatial-titiler.onrender.com/cog/tiles/WebMercatorQuad/{z}/{x}/{y}?url=https://pub-729a4f32b70f473abbf23bf25daf2899.r2.dev/cog/USGS_LPC_TX_Central_B1_2017_stratmap17_50cm_2996011a1_LAS_2019_dtm_cog.tif&tilesize=512";

export const TERRAIN_PROJECTION = "EPSG:3857";