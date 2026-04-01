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
    expect(swatches).toHaveLength(4);
    expect(swatches[1].style.backgroundColor).toContain('77, 230, 0');

    state.sbsColorShiftEnabled = true;
    renderer.updateLegendsPanel();
    swatches = legendsContentEl.querySelectorAll('.gl-legend-categorical__swatch');
    expect(swatches).toHaveLength(4);
    expect(swatches[1].style.backgroundColor).toContain('86, 180, 233');
  });

  it('allows editing the continuous legend max and reapplies WEPP ranges', () => {
    const legendsContentEl = document.createElement('div');
    const legendEmptyEl = document.createElement('p');
    legendEmptyEl.id = 'gl-legend-empty';
    legendsContentEl.appendChild(legendEmptyEl);

    const state = {
      comparisonMode: false,
      currentScenarioPath: '',
      landuseLayers: [],
      soilsLayers: [],
      hillslopesLayers: [],
      channelsLayers: [],
      weppLayers: [{ key: 'runoff_volume', label: 'RUNOFF (MM)', mode: 'runoff_volume', visible: true }],
      weppChannelLayers: [],
      weppYearlyLayers: [],
      weppYearlyChannelLayers: [],
      weppEventLayers: [],
      watarLayers: [],
      rapLayers: [],
      openetLayers: [],
      detectedLayers: [],
      weppRanges: { runoff_volume: { min: 0, max: 35.7 } },
      rapCumulativeMode: false,
      weppStatistic: 'mean',
    };

    const setValue = jest.fn((key, value) => {
      state[key] = value;
    });
    const applyLayers = jest.fn();

    const renderer = createLayerRenderer({
      getState: () => state,
      setValue,
      layerUtils: { getActiveLayersForLegend: () => [{ ...state.weppLayers[0], category: 'WEPP' }] },
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
      applyLayers,
      syncGraphLayout: jest.fn(),
      clearGraphModeOverride: jest.fn(),
      setGraphFocus: jest.fn(),
      setGraphCollapsed: jest.fn(),
      pickActiveWeppEventLayer: jest.fn(),
      soilColorForValue: jest.fn(),
      constants: {
        COMPARISON_MEASURES: [],
        WATER_MEASURES: ['runoff_volume'],
        SOIL_MEASURES: [],
      },
    });

    renderer.updateLegendsPanel();
    const maxInput = legendsContentEl.querySelector('.gl-legend-range-input[data-range-kind="continuous"]');
    expect(maxInput).not.toBeNull();
    expect(Number(maxInput.value)).toBeCloseTo(35.7, 5);

    maxInput.value = '30';
    maxInput.dispatchEvent(new Event('change', { bubbles: true }));

    expect(state.weppRanges.runoff_volume).toEqual({ min: 0, max: 30 });
    expect(setValue).toHaveBeenCalledWith(
      'weppRanges',
      expect.objectContaining({ runoff_volume: { min: 0, max: 30 } }),
    );
    expect(applyLayers).toHaveBeenCalled();

    const refreshedInput = legendsContentEl.querySelector('.gl-legend-range-input[data-range-kind="continuous"]');
    expect(refreshedInput).not.toBeNull();
    expect(Number(refreshedInput.value)).toBeCloseTo(30, 5);
  });

  it('allows editing diverging legend max and enforces symmetric min/max', () => {
    const legendsContentEl = document.createElement('div');
    const legendEmptyEl = document.createElement('p');
    legendEmptyEl.id = 'gl-legend-empty';
    legendsContentEl.appendChild(legendEmptyEl);

    const state = {
      comparisonMode: true,
      currentScenarioPath: '_pups/omni/scenarios/burned',
      landuseLayers: [],
      soilsLayers: [],
      hillslopesLayers: [],
      channelsLayers: [],
      weppLayers: [{ key: 'subrunoff_volume', label: 'SUBRUNOFF (MM)', mode: 'subrunoff_volume', visible: true }],
      weppChannelLayers: [],
      weppYearlyLayers: [],
      weppYearlyChannelLayers: [],
      weppEventLayers: [],
      watarLayers: [],
      rapLayers: [],
      openetLayers: [],
      detectedLayers: [],
      comparisonDiffRanges: { subrunoff_volume: { min: -47.89, max: 47.89 } },
      rapCumulativeMode: false,
      weppStatistic: 'mean',
    };

    const setValue = jest.fn((key, value) => {
      state[key] = value;
    });
    const applyLayers = jest.fn();

    const renderer = createLayerRenderer({
      getState: () => state,
      setValue,
      layerUtils: { getActiveLayersForLegend: () => [{ ...state.weppLayers[0], category: 'WEPP' }] },
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
      applyLayers,
      syncGraphLayout: jest.fn(),
      clearGraphModeOverride: jest.fn(),
      setGraphFocus: jest.fn(),
      setGraphCollapsed: jest.fn(),
      pickActiveWeppEventLayer: jest.fn(),
      soilColorForValue: jest.fn(),
      constants: {
        COMPARISON_MEASURES: ['subrunoff_volume'],
        WATER_MEASURES: ['subrunoff_volume'],
        SOIL_MEASURES: [],
      },
    });

    renderer.updateLegendsPanel();
    const maxInput = legendsContentEl.querySelector('.gl-legend-range-input[data-range-kind="diverging"]');
    expect(maxInput).not.toBeNull();
    expect(Number(maxInput.value)).toBeCloseTo(47.89, 5);

    maxInput.value = '30';
    maxInput.dispatchEvent(new Event('change', { bubbles: true }));

    expect(state.comparisonDiffRanges.subrunoff_volume).toEqual({ min: -30, max: 30 });
    expect(setValue).toHaveBeenCalledWith(
      'comparisonDiffRanges',
      expect.objectContaining({ subrunoff_volume: { min: -30, max: 30 } }),
    );
    expect(applyLayers).toHaveBeenCalled();

    const refreshedInput = legendsContentEl.querySelector('.gl-legend-range-input[data-range-kind="diverging"]');
    expect(refreshedInput).not.toBeNull();
    expect(Number(refreshedInput.value)).toBeCloseTo(30, 5);
    const labels = legendsContentEl.querySelectorAll('.gl-legend-continuous__labels span');
    expect(labels[0].textContent).toBe('-30.00');
  });

  it('keeps RAP dataset filenames in hover tooltips instead of visible labels', () => {
    const layerListEl = document.createElement('ul');
    const layerEmptyEl = document.createElement('div');
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
      openetLayers: [],
      detectedLayers: [],
      rapCumulativeMode: false,
      rapLayers: [
        { key: 'rap-tree', label: 'Tree Cover', path: 'rap/rap_subcatchment.parquet', selected: true, visible: false },
        { key: 'rap-shrub', label: 'Shrub Cover', path: 'rap/rap_subcatchment.parquet', selected: true, visible: false },
      ],
      weppStatistic: 'mean',
    };

    const renderer = createLayerRenderer({
      getState: () => state,
      setValue: jest.fn(),
      layerUtils: { getActiveLayersForLegend: () => [] },
      domRefs: { layerListEl, layerEmptyEl },
      yearSlider: { setRange: jest.fn(), show: jest.fn() },
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
    const rapDetails = findDetailsForTitle(layerListEl, 'RAP');
    expect(rapDetails).not.toBeNull();

    const cumulativeLabel = rapDetails.querySelector('label[for="layer-RAP-cumulative"]');
    expect(cumulativeLabel).not.toBeNull();
    expect(cumulativeLabel.title).toBe('rap/rap_subcatchment.parquet');

    const treeLabel = rapDetails.querySelector('label[for="layer-RAP-band-rap-tree"]');
    expect(treeLabel).not.toBeNull();
    expect(treeLabel.textContent).toContain('Tree Cover');
    expect(treeLabel.textContent).not.toContain('rap/rap_subcatchment.parquet');
    expect(treeLabel.title).toBe('rap/rap_subcatchment.parquet');
    expect(layerListEl.querySelectorAll('.gl-layer-path')).toHaveLength(0);
  });

  it('hides visible filepath rows and keeps filepaths as hover-only tooltips', () => {
    const layerListEl = document.createElement('ul');
    const layerEmptyEl = document.createElement('div');
    const state = {
      landuseLayers: [{ key: 'lu-cancov', label: 'Canopy cover (cancov)', path: 'landuse/landuse.parquet', visible: true }],
      soilsLayers: [],
      hillslopesLayers: [],
      channelsLayers: [{ key: 'channels_order', label: 'Channel Order', path: 'resources/channels.json', visible: true }],
      weppLayers: [],
      weppChannelLayers: [],
      weppYearlyLayers: [],
      weppYearlyChannelLayers: [],
      weppEventLayers: [{ key: 'event-q', label: 'Runoff (Q)', path: 'wepp/event.parquet', visible: false }],
      watarLayers: [],
      rapLayers: [],
      openetLayers: [],
      detectedLayers: [],
      rapCumulativeMode: false,
      weppStatistic: 'mean',
      weppEventSelectedDate: null,
      weppEventMetadata: null,
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

    expect(layerListEl.querySelectorAll('.gl-layer-path')).toHaveLength(0);
    const landuseLabel = layerListEl.querySelector('label[for="layer-Landuse-lu-cancov"]');
    expect(landuseLabel).not.toBeNull();
    expect(landuseLabel.title).toBe('landuse/landuse.parquet');

    const channelsLabel = layerListEl.querySelector('label[for="layer-Channels-channels_order"]');
    expect(channelsLabel).not.toBeNull();
    expect(channelsLabel.title).toBe('resources/channels.json');

    const weppEventLabel = layerListEl.querySelector('label[for="layer-WEPP-Event-event-q"]');
    expect(weppEventLabel).not.toBeNull();
    expect(weppEventLabel.title).toBe('wepp/event.parquet');
  });

  it('renders RUSLE section after WEPP and honors explicit raster colormaps in legend', () => {
    const layerListEl = document.createElement('ul');
    const layerEmptyEl = document.createElement('div');
    const legendsContentEl = document.createElement('div');
    const legendEmptyEl = document.createElement('p');
    legendEmptyEl.id = 'gl-legend-empty';
    legendsContentEl.appendChild(legendEmptyEl);

    const state = {
      landuseLayers: [],
      soilsLayers: [],
      hillslopesLayers: [],
      channelsLayers: [],
      weppLayers: [{ key: 'soil_loss', label: 'Soil Loss', mode: 'soil_loss', visible: false }],
      weppChannelLayers: [],
      weppYearlyLayers: [],
      weppYearlyChannelLayers: [],
      weppEventLayers: [],
      watarLayers: [],
      rapLayers: [],
      openetLayers: [],
      detectedLayers: [
        {
          key: 'rusle-a-observed-rap-nomograph',
          group: 'rusle',
          label: 'RUSLE A (Observed RAP, Nomograph K)',
          path: 'rusle/a_observed_rap_polaris_nomograph.tif',
          colormap: 'jet2',
          units: 't/ha/yr',
          range: { min: 0, max: 12 },
          visible: true,
        },
        {
          key: 'rusle-k-nomograph',
          group: 'rusle',
          label: 'RUSLE K (POLARIS Nomograph)',
          path: 'rusle/k_polaris_nomograph.tif',
          colormap: 'plasma',
          units: 't*ha*h/(ha*MJ*mm)',
          range: { min: 0, max: 0.7 },
          visible: true,
        },
      ],
      rapCumulativeMode: false,
      weppStatistic: 'mean',
    };

    const renderer = createLayerRenderer({
      getState: () => state,
      setValue: jest.fn(),
      layerUtils: {
        getActiveLayersForLegend: () =>
          state.detectedLayers
            .filter((layer) => layer.visible)
            .map((layer) => ({ ...layer, category: 'Raster' })),
      },
      domRefs: { layerListEl, layerEmptyEl, legendsContentEl, legendEmptyEl },
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
    const summaries = Array.from(layerListEl.querySelectorAll('summary.gl-layer-group')).map((el) => (el.textContent || '').trim());
    const weppIdx = summaries.indexOf('WEPP');
    const rusleIdx = summaries.indexOf('RUSLE');
    expect(weppIdx).toBeGreaterThanOrEqual(0);
    expect(rusleIdx).toBeGreaterThan(weppIdx);

    renderer.updateLegendsPanel();
    const bars = Array.from(legendsContentEl.querySelectorAll('.gl-legend-continuous__bar'));
    expect(bars.length).toBeGreaterThanOrEqual(2);
    expect(bars.some((bar) => bar.className.includes('gl-legend-continuous__bar--jet2'))).toBe(true);
    expect(bars.some((bar) => bar.className.includes('gl-legend-continuous__bar--plasma'))).toBe(true);
  });

  it('renders A tolerance control with raster-max default and applies overrides to A range', () => {
    const originalGetContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = () => null;
    try {
      const layerListEl = document.createElement('ul');
      const layerEmptyEl = document.createElement('div');
      const legendsContentEl = document.createElement('div');
      const legendEmptyEl = document.createElement('p');
      legendEmptyEl.id = 'gl-legend-empty';
      legendsContentEl.appendChild(legendEmptyEl);

      const state = {
        rusleATolerance: null,
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
        detectedLayers: [
          {
            key: 'rusle-a-observed-rap-nomograph',
            group: 'rusle',
            label: 'RUSLE A (Observed RAP, Nomograph K)',
            path: 'rusle/a_observed_rap_polaris_nomograph.tif',
            colormap: 'jet2',
            units: 't/ha/yr',
            values: new Float32Array([1, 6, 12]),
            nodata: -9999,
            width: 3,
            height: 1,
            range: { min: 1, max: 12 },
            canvas: document.createElement('canvas'),
            visible: true,
          },
        ],
        rapCumulativeMode: false,
        weppStatistic: 'mean',
      };

      const setValue = jest.fn((key, value) => {
        state[key] = value;
      });
      const applyLayers = jest.fn();

      const renderer = createLayerRenderer({
        getState: () => state,
        setValue,
        layerUtils: {
          getActiveLayersForLegend: () =>
            state.detectedLayers
              .filter((layer) => layer.visible)
              .map((layer) => ({ ...layer, category: 'Raster' })),
        },
        domRefs: { layerListEl, layerEmptyEl, legendsContentEl, legendEmptyEl },
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
        applyLayers,
        syncGraphLayout: jest.fn(),
        clearGraphModeOverride: jest.fn(),
        setGraphFocus: jest.fn(),
        setGraphCollapsed: jest.fn(),
        pickActiveWeppEventLayer: jest.fn(),
        soilColorForValue: jest.fn(),
        constants: {},
      });

      renderer.updateLayerList();

      const toleranceLabel = layerListEl.querySelector('label[for="gl-rusle-a-tolerance-input"]');
      const toleranceInput = layerListEl.querySelector('#gl-rusle-a-tolerance-input');
      expect(toleranceLabel).not.toBeNull();
      expect(toleranceLabel.textContent).toContain('A Tolerance');
      expect(toleranceInput).not.toBeNull();
      expect(toleranceInput.value).toBe('12');

      toleranceInput.value = '6';
      toleranceInput.dispatchEvent(new Event('change', { bubbles: true }));

      expect(state.rusleATolerance).toBe(6);
      expect(setValue).toHaveBeenCalledWith('rusleATolerance', 6);
      expect(state.detectedLayers[0].range).toEqual({ min: 1, max: 6 });
      expect(applyLayers).toHaveBeenCalled();

      renderer.updateLegendsPanel();
      const legendLabels = legendsContentEl.querySelectorAll('.gl-legend-continuous__labels span');
      expect(legendLabels).toHaveLength(2);
      expect(legendLabels[0].textContent).toBe('1.0');
      expect(legendLabels[1].textContent).toBe('6.0');
    } finally {
      HTMLCanvasElement.prototype.getContext = originalGetContext;
    }
  });
});
