/**
 * gl-dashboard entrypoint/orchestrator. Wires modules, binds DOM events, and exposes globals.
 * Business logic lives in gl-dashboard submodules (colors, data, layers, graphs, ui, scenario).
 */
(async function () {
  const ctx = window.GL_DASHBOARD_CONTEXT || {};
  const target = document.getElementById('gl-dashboard-map');

  if (!target) {
    return;
  }

  if (typeof deck === 'undefined' || !deck.Deck) {
    target.innerHTML = '<div style="padding:1rem;color:#e11d48;">deck.gl script failed to load.</div>';
    return;
  }

  const scriptUrl = (document.currentScript && document.currentScript.src) || '';
  const moduleBase = scriptUrl
    ? scriptUrl.replace(/gl-dashboard\.js(?:\?.*)?$/, 'gl-dashboard/')
    : `${ctx.sitePrefix || ''}/static/js/gl-dashboard/`;

  let config;
  let colorsModule;
  let stateModule;
  let graphModule;
  let graphModeModule;
  let yearSliderModule;
  let queryEngineModule;
  let graphLoadersModule;
  let detectorModule;
  let layerUtilsModule;
  let mapControllerModule;
  let layerRendererModule;
  let scenarioModule;
  let weppDataModule;
  let rasterUtilsModule;
  let graphControllerModule;
  let detectionControllerModule;
  let basemapControllerModule;
  let rapDataModule;

  try {
    [
      config,
      colorsModule,
      stateModule,
      graphModule,
      graphModeModule,
      yearSliderModule,
      queryEngineModule,
      graphLoadersModule,
      detectorModule,
      layerUtilsModule,
      mapControllerModule,
      layerRendererModule,
      scenarioModule,
      weppDataModule,
      rasterUtilsModule,
      graphControllerModule,
      detectionControllerModule,
      basemapControllerModule,
      rapDataModule,
    ] = await Promise.all([
      import(`${moduleBase}config.js`),
      import(`${moduleBase}colors.js`),
      import(`${moduleBase}state.js`),
      import(`${moduleBase}graphs/timeseries-graph.js`),
      import(`${moduleBase}ui/graph-mode.js`),
      import(`${moduleBase}ui/year-slider.js`),
      import(`${moduleBase}data/query-engine.js`),
      import(`${moduleBase}graphs/graph-loaders.js`),
      import(`${moduleBase}layers/detector.js`),
      import(`${moduleBase}map/layers.js`),
      import(`${moduleBase}map/controller.js`),
      import(`${moduleBase}layers/renderer.js`),
      import(`${moduleBase}scenario/manager.js`),
      import(`${moduleBase}data/wepp-data.js`),
      import(`${moduleBase}map/raster-utils.js`),
      import(`${moduleBase}graphs/controller.js`),
      import(`${moduleBase}layers/orchestrator.js`),
      import(`${moduleBase}map/basemap-controller.js`),
      import(`${moduleBase}data/rap-data.js`),
    ]);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error('gl-dashboard: failed to load modules', err);
    target.innerHTML = '<div style="padding:1rem;color:#e11d48;">Module load failed.</div>';
    return;
  }

  const {
    COMPARISON_MEASURES,
    WATER_MEASURES,
    SOIL_MEASURES,
    GRAPH_CONTEXT_KEYS,
    GRAPH_MODES,
    DEFAULT_CONTROLLER_OPTIONS,
    BASE_LAYER_DEFS,
    GRAPH_DEFS,
    CUMULATIVE_MEASURE_OPTIONS,
    MONTH_LABELS,
    createBasemapDefs,
    NLCD_COLORMAP,
    NLCD_LABELS,
    RAP_BAND_LABELS,
  } = config;

  const WEPP_YEARLY_PATH = 'wepp/output/interchange/loss_pw0.all_years.hill.parquet';
  const WEPP_LOSS_PATH = 'wepp/output/interchange/loss_pw0.hill.parquet';
  const WATAR_PATH = 'ash/post/hillslope_annuals.parquet';

  const colorScaleFactory =
    (typeof colorsModule.createColorScales === 'function' && colorsModule.createColorScales) ||
    (typeof config.createColorScales === 'function' && config.createColorScales);
  const colorScales =
    colorScaleFactory?.(typeof createColormap === 'function' ? createColormap : null) || {
      viridisScale: null,
      winterScale: null,
      jet2Scale: null,
      rdbuScale: null,
      viridisColor: colorsModule.viridisColor,
      winterColor: colorsModule.winterColor,
      jet2Color: colorsModule.jet2Color,
      divergingColor: colorsModule.divergingColor,
      rdbuColor: colorsModule.rdbuColor,
    };
  const {
    viridisScale,
    winterScale,
    jet2Scale,
    rdbuScale,
    viridisColor = colorsModule.viridisColor,
    winterColor = colorsModule.winterColor,
    jet2Color = colorsModule.jet2Color,
    divergingColor = colorsModule.divergingColor,
    rdbuColor = colorsModule.rdbuColor,
  } = colorScales;

  const { getState, setValue, setState, initState } = stateModule;
  const { createLayerUtils } = layerUtilsModule;
  const { createMapController } = mapControllerModule;
  const { createLayerRenderer } = layerRendererModule;
  const { createTimeseriesGraph } = graphModule;
  const { createGraphModeController } = graphModeModule;
  const { createYearSlider } = yearSliderModule;
  const { createScenarioManager } = scenarioModule;
  const { createQueryEngine } = queryEngineModule;
  const { createWeppDataManager } = weppDataModule;
  const { createRasterUtils } = rasterUtilsModule;
  const { createGraphController } = graphControllerModule;
  const { createDetectionController } = detectionControllerModule;
  const { createBasemapController } = basemapControllerModule;
  const { createRapDataManager } = rapDataModule;

  const { basemapDefs } = createBasemapDefs();
  const BASEMAP_DEFS = basemapDefs;

  const mapCenter = ctx.mapCenter; // [longitude, latitude]
  const mapExtent = ctx.mapExtent; // [west, south, east, north]
  let initialZoom = ctx.zoom || 5;
  if (mapExtent && mapExtent.length === 4 && mapExtent.every(Number.isFinite)) {
    const [west, south, east, north] = mapExtent;
    const span = Math.max(east - west, north - south);
    initialZoom = Math.max(2, Math.min(16, Math.log2(360 / (span || 0.001)) + 0.5));
  }

  const initialViewState = {
    longitude: mapCenter && mapCenter[0] != null ? mapCenter[0] : ctx.longitude || -114.5,
    latitude: mapCenter && mapCenter[1] != null ? mapCenter[1] : ctx.latitude || 43.8,
    zoom: initialZoom,
    minZoom: 2,
    maxZoom: 17,
    pitch: 0,
    bearing: 0,
  };

  initState({
    currentBasemapKey: BASEMAP_DEFS[ctx.basemap] ? ctx.basemap : 'googleTerrain',
    currentViewState: initialViewState,
    subcatchmentsVisible: true,
    subcatchmentLabelsVisible: false,
  });
  const state = getState();
  function bindStateKeys(keys) {
    keys.forEach((key) => {
      Object.defineProperty(window, key, {
        configurable: true,
        get() {
          return state[key];
        },
        set(val) {
          setValue(key, val);
        },
      });
    });
  }

  bindStateKeys([
    'currentBasemapKey',
    'currentScenarioPath',
    'comparisonMode',
    'subcatchmentsVisible',
    'subcatchmentLabelsVisible',
    'currentViewState',
    'graphFocus',
    'graphMode',
    'activeGraphKey',
    'rapSelectedYear',
    'rapCumulativeMode',
    'weppYearlySelectedYear',
    'weppEventSelectedDate',
  ]);
  window.glDashboardState = state;

  const queryEngine = createQueryEngine(ctx);
  const { postQueryEngine, postBaseQueryEngine, postQueryEngineForScenario } = queryEngine;
  let mapController;
  let layerUtils;
  let updateLayerList = () => {};
  let updateLegendsPanel = () => {};
  let timeseriesGraph;
  let graphModeController;
  let pendingApplyLayers = false;
  let suppressApplyLayersOnModeChange = false;
  let handleGraphPanelToggle = () => {};
  let loadRapTimeseriesData = async () => {};
  let loadWeppYearlyTimeseriesData = async () => {};
  let activateGraphItem = async () => {};
  let getClimateGraphOptions = () => ({});
  let getCumulativeGraphOptions = () => ({});

  const layerListEl = document.getElementById('gl-layer-list');
  const layerEmptyEl = document.getElementById('gl-layer-empty');
  const graphListEl = document.getElementById('gl-graph-list');
  const graphEmptyEl = document.getElementById('gl-graph-empty');
  const legendContentEl = document.getElementById('gl-legends-content');
  const legendEmptyEl = document.getElementById('gl-legend-empty');
  const graphPanelEl = document.getElementById('gl-graph');
  const glMainEl = document.querySelector('.gl-main');
  const graphModeButtons = document.querySelectorAll('[data-graph-mode]');

  const yearSlider = createYearSlider({
    el: document.getElementById('gl-year-slider'),
    input: document.getElementById('gl-year-slider-input'),
    valueEl: document.getElementById('gl-year-slider-value'),
    minEl: document.getElementById('gl-year-slider-min'),
    maxEl: document.getElementById('gl-year-slider-max'),
    playBtn: document.getElementById('gl-year-slider-play'),
  });
  const climateCtx = ctx.climate;
  if (climateCtx && climateCtx.startYear != null && climateCtx.endYear != null) {
    yearSlider.init({
      startYear: climateCtx.startYear,
      endYear: climateCtx.endYear,
      hasObserved: climateCtx.hasObserved,
    });
  }
  window.glDashboardYearSlider = yearSlider;

  if (typeof createRasterUtils !== 'function') {
    throw new Error('gl-dashboard: raster utils module failed to load');
  }

  const { loadRaster, loadSbsImage, fetchGdalInfo } = createRasterUtils({
    ctx,
    getState,
    setValue,
    colorFn: viridisColor,
  });

  function setViewState(viewState) {
    setValue('currentViewState', viewState);
    if (mapController) {
      mapController.setViewState(viewState);
    }
  }

  if (typeof createBasemapController !== 'function') {
    throw new Error('gl-dashboard: basemap controller module failed to load');
  }

  const basemapController = createBasemapController({
    deck,
    basemapDefs: BASEMAP_DEFS,
    getState,
    setValue,
  });
  if (basemapController) {
    basemapController.setBaseLayer(basemapController.createBaseLayer(getState().currentBasemapKey));
  }

  window.glDashboardSetBasemap = (key) => basemapController && basemapController.setBasemap(key);
  window.glDashboardBasemaps = BASEMAP_DEFS;
  window.glDashboardToggleLabels = (visible) => basemapController && basemapController.toggleSubcatchmentLabels(visible);
  window.glDashboardToggleSubcatchments = (visible) => basemapController && basemapController.toggleSubcatchments(visible);

  function pickActiveWeppEventLayer() {
    const layers = getState().weppEventLayers || [];
    for (let i = layers.length - 1; i >= 0; i--) {
      if (layers[i].visible) return layers[i];
    }
    return null;
  }

  function pickActiveWeppYearlyLayer() {
    const layers = getState().weppYearlyLayers || [];
    for (let i = layers.length - 1; i >= 0; i--) {
      if (layers[i].visible) return layers[i];
    }
    return null;
  }

  const weppDataManager = createWeppDataManager({
    ctx,
    getState,
    setValue,
    setState,
    postQueryEngine,
    postBaseQueryEngine,
    pickActiveWeppEventLayer,
    WEPP_YEARLY_PATH,
    WEPP_LOSS_PATH,
  });

  const {
    fetchWeppSummary,
    refreshWeppStatisticData: refreshWeppStatisticDataCore,
    computeWeppRanges: computeWeppRangesCore,
    computeWeppYearlyRanges: computeWeppYearlyRangesCore,
    computeWeppYearlyDiffRanges: computeWeppYearlyDiffRangesCore,
    loadBaseWeppYearlyData: loadBaseWeppYearlyDataCore,
    refreshWeppYearlyData: refreshWeppYearlyDataCore,
    computeWeppEventRanges: computeWeppEventRangesCore,
    computeWeppEventDiffRanges: computeWeppEventDiffRangesCore,
    loadBaseWeppEventData: loadBaseWeppEventDataCore,
    refreshWeppEventData: refreshWeppEventDataCore,
  } = weppDataManager;

  if (typeof createRapDataManager !== 'function') {
    throw new Error('gl-dashboard: rap data module failed to load');
  }

  const { refreshRapData, pickActiveRapLayer } = createRapDataManager({
    getState,
    setValue,
    postQueryEngine,
  });

  const scenarioManager = createScenarioManager({
    ctx,
    getState,
    setValue,
    setState,
    postQueryEngine,
    postBaseQueryEngine,
    fetchWeppSummary,
    weppDataManager,
    onScenarioChange: handleScenarioChange,
    onComparisonChange: handleComparisonChange,
  });

  const {
    buildScenarioUrl,
    buildBaseUrl,
    setScenario,
    setComparisonMode,
    computeComparisonDiffRanges,
  } = scenarioManager;

  window.glDashboardSetScenario = setScenario;
  window.glDashboardSetComparisonMode = setComparisonMode;

  function deselectAllSubcatchmentOverlays(options = {}) {
    const { skipApply = false, skipUpdate = false } = options;
    const keys = [
      'landuseLayers',
      'soilsLayers',
      'hillslopesLayers',
      'watarLayers',
      'weppLayers',
      'weppYearlyLayers',
      'weppEventLayers',
      'rapLayers',
    ];
    const updates = {};
    keys.forEach((key) => {
      const layers = (getState()[key] || []).map((l) => ({ ...l, visible: false }));
      updates[key] = layers;
    });
    updates.rapCumulativeMode = false;
    updates.activeGraphKey = null;
    setState(updates);
    clearGraphModeOverride();
    setGraphFocus(false, { force: true, skipModeSync: true });
    syncGraphLayout({ resetContext: true });
    if (!skipApply) {
      applyLayers();
    }
    if (!skipUpdate) {
      updateLayerList();
    }
  }

  async function refreshWeppStatisticData() {
    const changed = await refreshWeppStatisticDataCore();
    if (changed) {
      computeWeppRangesCore();
      applyLayers();
      updateLegendsPanel();
    }
  }

  async function refreshWeppYearlyData() {
    const changed = await refreshWeppYearlyDataCore();
    if (changed) {
      computeWeppYearlyRangesCore();
      if (getState().comparisonMode && getState().weppYearlySelectedYear != null) {
        computeWeppYearlyDiffRangesCore(getState().weppYearlySelectedYear);
      }
      applyLayers();
      updateLegendsPanel();
    }
  }

  async function refreshWeppEventData() {
    const changed = await refreshWeppEventDataCore();
    if (changed) {
      computeWeppEventRangesCore();
      if (getState().comparisonMode) {
        await loadBaseWeppEventDataCore();
        computeWeppEventDiffRangesCore();
      }
      applyLayers();
      updateLegendsPanel();
    }
  }

  layerUtils = createLayerUtils({
    deck,
    getState,
    colorScales: { viridisColor, winterColor, jet2Color, rdbuScale: rdbuColor },
    constants: {
      WATER_MEASURES,
      SOIL_MEASURES,
      NLCD_COLORMAP,
      NLCD_LABELS,
      RAP_BAND_LABELS,
      COMPARISON_MEASURES,
    },
  });

  mapController = createMapController({
    deck,
    target,
    controllerOptions: DEFAULT_CONTROLLER_OPTIONS,
    initialViewState,
    layers: [basemapController ? basemapController.getBaseLayer() : undefined].filter(Boolean),
    onViewStateChange: ({ viewState }) => {
      setViewState({
        ...viewState,
        minZoom: initialViewState.minZoom,
        maxZoom: initialViewState.maxZoom,
      });
    },
    onHover: (info) => {
      if (info && info.object && info.object.properties) {
        const props = info.object.properties;
        const topaz = props.TopazID || props.topaz_id || props.topaz || props.id;
        if (topaz != null) {
          timeseriesGraph && timeseriesGraph.highlightSubcatchment(String(topaz));
          return;
        }
      }
      timeseriesGraph && timeseriesGraph.clearHighlight();
    },
    getTooltip: (info) => layerUtils.formatTooltip(info),
    onError: (error) => {
      // eslint-disable-next-line no-console
      console.error('gl-dashboard render error', error);
    },
  });
  const { deckgl } = mapController;
  window.glDashboardDeck = deckgl;

  function applyLayers() {
    if (!layerUtils || !mapController) {
      pendingApplyLayers = true;
      return;
    }
    const stack = layerUtils.buildLayerStack(basemapController.getBaseLayer());
    mapController.applyLayers(stack);
    suppressApplyLayersOnModeChange = true;
    try {
      syncGraphLayout();
    } finally {
      suppressApplyLayersOnModeChange = false;
    }
    updateLegendsPanel();
  }

  if (basemapController && basemapController.setApplyLayers) {
    basemapController.setApplyLayers(applyLayers);
  }

  if (typeof createDetectionController !== 'function') {
    throw new Error('gl-dashboard: detection controller module failed to load');
  }

  const detectionController = createDetectionController({
    ctx,
    detectorModule,
    getState,
    setState,
    setValue,
    buildScenarioUrl,
    buildBaseUrl,
    fetchWeppSummary,
    weppLossPath: WEPP_LOSS_PATH,
    weppYearlyPath: WEPP_YEARLY_PATH,
    watarPath: WATAR_PATH,
    postQueryEngine,
    yearSlider,
    climateCtx,
    applyLayers: () => applyLayers(),
    updateLayerList: () => updateLayerList(),
    nlcdColormap: NLCD_COLORMAP,
    soilColorForValue: colorsModule.soilColorForValue,
    loadRaster,
    loadSbsImage,
    fetchGdalInfo,
    computeComparisonDiffRanges,
    baseLayerDefs: BASE_LAYER_DEFS,
    rapBandLabels: RAP_BAND_LABELS,
  });

  const {
    detectRasterLayers,
    detectLanduseOverlays,
    detectSoilsOverlays,
    detectHillslopesOverlays,
    detectWatarOverlays,
    detectWeppOverlays,
    detectWeppYearlyOverlays,
    detectWeppEventOverlays,
    detectRapOverlays,
    detectLayers,
  } = detectionController;

  function handleComparisonChange() {
    applyLayers();
    updateLayerList();
    updateLegendsPanel();
  }

  function handleGraphModeChange(payload = {}) {
    if (suppressApplyLayersOnModeChange) return;
    suppressApplyLayersOnModeChange = true;
    try {
      applyLayers();
      if (payload.contextKey === GRAPH_CONTEXT_KEYS.CLIMATE_YEARLY && getState().activeGraphKey === 'climate-yearly') {
        const graphOptions = getClimateGraphOptions();
        activateGraphItem('climate-yearly', { force: true, graphOptions, keepFocus: true });
      }
    } finally {
      suppressApplyLayersOnModeChange = false;
    }
  }

  function onHighlightSubcatchment(topazId) {
    if (getState().graphHighlightedTopazId === topazId) return;
    setValue('graphHighlightedTopazId', topazId);
    applyLayers();
  }

  timeseriesGraph = createTimeseriesGraph({
    container: document.getElementById('gl-graph-container'),
    emptyEl: graphEmptyEl,
    tooltipEl: document.getElementById('gl-graph-tooltip'),
    panelEl: graphPanelEl,
    getGraphFocus: () => getState().graphFocus,
    setGraphFocus: (focus) => setGraphFocus(focus),
    onPanelToggle: (visible) => handleGraphPanelToggle(visible),
    onHighlightSubcatchment,
  });
  timeseriesGraph.init();
  window.glDashboardTimeseriesGraph = timeseriesGraph;

  graphModeController = createGraphModeController({
    getState,
    setValue,
    domRefs: { glMainEl, graphPanelEl, graphModeButtons },
    yearSlider,
    timeseriesGraph: () => timeseriesGraph,
    onModeChange: handleGraphModeChange,
  });

  const {
    clearGraphModeOverride,
    setGraphFocus,
    setGraphCollapsed,
    toggleGraphPanel,
    setGraphMode,
    syncGraphLayout,
    ensureGraphExpanded,
  } = graphModeController;

  const omniScenarios = Array.isArray(ctx.omniScenarios) ? ctx.omniScenarios : [];
  const graphScenarios = [{ name: 'Base', path: '' }].concat(
    omniScenarios.map((s, idx) => {
      const name = s.name || `scenario-${idx + 1}`;
      const path = s.path || `_pups/omni/scenarios/${name}`;
      return { name, path };
    }),
  );

  if (typeof createGraphController !== 'function') {
    throw new Error('gl-dashboard: graph controller module failed to load');
  }

  const graphController = createGraphController({
        graphDefs: GRAPH_DEFS,
        graphScenarios,
        graphLoadersFactory: () =>
          graphLoadersModule.createGraphLoaders({
            graphScenarios,
            postQueryEngine: queryEngine.postQueryEngine,
            postBaseQueryEngine: queryEngine.postBaseQueryEngine,
            postQueryEngineForScenario: queryEngine.postQueryEngineForScenario,
            viridisColor,
            winterColor,
            jet2Color,
            RAP_BAND_LABELS,
          }),
        yearSlider,
        getState,
        setValue,
        graphModeController,
        timeseriesGraph: () => timeseriesGraph,
        graphPanelEl,
        graphModeButtons,
        graphEmptyEl,
        graphListEl,
        cumulativeMeasureOptions: CUMULATIVE_MEASURE_OPTIONS,
        monthLabels: MONTH_LABELS,
      });

  const {
    renderGraphList,
    getClimateGraphOptions: graphGetClimateGraphOptions,
    getCumulativeGraphOptions: graphGetCumulativeGraphOptions,
    loadRapTimeseriesData: graphLoadRapTimeseriesData,
    loadWeppYearlyTimeseriesData: graphLoadWeppYearlyTimeseriesData,
    activateGraphItem: graphActivateGraphItem,
    handleGraphPanelToggle: graphHandleGraphPanelToggle,
    bindModeButtons,
  } = graphController;

  getClimateGraphOptions = graphGetClimateGraphOptions;
  getCumulativeGraphOptions = graphGetCumulativeGraphOptions;
  loadRapTimeseriesData = graphLoadRapTimeseriesData;
  loadWeppYearlyTimeseriesData = graphLoadWeppYearlyTimeseriesData;
  activateGraphItem = graphActivateGraphItem;
  handleGraphPanelToggle = graphHandleGraphPanelToggle;

  bindModeButtons();

  const layerRenderer = createLayerRenderer({
    getState,
    setValue,
    layerUtils,
    domRefs: {
      layerListEl,
      layerEmptyEl,
      legendsContentEl: legendContentEl,
      legendEmptyEl,
    },
    yearSlider,
    deselectAllSubcatchmentOverlays,
    activateWeppYearlyLayer,
    refreshWeppStatisticData,
    refreshRapData,
    refreshWeppEventData,
    loadRapTimeseriesData,
    loadWeppYearlyTimeseriesData,
    applyLayers,
    syncGraphLayout,
    clearGraphModeOverride,
    setGraphFocus,
    setGraphCollapsed,
    pickActiveWeppEventLayer,
    soilColorForValue: colorsModule.soilColorForValue,
    constants: {
      COMPARISON_MEASURES,
      WATER_MEASURES,
      SOIL_MEASURES,
      RAP_BAND_LABELS,
      NLCD_COLORMAP,
      NLCD_LABELS,
    },
  });
  ({ updateLayerList, updateLegendsPanel } = layerRenderer);
  window.glDashboardUpdateLegends = updateLegendsPanel;

  const initialGraphMode = graphPanelEl && graphPanelEl.classList.contains('is-collapsed')
    ? GRAPH_MODES.MINIMIZED
    : getState().graphFocus
      ? GRAPH_MODES.FULL
      : GRAPH_MODES.SPLIT;
  setGraphMode(getState().graphMode || initialGraphMode, { source: 'auto', resetContext: true });

  window.glDashboardToggleGraphPanel = toggleGraphPanel;
  window.glDashboardSetGraphMode = setGraphMode;

  async function handleScenarioChange({ scenarioPath, phase } = {}) {
    const targetScenario = scenarioPath != null ? scenarioPath : getState().currentScenarioPath;
    const activeScenario = getState().currentScenarioPath;
    if (targetScenario != null && targetScenario !== activeScenario) {
      return;
    }

    if (phase === 'before_base') {
      await Promise.all([
        detectLanduseOverlays(),
        detectSoilsOverlays(),
        detectWeppOverlays(),
        detectWeppYearlyOverlays(),
      ]);
      return;
    }

    applyLayers();
    const graphEl = document.getElementById('gl-graph');
    const graphVisible = graphEl && !graphEl.classList.contains('is-collapsed');
    if (graphVisible) {
      if (getState().rapCumulativeMode || (getState().rapLayers || []).some((l) => l.visible)) {
        await loadRapTimeseriesData();
      }
      const activeWeppYearly = pickActiveWeppYearlyLayer();
      if (activeWeppYearly) {
        await loadWeppYearlyTimeseriesData();
      }
    }
  }

  async function activateWeppYearlyLayer() {
    const metadata = getState().weppYearlyMetadata;
    if (!metadata || !metadata.years || !metadata.years.length) {
      syncGraphLayout();
      return;
    }
    const minYear = metadata.minYear;
    const maxYear = metadata.maxYear;
    let selected = getState().weppYearlySelectedYear;
    if (selected == null || selected < minYear || selected > maxYear) {
      selected = maxYear;
    }
    setValue('weppYearlySelectedYear', selected);
    yearSlider.setRange(minYear, maxYear, selected);
    await refreshWeppYearlyData();
    setValue('activeGraphKey', 'wepp-yearly');
    await loadWeppYearlyTimeseriesData();
    syncGraphLayout();
  }

  yearSlider.on('change', async (year) => {
    let needsApply = false;
    const hasActiveRap = getState().rapCumulativeMode || (getState().rapLayers || []).some((l) => l.visible);
    if (hasActiveRap) {
      setValue('rapSelectedYear', year);
      await refreshRapData();
      needsApply = true;
      if (timeseriesGraph._source === GRAPH_CONTEXT_KEYS.RAP) {
        timeseriesGraph.setCurrentYear(year);
      }
    }
    const activeWeppYearly = pickActiveWeppYearlyLayer();
    if (activeWeppYearly) {
      setValue('weppYearlySelectedYear', year);
      await refreshWeppYearlyData();
      needsApply = true;
      if (timeseriesGraph._source === GRAPH_CONTEXT_KEYS.WEPP_YEARLY) {
        timeseriesGraph.setCurrentYear(year);
      }
    }
    const activeClimate = getState().activeGraphKey === 'climate-yearly' || timeseriesGraph._source === GRAPH_CONTEXT_KEYS.CLIMATE_YEARLY;
    if (activeClimate) {
      setValue('climateYearlySelectedYear', year);
      if (timeseriesGraph._source === GRAPH_CONTEXT_KEYS.CLIMATE_YEARLY) {
        timeseriesGraph.setCurrentYear(year);
      }
    }
    if (needsApply) {
      applyLayers();
    }
  });

  function bindScenarioSelector() {
    const scenarioSelect = document.getElementById('gl-scenario-select');
    const scenarioDisplay = document.getElementById('gl-scenario-display');
    if (!scenarioSelect || scenarioSelect.dataset.glScenarioBound === 'true') return;
    scenarioSelect.dataset.glScenarioBound = 'true';
    scenarioSelect.addEventListener('change', (e) => {
      const scenarioPath = e.target.value;
      const scenarioName =
        (e.target.options && e.target.options[e.target.selectedIndex] && e.target.options[e.target.selectedIndex].text) || 'Base';
      setScenario(scenarioPath);
      if (scenarioDisplay) {
        scenarioDisplay.innerHTML = `Scenario <strong>${scenarioName}</strong>`;
      }
    });
  }

  function bindComparisonToggle() {
    const comparisonToggle = document.getElementById('gl-comparison-toggle');
    const comparisonIndicator = document.getElementById('gl-comparison-indicator');
    if (!comparisonToggle || comparisonToggle.dataset.glComparisonBound === 'true') return;
    comparisonToggle.dataset.glComparisonBound = 'true';
    const syncIndicator = (checked) => {
      if (comparisonIndicator) {
        comparisonIndicator.style.display = checked ? 'inline' : 'none';
      }
    };
    syncIndicator(comparisonToggle.checked);
    comparisonToggle.addEventListener('change', (e) => {
      setComparisonMode(e.target.checked);
      syncIndicator(e.target.checked);
    });
  }

  async function initializeScenarioFromSelect() {
    const scenarioSelect = document.getElementById('gl-scenario-select');
    if (!scenarioSelect || !scenarioSelect.value) return false;

    const scenarioPath = scenarioSelect.value;
    const scenarioName =
      (scenarioSelect.options && scenarioSelect.options[scenarioSelect.selectedIndex] && scenarioSelect.options[scenarioSelect.selectedIndex].text) || 'Base';
    const scenarioDisplay = document.getElementById('gl-scenario-display');
    if (scenarioDisplay) {
      scenarioDisplay.innerHTML = `Scenario <strong>${scenarioName}</strong>`;
    }
    await setScenario(scenarioPath);
    return true;
  }

  function initializeDashboard() {
    // Synchronous UI setup - runs immediately
    bindScenarioSelector();
    bindComparisonToggle();
    basemapController.bindBasemapControls();
    renderGraphList();
    applyLayers(); // Render map immediately with base layers

    // Async layer detection - fire and forget, don't block page
    (async () => {
      try {
        const scenarioInitialized = await initializeScenarioFromSelect();
        const detectionTasks = [detectLayers()];
        if (!scenarioInitialized) {
          detectionTasks.push(
            detectLanduseOverlays(),
            detectSoilsOverlays(),
            detectWeppOverlays(),
            detectWeppYearlyOverlays(),
          );
        }
        await Promise.all(detectionTasks);
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn('gl-dashboard: layer detection failed', err);
      }
    })();
  }

  window.glDashboardGraphToggled = handleGraphPanelToggle;
  window.glDashboardHighlightSubcatchment = onHighlightSubcatchment;

  initializeDashboard();
})();
