import { describe, expect, it } from '@jest/globals';
import {
  divergingColor,
  hexToRgbaArray,
  jet2Color,
  normalizeColorEntry,
  rgbaStringToArray,
  rdbuColor,
  viridisColor,
  winterColor,
} from '../colors.js';

function withinByteRange(arr) {
  return arr.every((v) => v >= 0 && v <= 255);
}

describe('gl-dashboard colors', () => {
  it('returns RGBA arrays in range for core colormaps', () => {
    const viridisStart = viridisColor(0);
    const viridisEnd = viridisColor(1);
    expect(viridisStart).toEqual([68, 1, 84, 230]);
    expect(viridisEnd).toEqual([253, 231, 37, 230]);
    expect(withinByteRange(viridisStart)).toBe(true);
    expect(withinByteRange(viridisEnd)).toBe(true);

    const winterMid = winterColor(0.5);
    expect(winterMid).toEqual([0, 128, 192, 230]);
    expect(withinByteRange(winterMid)).toBe(true);

    const jetLow = jet2Color(0.25);
    const jetHigh = jet2Color(0.75);
    expect(jetLow).toEqual([128, 255, 128, 230]);
    expect(jetHigh).toEqual([255, 128, 0, 230]);
    expect(withinByteRange(jetLow)).toBe(true);
    expect(withinByteRange(jetHigh)).toBe(true);

    expect(divergingColor(-1)).toEqual([33, 102, 172, 230]);
    expect(divergingColor(1)).toEqual([255, 102, 94, 230]);
    expect(rdbuColor(0.25)).toEqual(divergingColor(-0.5));
  });

  it('normalizes color inputs to RGBA arrays', () => {
    expect(hexToRgbaArray('#112233', 200)).toEqual([17, 34, 51, 200]);
    expect(rgbaStringToArray('rgba(10, 20, 30, 0.5)')).toEqual([10, 20, 30, 128]);
    expect(normalizeColorEntry([1, 2, 3, 0.5])).toEqual([1, 2, 3, 128]);
    expect(normalizeColorEntry([10, 11, 12, 300])).toEqual([10, 11, 12, 230]);
    expect(normalizeColorEntry('rgba(100, 120, 140, 0.4)', 120)).toEqual([100, 120, 140, 120]);
    expect(normalizeColorEntry('not-a-color')).toBeNull();
  });
});
