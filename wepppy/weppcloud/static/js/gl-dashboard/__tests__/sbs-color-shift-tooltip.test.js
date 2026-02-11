import { describe, expect, it } from '@jest/globals';
import { createLayerUtils } from '../map/layers.js';

describe('gl-dashboard SBS color shift', () => {
  it('remaps SBS tooltip color values when color shift is enabled', () => {
    const state = {
      dashboardMode: 'run',
      sbsColorShiftEnabled: false,
      landuseLayers: [],
      soilsLayers: [],
      hillslopesLayers: [],
      watarLayers: [],
      weppLayers: [],
      weppChannelLayers: [],
      weppYearlyLayers: [],
      weppYearlyChannelLayers: [],
      weppEventLayers: [],
      openetLayers: [],
      rapLayers: [],
      detectedLayers: [
        {
          key: 'sbs',
          path: 'query/baer_wgs_map',
          visible: true,
          sampleMode: 'rgba',
          bounds: [0, 0, 1, 1],
          width: 1,
          height: 1,
          values: new Uint8ClampedArray([77, 230, 0, 255]),
        },
      ],
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

    const info = { coordinate: [0.5, 0.5] };
    const standardTooltip = layerUtils.formatTooltip(info);
    expect(standardTooltip).toContain('Value: rgba(77, 230, 0, 255)');

    state.sbsColorShiftEnabled = true;
    const shiftedTooltip = layerUtils.formatTooltip(info);
    expect(shiftedTooltip).toContain('Value: rgba(86, 180, 233, 255)');
  });
});
