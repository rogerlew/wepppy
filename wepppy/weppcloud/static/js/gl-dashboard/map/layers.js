/**
 * Deck layer builders, color/value helpers, and tooltip/legend utilities for gl-dashboard.
 * Pure functions: no DOM access. Consumers supply deck and state accessors.
 */

import { normalizeModeValue, resolveColormapName } from '../colors.js';
import { DASHBOARD_MODES } from '../batch-keys.js';
import { landuseValue, soilsValue, modeValue, scalarValue, weppEventValue, pickActive, resolveFeatureIdentity } from './layer-values.js';
import { formatLayerTooltip } from './layer-tooltips.js';

const CHANNEL_ORDER_COLORS = [
  '#8AE5FE',
  '#65C8FE',
  '#479EFF',
  '#306EFE',
  '#2500F4',
  '#6600cc',
  '#50006b',
  '#6b006b',
];
const CHANNEL_LINE_OPACITY = 0.6;
const CHANNEL_FILL_OPACITY = 0.9;
const CHANNEL_DEFAULT_ORDER = 4;
const CHANNEL_MAX_ORDER = 7;
const LABEL_FONT_FAMILY = 'system-ui, -apple-system, sans-serif';
const LABEL_FONT_WEIGHT = '600';
const SUBCATCHMENT_LABEL_FONT_SIZE = 12;
const SUBCATCHMENT_LABEL_OUTLINE_WIDTH = 2;
const CHANNEL_LABEL_OUTLINE_WIDTH = 2;
const CHANNEL_LABEL_FONT_SIZE = 13;
const LABEL_OUTLINE_ALPHA = 245;
const LABEL_MIN_CONTRAST_RATIO = 4.5;
const LABEL_TARGET_CONTRAST_RATIO = 5;
const FALLBACK_LABEL_THEME = Object.freeze({
  textColor: [95, 105, 120, 255],
  outlineColor: [255, 255, 255, LABEL_OUTLINE_ALPHA],
});
let cachedLabelThemeSignature = null;
let cachedLabelTheme = null;
const D8_DIRECTION_COLOR = [255, 105, 180, 230];
const D8_DIRECTION_ICON_SVG =
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><path fill="white" d="M8 29.5H38.4V22L56 32L38.4 42V34.5H8Z"/></svg>';
const D8_DIRECTION_ICON_ATLAS = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(D8_DIRECTION_ICON_SVG)}`;
const D8_DIRECTION_ICON_MAPPING = Object.freeze({
  arrow: { x: 0, y: 0, width: 64, height: 64, mask: true },
});
const D8_DIRECTION_ICON_ID = 'arrow';
const SBS_CLASS_DEFINITIONS = Object.freeze({
  130: Object.freeze({ label: 'Unchanged / Unburned', standard: [0, 128, 128], shifted: [0, 158, 115] }),
  131: Object.freeze({ label: 'Low Severity Burn', standard: [82, 204, 204], shifted: [86, 180, 233] }),
  132: Object.freeze({ label: 'Moderate Severity Burn', standard: [255, 232, 32], shifted: [240, 228, 66] }),
  133: Object.freeze({ label: 'High Severity Burn', standard: [168, 0, 0], shifted: [204, 121, 167] }),
});
const SBS_UNASSIGNED_RGB = Object.freeze([128, 0, 152]);
const SBS_RGB_TO_CLASS = Object.freeze({
  '46_203_24': 130, '161_250_220': 131, '255_161_5': 132, '217_34_3': 133,
  '0_115_74': 130, '77_230_0': 131, '255_255_0': 132, '255_0_0': 133,
  '0_128_128': 130, '82_204_204': 131, '255_232_32': 132, '168_0_0': 133,
});
const SBS_PACKED_RGB_TO_CLASS = Object.freeze(Object.entries(SBS_RGB_TO_CLASS).reduce((lookup, [key, classCode]) => {
  const channels = key.split('_').map(Number);
  lookup[(channels[0] << 16) | (channels[1] << 8) | channels[2]] = classCode;
  return lookup;
}, {}));

function isRapOverlayActive(state) {
  if (!state || typeof state !== 'object') return false;
  if (state.rapCumulativeMode) return true;
  const rapLayers = Array.isArray(state.rapLayers) ? state.rapLayers : [];
  return rapLayers.some((layer) => layer && layer.visible);
}

function hexToRgba(hex, alpha) {
  const normalized = String(hex || '').replace('#', '');
  const expanded = normalized.length === 3
    ? normalized[0] + normalized[0] + normalized[1] + normalized[1] + normalized[2] + normalized[2]
    : normalized;
  const intVal = Number.parseInt(expanded, 16);
  if (!Number.isFinite(intVal)) {
    return [0, 0, 0, Math.round(alpha * 255)];
  }
  return [(intVal >> 16) & 255, (intVal >> 8) & 255, intVal & 255, Math.round(alpha * 255)];
}

function clampByte(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return null;
  return Math.max(0, Math.min(255, Math.round(num)));
}

function clampUnitInterval(value) {
  if (!Number.isFinite(value)) return null;
  return Math.max(0, Math.min(1, value));
}

function parseHexColor(raw) {
  const hex = String(raw || '').trim().replace('#', '');
  if (![3, 4, 6, 8].includes(hex.length)) return null;
  const expanded = hex.length <= 4
    ? hex.split('').map((ch) => ch + ch).join('')
    : hex;
  if (expanded.length === 6) {
    const intVal = Number.parseInt(expanded, 16);
    if (!Number.isFinite(intVal)) return null;
    return [(intVal >> 16) & 255, (intVal >> 8) & 255, intVal & 255, 255];
  }
  const r = Number.parseInt(expanded.slice(0, 2), 16);
  const g = Number.parseInt(expanded.slice(2, 4), 16);
  const b = Number.parseInt(expanded.slice(4, 6), 16);
  const a = Number.parseInt(expanded.slice(6, 8), 16);
  if (![r, g, b, a].every(Number.isFinite)) return null;
  return [r, g, b, a];
}

function parseRgbComponent(part) {
  const value = String(part || '').trim();
  if (!value) return null;
  if (value.endsWith('%')) {
    const pct = Number.parseFloat(value.slice(0, -1));
    if (!Number.isFinite(pct)) return null;
    return clampByte((pct / 100) * 255);
  }
  return clampByte(Number.parseFloat(value));
}

function parseAlphaComponent(part) {
  const value = String(part || '').trim();
  if (!value) return null;
  if (value.endsWith('%')) {
    const pct = Number.parseFloat(value.slice(0, -1));
    if (!Number.isFinite(pct)) return null;
    return clampUnitInterval(pct / 100);
  }
  const num = Number.parseFloat(value);
  if (!Number.isFinite(num)) return null;
  if (num > 1) {
    return clampUnitInterval(num / 255);
  }
  return clampUnitInterval(num);
}

function parseRgbColor(raw) {
  const match = String(raw || '').trim().match(/^rgba?\((.*)\)$/i);
  if (!match) return null;
  const body = match[1].trim();
  if (!body) return null;
  let alphaPart = null;
  let rgbPart = body;
  if (body.includes('/')) {
    const split = body.split('/');
    if (split.length !== 2) return null;
    rgbPart = split[0].trim();
    alphaPart = split[1].trim();
  }
  let rgbParts;
  if (rgbPart.includes(',')) {
    rgbParts = rgbPart.split(',').map((s) => s.trim()).filter(Boolean);
  } else {
    rgbParts = rgbPart.split(/\s+/).filter(Boolean);
  }
  if (rgbParts.length < 3) return null;
  if (rgbParts.length > 3 && alphaPart == null) {
    alphaPart = rgbParts[3];
  }
  const r = parseRgbComponent(rgbParts[0]);
  const g = parseRgbComponent(rgbParts[1]);
  const b = parseRgbComponent(rgbParts[2]);
  if (![r, g, b].every(Number.isFinite)) return null;
  const alpha = alphaPart == null ? 1 : parseAlphaComponent(alphaPart);
  if (!Number.isFinite(alpha)) return null;
  return [r, g, b, Math.round(alpha * 255)];
}

function parseCssColor(raw) {
  const value = String(raw || '').trim();
  if (!value) return null;
  if (value.startsWith('#')) return parseHexColor(value);
  if (value.toLowerCase().startsWith('rgb')) return parseRgbColor(value);
  return null;
}

function compositeRgbaOverRgb(colorRgba, backgroundRgb) {
  if (!Array.isArray(colorRgba) || colorRgba.length < 4) return backgroundRgb.slice();
  const alpha = clampUnitInterval((colorRgba[3] || 0) / 255);
  if (alpha == null) return backgroundRgb.slice();
  const inv = 1 - alpha;
  return [
    Math.round(colorRgba[0] * alpha + backgroundRgb[0] * inv),
    Math.round(colorRgba[1] * alpha + backgroundRgb[1] * inv),
    Math.round(colorRgba[2] * alpha + backgroundRgb[2] * inv),
  ];
}

function relativeLuminance(rgb) {
  const channels = rgb.map((channel) => {
    const s = channel / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
}

function contrastRatio(a, b) {
  const l1 = relativeLuminance(a);
  const l2 = relativeLuminance(b);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

function blendRgb(foreground, background, backgroundWeight) {
  const weight = clampUnitInterval(backgroundWeight);
  if (weight == null) return foreground.slice();
  const fgWeight = 1 - weight;
  return [
    Math.round(foreground[0] * fgWeight + background[0] * weight),
    Math.round(foreground[1] * fgWeight + background[1] * weight),
    Math.round(foreground[2] * fgWeight + background[2] * weight),
  ];
}

function pickAccessibleTextColor({ mutedRgb, textRgb, surfaceRgb }) {
  const candidates = [
    mutedRgb,
    textRgb,
    FALLBACK_LABEL_THEME.textColor.slice(0, 3),
    [17, 24, 39],
    [255, 255, 255],
  ].filter((c) => Array.isArray(c) && c.length === 3);
  let bestColor = FALLBACK_LABEL_THEME.textColor.slice(0, 3);
  let bestContrast = 0;
  for (const candidate of candidates) {
    const ratio = contrastRatio(candidate, surfaceRgb);
    if (ratio > bestContrast) {
      bestContrast = ratio;
      bestColor = candidate;
    }
    if (ratio >= LABEL_MIN_CONTRAST_RATIO) {
      return candidate;
    }
  }
  return bestColor;
}

function reduceContrastToTarget(textRgb, surfaceRgb) {
  const currentContrast = contrastRatio(textRgb, surfaceRgb);
  if (currentContrast <= LABEL_TARGET_CONTRAST_RATIO) return textRgb;
  let low = 0;
  let high = 1;
  let best = textRgb;
  for (let i = 0; i < 16; i += 1) {
    const mid = (low + high) / 2;
    const candidate = blendRgb(textRgb, surfaceRgb, mid);
    const ratio = contrastRatio(candidate, surfaceRgb);
    if (ratio >= LABEL_TARGET_CONTRAST_RATIO) {
      low = mid;
      best = candidate;
    } else {
      high = mid;
    }
  }
  if (contrastRatio(best, surfaceRgb) < LABEL_MIN_CONTRAST_RATIO) return textRgb;
  return best;
}

function resolveLabelThemeStyles() {
  if (typeof document === 'undefined' || typeof getComputedStyle !== 'function' || !document.documentElement) {
    return FALLBACK_LABEL_THEME;
  }
  const rootStyle = getComputedStyle(document.documentElement);
  const mutedRaw = rootStyle.getPropertyValue('--wc-color-text-muted').trim();
  const textRaw = rootStyle.getPropertyValue('--wc-color-text').trim();
  const surfaceRaw = rootStyle.getPropertyValue('--wc-color-surface').trim();
  const surfaceAltRaw = rootStyle.getPropertyValue('--wc-color-surface-alt').trim();
  const pageRaw = rootStyle.getPropertyValue('--wc-color-page').trim();
  const signature = [mutedRaw, textRaw, surfaceRaw, surfaceAltRaw, pageRaw].join('|');
  if (cachedLabelThemeSignature === signature && cachedLabelTheme) {
    return cachedLabelTheme;
  }
  const fallbackSurfaceRgb = FALLBACK_LABEL_THEME.outlineColor.slice(0, 3);
  const pageColor = parseCssColor(pageRaw) || parseCssColor(surfaceAltRaw) || [...fallbackSurfaceRgb, 255];
  const pageRgb = compositeRgbaOverRgb(pageColor, fallbackSurfaceRgb);
  const surfaceColor = parseCssColor(surfaceRaw) || parseCssColor(surfaceAltRaw) || [...fallbackSurfaceRgb, 255];
  const surfaceRgb = compositeRgbaOverRgb(surfaceColor, pageRgb);
  const mutedColor = parseCssColor(mutedRaw);
  const textColor = parseCssColor(textRaw);
  const mutedRgb = mutedColor ? compositeRgbaOverRgb(mutedColor, surfaceRgb) : null;
  const textRgb = textColor ? compositeRgbaOverRgb(textColor, surfaceRgb) : null;
  const chosenText = pickAccessibleTextColor({ mutedRgb, textRgb, surfaceRgb });
  const tunedText = reduceContrastToTarget(chosenText, surfaceRgb);
  cachedLabelTheme = {
    textColor: [...tunedText, 255],
    outlineColor: [...surfaceRgb, LABEL_OUTLINE_ALPHA],
  };
  cachedLabelThemeSignature = signature;
  return cachedLabelTheme;
}

function getSbsRgbKey(r, g, b) {
  return `${r}_${g}_${b}`;
}

function mapSbsRgbForDisplay(r, g, b, shifted) {
  const classCode = SBS_RGB_TO_CLASS[getSbsRgbKey(r, g, b)] || null;
  if (classCode === null) return [...SBS_UNASSIGNED_RGB];
  return [...SBS_CLASS_DEFINITIONS[classCode][shifted ? 'shifted' : 'standard']];
}

function decodeSbsPixel(r, g, b) {
  const classCode = SBS_PACKED_RGB_TO_CLASS[(r << 16) | (g << 8) | b] || null;
  return classCode === null
    ? { classCode: null, label: 'Unassigned', unassigned: true }
    : { classCode, label: SBS_CLASS_DEFINITIONS[classCode].label, unassigned: false };
}

function getSbsLegendItems(shifted, unassignedCount = 0) {
  const palette = shifted ? 'shifted' : 'standard';
  const items = Object.entries(SBS_CLASS_DEFINITIONS).map(([key, definition]) => ({
    key: Number(key),
    color: `rgb(${definition[palette].join(', ')})`,
    label: `${definition.label} (${key})`,
  }));
  items.push({ key: 'unassigned', color: 'rgb(128, 0, 152)', label: `Unassigned: ${Number(unassignedCount) || 0}` });
  items.push({ key: 255, color: '#FFFFFF', label: 'Masked / Unmappable (255)', masked: true });
  return items;
}

function recolorSbsPixels(data, shifted) {
  const palette = shifted ? 'shifted' : 'standard';
  let unassignedPixelCount = 0;
  for (let i = 0; i < data.length; i += 4) {
    if (data[i + 3] === 0) continue;
    const classCode = SBS_PACKED_RGB_TO_CLASS[(data[i] << 16) | (data[i + 1] << 8) | data[i + 2]] || null;
    const mapped = classCode === null ? SBS_UNASSIGNED_RGB : SBS_CLASS_DEFINITIONS[classCode][palette];
    if (classCode === null) unassignedPixelCount += 1;
    data[i] = mapped[0];
    data[i + 1] = mapped[1];
    data[i + 2] = mapped[2];
    data[i + 3] = 255;
  }
  return unassignedPixelCount;
}

function getSbsDisplayCanvas(layer, shifted) {
  if (!layer || !layer.canvas) return null;

  const sourceCanvas = layer.canvas;
  const sourceWidth = Number(sourceCanvas.width);
  const sourceHeight = Number(sourceCanvas.height);
  if (!Number.isFinite(sourceWidth) || !Number.isFinite(sourceHeight) || sourceWidth <= 0 || sourceHeight <= 0) {
    throw new Error('Unable to decode SBS canvas with invalid dimensions.');
  }
  if (
    layer._sbsDisplayCanvas &&
    layer._sbsDisplayMode === shifted &&
    layer._sbsDisplayCanvas.width === sourceCanvas.width &&
    layer._sbsDisplayCanvas.height === sourceCanvas.height
  ) {
    return layer._sbsDisplayCanvas;
  }

  const canvas = document.createElement('canvas');
  canvas.width = sourceCanvas.width;
  canvas.height = sourceCanvas.height;
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('Unable to access SBS decode canvas context.');

  ctx.drawImage(sourceCanvas, 0, 0);
  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const data = imageData.data;
  const unassignedPixelCount = recolorSbsPixels(data, shifted);
  ctx.putImageData(imageData, 0, 0);
  layer.sbsUnassignedCount = unassignedPixelCount;
  layer._sbsDisplayCanvas = canvas;
  layer._sbsDisplayMode = shifted;
  return canvas;
}

const CHANNEL_LINE_PALETTE = CHANNEL_ORDER_COLORS.map((color) => hexToRgba(color, CHANNEL_LINE_OPACITY));
const CHANNEL_FILL_PALETTE = CHANNEL_ORDER_COLORS.map((color) => hexToRgba(color, CHANNEL_FILL_OPACITY));

function resolveChannelOrder(feature) {
  if (!feature || !feature.properties) return CHANNEL_DEFAULT_ORDER;
  const raw = Number.parseInt(feature.properties.Order, 10);
  if (!Number.isFinite(raw)) return CHANNEL_DEFAULT_ORDER;
  return Math.max(0, Math.min(CHANNEL_MAX_ORDER, raw));
}

function getChannelLineColor(feature) {
  const order = resolveChannelOrder(feature);
  return CHANNEL_LINE_PALETTE[order] || CHANNEL_LINE_PALETTE[CHANNEL_DEFAULT_ORDER];
}

function getChannelFillColor(feature) {
  const order = resolveChannelOrder(feature);
  return CHANNEL_FILL_PALETTE[order] || CHANNEL_FILL_PALETTE[CHANNEL_DEFAULT_ORDER];
}

function buildChannelLegendItems() {
  const items = [];
  for (let i = 1; i < CHANNEL_ORDER_COLORS.length; i += 1) {
    items.push({ color: CHANNEL_ORDER_COLORS[i], label: `Order ${i}` });
  }
  return items;
}

export function createLayerUtils({
  deck,
  getState,
  colorScales,
  constants,
}) {
  const { viridisColor, winterColor, jet2Color, plasmaColor = viridisColor, rdbuScale } = colorScales;
  const { WATER_MEASURES, SOIL_MEASURES, NLCD_COLORMAP, NLCD_LABELS, RAP_BAND_LABELS } = constants;

  function colorFromPalette(name, normalized) {
    if (name === 'winter') return winterColor(normalized);
    if (name === 'jet2') return jet2Color(normalized);
    if (name === 'plasma') return plasmaColor(normalized);
    if (name === 'viridis') return viridisColor(normalized);
    // Fallback to viridis to avoid silent gray fills if a palette is added without support.
    return viridisColor(normalized);
  }

  function landuseFillColor(mode, row) {
    if (!row) return [128, 128, 128, 200];
    if (mode === 'dominant') {
      // First check if the row has a color field (for custom landuses like Disturbed)
      if (row.color) {
        const hex = row.color.replace('#', '');
        const intVal = Number.parseInt(hex, 16);
        if (Number.isFinite(intVal)) {
          return [(intVal >> 16) & 255, (intVal >> 8) & 255, intVal & 255, 220];
        }
      }
      // Fall back to NLCD colormap for standard land cover codes
      const key = row.key ?? row._map;
      if (key == null) return [128, 128, 128, 200];
      const parsed = Number.parseInt(key, 10);
      if (!Number.isFinite(parsed)) return [128, 128, 128, 200];
      const hex = NLCD_COLORMAP[parsed];
      if (!hex) return [128, 128, 128, 200];
      const intVal = Number.parseInt(hex.replace('#', ''), 16);
      return [(intVal >> 16) & 255, (intVal >> 8) & 255, intVal & 255, 220];
    }
    const v = Number(row[mode]);
    const normalized = normalizeModeValue(mode, v);
    if (!Number.isFinite(normalized)) return [128, 128, 128, 200];
    const palette = resolveColormapName(mode, 'Landuse', { WATER_MEASURES, SOIL_MEASURES });
    return colorFromPalette(palette, normalized);
  }

  function landuseComparisonFillColor(mode, scenarioRow, baseRow) {
    const state = getState();
    if (!scenarioRow || !baseRow) return [128, 128, 128, 200];
    const scenarioValue = Number(scenarioRow[mode]);
    const baseValue = Number(baseRow[mode]);
    if (!Number.isFinite(scenarioValue) || !Number.isFinite(baseValue)) {
      return [128, 128, 128, 200];
    }
    const diff = baseValue - scenarioValue;
    const usePercentScale = Math.abs(baseValue) > 1 || Math.abs(scenarioValue) > 1;
    const range = state.comparisonDiffRanges[mode] || { min: usePercentScale ? -50 : -1, max: usePercentScale ? 50 : 1 };
    const normalized = Math.min(1, Math.max(0, (diff - range.min) / (range.max - range.min || 1)));
    return rdbuScale(normalized);
  }

  function landuseColor(mode, row, topazId) {
    const state = getState();
    if (state.comparisonMode && state.currentScenarioPath && state.baseSummaryCache.landuse && ['cancov', 'inrcov', 'rilcov'].includes(mode)) {
      const baseRow = topazId != null ? state.baseSummaryCache.landuse[String(topazId)] : null;
      return landuseComparisonFillColor(mode, row, baseRow);
    }
    return landuseFillColor(mode, row);
  }

  function soilsFillColor(mode, row) {
    const state = getState();
    if (!row) return [128, 128, 128, 200];
    if (mode === 'dominant') {
      const key = row.mukey;
      if (!key) return [128, 128, 128, 200];
      const hash = [...String(key)].reduce((acc, ch) => (acc * 31 + ch.charCodeAt(0)) >>> 0, 0);
      const r = (hash & 0xff0000) >> 16;
      const g = (hash & 0x00ff00) >> 8;
      const b = hash & 0x0000ff;
      return [r, g, b, 200];
    }
    const v = Number(row[mode]);
    const normalized = normalizeModeValue(mode, v);
    if (!Number.isFinite(normalized)) return [128, 128, 128, 200];
    const palette = resolveColormapName(mode, 'Soils', { WATER_MEASURES, SOIL_MEASURES });
    return colorFromPalette(palette, normalized);
  }

  function hillslopesFillColor(mode, row) {
    if (!row) return [128, 128, 128, 200];
    const v = Number(row[mode]);
    if (!Number.isFinite(v)) return [128, 128, 128, 200];
    let normalized = 0.5;
    if (mode === 'slope_scalar') {
      normalized = Math.min(1, Math.max(0, v));
    } else if (mode === 'length') {
      normalized = Math.min(1, Math.max(0, v / 1000));
    } else if (mode === 'aspect') {
      normalized = Math.min(1, Math.max(0, v / 360));
    }
    return viridisColor(normalized);
  }

  function watarFillColor(mode, row) {
    const state = getState();
    if (!row) return [128, 128, 128, 200];
    const value = Number(row[mode]);
    if (!Number.isFinite(value)) return [128, 128, 128, 200];
    const range = state.watarRanges[mode] || { min: 0, max: 1 };
    const normalized = Math.min(1, Math.max(0, (value - range.min) / (range.max - range.min)));
    return jet2Color(normalized);
  }

  function weppFillColor(mode, row) {
    const state = getState();
    if (!row) return [128, 128, 128, 200];
    const value = Number(row[mode]);
    if (!Number.isFinite(value)) return [128, 128, 128, 200];
    const range = state.weppRanges[mode] || { min: 0, max: 100 };
    const normalized = Math.min(1, Math.max(0, (value - range.min) / (range.max - range.min)));
    if (WATER_MEASURES.includes(mode)) {
      return winterColor(normalized);
    }
    if (SOIL_MEASURES.includes(mode)) {
      return jet2Color(normalized);
    }
    return viridisColor(normalized);
  }

  function weppChannelFillColor(mode, row) {
    const state = getState();
    if (!row) return [128, 128, 128, 200];
    const value = Number(row[mode]);
    if (!Number.isFinite(value)) return [128, 128, 128, 200];
    const range = state.weppChannelRanges[mode] || { min: 0, max: 1 };
    const normalized = Math.min(1, Math.max(0, (value - range.min) / (range.max - range.min)));
    const palette = resolveColormapName(mode, 'WEPP Channels', { WATER_MEASURES, SOIL_MEASURES });
    return colorFromPalette(palette, normalized);
  }

  function weppYearlyChannelFillColor(mode, row) {
    const state = getState();
    if (!row) return [128, 128, 128, 200];
    const value = Number(row[mode]);
    if (!Number.isFinite(value)) return [128, 128, 128, 200];
    const range = state.weppYearlyChannelRanges[mode] || { min: 0, max: 1 };
    const normalized = Math.min(1, Math.max(0, (value - range.min) / (range.max - range.min)));
    const palette = resolveColormapName(mode, 'WEPP Yearly Channels', { WATER_MEASURES, SOIL_MEASURES });
    return colorFromPalette(palette, normalized);
  }

  function weppComparisonFillColor(mode, scenarioRow, baseRow) {
    const state = getState();
    if (!scenarioRow || !baseRow) return [128, 128, 128, 200];
    const scenarioValue = Number(scenarioRow[mode]);
    const baseValue = Number(baseRow[mode]);
    if (!Number.isFinite(scenarioValue) || !Number.isFinite(baseValue)) {
      return [128, 128, 128, 200];
    }
    const diff = baseValue - scenarioValue;
    const range = state.comparisonDiffRanges[mode] || { min: -100, max: 100 };
    const normalized = Math.min(1, Math.max(0, (diff - range.min) / (range.max - range.min || 1)));
    return rdbuScale(normalized);
  }

  function weppYearlyFillColor(mode, row) {
    const state = getState();
    if (!row) return [128, 128, 128, 200];
    const value = Number(row[mode]);
    if (!Number.isFinite(value)) return [128, 128, 128, 200];
    const range = state.weppYearlyRanges[mode] || { min: 0, max: 100 };
    const normalized = Math.min(1, Math.max(0, (value - range.min) / (range.max - range.min)));
    if (WATER_MEASURES.includes(mode)) {
      return winterColor(normalized);
    }
    if (SOIL_MEASURES.includes(mode)) {
      return jet2Color(normalized);
    }
    return viridisColor(normalized);
  }

  function weppYearlyComparisonFillColor(mode, scenarioRow, baseRow) {
    const state = getState();
    if (!scenarioRow || !baseRow) return [128, 128, 128, 200];
    const scenarioValue = Number(scenarioRow[mode]);
    const baseValue = Number(baseRow[mode]);
    if (!Number.isFinite(scenarioValue) || !Number.isFinite(baseValue)) {
      return [128, 128, 128, 200];
    }
    const diff = baseValue - scenarioValue;
    const range = state.weppYearlyDiffRanges[mode] || { min: -100, max: 100 };
    const normalized = Math.min(1, Math.max(0, (diff - range.min) / (range.max - range.min || 1)));
    return rdbuScale(normalized);
  }

  function weppEventFillColor(mode, row) {
    const state = getState();
    if (!row || (['event_P', 'event_Q', 'event_ET'].includes(mode) && row[mode] == null)) return [128, 128, 128, 200];
    const value = Number(row[mode]);
    if (!Number.isFinite(value)) return [128, 128, 128, 200];
    const range = state.weppEventRanges[mode] || { min: 0, max: 1 };
    const normalized = Math.min(1, Math.max(0, (value - range.min) / (range.max - range.min)));
    const palette = resolveColormapName(mode, 'WEPP Event', { WATER_MEASURES, SOIL_MEASURES });
    return colorFromPalette(palette, normalized);
  }

  function openetFillColor(value) {
    const state = getState();
    if (!Number.isFinite(value)) return [128, 128, 128, 200];
    const range = state.openetRanges || { min: 0, max: 1 };
    const normalized = Math.min(1, Math.max(0, (value - range.min) / (range.max - range.min || 1)));
    return winterColor(normalized);
  }

  function rapFillColor(row) {
    const v = scalarValue(row);
    if (v === null) return [128, 128, 128, 200];
    const normalized = Math.min(1, Math.max(0, v / 100));
    return winterColor(normalized);
  }

  function buildSubcatchmentLabelsLayer(state) {
    if (!state.subcatchmentLabelsVisible || !state.subcatchmentsVisible || !state.subcatchmentsGeoJson) {
      return [];
    }
    const labelTheme = resolveLabelThemeStyles();
    const labelData = [];
    const seenIds = new Set();
    const features = state.subcatchmentsGeoJson.features || [];
    features.forEach((feature) => {
      const props = feature.properties || {};
      const identity = resolveFeatureIdentity(props, state);
      if (!identity.key || identity.topazId == null) return;
      const idKey = String(identity.key);
      if (seenIds.has(idKey)) return;
      seenIds.add(idKey);
      const geom = feature.geometry;
      if (!geom) return;
      let coords = [];
      if (geom.type === 'Polygon' && geom.coordinates && geom.coordinates[0]) {
        coords = geom.coordinates[0];
      } else if (geom.type === 'MultiPolygon' && geom.coordinates && geom.coordinates[0] && geom.coordinates[0][0]) {
        coords = geom.coordinates[0][0];
      }
      if (!coords.length) return;
      let sumX = 0;
      let sumY = 0;
      coords.forEach((pt) => {
        sumX += pt[0];
        sumY += pt[1];
      });
      const centroid = [sumX / coords.length, sumY / coords.length];
      const includeRunLabelInText =
        state.dashboardMode === DASHBOARD_MODES.BATCH && identity.runLabel && !isRapOverlayActive(state);
      const text =
        includeRunLabelInText
          ? `${identity.runLabel}:${identity.topazId}`
          : String(identity.topazId);
      labelData.push({
        position: centroid,
        text,
      });
    });
    return [
      new deck.TextLayer({
        id: 'subcatchment-labels',
        data: labelData,
        getPosition: (d) => d.position,
        getText: (d) => d.text,
        getSize: SUBCATCHMENT_LABEL_FONT_SIZE,
        getColor: labelTheme.textColor,
        getTextAnchor: 'middle',
        getAlignmentBaseline: 'center',
        fontFamily: LABEL_FONT_FAMILY,
        fontWeight: LABEL_FONT_WEIGHT,
        outlineColor: labelTheme.outlineColor,
        outlineWidth: SUBCATCHMENT_LABEL_OUTLINE_WIDTH,
        billboard: false,
        sizeUnits: 'pixels',
        pickable: false,
      }),
    ];
  }

  function buildChannelsLayer(state) {
    const activeChannelOrder = pickActive(state.channelsLayers || []);
    if (!state.channelsVisible || !state.channelsGeoJson || !activeChannelOrder) return [];
    return [
      new deck.GeoJsonLayer({
        id: 'channels-pass2',
        data: state.channelsGeoJson,
        pickable: false,
        stroked: true,
        filled: true,
        lineWidthUnits: 'pixels',
        lineWidthMinPixels: 1,
        getLineWidth: () => 1.5,
        getLineColor: getChannelLineColor,
        getFillColor: getChannelFillColor,
      }),
    ];
  }

  function buildChannelLabelsLayer(state) {
    if (!state.channelLabelsVisible || !state.channelsVisible) return [];
    const labelData = Array.isArray(state.channelLabelsData) ? state.channelLabelsData : [];
    if (!labelData.length) return [];
    const labelTheme = resolveLabelThemeStyles();
    return [
      new deck.TextLayer({
        id: 'channel-labels',
        data: labelData,
        getPosition: (d) => d.position,
        getText: (d) => d.text,
        getSize: CHANNEL_LABEL_FONT_SIZE,
        getColor: labelTheme.textColor,
        getTextAnchor: 'middle',
        getAlignmentBaseline: 'center',
        fontFamily: LABEL_FONT_FAMILY,
        fontWeight: LABEL_FONT_WEIGHT,
        outlineColor: labelTheme.outlineColor,
        outlineWidth: CHANNEL_LABEL_OUTLINE_WIDTH,
        billboard: false,
        sizeUnits: 'pixels',
        pickable: false,
      }),
    ];
  }

  function buildD8DirectionLayer(state) {
    const layer = state.d8DirectionLayer;
    if (!state.subcatchmentsVisible || !layer || !layer.visible || !Array.isArray(layer.data) || !layer.data.length) return [];
    return [
      new deck.IconLayer({
        id: 'd8-direction-arrows',
        data: layer.data,
        iconAtlas: D8_DIRECTION_ICON_ATLAS,
        iconMapping: D8_DIRECTION_ICON_MAPPING,
        getIcon: () => D8_DIRECTION_ICON_ID,
        getPosition: (d) => d.position,
        getAngle: (d) => d.angle,
        getColor: () => D8_DIRECTION_COLOR,
        getSize: () => layer.cellSizeMeters,
        sizeUnits: 'meters',
        billboard: false,
        pickable: false,
      }),
    ];
  }

  function buildLanduseLayers(state) {
    if (!state.subcatchmentsVisible) return [];
    const activeLayers = state.landuseLayers
      .filter((l) => l.visible && state.subcatchmentsGeoJson && state.landuseSummary)
      .map((overlay) => {
        return new deck.GeoJsonLayer({
          id: `landuse-${overlay.key}${state.comparisonMode && state.currentScenarioPath && state.baseSummaryCache.landuse && constants.COMPARISON_MEASURES.includes(overlay.mode) ? '-diff' : ''}`,
          data: state.subcatchmentsGeoJson,
          pickable: true,
          stroked: false,
          filled: true,
          opacity: 0.8,
          getFillColor: (f) => {
            const props = f && f.properties;
            const identity = resolveFeatureIdentity(props, state);
            const row = identity.key != null ? state.landuseSummary[String(identity.key)] : null;
            return landuseColor(overlay.mode, row, identity.topazId);
          },
          updateTriggers: {
            getFillColor: [state.comparisonMode, state.currentScenarioPath, state.comparisonDiffRanges[overlay.mode]],
          },
        });
      });
    return activeLayers;
  }

  function buildSoilsLayers(state) {
    if (!state.subcatchmentsVisible) return [];
    const activeLayers = state.soilsLayers
      .filter((l) => l.visible && state.subcatchmentsGeoJson && state.soilsSummary)
      .map((overlay) => {
        return new deck.GeoJsonLayer({
          id: `soils-${overlay.key}`,
          data: state.subcatchmentsGeoJson,
          pickable: true,
          stroked: false,
          filled: true,
          opacity: 0.8,
          getFillColor: (f) => {
            const props = f && f.properties;
            const identity = resolveFeatureIdentity(props, state);
            const row = identity.key != null ? state.soilsSummary[String(identity.key)] : null;
            return soilsFillColor(overlay.mode, row);
          },
          updateTriggers: {
            getFillColor: [state.graphHighlightedTopazId],
          },
        });
      });
    return activeLayers;
  }

  function buildHillslopesLayers(state) {
    if (!state.subcatchmentsVisible) return [];
    const activeLayers = state.hillslopesLayers
      .filter((l) => l.visible && state.subcatchmentsGeoJson && state.hillslopesSummary)
      .map((overlay) => {
        return new deck.GeoJsonLayer({
          id: `hillslopes-${overlay.key}`,
          data: state.subcatchmentsGeoJson,
          pickable: true,
          stroked: false,
          filled: true,
          opacity: 0.8,
          getFillColor: (f) => {
            const props = f && f.properties;
            const identity = resolveFeatureIdentity(props, state);
            const row = identity.key != null ? state.hillslopesSummary[String(identity.key)] : null;
            return hillslopesFillColor(overlay.mode, row);
          },
        });
      });
    return activeLayers;
  }

  function buildWatarLayers(state) {
    if (!state.subcatchmentsVisible) return [];
    const activeLayers = state.watarLayers
      .filter((l) => l.visible && state.subcatchmentsGeoJson && state.watarSummary)
      .map((overlay) => {
        return new deck.GeoJsonLayer({
          id: `watar-${overlay.key}`,
          data: state.subcatchmentsGeoJson,
          pickable: true,
          stroked: false,
          filled: true,
          opacity: 0.8,
          getFillColor: (f) => {
            const props = f && f.properties;
            const identity = resolveFeatureIdentity(props, state);
            const row = identity.key != null ? state.watarSummary[String(identity.key)] : null;
            return watarFillColor(overlay.mode, row);
          },
          updateTriggers: {
            getFillColor: [state.watarRanges[overlay.mode]],
          },
        });
      });
    return activeLayers;
  }

  function buildOpenetLayers(state) {
    if (!state.subcatchmentsVisible) return [];
    const activeLayers = state.openetLayers
      .filter((l) => l.visible && state.subcatchmentsGeoJson && state.openetSummary)
      .map((overlay) => {
        return new deck.GeoJsonLayer({
          id: `openet-${overlay.key}`,
          data: state.subcatchmentsGeoJson,
          pickable: true,
          stroked: false,
          filled: true,
          opacity: 0.8,
          getFillColor: (f) => {
            const props = f && f.properties;
            const identity = resolveFeatureIdentity(props, state);
            const row = identity.key != null ? state.openetSummary[String(identity.key)] : null;
            return openetFillColor(scalarValue(row));
          },
          updateTriggers: {
            getFillColor: [state.openetSelectedMonthIndex, overlay.datasetKey, state.openetRanges],
          },
        });
      });
    return activeLayers;
  }

  function buildWeppLayers(state) {
    if (!state.subcatchmentsVisible) return [];
    const activeLayers = state.weppLayers
      .filter((l) => l.visible && state.subcatchmentsGeoJson && state.weppSummary)
      .map((overlay) => {
        const useComparison =
          state.comparisonMode &&
          state.currentScenarioPath &&
          constants.COMPARISON_MEASURES.includes(overlay.mode) &&
          state.baseSummaryCache.wepp;
        return new deck.GeoJsonLayer({
          id: `wepp-${overlay.key}${useComparison ? '-diff' : ''}`,
          data: state.subcatchmentsGeoJson,
          pickable: true,
          stroked: false,
          filled: true,
          opacity: 0.8,
          getFillColor: (f) => {
            const props = f && f.properties;
            const identity = resolveFeatureIdentity(props, state);
            const row = identity.key != null ? state.weppSummary[String(identity.key)] : null;
            if (useComparison) {
              const baseRow = identity.key != null ? state.baseSummaryCache.wepp[String(identity.key)] : null;
              return weppComparisonFillColor(overlay.mode, row, baseRow);
            }
            return weppFillColor(overlay.mode, row);
          },
          updateTriggers: {
            getFillColor: [
              state.comparisonMode,
              state.currentScenarioPath,
              state.comparisonDiffRanges[overlay.mode],
              state.weppRanges[overlay.mode],
              state.weppStatistic,
            ],
          },
        });
      });
    return activeLayers;
  }

  function buildWeppChannelLayers(state) {
    if (!state.channelsVisible) return [];
    const activeLayers = (state.weppChannelLayers || [])
      .filter((l) => l.visible && state.channelsGeoJson && state.weppChannelSummary)
      .map((overlay) => {
        return new deck.GeoJsonLayer({
          id: `wepp-channel-${overlay.key}`,
          data: state.channelsGeoJson,
          pickable: true,
          stroked: true,
          filled: true,
          lineWidthUnits: 'pixels',
          lineWidthMinPixels: 1,
          getLineWidth: () => 2,
          getLineColor: (f) => {
            const props = f && f.properties;
            const identity = resolveFeatureIdentity(props, state);
            const row = identity.key != null ? state.weppChannelSummary[String(identity.key)] : null;
            return weppChannelFillColor(overlay.mode, row);
          },
          getFillColor: (f) => {
            const props = f && f.properties;
            const identity = resolveFeatureIdentity(props, state);
            const row = identity.key != null ? state.weppChannelSummary[String(identity.key)] : null;
            return weppChannelFillColor(overlay.mode, row);
          },
          updateTriggers: {
            getLineColor: [state.weppChannelRanges[overlay.mode], state.weppStatistic],
            getFillColor: [state.weppChannelRanges[overlay.mode], state.weppStatistic],
          },
        });
      });
    return activeLayers;
  }

  function buildWeppYearlyChannelLayers(state) {
    if (!state.channelsVisible) return [];
    const activeLayers = (state.weppYearlyChannelLayers || [])
      .filter((l) => l.visible && state.channelsGeoJson && state.weppYearlyChannelSummary)
      .map((overlay) => {
        return new deck.GeoJsonLayer({
          id: `wepp-yearly-channel-${overlay.key}`,
          data: state.channelsGeoJson,
          pickable: true,
          stroked: true,
          filled: true,
          lineWidthUnits: 'pixels',
          lineWidthMinPixels: 1,
          getLineWidth: () => 2,
          getLineColor: (f) => {
            const props = f && f.properties;
            const identity = resolveFeatureIdentity(props, state);
            const row = identity.key != null ? state.weppYearlyChannelSummary[String(identity.key)] : null;
            return weppYearlyChannelFillColor(overlay.mode, row);
          },
          getFillColor: (f) => {
            const props = f && f.properties;
            const identity = resolveFeatureIdentity(props, state);
            const row = identity.key != null ? state.weppYearlyChannelSummary[String(identity.key)] : null;
            return weppYearlyChannelFillColor(overlay.mode, row);
          },
          updateTriggers: {
            getLineColor: [state.weppYearlySelectedYear, state.weppYearlyChannelRanges[overlay.mode]],
            getFillColor: [state.weppYearlySelectedYear, state.weppYearlyChannelRanges[overlay.mode]],
          },
        });
      });
    return activeLayers;
  }

  function buildWeppYearlyLayers(state) {
    if (!state.subcatchmentsVisible) return [];
    const activeLayers = state.weppYearlyLayers
      .filter((l) => l.visible && state.subcatchmentsGeoJson && state.weppYearlySummary)
      .map((overlay) => {
        const useComparison =
          state.comparisonMode &&
          state.currentScenarioPath &&
          constants.COMPARISON_MEASURES.includes(overlay.mode) &&
          state.baseWeppYearlyCache[state.weppYearlySelectedYear];
        return new deck.GeoJsonLayer({
          id: `wepp-yearly-${overlay.key}${useComparison ? '-diff' : ''}`,
          data: state.subcatchmentsGeoJson,
          pickable: true,
          stroked: false,
          filled: true,
          opacity: 0.8,
          getFillColor: (f) => {
            const props = f && f.properties;
            const identity = resolveFeatureIdentity(props, state);
            const row = identity.key != null ? state.weppYearlySummary[String(identity.key)] : null;
            if (useComparison) {
              const baseSummary = state.baseWeppYearlyCache[state.weppYearlySelectedYear] || {};
              const baseRow = identity.key != null ? baseSummary[String(identity.key)] : null;
              return weppYearlyComparisonFillColor(overlay.mode, row, baseRow);
            }
            return weppYearlyFillColor(overlay.mode, row);
          },
          updateTriggers: {
            getFillColor: [state.comparisonMode, state.currentScenarioPath, state.weppYearlySelectedYear, state.weppYearlyRanges[overlay.mode]],
          },
        });
      });
    return activeLayers;
  }

  function buildWeppEventLayers(state) {
    if (!state.subcatchmentsVisible) return [];
    const activeLayers = state.weppEventLayers
      .filter((l) => l.visible && state.subcatchmentsGeoJson && state.weppEventSummary)
      .map((overlay) => {
        return new deck.GeoJsonLayer({
          id: `wepp-event-${overlay.key}`,
          data: state.subcatchmentsGeoJson,
          pickable: true,
          stroked: false,
          filled: true,
          opacity: 0.8,
          getFillColor: (f) => {
            const props = f && f.properties;
            const identity = resolveFeatureIdentity(props, state);
            const row = identity.key != null ? state.weppEventSummary[String(identity.key)] : null;
            return weppEventFillColor(overlay.mode, row);
          },
          updateTriggers: {
            getFillColor: [state.weppEventSelectedDate, state.weppEventRanges[overlay.mode]],
          },
        });
      });
    return activeLayers;
  }

  function buildRapLayers(state) {
    if (!state.subcatchmentsVisible) return [];
    if (!state.rapSummary) return [];
    if (state.rapCumulativeMode) {
      const selectedBands = state.rapLayers.filter((l) => l.selected !== false);
      const bandIds = selectedBands.map((l) => l.bandId).join(',');
      return [
        new deck.GeoJsonLayer({
          id: `rap-cumulative-${bandIds}`,
          data: state.subcatchmentsGeoJson,
          pickable: true,
          stroked: false,
          filled: true,
          opacity: 0.8,
          getFillColor: (f) => {
            const props = f && f.properties;
            const identity = resolveFeatureIdentity(props, state);
            const row = identity.key != null ? state.rapSummary[String(identity.key)] : null;
            if (state.graphHighlightedTopazId && String(identity.key) === String(state.graphHighlightedTopazId)) {
              return [255, 200, 0, 255];
            }
            return rapFillColor(row);
          },
          getLineColor: (f) => {
            const props = f && f.properties;
            const identity = resolveFeatureIdentity(props, state);
            if (state.graphHighlightedTopazId && String(identity.key) === String(state.graphHighlightedTopazId)) {
              return [255, 200, 0, 255];
            }
            return [0, 0, 0, 0];
          },
          getLineWidth: (f) => {
            const props = f && f.properties;
            const identity = resolveFeatureIdentity(props, state);
            if (state.graphHighlightedTopazId && String(identity.key) === String(state.graphHighlightedTopazId)) {
              return 3;
            }
            return 0;
          },
          lineWidthUnits: 'pixels',
          updateTriggers: {
            getFillColor: [state.rapSelectedYear, bandIds, state.graphHighlightedTopazId],
            getLineColor: [state.graphHighlightedTopazId],
            getLineWidth: [state.graphHighlightedTopazId],
          },
        }),
      ];
    }

    const activeLayer = pickActive(state.rapLayers);
    if (!activeLayer) return [];
    return [
      new deck.GeoJsonLayer({
        id: `rap-${activeLayer.key}`,
        data: state.subcatchmentsGeoJson,
        pickable: true,
        stroked: false,
        filled: true,
        opacity: 0.8,
        getFillColor: (f) => {
          const props = f && f.properties;
          const identity = resolveFeatureIdentity(props, state);
          const row = identity.key != null ? state.rapSummary[String(identity.key)] : null;
          return rapFillColor(row);
        },
        getLineColor: (f) => {
          const props = f && f.properties;
          const identity = resolveFeatureIdentity(props, state);
          if (state.graphHighlightedTopazId && String(identity.key) === String(state.graphHighlightedTopazId)) {
            return [255, 200, 0, 255];
          }
          return [0, 0, 0, 0];
        },
        getLineWidth: (f) => {
          const props = f && f.properties;
          const identity = resolveFeatureIdentity(props, state);
          if (state.graphHighlightedTopazId && String(identity.key) === String(state.graphHighlightedTopazId)) {
            return 3;
          }
          return 0;
        },
        lineWidthUnits: 'pixels',
        updateTriggers: {
          getFillColor: [state.rapSelectedYear, activeLayer.bandId],
          getLineColor: [state.graphHighlightedTopazId],
          getLineWidth: [state.graphHighlightedTopazId],
        },
      }),
    ];
  }

  function sampleRaster(layer, lonLat) {
    if (!layer || !layer.values || !layer.width || !layer.height || !layer.bounds) return null;
    const [lon, lat] = lonLat || [];
    if (!Number.isFinite(lon) || !Number.isFinite(lat)) return null;
    const [west, south, east, north] = layer.bounds;
    if (lon < west || lon > east || lat < south || lat > north) {
      return null;
    }
    const x = ((lon - west) / (east - west)) * layer.width;
    const y = ((north - lat) / (north - south)) * layer.height;
    const xi = Math.floor(x);
    const yi = Math.floor(y);
    if (xi < 0 || xi >= layer.width || yi < 0 || yi >= layer.height) return null;
    if (layer.sampleMode === 'rgba') {
      const base = (yi * layer.width + xi) * 4;
      const a = layer.values[base + 3];
      if (a === 0) return null;
      const decoded = decodeSbsPixel(layer.values[base], layer.values[base + 1], layer.values[base + 2]);
      return decoded.unassigned ? 'Unassigned' : `${decoded.classCode}: ${decoded.label}`;
    }
    const idx = yi * layer.width + xi;
    const v = layer.values[idx];
    return Number.isFinite(v) ? v : null;
  }

  function buildRasterLayers(state) {
    const sbsColorShift = !!state.sbsColorShiftEnabled;
    return state.detectedLayers
      .filter((layer) => layer.visible)
      .map((layer) => {
        if (layer.imageUrl) {
          const cacheBusted = `${layer.imageUrl}${layer.imageUrl.includes('?') ? '&' : '?'}t=${Date.now()}`;
          return new deck.BitmapLayer({
            id: `raster-${layer.key}`,
            image: cacheBusted,
            bounds: layer.bounds,
            pickable: false,
            opacity: 0.8,
          });
        }
        if (layer.canvas) {
          const image = layer.key === 'sbs'
            ? getSbsDisplayCanvas(layer, sbsColorShift)
            : layer.canvas;
          return new deck.BitmapLayer({
            id: `raster-${layer.key}`,
            image,
            bounds: layer.bounds,
            pickable: false,
            opacity: 0.8,
          });
        }
        return null;
      })
      .filter(Boolean);
  }

  function buildLayerStack(baseLayer) {
    const state = getState();
    const rasterLayers = buildRasterLayers(state);
    const landuseDeckLayers = buildLanduseLayers(state);
    const soilsDeckLayers = buildSoilsLayers(state);
    const hillslopesDeckLayers = buildHillslopesLayers(state);
    const watarDeckLayers = buildWatarLayers(state);
    const weppDeckLayers = buildWeppLayers(state);
    const weppYearlyDeckLayers = buildWeppYearlyLayers(state);
    const weppEventDeckLayers = buildWeppEventLayers(state);
    const openetDeckLayers = buildOpenetLayers(state);
    const rapDeckLayers = buildRapLayers(state);
    const channelDeckLayers = buildChannelsLayer(state);
    const weppChannelDeckLayers = buildWeppChannelLayers(state);
    const weppYearlyChannelDeckLayers = buildWeppYearlyChannelLayers(state);
    const d8DirectionLayer = buildD8DirectionLayer(state);
    const labelLayers = buildSubcatchmentLabelsLayer(state);
    const channelLabelLayers = buildChannelLabelsLayer(state);
    return [
      baseLayer,
      ...landuseDeckLayers,
      ...soilsDeckLayers,
      ...hillslopesDeckLayers,
      ...watarDeckLayers,
      ...weppDeckLayers,
      ...weppYearlyDeckLayers,
      ...weppEventDeckLayers,
      ...openetDeckLayers,
      ...rapDeckLayers,
      ...rasterLayers,
      ...channelDeckLayers,
      ...weppChannelDeckLayers,
      ...weppYearlyChannelDeckLayers,
      ...d8DirectionLayer,
      ...labelLayers,
      ...channelLabelLayers,
    ];
  }

  function formatTooltip(info) {
    return formatLayerTooltip(info, getState(), RAP_BAND_LABELS, sampleRaster);
  }

  function pickActiveLayerForLegend(category, state) {
    const layersByCategory = {
      Landuse: state.landuseLayers,
      Soils: state.soilsLayers,
      Watershed: state.hillslopesLayers,
      Channels: state.channelsLayers,
      RAP: state.rapLayers,
      WEPP: state.weppLayers,
      'WEPP Channels': state.weppChannelLayers,
      'WEPP Yearly': state.weppYearlyLayers,
      'WEPP Yearly Channels': state.weppYearlyChannelLayers,
      'WEPP Event': state.weppEventLayers,
      WATAR: state.watarLayers,
      OpenET: state.openetLayers,
      Raster: state.detectedLayers,
    };
    const layers = layersByCategory[category] || [];
    const layer = pickActive(layers);
    if (!layer) return null;
    return { ...layer, category };
  }

  function getActiveLayersForLegend() {
    const state = getState();
    const active = [];
    if (state.subcatchmentsVisible) {
      const landuse = pickActiveLayerForLegend('Landuse', state);
      if (landuse) active.push(landuse);
      const soils = pickActiveLayerForLegend('Soils', state);
      if (soils) active.push(soils);
      const hills = pickActiveLayerForLegend('Watershed', state);
      if (hills) active.push(hills);
      if (state.rapCumulativeMode) {
        const selectedBands = state.rapLayers.filter((l) => l.selected !== false);
        const bandNames = selectedBands.map((l) => RAP_BAND_LABELS[l.bandKey] || l.bandKey).join(' + ');
        active.push({
          key: 'rap-cumulative',
          label: `Cumulative Cover (${bandNames})`,
          category: 'RAP',
          isCumulative: true,
        });
      } else {
        const rap = pickActiveLayerForLegend('RAP', state);
        if (rap) active.push(rap);
      }
      const wepp = pickActiveLayerForLegend('WEPP', state);
      if (wepp) active.push(wepp);
      const weppYearly = pickActiveLayerForLegend('WEPP Yearly', state);
      if (weppYearly) active.push(weppYearly);
      const weppEvent = pickActiveLayerForLegend('WEPP Event', state);
      if (weppEvent) active.push(weppEvent);
      const openet = pickActiveLayerForLegend('OpenET', state);
      if (openet) active.push(openet);
      const watar = pickActiveLayerForLegend('WATAR', state);
      if (watar) active.push(watar);
    }
    if (state.channelsVisible && state.channelsGeoJson) {
      const channelsLayer = pickActiveLayerForLegend('Channels', state);
      if (channelsLayer) {
        active.push(channelsLayer);
      }
    }
    const weppChannels = pickActiveLayerForLegend('WEPP Channels', state);
    if (weppChannels && state.channelsVisible) {
      active.push(weppChannels);
    }
    const weppYearlyChannels = pickActiveLayerForLegend('WEPP Yearly Channels', state);
    if (weppYearlyChannels && state.channelsVisible) {
      active.push(weppYearlyChannels);
    }
    state.detectedLayers.forEach((layer) => {
      if (layer.visible) {
        active.push({ ...layer, category: 'Raster' });
      }
    });
    return active;
  }

  return {
    buildLayerStack,
    formatTooltip,
    getActiveLayersForLegend,
    getChannelLegendItems: buildChannelLegendItems,
    getSbsLegendItems,
    recolorSbsPixels,
    getSbsDisplayCanvas,
    constants: { NLCD_COLORMAP, NLCD_LABELS, RAP_BAND_LABELS },
    helpers: {
      landuseValue,
      soilsValue,
      hillslopesValue: modeValue,
      watarValue: modeValue,
      weppValue: modeValue,
      weppChannelValue: modeValue,
      weppYearlyChannelValue: modeValue,
      weppYearlyValue: modeValue,
      weppEventValue,
      rapValue: scalarValue,
      landuseFillColor: landuseColor,
      soilsFillColor,
      hillslopesFillColor,
      watarFillColor,
      weppFillColor,
      weppYearlyChannelFillColor,
      weppYearlyFillColor,
      weppEventFillColor,
      rapFillColor,
      sampleRaster,
    },
  };
}
