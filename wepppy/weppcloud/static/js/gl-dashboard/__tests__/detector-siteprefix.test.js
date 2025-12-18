import { afterEach, beforeEach, describe, expect, it, jest } from '@jest/globals';
import { detectRasterLayers } from '../layers/detector.js';
import { createRasterUtils } from '../map/raster-utils.js';

const originalFetch = global.fetch;
const originalGeoTiff = global.GeoTIFF;

describe('gl-dashboard detector URL construction', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    global.GeoTIFF = originalGeoTiff;
    jest.clearAllMocks();
  });

  it('prefixes gdalinfo requests with sitePrefix', async () => {
    global.fetch.mockResolvedValue({ ok: true, json: async () => ({ ok: true }) });

    const utils = createRasterUtils({
      ctx: { sitePrefix: '/site', runid: 'run1', config: 'cfg1' },
      getState: () => ({ geoTiffLoader: null }),
      setValue: () => {},
      colorFn: () => [0, 0, 0, 255],
    });

    await utils.fetchGdalInfo('foo.tif');

    expect(global.fetch).toHaveBeenCalledWith('/site/runs/run1/cfg1/gdalinfo/foo.tif');
  });

  it('prefixes browse requests with sitePrefix when loading rasters', async () => {
    global.fetch.mockResolvedValue({ ok: false, status: 404 });
    const prevGeoTiff = global.GeoTIFF;
    global.GeoTIFF = { fromArrayBuffer: jest.fn() };

    try {
      const utils = createRasterUtils({
        ctx: { sitePrefix: '/site', runid: 'run1', config: 'cfg1' },
        getState: () => ({ geoTiffLoader: null }),
        setValue: () => {},
        colorFn: () => [0, 0, 0, 255],
      });

      await expect(utils.loadRaster('rasters/loss.tif')).rejects.toThrow(
        '/site/runs/run1/cfg1/browse/rasters/loss.tif',
      );
      expect(global.fetch).toHaveBeenCalledWith('/site/runs/run1/cfg1/browse/rasters/loss.tif');
    } finally {
      global.GeoTIFF = prevGeoTiff;
    }
  });

  it('hits query endpoint under sitePrefix when detecting SBS overlays', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        Success: true,
        Content: { bounds: [[45, -120], [46, -121]], imgurl: 'http://example.com/sbs.png' },
      }),
    });

    const loadSbsImage = jest.fn().mockResolvedValue({
      canvas: 'c',
      width: 1,
      height: 1,
      values: new Uint8ClampedArray([0, 0, 0, 0]),
      sampleMode: 'rgba',
    });

    const result = await detectRasterLayers({
      ctx: { sitePrefix: '/site', runid: 'run1', config: 'cfg1' },
      layerDefs: [],
      loadRaster: jest.fn(),
      loadSbsImage,
      fetchGdalInfo: jest.fn(),
      nlcdColormap: null,
      soilColorForValue: () => null,
    });

    expect(global.fetch).toHaveBeenCalledWith('/site/runs/run1/cfg1/query/baer_wgs_map');
    expect(result.detectedLayers).toHaveLength(1);
    expect(result.detectedLayers[0].path).toBe('query/baer_wgs_map');
  });
});
