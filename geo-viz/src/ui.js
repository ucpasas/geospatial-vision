// ─── ui.js ────────────────────────────────────────────────────────────────────
// DOM only. No renderer imports.
// Manages: layer toggle checkboxes, FPS display, loading state, point count.
// ──────────────────────────────────────────────────────────────────────────────

/**
 * Initialise layer toggles.
 * @param {Function} onToggle — called with (layerId, boolean) on change
 */
export function initToggles(onToggle) {
  const toggles = document.querySelectorAll('.layer-toggle');
  toggles.forEach(cb => {
    cb.addEventListener('change', () => {
      onToggle(cb.dataset.layer, cb.checked);
    });
  });
}

/**
 * Mount the FPS/draw-call display into #stats-container.
 * Called once at startup.
 */
export function mountFpsDisplay() {
  const el = document.getElementById('stats-container');
  if (!el) return;
  el.innerHTML = `
    <div class="stat-row"><span class="stat-label">FPS</span><span class="stat-value" id="stat-fps">—</span></div>
    <div class="stat-row"><span class="stat-label">DRAW CALLS</span><span class="stat-value" id="stat-draws">—</span></div>
    <div class="stat-row"><span class="stat-label">POINTS</span><span class="stat-value" id="stat-points">—</span></div>
  `;
}

/**
 * Update stats display on each render.
 * Reads from deck.gl's onAfterRender metrics object.
 */
export function updateStatsDisplay(metrics, pointCount) {
  const fps   = document.getElementById('stat-fps');
  const draws = document.getElementById('stat-draws');
  const pts   = document.getElementById('stat-points');
  if (fps   && metrics?.fps)              fps.textContent   = Math.round(metrics.fps);
  if (draws && metrics?.renderCount)      draws.textContent = metrics.renderCount;
  if (pts   && pointCount !== undefined)  pts.textContent   = pointCount.toLocaleString();
}

/** Show/hide the loading overlay with an optional message. */
export function setLoading(visible, message = 'Loading…') {
  const overlay = document.getElementById('loading-overlay');
  const msg     = document.getElementById('loading-message');
  if (!overlay) return;
  overlay.style.display = visible ? 'flex' : 'none';
  if (msg) msg.textContent = message;
}

/** Update the point count badge in the header. */
export function setPointCount(n) {
  const el = document.getElementById('point-count');
  if (el) el.textContent = `${(n / 1000).toFixed(0)}k pts`;
}