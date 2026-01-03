import { describe, expect, it, jest } from '@jest/globals';
import { renderEventTable, updateEventSelection } from '../ui/event-table.js';

function buildEventTable() {
  document.body.innerHTML = `
    <table id="storm_event_characteristics_table">
      <tbody>
        <tr data-sort-position="top">
          <td data-storm-event-analyzer-unit="select"></td>
          <td data-storm-event-analyzer-unit="measure"></td>
          <td data-storm-event-analyzer-unit="date"></td>
          <td data-storm-event-analyzer-unit="depth"></td>
          <td data-storm-event-analyzer-unit="duration"></td>
          <td data-storm-event-analyzer-unit="saturation"></td>
          <td data-storm-event-analyzer-unit="snow-coverage"></td>
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
        depth_mm: 5,
        duration_hours: 1,
        soil_saturation_pct: 20,
        snow_coverage_t1_pct: 0,
        peak_discharge_m3s: 0.5,
      },
      {
        sim_day_index: 102,
        date: '2026-01-02',
        measure_value: 12,
        depth_mm: 6,
        duration_hours: 2,
        soil_saturation_pct: 30,
        snow_coverage_t1_pct: 1,
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

    const selectedRadio = renderedRows[1].querySelector('input[type="radio"]');
    expect(selectedRadio).toBeTruthy();
    expect(selectedRadio.checked).toBe(true);
  });

  it('fires selection callback when a radio is clicked', () => {
    const table = buildEventTable();
    const rows = [
      {
        sim_day_index: 200,
        date: '2026-02-01',
        measure_value: 11,
        depth_mm: 4,
        duration_hours: 1.5,
        soil_saturation_pct: 25,
        snow_coverage_t1_pct: 0,
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

    const radio = table.querySelector('tbody tr:not([data-sort-position="top"]) input[type="radio"]');
    radio.click();

    expect(onSelect).toHaveBeenCalledWith(200);
  });

  it('fires selection callback when a row is clicked', () => {
    const table = buildEventTable();
    const rows = [
      {
        sim_day_index: 210,
        date: '2026-02-10',
        measure_value: 13,
        depth_mm: 4,
        duration_hours: 1.0,
        soil_saturation_pct: 25,
        snow_coverage_t1_pct: 0,
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

    expect(onSelect).toHaveBeenCalledWith(210);
  });

  it('updates selection without re-rendering', () => {
    const table = buildEventTable();
    const rows = [
      {
        sim_day_index: 201,
        date: '2026-02-02',
        measure_value: 11,
        depth_mm: 4,
        duration_hours: 1.5,
        soil_saturation_pct: 25,
        snow_coverage_t1_pct: 0,
        peak_discharge_m3s: 0.4,
      },
      {
        sim_day_index: 202,
        date: '2026-02-03',
        measure_value: 12,
        depth_mm: 5,
        duration_hours: 2.0,
        soil_saturation_pct: 30,
        snow_coverage_t1_pct: 0.5,
        peak_discharge_m3s: 0.6,
      },
    ];

    renderEventTable({
      table,
      rows,
      selectedEventSimDayIndex: null,
      unitizer: null,
      onSelect: () => {},
    });

    updateEventSelection({ table, selectedEventSimDayIndex: 202 });

    const renderedRows = table.querySelectorAll('tbody tr:not([data-sort-position="top"])');
    expect(renderedRows[1].classList.contains('is-selected')).toBe(true);
    const selectedRadio = renderedRows[1].querySelector('input[type="radio"]');
    expect(selectedRadio.checked).toBe(true);
  });
});
