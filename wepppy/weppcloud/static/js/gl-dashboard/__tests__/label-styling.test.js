import { afterEach, describe, expect, it } from '@jest/globals';
import { createLayerUtils } from '../map/layers.js';

class FakeLayer {
  constructor(props) {
    Object.assign(this, props);
  }
}

function relativeLuminance(rgb) {
  const channels = rgb.map((channel) => {
    const s = channel / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
}

function contrastRatio(a, b) {
  const l1 = relativeLuminance(a);
  const l2 = relativeLuminance(b);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

function buildLabelLayers() {
  const state = {
    dashboardMode: 'batch',
    subcatchmentLabelsVisible: true,
    subcatchmentsVisible: true,
    subcatchmentsGeoJson: {
      features: [
        {
          geometry: {
            type: 'Polygon',
            coordinates: [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]],
          },
          properties: {
            feature_key: 'batch;;spring;;run-1-1',
            TopazID: 1,
            runid: 'batch;;spring;;run-1',
            leaf_runid: 'run-1',
          },
        },
      ],
    },
    channelsVisible: true,
    channelLabelsVisible: true,
    channelLabelsData: [{ position: [1, 1], text: 'run-1:1' }],
    channelsLayers: [],
    detectedLayers: [],
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
  };

  const layerUtils = createLayerUtils({
    deck: {
      TextLayer: FakeLayer,
      GeoJsonLayer: FakeLayer,
      BitmapLayer: FakeLayer,
      IconLayer: FakeLayer,
    },
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

  const stack = layerUtils.buildLayerStack({ id: 'base' });
  const subcatchmentLabels = stack.find((layer) => layer.id === 'subcatchment-labels');
  const channelLabels = stack.find((layer) => layer.id === 'channel-labels');
  return { subcatchmentLabels, channelLabels };
}

function setThemeTokens(tokens) {
  Object.entries(tokens).forEach(([name, value]) => {
    document.documentElement.style.setProperty(name, value);
  });
}

afterEach(() => {
  document.documentElement.removeAttribute('style');
});

describe('gl-dashboard map label styling', () => {
  it('reduces label font sizes and keeps AA contrast in light themes', () => {
    setThemeTokens({
      '--wc-color-page': '#ffffff',
      '--wc-color-surface': '#ffffff',
      '--wc-color-surface-alt': '#f3f4f5',
      '--wc-color-text': '#1f2328',
      '--wc-color-text-muted': '#4b5563',
    });

    const { subcatchmentLabels, channelLabels } = buildLabelLayers();

    expect(subcatchmentLabels).toBeDefined();
    expect(channelLabels).toBeDefined();
    expect(subcatchmentLabels.getSize).toBe(12);
    expect(channelLabels.getSize).toBe(13);

    const subcatchContrast = contrastRatio(
      subcatchmentLabels.getColor.slice(0, 3),
      subcatchmentLabels.outlineColor.slice(0, 3),
    );
    const channelContrast = contrastRatio(
      channelLabels.getColor.slice(0, 3),
      channelLabels.outlineColor.slice(0, 3),
    );

    expect(subcatchContrast).toBeGreaterThanOrEqual(4.5);
    expect(channelContrast).toBeGreaterThanOrEqual(4.5);
    expect(channelLabels.getColor).not.toEqual([26, 115, 232, 255]);
  });

  it('promotes low-alpha muted theme values to AA contrast', () => {
    setThemeTokens({
      '--wc-color-page': '#fcfcfc',
      '--wc-color-surface': '#fcfcfc',
      '--wc-color-surface-alt': '#f3f3f4',
      '--wc-color-text': '#15151DEB',
      '--wc-color-text-muted': '#0E0E2A47',
    });

    const { subcatchmentLabels } = buildLabelLayers();
    const contrast = contrastRatio(
      subcatchmentLabels.getColor.slice(0, 3),
      subcatchmentLabels.outlineColor.slice(0, 3),
    );

    expect(contrast).toBeGreaterThanOrEqual(4.5);
  });
});
