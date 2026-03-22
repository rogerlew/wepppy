import { afterEach, beforeEach, describe, expect, it, jest } from '@jest/globals';
import { createRasterUtils } from '../map/raster-utils.js';

const originalFetch = global.fetch;
const originalGeoTiff = global.GeoTIFF;
const originalCanvasGetContext = HTMLCanvasElement.prototype.getContext;

describe('gl-dashboard raster utils nodata handling', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
    global.GeoTIFF = { fromArrayBuffer: jest.fn() };
    HTMLCanvasElement.prototype.getContext = function mockGetContext() {
      if (!this.__ctx2dMock) {
        const canvas = this;
        canvas.__imageDataMock = null;
        canvas.__ctx2dMock = {
          createImageData(width, height) {
            return {
              width,
              height,
              data: new Uint8ClampedArray(width * height * 4),
            };
          },
          putImageData(imageData) {
            canvas.__imageDataMock = {
              width: imageData.width,
              height: imageData.height,
              data: new Uint8ClampedArray(imageData.data),
            };
          },
          getImageData(x, y, width, height) {
            if (canvas.__imageDataMock) {
              return {
                width,
                height,
                data: new Uint8ClampedArray(canvas.__imageDataMock.data),
              };
            }
            return {
              width,
              height,
              data: new Uint8ClampedArray(width * height * 4),
            };
          },
        };
      }
      return this.__ctx2dMock;
    };
  });

  afterEach(() => {
    global.fetch = originalFetch;
    global.GeoTIFF = originalGeoTiff;
    HTMLCanvasElement.prototype.getContext = originalCanvasGetContext;
    jest.clearAllMocks();
  });

  it('renders nodata pixels transparent', async () => {
    const values = new Float32Array([1, -9999, 2]);
    const image = {
      getWidth: () => 3,
      getHeight: () => 1,
      readRasters: jest.fn().mockResolvedValue(values),
      getBoundingBox: () => [0, 0, 3, 1],
      getGDALNoData: () => '-9999',
    };
    const tiff = { getImage: jest.fn().mockResolvedValue(image) };
    global.GeoTIFF.fromArrayBuffer.mockResolvedValue(tiff);
    global.fetch.mockResolvedValue({
      ok: true,
      arrayBuffer: async () => new ArrayBuffer(8),
    });

    const utils = createRasterUtils({
      ctx: { sitePrefix: '', runid: 'run1', config: 'cfg1' },
      getState: () => ({ geoTiffLoader: null }),
      setValue: jest.fn(),
      colorFn: () => [255, 0, 0, 230],
    });

    const raster = await utils.loadRaster('rusle/a_observed_rap_polaris_nomograph.tif', () => [10, 20, 30, 230]);
    const data = raster.canvas.getContext('2d').getImageData(0, 0, 3, 1).data;

    expect(data[3]).toBe(230);
    expect(data[7]).toBe(0);
    expect(data[11]).toBe(230);
  });
});
