import { describe, expect, jest, test } from '@jest/globals';
import { createScenarioManager } from '../scenario/manager.js';

describe('scenario manager', () => {
  test('keeps existing overlays while switching scenarios (no geometry flash)', async () => {
    const state = {
      currentScenarioPath: '',
      landuseSummary: { a: { inrcov: 1 } },
      soilsSummary: { a: { clay: 10 } },
      weppSummary: { a: { soil_loss: 1 } },
      subcatchmentsGeoJson: { type: 'FeatureCollection', features: [{ id: 'a' }] },
      weppYearlyRanges: { foo: { min: 1, max: 2 } },
      weppYearlyDiffRanges: { foo: { min: -1, max: 1 } },
      weppYearlyCache: { 2020: {} },
      baseWeppYearlyCache: { 2020: {} },
    };

    const setState = (partial) => Object.assign(state, partial);
    const setValue = (key, value) => {
      state[key] = value;
    };

    const scenarioManager = createScenarioManager({
      ctx: { sitePrefix: '', runid: 'r', config: 'c' },
      getState: () => state,
      setValue,
      setState,
      postQueryEngine: jest.fn(),
      postBaseQueryEngine: jest.fn(),
      fetchWeppSummary: jest.fn(),
      weppDataManager: {},
      onScenarioChange: jest.fn().mockResolvedValue(undefined),
    });

    await scenarioManager.setScenario('_pups/omni/scenarios/test');

    expect(state.currentScenarioPath).toBe('_pups/omni/scenarios/test');
    expect(state.landuseSummary).toBeTruthy();
    expect(state.soilsSummary).toBeTruthy();
    expect(state.weppSummary).toBeTruthy();
    expect(state.subcatchmentsGeoJson).toBeTruthy();
    expect(state.weppYearlyRanges).toEqual({});
    expect(state.weppYearlyDiffRanges).toEqual({});
  });
});
