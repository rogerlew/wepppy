import { describe, expect, it } from '@jest/globals';
import { createLayerUtils } from '../map/layers.js';

describe('gl-dashboard batch tooltip formatting', () => {
  it('includes run + TopazID lines and looks up values by feature_key', () => {
    const state = {
      dashboardMode: 'batch',
      landuseLayers: [{ key: 'lu-cancov', path: 'landuse/landuse.parquet', mode: 'cancov', visible: true }],
      soilsLayers: [],
      hillslopesLayers: [],
      watarLayers: [],
      weppLayers: [],
      weppYearlyLayers: [],
      weppEventLayers: [],
      openetLayers: [],
      rapLayers: [],
      landuseSummary: {
        'batch;;spring-2025-a;;run-002-1': { cancov: 0.1 },
      },
    };

    const layerUtils = createLayerUtils({
      deck: {},
      getState: () => state,
      colorScales: {
        viridisColor: () => [0, 0, 0, 0],
        winterColor: () => [0, 0, 0, 0],
        jet2Color: () => [0, 0, 0, 0],
        rdbuScale: () => [0, 0, 0, 0],
      },
      constants: {
        WATER_MEASURES: {},
        SOIL_MEASURES: {},
        NLCD_COLORMAP: {},
        NLCD_LABELS: {},
        RAP_BAND_LABELS: {},
      },
    });

    const tooltip = layerUtils.formatTooltip({
      object: {
        properties: {
          feature_key: 'batch;;spring-2025-a;;run-002-1',
          TopazID: 1,
          runid: 'batch;;spring-2025-a;;run-002',
          leaf_runid: 'run-002',
        },
      },
    });

    expect(tooltip).toBe(
      'Layer: landuse/landuse.parquet\nRun: run-002\nTopazID: 1\ncancov: 0.100',
    );
  });
});

