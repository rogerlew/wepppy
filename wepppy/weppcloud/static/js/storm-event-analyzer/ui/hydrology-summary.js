function applyHtml(target, html) {
  if (!target) return;
  if (typeof window !== 'undefined' && typeof window.applyLabelHtml === 'function') {
    window.applyLabelHtml(target, html);
    return;
  }
  target.innerHTML = html;
}

function renderUnits(unitizer, unitKey) {
  if (unitizer && typeof unitizer.renderUnits === 'function') {
    return unitizer.renderUnits(unitKey);
  }
  return unitKey || '';
}

function renderValue(unitizer, value, unitKey) {
  if (value === null || value === undefined || value === '') {
    return '&mdash;';
  }
  if (unitizer && typeof unitizer.renderValue === 'function') {
    return unitizer.renderValue(value, unitKey);
  }
  return String(value);
}

function formatChangeValue(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return null;
  }
  return numeric.toFixed(1);
}

function setScenarioColumnsVisible(section, visible) {
  const scenarioCells = section.querySelectorAll('[data-storm-event-analyzer-summary$="-scenario"]');
  const changeCells = section.querySelectorAll('[data-storm-event-analyzer-summary$="-change"]');
  const scenarioHeader = section.querySelectorAll('[data-storm-event-analyzer-summary-label="scenario"]');
  const changeHeader = section.querySelectorAll('[data-storm-event-analyzer-summary-label="change"]');
  const targets = [...scenarioCells, ...changeCells, ...scenarioHeader, ...changeHeader];
  targets.forEach((cell) => {
    if (visible) {
      cell.removeAttribute('hidden');
    } else {
      cell.setAttribute('hidden', 'hidden');
    }
  });
}

function setValueCell(cell, value, unitKey, unitizer, placeholder) {
  if (!cell) return;
  if (value === null || value === undefined || value === '') {
    cell.classList.add('wc-text-muted');
    cell.innerHTML = placeholder;
    return;
  }
  cell.classList.remove('wc-text-muted');
  applyHtml(cell, renderValue(unitizer, value, unitKey));
}

function setChangeCell(cell, value, placeholder) {
  if (!cell) return;
  if (value === null || value === undefined || value === '') {
    cell.classList.add('wc-text-muted');
    cell.innerHTML = placeholder;
    return;
  }
  const formatted = formatChangeValue(value);
  if (formatted === null) {
    cell.classList.add('wc-text-muted');
    cell.innerHTML = placeholder;
    return;
  }
  cell.classList.remove('wc-text-muted');
  cell.textContent = formatted;
}

function setUnitCell(cell, unitKey, unitizer) {
  if (!cell) return;
  applyHtml(cell, renderUnits(unitizer, unitKey));
}

function buildSelectedMeasureLabel(selectedMetric) {
  if (!selectedMetric) {
    return 'Selected measure';
  }
  const prefix =
    selectedMetric.table === 'wepp'
      ? 'WEPP Climate'
      : selectedMetric.table === 'noaa'
        ? 'NOAA Atlas 14'
        : 'Selected measure';
  const label = selectedMetric.label || 'Selected measure';
  const ari = selectedMetric.ari || '';
  if (!ari) {
    return `${prefix} ${label}`.trim();
  }
  return `${prefix} ${label} ${ari}-year ARI`.trim();
}

function computePercentChange(baseValue, scenarioValue) {
  if (baseValue === null || baseValue === undefined || baseValue === '') {
    return null;
  }
  if (scenarioValue === null || scenarioValue === undefined || scenarioValue === '') {
    return null;
  }
  const base = Number(baseValue);
  const scenario = Number(scenarioValue);
  if (!Number.isFinite(base) || !Number.isFinite(scenario) || base === 0) {
    return null;
  }
  return ((scenario - base) / base) * 100;
}

function buildSummaryValues(row) {
  return {
    date: row ? row.date : null,
    depth: row ? row.depth_mm : null,
    duration: row ? row.duration_hours : null,
    'selected-measure': row ? row.measure_value : null,
    'soil-saturation': row ? row.soil_saturation_pct : null,
    'snow-coverage': row ? row.snow_coverage_t1_pct : null,
    'snow-water': row ? row.snow_water_t1_mm : null,
    runoff: row ? row.runoff_mm : null,
    'runoff-volume': row ? row.runoff_volume_m3 : null,
    tc: row ? row.tc_hours : null,
    'peak-discharge': row ? row.peak_discharge_m3s : null,
    'sediment-yield': row ? row.sediment_yield_kg : null,
    'runoff-coefficient':
      row && Number.isFinite(row.runoff_coefficient) ? row.runoff_coefficient * 100 : null,
  };
}

