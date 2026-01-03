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

export function renderHydrologySummary({ section, row, unitizer, tcAvailable, selectedMetric }) {
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

  const selectedMeasureLabel = buildSelectedMeasureLabel(selectedMetric);
  const selectedMeasureCell = section.querySelector('[data-storm-event-analyzer-summary-label="selected-measure"]');
  if (selectedMeasureCell) {
    selectedMeasureCell.textContent = selectedMeasureLabel;
  }

  const values = {
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
    'runoff-coefficient': row && Number.isFinite(row.runoff_coefficient) ? row.runoff_coefficient * 100 : null,
  };

  const units = {
    date: 'YY-MM-DD',
    depth: 'mm',
    duration: 'hours',
    'selected-measure': selectedMetric ? selectedMetric.unitKey || '' : '',
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

  Object.entries(values).forEach(([key, value]) => {
    if (key === 'tc' && !tcAvailable) {
      return;
    }
    const valueCell = section.querySelector(`[data-storm-event-analyzer-summary="${key}"]`);
    const unitCell = section.querySelector(`[data-storm-event-analyzer-unit="summary-${key}"]`);
    const unitKey = units[key];
    setValueCell(valueCell, value, unitKey, unitizer, placeholder);
    setUnitCell(unitCell, unitKey, unitizer);
  });
}
