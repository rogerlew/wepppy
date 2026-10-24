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

  test('buildScenarioUrl uses composite runid for omni contrast paths', () => {
    const state = { currentScenarioPath: '_pups/omni/contrasts/12' };
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
      '/weppcloud/runs/decimal-pleasing;;omni-contrast;;12/disturbed9002_wbt/query/landuse/subcatchments',
    );
  });

  test('buildScenarioUrl strips nested composite runid to parent before rebuilding', () => {
    const state = { currentScenarioPath: '_pups/omni/scenarios/treated' };
    const scenarioManager = createScenarioManager({
      ctx: {
        sitePrefix: '/weppcloud',
        runid: 'batch;;spring-2025;;run-001;;omni;;undisturbed',
        config: 'disturbed9002_wbt',
      },
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
      '/weppcloud/runs/batch;;spring-2025;;run-001;;omni;;treated/disturbed9002_wbt/query/soils/subcatchments',
    );
  });

  test('buildScenarioUrl preserves grouped runid segments for omni contrasts', () => {
    const state = { currentScenarioPath: '_pups/omni/contrasts/3' };
    const scenarioManager = createScenarioManager({
      ctx: { sitePrefix: '/weppcloud', runid: 'batch;;spring-2025;;run-001', config: 'disturbed9002_wbt' },
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
      '/weppcloud/runs/batch;;spring-2025;;run-001;;omni-contrast;;3/disturbed9002_wbt/query/landuse/subcatchments',
    );
  });
});

test.each(['root-run', 'root-run;;omni;;child'])('Roads scope rejects programmatic map scenario/comparison re-entry for %s', async (runid) => {
  const state = { currentScenarioPath: '', comparisonMode: false, weppSummary: { current: true } };
  const setValue = jest.fn((key, value) => { state[key] = value; });
  const postQueryEngine = jest.fn();
  const onScenarioChange = jest.fn();
  const manager = createScenarioManager({
    ctx: { sitePrefix: '/weppcloud', runid, config: 'cfg', outputScope: 'roads' },
    getState: () => state, setValue, setState: jest.fn(), postQueryEngine,
    postBaseQueryEngine: jest.fn(), fetchWeppSummary: jest.fn(), weppDataManager: {}, onScenarioChange,
  });
  await manager.setScenario('_pups/omni/scenarios/another');
  await manager.setComparisonMode(true);
  expect(state).toEqual({ currentScenarioPath: '', comparisonMode: false, weppSummary: { current: true } });
  expect(setValue).not.toHaveBeenCalled();
  expect(postQueryEngine).not.toHaveBeenCalled();
  expect(onScenarioChange).not.toHaveBeenCalled();
});
