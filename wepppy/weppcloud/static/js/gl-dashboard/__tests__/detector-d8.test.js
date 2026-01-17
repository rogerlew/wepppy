import { describe, expect, it, jest } from '@jest/globals';
import { detectD8DirectionLayer } from '../layers/detector.js';

const baseInfo = {
  metadata: {
    '': { WEPP_CELL_SIZE_M: '10' },
  },
};

const rasterBounds = [0, 0, 1, 1];

describe('gl-dashboard D8 direction mapping', () => {
  it.each([
    ['NE', 1, 45],
    ['E', 2, 0],
    ['SE', 4, -45],
    ['S', 8, -90],
    ['SW', 16, -135],
    ['W', 32, 180],
    ['NW', 64, 135],
    ['N', 128, 90],
  ])('maps %s pointer (%d) to %d degrees', async (_label, code, expected) => {
    const result = await detectD8DirectionLayer({
      fetchGdalInfo: jest.fn().mockResolvedValue(baseInfo),
      loadRasterFromDownload: jest.fn().mockResolvedValue({
        values: [code],
        width: 1,
        height: 1,
        bounds: rasterBounds,
        nodata: null,
      }),
    });

    expect(result).not.toBeNull();
    expect(result.d8DirectionLayer.cellSizeMeters).toBe(10);
    expect(result.d8DirectionLayer.data).toHaveLength(1);
    expect(result.d8DirectionLayer.data[0].angle).toBeCloseTo(expected, 4);
  });
});
