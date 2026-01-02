import { describe, expect, it } from '@jest/globals';
import { applyNoaaAvailability, renderFrequencyTable } from '../ui/frequency-table.js';

function buildTable() {
  document.body.innerHTML = `
    <table id="storm_event_wepp_frequency">
      <thead>
        <tr data-storm-event-analyzer-ari-header-row="wepp">
          <th scope="col">Metric</th>
          <th scope="col" class="wc-text-right" data-storm-event-analyzer-ari-header>ARI</th>
          <th scope="col">Units</th>
        </tr>
      </thead>
      <tbody>
        <tr data-storm-event-analyzer-ari-unit-row="wepp">
          <td data-storm-event-analyzer-unit="wepp-metric">&nbsp;</td>
          <td class="wc-text-right" data-storm-event-analyzer-unit="wepp-ari">&nbsp;</td>
          <td data-storm-event-analyzer-unit="wepp-units">&nbsp;</td>
        </tr>
      </tbody>
    </table>
    <p data-noaa-unavailable hidden>NOAA Atlas 14 data unavailable.</p>
  `;
  return document.getElementById('storm_event_wepp_frequency');
}

describe('storm-event-analyzer frequency table rendering', () => {
  it('renders dynamic headers and rows with selection state', () => {
    const table = buildTable();
    const data = {
      recurrence: [1, 2],
      rows: [
        {
          label: '10-min intensity',
          displayLabel: '10-min intensity',
          durationMinutes: 10,
          values: [10, 20],
        },
      ],
    };
    const selectedMetric = {
      table: 'wepp',
      durationMinutes: 10,
      ari: 2,
      value: 20,
    };

    renderFrequencyTable({ table, data, tableKey: 'wepp', selectedMetric, unitizer: null, onSelect: () => {} });

    const headerCells = table.querySelectorAll('thead th');
    expect(headerCells).toHaveLength(4);
    expect(headerCells[1].textContent).toBe('1');
    expect(headerCells[2].textContent).toBe('2');

    const metricCells = table.querySelectorAll('[data-storm-event-analyzer-cell]');
    expect(metricCells).toHaveLength(2);

    const selected = Array.from(metricCells).find((cell) => cell.classList.contains('is-selected'));
    expect(selected).toBeTruthy();
    expect(selected.getAttribute('aria-selected')).toBe('true');
  });

  it('toggles NOAA availability messaging', () => {
    const table = buildTable();
    const message = document.querySelector('[data-noaa-unavailable]');

    applyNoaaAvailability({ table, message, available: false });
    expect(table.hasAttribute('hidden')).toBe(true);
    expect(message.hasAttribute('hidden')).toBe(false);

    applyNoaaAvailability({ table, message, available: true });
    expect(table.hasAttribute('hidden')).toBe(false);
    expect(message.hasAttribute('hidden')).toBe(true);
  });
});
