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

  test('buildScenarioUrl uses composite runid for omni scenario paths', () => {
    const state = { currentScenarioPath: '_pups/omni/scenarios/burned' };
    const scenarioManager = createScenarioManager({
      ctx: { sitePrefix: '/weppcloud', runid: 'decimal-pleasing', config: 'disturbed9002_wbt' },
      getState: () => state,
      setValue: () => {},
      setState: () => {},
      postQueryEngine: jest.fn(),
      postBaseQueryEngine: jest.fn(),
      fetchWeppSummary: jest.fn(),
      weppDataManager: {},
      onScenarioChange: jest.fn(),
    });

    const url = scenarioManager.buildScenarioUrl('query/landuse/subcatchments');

    expect(url).toBe(
      '/weppcloud/runs/decimal-pleasing;;omni;;burned/disturbed9002_wbt/query/landuse/subcatchments',
    );
  });

  test('buildScenarioUrl strips composite runid to parent before rebuilding', () => {
    const state = { currentScenarioPath: '_pups/omni/scenarios/treated' };
    const scenarioManager = createScenarioManager({
      ctx: { sitePrefix: '/weppcloud', runid: 'decimal-pleasing;;omni;;undisturbed', config: 'disturbed9002_wbt' },
      getState: () => state,
      setValue: () => {},
      setState: () => {},
      postQueryEngine: jest.fn(),
      postBaseQueryEngine: jest.fn(),
      fetchWeppSummary: jest.fn(),
      weppDataManager: {},
      onScenarioChange: jest.fn(),
    });

    const url = scenarioManager.buildScenarioUrl('query/soils/subcatchments');

    expect(url).toBe(
      '/weppcloud/runs/decimal-pleasing;;omni;;treated/disturbed9002_wbt/query/soils/subcatchments',
    );
  });
});
