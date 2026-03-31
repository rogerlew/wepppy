import { describe, expect, it, jest } from '@jest/globals';
import {
  buildEventDatePayload,
  buildEventFilterPayload,
  buildHydrologyPayload,
  buildSoilPayload,
  computeIntensityRange,
  createEventDataManager,
  getIntensityColumn,
} from '../data/event-data.js';

const TEST_WEPP_PATHS = Object.freeze({
  soil: 'wepp/roads/output/interchange/H.soil.parquet',
  water: 'wepp/roads/output/interchange/H.wat.parquet',
  outlet: 'wepp/roads/output/interchange/ebe_pw0.parquet',
  hillEvents: 'wepp/roads/output/interchange/H.ebe.parquet',
  tc: 'wepp/roads/output/interchange/tc_out.parquet',
});

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

  it('builds manual date payload with exact year-month-day filters', () => {
    const payload = buildEventDatePayload({
      year: 96,
      month: 8,
      day: 4,
      warmupYear: 95,
    });

    const yearFilter = payload.filters.find((filter) => filter.column === 'ev.year' && filter.operator !== '>');
    expect(yearFilter).toEqual({ column: 'ev.year', operator: '=', value: 96 });
    expect(payload.filters).toEqual(
      expect.arrayContaining([
        { column: 'ev.month', operator: '=', value: 8 },
        { column: 'ev.day_of_month', operator: '=', value: 4 },
        { column: 'ev.year', operator: '>', value: 95 },
      ]),
    );
  });

  it('builds manual date payload with IN operator when year aliases are provided', () => {
    const payload = buildEventDatePayload({
      year: [96, 1996, 2096],
      month: 8,
      day: 4,
      warmupYear: null,
    });
    const yearFilter = payload.filters.find((filter) => filter.column === 'ev.year');
    expect(yearFilter).toEqual({ column: 'ev.year', operator: 'IN', value: [96, 1996, 2096] });
  });

  it('builds soil payload using TSMF by default with legacy fallback option', () => {
    const primary = buildSoilPayload({
      filterColumn: 'peak_intensity_10',
      minValue: 1,
      maxValue: 2,
      warmupYear: null,
    }, TEST_WEPP_PATHS);
    expect(primary.aggregations[0].sql).toBe('AVG(soil.TSMF) * 100');
    expect(primary.datasets[1].path).toBe(TEST_WEPP_PATHS.soil);

    const fallback = buildSoilPayload({
      filterColumn: 'peak_intensity_10',
      minValue: 1,
      maxValue: 2,
      warmupYear: null,
      soilSaturationSource: 'saturation',
    }, TEST_WEPP_PATHS);
    expect(fallback.aggregations[0].sql).toBe('AVG(soil.Saturation) * 100');
  });

  it('builds hydrology payload with explicit scoped output path', () => {
    const payload = buildHydrologyPayload(
      {
        filterColumn: 'peak_intensity_10',
        minValue: 1,
        maxValue: 2,
        warmupYear: null,
      },
      TEST_WEPP_PATHS,
    );

    expect(payload.datasets[1].path).toBe(TEST_WEPP_PATHS.outlet);
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

    const manager = createEventDataManager({
      ctx: { runid: 'demo', config: 'disturbed' },
      postQueryEngine,
      weppPaths: TEST_WEPP_PATHS,
    });
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

    const manager = createEventDataManager({
      ctx: { runid: 'demo', config: 'disturbed' },
      postQueryEngine,
      weppPaths: TEST_WEPP_PATHS,
    });
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

  it('requires explicit weppPaths when constructing event data manager', () => {
    expect(() => {
      createEventDataManager({
        ctx: { runid: 'demo', config: 'disturbed' },
        postQueryEngine: jest.fn(),
      });
    }).toThrow('STORM_EVENT_ANALYZER_CONTEXT.weppPaths');
  });

  it('fetches a single event row by manual date and enriches hydrology fields', async () => {
    const postQueryEngine = jest.fn(async (payload) => {
      const filters = Array.isArray(payload.filters) ? payload.filters : [];
      const hasDateFilter = filters.some(
        (filter) => filter.column === 'ev.year' && (filter.operator === '=' || filter.operator === 'IN'),
      );
      if (hasDateFilter) {
        return {
          records: [
            {
              sim_day_index: 42,
              year: 96,
              month: 8,
              day_of_month: 4,
              depth_mm: 20,
              precip_mm: 20,
              duration_hours: 2,
              tp: 0.4,
              ip: 5,
              peak_intensity_10: 18,
              peak_intensity_15: 15,
              peak_intensity_30: 12,
              peak_intensity_60: 8,
            },
          ],
        };
      }

      const aggregations = Array.isArray(payload.aggregations) ? payload.aggregations : [];
      if (aggregations.some((agg) => agg.alias === 'soil_saturation_pct')) {
        return { records: [{ sim_day_index: 42, soil_saturation_pct: 55 }] };
      }
      if (aggregations.some((agg) => agg.alias === 'snow_coverage_t1_pct')) {
        return { records: [{ sim_day_index: 42, snow_coverage_t1_pct: 0, snow_water_t1_mm: 0 }] };
      }
      if (aggregations.some((agg) => agg.alias === 'runoff_volume_m3')) {
        return {
          records: [{ sim_day_index: 42, runoff_volume_m3: 100, peak_discharge_m3s: 3.2, sediment_yield_kg: 40 }],
        };
      }
      if (aggregations.some((agg) => agg.alias === 'precip_volume_m3')) {
        return { records: [{ sim_day_index: 42, precip_volume_m3: 200, total_area_m2: 10000 }] };
      }
      if (Array.isArray(payload.columns) && payload.columns.includes('tc."Time of Conc (hr)" AS tc_hours')) {
        return { records: [{ sim_day_index: 42, tc_hours: 1.25 }] };
      }
      return { records: [] };
    });

    const manager = createEventDataManager({
      ctx: { runid: 'demo', config: 'disturbed' },
      postQueryEngine,
      weppPaths: TEST_WEPP_PATHS,
    });
    const result = await manager.fetchEventRowByDate({
      year: 96,
      month: 8,
      day: 4,
      includeWarmup: false,
    });

    expect(result.row).toEqual(
      expect.objectContaining({
        sim_day_index: 42,
        date: '96-08-04',
        measure_value: null,
        soil_saturation_pct: 55,
        runoff_volume_m3: 100,
        runoff_mm: 10,
        runoff_coefficient: 0.5,
        tc_hours: 1.25,
      }),
    );
    expect(result.tcAvailable).toBe(true);
  });

  it('accepts four-digit manual year when climate data stores two-digit years', async () => {
    const postQueryEngine = jest.fn(async (payload) => {
      const filters = Array.isArray(payload.filters) ? payload.filters : [];
      const yearFilter = filters.find((filter) => filter.column === 'ev.year');
      const monthFilter = filters.find((filter) => filter.column === 'ev.month');
      const dayFilter = filters.find((filter) => filter.column === 'ev.day_of_month');
      if (yearFilter && monthFilter && dayFilter) {
        const matchesTwoDigitYear =
          yearFilter.operator === 'IN' &&
          Array.isArray(yearFilter.value) &&
          yearFilter.value.includes(96) &&
          yearFilter.value.includes(1996);
        if (matchesTwoDigitYear && monthFilter.value === 8 && dayFilter.value === 4) {
          return {
            records: [
              {
                sim_day_index: 42,
                year: 96,
                month: 8,
                day_of_month: 4,
                depth_mm: 20,
                precip_mm: 20,
                duration_hours: 2,
                tp: 0.4,
                ip: 5,
                peak_intensity_10: 18,
                peak_intensity_15: 15,
                peak_intensity_30: 12,
                peak_intensity_60: 8,
              },
            ],
          };
        }
      }
      return { records: [] };
    });

    const manager = createEventDataManager({
      ctx: { runid: 'demo', config: 'disturbed' },
      postQueryEngine,
      weppPaths: TEST_WEPP_PATHS,
    });
    const result = await manager.fetchEventRowByDate({
      year: 1996,
      month: 8,
      day: 4,
      includeWarmup: false,
    });
    expect(result.row).toEqual(expect.objectContaining({ sim_day_index: 42, date: '96-08-04' }));
  });
});
