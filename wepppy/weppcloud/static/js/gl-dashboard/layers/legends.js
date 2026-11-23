import { resolveColormapName } from '../colors.js';

// Units for continuous layers
const LAYER_UNITS = {
  cancov: '%',
  inrcov: '%',
  rilcov: '%',
  clay: '%',
  sand: '%',
  rock: '%',
  bd: 'g/cm³',
  slope_scalar: 'rise/run',
  length: 'm',
  aspect: '°',
  runoff_volume: 'mm',
  subrunoff_volume: 'mm',
  baseflow_volume: 'mm',
  soil_loss: 't/ha',
  sediment_deposition: 't/ha',
  sediment_yield: 't/ha',
  channel_discharge_volume: 'm^3',
  channel_soil_loss: 'kg',
  wind_transport: 't/ha',
  water_transport: 't/ha',
  ash_transport: 't/ha',
  openet_et: 'mm',
  // WEPP Event metrics
  event_P: 'mm',
  event_Q: 'mm',
  event_ET: 'mm',
  event_Saturation: '%',
  event_peakro: 'm³/s',
  event_tdet: 'kg',
};

const LEGEND_RANGE_EPSILON = 1e-9;
const EDITABLE_CONTINUOUS_RANGE_STATE_KEYS = Object.freeze({
  WATAR: 'watarRanges',
  WEPP: 'weppRanges',
  'WEPP Channels': 'weppChannelRanges',
  'WEPP Yearly': 'weppYearlyRanges',
  'WEPP Yearly Channels': 'weppYearlyChannelRanges',
  'WEPP Event': 'weppEventRanges',
});

