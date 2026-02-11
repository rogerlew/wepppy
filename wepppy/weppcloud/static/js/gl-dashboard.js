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
  const scriptQueryIndex = scriptUrl.indexOf('?');
  const scriptQuery = scriptQueryIndex >= 0 ? scriptUrl.slice(scriptQueryIndex) : '';
  const moduleBase = scriptUrl
    ? scriptUrl.replace(/gl-dashboard\.js(?:\?.*)?$/, 'gl-dashboard/')
    : `${ctx.sitePrefix || ''}/static/js/gl-dashboard/`;
  const moduleSuffix = scriptQuery || '';

  let config;
  let batchKeysModule;
  let colorsModule;
  let stateModule;
  let graphModule;
  let graphModeModule;
  let yearSliderModule;
  let monthSliderModule;
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
  let openetDataModule;

  try {
    [
      config,
      batchKeysModule,
      colorsModule,
      stateModule,
      graphModule,
      graphModeModule,
      yearSliderModule,
      monthSliderModule,
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
      openetDataModule,
    ] = await Promise.all([
      import(`${moduleBase}config.js${moduleSuffix}`),
      import(`${moduleBase}batch-keys.js${moduleSuffix}`),
      import(`${moduleBase}colors.js${moduleSuffix}`),
      import(`${moduleBase}state.js${moduleSuffix}`),
      import(`${moduleBase}graphs/timeseries-graph.js${moduleSuffix}`),
      import(`${moduleBase}ui/graph-mode.js${moduleSuffix}`),
      import(`${moduleBase}ui/year-slider.js${moduleSuffix}`),
      import(`${moduleBase}ui/month-slider.js${moduleSuffix}`),
      import(`${moduleBase}data/query-engine.js${moduleSuffix}`),
      import(`${moduleBase}graphs/graph-loaders.js${moduleSuffix}`),
      import(`${moduleBase}layers/detector.js${moduleSuffix}`),
      import(`${moduleBase}map/layers.js${moduleSuffix}`),
      import(`${moduleBase}map/controller.js${moduleSuffix}`),
      import(`${moduleBase}layers/renderer.js${moduleSuffix}`),
      import(`${moduleBase}scenario/manager.js${moduleSuffix}`),
      import(`${moduleBase}data/wepp-data.js${moduleSuffix}`),
      import(`${moduleBase}map/raster-utils.js${moduleSuffix}`),
      import(`${moduleBase}graphs/controller.js${moduleSuffix}`),
      import(`${moduleBase}layers/orchestrator.js${moduleSuffix}`),
      import(`${moduleBase}map/basemap-controller.js${moduleSuffix}`),
      import(`${moduleBase}data/rap-data.js${moduleSuffix}`),
      import(`${moduleBase}data/openet-data.js${moduleSuffix}`),
    ]);
  } catch (err) {
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
  const { DASHBOARD_MODES, getFeatureKeyFromProperties } = batchKeysModule;

  const WEPP_YEARLY_PATH = 'wepp/output/interchange/loss_pw0.all_years.hill.parquet';
  const WEPP_LOSS_PATH = 'wepp/output/interchange/loss_pw0.hill.parquet';
  const WEPP_CHANNEL_PATH = 'wepp/output/interchange/loss_pw0.all_years.chn.parquet';
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
    viridisColor = colorsModule.viridisColor,
    winterColor = colorsModule.winterColor,
    jet2Color = colorsModule.jet2Color,
    rdbuColor = colorsModule.rdbuColor,
  } = colorScales;

  const { getState, setValue, setState, initState, subscribe } = stateModule;
  const { createLayerUtils } = layerUtilsModule;
  const { createMapController } = mapControllerModule;
  const { createLayerRenderer } = layerRendererModule;
  const { createTimeseriesGraph } = graphModule;
  const { createGraphModeController } = graphModeModule;
  const { createYearSlider } = yearSliderModule;
  const { createMonthSlider } = monthSliderModule;
  const { createScenarioManager } = scenarioModule;
  const { createQueryEngine } = queryEngineModule;
  const { createWeppDataManager } = weppDataModule;
  const { createOpenetDataManager } = openetDataModule;
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
  const dashboardMode =
    ctx.mode === DASHBOARD_MODES.BATCH ? DASHBOARD_MODES.BATCH : DASHBOARD_MODES.RUN;

  initState({
    dashboardMode,
    batchModeEnabled: !!ctx.batchModeEnabled,
    currentBasemapKey: BASEMAP_DEFS[ctx.basemap] ? ctx.basemap : 'googleTerrain',
    currentViewState: initialViewState,
    subcatchmentsVisible: true,
    subcatchmentLabelsVisible: false,
    channelsVisible: true,
    channelLabelsVisible: false,
    sbsColorShiftEnabled: false,
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
    'dashboardMode',
    'batchModeEnabled',
    'currentBasemapKey',
    'currentScenarioPath',
    'comparisonMode',
    'subcatchmentsVisible',
    'subcatchmentLabelsVisible',
    'channelsVisible',
    'channelLabelsVisible',
    'sbsColorShiftEnabled',
    'currentViewState',
    'graphFocus',
    'graphMode',
    'activeGraphKey',
    'rapSelectedYear',
    'rapCumulativeMode',
    'weppYearlySelectedYear',
    'weppEventSelectedDate',
    'openetSelectedMonthIndex',
    'openetSelectedDatasetKey',
    'openetYearlySelectedDatasetKey',
    'openetYearlySelectedYear',
    'openetYearlyWaterYear',
    'openetYearlyStartMonth',
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
  let suppressApplyLayersOnModeChange = false;
  let handleGraphPanelToggle = () => {};
  let loadRapTimeseriesData = async () => {};
  let loadWeppYearlyTimeseriesData = async () => {};
  let loadOpenetTimeseriesData = async () => {};
  let loadOpenetYearlyTimeseriesData = async () => {};
  let activateGraphItem = async () => {};
  let getClimateGraphOptions = () => ({});

  const layerListEl = document.getElementById('gl-layer-list');
  const layerEmptyEl = document.getElementById('gl-layer-empty');
  const graphListEl = document.getElementById('gl-graph-list');
  const graphEmptyEl = document.getElementById('gl-graph-empty');
  const legendContentEl = document.getElementById('gl-legends-content');
  const legendEmptyEl = document.getElementById('gl-legend-empty');
  const graphPanelEl = document.getElementById('gl-graph');
  const glMainEl = document.querySelector('.gl-main');
  const graphModeButtons = document.querySelectorAll('[data-graph-mode]');
  const batchStatusContentEl = document.getElementById('gl-batch-status-content');

  const yearSlider = createYearSlider({
    el: document.getElementById('gl-year-slider'),
    input: document.getElementById('gl-year-slider-input'),
    valueEl: document.getElementById('gl-year-slider-value'),
    minEl: document.getElementById('gl-year-slider-min'),
    maxEl: document.getElementById('gl-year-slider-max'),
    playBtn: document.getElementById('gl-year-slider-play'),
  });
  const monthSlider = createMonthSlider({
    el: document.getElementById('gl-month-slider'),
    input: document.getElementById('gl-month-slider-input'),
    valueEl: document.getElementById('gl-month-slider-value'),
    minEl: document.getElementById('gl-month-slider-min'),
    maxEl: document.getElementById('gl-month-slider-max'),
    playBtn: document.getElementById('gl-month-slider-play'),
    formatLabel: (item) => (item && item.label ? item.label : ''),
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
  window.glDashboardMonthSlider = monthSlider;

  function renderBatchStatus(readiness) {
    if (!batchStatusContentEl) return;
    while (batchStatusContentEl.firstChild) {
      batchStatusContentEl.removeChild(batchStatusContentEl.firstChild);
    }

    if (!readiness) {
      batchStatusContentEl.textContent = 'Batch status unavailable.';
      return;
    }

    const total = Number(readiness.totalRuns) || 0;
    const readyRuns = Array.isArray(readiness.readyRuns) ? readiness.readyRuns : [];
    const readyCount = readyRuns.length;
    const excludedCount = Math.max(0, total - readyCount);

    const headline = document.createElement('div');
    headline.innerHTML = `<strong>${readyCount}</strong> of <strong>${total}</strong> runs ready`;
    batchStatusContentEl.appendChild(headline);

    const mergedCounts = readiness.mergedCounts || {};
    if (mergedCounts.subcatchments != null) {
      const row = document.createElement('div');
      row.textContent = `Subcatchments: ${Number(mergedCounts.subcatchments) || 0} features`;
      batchStatusContentEl.appendChild(row);
    }

    if (excludedCount) {
      const title = document.createElement('div');
      title.style.marginTop = '0.35rem';
      title.innerHTML = `<strong>Excluded</strong> (${excludedCount})`;
      batchStatusContentEl.appendChild(title);
    }

    const statuses = Array.isArray(readiness.statuses) ? readiness.statuses : [];
    const excluded = statuses.filter((s) => s && s.ready === false);
    if (excluded.length) {
      const ul = document.createElement('ul');
      ul.style.margin = '0.25rem 0 0 1.1rem';
      ul.style.padding = '0';
      ul.style.display = 'grid';
      ul.style.gap = '0.15rem';
      excluded.forEach((s) => {
        const li = document.createElement('li');
        const missing = Array.isArray(s.missingRequired) ? s.missingRequired.join(', ') : '';
        li.textContent = `${s.leaf_runid || s.runid}${missing ? ` (missing: ${missing})` : ''}`;
        ul.appendChild(li);
      });
      batchStatusContentEl.appendChild(ul);
    }

    const degraded = statuses.filter((s) => s && s.ready === true && Array.isArray(s.missingOptional) && s.missingOptional.length);
    if (degraded.length) {
      const title = document.createElement('div');
      title.style.marginTop = '0.35rem';
      title.innerHTML = `<strong>Degraded</strong> (${degraded.length})`;
      batchStatusContentEl.appendChild(title);
      const ul = document.createElement('ul');
      ul.style.margin = '0.25rem 0 0 1.1rem';
      ul.style.padding = '0';
      ul.style.display = 'grid';
      ul.style.gap = '0.15rem';
      degraded.forEach((s) => {
        const li = document.createElement('li');
        li.textContent = `${s.leaf_runid || s.runid} (missing: ${s.missingOptional.join(', ')})`;
        ul.appendChild(li);
      });
      batchStatusContentEl.appendChild(ul);
    }
  }

  async function initializeBatchReadiness() {
    if (dashboardMode !== DASHBOARD_MODES.BATCH) return null;
    if (!ctx || !ctx.batch || !Array.isArray(ctx.batch.runs) || !ctx.batch.runs.length) {
      const readiness = { totalRuns: 0, readyRuns: [], statuses: [], mergedCounts: { subcatchments: 0, channels: 0 } };
      setValue('batchReadiness', readiness);
      renderBatchStatus(readiness);
      return readiness;
    }
    if (!detectorModule || typeof detectorModule.detectBatchReadiness !== 'function') {
      renderBatchStatus(null);
      return null;
    }

    try {
      const readiness = await detectorModule.detectBatchReadiness({ ctx });
      setValue('batchReadiness', readiness);
      renderBatchStatus(readiness);
      if (readiness && Array.isArray(readiness.readyRuns) && readiness.readyRuns.length) {
        ctx.batch.runs = readiness.readyRuns;
      }
      return readiness;
    } catch (err) {
      console.warn('gl-dashboard: batch readiness failed', err);
      renderBatchStatus(null);
      return null;
    }
  }

  if (typeof createRasterUtils !== 'function') {
    throw new Error('gl-dashboard: raster utils module failed to load');
  }

  const { loadRaster, loadRasterFromDownload, loadSbsImage, fetchGdalInfo } = createRasterUtils({
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

  function pickActiveWeppYearlyChannelLayer() {
    const layers = getState().weppYearlyChannelLayers || [];
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
    WEPP_CHANNEL_PATH,
  });

  const {
    fetchWeppSummary,
    fetchWeppChannelSummary,
    refreshWeppStatisticData: refreshWeppStatisticDataCore,
    refreshWeppChannelStatisticData: refreshWeppChannelStatisticDataCore,
    computeWeppRanges: computeWeppRangesCore,
    computeWeppChannelRanges: computeWeppChannelRangesCore,
    refreshWeppYearlyChannelData: refreshWeppYearlyChannelDataCore,
    computeWeppYearlyChannelRanges: computeWeppYearlyChannelRangesCore,
    computeWeppYearlyRanges: computeWeppYearlyRangesCore,
    computeWeppYearlyDiffRanges: computeWeppYearlyDiffRangesCore,
    refreshWeppYearlyData: refreshWeppYearlyDataCore,
    computeWeppEventRanges: computeWeppEventRangesCore,
    computeWeppEventDiffRanges: computeWeppEventDiffRangesCore,
    loadBaseWeppEventData: loadBaseWeppEventDataCore,
    refreshWeppEventData: refreshWeppEventDataCore,
  } = weppDataManager;

  if (typeof createRapDataManager !== 'function') {
    throw new Error('gl-dashboard: rap data module failed to load');
  }

  const { refreshRapData } = createRapDataManager({
    getState,
    setValue,
    postQueryEngine,
  });

  if (typeof createOpenetDataManager !== 'function') {
    throw new Error('gl-dashboard: OpenET data module failed to load');
  }

  const { refreshOpenetData } = createOpenetDataManager({
    getState,
    setState,
    postBaseQueryEngine,
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
      'openetLayers',
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
    const channelChanged = typeof refreshWeppChannelStatisticDataCore === 'function'
      ? await refreshWeppChannelStatisticDataCore()
      : false;
    if (changed) {
      computeWeppRangesCore();
    }
    if (channelChanged && typeof computeWeppChannelRangesCore === 'function') {
      computeWeppChannelRangesCore();
    }
    if (changed || channelChanged) {
      applyLayers();
      updateLegendsPanel();
    }
  }

  async function refreshWeppYearlyData() {
    const changed = await refreshWeppYearlyDataCore();
    const channelChanged = typeof refreshWeppYearlyChannelDataCore === 'function'
      ? await refreshWeppYearlyChannelDataCore()
      : false;
    if (changed) {
      computeWeppYearlyRangesCore();
      if (getState().comparisonMode && getState().weppYearlySelectedYear != null) {
        computeWeppYearlyDiffRangesCore(getState().weppYearlySelectedYear);
      }
    }
    if (channelChanged && typeof computeWeppYearlyChannelRangesCore === 'function') {
      computeWeppYearlyChannelRangesCore();
    }
    if (changed || channelChanged) {
      applyLayers();
      updateLegendsPanel();
    }
  }

  async function refreshWeppYearlyChannelData() {
    if (typeof refreshWeppYearlyChannelDataCore !== 'function') return;
    const changed = await refreshWeppYearlyChannelDataCore();
    if (changed && typeof computeWeppYearlyChannelRangesCore === 'function') {
      computeWeppYearlyChannelRangesCore();
    }
    if (changed) {
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

  let userInteractedWithMap = false;
  let didAutoFitBatch = false;

  mapController = createMapController({
    deck,
    target,
    controllerOptions: DEFAULT_CONTROLLER_OPTIONS,
    initialViewState,
    layers: [basemapController ? basemapController.getBaseLayer() : undefined].filter(Boolean),
    onViewStateChange: ({ viewState, interactionState }) => {
      if (
        interactionState &&
        (interactionState.isDragging ||
          interactionState.isPanning ||
          interactionState.isZooming ||
          interactionState.isRotating)
      ) {
        userInteractedWithMap = true;
      }
      setViewState({
        ...viewState,
        minZoom: initialViewState.minZoom,
        maxZoom: initialViewState.maxZoom,
      });
    },
    onHover: (info) => {
      if (info && info.object && info.object.properties) {
        const props = info.object.properties;
        const state = getState();
        const key =
          state.dashboardMode === DASHBOARD_MODES.BATCH
            ? getFeatureKeyFromProperties(props)
            : props.TopazID || props.topaz_id || props.topaz || props.id || props.WeppID || props.wepp_id;
        if (key != null) {
          timeseriesGraph && timeseriesGraph.highlightSubcatchment(String(key));
          return;
        }
      }
      timeseriesGraph && timeseriesGraph.clearHighlight();
    },
    getTooltip: (info) => layerUtils.formatTooltip(info),
    onError: (error) => {
      console.error('gl-dashboard render error', error);
    },
  });
  const { deckgl } = mapController;
  window.glDashboardDeck = deckgl;

  function computeGeoJsonExtent(geoJson) {
    if (!geoJson || !Array.isArray(geoJson.features)) return null;
    let west = Infinity;
    let south = Infinity;
    let east = -Infinity;
    let north = -Infinity;

    function walk(coords) {
      if (!Array.isArray(coords)) return;
      if (coords.length >= 2 && typeof coords[0] === 'number' && typeof coords[1] === 'number') {
        const lon = coords[0];
        const lat = coords[1];
        if (!Number.isFinite(lon) || !Number.isFinite(lat)) return;
        if (lon < west) west = lon;
        if (lon > east) east = lon;
        if (lat < south) south = lat;
        if (lat > north) north = lat;
        return;
      }
      coords.forEach(walk);
    }

    for (const feature of geoJson.features) {
      const geom = feature && feature.geometry;
      if (!geom || !geom.coordinates) continue;
      walk(geom.coordinates);
    }

    if (![west, south, east, north].every((v) => Number.isFinite(v))) {
      return null;
    }
    return [west, south, east, north];
  }

  if (dashboardMode === DASHBOARD_MODES.BATCH && typeof subscribe === 'function') {
    subscribe(['subcatchmentsGeoJson'], () => {
      if (didAutoFitBatch || userInteractedWithMap) return;
      const geoJson = getState().subcatchmentsGeoJson;
      const extent = computeGeoJsonExtent(geoJson);
      if (!extent) return;
      const [west, south, east, north] = extent;
      const span = Math.max(east - west, north - south);
      const zoom = Math.max(2, Math.min(16, Math.log2(360 / (span || 0.001)) + 0.5));
      const next = {
        ...(getState().currentViewState || initialViewState),
        longitude: (west + east) / 2,
        latitude: (south + north) / 2,
        zoom,
        minZoom: initialViewState.minZoom,
        maxZoom: initialViewState.maxZoom,
      };
      didAutoFitBatch = true;
      setViewState(next);
    });
  }

  function applyLayers() {
    if (!layerUtils || !mapController) return;
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

  const isOmniChild = !!ctx.isOmniChild;
  const omniScenarios = !isOmniChild && Array.isArray(ctx.omniScenarios) ? ctx.omniScenarios : [];
  const omniContrasts = !isOmniChild && Array.isArray(ctx.omniContrasts) ? ctx.omniContrasts : [];
  let graphDefs = GRAPH_DEFS;
  if (isOmniChild) {
    graphDefs = graphDefs.filter((group) => group.key !== 'omni' && group.key !== 'omni-contrasts');
  }
  if (!omniScenarios.length) {
    graphDefs = graphDefs.filter((group) => group.key !== 'omni');
  }
  if (!omniContrasts.length) {
    graphDefs = graphDefs.filter((group) => group.key !== 'omni-contrasts');
  }
  let baseScenarioLabel = getState().baseScenarioLabel || 'Undisturbed';
  const graphScenarios = [{ name: baseScenarioLabel, path: '' }].concat(
    omniScenarios.map((s, idx) => {
      const name = s.name || `scenario-${idx + 1}`;
      const path = s.path || `_pups/omni/scenarios/${name}`;
      return { name, path };
    }),
  );
  const graphContrastScenarios = omniContrasts.map((c, idx) => {
    const id = c.id != null ? c.id : idx + 1;
    const name = c.name || `contrast-${id}`;
    const path = c.path || `_pups/omni/contrasts/${id}`;
    return { id, name, path };
  });
  const graphCumulativeScenarios = graphScenarios.concat(graphContrastScenarios);

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
    monthSlider,
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
  } = graphModeController;

  if (typeof createGraphController !== 'function') {
    throw new Error('gl-dashboard: graph controller module failed to load');
  }

  const graphController = createGraphController({
    graphDefs,
    graphScenarios,
    graphContrastScenarios,
    graphLoadersFactory: () =>
      graphLoadersModule.createGraphLoaders({
        cacheNamespace: `${ctx.runid || ''}::${ctx.config || ''}`,
        graphScenarios,
        contrastScenarios: graphContrastScenarios,
        graphCumulativeScenarios,
        postQueryEngine,
        postBaseQueryEngine,
        postQueryEngineForScenario,
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
    loadRapTimeseriesData: graphLoadRapTimeseriesData,
    loadWeppYearlyTimeseriesData: graphLoadWeppYearlyTimeseriesData,
    loadOpenetTimeseriesData: graphLoadOpenetTimeseriesData,
    loadOpenetYearlyTimeseriesData: graphLoadOpenetYearlyTimeseriesData,
    activateGraphItem: graphActivateGraphItem,
    handleGraphPanelToggle: graphHandleGraphPanelToggle,
    bindModeButtons,
  } = graphController;

  getClimateGraphOptions = graphGetClimateGraphOptions;
  loadRapTimeseriesData = graphLoadRapTimeseriesData;
  loadWeppYearlyTimeseriesData = graphLoadWeppYearlyTimeseriesData;
  loadOpenetTimeseriesData = graphLoadOpenetTimeseriesData;
  loadOpenetYearlyTimeseriesData = graphLoadOpenetYearlyTimeseriesData;
  activateGraphItem = graphActivateGraphItem;
  handleGraphPanelToggle = graphHandleGraphPanelToggle;

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
    fetchWeppChannelSummary,
    weppLossPath: WEPP_LOSS_PATH,
    weppChannelPath: WEPP_CHANNEL_PATH,
    weppYearlyPath: WEPP_YEARLY_PATH,
    watarPath: WATAR_PATH,
    postQueryEngine,
    postBaseQueryEngine,
    yearSlider,
    monthSlider,
    climateCtx,
    applyLayers: () => applyLayers(),
    updateLayerList: () => updateLayerList(),
    nlcdColormap: NLCD_COLORMAP,
    soilColorForValue: colorsModule.soilColorForValue,
    loadRaster,
    loadRasterFromDownload,
    loadSbsImage,
    fetchGdalInfo,
    computeComparisonDiffRanges,
    baseLayerDefs: BASE_LAYER_DEFS,
    rapBandLabels: RAP_BAND_LABELS,
    monthLabels: MONTH_LABELS,
    onBaseScenarioDetected: (label) => setBaseScenarioLabel(label),
  });

  const {
    detectLanduseOverlays,
    detectSoilsOverlays,
    detectWeppOverlays,
    detectWeppChannelOverlays,
    detectWeppYearlyChannelOverlays,
    detectWeppYearlyOverlays,
    detectLayers,
  } = detectionController;

  function setBaseScenarioLabel(label = 'Undisturbed') {
    const normalized = label || 'Undisturbed';
    if (normalized === baseScenarioLabel) return;
    baseScenarioLabel = normalized;
    setValue('baseScenarioLabel', normalized);

    const scenarioSelect = document.getElementById('gl-scenario-select');
    if (scenarioSelect) {
      const baseOption = scenarioSelect.querySelector('option[value=""]');
      if (baseOption) {
        baseOption.textContent = `${normalized} (Base)`;
      }
      if (!getState().currentScenarioPath) {
        const scenarioDisplay = document.getElementById('gl-scenario-display');
        if (scenarioDisplay) {
          scenarioDisplay.innerHTML = `Scenario <strong>${normalized}</strong>`;
        }
      }
    }

    if (graphScenarios.length) {
      graphScenarios[0].name = normalized;
      if (graphCumulativeScenarios.length) {
        graphCumulativeScenarios[0].name = normalized;
      }
      renderGraphList();
    }
  }

  bindModeButtons();
  if (dashboardMode !== DASHBOARD_MODES.BATCH && typeof subscribe === 'function') {
    subscribe(['openetMetadata'], () => {
      renderGraphList();
    });
  }

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
    activateWeppYearlyChannelLayer,
    refreshWeppStatisticData,
    refreshRapData,
    refreshOpenetData,
    refreshWeppEventData,
    loadRapTimeseriesData,
    loadWeppYearlyTimeseriesData,
    loadOpenetTimeseriesData,
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
        detectWeppChannelOverlays(),
        detectWeppYearlyOverlays(),
        detectWeppYearlyChannelOverlays(),
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

  async function activateWeppYearlyChannelLayer() {
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
    await refreshWeppYearlyChannelData();
    syncGraphLayout();
  }

  function openetIndexToXValue(index) {
    const meta = getState().openetMetadata;
    if (!meta || !Array.isArray(meta.months)) return null;
    const entry = meta.months[index];
    if (!entry) return null;
    const year = Number(entry.year);
    const month = Number(entry.month);
    if (!Number.isFinite(year) || !Number.isFinite(month)) return null;
    return Number((year + (month - 1) / 12).toFixed(6));
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
    const activeWeppYearlyChannel = pickActiveWeppYearlyChannelLayer();
    if (activeWeppYearly || activeWeppYearlyChannel) {
      setValue('weppYearlySelectedYear', year);
    }
    if (activeWeppYearly) {
      await refreshWeppYearlyData();
      needsApply = true;
      if (timeseriesGraph._source === GRAPH_CONTEXT_KEYS.WEPP_YEARLY) {
        timeseriesGraph.setCurrentYear(year);
      }
    } else if (activeWeppYearlyChannel) {
      await refreshWeppYearlyChannelData();
      needsApply = true;
    }
    const activeClimate = getState().activeGraphKey === 'climate-yearly' || timeseriesGraph._source === GRAPH_CONTEXT_KEYS.CLIMATE_YEARLY;
    if (activeClimate) {
      setValue('climateYearlySelectedYear', year);
      if (timeseriesGraph._source === GRAPH_CONTEXT_KEYS.CLIMATE_YEARLY) {
        timeseriesGraph.setCurrentYear(year);
      }
    }
    const activeOpenetYearly =
      getState().activeGraphKey === 'openet-yearly' || timeseriesGraph._source === GRAPH_CONTEXT_KEYS.OPENET_YEARLY;
    if (activeOpenetYearly) {
      setValue('openetYearlySelectedYear', year);
      await loadOpenetYearlyTimeseriesData();
    }
    if (needsApply) {
      applyLayers();
    }
  });

  monthSlider.on('change', async (index) => {
    if (dashboardMode === DASHBOARD_MODES.BATCH) return;
    setValue('openetSelectedMonthIndex', index);
    const changed = await refreshOpenetData();
    if (changed) {
      applyLayers();
      updateLegendsPanel();
    }
    const graphEl = document.getElementById('gl-graph');
    const graphVisible = graphEl && !graphEl.classList.contains('is-collapsed');
    if (graphVisible) {
      if (timeseriesGraph && timeseriesGraph._source === GRAPH_CONTEXT_KEYS.OPENET) {
        const xVal = openetIndexToXValue(index);
        if (xVal != null) {
          timeseriesGraph.setCurrentYear(xVal);
        }
      } else if ((getState().openetLayers || []).some((layer) => layer.visible)) {
        await loadOpenetTimeseriesData();
      }
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
        scenarioPath && e.target.options && e.target.options[e.target.selectedIndex]
          ? e.target.options[e.target.selectedIndex].text
          : baseScenarioLabel;
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

  function bindSbsColorShiftToggle() {
    const colorShiftToggle = document.getElementById('gl-sbs-color-shift-toggle');
    if (!colorShiftToggle || colorShiftToggle.dataset.glSbsColorShiftBound === 'true') return;
    colorShiftToggle.dataset.glSbsColorShiftBound = 'true';
    colorShiftToggle.checked = !!getState().sbsColorShiftEnabled;
    colorShiftToggle.addEventListener('change', (e) => {
      const enabled = !!(e && e.target && e.target.checked);
      if (enabled === getState().sbsColorShiftEnabled) {
        return;
      }
      setValue('sbsColorShiftEnabled', enabled);
      applyLayers();
      updateLegendsPanel();
    });
  }

  async function initializeScenarioFromSelect() {
    const scenarioSelect = document.getElementById('gl-scenario-select');
    if (!scenarioSelect || !scenarioSelect.value) return false;

    const scenarioPath = scenarioSelect.value;
    const scenarioName =
      scenarioPath && scenarioSelect.options && scenarioSelect.options[scenarioSelect.selectedIndex]
        ? scenarioSelect.options[scenarioSelect.selectedIndex].text
        : baseScenarioLabel;
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
    bindSbsColorShiftToggle();
    setBaseScenarioLabel(baseScenarioLabel);
    basemapController.bindBasemapControls();
    if (dashboardMode === DASHBOARD_MODES.BATCH) {
      if (graphListEl) {
        graphListEl.innerHTML =
          '<li class="gl-layer-item" style="color:var(--wc-color-text-muted);">Graphs are not available in batch mode.</li>';
      }
      if (graphEmptyEl) {
        graphEmptyEl.textContent = 'Graphs are not available in batch mode.';
        graphEmptyEl.hidden = false;
      }
    } else {
      renderGraphList();
    }
    applyLayers(); // Render map immediately with base layers

    // Async layer detection - fire and forget, don't block page
    (async () => {
      try {
        const scenarioInitialized = await initializeScenarioFromSelect();
        if (dashboardMode === DASHBOARD_MODES.BATCH) {
          const readiness = await initializeBatchReadiness();
          if (readiness && Array.isArray(readiness.readyRuns) && readiness.readyRuns.length === 0) {
            console.warn('gl-dashboard: batch has no ready runs');
            return;
          }
        }
        const detectionTasks = [detectLayers()];
        if (!scenarioInitialized) {
          detectionTasks.push(
            detectLanduseOverlays(),
            detectSoilsOverlays(),
          );
          if (dashboardMode !== DASHBOARD_MODES.BATCH) {
            detectionTasks.push(
              detectWeppOverlays(),
              detectWeppChannelOverlays(),
              detectWeppYearlyOverlays(),
              detectWeppYearlyChannelOverlays(),
            );
          }
        }
        await Promise.all(detectionTasks);
      } catch (err) {
        console.warn('gl-dashboard: layer detection failed', err);
      }
    })();
  }

  window.glDashboardGraphToggled = handleGraphPanelToggle;
  window.glDashboardHighlightSubcatchment = onHighlightSubcatchment;

  initializeDashboard();
})();
