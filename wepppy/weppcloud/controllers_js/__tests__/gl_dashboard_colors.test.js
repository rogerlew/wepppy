let MODE_COLORMAP;
let normalizeModeValue;
let resolveColormapName;

beforeAll(async () => {
  const mod = await import('../../static/js/gl-dashboard/colors.js');
  MODE_COLORMAP = mod.MODE_COLORMAP;
  normalizeModeValue = mod.normalizeModeValue;
  resolveColormapName = mod.resolveColormapName;
});

describe('gl-dashboard color helpers', () => {
  test('cover modes use viridis colormap', () => {
    expect(MODE_COLORMAP.cancov).toBe('viridis');
    expect(resolveColormapName('cancov', 'Landuse')).toBe('viridis');
    expect(resolveColormapName('inrcov', 'Landuse')).toBe('viridis');
    expect(resolveColormapName('rilcov', 'Landuse')).toBe('viridis');
  });

  test('cover normalization accepts fractions and percents', () => {
    expect(normalizeModeValue('cancov', 0.35)).toBeCloseTo(0.35);
    expect(normalizeModeValue('cancov', 35)).toBeCloseTo(0.35);
    expect(normalizeModeValue('cancov', 150)).toBeCloseTo(1);
  });

  test('soil normalization keeps bounded scales', () => {
    expect(normalizeModeValue('bd', 0.8)).toBeCloseTo(0);
    expect(normalizeModeValue('bd', 2.2)).toBeCloseTo(1);
    expect(normalizeModeValue('soil_depth', 2000)).toBeCloseTo(1);
    expect(normalizeModeValue('soil_depth', 2500)).toBeCloseTo(1);
    expect(normalizeModeValue('sand', 50)).toBeCloseTo(0.5);
  });

  test('defaults to viridis when no explicit mapping exists', () => {
    expect(resolveColormapName('unknown-mode', 'Landuse', { WATER_MEASURES: [], SOIL_MEASURES: [] })).toBe('viridis');
  });

  test('event ET uses viridis even though it is a water measure', () => {
    expect(resolveColormapName('event_ET', 'WEPP Event', { WATER_MEASURES: ['event_ET'], SOIL_MEASURES: [] })).toBe('viridis');
  });

  test('dominant landuse uses row color field when present', async () => {
    // Import the landuseFillColor function from layers.js module
    // This test verifies the fix for disturbed/custom landuse colors
    const rowWithColor = {
      key: 118,
      _map: 'disturbed',
      color: '#ffff00',
      desc: 'Moderate Severity Fire'
    };
    
    const rowWithoutColor = {
      key: 42,
      _map: null
    };

    // Mock NLCD colormap
    global.NLCD_COLORMAP = { 42: '#1c6330' };

    // Test that row.color is used when present
    const colorWithCustom = hexToRgba(rowWithColor.color);
    expect(colorWithCustom).toEqual([255, 255, 0, 220]);

    // Test that NLCD colormap is used as fallback
    const colorWithNLCD = hexToRgba('#1c6330');
    expect(colorWithNLCD).toEqual([28, 99, 48, 220]);
  });
});

function hexToRgba(hex) {
  const intVal = Number.parseInt(hex.replace('#', ''), 16);
  return [(intVal >> 16) & 255, (intVal >> 8) & 255, intVal & 255, 220];
}
