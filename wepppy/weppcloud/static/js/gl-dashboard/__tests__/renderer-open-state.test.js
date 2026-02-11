import { describe, expect, it, jest } from '@jest/globals';
import { createLayerRenderer } from '../layers/renderer.js';

function findDetailsForTitle(container, title) {
  const summaries = container.querySelectorAll('summary.gl-layer-group');
  for (const summary of summaries) {
    if (summary.textContent && summary.textContent.trim() === title) {
      return summary.closest('details');
    }
  }
  return null;
}

describe('gl-dashboard layer renderer', () => {
  it('preserves section open state across updates', () => {
    const layerListEl = document.createElement('ul');
    const layerEmptyEl = document.createElement('div');
    const state = {
      landuseLayers: [{ key: 'lu-dominant', label: 'Dominant landuse', visible: true }],
      soilsLayers: [],
      hillslopesLayers: [{ key: 'hillslope-slope', label: 'Slope (rise/run)', visible: false }],
      d8DirectionLayer: {
        key: 'd8-direction',
        label: 'D8 Direction',
        visible: false,
        path: 'dem/wbt/flovec.wgs.tif',
        data: [{ position: [0, 0], angle: 0 }],
        bounds: [0, 0, 1, 1],
        cellSizeMeters: 10,
      },
      channelsLayers: [],
      weppLayers: [],
      weppChannelLayers: [],
      weppYearlyLayers: [],
      weppYearlyChannelLayers: [],
      weppEventLayers: [],
      watarLayers: [],
      rapLayers: [],
      openetLayers: [],
      detectedLayers: [],
      rapCumulativeMode: false,
      weppStatistic: 'mean',
    };

    const renderer = createLayerRenderer({
      getState: () => state,
      setValue: jest.fn(),
      layerUtils: { getActiveLayersForLegend: () => [] },
      domRefs: { layerListEl, layerEmptyEl },
      yearSlider: { setRange: jest.fn() },
      deselectAllSubcatchmentOverlays: jest.fn(),
      activateWeppYearlyLayer: jest.fn(),
      activateWeppYearlyChannelLayer: jest.fn(),
      refreshWeppStatisticData: jest.fn(),
      refreshRapData: jest.fn(),
      refreshOpenetData: jest.fn(),
      refreshWeppEventData: jest.fn(),
      loadRapTimeseriesData: jest.fn(),
      loadWeppYearlyTimeseriesData: jest.fn(),
      loadOpenetTimeseriesData: jest.fn(),
      applyLayers: jest.fn(),
      syncGraphLayout: jest.fn(),
      clearGraphModeOverride: jest.fn(),
      setGraphFocus: jest.fn(),
      setGraphCollapsed: jest.fn(),
      pickActiveWeppEventLayer: jest.fn(),
      soilColorForValue: jest.fn(),
      constants: {},
    });

    renderer.updateLayerList();
    const hillslopesDetails = findDetailsForTitle(layerListEl, 'Hillslopes');
    expect(hillslopesDetails).not.toBeNull();
    expect(hillslopesDetails.open).toBe(false);

    hillslopesDetails.open = true;
    renderer.updateLayerList();

    const refreshedDetails = findDetailsForTitle(layerListEl, 'Hillslopes');
    expect(refreshedDetails).not.toBeNull();
    expect(refreshedDetails.open).toBe(true);
  });

  it('swaps SBS legend colors when color shift is enabled', () => {
    const legendsContentEl = document.createElement('div');
    const legendEmptyEl = document.createElement('p');
    legendEmptyEl.id = 'gl-legend-empty';
    legendsContentEl.appendChild(legendEmptyEl);

    const state = {
      landuseLayers: [],
      soilsLayers: [],
      hillslopesLayers: [],
      channelsLayers: [],
      weppLayers: [],
      weppChannelLayers: [],
      weppYearlyLayers: [],
      weppYearlyChannelLayers: [],
      weppEventLayers: [],
      watarLayers: [],
      rapLayers: [],
      openetLayers: [],
      detectedLayers: [{ key: 'sbs', label: 'SBS Map', visible: true }],
      sbsColorShiftEnabled: false,
      rapCumulativeMode: false,
      weppStatistic: 'mean',
    };

    const renderer = createLayerRenderer({
      getState: () => state,
      setValue: jest.fn(),
      layerUtils: { getActiveLayersForLegend: () => state.detectedLayers },
      domRefs: {
        layerListEl: document.createElement('ul'),
        layerEmptyEl: document.createElement('div'),
        legendsContentEl,
        legendEmptyEl,
      },
      yearSlider: { setRange: jest.fn() },
      deselectAllSubcatchmentOverlays: jest.fn(),
      activateWeppYearlyLayer: jest.fn(),
      activateWeppYearlyChannelLayer: jest.fn(),
      refreshWeppStatisticData: jest.fn(),
      refreshRapData: jest.fn(),
      refreshOpenetData: jest.fn(),
      refreshWeppEventData: jest.fn(),
      loadRapTimeseriesData: jest.fn(),
      loadWeppYearlyTimeseriesData: jest.fn(),
      loadOpenetTimeseriesData: jest.fn(),
      applyLayers: jest.fn(),
      syncGraphLayout: jest.fn(),
      clearGraphModeOverride: jest.fn(),
      setGraphFocus: jest.fn(),
      setGraphCollapsed: jest.fn(),
      pickActiveWeppEventLayer: jest.fn(),
      soilColorForValue: jest.fn(),
      constants: {},
    });

    renderer.updateLegendsPanel();
    let swatches = legendsContentEl.querySelectorAll('.gl-legend-categorical__swatch');
    expect(swatches.length).toBe(4);
    expect(swatches[1].style.backgroundColor).toContain('77, 230, 0');

    state.sbsColorShiftEnabled = true;
    renderer.updateLegendsPanel();
    swatches = legendsContentEl.querySelectorAll('.gl-legend-categorical__swatch');
    expect(swatches.length).toBe(4);
    expect(swatches[1].style.backgroundColor).toContain('86, 180, 233');
  });
});
