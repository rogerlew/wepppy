import { describe, expect, it, jest } from '@jest/globals';
import { renderEventTable } from '../ui/event-table.js';

function buildEventTable() {
  document.body.innerHTML = `
    <table id="storm_event_characteristics_table">
      <tbody>
        <tr data-sort-position="top">
          <td data-storm-event-analyzer-unit="measure"></td>
          <td data-storm-event-analyzer-unit="date"></td>
          <td data-storm-event-analyzer-unit="precip"></td>
          <td data-storm-event-analyzer-unit="depth"></td>
          <td data-storm-event-analyzer-unit="duration"></td>
          <td data-storm-event-analyzer-unit="saturation"></td>
          <td data-storm-event-analyzer-unit="snow-water"></td>
          <td data-storm-event-analyzer-unit="peak-discharge"></td>
        </tr>
      </tbody>
    </table>
  `;
  return document.getElementById('storm_event_characteristics_table');
}

describe('storm-event-analyzer event table rendering', () => {
  it('renders rows and highlights the selected event', () => {
    const table = buildEventTable();
    const rows = [
      {
        sim_day_index: 101,
        date: '2026-01-01',
        measure_value: 10,
        precip_mm: 5,
        depth_mm: 5,
        duration_hours: 1,
        soil_saturation_pct: 20,
        snow_water_t1_mm: 0,
        peak_discharge_m3s: 0.5,
      },
      {
        sim_day_index: 102,
        date: '2026-01-02',
        measure_value: 12,
        precip_mm: 6,
        depth_mm: 6,
        duration_hours: 2,
        soil_saturation_pct: 30,
        snow_water_t1_mm: 1,
        peak_discharge_m3s: 0.7,
      },
    ];

    renderEventTable({
      table,
      rows,
      selectedEventSimDayIndex: 102,
      unitizer: null,
      onSelect: () => {},
    });

    const renderedRows = table.querySelectorAll('tbody tr:not([data-sort-position="top"])');
    expect(renderedRows).toHaveLength(2);
    expect(renderedRows[1].classList.contains('is-selected')).toBe(true);
    expect(renderedRows[1].getAttribute('aria-selected')).toBe('true');
  });

  it('fires selection callback when a row is clicked', () => {
    const table = buildEventTable();
    const rows = [
      {
        sim_day_index: 200,
        date: '2026-02-01',
        measure_value: 11,
        precip_mm: 4,
        depth_mm: 4,
        duration_hours: 1.5,
        soil_saturation_pct: 25,
        snow_water_t1_mm: 0,
        peak_discharge_m3s: 0.4,
      },
    ];
    const onSelect = jest.fn();

    renderEventTable({
      table,
      rows,
      selectedEventSimDayIndex: null,
      unitizer: null,
      onSelect,
    });

    const row = table.querySelector('tbody tr:not([data-sort-position="top"])');
    row.click();

    expect(onSelect).toHaveBeenCalledWith(200);
  });
});
