import { describe, expect, jest, test } from '@jest/globals';
import { createDetectionController } from '../layers/orchestrator.js';

describe('layers/orchestrator landuse detection', () => {
  test('re-applies previous landuse selection when scenarios change', async () => {
    const state = {
      landuseLayers: [{ key: 'lu-inrcov', visible: true }],
      subcatchmentsGeoJson: null,
      comparisonMode: false,
    };

    const detectorModule = {
      detectLanduseOverlays: jest.fn().mockResolvedValue({
        landuseSummary: { foo: { inrcov: 1 } },
        subcatchmentsGeoJson: { type: 'FeatureCollection', features: [] },
        landuseLayers: [
          { key: 'lu-dominant', visible: true },
          { key: 'lu-inrcov', visible: false },
        ],
      }),
    };

    const applyLayers = jest.fn();
    const updateLayerList = jest.fn();
    const controller = createDetectionController({
      ctx: {},
      detectorModule,
      getState: () => state,
      setState: (partial) => Object.assign(state, partial),
      setValue: (key, value) => {
        state[key] = value;
      },
      buildScenarioUrl: (path) => `/runs/base/${path}`,
      buildBaseUrl: (path) => `/runs/base/${path}`,
      fetchWeppSummary: jest.fn(),
      weppLossPath: '',
      weppYearlyPath: '',
      watarPath: '',
      postQueryEngine: jest.fn(),
      yearSlider: { setRange: jest.fn() },
      climateCtx: {},
      applyLayers,
      updateLayerList,
      nlcdColormap: {},
      soilColorForValue: () => {},
      loadRaster: jest.fn(),
      loadSbsImage: jest.fn(),
      fetchGdalInfo: jest.fn(),
      computeComparisonDiffRanges: jest.fn(),
      baseLayerDefs: [],
      rapBandLabels: {},
    });

    await controller.detectLanduseOverlays();

    expect(detectorModule.detectLanduseOverlays).toHaveBeenCalled();
    expect(updateLayerList).toHaveBeenCalled();
    expect(applyLayers).toHaveBeenCalled();

    const active = state.landuseLayers.find((l) => l && l.visible);
    expect(active).toBeTruthy();
    expect(active.key).toBe('lu-inrcov');
    expect(state.landuseLayers.find((l) => l.key === 'lu-dominant')?.visible).toBe(false);
  });
});
