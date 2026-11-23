import { jet2Color } from '../colors.js';

const RUSLE_A_UNITS = 't/ha/yr';
const RUSLE_TOLERANCE_EPSILON = 1e-9;

function isNoDataValue(value, nodata) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return true;
  if (!Number.isFinite(nodata)) return false;
  const tolerance = Math.max(1e-12, Math.abs(nodata) * 1e-12);
  return Math.abs(numeric - nodata) <= tolerance;
}

function normalizeRasterRange(range, { allowEqual = false } = {}) {
  if (!range || typeof range !== 'object') return null;
  const min = Number(range.min);
  const max = Number(range.max);
  if (!Number.isFinite(min) || !Number.isFinite(max)) return null;
  if (allowEqual ? max < min : max <= min) return null;
  return { min, max };
}

function computeRasterRangeFromValues(values, nodata) {
  if (!values || typeof values.length !== 'number') return null;
  let min = Infinity;
  let max = -Infinity;
  for (let i = 0; i < values.length; i += 1) {
    const numeric = Number(values[i]);
    if (!Number.isFinite(numeric) || isNoDataValue(numeric, nodata)) continue;
    if (numeric < min) min = numeric;
    if (numeric > max) max = numeric;
  }
  if (!Number.isFinite(min) || !Number.isFinite(max) || max < min) return null;
  return { min, max };
}

function isRusleALayer(layer) {
  if (!layer || typeof layer !== 'object') return false;
  if (typeof layer.key === 'string' && layer.key.startsWith('rusle-a-')) {
    return true;
  }
  if (typeof layer.path === 'string' && layer.path.startsWith('rusle/a_')) {
    return true;
  }
  return false;
}

function resolveRusleABaseRange(layer) {
  if (!layer || typeof layer !== 'object') return null;
  const cached = normalizeRasterRange(layer._rusleBaseRange, { allowEqual: true });
  if (cached) return cached;
  const fromValues = computeRasterRangeFromValues(layer.values, layer.nodata);
  const fromRange = normalizeRasterRange(layer.range, { allowEqual: true });
  const resolved = fromValues || fromRange;
  if (resolved) {
    layer._rusleBaseRange = { ...resolved };
  }
  return resolved ? { ...resolved } : null;
}

function resolveRusleToleranceMax(baseRange, candidate) {
  if (!baseRange) return null;
  const parsed = Number(candidate);
  const span = Math.abs(baseRange.max - baseRange.min);
  const minTolerance = baseRange.min + Math.max(RUSLE_TOLERANCE_EPSILON, span * 1e-9);
  if (!Number.isFinite(parsed)) {
    return baseRange.max;
  }
  if (parsed <= baseRange.min) {
    return minTolerance;
  }
  return parsed;
}

function parseOptionalFiniteNumber(value) {
  if (value === null || value === undefined || value === '') {
    return Number.NaN;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : Number.NaN;
}

function buildRusleACanvasFromValues(layer, effectiveRange) {
  if (!layer || !layer.values || !layer.width || !layer.height) {
    return layer && layer.canvas ? layer.canvas : null;
  }
  const width = Number(layer.width);
  const height = Number(layer.height);
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
    return layer.canvas || null;
  }
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  let ctx2d = null;
  try {
    ctx2d = canvas.getContext('2d');
  } catch (err) {
    return layer.canvas || null;
  }
  if (!ctx2d || typeof ctx2d.createImageData !== 'function' || typeof ctx2d.putImageData !== 'function') {
    return layer.canvas || null;
  }
  const imgData = ctx2d.createImageData(width, height);
  const values = layer.values;
  const span = effectiveRange.max - effectiveRange.min || 1;
  for (let i = 0, j = 0; i < values.length; i += 1, j += 4) {
    const numeric = Number(values[i]);
    if (!Number.isFinite(numeric) || isNoDataValue(numeric, layer.nodata)) {
      imgData.data[j] = 0;
      imgData.data[j + 1] = 0;
      imgData.data[j + 2] = 0;
      imgData.data[j + 3] = 0;
      continue;
    }
    const normalized = Math.min(1, Math.max(0, (numeric - effectiveRange.min) / span));
    const color = jet2Color(normalized);
    imgData.data[j] = color[0];
    imgData.data[j + 1] = color[1];
    imgData.data[j + 2] = color[2];
    imgData.data[j + 3] = color[3] || 230;
  }
  ctx2d.putImageData(imgData, 0, 0);
  return canvas;
}

