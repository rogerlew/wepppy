import { INTENSITY_UNIT_KEY } from '../config.js';

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

function buildHeaderRow(headerRow, recurrence) {
  if (!headerRow) return;
  headerRow.innerHTML = '';

  const metricHeader = document.createElement('th');
  metricHeader.scope = 'col';
  metricHeader.textContent = 'Metric';
  headerRow.appendChild(metricHeader);

  recurrence.forEach((ari) => {
    const th = document.createElement('th');
    th.scope = 'col';
    th.className = 'wc-text-right';
    th.dataset.stormEventAnalyzerAriHeader = 'true';
    th.dataset.ari = String(ari);
    th.textContent = String(ari);
    headerRow.appendChild(th);
  });

  const unitsHeader = document.createElement('th');
  unitsHeader.scope = 'col';
  unitsHeader.textContent = 'Units';
  headerRow.appendChild(unitsHeader);
}

function buildUnitsRow(unitRow, recurrence, unitKey, tableKey, unitizer) {
  if (!unitRow) return;
  unitRow.innerHTML = '';

  const metricCell = document.createElement('td');
  metricCell.dataset.stormEventAnalyzerUnit = `${tableKey}-metric`;
  metricCell.innerHTML = '&nbsp;';
  unitRow.appendChild(metricCell);

  recurrence.forEach((ari) => {
    const cell = document.createElement('td');
    cell.className = 'wc-text-right';
    cell.dataset.stormEventAnalyzerUnit = `${tableKey}-ari`;
    cell.dataset.unitKey = unitKey;
    cell.dataset.ari = String(ari);
    applyHtml(cell, renderUnits(unitizer, unitKey));
    unitRow.appendChild(cell);
  });

  const unitsCell = document.createElement('td');
  unitsCell.dataset.stormEventAnalyzerUnit = `${tableKey}-units`;
  unitsCell.dataset.unitKey = unitKey;
  applyHtml(unitsCell, renderUnits(unitizer, unitKey));
  unitRow.appendChild(unitsCell);
}

function buildMetricRows({ tbody, recurrence, rows, tableKey, unitKey, unitizer, selectedMetric, onSelect }) {
  rows.forEach((row) => {
    const tr = document.createElement('tr');

    const labelCell = document.createElement('th');
    labelCell.scope = 'row';
    labelCell.textContent = row.displayLabel || row.label;
    tr.appendChild(labelCell);

    recurrence.forEach((ari, idx) => {
      const value = row.values[idx];
      const td = document.createElement('td');
      td.className = 'wc-text-right storm-event-analyzer__metric-cell';
      td.dataset.stormEventAnalyzerCell = 'true';
      td.dataset.durationMinutes = String(row.durationMinutes || '');
      td.dataset.ari = String(ari);
      td.dataset.unitKey = unitKey;

      if (value === null || value === undefined || value === '') {
        td.setAttribute('aria-disabled', 'true');
        td.innerHTML = '&mdash;';
      } else {
        td.dataset.value = String(value);
        td.setAttribute('role', 'button');
        td.tabIndex = 0;
        td.setAttribute('aria-selected', 'false');
        applyHtml(td, renderValue(unitizer, value, unitKey));

        td.addEventListener('click', () => {
          if (typeof onSelect === 'function') {
            onSelect({
              table: tableKey,
              durationMinutes: row.durationMinutes,
              ari,
              value,
              unitKey,
              label: row.displayLabel || row.label,
            });
          }
        });
        td.addEventListener('keydown', (event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            td.click();
          }
        });
      }

      if (
        selectedMetric &&
        selectedMetric.table === tableKey &&
        Number(selectedMetric.durationMinutes) === Number(row.durationMinutes) &&
        Number(selectedMetric.ari) === Number(ari)
      ) {
        td.classList.add('is-selected');
        td.setAttribute('aria-selected', 'true');
      }

      tr.appendChild(td);
    });

    const unitsCell = document.createElement('td');
    unitsCell.dataset.stormEventAnalyzerUnit = `${tableKey}-row-unit`;
    unitsCell.dataset.unitKey = unitKey;
    applyHtml(unitsCell, renderUnits(unitizer, unitKey));
    tr.appendChild(unitsCell);

    tbody.appendChild(tr);
  });
}

export function renderFrequencyTable({
  table,
  data,
  tableKey,
  unitizer,
  selectedMetric,
  onSelect,
  unitKey = INTENSITY_UNIT_KEY,
}) {
  if (!table || !data) {
    return;
  }

  const headerRow = table.querySelector('[data-storm-event-analyzer-ari-header-row]');
  const unitRow = table.querySelector('[data-storm-event-analyzer-ari-unit-row]');
  const tbody = table.tBodies[0] || table.createTBody();

  buildHeaderRow(headerRow, data.recurrence);

  tbody.innerHTML = '';
  if (unitRow) {
    buildUnitsRow(unitRow, data.recurrence, unitKey, tableKey, unitizer);
    tbody.appendChild(unitRow);
  }

  buildMetricRows({
    tbody,
    recurrence: data.recurrence,
    rows: data.rows,
    tableKey,
    unitKey,
    unitizer,
    selectedMetric,
    onSelect,
  });
}

export function applyNoaaAvailability({ table, message, available }) {
  if (table) {
    if (available) {
      table.removeAttribute('hidden');
    } else {
      table.setAttribute('hidden', 'hidden');
    }
  }

  if (message) {
    if (available) {
      message.setAttribute('hidden', 'hidden');
    } else {
      message.removeAttribute('hidden');
    }
  }
}
