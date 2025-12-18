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

const HEX_RGB_RE = /^#?([0-9a-f]{6})$/i;
const RGBA_RE = /^rgba?\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*(?:,\s*([0-9.]+)\s*)?\)$/i;
const soilColorCache = new Map();

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

export function hslToHex(h, s, l) {
  const sat = s / 100;
  const light = l / 100;
  const a = sat * Math.min(light, 1 - light);
  const f = (n) => {
    const k = (n + h / 30) % 12;
    const color = light - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
    return Math.round(255 * color)
      .toString(16)
      .padStart(2, '0');
  };
  return `#${f(0)}${f(8)}${f(4)}`;
}

export function soilColorForValue(value) {
  if (!Number.isFinite(value)) return null;
  if (soilColorCache.has(value)) {
    return soilColorCache.get(value);
  }
  const v = Math.abs(Math.trunc(value));
  const hue = ((v * 2654435761) >>> 0) % 360; // Knuth hash for spread
  const sat = 50 + (((v * 1013904223) >>> 0) % 30); // 50-79
  const light = 45 + (((v * 1664525) >>> 0) % 20); // 45-64
  const hex = hslToHex(hue, sat, light);
  soilColorCache.set(value, hex);
  return hex;
}

export function hexToRgbaArray(hex, alpha = 230) {
  const parsed = HEX_RGB_RE.exec(hex || '');
  if (!parsed) return null;
  const intVal = parseInt(parsed[1], 16);
  return [(intVal >> 16) & 255, (intVal >> 8) & 255, intVal & 255, alpha];
}

export function rgbaStringToArray(str, alphaOverride) {
  const match = RGBA_RE.exec(str || '');
  if (!match) return null;
  const r = Number(match[1]);
  const g = Number(match[2]);
  const b = Number(match[3]);
  const aRaw = match[4];
  if (![r, g, b].every(Number.isFinite)) return null;
  const a = Number.isFinite(Number(aRaw)) ? Number(aRaw) * 255 : 255;
  const finalA = Number.isFinite(alphaOverride) ? alphaOverride : a;
  return [Math.round(r), Math.round(g), Math.round(b), Math.round(finalA)];
}

export function normalizeColorEntry(entry, alpha = 230) {
  if (!entry) return null;
  if (Array.isArray(entry)) {
    if (entry.length === 4 && entry.every((v) => Number.isFinite(Number(v)))) {
      const r = Number(entry[0]);
      const g = Number(entry[1]);
      const b = Number(entry[2]);
      let a = Number(entry[3]);
      if (a <= 1) {
        a = a * 255;
      }
      if (a >= 254) {
        a = alpha;
      }
      return [r, g, b, Math.round(a)];
    }
  } else if (typeof entry === 'string') {
    const hex = hexToRgbaArray(entry, alpha);
    if (hex) return hex;
    const rgba = rgbaStringToArray(entry, alpha);
    if (rgba) return rgba;
  }
  return null;
}

export function viridisColor(val, scale) {
  const v = Math.min(1, Math.max(0, Number(val)));
  if (scale && typeof scale.map === 'function') {
    const mapped = scale.map(v);
    const rgba = normalizeColorEntry(mapped, 230);
    if (rgba) return rgba;
  }
  if (scale && Array.isArray(scale) && scale.length) {
    const idx = Math.min(scale.length - 1, Math.floor(v * (scale.length - 1)));
    const color = scale[idx];
    const rgba = normalizeColorEntry(color, 230);
    if (rgba) return rgba;
  }
  const start = [68, 1, 84];
  const end = [253, 231, 37];
  return [
    Math.round(start[0] + (end[0] - start[0]) * v),
    Math.round(start[1] + (end[1] - start[1]) * v),
    Math.round(start[2] + (end[2] - start[2]) * v),
    230,
  ];
}

export function winterColor(val, scale) {
  const v = Math.min(1, Math.max(0, Number(val)));
  if (scale && typeof scale.map === 'function') {
    const mapped = scale.map(v);
    const rgba = normalizeColorEntry(mapped, 230);
    if (rgba) return rgba;
  }
  if (scale && Array.isArray(scale) && scale.length) {
    const idx = Math.min(scale.length - 1, Math.floor(v * (scale.length - 1)));
    const color = scale[idx];
    const rgba = normalizeColorEntry(color, 230);
    if (rgba) return rgba;
  }
  return [
    0,
    Math.round(v * 255),
    Math.round(255 - v * 127),
    230,
  ];
}

export function jet2Color(val, scale) {
  const v = Math.min(1, Math.max(0, Number(val)));
  if (scale && typeof scale.map === 'function') {
    const mapped = scale.map(v);
    const rgba = normalizeColorEntry(mapped, 230);
    if (rgba) return rgba;
  }
  if (scale && Array.isArray(scale) && scale.length) {
    const idx = Math.min(scale.length - 1, Math.floor(v * (scale.length - 1)));
    const color = scale[idx];
    const rgba = normalizeColorEntry(color, 230);
    if (rgba) return rgba;
  }
  if (v < 0.5) {
    const t = v * 2;
    return [
      Math.round(255 * t),
      255,
      Math.round(255 * (1 - t)),
      230,
    ];
  }
  const t = (v - 0.5) * 2;
  return [
    255,
    Math.round(255 * (1 - t)),
    0,
    230,
  ];
}

export function divergingColor(normalizedDiff, scale) {
  const v = Math.min(1, Math.max(0, (normalizedDiff + 1) / 2));
  if (scale && typeof scale.map === 'function') {
    const mapped = scale.map(v);
    const rgba = normalizeColorEntry(mapped, 230);
    if (rgba) return rgba;
  }
  if (scale && Array.isArray(scale) && scale.length) {
    const idx = Math.min(scale.length - 1, Math.floor(v * (scale.length - 1)));
    const color = scale[idx];
    const rgba = normalizeColorEntry(color, 230);
    if (rgba) return rgba;
  }
  if (normalizedDiff < 0) {
    const t = normalizedDiff + 1;
    return [
      Math.round(33 + (255 - 33) * t),
      Math.round(102 + (255 - 102) * t),
      Math.round(172 + (255 - 172) * t),
      230,
    ];
  }
  const t = normalizedDiff;
  return [
    255,
    Math.round(255 - (255 - 102) * t),
    Math.round(255 - (255 - 94) * t),
    230,
  ];
}

export function rdbuColor(normalized, scale) {
  const clamped = Math.min(1, Math.max(0, Number(normalized)));
  return divergingColor(clamped * 2 - 1, scale);
}

function makeScale(colormapFn, name) {
  if (typeof colormapFn === 'function') {
    try {
      return colormapFn({ colormap: name, nshades: 256, format: 'rgba' });
    } catch (err) {
      return null;
    }
  }
  return null;
}

export function createColorScales(colormapFn) {
  const viridisScale = makeScale(colormapFn, 'viridis');
  const rdbuScale = makeScale(colormapFn, 'rdbu');
  const winterScale = makeScale(colormapFn, 'winter');
  const jet2Scale = makeScale(colormapFn, 'jet2');

  return {
    viridisScale,
    rdbuScale,
    winterScale,
    jet2Scale,
    viridisColor: (val) => viridisColor(val, viridisScale),
    winterColor: (val) => winterColor(val, winterScale),
    jet2Color: (val) => jet2Color(val, jet2Scale),
    divergingColor: (val) => divergingColor(val, rdbuScale),
    rdbuColor: (val) => rdbuColor(val, rdbuScale),
  };
}

export { MODE_COLORMAP };
