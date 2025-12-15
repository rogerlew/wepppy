/**
 * Shared colormap + normalization helpers for gl-dashboard overlays.
 * Pure helpers: no DOM/deck access.
 */

const MODE_COLORMAP = {
  // Landuse cover (fractions or percentages)
  cancov: 'viridis',
  inrcov: 'viridis',
  rilcov: 'viridis',
  // Soils (percentages or bounded scalars)
  clay: 'viridis',
  sand: 'viridis',
  rock: 'viridis',
  bd: 'viridis',
  soil_depth: 'viridis',
  // WEPP Event
  event_ET: 'viridis',
};

function clamp01(v) {
  return Math.min(1, Math.max(0, v));
}

function normalizeFractionOrPercent(value) {
  if (!Number.isFinite(value)) return null;
  const scaled = Math.abs(value) <= 1 ? value : value / 100;
  return clamp01(scaled);
}

function normalizeBulkDensity(value) {
  if (!Number.isFinite(value)) return null;
  // Typical bounds 0.8–2.2 g/cm3 (centered to use full scale)
  return clamp01((value - 0.8) / 1.4);
}

function normalizeSoilDepth(value) {
  if (!Number.isFinite(value)) return null;
  // Cap at 2000 mm to avoid single deep horizons dominating the scale
  return clamp01(Math.min(value, 2000) / 2000);
}

const MODE_NORMALIZERS = {
  cancov: normalizeFractionOrPercent,
  inrcov: normalizeFractionOrPercent,
  rilcov: normalizeFractionOrPercent,
  clay: normalizeFractionOrPercent,
  sand: normalizeFractionOrPercent,
  rock: normalizeFractionOrPercent,
  bd: normalizeBulkDensity,
  soil_depth: normalizeSoilDepth,
};

export function normalizeModeValue(mode, value) {
  const fn = MODE_NORMALIZERS[mode];
  if (!fn) return null;
  return fn(value);
}

export function resolveColormapName(mode, category, constants = {}) {
  const { WATER_MEASURES = [], SOIL_MEASURES = [] } = constants;
  if (MODE_COLORMAP[mode]) return MODE_COLORMAP[mode];
  if (category === 'WATAR') return 'jet2';
  if (WATER_MEASURES.includes(mode)) return 'winter';
  if (SOIL_MEASURES.includes(mode)) return 'jet2';
  return 'viridis';
}

export { MODE_COLORMAP };