export function createLegendsPanel({
  getState, setValue, layerUtils, legendsContentEl, legendEmptyEl, soilColorForValue, constants, applyLayers,
}) {
  const {
    COMPARISON_MEASURES,
    WATER_MEASURES,
    SOIL_MEASURES,
    NLCD_COLORMAP,
    NLCD_LABELS,
  } = constants || {};
  const comparisonMeasures = Array.isArray(COMPARISON_MEASURES) ? COMPARISON_MEASURES : [];

  function formatLegendInputValue(value) {
    if (!Number.isFinite(value)) return '';
    const absVal = Math.abs(value);
    if (absVal >= 10000) return String(Math.round(value));
    if (absVal >= 100) return value.toFixed(1);
    if (absVal >= 1) return value.toFixed(2);
    return value.toFixed(3);
  }

  function resolveLegendUpperBound(minValue, candidate, fallbackMax) {
    const parsed = Number(candidate);
    const currentFallback = Number.isFinite(fallbackMax) ? fallbackMax : minValue + 1;
    if (!Number.isFinite(parsed)) {
      return currentFallback;
    }
    const span = Math.abs(currentFallback - minValue);
    const minAllowed = minValue + Math.max(LEGEND_RANGE_EPSILON, span * 1e-9);
    if (parsed <= minValue) {
      return minAllowed;
    }
    return parsed;
  }

  function resolveLegendAbsoluteMax(candidate, fallbackAbs) {
    const parsed = Number(candidate);
    const fallback = Number.isFinite(fallbackAbs) && fallbackAbs > 0 ? fallbackAbs : 1;
    if (!Number.isFinite(parsed)) {
      return fallback;
    }
    const absValue = Math.abs(parsed);
    return Math.max(absValue, Math.max(LEGEND_RANGE_EPSILON, fallback * 1e-9));
  }

  function updateModeRangeState(stateKey, mode, nextRange) {
    if (!stateKey || !mode || !nextRange) return;
    const currentState = getState();
    const nextMap = {
      ...(currentState[stateKey] || {}),
      [mode]: {
        min: nextRange.min,
        max: nextRange.max,
      },
    };
    setValue(stateKey, nextMap);
  }

  function setContinuousLegendRange(layer, mode, minValue, maxValue) {
    if (!layer) return null;
    const normalized = {
      min: Number(minValue),
      max: Number(maxValue),
    };
    if (!Number.isFinite(normalized.min) || !Number.isFinite(normalized.max) || normalized.max <= normalized.min) {
      return null;
    }
    if (layer.category === 'OpenET') {
      const current = getState().openetRanges || {};
      setValue('openetRanges', {
        ...current,
        min: normalized.min,
        max: normalized.max,
      });
      return normalized;
    }
    const stateKey = EDITABLE_CONTINUOUS_RANGE_STATE_KEYS[layer.category];
    if (!stateKey || !mode) return null;
    if (layer.category === 'WEPP Yearly') {
      const currentState = getState();
      setValue('weppYearlyRanges', {
        ...(currentState.weppYearlyRanges || {}),
        [mode]: {
          min: normalized.min,
          max: normalized.max,
        },
      });
      setValue('weppYearlyRangeOverrides', {
        ...(currentState.weppYearlyRangeOverrides || {}),
        [mode]: {
          min: normalized.min,
          max: normalized.max,
        },
      });
      return normalized;
    }
    updateModeRangeState(stateKey, mode, normalized);
    return normalized;
  }

  function setDivergingLegendRange(layer, mode, absMaxValue) {
    if (!layer || !mode) return null;
    const absMax = Number(absMaxValue);
    if (!Number.isFinite(absMax) || absMax <= 0) return null;
    const stateKey = layer.category === 'WEPP Yearly' ? 'weppYearlyDiffRanges' : 'comparisonDiffRanges';
    updateModeRangeState(stateKey, mode, { min: -absMax, max: absMax });
    return { min: -absMax, max: absMax };
  }

  function createLegendMaxInput({
    value,
    ariaLabel,
    onCommit,
    kind = 'continuous',
    className = '',
  }) {
    const input = document.createElement('input');
    input.type = 'number';
    input.step = 'any';
    input.inputMode = 'decimal';
    input.className = `gl-legend-range-input ${className}`.trim();
    input.setAttribute('data-range-kind', kind);
    input.setAttribute('aria-label', ariaLabel);
    input.value = formatLegendInputValue(value);
    input.title = 'Set legend upper bound';

    let committedValue = value;

    const commit = ({ refreshLegend = true, revertOnInvalid = true } = {}) => {
      const nextValue = onCommit(input.value, { refreshLegend });
      if (Number.isFinite(nextValue)) {
        committedValue = nextValue;
      } else if (revertOnInvalid) {
        input.value = formatLegendInputValue(committedValue);
      }
    };

    input.addEventListener('input', () => {
      commit({ refreshLegend: false, revertOnInvalid: false });
    });
    input.addEventListener('change', () => {
      commit({ refreshLegend: true, revertOnInvalid: true });
    });
    input.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        commit({ refreshLegend: true, revertOnInvalid: true });
      } else if (event.key === 'Escape') {
        input.value = formatLegendInputValue(committedValue);
        input.blur();
      }
    });
    return input;
  }

  function resolveContinuousLegendEditor(layer, mode, minVal, maxVal) {
    if (!layer || !Number.isFinite(minVal) || !Number.isFinite(maxVal) || maxVal <= minVal) {
      return null;
    }
    const isEditableCategory = layer.category === 'OpenET' || !!EDITABLE_CONTINUOUS_RANGE_STATE_KEYS[layer.category];
    if (!isEditableCategory) return null;
    return {
      maxValue: maxVal,
      ariaLabel: `${layer.label || layer.key} legend maximum`,
      onCommit: (candidateValue, { refreshLegend = true } = {}) => {
        const nextMax = resolveLegendUpperBound(minVal, candidateValue, maxVal);
        const applied = setContinuousLegendRange(layer, mode, minVal, nextMax);
        if (!applied) return Number.NaN;
        applyLayers({ skipLegendUpdate: true, skipGraphSync: true });
        if (refreshLegend) {
          updateLegendsPanel();
        }
        return applied.max;
      },
    };
  }

  function resolveDivergingLegendEditor(layer, mode, range) {
    if (!layer || !mode || !range || !Number.isFinite(range.min) || !Number.isFinite(range.max)) {
      return null;
    }
    const currentAbsMax = Math.max(Math.abs(range.min), Math.abs(range.max));
    if (!Number.isFinite(currentAbsMax) || currentAbsMax <= 0) return null;
    return {
      maxValue: currentAbsMax,
      ariaLabel: `${layer.label || layer.key} absolute difference maximum`,
      onCommit: (candidateValue, { refreshLegend = true } = {}) => {
        const nextAbsMax = resolveLegendAbsoluteMax(candidateValue, currentAbsMax);
        const applied = setDivergingLegendRange(layer, mode, nextAbsMax);
        if (!applied) return Number.NaN;
        applyLayers({ skipLegendUpdate: true, skipGraphSync: true });
        if (refreshLegend) {
          updateLegendsPanel();
        }
        return Math.abs(applied.max);
      },
    };
  }

  function formatLegendValue(value, decimals = 1) {
    if (!Number.isFinite(value)) return '—';
    return value.toFixed(decimals);
  }

  function getUsedNlcdClasses(layer) {
    const classes = new Set();
    if (!layer || !layer.values) return [];
    const values = layer.values;
    for (let i = 0; i < values.length; i++) {
      const v = values[i];
      if (Number.isFinite(v) && v > 0 && NLCD_COLORMAP[v]) {
        classes.add(v);
      }
    }
    return Array.from(classes)
      .sort((a, b) => a - b)
      .map((code) => ({
        color: NLCD_COLORMAP[code],
        label: NLCD_LABELS[code] || `Class ${code}`,
      }));
  }

  function getUsedSoilClasses(layer) {
    const codes = new Set();
    if (!layer || !layer.values) return [];
    const values = layer.values;
    for (let i = 0; i < values.length; i++) {
      const v = values[i];
      if (Number.isFinite(v) && v > 0) {
        codes.add(v);
      }
    }
    if (codes.size === 0) return [];
    return Array.from(codes)
      .sort((a, b) => a - b)
      .map((code) => {
        const color = soilColorForValue(code);
        const label = String(code);
        return { color, label };
      });
  }

  function getUsedLanduseClasses(state) {
    const classMap = new Map();
    if (!state.landuseSummary) return classMap;
    for (const topazId of Object.keys(state.landuseSummary)) {
      const row = state.landuseSummary[topazId];
      if (!row) continue;
      const key = row.key ?? row._map;
      if (key == null || classMap.has(key)) continue;
      const color = row.color;
      const desc = row.desc || `Class ${key}`;
      classMap.set(key, { color, desc });
    }
    return classMap;
  }

  function getUsedSoilsClasses(state) {
    const classMap = new Map();
    if (!state.soilsSummary) return classMap;
    for (const topazId of Object.keys(state.soilsSummary)) {
      const row = state.soilsSummary[topazId];
      if (!row) continue;
      const mukey = row.mukey;
      if (mukey == null || classMap.has(mukey)) continue;
      const color = row.color;
      const desc = row.desc || mukey;
      classMap.set(mukey, { color, desc });
    }
    return classMap;
  }

  function renderCategoricalLegend(items) {
    const container = document.createElement('div');
    container.className = 'gl-legend-categorical';
    for (const item of items) {
      const row = document.createElement('div');
      row.className = 'gl-legend-categorical__item';
      const swatch = document.createElement('span');
      swatch.className = 'gl-legend-categorical__swatch';
      swatch.style.backgroundColor = item.color;
      if (item.masked) swatch.style.border = '1px solid #333';
      const label = document.createElement('span');
      label.textContent = item.label;
      row.appendChild(swatch);
      row.appendChild(label);
      container.appendChild(row);
    }
    return container;
  }

  function getSbsLegendClasses(state, layer) {
    if (!layerUtils || typeof layerUtils.getSbsLegendItems !== 'function') return [];
    return layerUtils.getSbsLegendItems(
      !!(state && state.sbsColorShiftEnabled),
      layer && layer.sbsUnassignedCount,
    );
  }

  function renderContinuousLegend(minVal, maxVal, unit, colormap, editor = null) {
    const container = document.createElement('div');
    container.className = 'gl-legend-continuous';

    const barWrapper = document.createElement('div');
    barWrapper.className = 'gl-legend-continuous__bar-wrapper';
    const bar = document.createElement('div');
    let barClass = 'gl-legend-continuous__bar';
    if (colormap === 'winter') {
      barClass += ' gl-legend-continuous__bar--winter';
    } else if (colormap === 'plasma') {
      barClass += ' gl-legend-continuous__bar--plasma';
    } else if (colormap === 'jet2') {
      barClass += ' gl-legend-continuous__bar--jet2';
    }
    bar.className = barClass;
    barWrapper.appendChild(bar);
    container.appendChild(barWrapper);

    const labels = document.createElement('div');
    labels.className = 'gl-legend-continuous__labels';
    const minLabel = document.createElement('span');
    minLabel.textContent = formatLegendValue(minVal);
    let maxLabel;
    if (editor && Number.isFinite(editor.maxValue) && typeof editor.onCommit === 'function') {
      maxLabel = createLegendMaxInput({
        value: editor.maxValue,
        ariaLabel: editor.ariaLabel || 'Legend maximum',
        onCommit: editor.onCommit,
        kind: 'continuous',
      });
    } else {
      maxLabel = document.createElement('span');
      maxLabel.textContent = formatLegendValue(maxVal);
    }
    labels.appendChild(minLabel);
    labels.appendChild(maxLabel);
    container.appendChild(labels);

    if (unit) {
      const unitEl = document.createElement('div');
      unitEl.className = 'gl-legend-continuous__unit';
      unitEl.textContent = unit;
      container.appendChild(unitEl);
    }

    return container;
  }

  function renderDivergingLegend(unit, label, mode, rangeOverride, state, editor = null) {
    const container = document.createElement('div');
    container.className = 'gl-legend-continuous gl-legend-diverging';

    const barWrapper = document.createElement('div');
    barWrapper.className = 'gl-legend-continuous__bar-wrapper';
    const bar = document.createElement('div');
    bar.className = 'gl-legend-continuous__bar gl-legend-diverging__bar';
    bar.style.background = 'linear-gradient(to right, #2166AC, #F7F7F7 50%, #B2182B)';
    barWrapper.appendChild(bar);
    container.appendChild(barWrapper);

    const comparisonRanges = (state && state.comparisonDiffRanges) || {};
    const range = rangeOverride || (mode ? comparisonRanges[mode] : null);
    const hasRange = range && Number.isFinite(range.min) && Number.isFinite(range.max);

    function formatRangeValue(val) {
      const absVal = Math.abs(val);
      if (absVal >= 10000) return val.toFixed(0);
      if (absVal >= 100) return val.toFixed(1);
      if (absVal >= 1) return val.toFixed(2);
      return val.toFixed(3);
    }

    const labels = document.createElement('div');
    labels.className = 'gl-legend-continuous__labels';
    labels.style.justifyContent = 'space-between';

    const leftLabel = document.createElement('span');
    leftLabel.textContent = hasRange ? formatRangeValue(range.min) : 'Scenario > Base';
    leftLabel.style.color = '#2166AC';

    const centerLabel = document.createElement('span');
    centerLabel.textContent = '0';
    centerLabel.style.color = 'var(--gl-text-secondary, #8fa0c2)';

    let rightLabel;
    if (hasRange && editor && Number.isFinite(editor.maxValue) && typeof editor.onCommit === 'function') {
      rightLabel = createLegendMaxInput({
        value: editor.maxValue,
        ariaLabel: editor.ariaLabel || 'Difference maximum',
        onCommit: editor.onCommit,
        kind: 'diverging',
        className: 'gl-legend-range-input--diverging',
      });
      rightLabel.style.color = '#B2182B';
    } else {
      rightLabel = document.createElement('span');
      rightLabel.textContent = hasRange ? `+${formatRangeValue(range.max)}` : 'Base > Scenario';
      rightLabel.style.color = '#B2182B';
    }

    labels.appendChild(leftLabel);
    labels.appendChild(centerLabel);
    labels.appendChild(rightLabel);
    container.appendChild(labels);

    if (unit) {
      const unitEl = document.createElement('div');
      unitEl.className = 'gl-legend-continuous__unit';
      unitEl.textContent = `Difference (${unit})`;
      container.appendChild(unitEl);
    }

    if (label) {
      const labelEl = document.createElement('div');
      labelEl.style.cssText =
        'font-size:0.7rem;color:var(--gl-text-secondary, #8fa0c2);margin-top:4px;text-align:center;';
      labelEl.textContent = label;
      container.appendChild(labelEl);
    }

    return container;
  }

  function renderAspectLegend() {
    const directions = [
      { label: 'N (0°)', degrees: 0 },
      { label: 'NE (45°)', degrees: 45 },
      { label: 'E (90°)', degrees: 90 },
      { label: 'SE (135°)', degrees: 135 },
      { label: 'S (180°)', degrees: 180 },
      { label: 'SW (225°)', degrees: 225 },
      { label: 'W (270°)', degrees: 270 },
      { label: 'NW (315°)', degrees: 315 },
    ];

    function aspectToRgb(degrees) {
      const hue = degrees % 360;
      const h = hue / 60;
      const c = 200;
      const x = c * (1 - Math.abs((h % 2) - 1));
      let r;
      let g;
      let b;
      if (h < 1) { r = c; g = x; b = 0; }
      else if (h < 2) { r = x; g = c; b = 0; }
      else if (h < 3) { r = 0; g = c; b = x; }
      else if (h < 4) { r = 0; g = x; b = c; }
      else if (h < 5) { r = x; g = 0; b = c; }
      else { r = c; g = 0; b = x; }
      return `rgb(${Math.round(r + 55)}, ${Math.round(g + 55)}, ${Math.round(b + 55)})`;
    }

    const items = directions.map((d) => ({
      label: d.label,
      color: aspectToRgb(d.degrees),
    }));

    return renderCategoricalLegend(items);
  }

  function renderLegendForLayer(layer, state) {
    const section = document.createElement('div');
    section.className = 'gl-legend-section';

    const title = document.createElement('h5');
    title.className = 'gl-legend-section__title';
    title.textContent = layer.label || layer.key;
    section.appendChild(title);

    const mode = layer.mode || '';
    const comparisonRanges = state.comparisonDiffRanges || {};
    const yearlyDiffRanges = state.weppYearlyDiffRanges || {};
    const diffRangeOverride = layer.category === 'WEPP Yearly' ? yearlyDiffRanges[mode] : null;
    const divergingMode = diffRangeOverride ? mode : layer.category === 'WEPP Yearly' ? null : mode;
    if (state.comparisonMode && comparisonMeasures.includes(mode) && state.currentScenarioPath) {
      const unit = LAYER_UNITS[mode] || '';
      const activeRange = diffRangeOverride || (divergingMode ? comparisonRanges[divergingMode] : null);
      const divergingEditor = resolveDivergingLegendEditor(layer, divergingMode, activeRange);
      section.appendChild(
        renderDivergingLegend(unit, 'Base − Scenario', divergingMode, diffRangeOverride, state, divergingEditor),
      );
      return section;
    }

    if (mode === 'dominant' && layer.category === 'Landuse') {
      const classMap = getUsedLanduseClasses(state);
      const items = [];
      for (const [key, info] of classMap.entries()) {
        const colorCss = info.color || '#888888';
        items.push({ color: colorCss, label: info.desc || `Class ${key}` });
      }
      if (items.length) {
        section.appendChild(renderCategoricalLegend(items));
      }
      return section;
    }

    if (mode === 'dominant' && layer.category === 'Soils') {
      const classMap = getUsedSoilsClasses(state);
      const items = [];
      for (const [mukey, info] of classMap.entries()) {
        const colorCss = info.color || '#888888';
        items.push({ color: colorCss, label: info.desc || mukey });
      }
      if (items.length) {
        section.appendChild(renderCategoricalLegend(items));
      }
      return section;
    }

    if (layer.key === 'landuse' && layer.category === 'Raster') {
      const nlcdItems = getUsedNlcdClasses(layer);
      if (nlcdItems.length) {
        section.appendChild(renderCategoricalLegend(nlcdItems));
      } else {
        const note = document.createElement('p');
        note.style.cssText = 'font-size:0.75rem;color:#8fa0c2;margin:0;';
        note.textContent = 'NLCD land cover classes';
        section.appendChild(note);
      }
      return section;
    }

    if (layer.key === 'soils' && layer.category === 'Raster') {
      const soilItems = getUsedSoilClasses(layer);
      if (soilItems.length) {
        section.appendChild(renderCategoricalLegend(soilItems));
      } else {
        const note = document.createElement('p');
        note.style.cssText = 'font-size:0.75rem;color:#8fa0c2;margin:0;';
        note.textContent = 'SSURGO soil types';
        section.appendChild(note);
      }
      return section;
    }

    if (layer.key === 'sbs') {
      section.appendChild(renderCategoricalLegend(getSbsLegendClasses(state, layer)));
      return section;
    }

    if (layer.category === 'Channels') {
      const items = typeof layerUtils.getChannelLegendItems === 'function' ? layerUtils.getChannelLegendItems() : [];
      if (items.length) {
        section.appendChild(renderCategoricalLegend(items));
      }
      return section;
    }

    section.appendChild(renderNumericLayerLegend(layer, mode, state));
    return section;
  }

  function renderNumericLayerLegend(layer, mode, state) {
    const rangeKey = EDITABLE_CONTINUOUS_RANGE_STATE_KEYS[layer.category];
    const modeRange = rangeKey && state[rangeKey]?.[mode];
    let minVal = 0;
    let maxVal = 100;
    let unit = LAYER_UNITS[mode] || '';

    // CV statistic always shows percentage
    if (state.weppStatistic === 'cv') {
      unit = '%';
    }

    if (
      layer.category === 'Raster' &&
      layer.range &&
      Number.isFinite(layer.range.min) &&
      Number.isFinite(layer.range.max) &&
      layer.range.max > layer.range.min
    ) {
      minVal = layer.range.min;
      maxVal = layer.range.max;
      unit = layer.units || unit;
    } else if (['cancov', 'inrcov', 'rilcov'].includes(mode)) {
      minVal = 0;
      maxVal = 100;
      unit = '%';
    } else if (['clay', 'sand', 'rock'].includes(mode) && state.soilsSummary) {
      minVal = 0;
      maxVal = 100;
      unit = '%';
    } else if (mode === 'bd' && state.soilsSummary) {
      minVal = 0.5;
      maxVal = 2.0;
      unit = 'g/cm³';
    } else if (mode === 'soil_depth' && state.soilsSummary) {
      minVal = 0;
      maxVal = 2000;
      unit = 'mm';
    } else if (mode === 'slope_scalar' && state.hillslopesSummary) {
      minVal = 0;
      maxVal = 100;
      unit = '%';
    } else if (mode === 'length' && state.hillslopesSummary) {
      minVal = 0;
      maxVal = 1000;
      unit = 'm';
    } else if (mode === 'aspect' && state.hillslopesSummary) {
      return renderAspectLegend();
    } else if (modeRange) {
      minVal = modeRange.min;
      maxVal = modeRange.max;
      if (layer.category === 'WEPP Event') unit = LAYER_UNITS[mode] || '';
    } else if (layer.category === 'OpenET' && state.openetRanges) {
      if (Number.isFinite(state.openetRanges.min) && Number.isFinite(state.openetRanges.max)) {
        minVal = state.openetRanges.min;
        maxVal = state.openetRanges.max;
        unit = layer.units || LAYER_UNITS[mode] || 'mm';
      }
    } else if (layer.isCumulative) {
      minVal = 0;
      maxVal = 100;
      unit = '%';
    } else if (layer.bandKey && state.rapSummary) {
      minVal = 0;
      maxVal = 100;
      unit = '%';
    }

    const colormap = layer.colormap || resolveColormapName(mode, layer.category, { WATER_MEASURES, SOIL_MEASURES });
    const continuousEditor = resolveContinuousLegendEditor(layer, mode, minVal, maxVal);
    return renderContinuousLegend(minVal, maxVal, unit, colormap, continuousEditor);
  }

  function updateLegendsPanel() {
    const contentEl = legendsContentEl || document.getElementById('gl-legends-content');
    const emptyEl = legendEmptyEl || document.getElementById('gl-legend-empty');
    if (!contentEl) return;

    const state = getState();
    const activeLayers = layerUtils.getActiveLayersForLegend();

    const children = Array.from(contentEl.children);
    for (const child of children) {
      if (child.id !== 'gl-legend-empty') {
        child.remove();
      }
    }

    if (!activeLayers.length) {
      if (emptyEl) emptyEl.style.display = '';
      return;
    }

    if (emptyEl) emptyEl.style.display = 'none';

    for (const layer of activeLayers) {
      const legendSection = renderLegendForLayer(layer, state);
      contentEl.appendChild(legendSection);
    }
  }

  return updateLegendsPanel;
}
