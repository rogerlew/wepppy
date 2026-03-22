import { describe, expect, it, jest } from '@jest/globals';
import {
  buildEventFilterPayload,
  buildSoilPayload,
  computeIntensityRange,
  createEventDataManager,
  getIntensityColumn,
} from '../data/event-data.js';

describe('storm-event-analyzer event data helpers', () => {
  it('maps duration minutes to intensity columns', () => {
    expect(getIntensityColumn(10)).toBe('peak_intensity_10');
    expect(getIntensityColumn('15')).toBe('peak_intensity_15');
    expect(getIntensityColumn(999)).toBeNull();
  });

  it('computes intensity range from tolerance percent', () => {
    const range = computeIntensityRange(100, 10);
    expect(range.minValue).toBeCloseTo(90);
    expect(range.maxValue).toBeCloseTo(110);
  });

  it('builds event filter payload with warm-up filter', () => {
    const payload = buildEventFilterPayload({
      filterColumn: 'peak_intensity_10',
      minValue: 1,
      maxValue: 2,
      warmupYear: 1999,
    });

    const filters = payload.filters.filter((filter) => filter.column === 'ev.peak_intensity_10');
    expect(filters).toHaveLength(2);
    expect(filters[0].operator).toBe('>=');
    expect(filters[1].operator).toBe('<=');

    const warmupFilter = payload.filters.find((filter) => filter.column === 'ev.year');
    expect(warmupFilter).toEqual({ column: 'ev.year', operator: '>', value: 1999 });
  });

  it('builds soil payload using TSMF by default with legacy fallback option', () => {
    const primary = buildSoilPayload({
      filterColumn: 'peak_intensity_10',
      minValue: 1,
      maxValue: 2,
      warmupYear: null,
    });
    expect(primary.aggregations[0].sql).toBe('AVG(soil.TSMF) * 100');

    const fallback = buildSoilPayload({
      filterColumn: 'peak_intensity_10',
      minValue: 1,
      maxValue: 2,
      warmupYear: null,
      soilSaturationSource: 'saturation',
    });
    expect(fallback.aggregations[0].sql).toBe('AVG(soil.Saturation) * 100');
  });

  it('falls back to legacy Saturation when TSMF is unavailable', async () => {
    const postQueryEngine = jest.fn(async (payload) => {
      if (payload.datasets && payload.datasets.length === 1 && payload.datasets[0].alias === 'ev') {
        return {
          records: [
            {
              sim_day_index: 5,
              year: 2026,
              month: 1,
              day_of_month: 2,
              depth_mm: 10,
              precip_mm: 10,
              duration_hours: 1,
              peak_intensity_10: 10,
            },
          ],
        };
      }

      const soilAgg = payload.aggregations && payload.aggregations.find((agg) => agg.alias === 'soil_saturation_pct');
      if (soilAgg) {
        if (soilAgg.sql.includes('soil.TSMF')) {
          throw new Error('Binder Error: Referenced column "TSMF" not found in FROM clause');
        }
        return { records: [{ sim_day_index: 5, soil_saturation_pct: 41 }] };
      }

      return { records: [] };
    });

    const manager = createEventDataManager({ ctx: { runid: 'demo', config: 'disturbed' }, postQueryEngine });
    const result = await manager.fetchEventRows({
      selectedMetric: { durationMinutes: 10, value: 10 },
      filterRangePct: 10,
      includeWarmup: false,
    });

    expect(result.soilSaturationLabel).toBe('Top 0.1 m Saturation');
    expect(result.rows).toHaveLength(1);
    expect(result.rows[0].soil_saturation_pct).toBe(41);

    const soilPayloads = postQueryEngine.mock.calls
      .map(([payload]) => payload)
      .filter((payload) => payload.aggregations && payload.aggregations.some((agg) => agg.alias === 'soil_saturation_pct'));
    expect(soilPayloads).toHaveLength(2);
    expect(soilPayloads[0].aggregations[0].sql).toContain('soil.TSMF');
    expect(soilPayloads[1].aggregations[0].sql).toContain('soil.Saturation');
  });

  it('keeps missing numeric fields null and tolerates missing supporting datasets', async () => {
    const postQueryEngine = jest
      .fn()
      .mockResolvedValueOnce({
        records: [
          {
            sim_day_index: 5,
            year: 2026,
            month: 1,
            day_of_month: 2,
            depth_mm: null,
            precip_mm: null,
            duration_hours: null,
            peak_intensity_10: null,
          },
          {
            sim_day_index: 6,
            year: 2026,
            month: 1,
            day_of_month: 3,
            depth_mm: 12,
            precip_mm: null,
            duration_hours: 1.5,
            peak_intensity_10: 9.4,
          },
        ],
      })
      .mockRejectedValueOnce(new Error('soil missing'))
      .mockResolvedValueOnce({ records: [] })
      .mockResolvedValueOnce({ records: [] })
      .mockResolvedValueOnce({ records: [] })
      .mockResolvedValueOnce({ records: [] });

    const manager = createEventDataManager({ ctx: { runid: 'demo', config: 'disturbed' }, postQueryEngine });
    const result = await manager.fetchEventRows({
      selectedMetric: { durationMinutes: 10, value: 10 },
      filterRangePct: 10,
      includeWarmup: false,
    });
    const rows = result.rows;

    expect(rows).toHaveLength(2);
    expect(rows[0].depth_mm).toBeNull();
    expect(rows[0].duration_hours).toBeNull();
    expect(rows[0].measure_value).toBeNull();
    expect(rows[0].precip_mm).toBeNull();
    expect(rows[0].soil_saturation_pct).toBeNull();
    expect(rows[1].precip_mm).toBe(12);
  });
});
