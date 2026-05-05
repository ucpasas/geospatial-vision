export const COPC_URL = "https://pub-729a4f32b70f473abbf23bf25daf2899.r2.dev/copc/Melbourne_2018.laz.copc";

const isLocalhost =
  typeof window !== "undefined" &&
  (window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1");

export const LAZ_PERF_PATH = isLocalhost
  ? "/assets/wasm"
  : "/geospatial-vision/giro3d-viewer/assets/wasm";

export const TERRAIN_URL = "https://geospatial-titiler.onrender.com/cog/tiles/WebMercatorQuad/{z}/{x}/{y}?url=https://pub-729a4f32b70f473abbf23bf25daf2899.r2.dev/cog/Melbourne_2018_dtm_f32_v2.tif&colormap_name=terrain&rescale=-5,100";

export const TERRAIN_PROJECTION = "EPSG:3857";