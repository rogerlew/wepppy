import { describe, expect, it } from '@jest/globals';
import { renderHydrologySummary } from '../ui/hydrology-summary.js';

function buildSummarySection() {
  document.body.innerHTML = `
    <section id="storm-event-analyzer__summary">
      <table id="storm_event_hydrology_summary">
        <thead>
          <tr>
            <th scope="col">Metric</th>
            <th scope="col" data-storm-event-analyzer-summary-label="base">Undisturbed</th>
            <th scope="col" data-storm-event-analyzer-summary-label="scenario">Scenario</th>
            <th scope="col">Units</th>
            <th scope="col" data-storm-event-analyzer-summary-label="change">% change</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row">Date</th>
            <td data-storm-event-analyzer-summary="date">--</td>
            <td data-storm-event-analyzer-summary="date-scenario">--</td>
            <td data-storm-event-analyzer-unit="summary-date">--</td>
            <td data-storm-event-analyzer-summary="date-change">--</td>
          </tr>
          <tr>
            <th scope="row">Depth</th>
            <td data-storm-event-analyzer-summary="depth">--</td>
            <td data-storm-event-analyzer-summary="depth-scenario">--</td>
            <td data-storm-event-analyzer-unit="summary-depth">--</td>
            <td data-storm-event-analyzer-summary="depth-change">--</td>
          </tr>
          <tr>
            <th scope="row">Duration</th>
            <td data-storm-event-analyzer-summary="duration">--</td>
            <td data-storm-event-analyzer-summary="duration-scenario">--</td>
            <td data-storm-event-analyzer-unit="summary-duration">--</td>
            <td data-storm-event-analyzer-summary="duration-change">--</td>
          </tr>
          <tr>
            <th scope="row" data-storm-event-analyzer-summary-label="selected-measure">Selected measure</th>
            <td data-storm-event-analyzer-summary="selected-measure">--</td>
            <td data-storm-event-analyzer-summary="selected-measure-scenario">--</td>
            <td data-storm-event-analyzer-unit="summary-selected-measure">--</td>
            <td data-storm-event-analyzer-summary="selected-measure-change">--</td>
          </tr>
          <tr>
            <th scope="row">Soil saturation <sub>T-1</sub></th>
            <td data-storm-event-analyzer-summary="soil-saturation">--</td>
            <td data-storm-event-analyzer-summary="soil-saturation-scenario">--</td>
            <td data-storm-event-analyzer-unit="summary-soil-saturation">--</td>
            <td data-storm-event-analyzer-summary="soil-saturation-change">--</td>
          </tr>
          <tr>
            <th scope="row">Snow coverage <sub>T-1</sub></th>
            <td data-storm-event-analyzer-summary="snow-coverage">--</td>
            <td data-storm-event-analyzer-summary="snow-coverage-scenario">--</td>
            <td data-storm-event-analyzer-unit="summary-snow-coverage">--</td>
            <td data-storm-event-analyzer-summary="snow-coverage-change">--</td>
          </tr>
          <tr>
            <th scope="row">Snow-Water equivalent <sub>T-1</sub></th>
            <td data-storm-event-analyzer-summary="snow-water">--</td>
            <td data-storm-event-analyzer-summary="snow-water-scenario">--</td>
            <td data-storm-event-analyzer-unit="summary-snow-water">--</td>
            <td data-storm-event-analyzer-summary="snow-water-change">--</td>
          </tr>
          <tr>
            <th scope="row">Runoff</th>
            <td data-storm-event-analyzer-summary="runoff">--</td>
            <td data-storm-event-analyzer-summary="runoff-scenario">--</td>
            <td data-storm-event-analyzer-unit="summary-runoff">--</td>
            <td data-storm-event-analyzer-summary="runoff-change">--</td>
          </tr>
          <tr>
            <th scope="row">Runoff volume</th>
            <td data-storm-event-analyzer-summary="runoff-volume">--</td>
            <td data-storm-event-analyzer-summary="runoff-volume-scenario">--</td>
            <td data-storm-event-analyzer-unit="summary-runoff-volume">--</td>
            <td data-storm-event-analyzer-summary="runoff-volume-change">--</td>
          </tr>
          <tr>
            <th scope="row">Tc</th>
            <td data-storm-event-analyzer-summary="tc">--</td>
            <td data-storm-event-analyzer-summary="tc-scenario">--</td>
            <td data-storm-event-analyzer-unit="summary-tc">--</td>
            <td data-storm-event-analyzer-summary="tc-change">--</td>
          </tr>
          <tr>
            <th scope="row">Peak discharge</th>
            <td data-storm-event-analyzer-summary="peak-discharge">--</td>
            <td data-storm-event-analyzer-summary="peak-discharge-scenario">--</td>
            <td data-storm-event-analyzer-unit="summary-peak-discharge">--</td>
            <td data-storm-event-analyzer-summary="peak-discharge-change">--</td>
          </tr>
          <tr>
            <th scope="row">Sediment yield</th>
            <td data-storm-event-analyzer-summary="sediment-yield">--</td>
            <td data-storm-event-analyzer-summary="sediment-yield-scenario">--</td>
            <td data-storm-event-analyzer-unit="summary-sediment-yield">--</td>
            <td data-storm-event-analyzer-summary="sediment-yield-change">--</td>
          </tr>
          <tr>
            <th scope="row">Runoff coefficient</th>
            <td data-storm-event-analyzer-summary="runoff-coefficient">--</td>
            <td data-storm-event-analyzer-summary="runoff-coefficient-scenario">--</td>
            <td data-storm-event-analyzer-unit="summary-runoff-coefficient">--</td>
            <td data-storm-event-analyzer-summary="runoff-coefficient-change">--</td>
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

    renderHydrologySummary({
      section,
      row: null,
      unitizer: null,
      tcAvailable: true,
      selectedMetric: null,
      omniScenario: null,
      omniSummary: null,
      baseScenarioLabel: 'Undisturbed',
    });

    const emptyState = section.querySelector('[data-empty-state]');
    expect(emptyState.hasAttribute('hidden')).toBe(false);
    const runoffCell = section.querySelector('[data-storm-event-analyzer-summary="runoff"]');
    expect(runoffCell.textContent).toBe('--');
    const runoffScenarioCell = section.querySelector('[data-storm-event-analyzer-summary="runoff-scenario"]');
    expect(runoffScenarioCell.textContent).toBe('\u2014');
    const runoffChangeCell = section.querySelector('[data-storm-event-analyzer-summary="runoff-change"]');
    expect(runoffChangeCell.textContent).toBe('\u2014');
    const scenarioHeader = section.querySelector('[data-storm-event-analyzer-summary-label="scenario"]');
    expect(scenarioHeader.hasAttribute('hidden')).toBe(true);
    const changeHeader = section.querySelector('[data-storm-event-analyzer-summary-label="change"]');
    expect(changeHeader.hasAttribute('hidden')).toBe(true);
  });

  it('updates the selected measure label based on the selected metric', () => {
    const section = buildSummarySection();

    renderHydrologySummary({
      section,
      row: null,
      unitizer: null,
      tcAvailable: true,
      selectedMetric: {
        table: 'wepp',
        label: '15-min intensity',
        ari: 10,
        unitKey: 'mm/hour',
      },
      omniScenario: null,
      omniSummary: null,
      baseScenarioLabel: 'Undisturbed',
    });

    const labelCell = section.querySelector('[data-storm-event-analyzer-summary-label="selected-measure"]');
    expect(labelCell.textContent).toBe('WEPP Climate 15-min intensity 10-year ARI');
  });

  it('updates the base and scenario column labels when a scenario is selected', () => {
    const section = buildSummarySection();

    renderHydrologySummary({
      section,
      row: null,
      unitizer: null,
      tcAvailable: true,
      selectedMetric: null,
      omniScenario: { name: 'Mulch 30', path: '_pups/omni/scenarios/mulch_30' },
      omniSummary: null,
      baseScenarioLabel: 'Burned',
    });

    const baseLabel = section.querySelector('[data-storm-event-analyzer-summary-label="base"]');
    expect(baseLabel.textContent).toBe('Burned');
    const scenarioLabel = section.querySelector('[data-storm-event-analyzer-summary-label="scenario"]');
    expect(scenarioLabel.textContent).toBe('Mulch 30');
    expect(scenarioLabel.hasAttribute('hidden')).toBe(false);
    const changeLabel = section.querySelector('[data-storm-event-analyzer-summary-label="change"]');
    expect(changeLabel.hasAttribute('hidden')).toBe(false);
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
        date: '2024-06-03',
        depth_mm: 20,
        duration_hours: 2,
        measure_value: 30,
        soil_saturation_pct: 35,
        snow_coverage_t1_pct: 15,
        snow_water_t1_mm: 12,
      },
      unitizer: null,
      tcAvailable: false,
      selectedMetric: {
        table: 'wepp',
        label: '15-min intensity',
        ari: 10,
        unitKey: 'mm/hour',
      },
      omniScenario: null,
      omniSummary: null,
      baseScenarioLabel: 'Undisturbed',
    });

    const tcCell = section.querySelector('[data-storm-event-analyzer-summary="tc"]');
    const tcRow = tcCell.closest('tr');
    expect(tcRow.hasAttribute('hidden')).toBe(true);
  });

  it('renders values, scenario comparison, and placeholder for missing data', () => {
    const section = buildSummarySection();
    const unitizer = {
      renderValue: (value, unitKey) => `${value}:${unitKey}`,
      renderUnits: (unitKey) => `units:${unitKey}`,
    };

    renderHydrologySummary({
      section,
      row: {
        date: '2024-06-03',
        depth_mm: 20,
        duration_hours: 2,
        measure_value: 30,
        soil_saturation_pct: 35,
        snow_coverage_t1_pct: 15,
        snow_water_t1_mm: null,
        runoff_mm: 12,
        runoff_volume_m3: 50,
        tc_hours: null,
        peak_discharge_m3s: 1.2,
        sediment_yield_kg: 10,
        runoff_coefficient: 0.2,
      },
      unitizer,
      tcAvailable: true,
      selectedMetric: {
        table: 'noaa',
        label: '15-min intensity',
        ari: 10,
        unitKey: 'mm/hour',
      },
      omniScenario: { name: 'Mulch 30', path: '_pups/omni/scenarios/mulch_30' },
      omniSummary: {
        date: '2024-06-03',
        depth_mm: 24,
        duration_hours: 2,
        measure_value: 36,
        soil_saturation_pct: 40,
        snow_coverage_t1_pct: 10,
        snow_water_t1_mm: 5,
        runoff_mm: 18,
        runoff_volume_m3: 75,
        tc_hours: null,
        peak_discharge_m3s: 1.5,
        sediment_yield_kg: 12,
        runoff_coefficient: 0.3,
      },
      baseScenarioLabel: 'Undisturbed',
    });

    const dateCell = section.querySelector('[data-storm-event-analyzer-summary="date"]');
    expect(dateCell.textContent).toBe('2024-06-03:YY-MM-DD');
    const selectedMeasureCell = section.querySelector('[data-storm-event-analyzer-summary="selected-measure"]');
    expect(selectedMeasureCell.textContent).toBe('30:mm/hour');
    const snowWaterCell = section.querySelector('[data-storm-event-analyzer-summary="snow-water"]');
    expect(snowWaterCell.textContent).toBe('\u2014');
    expect(snowWaterCell.classList.contains('wc-text-muted')).toBe(true);
    const snowWaterScenarioCell = section.querySelector('[data-storm-event-analyzer-summary="snow-water-scenario"]');
    expect(snowWaterScenarioCell.textContent).toBe('5:mm');
    const snowWaterChangeCell = section.querySelector('[data-storm-event-analyzer-summary="snow-water-change"]');
    expect(snowWaterChangeCell.textContent).toBe('\u2014');
    const selectedMeasureUnit = section.querySelector(
      '[data-storm-event-analyzer-unit="summary-selected-measure"]',
    );
    expect(selectedMeasureUnit.textContent).toBe('units:mm/hour');
    const runoffCell = section.querySelector('[data-storm-event-analyzer-summary="runoff"]');
    expect(runoffCell.textContent).toBe('12:mm');
    const runoffScenarioCell = section.querySelector('[data-storm-event-analyzer-summary="runoff-scenario"]');
    expect(runoffScenarioCell.textContent).toBe('18:mm');
    const runoffChangeCell = section.querySelector('[data-storm-event-analyzer-summary="runoff-change"]');
    expect(runoffChangeCell.textContent).toBe('50.0');
    const tcCell = section.querySelector('[data-storm-event-analyzer-summary="tc"]');
    expect(tcCell.textContent).toBe('\u2014');
    expect(tcCell.classList.contains('wc-text-muted')).toBe(true);
  });
});
