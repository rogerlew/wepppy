import { describe, expect, it } from '@jest/globals';
import { renderHydrologySummary } from '../ui/hydrology-summary.js';

function buildSummarySection() {
  document.body.innerHTML = `
    <section id="storm-event-analyzer__summary">
      <table id="storm_event_hydrology_summary">
        <tbody>
          <tr>
            <th scope="row">Runoff</th>
            <td data-storm-event-analyzer-summary="runoff">--</td>
            <td data-storm-event-analyzer-unit="summary-runoff">--</td>
          </tr>
          <tr>
            <th scope="row">Runoff volume</th>
            <td data-storm-event-analyzer-summary="runoff-volume">--</td>
            <td data-storm-event-analyzer-unit="summary-runoff-volume">--</td>
          </tr>
          <tr>
            <th scope="row">Tc</th>
            <td data-storm-event-analyzer-summary="tc">--</td>
            <td data-storm-event-analyzer-unit="summary-tc">--</td>
          </tr>
          <tr>
            <th scope="row">Peak discharge</th>
            <td data-storm-event-analyzer-summary="peak-discharge">--</td>
            <td data-storm-event-analyzer-unit="summary-peak-discharge">--</td>
          </tr>
          <tr>
            <th scope="row">Sediment yield</th>
            <td data-storm-event-analyzer-summary="sediment-yield">--</td>
            <td data-storm-event-analyzer-unit="summary-sediment-yield">--</td>
          </tr>
          <tr>
            <th scope="row">Runoff coefficient</th>
            <td data-storm-event-analyzer-summary="runoff-coefficient">--</td>
            <td data-storm-event-analyzer-unit="summary-runoff-coefficient">--</td>
          </tr>
        </tbody>
      </table>
      <p data-empty-state hidden>Select an event to view hydrology details.</p>
    </section>
  `;
  return document.getElementById('storm-event-analyzer__summary');
}

describe('storm-event-analyzer hydrology summary rendering', () => {
  it('shows empty state when no event is selected', () => {
    const section = buildSummarySection();

    renderHydrologySummary({ section, row: null, unitizer: null, tcAvailable: true });

    const emptyState = section.querySelector('[data-empty-state]');
    expect(emptyState.hasAttribute('hidden')).toBe(false);
    const runoffCell = section.querySelector('[data-storm-event-analyzer-summary="runoff"]');
    expect(runoffCell.textContent).toBe('--');
  });

  it('hides the Tc row when tc_out is unavailable', () => {
    const section = buildSummarySection();

    renderHydrologySummary({
      section,
      row: {
        runoff_mm: 12,
        runoff_volume_m3: 50,
        tc_hours: 0.5,
        peak_discharge_m3s: 1.2,
        sediment_yield_kg: 10,
        runoff_coefficient: 0.2,
      },
      unitizer: null,
      tcAvailable: false,
    });

    const tcCell = section.querySelector('[data-storm-event-analyzer-summary="tc"]');
    const tcRow = tcCell.closest('tr');
    expect(tcRow.hasAttribute('hidden')).toBe(true);
  });

  it('renders values and placeholder for missing Tc', () => {
    const section = buildSummarySection();
    const unitizer = {
      renderValue: (value, unitKey) => `${value}:${unitKey}`,
      renderUnits: (unitKey) => `units:${unitKey}`,
    };

    renderHydrologySummary({
      section,
      row: {
        runoff_mm: 12,
        runoff_volume_m3: 50,
        tc_hours: null,
        peak_discharge_m3s: 1.2,
        sediment_yield_kg: 10,
        runoff_coefficient: 0.2,
      },
      unitizer,
      tcAvailable: true,
    });

    const runoffCell = section.querySelector('[data-storm-event-analyzer-summary="runoff"]');
    expect(runoffCell.textContent).toBe('12:mm');
    const tcCell = section.querySelector('[data-storm-event-analyzer-summary="tc"]');
    expect(tcCell.textContent).toBe('\u2014');
    expect(tcCell.classList.contains('wc-text-muted')).toBe(true);
  });
});
