// src/filters.js
// ─────────────────────────────────────────────────────────────────────────────
// Classification filter logic.
// Viewer-agnostic — works with plain Sets and filter spec objects.
// The caller is responsible for pushing specs to source.filters.
// ─────────────────────────────────────────────────────────────────────────────

// Default hidden classes on load.
// ASPRS class 18 = high noise.
const DEFAULT_HIDDEN = [18];

/**
 * Creates a mutable set of hidden classification codes.
 * @param {number[]} initial - class codes to hide on startup
 * @returns {Set<number>}
 */
export function createHiddenSet(initial = DEFAULT_HIDDEN) {
  return new Set(initial);
}

/**
 * Full ASPRS classification table.
 * Source: LAS 1.4 spec.
 * Only classes present in the file will be visible — the rest are greyed out.
 */
export const ASPRS_CLASSES = [
  { code: 0,  label: "Created, never classified" },
  { code: 1,  label: "Unclassified" },
  { code: 2,  label: "Ground" },
  { code: 3,  label: "Low vegetation" },
  { code: 4,  label: "Medium vegetation" },
  { code: 5,  label: "High vegetation" },
  { code: 6,  label: "Building" },
  { code: 7,  label: "Low point (noise)" },
  { code: 8,  label: "Reserved" },
  { code: 9,  label: "Water" },
  { code: 10, label: "Rail" },
  { code: 11, label: "Road surface" },
  { code: 12, label: "Reserved" },
  { code: 13, label: "Wire — guard" },
  { code: 14, label: "Wire — conductor" },
  { code: 15, label: "Transmission tower" },
  { code: 16, label: "Wire connector" },
  { code: 17, label: "Bridge deck" },
  { code: 18, label: "High noise" },
];

/**
 * Builds a filter spec from the current hidden set.
 * Returns null if nothing is hidden (disables filtering).
 *
 * The spec shape matches Giro3D's source.filters API today.
 * If you swap viewers, replace this function — callers don't change.
 *
 * @param {Set<number>} hiddenClasses
 * @returns {object[]|null}
 */
export function buildClassificationFilter(hiddenClasses) {
  if (hiddenClasses.size === 0) return null;

  return [{
    dimension: "Classification",
    operator: "not_in",
    values: new Set(hiddenClasses),
  }];
}

/**
 * Adds a class code to the hidden set.
 * @param {Set<number>} hiddenClasses
 * @param {number} code
 */
export function hideClass(hiddenClasses, code) {
  hiddenClasses.add(code);
}

/**
 * Removes a class code from the hidden set.
 * @param {Set<number>} hiddenClasses
 * @param {number} code
 */
export function showClass(hiddenClasses, code) {
  hiddenClasses.delete(code);
}

/**
 * Toggles a class code in the hidden set.
 * @param {Set<number>} hiddenClasses
 * @param {number} code
 * @param {boolean} hidden
 */
export function setClassVisibility(hiddenClasses, code, hidden) {
  hidden ? hiddenClasses.add(code) : hiddenClasses.delete(code);
}