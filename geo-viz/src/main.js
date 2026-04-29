// ─── main.js ──────────────────────────────────────────────────────────────────
// Thin orchestrator. Calls modules in sequence.
// Order: ui init → deck init → COG load → layer build → render loop
// ──────────────────────────────────────────────────────────────────────────────

import { Deck } from 'deck.gl';
import { GEOJSON_URL, INITIAL_ZOOM, INITIAL_PITCH, INITIAL_BEARING } from './config.js';
import { loadCOG } from './cog.js';
import { calibrateHeightRange, makeScatterLayer, makeHexLayer, makeGeoJsonLayer } from './layers.js';
import { getTooltip } from './tooltip.js';
import { initToggles, mountFpsDisplay, updateStatsDisplay, setLoading, setPointCount } from './ui.js';

// ── State ─────────────────────────────────────────────────────────────────────
const visibility = { scatter: true, hex: false, geojson: false };
let pointData = [];
let deck = null;
let heightRange = { min: 0, max: 1 };

// ── Layer rebuild ─────────────────────────────────────────────────────────────
function rebuildLayers() {
  if (!deck) return;
  deck.setProps({
    layers: [
      makeScatterLayer(pointData, visibility.scatter, heightRange),
      makeHexLayer(pointData,       visibility.hex),
      makeGeoJsonLayer(GEOJSON_URL, visibility.geojson),
    ],
  });
}

// ── Render loop ──────────────────────────────────────────────────────────────
    function updateLoop() {
    updateStatsDisplay(deck.metrics, pointData.length);
    requestAnimationFrame(updateLoop);
}

// ── Entry point ───────────────────────────────────────────────────────────────
async function init() {
  mountFpsDisplay();

  initToggles((layerId, checked) => {
    visibility[layerId] = checked;
    rebuildLayers();
  });

  try {
    setLoading(true, 'Loading COG metadata…');
    const { points, center } = await loadCOG();

    deck = new Deck({
      canvas: 'deck-canvas',
      initialViewState: {
        longitude: center[0],
        latitude:  center[1],
        zoom:      INITIAL_ZOOM,
        pitch:     INITIAL_PITCH,
        bearing:   INITIAL_BEARING,
      },
      controller: true,
      layers: [],
      getTooltip,
      parameters: {
        clearColor: [0.05, 0.07, 0.10, 1],
      },
    });

    requestAnimationFrame(updateLoop);

    pointData = points;
    heightRange = calibrateHeightRange(pointData);
    setPointCount(pointData.length);
    setLoading(false);
    rebuildLayers();

  } catch (err) {
    console.error('Data load failed:', err);
    setLoading(true, `⚠ ${err.message}`);
  }
}

init();