import { describe, expect, it, jest } from '@jest/globals';
import {
  buildEventFilterPayload,
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
      .mockResolvedValueOnce({ records: [] });

    const manager = createEventDataManager({ ctx: { runid: 'demo', config: 'disturbed' }, postQueryEngine });
    const rows = await manager.fetchEventRows({
      selectedMetric: { durationMinutes: 10, value: 10 },
      filterRangePct: 10,
      includeWarmup: false,
    });

    expect(rows).toHaveLength(2);
    expect(rows[0].depth_mm).toBeNull();
    expect(rows[0].duration_hours).toBeNull();
    expect(rows[0].measure_value).toBeNull();
    expect(rows[0].precip_mm).toBeNull();
    expect(rows[0].soil_saturation_pct).toBeNull();
    expect(rows[1].precip_mm).toBe(12);
  });
});
