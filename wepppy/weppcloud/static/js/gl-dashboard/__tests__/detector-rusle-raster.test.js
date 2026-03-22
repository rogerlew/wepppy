import { afterEach, beforeEach, describe, expect, it, jest } from '@jest/globals';
import { detectRasterLayers } from '../layers/detector.js';
import { jet2Color, plasmaColor, viridisColor } from '../colors.js';

const originalFetch = global.fetch;

describe('gl-dashboard detector RUSLE rasters', () => {
  beforeEach(() => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({}),
    });
  });

  afterEach(() => {
    global.fetch = originalFetch;
    jest.clearAllMocks();
  });

  it('applies explicit colormap metadata and range for RUSLE rasters', async () => {
    const loadRaster = jest.fn().mockResolvedValue({
      canvas: document.createElement('canvas'),
      bounds: [-121, 44, -120, 45],
      values: new Float32Array([0, 0.5, 1]),
      width: 3,
      height: 1,
      sampleMode: 'palette',
      nodata: -9999,
    });

    const result = await detectRasterLayers({
      ctx: { sitePrefix: '/site', runid: 'run1', config: 'cfg1' },
      layerDefs: [
        {
          key: 'rusle-c-observed-rap',
          group: 'rusle',
          label: 'RUSLE C (Observed RAP)',
          paths: ['rusle/c_observed_rap.tif'],
          colormap: 'viridis',
          units: 'unitless',
          valueRange: { min: 0, max: 1 },
        },
      ],
      loadRaster,
      loadSbsImage: jest.fn(),
      fetchGdalInfo: jest.fn().mockResolvedValue({
        cornerCoordinates: {
          lowerLeft: [-121, 44],
          upperRight: [-120, 45],
        },
      }),
      nlcdColormap: null,
      soilColorForValue: () => null,
    });

    expect(result.detectedLayers).toHaveLength(1);
    const [layer] = result.detectedLayers;
    expect(layer.group).toBe('rusle');
    expect(layer.colormap).toBe('viridis');
    expect(layer.units).toBe('unitless');
    expect(layer.range).toEqual({ min: 0, max: 1 });

    const passedColorMap = loadRaster.mock.calls[0][1];
    expect(typeof passedColorMap).toBe('function');
    expect(passedColorMap(0)).toEqual(viridisColor(0));
    expect(passedColorMap(1)).toEqual(viridisColor(1));
  });

  it('uses plasma colormap when configured for RUSLE K rasters', async () => {
    const loadRaster = jest.fn().mockResolvedValue({
      canvas: document.createElement('canvas'),
      bounds: [-121, 44, -120, 45],
      values: new Float32Array([0, 0.35, 0.7]),
      width: 3,
      height: 1,
      sampleMode: 'palette',
      nodata: -9999,
    });

    const result = await detectRasterLayers({
      ctx: { sitePrefix: '/site', runid: 'run1', config: 'cfg1' },
      layerDefs: [
        {
          key: 'rusle-k-nomograph',
          group: 'rusle',
          label: 'RUSLE K (POLARIS Nomograph)',
          paths: ['rusle/k_polaris_nomograph.tif'],
          colormap: 'plasma',
          units: 't*ha*h/(ha*MJ*mm)',
          valueRange: { min: 0, max: 0.7 },
        },
      ],
      loadRaster,
      loadSbsImage: jest.fn(),
      fetchGdalInfo: jest.fn().mockResolvedValue({
        cornerCoordinates: {
          lowerLeft: [-121, 44],
          upperRight: [-120, 45],
        },
      }),
      nlcdColormap: null,
      soilColorForValue: () => null,
    });

    expect(result.detectedLayers).toHaveLength(1);
    const [layer] = result.detectedLayers;
    expect(layer.colormap).toBe('plasma');
    expect(layer.range).toEqual({ min: 0, max: 0.7 });

    const passedColorMap = loadRaster.mock.calls[0][1];
    expect(typeof passedColorMap).toBe('function');
    expect(passedColorMap(0)).toEqual(plasmaColor(0));
    expect(passedColorMap(0.7)).toEqual(plasmaColor(1));
  });

  it('uses dynamic range from raster values for RUSLE A when no fixed range is configured', async () => {
    const loadRaster = jest.fn().mockResolvedValue({
      canvas: document.createElement('canvas'),
      bounds: [-121, 44, -120, 45],
      values: new Float32Array([2, -9999, 6]),
      width: 3,
      height: 1,
      sampleMode: 'palette',
      nodata: -9999,
    });

    const result = await detectRasterLayers({
      ctx: { sitePrefix: '/site', runid: 'run1', config: 'cfg1' },
      layerDefs: [
        {
          key: 'rusle-a-observed-rap-nomograph',
          group: 'rusle',
          label: 'RUSLE A (Observed RAP, Nomograph K)',
          paths: ['rusle/a_observed_rap_polaris_nomograph.tif'],
          colormap: 'jet2',
          units: 't/ha/yr',
        },
      ],
      loadRaster,
      loadSbsImage: jest.fn(),
      fetchGdalInfo: jest.fn().mockResolvedValue({
        cornerCoordinates: {
          lowerLeft: [-121, 44],
          upperRight: [-120, 45],
        },
      }),
      nlcdColormap: null,
      soilColorForValue: () => null,
    });

    expect(result.detectedLayers).toHaveLength(1);
    const [layer] = result.detectedLayers;
    expect(layer.range).toEqual({ min: 2, max: 6 });

    const passedColorMap = loadRaster.mock.calls[0][1];
    expect(typeof passedColorMap).toBe('function');
    expect(passedColorMap.dynamicRange).toBe(true);
    expect(typeof passedColorMap.setDynamicRange).toBe('function');
    passedColorMap.setDynamicRange({ min: 2, max: 6 });
    expect(passedColorMap(2)).toEqual(jet2Color(0));
    expect(passedColorMap(6)).toEqual(jet2Color(1));
  });
});
