import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import { createWeppDataManager } from '../data/wepp-data.js';

describe('gl-dashboard wepp-data ranges', () => {
  let state;
  let manager;
  let setState;
  let setValue;

  beforeEach(() => {
    state = {
      weppSummary: {
        10: {
          runoff_volume: 5,
          subrunoff_volume: undefined,
          baseflow_volume: 0,
          soil_loss: 2,
          sediment_deposition: 1,
          sediment_yield: 1,
        },
        11: {
          runoff_volume: 1,
          subrunoff_volume: 1.5,
          baseflow_volume: 0,
          soil_loss: 2.5,
          sediment_deposition: -1,
          sediment_yield: 0,
        },
      },
      weppYearlySummary: {
        a: { runoff_volume: 0, soil_loss: 4, sediment_yield: 0 },
        b: { runoff_volume: 0, soil_loss: 6, sediment_yield: 0 },
        c: { runoff_volume: 0, soil_loss: 5, sediment_yield: 0 },
        d: { runoff_volume: 0, soil_loss: 4, sediment_yield: 0 },
      },
      baseWeppYearlyCache: {
        2020: {
          a: { runoff_volume: 2, soil_loss: 3 },
          b: { runoff_volume: 5, soil_loss: 4 },
          c: { runoff_volume: 0, soil_loss: 5 },
          d: { runoff_volume: 3, soil_loss: 6 },
        },
      },
      weppEventSummary: {
        30: { event_P: 10, event_Q: 2, event_ET: 5, event_peakro: 1, event_tdet: 0.5 },
        31: { event_P: 20, event_Q: 4, event_ET: 5, event_peakro: 1, event_tdet: 0.5 },
      },
      baseSummaryCache: {
        weppEvent: {
          30: { event_P: 12, event_Q: 1, event_ET: 3, event_peakro: 2, event_tdet: 1 },
          31: { event_P: 18, event_Q: 5, event_ET: 3, event_peakro: 1, event_tdet: 0.5 },
        },
      },
      comparisonDiffRanges: {},
      weppYearlyDiffRanges: {},
      weppYearlyRanges: {},
      weppRanges: {},
      weppEventRanges: {},
    };

    setValue = jest.fn((key, value) => {
      state[key] = value;
    });
    setState = jest.fn((updates) => {
      Object.assign(state, updates);
    });

    manager = createWeppDataManager({
      ctx: { sitePrefix: '/site', runid: 'run1', config: 'cfg1' },
      getState: () => state,
      setValue,
      setState,
      postQueryEngine: async () => null,
      postBaseQueryEngine: async () => null,
      pickActiveWeppEventLayer: () => ({ mode: 'event_P' }),
      WEPP_YEARLY_PATH: 'wepp/output/interchange/H.parquet',
      WEPP_LOSS_PATH: 'wepp/output/loss.parquet',
    });
  });

  it('computes WEPP summary ranges and applies defaults for missing values', () => {
    const ranges = manager.computeWeppRanges();

    expect(ranges.runoff_volume).toEqual({ min: 1, max: 5 });
    expect(ranges.subrunoff_volume).toEqual({ min: 1.5, max: 2.5 });
    expect(ranges.baseflow_volume).toEqual({ min: 0, max: 1 });
    expect(ranges.soil_loss).toEqual({ min: 2, max: 2.5 });
    expect(ranges.sediment_deposition).toEqual({ min: -1, max: 1 });
    expect(ranges.sediment_yield).toEqual({ min: 0, max: 1 });
    expect(state.weppRanges).toEqual(ranges);
    expect(setValue).toHaveBeenCalledWith('weppRanges', ranges);
  });

  it('computes yearly ranges and bumps flat distributions', () => {
    const ranges = manager.computeWeppYearlyRanges();

    expect(ranges.runoff_volume).toEqual({ min: 0, max: 1 });
    expect(ranges.soil_loss).toEqual({ min: 4, max: 6 });
    expect(ranges.sediment_yield).toEqual({ min: 0, max: 1 });
    expect(state.weppYearlyRanges).toEqual(ranges);
    expect(setState).toHaveBeenCalledWith({ weppYearlyRanges: ranges });
  });

  it('computes yearly diff ranges with robust bounds', () => {
    const diffRanges = manager.computeWeppYearlyDiffRanges(2020);

    expect(diffRanges.runoff_volume).toEqual({ min: -5, max: 5, p5: 0, p95: 5 });
    expect(diffRanges.soil_loss).toEqual({ min: -2, max: 2, p5: -2, p95: 2 });
    expect(state.weppYearlyDiffRanges).toEqual(diffRanges);
  });

  it('computes event ranges and preserves epsilon for flat data', () => {
    const ranges = manager.computeWeppEventRanges();

    expect(ranges.event_P).toEqual({ min: 10, max: 20 });
    expect(ranges.event_ET.max).toBeCloseTo(ranges.event_ET.min + 0.001);
    expect(ranges.event_peakro.max).toBeCloseTo(ranges.event_peakro.min + 0.001);
    expect(state.weppEventRanges).toEqual(ranges);
  });

  it('computes event diff ranges against base cache', () => {
    const diff = manager.computeWeppEventDiffRanges();

    expect(diff.event_P).toEqual({ min: -2, max: 2, p5: -2, p95: 2 });
    expect(state.comparisonDiffRanges).toEqual(diff);
  });
});
