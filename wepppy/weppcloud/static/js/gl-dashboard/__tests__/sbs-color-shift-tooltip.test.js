import { describe, expect, it, jest } from '@jest/globals';
import { createLayerUtils } from '../map/layers.js';

describe('gl-dashboard SBS class tooltip', () => {
  it('reports decoded class semantics independent of display mode', () => {
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
          values: new Uint8ClampedArray([82, 204, 204, 255]),
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
    expect(standardTooltip).toContain('Value: 131: Low Severity Burn');

    state.sbsColorShiftEnabled = true;
    const shiftedTooltip = layerUtils.formatTooltip(info);
    expect(shiftedTooltip).toContain('Value: 131: Low Severity Burn');

    state.detectedLayers[0].values = new Uint8ClampedArray([1, 2, 3, 255]);
    expect(layerUtils.formatTooltip(info)).toContain('Value: Unassigned');
  });

  it('decodes historical pixels, preserves source bytes, and counts unknown opaque pixels', () => {
    const layerUtils = createLayerUtils({
      deck: {},
      getState: () => ({}),
      colorScales: {},
      constants: {},
    });
    const source = new Uint8ClampedArray([
      161, 250, 220, 80,
      77, 230, 0, 255,
      82, 204, 204, 255,
      100, 100, 100, 30,
      168, 0, 0, 255,
      9, 9, 9, 0,
    ]);
    const stored = source.slice();
    const display = source.slice();

    expect(layerUtils.recolorSbsPixels(display, false)).toBe(1);
    expect(source).toEqual(stored);
    expect(Array.from(display)).toEqual([
      82, 204, 204, 255,
      82, 204, 204, 255,
      82, 204, 204, 255,
      128, 0, 152, 255,
      168, 0, 0, 255,
      9, 9, 9, 0,
    ]);
  });

  it('builds one decoded display canvas and replaces it when mode changes', () => {
    const layerUtils = createLayerUtils({
      deck: {}, getState: () => ({}), colorScales: {}, constants: {},
    });
    const originalGetContext = HTMLCanvasElement.prototype.getContext;
    const putImageData = jest.fn();
    HTMLCanvasElement.prototype.getContext = () => ({
      drawImage: jest.fn(),
      getImageData: () => ({ data: new Uint8ClampedArray([1, 2, 3, 40]) }),
      putImageData,
    });
    try {
      const sourceCanvas = document.createElement('canvas');
      sourceCanvas.width = 1;
      sourceCanvas.height = 1;
      const layer = { canvas: sourceCanvas };

      const standard = layerUtils.getSbsDisplayCanvas(layer, false);
      expect(layer.sbsUnassignedCount).toBe(1);
      expect(layerUtils.getSbsDisplayCanvas(layer, false)).toBe(standard);
      const shifted = layerUtils.getSbsDisplayCanvas(layer, true);
      expect(shifted).not.toBe(standard);
      expect(layer._sbsDisplayCanvas).toBe(shifted);
      expect(layer._sbsDisplayMode).toBe(true);
      expect(putImageData).toHaveBeenCalledTimes(2);
    } finally {
      HTMLCanvasElement.prototype.getContext = originalGetContext;
    }
  });

  it('locks the approved pre-2018 interpolation and clamp compatibility outcomes', () => {
    const layerUtils = createLayerUtils({
      deck: {}, getState: () => ({}), colorScales: {}, constants: {},
    });
    const display = new Uint8ClampedArray([
      75, 71, 71, 255, // GDAL between-break interpolation fixture.
      168, 0, 0, 255, // GDAL above-range clamp fixture.
    ]);

    expect(layerUtils.recolorSbsPixels(display, false)).toBe(1);
    expect(Array.from(display)).toEqual([
      128, 0, 152, 255,
      168, 0, 0, 255,
    ]);
  });
});
