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

function setUnitCell(cell, unitizer, unitKey) {
  if (!cell) return;
  applyHtml(cell, unitKey ? renderUnits(unitizer, unitKey) : '&nbsp;');
}

function updateUnitRow(table, unitizer) {
  if (!table) return;
  const units = {
    measure: 'mm/hour',
    date: null,
    precip: 'mm',
    depth: 'mm',
    duration: 'hours',
    saturation: 'pct',
    'snow-water': 'mm',
    'peak-discharge': 'm^3/s',
  };

  Object.entries(units).forEach(([key, unitKey]) => {
    const cell = table.querySelector(`[data-storm-event-analyzer-unit="${key}"]`);
    setUnitCell(cell, unitizer, unitKey);
  });
}

function clearRows(tbody) {
  if (!tbody) return;
  Array.from(tbody.querySelectorAll('tr')).forEach((row) => {
    if (row.getAttribute('data-sort-position') === 'top') {
      return;
    }
    row.remove();
  });
}

function setSortKey(cell, value) {
  if (!cell) return;
  if (value === null || value === undefined || Number.isNaN(value)) {
    return;
  }
  cell.setAttribute('sorttable_customkey', String(value));
}

export function renderEventTable({ table, rows, selectedEventSimDayIndex, unitizer, onSelect }) {
  if (!table) {
    return;
  }
  const tbody = table.tBodies[0] || table.createTBody();
  updateUnitRow(table, unitizer);
  clearRows(tbody);

  rows.forEach((row) => {
    const tr = document.createElement('tr');
    tr.classList.add('storm-event-analyzer__event-row');
    tr.dataset.simDayIndex = String(row.sim_day_index);

    if (Number(row.sim_day_index) === Number(selectedEventSimDayIndex)) {
      tr.classList.add('is-selected');
      tr.setAttribute('aria-selected', 'true');
    } else {
      tr.setAttribute('aria-selected', 'false');
    }

    const measureCell = document.createElement('td');
    measureCell.className = 'wc-text-right';
    applyHtml(measureCell, renderValue(unitizer, row.measure_value, 'mm/hour'));
    setSortKey(measureCell, row.measure_value);
    tr.appendChild(measureCell);

    const dateCell = document.createElement('td');
    dateCell.textContent = row.date || '';
    setSortKey(dateCell, row.date || '');
    tr.appendChild(dateCell);

    const precipCell = document.createElement('td');
    precipCell.className = 'wc-text-right';
    applyHtml(precipCell, renderValue(unitizer, row.precip_mm, 'mm'));
    setSortKey(precipCell, row.precip_mm);
    tr.appendChild(precipCell);

    const depthCell = document.createElement('td');
    depthCell.className = 'wc-text-right';
    applyHtml(depthCell, renderValue(unitizer, row.depth_mm, 'mm'));
    setSortKey(depthCell, row.depth_mm);
    tr.appendChild(depthCell);

    const durationCell = document.createElement('td');
    durationCell.className = 'wc-text-right';
    applyHtml(durationCell, renderValue(unitizer, row.duration_hours, 'hours'));
    setSortKey(durationCell, row.duration_hours);
    tr.appendChild(durationCell);

    const saturationCell = document.createElement('td');
    saturationCell.className = 'wc-text-right';
    applyHtml(saturationCell, renderValue(unitizer, row.soil_saturation_pct, 'pct'));
    setSortKey(saturationCell, row.soil_saturation_pct);
    tr.appendChild(saturationCell);

    const snowCell = document.createElement('td');
    snowCell.className = 'wc-text-right';
    applyHtml(snowCell, renderValue(unitizer, row.snow_water_t1_mm, 'mm'));
    setSortKey(snowCell, row.snow_water_t1_mm);
    tr.appendChild(snowCell);

    const peakCell = document.createElement('td');
    peakCell.className = 'wc-text-right';
    applyHtml(peakCell, renderValue(unitizer, row.peak_discharge_m3s, 'm^3/s'));
    setSortKey(peakCell, row.peak_discharge_m3s);
    tr.appendChild(peakCell);

    tr.addEventListener('click', () => {
      if (typeof onSelect === 'function') {
        onSelect(row.sim_day_index);
      }
    });

    tbody.appendChild(tr);
  });
}

export function setEventErrorBanner({ banner, message }) {
  if (!banner) {
    return;
  }
  const body = banner.querySelector('[data-storm-event-analyzer-error-body]') || banner;
  if (message) {
    banner.removeAttribute('hidden');
    body.textContent = message;
  } else {
    banner.setAttribute('hidden', 'hidden');
    body.textContent = '';
  }
}