export function renderHydrologySummary({
  section,
  row,
  unitizer,
  tcAvailable,
  selectedMetric,
  omniScenario,
  omniSummary,
  baseScenarioLabel,
}) {
  if (!section) {
    return;
  }

  const emptyState = section.querySelector('[data-empty-state]');
  const hasSelection = !!row;
  if (emptyState) {
    if (hasSelection) {
      emptyState.setAttribute('hidden', 'hidden');
    } else {
      emptyState.removeAttribute('hidden');
    }
  }

  const tcCell = section.querySelector('[data-storm-event-analyzer-summary="tc"]');
  const tcRow = tcCell ? tcCell.closest('tr') : null;
  if (tcRow) {
    if (tcAvailable) {
      tcRow.removeAttribute('hidden');
    } else {
      tcRow.setAttribute('hidden', 'hidden');
    }
  }

  const placeholder = hasSelection ? '&mdash;' : '--';
  const scenarioSelected = !!omniScenario;
  const scenarioPlaceholder = scenarioSelected ? placeholder : '&mdash;';
  const changePlaceholder = scenarioSelected ? placeholder : '&mdash;';
  setScenarioColumnsVisible(section, scenarioSelected);

  const selectedMeasureLabel = buildSelectedMeasureLabel(selectedMetric);
  const selectedMeasureCell = section.querySelector('[data-storm-event-analyzer-summary-label="selected-measure"]');
  if (selectedMeasureCell) {
    selectedMeasureCell.textContent = selectedMeasureLabel;
  }

  const baseLabelCell = section.querySelector('[data-storm-event-analyzer-summary-label="base"]');
  if (baseLabelCell && baseScenarioLabel) {
    baseLabelCell.textContent = baseScenarioLabel;
  }
  const scenarioLabelCell = section.querySelector('[data-storm-event-analyzer-summary-label="scenario"]');
  if (scenarioLabelCell) {
    scenarioLabelCell.textContent = scenarioSelected && omniScenario && omniScenario.name ? omniScenario.name : 'Scenario';
  }

  const baseValues = buildSummaryValues(row);
  const scenarioValues = buildSummaryValues(omniSummary);
  const changeValues = {};
  Object.keys(baseValues).forEach((key) => {
    changeValues[key] = computePercentChange(baseValues[key], scenarioValues[key]);
  });
  const selectedMeasureUnit = selectedMetric ? selectedMetric.unitKey || '' : '';

  const units = {
    date: 'YY-MM-DD',
    depth: 'mm',
    duration: 'hours',
    'selected-measure': selectedMeasureUnit,
    'soil-saturation': '%',
    'snow-coverage': '%',
    'snow-water': 'mm',
    runoff: 'mm',
    'runoff-volume': 'm^3',
    tc: 'hours',
    'peak-discharge': 'm^3/s',
    'sediment-yield': 'kg',
    'runoff-coefficient': '%',
  };

  Object.entries(baseValues).forEach(([key, value]) => {
    if (key === 'tc' && !tcAvailable) {
      return;
    }
    const valueCell = section.querySelector(`[data-storm-event-analyzer-summary="${key}"]`);
    const scenarioCell = section.querySelector(`[data-storm-event-analyzer-summary="${key}-scenario"]`);
    const unitCell = section.querySelector(`[data-storm-event-analyzer-unit="summary-${key}"]`);
    const changeCell = section.querySelector(`[data-storm-event-analyzer-summary="${key}-change"]`);
    const unitKey = units[key];
    setValueCell(valueCell, value, unitKey, unitizer, placeholder);
    setValueCell(scenarioCell, scenarioValues[key], unitKey, unitizer, scenarioPlaceholder);
    setUnitCell(unitCell, unitKey, unitizer);
    setChangeCell(changeCell, changeValues[key], changePlaceholder);
  });
}