function applyRusleAToleranceToLayer(layer, toleranceValue) {
  const target = layer && layer.rasterRef ? layer.rasterRef : layer;
  if (!isRusleALayer(target)) return null;
  const baseRange = resolveRusleABaseRange(target);
  if (!baseRange) return null;
  const toleranceMax = resolveRusleToleranceMax(baseRange, toleranceValue);
  if (!Number.isFinite(toleranceMax)) return null;
  const effectiveRange = { min: baseRange.min, max: toleranceMax };
  const canvas = buildRusleACanvasFromValues(target, effectiveRange);
  if (canvas) {
    target.canvas = canvas;
  }
  target.range = effectiveRange;
  if (layer && layer !== target) {
    layer.range = effectiveRange;
    layer.canvas = canvas || layer.canvas;
  }
  return { toleranceMax, baseRange, effectiveRange };
}

function resolvePrimaryRusleALayer(layers) {
  if (!Array.isArray(layers) || !layers.length) return null;
  return layers.find((layer) => layer && layer.visible) || layers[0];
}

export function renderRusleTolerance(details, items, state, { setValue, applyLayers, updateLegendsPanel }) {
  const rusleALayers = items.filter(isRusleALayer);
  if (!rusleALayers.length) return;
  const primaryLayer = resolvePrimaryRusleALayer(rusleALayers);
  const primaryRange = resolveRusleABaseRange(primaryLayer);
  const stateTolerance = parseOptionalFiniteNumber(state.rusleATolerance);
  const toleranceValue =
    Number.isFinite(stateTolerance) || !primaryRange ? stateTolerance : primaryRange.max;
  let appliedTolerance = toleranceValue;
  rusleALayers.forEach((layer) => {
    const applied = applyRusleAToleranceToLayer(layer, appliedTolerance);
    if (applied && !Number.isFinite(appliedTolerance)) {
      appliedTolerance = applied.toleranceMax;
    }
  });
  if (!Number.isFinite(appliedTolerance) && primaryRange) {
    appliedTolerance = primaryRange.max;
  }

  const toleranceBlock = document.createElement('div');
  toleranceBlock.className = 'gl-rusle-a-tolerance';
  toleranceBlock.style.cssText = 'display:grid;gap:0.25rem;margin:0.35rem 0 0.5rem;width:100%;';

  const toleranceLabel = document.createElement('label');
  toleranceLabel.className = 'gl-rusle-a-tolerance__label';
  toleranceLabel.setAttribute('for', 'gl-rusle-a-tolerance-input');
  toleranceLabel.textContent = `A Tolerance (${RUSLE_A_UNITS})`;
  toleranceLabel.style.cssText = 'font-size:0.85rem;color:var(--wc-color-text-muted);';
  toleranceBlock.appendChild(toleranceLabel);

  const toleranceInput = document.createElement('input');
  toleranceInput.id = 'gl-rusle-a-tolerance-input';
  toleranceInput.type = 'number';
  toleranceInput.step = '0.01';
  toleranceInput.inputMode = 'decimal';
  toleranceInput.className = 'gl-custom-select__trigger gl-rusle-a-tolerance__input';
  if (primaryRange && Number.isFinite(primaryRange.min)) {
    toleranceInput.min = String(primaryRange.min);
  }
  if (Number.isFinite(appliedTolerance)) {
    toleranceInput.value = String(Number(appliedTolerance.toFixed(4)));
  } else if (primaryRange && Number.isFinite(primaryRange.max)) {
    toleranceInput.value = String(Number(primaryRange.max.toFixed(4)));
  }

  toleranceInput.addEventListener('change', () => {
    const parsed = Number(toleranceInput.value);
    if (!Number.isFinite(parsed)) {
      if (Number.isFinite(appliedTolerance)) {
        toleranceInput.value = String(Number(appliedTolerance.toFixed(4)));
      }
      return;
    }
    setValue('rusleATolerance', parsed);
    let nextAppliedTolerance = parsed;
    rusleALayers.forEach((layer) => {
      const applied = applyRusleAToleranceToLayer(layer, nextAppliedTolerance);
      if (applied && !Number.isFinite(nextAppliedTolerance)) {
        nextAppliedTolerance = applied.toleranceMax;
      }
    });
    if (Number.isFinite(nextAppliedTolerance)) {
      appliedTolerance = nextAppliedTolerance;
      toleranceInput.value = String(Number(nextAppliedTolerance.toFixed(4)));
      if (Math.abs(nextAppliedTolerance - parsed) > RUSLE_TOLERANCE_EPSILON) {
        setValue('rusleATolerance', nextAppliedTolerance);
      }
    }
    applyLayers();
    updateLegendsPanel();
  });

  toleranceBlock.appendChild(toleranceInput);
  details.appendChild(toleranceBlock);
}
