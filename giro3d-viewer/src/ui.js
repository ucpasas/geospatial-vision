// src/ui.js
// ─────────────────────────────────────────────────────────────────────────────
// All DOM wiring and event listeners.
// No imports from @giro3d/giro3d — this module is renderer-agnostic.
// Receives viewer state via the init() call and talks back through
// the module functions passed in.
// ─────────────────────────────────────────────────────────────────────────────

import { makeColorRamp } from "./pointcloud.js";
import { setClassVisibility, buildClassificationFilter, ASPRS_CLASSES } from "./filters.js";

// ─── Progress ─────────────────────────────────────────────────────────────────

/**
 * Updates the progress bar. normalized = 0–1.
 * @param {number} normalized
 */
export function setProgress(normalized) {
  const bar = document.getElementById("progress-bar");
  if (bar) bar.style.width = `${Math.round(normalized * 100)}%`;
}

/**
 * Shows or hides the progress bar wrapper.
 * @param {boolean} visible
 */
export function setProgressVisible(visible) {
  const wrap = document.getElementById("progress-wrap");
  if (wrap) wrap.style.display = visible ? "block" : "none";
}

/**
 * Sets the status bar text.
 * @param {string} text
 */
export function setStatus(text) {
  const el = document.getElementById("status-text");
  if (el) el.textContent = text;
}

/**
 * Shows an error message in the error box.
 * @param {string} message
 */
export function showError(message) {
  const el = document.getElementById("error-box");
  if (!el) return;
  el.textContent = message;
  el.style.display = "block";
}

// ─── Stats ────────────────────────────────────────────────────────────────────

/**
 * Updates the point count stats panel.
 * Called on every update-end event from the instance.
 * @param {{ total: number, displayed: number }} counts
 */
export function updatePointCounts({ total, displayed }) {
  const totalEl     = document.getElementById("point-count");
  const displayedEl = document.getElementById("displayed-count");
  if (totalEl)     totalEl.textContent     = fmt(total);
  if (displayedEl) displayedEl.textContent = fmt(displayed);
}

/**
 * Shows the info panel (hidden until data is loaded).
 */
export function showInfoPanel() {
  const el = document.getElementById("info-panel");
  if (el) el.style.display = "block";
}

// ─── Attribute selector ───────────────────────────────────────────────────────

/**
 * Populates the attribute dropdown from file metadata.
 * @param {object[]} attributes - from metadata.attributes
 */
export function populateAttributes(attributes) {
  const select = document.getElementById("attribute-select");
  if (!select) return;
  select.innerHTML = "";
  for (const attr of attributes) {
    const opt = document.createElement("option");
    opt.value = attr.name;
    opt.textContent = attr.name;
    select.appendChild(opt);
  }
}

// ─── Wire UI ──────────────────────────────────────────────────────────────────
// All event listeners in one place.
// Dependencies are injected — ui.js never imports from viewer.js,
// pointcloud.js, or terrain.js directly. It calls the functions
// passed in via the handlers object.

/**
 * Wires all UI controls to their handlers.
 *
 * @param {object} handlers
 * @param {object} handlers.instance      - Giro3D instance (for notifyChange)
 * @param {object} handlers.entity        - PointCloud entity
 * @param {object} handlers.source        - COPCSource
 * @param {object} handlers.colorMap      - shared ColorMap instance
 * @param {Set}    handlers.hiddenClasses - mutable hidden class set
 * @param {function} handlers.onEDL          - (enabled: bool) => void
 * @param {function} handlers.onInpainting   - (enabled: bool) => void
 * @param {function} handlers.onPointSize    - (size: number) => void
 * @param {function} handlers.onAttribute    - (name: string) => void
 * @param {function} handlers.onClassFilter  - (filters: object[]|null) => void
 */
export function wireUI(handlers) {
  const {
    instance,
    entity,
    source,
    colorMap,
    hiddenClasses,
    onEDL,
    onInpainting,
    onPointSize,
    onAttribute,
    onClassFilter,
  } = handlers;

  // ── EDL toggle ──────────────────────────────────────────────────────────
  document.getElementById("edl-toggle")
    ?.addEventListener("change", (e) => onEDL(e.target.checked));

  // ── Inpainting toggle ────────────────────────────────────────────────────
  document.getElementById("inpaint-toggle")
    ?.addEventListener("change", (e) => onInpainting(e.target.checked));

  // ── Point size slider ────────────────────────────────────────────────────
  document.getElementById("point-size")
    ?.addEventListener("input", (e) => {
      const v = Number(e.target.value);
      const label = document.getElementById("point-size-label");
      if (label) label.textContent = v === 0 ? "auto" : v;
      onPointSize(v);
    });

  // ── Attribute selector ───────────────────────────────────────────────────
  document.getElementById("attribute-select")
    ?.addEventListener("change", (e) => onAttribute(e.target.value));

  // ── Colour ramp selector ─────────────────────────────────────────────────
  document.getElementById("ramp-select")
    ?.addEventListener("change", (e) => {
      colorMap.colors = makeColorRamp(e.target.value);
      instance.notifyChange(entity);
    });
}

// ─── Classification panel ─────────────────────────────────────────────────────

/**
 * Builds the full ASPRS classification panel.
 * Called after load — needs the entity to know which classes are present.
 *
 * @param {Set<number>} hiddenClasses - mutable hidden class set
 * @param {number[]} presentCodes - class codes actually in this file
 * @param {function} onClassFilter - callback when filter changes
 */
export function buildClassificationPanel(hiddenClasses, presentCodes, onClassFilter) {
  const container = document.getElementById("classification-list");
  if (!container) return;

  const presentSet = new Set(presentCodes);
  container.innerHTML = "";

  for (const { code, label } of ASPRS_CLASSES) {
    const present = presentSet.has(code);
    const hidden  = hiddenClasses.has(code);

    const row = document.createElement("div");
    row.className = "class-row" + (present ? "" : " class-absent");

    row.innerHTML = `
      <label class="class-label">
        <input
          type="checkbox"
          data-code="${code}"
          ${present ? "" : "disabled"}
          ${!hidden && present ? "checked" : ""}
        />
        <span class="class-code">${code}</span>
        <span class="class-name">${label}</span>
      </label>
    `;

    const checkbox = row.querySelector("input");
    checkbox.addEventListener("change", (e) => {
      setClassVisibility(hiddenClasses, code, !e.target.checked);
      onClassFilter(buildClassificationFilter(hiddenClasses));
    });

    container.appendChild(row);
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const nf = new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 });

function fmt(n) {
  if (n >= 1_000_000) return nf.format(n / 1_000_000) + "M";
  if (n >= 1_000)     return nf.format(n / 1_000) + "K";
  return String(n);
}