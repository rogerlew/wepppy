/**
 * gl-dashboard entrypoint/orchestrator. Wires modules, binds DOM events, and exposes globals.
 * Keep business logic in submodules (config/state/colors/data/graphs/layers/map).
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
  let stateModule;
  let graphModule;
  let queryEngineModule;
  let graphLoadersModule;
  let detectorModule;
  let layerUtilsModule;
  let mapControllerModule;
  let layerRendererModule;
  try {
    [config, stateModule, graphModule, queryEngineModule, graphLoadersModule, detectorModule, layerUtilsModule, mapControllerModule, layerRendererModule] = await Promise.all([
      import(`${moduleBase}config.js`),
      import(`${moduleBase}state.js`),
      import(`${moduleBase}graphs/timeseries-graph.js`),
      import(`${moduleBase}data/query-engine.js`),
      import(`${moduleBase}graphs/graph-loaders.js`),
      import(`${moduleBase}layers/detector.js`),
      import(`${moduleBase}map/layers.js`),
      import(`${moduleBase}map/controller.js`),
      import(`${moduleBase}layers/renderer.js`),
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
    DEFAULT_CONTROLLER_OPTIONS,
    BASE_LAYER_DEFS,
    GRAPH_DEFS,
    createBasemapDefs,
    createColorScales,
  } = config;
  const { getState, setValue, setState, initState } = stateModule;
  const { createLayerUtils } = layerUtilsModule;
  const { createMapController } = mapControllerModule;
  const { createLayerRenderer } = layerRendererModule;
  const { createTimeseriesGraph } = graphModule;
  const state = getState();
  const queryEngine = queryEngineModule.createQueryEngine(ctx);
  let graphLoaders;
  let glMainEl;
  let graphPanelEl;
  let graphModeButtons;
  let graphModeUserOverride = null;
  let graphControlsEnabled = true;
  // Use var to avoid TDZ issues if syncGraphModeForContext fires early during init.
  var lastGraphContextKey = null; // eslint-disable-line no-var

  function isRapActive(stateObj) {
    // RAP should only drive graph controls when a RAP overlay is actually in play
    if (stateObj.rapCumulativeMode) return true;
    return (stateObj.rapLayers || []).some((l) => l && l.visible);
  }

  function isWeppYearlyActive(stateObj) {
    if (!stateObj.weppYearlySummary) return false;
    return (stateObj.weppYearlyLayers || []).some((l) => l && l.visible);
  }

  const { rdbuScale, winterScale, jet2Scale } = createColorScales(
    typeof createColormap === 'function' ? createColormap : null
  );

  const { basemapDefs } = createBasemapDefs();
  const BASEMAP_DEFS = basemapDefs;
  const layerDefs = BASE_LAYER_DEFS;
  const graphDefs = GRAPH_DEFS;
  const {
    detectRasterLayers: detectRasterLayersData,
    detectLanduseOverlays: detectLanduseData,
    detectSoilsOverlays: detectSoilsData,
    detectHillslopesOverlays: detectHillslopesData,
    detectWatarOverlays: detectWatarData,
    detectWeppOverlays: detectWeppData,
    detectWeppYearlyOverlays: detectWeppYearlyData,
    detectWeppEventOverlays: detectWeppEventData,
    detectRapOverlays: detectRapData,
  } = detectorModule || {};

  const mapCenter = ctx.mapCenter; // [longitude, latitude]
  const mapExtent = ctx.mapExtent; // [west, south, east, north]

  let initialZoom = ctx.zoom || 5;
  if (mapExtent && mapExtent.length === 4 && mapExtent.every(Number.isFinite)) {
    const [west, south, east, north] = mapExtent;
    const span = Math.max(east - west, north - south);
    initialZoom = Math.max(2, Math.min(16, Math.log2(360 / (span || 0.001)) + 0.5));
  }

  const initialViewState = {
    longitude: mapCenter && mapCenter[0] != null ? mapCenter[0] : (ctx.longitude || -114.5),
    latitude: mapCenter && mapCenter[1] != null ? mapCenter[1] : (ctx.latitude || 43.8),
    zoom: initialZoom,
    minZoom: 2,
    maxZoom: 17,
    pitch: 0,
    bearing: 0,
  };

  const controllerOptions = DEFAULT_CONTROLLER_OPTIONS;

  initState({
    currentBasemapKey: BASEMAP_DEFS[ctx.basemap] ? ctx.basemap : 'googleTerrain',
    currentViewState: initialViewState,
    subcatchmentsVisible: true,
    subcatchmentLabelsVisible: false,
  });

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
    'currentScenarioPath',
    'comparisonMode',
    'baseSummaryCache',
    'comparisonDiffRanges',
    'subcatchmentsVisible',
    'currentBasemapKey',
    'currentViewState',
    'graphFocus',
    'graphMode',
    'activeGraphKey',
    'hillLossCache',
    'channelLossCache',
    'outletAllYearsCache',
    'hillslopeAreaCache',
    'graphDataCache',
    'landuseSummary',
    'soilsSummary',
    'hillslopesSummary',
    'watarSummary',
    'weppSummary',
    'weppStatistic',
    'weppYearlyMetadata',
    'weppYearlySelectedYear',
    'weppYearlySummary',
    'weppYearlyDiffRanges',
    'weppYearlyRanges',
    'weppYearlyCache',
    'baseWeppYearlyCache',
    'weppEventSummary',
    'weppEventMetadata',
    'weppEventSelectedDate',
    'weppEventRanges',
    'rapSummary',
    'rapMetadata',
    'rapSelectedYear',
    'rapCumulativeMode',
    'subcatchmentsGeoJson',
    'subcatchmentLabelsVisible',
    'graphHighlightedTopazId',
    'watarRanges',
    'weppRanges',
    'geoTiffLoader',
    'detectedLayers',
    'landuseLayers',
    'soilsLayers',
    'hillslopesLayers',
    'watarLayers',
    'weppLayers',
    'weppYearlyLayers',
    'weppEventLayers',
    'rapLayers',
  ]);

  function setViewState(viewState) {
    setValue('currentViewState', viewState);
    if (mapController) {
      mapController.setViewState(viewState);
    }
  }

  function createBaseLayer(basemapKey) {
    const basemapDef = BASEMAP_DEFS[basemapKey] || BASEMAP_DEFS.googleTerrain;
    return new deck.TileLayer({
      id: 'gl-dashboard-base-tiles',
      data: basemapDef.template,
      minZoom: 0,
      maxZoom: 19,
      tileSize: 256,
      maxRequests: 8,
      getTileData: async ({ index, signal }) => {
        const { x, y, z } = index || {};
        if (![x, y, z].every(Number.isFinite)) {
          throw new Error(`Tile coords missing: x=${x} y=${y} z=${z}`);
        }
        const url = basemapDef.getUrl(x, y, z);
        const response = await fetch(url, { signal, mode: 'cors' });
        if (!response.ok) {
          throw new Error(`Tile fetch failed ${response.status}: ${url}`);
        }
        const blob = await response.blob();
        return await createImageBitmap(blob);
      },
      onTileError: (err) => {
        // eslint-disable-next-line no-console
        console.error('gl-dashboard tile error', err);
      },
      renderSubLayers: (props) => {
        const tile = props.tile;
        const data = props.data;

        if (!tile || !data || !tile.bbox) {
          return null;
        }

        const { west, south, east, north } = tile.bbox;
        const bounds = [west, south, east, north];
        if (bounds.some((v) => !Number.isFinite(v))) {
          return null;
        }

        return new deck.BitmapLayer(props, {
          id: `${props.id}-${tile.id}`,
          data: null,
          image: data,
          bounds,
          pickable: false,
          opacity: 0.95,
        });
      },
    });
  }

  let mapController;
  let baseLayer = createBaseLayer(currentBasemapKey);

  function setBasemap(basemapKey) {
    if (!BASEMAP_DEFS[basemapKey]) {
      console.warn('gl-dashboard: unknown basemap key', basemapKey);
      return;
    }
    currentBasemapKey = basemapKey;
    baseLayer = createBaseLayer(basemapKey);
    applyLayers();
    // Update selector UI if present
    const selector = document.getElementById('gl-basemap-select');
    if (selector && selector.value !== basemapKey) {
      selector.value = basemapKey;
    }
  }

  function toggleSubcatchmentLabels(visible) {
    subcatchmentLabelsVisible = !!visible;
    applyLayers();
    // Update checkbox UI if present
    const checkbox = document.getElementById('gl-subcatchment-labels-toggle');
    if (checkbox && checkbox.checked !== subcatchmentLabelsVisible) {
      checkbox.checked = subcatchmentLabelsVisible;
    }
  }

  function toggleSubcatchments(visible) {
    const desired = !!visible;
    subcatchmentsVisible = desired;
    // Subcatchment overlays are GeoJson layers; toggling off hides all subcatchment-based layers.
    applyLayers();
    const checkbox = document.getElementById('gl-subcatchments-toggle');
    if (checkbox && checkbox.checked !== desired) {
      checkbox.checked = desired;
    }
  }

  // Expose basemap API for external use
  window.glDashboardSetBasemap = setBasemap;
  window.glDashboardBasemaps = BASEMAP_DEFS;
  window.glDashboardToggleLabels = toggleSubcatchmentLabels;
  window.glDashboardToggleSubcatchments = toggleSubcatchments;

  // Wire UI toggles
  const labelsToggle = document.getElementById('gl-subcatchment-labels-toggle');
  if (labelsToggle) {
    labelsToggle.addEventListener('change', (e) => toggleSubcatchmentLabels(e.target.checked));
  }
  const subcatchmentsToggle = document.getElementById('gl-subcatchments-toggle');
  if (subcatchmentsToggle) {
    subcatchmentsToggle.addEventListener('change', (e) => toggleSubcatchments(e.target.checked));
    // Ensure initial state matches flag
    subcatchmentsToggle.checked = subcatchmentsVisible;
  }

  // ============================================================================
  // Scenario and Comparison Mode Functions
  // ============================================================================
  
  /**
   * Build a URL path that respects the current scenario selection.
   * Uses the ?pup= query parameter to specify the scenario path.
   * @param {string} relativePath - Path relative to the run root (e.g., 'landuse/landuse.parquet')
   * @returns {string} Full URL path with scenario query parameter if applicable
   */
  function buildScenarioUrl(relativePath) {
    const baseUrl = `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/${relativePath}`;
    if (currentScenarioPath) {
      // Convert full scenario path (e.g., '_pups/omni/scenarios/mulch_15') 
      // to pup parameter (e.g., 'omni/scenarios/mulch_15')
      const pupPath = currentScenarioPath.replace(/^_pups\//, '');
      return `${baseUrl}?pup=${encodeURIComponent(pupPath)}`;
    }
    // Base scenario
    return baseUrl;
  }
  
  /**
   * Build a URL path for the base scenario (used in comparison mode).
   * @param {string} relativePath - Path relative to the run root
   * @returns {string} Full URL path to base scenario
   */
  function buildBaseUrl(relativePath) {
    return `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/${relativePath}`;
  }

  /**
   * Set the active scenario and reload data.
   * @param {string} scenarioPath - Path to scenario (e.g., '_pups/omni/scenarios/mulch_15') or empty for base
   */
  async function setScenario(scenarioPath) {
    if (scenarioPath === currentScenarioPath) return;
    
    currentScenarioPath = scenarioPath || '';
    
    // Clear cached data
    landuseSummary = null;
    soilsSummary = null;
    weppSummary = null;
    weppYearlySummary = null;
    weppYearlyMetadata = null;
    weppYearlyRanges = {};
    weppYearlyDiffRanges = {};
    weppYearlyCache = {};
    baseWeppYearlyCache = {};
    weppYearlySelectedYear = null;
    weppEventSummary = null;
    setState({
      weppYearlySummary: null,
      weppYearlyMetadata: null,
      weppYearlyRanges: {},
      weppYearlyDiffRanges: {},
      weppYearlyCache: {},
      baseWeppYearlyCache: {},
      weppYearlySelectedYear: null,
      weppYearlyLayers: [],
    });
    
    // Reload data for current layers
    await Promise.all([
      detectLanduseOverlays(),
      detectSoilsOverlays(),
      detectWeppOverlays(),
      detectWeppYearlyOverlays(),
    ]);
    
    // If comparison mode is on, we need the base data too
    if (comparisonMode && currentScenarioPath) {
      await loadBaseScenarioData();
      if (weppYearlySelectedYear != null) {
        await loadBaseWeppYearlyData(weppYearlySelectedYear);
        computeWeppYearlyDiffRanges(weppYearlySelectedYear);
      }
    }
    
    applyLayers();

    const graphEl = document.getElementById('gl-graph');
    const graphVisible = graphEl && !graphEl.classList.contains('is-collapsed');
    if (graphVisible) {
      if (rapCumulativeMode || rapLayers.some((l) => l.visible)) {
        await loadRapTimeseriesData();
      }
      const activeWeppYearly = pickActiveWeppYearlyLayer();
      if (activeWeppYearly) {
        await loadWeppYearlyTimeseriesData();
      }
    }
  }
  
  /**
   * Enable or disable comparison mode.
   * In comparison mode, shows (Base - Scenario) difference maps for supported measures.
   * @param {boolean} enabled - Whether comparison mode is enabled
   */
  async function setComparisonMode(enabled) {
    comparisonMode = !!enabled;
    if (!comparisonMode) {
      weppYearlyDiffRanges = {};
    }
    
    // If enabling comparison mode and we have a scenario selected, load base data
    if (comparisonMode && currentScenarioPath) {
      await loadBaseScenarioData();
      if (weppYearlySelectedYear != null) {
        await loadBaseWeppYearlyData(weppYearlySelectedYear);
        computeWeppYearlyDiffRanges(weppYearlySelectedYear);
      }
    }
    
    applyLayers();
    updateLayerList(); // Update layer list to show comparison indicators
    updateLegendsPanel(); // Update legends to show diverging scale
  }
  
  /**
   * Load base scenario data for comparison mode.
   */
  async function loadBaseScenarioData() {
    baseSummaryCache = {};
    comparisonDiffRanges = {};
    
    try {
      // Load base landuse data
      const landuseUrl = buildBaseUrl('query/landuse/subcatchments');
      const landuseResp = await fetch(landuseUrl);
      if (landuseResp.ok) {
        baseSummaryCache.landuse = await landuseResp.json();
      }
      
      // Load base WEPP data through query-engine
      baseSummaryCache.wepp = await fetchWeppSummary(weppStatistic, { base: true });
      
      // Compute difference ranges for proper colormap scaling
      computeComparisonDiffRanges();
      
      // Note: WEPP Event data is loaded per-date, so we'll load base event data
      // on demand when a comparison is requested for a specific date
    } catch (err) {
      console.warn('gl-dashboard: failed to load base scenario data for comparison', err);
    }
  }
  
  /**
   * Compute difference ranges for comparison mode colormap scaling.
   * For each comparable measure, finds robust min/max difference using percentiles.
   * Uses 5th/95th percentiles to avoid outlier domination while keeping 0 at midpoint.
   */
  function computeComparisonDiffRanges() {
    comparisonDiffRanges = {};
    
    /**
     * Compute robust range using percentiles.
     * @param {number[]} diffs - Array of difference values
     * @returns {{min: number, max: number}} Range object
     */
    function computeRobustRange(diffs) {
      if (!diffs.length) return null;
      diffs.sort((a, b) => a - b);
      
      // Use 5th and 95th percentiles to avoid outlier domination
      const p5Idx = Math.floor(diffs.length * 0.05);
      const p95Idx = Math.floor(diffs.length * 0.95);
      const p5 = diffs[p5Idx];
      const p95 = diffs[p95Idx];
      
      // Make range symmetric around 0 for proper diverging colormap
      // Take the larger absolute value to ensure full color range is used
      const maxAbs = Math.max(Math.abs(p5), Math.abs(p95));
      
      return { min: -maxAbs, max: maxAbs, p5, p95 };
    }
    
    // Compute landuse cover difference ranges
    if (landuseSummary && baseSummaryCache.landuse) {
      const coverModes = ['cancov', 'inrcov', 'rilcov'];
      for (const mode of coverModes) {
        const diffs = [];
        for (const topazId of Object.keys(landuseSummary)) {
          const scenarioRow = landuseSummary[topazId];
          const baseRow = baseSummaryCache.landuse[topazId];
          if (!scenarioRow || !baseRow) continue;
          const scenarioValue = Number(scenarioRow[mode]);
          const baseValue = Number(baseRow[mode]);
          if (!Number.isFinite(scenarioValue) || !Number.isFinite(baseValue)) continue;
          diffs.push(baseValue - scenarioValue);
        }
        const range = computeRobustRange(diffs);
        if (range) {
          comparisonDiffRanges[mode] = range;
        }
      }
    }
    
    // Compute WEPP measure difference ranges
    if (weppSummary && baseSummaryCache.wepp) {
      const weppModes = ['runoff_volume', 'subrunoff_volume', 'baseflow_volume', 'soil_loss', 'sediment_deposition', 'sediment_yield'];
      for (const mode of weppModes) {
        const diffs = [];
        for (const topazId of Object.keys(weppSummary)) {
          const scenarioRow = weppSummary[topazId];
          const baseRow = baseSummaryCache.wepp[topazId];
          if (!scenarioRow || !baseRow) continue;
          const scenarioValue = Number(scenarioRow[mode]);
          const baseValue = Number(baseRow[mode]);
          if (!Number.isFinite(scenarioValue) || !Number.isFinite(baseValue)) continue;
          diffs.push(baseValue - scenarioValue);
        }
        const range = computeRobustRange(diffs);
        if (range) {
          comparisonDiffRanges[mode] = range;
        }
      }
    }
    
    console.log('gl-dashboard: computed comparison diff ranges', comparisonDiffRanges);
  }
  
  /**
   * Compute WEPP Event difference ranges for the current date.
   * Uses percentile-based scaling for robustness.
   */
  function computeWeppEventDiffRanges() {
    if (!weppEventSummary || !baseSummaryCache.weppEvent) return;
    
    function computeRobustRange(diffs) {
      if (!diffs.length) return null;
      diffs.sort((a, b) => a - b);
      const p5Idx = Math.floor(diffs.length * 0.05);
      const p95Idx = Math.floor(diffs.length * 0.95);
      const p5 = diffs[p5Idx];
      const p95 = diffs[p95Idx];
      const maxAbs = Math.max(Math.abs(p5), Math.abs(p95));
      return { min: -maxAbs, max: maxAbs, p5, p95 };
    }
    
    const eventModes = ['event_P', 'event_Q', 'event_ET', 'event_peakro', 'event_tdet'];
    for (const mode of eventModes) {
      const diffs = [];
      for (const topazId of Object.keys(weppEventSummary)) {
        const scenarioRow = weppEventSummary[topazId];
        const baseRow = baseSummaryCache.weppEvent[topazId];
        if (!scenarioRow || !baseRow) continue;
        const scenarioValue = Number(scenarioRow[mode]);
        const baseValue = Number(baseRow[mode]);
        if (!Number.isFinite(scenarioValue) || !Number.isFinite(baseValue)) continue;
        diffs.push(baseValue - scenarioValue);
      }
      const range = computeRobustRange(diffs);
      if (range) {
        comparisonDiffRanges[mode] = range;
      }
    }
  }

  // Load base scenario WEPP Event data for current date
  async function loadBaseWeppEventData() {
    if (!weppEventSelectedDate || !comparisonMode) return;
    
    const [year, month, day] = weppEventSelectedDate.split('-').map(Number);
    if (!year || !month || !day) return;
    
    const activeLayer = pickActiveWeppEventLayer();
    if (!activeLayer) return;
    
    try {
      const mode = activeLayer.mode;
      const columns = ['hill.topaz_id AS topaz_id'];
      let filters;
      let baseQueryResult = {};
      
      // Use base URL for query engine (no scenario path)
      const origin = window.location.origin || `${window.location.protocol}//${window.location.host}`;
      const baseQueryUrl = `${origin}/query-engine/runs/${ctx.runid}/query`;

      if (mode === 'event_P' || mode === 'event_Q' || mode === 'event_ET') {
        const parquetPath = 'wepp/output/interchange/H.wat.parquet';
        const watColumn = mode === 'event_P' ? 'P' : mode === 'event_Q' ? 'Q' : null;
        const valueExpression =
          mode === 'event_ET'
            ? '(SUM(wat.Ep) + SUM(wat.Es) + SUM(wat.Er))'
            : `SUM(wat.${watColumn})`;
        filters = [
          { column: 'wat.year', op: '=', value: year },
          { column: 'wat.month', op: '=', value: month },
          { column: 'wat.day_of_month', op: '=', value: day },
        ];
        const dataPayload = {
          datasets: [
            { path: parquetPath, alias: 'wat' },
            { path: 'watershed/hillslopes.parquet', alias: 'hill' },
          ],
          joins: [{ left: 'wat', right: 'hill', on: 'wepp_id', type: 'inner' }],
          columns,
          aggregations: [{ sql: valueExpression, alias: 'value' }],
          filters,
          group_by: ['hill.topaz_id'],
        };
        const resp = await fetch(baseQueryUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
          body: JSON.stringify(dataPayload),
        });
        if (resp.ok) {
          const dataResult = await resp.json();
          if (dataResult && dataResult.records) {
            for (const row of dataResult.records) {
              baseQueryResult[String(row.topaz_id)] = { [mode]: row.value };
            }
          }
        }
      } else if (mode === 'event_peakro' || mode === 'event_tdet') {
        const parquetPath = 'wepp/output/interchange/H.pass.parquet';
        const passColumn = mode === 'event_peakro' ? 'peakro' : 'tdet';
        const valueExpression =
          mode === 'event_peakro' ? `MAX(pass.${passColumn})` : `SUM(pass.${passColumn})`;
        filters = [
          { column: 'pass.year', op: '=', value: year },
          { column: 'pass.month', op: '=', value: month },
          { column: 'pass.day_of_month', op: '=', value: day },
        ];
        const dataPayload = {
          datasets: [
            { path: parquetPath, alias: 'pass' },
            { path: 'watershed/hillslopes.parquet', alias: 'hill' },
          ],
          joins: [{ left: 'pass', right: 'hill', on: 'wepp_id', type: 'inner' }],
          columns,
          aggregations: [{ sql: valueExpression, alias: 'value' }],
          filters,
          group_by: ['hill.topaz_id'],
        };
        const resp = await fetch(baseQueryUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
          body: JSON.stringify(dataPayload),
        });
        if (resp.ok) {
          const dataResult = await resp.json();
          if (dataResult && dataResult.records) {
            for (const row of dataResult.records) {
              baseQueryResult[String(row.topaz_id)] = { [mode]: row.value };
            }
          }
        }
      }
      
      baseSummaryCache.weppEvent = baseQueryResult;
      
      // Compute WEPP Event difference ranges for colormap scaling
      computeWeppEventDiffRanges();
    } catch (err) {
      console.warn('gl-dashboard: failed to load base WEPP Event data for comparison', err);
    }
  }
  
  // Expose scenario API for external use
  window.glDashboardSetScenario = setScenario;
  window.glDashboardSetComparisonMode = setComparisonMode;

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

  function setGraphFocus(enabled, options = {}) {
    const { skipModeSync = false, force = false } = options;
    const focus = !!enabled;
    const currentMode = getState().graphMode || 'split';
    if (!focus && graphModeUserOverride === 'full' && !force) {
      // Preserve user-selected full mode unless explicitly forced to drop.
      return;
    }
    setValue('graphFocus', focus);
    if (glMainEl) {
      if (focus) {
        glMainEl.classList.add('graph-focus');
      } else {
        glMainEl.classList.remove('graph-focus');
      }
    }
    if (!skipModeSync) {
      const collapsed = graphPanelEl ? graphPanelEl.classList.contains('is-collapsed') : false;
      const mode = collapsed ? 'minimized' : focus ? 'full' : 'split';
      setValue('graphMode', mode);
      updateGraphModeButtons(mode);
    }
  }

  function ensureGraphExpanded() {
    if (graphPanelEl) {
      graphPanelEl.classList.remove('is-collapsed');
    }
  }

  function setGraphCollapsed(collapsed, options = {}) {
    const { focusOnExpand = true } = options;
    if (!graphPanelEl) return;
    graphPanelEl.classList.toggle('is-collapsed', collapsed);
    if (typeof window.glDashboardGraphToggled === 'function') {
      window.glDashboardGraphToggled(!graphPanelEl.classList.contains('is-collapsed'));
    }
    if (collapsed) {
      setGraphFocus(false, { force: true });
    } else {
      setGraphFocus(focusOnExpand);
      // Refresh layout after expanding
      if (timeseriesGraph && typeof timeseriesGraph._resizeCanvas === 'function') {
        timeseriesGraph._resizeCanvas();
        if (timeseriesGraph._data) {
          timeseriesGraph.render();
        }
      }
    }
  }

  function toggleGraphPanel() {
    if (!graphPanelEl) return;
    const collapsing = !graphPanelEl.classList.contains('is-collapsed');
    setGraphMode(collapsing ? 'minimized' : 'split', { source: 'user' });
  }

  function currentGraphSource() {
    try {
      const g = window.glDashboardTimeseriesGraph;
      return g && g._source ? g._source : null;
    } catch (err) {
      return null;
    }
  }

  function updateGraphModeButtons(mode) {
    if (!graphModeButtons || !graphModeButtons.length) return;
    const omniFocused = currentGraphSource() === 'omni' && getState().graphFocus;

    graphModeButtons.forEach((btn) => {
      const isActive = btn.dataset.graphMode === mode;
      btn.classList.toggle('is-active', isActive);
      btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
      const isMin = btn.dataset.graphMode === 'minimized';
      const isSplit = btn.dataset.graphMode === 'split';
      const disable = (!graphControlsEnabled && !isMin) || (omniFocused && isSplit);
      if (disable) {
        btn.classList.add('is-disabled');
        btn.setAttribute('aria-disabled', 'true');
        btn.disabled = true;
      } else {
        btn.classList.remove('is-disabled');
        btn.removeAttribute('aria-disabled');
        btn.disabled = false;
      }
    });
  }

  function setGraphControlsEnabled(enabled) {
    graphControlsEnabled = !!enabled;
    updateGraphModeButtons(getState().graphMode || 'split');
  }

  function setGraphMode(mode, options = {}) {
    const { source = 'auto' } = options;
    const validated = ['minimized', 'split', 'full'].includes(mode) ? mode : 'split';
    if (source === 'user') {
      graphModeUserOverride = validated;
    }
    const targetMode = source === 'user' ? validated : graphModeUserOverride || validated;
    const currentMode = getState().graphMode || 'split';
    if (targetMode === currentMode && source !== 'user') {
      updateGraphModeButtons(targetMode);
      return;
    }
    const st = getState();
    const graphCapable = isRapActive(st) || isWeppYearlyActive(st) || !!st.activeGraphKey;
    const effectiveMode = !graphCapable && source !== 'user' ? 'minimized' : targetMode;

    setValue('graphMode', effectiveMode);
    if (effectiveMode === 'minimized') {
      setGraphCollapsed(true);
      setGraphFocus(false, { skipModeSync: true, force: true });
    } else if (effectiveMode === 'split') {
      setGraphCollapsed(false, { focusOnExpand: false });
      setGraphFocus(false, { skipModeSync: true, force: true });
    } else if (effectiveMode === 'full') {
      setGraphCollapsed(false, { focusOnExpand: true });
      setGraphFocus(true, { skipModeSync: true, force: true });
    }
    updateGraphModeButtons(effectiveMode);
  }

  window.glDashboardToggleGraphPanel = toggleGraphPanel;
  window.glDashboardSetGraphMode = setGraphMode;

  const omniScenarios = Array.isArray(ctx.omniScenarios) ? ctx.omniScenarios : [];
  const graphScenarios = [{ name: 'Base', path: '' }].concat(
    omniScenarios.map((s) => ({ name: s.name || s.path || 'Scenario', path: s.path || '' }))
  );

  function ensureGraphLoaders() {
    if (!graphLoaders) {
      graphLoaders = graphLoadersModule.createGraphLoaders({
        graphScenarios,
        postQueryEngine: queryEngine.postQueryEngine,
        postBaseQueryEngine: queryEngine.postBaseQueryEngine,
        postQueryEngineForScenario: queryEngine.postQueryEngineForScenario,
        viridisColor,
        winterColor,
        jet2Color,
        RAP_BAND_LABELS,
      });
    }
    return graphLoaders;
  }
  const layerListEl = document.getElementById('gl-layer-list');
  const layerEmptyEl = document.getElementById('gl-layer-empty');
  const graphListEl = document.getElementById('gl-graph-list');
  const graphEmptyEl = document.getElementById('gl-graph-empty');
  const legendContentEl = document.getElementById('gl-legends-content');
  const legendEmptyEl = document.getElementById('gl-legend-empty');
  glMainEl = document.querySelector('.gl-main');
  graphPanelEl = document.getElementById('gl-graph');
  graphModeButtons = document.querySelectorAll('[data-graph-mode]');

  if (graphModeButtons && graphModeButtons.length) {
    graphModeButtons.forEach((btn) => {
      btn.addEventListener('click', () => setGraphMode(btn.dataset.graphMode, { source: 'user' }));
    });
  }

  const initialGraphMode = graphPanelEl && graphPanelEl.classList.contains('is-collapsed')
    ? 'minimized'
    : getState().graphFocus
      ? 'full'
      : 'split';
  setGraphMode(getState().graphMode || initialGraphMode, { source: 'auto' });
  setGraphControlsEnabled(true);

  // ============================================================================
  // Year Slider Controller (generic, reusable for RAP and other features)
  // ============================================================================
  const yearSlider = {
    el: document.getElementById('gl-year-slider'),
    input: document.getElementById('gl-year-slider-input'),
    valueEl: document.getElementById('gl-year-slider-value'),
    minEl: document.getElementById('gl-year-slider-min'),
    maxEl: document.getElementById('gl-year-slider-max'),
    _listeners: [],
    _visible: false,
    _minYear: 1,
    _maxYear: 100,
    _currentYear: 1,
    _hasObserved: false,
    _initialized: false,

    init(config) {
      if (!this.el || !this.input) return;
      if (this._initialized) return; // Only init once
      this._initialized = true;
      
      this._minYear = config.startYear || 1;
      this._maxYear = config.endYear || 100;
      this._hasObserved = config.hasObserved || false;
      this._currentYear = this._minYear; // Default to first year
      this._playing = false;
      this._intervalId = null;
      this._playBtn = document.getElementById('gl-year-slider-play');

      this.input.min = String(this._minYear);
      this.input.max = String(this._maxYear);
      this.input.value = String(this._currentYear);

      if (this.minEl) this.minEl.textContent = String(this._minYear);
      if (this.maxEl) this.maxEl.textContent = String(this._maxYear);
      this._updateDisplay();

      // Attach input listener
      this.input.addEventListener('input', () => {
        this._currentYear = parseInt(this.input.value, 10);
        this._updateDisplay();
        this._emit('change', this._currentYear);
      });

      // Play/pause button
      if (this._playBtn) {
        this._playBtn.addEventListener('click', () => this.toggle());
      }
    },

    _updateDisplay() {
      if (this.valueEl) {
        this.valueEl.textContent = String(this._currentYear);
      }
    },

    show() {
      if (this.el && !this._visible) {
        this.el.classList.add('is-visible');
        this._visible = true;
      }
    },

    hide() {
      if (this.el && this._visible) {
        this.el.classList.remove('is-visible');
        this._visible = false;
      }
    },

    setRange(minYear, maxYear, currentYear) {
      // Initialize if not already done
      if (!this._initialized && this.el && this.input) {
        this.init({ startYear: minYear, endYear: maxYear });
      }
      this._minYear = minYear;
      this._maxYear = maxYear;
      if (this.input) {
        this.input.min = String(minYear);
        this.input.max = String(maxYear);
      }
      if (this.minEl) this.minEl.textContent = String(minYear);
      if (this.maxEl) this.maxEl.textContent = String(maxYear);
      if (currentYear != null) {
        this._currentYear = currentYear;
        if (this.input) this.input.value = String(currentYear);
      }
      this._updateDisplay();
    },

    getValue() {
      return this._currentYear;
    },

    setValue(year) {
      this._currentYear = year;
      if (this.input) this.input.value = String(year);
      this._updateDisplay();
    },

    on(event, callback) {
      this._listeners.push({ event, callback });
    },

    off(event, callback) {
      this._listeners = this._listeners.filter(
        (l) => !(l.event === event && l.callback === callback)
      );
    },

    _emit(event, data) {
      for (const listener of this._listeners) {
        if (listener.event === event) {
          listener.callback(data);
        }
      }
    },

    play() {
      if (this._playing) return;
      this._playing = true;
      this._updatePlayButton();
      
      // Start animation interval (1 year every 3 seconds)
      this._intervalId = setInterval(() => {
        let nextYear = this._currentYear + 1;
        // Loop back to start when reaching end
        if (nextYear > this._maxYear) {
          nextYear = this._minYear;
        }
        this._currentYear = nextYear;
        if (this.input) this.input.value = String(nextYear);
        this._updateDisplay();
        this._emit('change', this._currentYear);
      }, 3000);
    },

    pause() {
      if (!this._playing) return;
      this._playing = false;
      if (this._intervalId) {
        clearInterval(this._intervalId);
        this._intervalId = null;
      }
      this._updatePlayButton();
    },

    toggle() {
      if (this._playing) {
        this.pause();
      } else {
        this.play();
      }
    },

    _updatePlayButton() {
      if (this._playBtn) {
        this._playBtn.textContent = this._playing ? '⏸' : '▶';
        this._playBtn.title = this._playing ? 'Pause' : 'Play';
      }
    },
  };

  // Initialize year slider from climate context
  const climateCtx = ctx.climate;
  if (climateCtx && climateCtx.startYear != null && climateCtx.endYear != null) {
    yearSlider.init({
      startYear: climateCtx.startYear,
      endYear: climateCtx.endYear,
      hasObserved: climateCtx.hasObserved,
    });
  }

  // Expose for external use
  window.glDashboardYearSlider = yearSlider;
  // Initial graph control sync after year slider is available
  syncGraphModeForContext();

  // ============================================================================
  // Timeseries Graph Controller (for RAP and other timeseries data)
  // ============================================================================
  function syncGraphModeForContext() {
    const st = getState();
    const rapActive = isRapActive(st);
    const yearlyActive = isWeppYearlyActive(st);
    const graphCapable = rapActive || yearlyActive || !!st.activeGraphKey;
    const contextKey = `${graphCapable ? 1 : 0}-${rapActive ? 1 : 0}-${yearlyActive ? 1 : 0}-${graphModeUserOverride || ''}-${st.activeGraphKey || ''}`;
    if (contextKey === lastGraphContextKey) {
      return;
    }
    lastGraphContextKey = contextKey;

    if (!graphCapable) {
      graphModeUserOverride = null;
      const tg = window.glDashboardTimeseriesGraph;
      if (tg && typeof tg.hide === 'function') {
        tg.hide();
      }
      if (st.activeGraphKey) {
        setValue('activeGraphKey', null);
      }
      setGraphFocus(false, { force: true, skipModeSync: true });
      setGraphControlsEnabled(false);
      setGraphMode('minimized', { source: 'auto' });
      yearSlider.hide();
      return;
    }

    // If a non-graph context (e.g., map-only) left the user in a minimized override,
    // clear it when a graph-capable RAP/WEPP Yearly context becomes active so we auto-open split.
    if (graphModeUserOverride === 'minimized' && (rapActive || yearlyActive)) {
      graphModeUserOverride = null;
    }

    setGraphControlsEnabled(true);
    const targetMode = graphModeUserOverride || 'split';
    setGraphMode(targetMode, { source: graphModeUserOverride ? 'user' : 'auto' });

    // Year slider visible only for RAP or WEPP Yearly contexts
    if (rapActive || yearlyActive) {
      yearSlider.show();
    } else {
      yearSlider.hide();
    }
  }

  async function handleGraphPanelToggle(visible) {
    if (!visible) {
      setGraphFocus(false);
      return;
    }
    if (activeGraphKey && graphFocus) {
      await activateGraphItem(activeGraphKey, { keepFocus: graphFocus });
      return;
    }
    if (rapCumulativeMode || rapLayers.some((l) => l.visible)) {
      await loadRapTimeseriesData();
    }
    const activeWeppYearly = pickActiveWeppYearlyLayer();
    if (activeWeppYearly) {
      await loadWeppYearlyTimeseriesData();
    }
  }

  const timeseriesGraph = createTimeseriesGraph({
    container: document.getElementById('gl-graph-container'),
    emptyEl: document.getElementById('gl-graph-empty'),
    tooltipEl: document.getElementById('gl-graph-tooltip'),
    panelEl: graphPanelEl,
    getGraphFocus: () => graphFocus,
    setGraphFocus,
    onPanelToggle: handleGraphPanelToggle,
  });

  timeseriesGraph.init();
  syncGraphModeForContext();

  window.glDashboardTimeseriesGraph = timeseriesGraph;
  window.glDashboardGraphToggled = handleGraphPanelToggle;

  const NLCD_COLORMAP = {
    11: '#5475A8', // Open water
    12: '#ffffff', // Perennial ice/snow
    21: '#e6d6d6', // Developed, open space
    22: '#ccb1b1', // Developed, low intensity
    23: '#ff0000', // Developed, medium intensity
    24: '#b50000', // Developed, high intensity
    31: '#d2cdc0', // Barren land
    41: '#85c77e', // Deciduous forest
    42: '#38814e', // Evergreen forest
    43: '#d4e7b0', // Mixed forest
    51: '#af963c', // Dwarf scrub
    52: '#dcca8f', // Shrub/scrub
    71: '#fde9aa', // Grassland/herbaceous
    72: '#d1d182', // Sedge/herbaceous
    73: '#a3cc51', // Lichens
    74: '#82ba9e', // Moss
    81: '#fbf65d', // Pasture/hay
    82: '#ca9146', // Cultivated crops
    90: '#c8e6f8', // Woody wetlands
    95: '#64b3d5', // Emergent herbaceous wetlands
  };
  const NLCD_LABELS = {
    11: 'Open Water',
    12: 'Perennial Ice/Snow',
    21: 'Developed, Open Space',
    22: 'Developed, Low Intensity',
    23: 'Developed, Medium Intensity',
    24: 'Developed, High Intensity',
    31: 'Barren Land',
    41: 'Deciduous Forest',
    42: 'Evergreen Forest',
    43: 'Mixed Forest',
    51: 'Dwarf Scrub',
    52: 'Shrub/Scrub',
    71: 'Grassland/Herbaceous',
    72: 'Sedge/Herbaceous',
    73: 'Lichens',
    74: 'Moss',
    81: 'Pasture/Hay',
    82: 'Cultivated Crops',
    90: 'Woody Wetlands',
    95: 'Emergent Herbaceous Wetlands',
  };
  const HEX_RGB_RE = /^#?([0-9a-f]{6})$/i;
  const soilColorCache = new Map();
  const viridisScale =
    typeof createColormap === 'function'
      ? createColormap({ colormap: 'viridis', nshades: 256, format: 'rgba' })
      : null;
  const RGBA_RE = /^rgba?\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*(?:,\s*([0-9.]+)\s*)?\)$/i;
  const GRAPH_COLORS = [
    [99, 179, 237],
    [139, 92, 246],
    [16, 185, 129],
    [244, 114, 182],
    [251, 146, 60],
    [94, 234, 212],
    [248, 113, 113],
    [125, 211, 252],
  ];

  function hslToHex(h, s, l) {
    const sat = s / 100;
    const light = l / 100;
    const a = sat * Math.min(light, 1 - light);
    const f = (n) => {
      const k = (n + h / 30) % 12;
      const color = light - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
      return Math.round(255 * color)
        .toString(16)
        .padStart(2, '0');
    };
    return `#${f(0)}${f(8)}${f(4)}`;
  }

  function soilColorForValue(value) {
    if (!Number.isFinite(value)) return null;
    if (soilColorCache.has(value)) {
      return soilColorCache.get(value);
    }
    const v = Math.abs(Math.trunc(value));
    const hue = ((v * 2654435761) >>> 0) % 360; // Knuth hash for spread
    const sat = 50 + (((v * 1013904223) >>> 0) % 30); // 50-79
    const light = 45 + (((v * 1664525) >>> 0) % 20); // 45-64
    const hex = hslToHex(hue, sat, light);
    soilColorCache.set(value, hex);
    return hex;
  }

  function resolveGeoTiffGlobal() {
    if (typeof GeoTIFF !== 'undefined' && GeoTIFF && typeof GeoTIFF.fromArrayBuffer === 'function') {
      return GeoTIFF;
    }
    if (typeof geotiff !== 'undefined') {
      if (geotiff.GeoTIFF && typeof geotiff.GeoTIFF.fromArrayBuffer === 'function') {
        return geotiff.GeoTIFF;
      }
      if (geotiff.default && typeof geotiff.default.fromArrayBuffer === 'function') {
        return geotiff.default;
      }
    }
    return null;
  }

  async function ensureGeoTiff() {
    const existing = resolveGeoTiffGlobal();
    if (existing) {
      return existing;
    }
    if (!geoTiffLoader) {
      geoTiffLoader = new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = ctx.geoTiffUrl || 'https://unpkg.com/geotiff@2.1.3/dist-browser/geotiff.js';
        script.async = true;
        script.onload = () => {
          const GT = resolveGeoTiffGlobal();
          if (GT) {
            resolve(GT);
          } else {
            reject(new Error('GeoTIFF global missing after script load'));
          }
        };
        script.onerror = () => {
          reject(new Error('GeoTIFF script failed to load'));
        };
        document.head.appendChild(script);
      });
    }
    return geoTiffLoader;
  }

  async function loadSbsImage(imgurl) {
    const imgResp = await fetch(imgurl);
    if (!imgResp.ok) {
      throw new Error(`SBS image fetch failed: ${imgResp.status}`);
    }
    const blob = await imgResp.blob();
    const bitmap = await createImageBitmap(blob);
    const canvas = document.createElement('canvas');
    canvas.width = bitmap.width;
    canvas.height = bitmap.height;
    const ctx2d = canvas.getContext('2d');
    ctx2d.drawImage(bitmap, 0, 0);
    const imgData = ctx2d.getImageData(0, 0, canvas.width, canvas.height);
    return {
      canvas,
      width: canvas.width,
      height: canvas.height,
      values: imgData.data,
      sampleMode: 'rgba',
    };
  }

  // Helper to deselect all subcatchment overlays across landuse, soils, and hillslopes
  function deselectAllSubcatchmentOverlays() {
    landuseLayers.forEach((l) => {
      l.visible = false;
      const el = document.getElementById(`layer-Landuse-${l.key}`);
      if (el) el.checked = false;
    });
    soilsLayers.forEach((l) => {
      l.visible = false;
      const el = document.getElementById(`layer-Soils-${l.key}`);
      if (el) el.checked = false;
    });
    hillslopesLayers.forEach((l) => {
      l.visible = false;
      const el = document.getElementById(`layer-Watershed-${l.key}`);
      if (el) el.checked = false;
    });
    weppLayers.forEach((l) => {
      l.visible = false;
      const el = document.getElementById(`layer-WEPP-${l.key}`);
      if (el) el.checked = false;
    });
    watarLayers.forEach((l) => {
      l.visible = false;
      const el = document.getElementById(`layer-WATAR-${l.key}`);
      if (el) el.checked = false;
    });
    weppYearlyLayers.forEach((l) => {
      l.visible = false;
      const el = document.getElementById(`layer-WEPP-Yearly-${l.key}`);
      if (el) el.checked = false;
    });
    weppEventLayers.forEach((l) => {
      l.visible = false;
      const el = document.getElementById(`layer-WEPP-Event-${l.key}`);
      if (el) el.checked = false;
    });
    rapLayers.forEach((l) => {
      l.visible = false;
      const el = document.getElementById(`layer-RAP-${l.key}`);
      if (el) el.checked = false;
    });
    // Reset RAP cumulative mode
    rapCumulativeMode = false;
    const cumulativeEl = document.getElementById('layer-RAP-cumulative');
    if (cumulativeEl) cumulativeEl.checked = false;
    // Hide year slider when no RAP layers active
    yearSlider.hide();
    // Clear active graph context when switching to map-only overlays
    setValue('activeGraphKey', null);
    setGraphFocus(false, { force: true, skipModeSync: true });
    graphModeUserOverride = null;
  }

  async function activateWeppYearlyLayer() {
    if (!weppYearlyMetadata || !weppYearlyMetadata.years || !weppYearlyMetadata.years.length) {
      yearSlider.hide();
      return;
    }
    const minYear = weppYearlyMetadata.minYear;
    const maxYear = weppYearlyMetadata.maxYear;
    if (weppYearlySelectedYear == null || weppYearlySelectedYear < minYear || weppYearlySelectedYear > maxYear) {
      weppYearlySelectedYear = maxYear;
    }
    setValue('weppYearlySelectedYear', weppYearlySelectedYear);
    yearSlider.setRange(minYear, maxYear, weppYearlySelectedYear);
    yearSlider.show();
    await refreshWeppYearlyData();
  }

  function updateGraphList() {
    if (!graphListEl) return;
    graphListEl.innerHTML = '';
    let rendered = 0;
    graphDefs.forEach((group, idx) => {
      const details = document.createElement('details');
      details.className = 'gl-layer-details';
      const hasActive = group.items.some((i) => i.key === activeGraphKey);
      details.open = idx === 0 || hasActive;

      const summary = document.createElement('summary');
      summary.className = 'gl-layer-group';
      summary.textContent = group.title || 'Graphs';
      details.appendChild(summary);

      const itemList = document.createElement('ul');
      itemList.className = 'gl-layer-items';

      group.items.forEach((item) => {
        const li = document.createElement('li');
        li.className = 'gl-layer-item';
        const input = document.createElement('input');
        input.type = 'radio';
        input.name = 'graph-selection';
        input.id = `graph-${item.key}`;
        input.checked = activeGraphKey === item.key;
        input.addEventListener('change', async () => {
          if (input.checked) {
            await activateGraphItem(item.key);
          }
        });
        const label = document.createElement('label');
        label.setAttribute('for', input.id);
        label.innerHTML = `<span class="gl-layer-name">${item.label}</span>`;
        li.appendChild(input);
        li.appendChild(label);
        itemList.appendChild(li);
        rendered += 1;
      });

      details.appendChild(itemList);
      graphListEl.appendChild(details);
    });

    if (graphEmptyEl) {
      graphEmptyEl.hidden = rendered > 0;
    }
  }

  /**
   * Render the RAP section with cumulative cover radio + band checkboxes.
   */
  function buildSubcatchmentLabelsLayer() {
    if (!subcatchmentLabelsVisible || !subcatchmentsGeoJson) {
      return [];
    }
    // Compute centroids for label placement, ensuring unique labels per topaz_id
    const labelData = [];
    const seenIds = new Set();
    const features = subcatchmentsGeoJson.features || [];
    features.forEach((feature) => {
      const props = feature.properties || {};
      const topazId = props.TopazID || props.topaz_id || props.topaz || props.id;
      if (topazId == null) return;
      // Skip if we've already added a label for this topaz_id
      const idKey = String(topazId);
      if (seenIds.has(idKey)) return;
      seenIds.add(idKey);
      // Compute centroid from geometry
      const geom = feature.geometry;
      if (!geom) return;
      let coords = [];
      if (geom.type === 'Polygon' && geom.coordinates && geom.coordinates[0]) {
        coords = geom.coordinates[0];
      } else if (geom.type === 'MultiPolygon' && geom.coordinates && geom.coordinates[0] && geom.coordinates[0][0]) {
        coords = geom.coordinates[0][0];
      }
      if (!coords.length) return;
      let sumX = 0, sumY = 0;
      coords.forEach((pt) => {
        sumX += pt[0];
        sumY += pt[1];
      });
      const centroid = [sumX / coords.length, sumY / coords.length];
      labelData.push({
        position: centroid,
        text: idKey,
      });
    });
    return [
      new deck.TextLayer({
        id: 'subcatchment-labels',
        data: labelData,
        getPosition: (d) => d.position,
        getText: (d) => d.text,
        getSize: 14,
        getColor: [255, 255, 255, 255],
        getTextAnchor: 'middle',
        getAlignmentBaseline: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        fontWeight: 'bold',
        outlineColor: [0, 0, 0, 200],
        outlineWidth: 2,
        billboard: false,
        sizeUnits: 'pixels',
        pickable: false,
      }),
    ];
  }

  function applyLayers() {
    const stack = layerUtils.buildLayerStack(baseLayer);
    if (mapController) {
      mapController.applyLayers(stack);
    }
    syncGraphModeForContext();
    updateLegendsPanel();
  }

  function hexToRgbaArray(hex, alpha = 230) {
    const parsed = HEX_RGB_RE.exec(hex || '');
    if (!parsed) return null;
    const intVal = parseInt(parsed[1], 16);
    return [(intVal >> 16) & 255, (intVal >> 8) & 255, intVal & 255, alpha];
  }

  function rgbaStringToArray(str, alphaOverride) {
    const match = RGBA_RE.exec(str || '');
    if (!match) return null;
    const r = Number(match[1]);
    const g = Number(match[2]);
    const b = Number(match[3]);
    const aRaw = match[4];
    if (![r, g, b].every(Number.isFinite)) return null;
    const a = Number.isFinite(Number(aRaw)) ? Number(aRaw) * 255 : 255;
    const finalA = Number.isFinite(alphaOverride) ? alphaOverride : a;
    return [Math.round(r), Math.round(g), Math.round(b), Math.round(finalA)];
  }

  function normalizeColorEntry(entry, alpha = 230) {
    if (!entry) return null;
    if (Array.isArray(entry)) {
      if (entry.length === 4 && entry.every((v) => Number.isFinite(Number(v)))) {
        const r = Number(entry[0]);
        const g = Number(entry[1]);
        const b = Number(entry[2]);
        let a = Number(entry[3]);
        // colormap library returns alpha in 0-1 range; convert to 0-255
        if (a <= 1) {
          a = a * 255;
        }
        // Use the passed alpha override if the original alpha was fully opaque
        if (a >= 254) {
          a = alpha;
        }
        return [r, g, b, Math.round(a)];
      }
    } else if (typeof entry === 'string') {
      const hex = hexToRgbaArray(entry, alpha);
      if (hex) return hex;
      const rgba = rgbaStringToArray(entry, alpha);
      if (rgba) return rgba;
    }
    return null;
  }

  function viridisColor(val) {
    const v = Math.min(1, Math.max(0, Number(val)));
    if (viridisScale && typeof viridisScale.map === 'function') {
      const mapped = viridisScale.map(v);
      const rgba = normalizeColorEntry(mapped, 230);
      if (rgba) return rgba;
    }
    if (viridisScale && Array.isArray(viridisScale) && viridisScale.length) {
      const idx = Math.min(viridisScale.length - 1, Math.floor(v * (viridisScale.length - 1)));
      const color = viridisScale[idx];
      const rgba = normalizeColorEntry(color, 230);
      if (rgba) return rgba;
    }
    const start = [68, 1, 84];
    const end = [253, 231, 37];
    return [
      Math.round(start[0] + (end[0] - start[0]) * v),
      Math.round(start[1] + (end[1] - start[1]) * v),
      Math.round(start[2] + (end[2] - start[2]) * v),
      230,
    ];
  }

  /**
   * Winter colormap for water-related measures (blue→green).
   * @param {number} val - Normalized value 0-1
   * @returns {Array} RGBA color array
   */
  function winterColor(val) {
    const v = Math.min(1, Math.max(0, Number(val)));
    if (winterScale && typeof winterScale.map === 'function') {
      const mapped = winterScale.map(v);
      const rgba = normalizeColorEntry(mapped, 230);
      if (rgba) return rgba;
    }
    if (winterScale && Array.isArray(winterScale) && winterScale.length) {
      const idx = Math.min(winterScale.length - 1, Math.floor(v * (winterScale.length - 1)));
      const color = winterScale[idx];
      const rgba = normalizeColorEntry(color, 230);
      if (rgba) return rgba;
    }
    // Fallback: blue (0, 0, 255) to green (0, 255, 128)
    return [
      0,
      Math.round(v * 255),
      Math.round(255 - v * 127),
      230,
    ];
  }

  /**
   * Jet2 colormap for soil-related measures (cyan→yellow→red).
   * @param {number} val - Normalized value 0-1
   * @returns {Array} RGBA color array
   */
  function jet2Color(val) {
    const v = Math.min(1, Math.max(0, Number(val)));
    if (jet2Scale && typeof jet2Scale.map === 'function') {
      const mapped = jet2Scale.map(v);
      const rgba = normalizeColorEntry(mapped, 230);
      if (rgba) return rgba;
    }
    if (jet2Scale && Array.isArray(jet2Scale) && jet2Scale.length) {
      const idx = Math.min(jet2Scale.length - 1, Math.floor(v * (jet2Scale.length - 1)));
      const color = jet2Scale[idx];
      const rgba = normalizeColorEntry(color, 230);
      if (rgba) return rgba;
    }
    // Fallback: cyan (0, 255, 255) → yellow (255, 255, 0) → red (255, 0, 0)
    if (v < 0.5) {
      const t = v * 2;
      return [
        Math.round(255 * t),
        255,
        Math.round(255 * (1 - t)),
        230,
      ];
    } else {
      const t = (v - 0.5) * 2;
      return [
        255,
        Math.round(255 * (1 - t)),
        0,
        230,
      ];
    }
  }

  /**
   * Diverging color function for comparison mode using rdbu colormap.
   * Maps normalized difference values (-1 to 1) to blue-white-red colors.
   * Negative = blue (scenario < base), Zero = white, Positive = red (scenario > base)
   * @param {number} normalizedDiff - Difference normalized to -1 to 1 range
   * @returns {Array} RGBA color array
   */
  function divergingColor(normalizedDiff) {
    // Map -1 to 1 range to 0 to 1 for colormap lookup
    // rdbu is red-white-blue, but we want blue (negative/scenario lower) to red (positive/scenario higher)
    // So we invert: low values (scenario < base) = blue, high values (scenario > base) = red
    const v = Math.min(1, Math.max(0, (normalizedDiff + 1) / 2));
    
    if (rdbuScale && typeof rdbuScale.map === 'function') {
      const mapped = rdbuScale.map(v);
      const rgba = normalizeColorEntry(mapped, 230);
      if (rgba) return rgba;
    }
    if (rdbuScale && Array.isArray(rdbuScale) && rdbuScale.length) {
      const idx = Math.min(rdbuScale.length - 1, Math.floor(v * (rdbuScale.length - 1)));
      const color = rdbuScale[idx];
      const rgba = normalizeColorEntry(color, 230);
      if (rgba) return rgba;
    }
    
    // Fallback: simple blue-white-red gradient
    if (normalizedDiff < 0) {
      // Blue to white for negative values
      const t = normalizedDiff + 1; // 0 to 1
      return [
        Math.round(33 + (255 - 33) * t),
        Math.round(102 + (255 - 102) * t),
        Math.round(172 + (255 - 172) * t),
        230
      ];
    } else {
      // White to red for positive values
      const t = normalizedDiff; // 0 to 1
      return [
        255,
        Math.round(255 - (255 - 102) * t),
        Math.round(255 - (255 - 94) * t),
        230
      ];
    }
  }

  // Normalize 0-1 diverging input to [-1, 1] for the rdbu gradient.
  function rdbuColor(normalized) {
    const clamped = Math.min(1, Math.max(0, Number(normalized)));
    return divergingColor(clamped * 2 - 1);
  }

  // RAP band labels for display
  const RAP_BAND_LABELS = {
    annual_forb_grass: 'Annual Forb & Grass',
    bare_ground: 'Bare Ground',
    litter: 'Litter',
    perennial_forb_grass: 'Perennial Forb & Grass',
    shrub: 'Shrub',
    tree: 'Tree',
  };

  const layerUtils = createLayerUtils({
    deck,
    getState,
    colorScales: {
      viridisColor,
      winterColor,
      jet2Color,
      rdbuScale: rdbuColor,
    },
    constants: {
      WATER_MEASURES,
      SOIL_MEASURES,
      NLCD_COLORMAP,
      NLCD_LABELS,
      RAP_BAND_LABELS,
      COMPARISON_MEASURES,
    },
  });

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
    setGraphFocus,
    setGraphCollapsed,
    pickActiveWeppEventLayer,
    soilColorForValue,
    constants: {
      COMPARISON_MEASURES,
      WATER_MEASURES,
      SOIL_MEASURES,
      RAP_BAND_LABELS,
      NLCD_COLORMAP,
      NLCD_LABELS,
    },
  });
  const { updateLayerList, updateLegendsPanel } = layerRenderer;
  window.glDashboardUpdateLegends = updateLegendsPanel;

  /**
   * Get comparison fill color for landuse layer.
   * Uses computed difference ranges for proper diverging colormap scaling.
   * @param {string} mode - The landuse metric (cancov, inrcov, rilcov)
   * @param {Object} scenarioRow - Row from scenario landuse summary
   * @param {Object} baseRow - Row from base landuse summary
   * @returns {Array} RGBA color array
   */
  function landuseComparisonFillColor(mode, scenarioRow, baseRow) {
    if (!scenarioRow || !baseRow) return [120, 120, 120, 120];
    
    const scenarioValue = Number(scenarioRow[mode]);
    const baseValue = Number(baseRow[mode]);
    
    if (!Number.isFinite(scenarioValue) || !Number.isFinite(baseValue)) {
      return [120, 120, 120, 120];
    }
    
    // Compute difference: Base - Scenario
    // Positive = base is higher (scenario reduced cover)
    // Negative = scenario is higher (scenario increased cover)
    const diff = baseValue - scenarioValue;
    
    // Normalize using computed difference range for this measure
    // This ensures 0 maps to 0.5 (neutral), with proper scaling for actual data range
    const range = comparisonDiffRanges[mode];
    let normalizedDiff;
    if (range && (range.min !== range.max)) {
      // Scale to -1 to 1 with 0 at the midpoint
      const maxAbs = Math.max(Math.abs(range.min), Math.abs(range.max));
      normalizedDiff = maxAbs > 0 ? diff / maxAbs : 0;
    } else {
      // Fallback: treat cover diff directly as -1 to 1
      normalizedDiff = diff;
    }
    normalizedDiff = Math.max(-1, Math.min(1, normalizedDiff));
    
    return divergingColor(normalizedDiff);
  }

  function landuseFillColor(mode, row) {
    if (!row) return [120, 120, 120, 120];
    if (mode === 'dominant') {
      const rgba = hexToRgbaArray(row.color, 220);
      return rgba || [120, 120, 120, 180];
    }
    const value = Number(row[mode]);
    if (!Number.isFinite(value)) {
      return [120, 120, 120, 120];
    }
    return viridisColor(Math.min(1, Math.max(0, value)));
  }

  function landuseValue(mode, row) {
    if (!row) return null;
    if (mode === 'dominant') {
      return row.desc || row.key || row._map || 'landuse';
    }
    const v = Number(row[mode]);
    return Number.isFinite(v) ? v : null;
  }

  function soilsFillColor(mode, row) {
    if (!row) return [120, 120, 120, 120];
    if (mode === 'dominant') {
      const rgba = hexToRgbaArray(row.color, 220);
      return rgba || [120, 120, 120, 180];
    }
    const value = Number(row[mode]);
    if (!Number.isFinite(value)) {
      return [120, 120, 120, 120];
    }
    // Normalize value ranges for viridis color scale
    let normalized = 0;
    if (mode === 'clay' || mode === 'sand' || mode === 'rock') {
      // These are percentages 0-100
      normalized = Math.min(1, Math.max(0, value / 100));
    } else if (mode === 'bd') {
      // Bulk density typically 0.5-2.0 g/cm3
      normalized = Math.min(1, Math.max(0, (value - 0.5) / 1.5));
    } else if (mode === 'soil_depth') {
      // Soil depth typically 0-2000 mm
      normalized = Math.min(1, Math.max(0, value / 2000));
    } else {
      normalized = Math.min(1, Math.max(0, value));
    }
    return viridisColor(normalized);
  }

  function soilsValue(mode, row) {
    if (!row) return null;
    if (mode === 'dominant') {
      return row.desc || row.simple_texture || row.mukey || 'soil';
    }
    const v = Number(row[mode]);
    return Number.isFinite(v) ? v : null;
  }

  function buildSoilsLayers() {
    const activeLayers = soilsLayers
      .filter((l) => l.visible && subcatchmentsGeoJson && soilsSummary)
      .map((overlay) => {
        return new deck.GeoJsonLayer({
          id: `soils-${overlay.key}`,
          data: subcatchmentsGeoJson,
          pickable: true,
          stroked: false,
          filled: true,
          opacity: 0.8,
          getFillColor: (f) => {
            const props = f && f.properties;
            const topaz =
              props &&
              (props.TopazID ||
                props.topaz_id ||
                props.topaz ||
                props.id ||
                props.WeppID ||
                props.wepp_id);
            const row = topaz != null ? soilsSummary[String(topaz)] : null;
            return soilsFillColor(overlay.mode, row);
          },
        });
      });
    return activeLayers;
  }

  // Hillslopes value ranges for normalization (approximate)
  const HILLSLOPES_RANGES = {
    slope_scalar: { min: 0, max: 1 },     // 0-100% slope as decimal
    length: { min: 0, max: 1000 },         // meters
    aspect: { min: 0, max: 360 },          // degrees
  };

  function hillslopesFillColor(mode, row) {
    if (!row) return [128, 128, 128, 200];
    const value = Number(row[mode]);
    if (!Number.isFinite(value)) return [128, 128, 128, 200];

    // For aspect, use a circular colormap (HSL hue)
    if (mode === 'aspect') {
      // Convert aspect degrees to hue (0-360)
      const hue = value % 360;
      // Simple HSL to RGB conversion for hue wheel
      const h = hue / 60;
      const c = 200; // chroma
      const x = c * (1 - Math.abs((h % 2) - 1));
      let r, g, b;
      if (h < 1) { r = c; g = x; b = 0; }
      else if (h < 2) { r = x; g = c; b = 0; }
      else if (h < 3) { r = 0; g = c; b = x; }
      else if (h < 4) { r = 0; g = x; b = c; }
      else if (h < 5) { r = x; g = 0; b = c; }
      else { r = c; g = 0; b = x; }
      return [Math.round(r + 55), Math.round(g + 55), Math.round(b + 55), 200];
    }

    // For slope and length, use viridis scale
    const range = HILLSLOPES_RANGES[mode] || { min: 0, max: 1 };
    const normalized = Math.min(1, Math.max(0, (value - range.min) / (range.max - range.min)));
    return viridisColor(normalized);
  }

  function hillslopesValue(mode, row) {
    if (!row) return null;
    const v = Number(row[mode]);
    return Number.isFinite(v) ? v : null;
  }

  function buildHillslopesLayers() {
    const activeLayers = hillslopesLayers
      .filter((l) => l.visible && subcatchmentsGeoJson && hillslopesSummary)
      .map((overlay) => {
        return new deck.GeoJsonLayer({
          id: `hillslopes-${overlay.key}`,
          data: subcatchmentsGeoJson,
          pickable: true,
          stroked: false,
          filled: true,
          opacity: 0.8,
          getFillColor: (f) => {
            const props = f && f.properties;
            const topaz =
              props &&
              (props.TopazID ||
                props.topaz_id ||
                props.topaz ||
                props.id ||
                props.WeppID ||
                props.wepp_id);
            const row = topaz != null ? hillslopesSummary[String(topaz)] : null;
            return hillslopesFillColor(overlay.mode, row);
          },
        });
      });
    return activeLayers;
  }

  function pickActiveHillslopesLayer() {
    for (let i = hillslopesLayers.length - 1; i >= 0; i--) {
      const layer = hillslopesLayers[i];
      if (layer.visible) {
        return layer;
      }
    }
    return null;
  }

  function watarFillColor(mode, row) {
    if (!row) return [128, 128, 128, 200];
    const value = Number(row[mode]);
    if (!Number.isFinite(value)) return [128, 128, 128, 200];
    const range = watarRanges[mode] || { min: 0, max: 1 };
    const normalized = Math.min(1, Math.max(0, (value - range.min) / (range.max - range.min)));
    return jet2Color(normalized);
  }

  function watarValue(mode, row) {
    if (!row) return null;
    const v = Number(row[mode]);
    return Number.isFinite(v) ? v : null;
  }

  function buildWatarLayers() {
    const activeLayers = watarLayers
      .filter((l) => l.visible && subcatchmentsGeoJson && watarSummary)
      .map((overlay) => {
        return new deck.GeoJsonLayer({
          id: `watar-${overlay.key}`,
          data: subcatchmentsGeoJson,
          pickable: true,
          stroked: false,
          filled: true,
          opacity: 0.8,
          getFillColor: (f) => {
            const props = f && f.properties;
            const topaz =
              props &&
              (props.TopazID ||
                props.topaz_id ||
                props.topaz ||
                props.id ||
                props.WeppID ||
                props.wepp_id);
            const row = topaz != null ? watarSummary[String(topaz)] : null;
            return watarFillColor(overlay.mode, row);
          },
        });
      });
    return activeLayers;
  }

  function pickActiveWatarLayer() {
    for (let i = watarLayers.length - 1; i >= 0; i--) {
      const layer = watarLayers[i];
      if (layer.visible) {
        return layer;
      }
    }
    return null;
  }

  const WEPP_YEARLY_PATH = 'wepp/output/interchange/loss_pw0.all_years.hill.parquet';
  const WEPP_LOSS_PATH = 'wepp/output/interchange/loss_pw0.hill.parquet';
  const WATAR_PATH = 'ash/post/hillslope_annuals.parquet';

  // WEPP loss ranges computed dynamically from weppSummary data
  let watarRanges = {};
  let weppRanges = {};
  let weppYearlyRanges = {};

  function buildWeppAggregations(statistic) {
    const stat = (statistic || 'mean').toLowerCase();
    const measureMap = {
      runoff_volume: '"Runoff Volume"',
      subrunoff_volume: '"Subrunoff Volume"',
      baseflow_volume: '"Baseflow Volume"',
      soil_loss: '"Soil Loss"',
      sediment_deposition: '"Sediment Deposition"',
      sediment_yield: '"Sediment Yield"',
    };

    function statExpression(column) {
      if (stat === 'p90') return `quantile(loss.${column}, 0.9)`;
      if (stat === 'sd') return `stddev_samp(loss.${column})`;
      if (stat === 'cv') {
        return `CASE WHEN avg(loss.${column}) = 0 THEN NULL ELSE stddev_samp(loss.${column}) / avg(loss.${column}) * 100 END`;
      }
      return `avg(loss.${column})`;
    }

    return Object.entries(measureMap).map(([alias, column]) => ({
      sql: statExpression(column),
      alias,
    }));
  }

  async function fetchWeppSummary(statistic, { base = false } = {}) {
    const aggregations = buildWeppAggregations(statistic);
    const columns = ['hill.topaz_id AS topaz_id', 'hill.wepp_id AS wepp_id'];
    const joins = [{ left: 'loss', right: 'hill', on: 'wepp_id', type: 'inner' }];
    const datasetPaths = [WEPP_YEARLY_PATH, WEPP_LOSS_PATH];

    async function runWithDataset(path) {
      const payload = {
        datasets: [
          { path, alias: 'loss' },
          { path: 'watershed/hillslopes.parquet', alias: 'hill' },
        ],
        joins,
        columns,
        group_by: ['hill.topaz_id', 'hill.wepp_id'],
        aggregations,
      };
      const result = base ? await postBaseQueryEngine(payload) : await postQueryEngine(payload);
      if (result && result.records) {
        const summary = {};
        for (const row of result.records) {
          const topazId = row.topaz_id;
          if (topazId != null) {
            summary[String(topazId)] = row;
          }
        }
        return summary;
      }
      return null;
    }

    for (const path of datasetPaths) {
      const summary = await runWithDataset(path);
      if (summary !== null) {
        return summary;
      }
    }
    return null;
  }

  async function refreshWeppStatisticData() {
    // If no WEPP overlays are active, just keep the stat selection for later.
    const hasActiveWepp = weppLayers.some((l) => l.visible);
    if (!hasActiveWepp) {
      return;
    }

    try {
      weppSummary = await fetchWeppSummary(weppStatistic);
      if (weppSummary) {
        computeWeppRanges();
      }

      if (comparisonMode && currentScenarioPath) {
        baseSummaryCache.wepp = await fetchWeppSummary(weppStatistic, { base: true });
        if (baseSummaryCache.wepp) {
          computeComparisonDiffRanges();
        }
      }

      applyLayers();
      updateLegendsPanel();
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to refresh WEPP data for statistic', err);
    }
  }

  function computeWeppRanges() {
    if (!weppSummary) return;
    const modes = ['runoff_volume', 'subrunoff_volume', 'baseflow_volume', 'soil_loss', 'sediment_deposition', 'sediment_yield'];
    weppRanges = {};
    for (const mode of modes) {
      let min = Infinity;
      let max = -Infinity;
      for (const key of Object.keys(weppSummary)) {
        const row = weppSummary[key];
        const v = Number(row[mode]);
        if (Number.isFinite(v)) {
          if (v < min) min = v;
          if (v > max) max = v;
        }
      }
      // Handle edge cases
      if (!Number.isFinite(min)) min = 0;
      if (!Number.isFinite(max)) max = 1;
      if (max <= min) max = min + 1;
      weppRanges[mode] = { min, max };
    }
  }

  function weppFillColor(mode, row) {
    if (!row) return [128, 128, 128, 200];
    const value = Number(row[mode]);
    if (!Number.isFinite(value)) return [128, 128, 128, 200];

    const range = weppRanges[mode] || { min: 0, max: 100 };
    const normalized = Math.min(1, Math.max(0, (value - range.min) / (range.max - range.min)));
    
    // Use winter colormap for water-related measures, jet2 for soil-related measures
    if (WATER_MEASURES.includes(mode)) {
      return winterColor(normalized);
    } else if (SOIL_MEASURES.includes(mode)) {
      return jet2Color(normalized);
    }
    return viridisColor(normalized);
  }

  /**
   * Get comparison fill color for WEPP layer.
   * Uses computed difference ranges for proper diverging colormap scaling.
   * @param {string} mode - The WEPP metric
   * @param {Object} scenarioRow - Row from scenario WEPP summary
   * @param {Object} baseRow - Row from base WEPP summary  
   * @returns {Array} RGBA color array
   */
  function weppComparisonFillColor(mode, scenarioRow, baseRow) {
    if (!scenarioRow || !baseRow) return [128, 128, 128, 200];
    
    const scenarioValue = Number(scenarioRow[mode]);
    const baseValue = Number(baseRow[mode]);
    
    if (!Number.isFinite(scenarioValue) || !Number.isFinite(baseValue)) {
      return [128, 128, 128, 200];
    }
    
    // Compute difference: Base - Scenario
    // Positive = base is higher (scenario reduced runoff/erosion - improvement)
    // Negative = scenario is higher (scenario increased runoff/erosion - worse)
    const diff = baseValue - scenarioValue;
    
    // Normalize using computed difference range for this measure
    // This ensures 0 maps to 0.5 (neutral), with proper scaling for actual data range
    const range = comparisonDiffRanges[mode];
    let normalizedDiff;
    if (range && (range.min !== range.max)) {
      // Scale to -1 to 1 with 0 at the midpoint
      const maxAbs = Math.max(Math.abs(range.min), Math.abs(range.max));
      normalizedDiff = maxAbs > 0 ? diff / maxAbs : 0;
    } else {
      // Fallback: use WEPP ranges
      const fallbackRange = weppRanges[mode] || { min: 0, max: 100 };
      const maxDiff = fallbackRange.max - fallbackRange.min;
      normalizedDiff = maxDiff > 0 ? diff / maxDiff : 0;
    }
    normalizedDiff = Math.max(-1, Math.min(1, normalizedDiff));
    
    return divergingColor(normalizedDiff);
  }

  function weppValue(mode, row) {
    if (!row) return null;
    const v = Number(row[mode]);
    return Number.isFinite(v) ? v : null;
  }

  function buildWeppLayers() {
    const activeLayers = weppLayers
      .filter((l) => l.visible && subcatchmentsGeoJson && weppSummary)
      .map((overlay) => {
        // Check if comparison mode is active and this is a comparable measure
        const useComparison = comparisonMode && 
                             currentScenarioPath && 
                             COMPARISON_MEASURES.includes(overlay.mode) &&
                             baseSummaryCache.wepp;
        
        return new deck.GeoJsonLayer({
          id: `wepp-${overlay.key}${useComparison ? '-diff' : ''}`,
          data: subcatchmentsGeoJson,
          pickable: true,
          stroked: false,
          filled: true,
          opacity: 0.8,
          getFillColor: (f) => {
            const props = f && f.properties;
            const topaz =
              props &&
              (props.TopazID ||
                props.topaz_id ||
                props.topaz ||
                props.id ||
                props.WeppID ||
                props.wepp_id);
            const row = topaz != null ? weppSummary[String(topaz)] : null;
            
            if (useComparison) {
              const baseRow = topaz != null ? baseSummaryCache.wepp[String(topaz)] : null;
              return weppComparisonFillColor(overlay.mode, row, baseRow);
            }
            return weppFillColor(overlay.mode, row);
          },
          updateTriggers: {
            getFillColor: [comparisonMode, currentScenarioPath, comparisonDiffRanges[overlay.mode], weppStatistic],
          },
        });
      });
    return activeLayers;
  }

  function pickActiveWeppLayer() {
    for (let i = weppLayers.length - 1; i >= 0; i--) {
      const layer = weppLayers[i];
      if (layer.visible) {
        return layer;
      }
    }
    return null;
  }

  function computeWeppYearlyRanges() {
    if (!weppYearlySummary) return;
    const modes = ['runoff_volume', 'subrunoff_volume', 'baseflow_volume', 'soil_loss', 'sediment_deposition', 'sediment_yield'];
    weppYearlyRanges = {};
    for (const mode of modes) {
      let min = Infinity;
      let max = -Infinity;
      for (const key of Object.keys(weppYearlySummary)) {
        const row = weppYearlySummary[key];
        const v = Number(row[mode]);
        if (Number.isFinite(v)) {
          if (v < min) min = v;
          if (v > max) max = v;
        }
      }
      if (!Number.isFinite(min)) min = 0;
      if (!Number.isFinite(max)) max = 1;
      if (max <= min) max = min + 1;
      weppYearlyRanges[mode] = { min, max };
    }
  }

  function weppYearlyFillColor(mode, row) {
    if (!row) return [128, 128, 128, 200];
    const value = Number(row[mode]);
    if (!Number.isFinite(value)) return [128, 128, 128, 200];

    const range = weppYearlyRanges[mode] || { min: 0, max: 100 };
    const normalized = Math.min(1, Math.max(0, (value - range.min) / (range.max - range.min)));

    if (WATER_MEASURES.includes(mode)) {
      return winterColor(normalized);
    } else if (SOIL_MEASURES.includes(mode)) {
      return jet2Color(normalized);
    }
    return viridisColor(normalized);
  }

  function weppYearlyComparisonFillColor(mode, scenarioRow, baseRow) {
    if (!scenarioRow || !baseRow) return [128, 128, 128, 200];
    const scenarioValue = Number(scenarioRow[mode]);
    const baseValue = Number(baseRow[mode]);
    if (!Number.isFinite(scenarioValue) || !Number.isFinite(baseValue)) {
      return [128, 128, 128, 200];
    }
    const diff = baseValue - scenarioValue;
    const range = weppYearlyDiffRanges[mode];
    let normalizedDiff;
    if (range && range.min !== range.max) {
      const maxAbs = Math.max(Math.abs(range.min), Math.abs(range.max));
      normalizedDiff = maxAbs > 0 ? diff / maxAbs : 0;
    } else {
      const fallbackRange = weppYearlyRanges[mode] || { min: 0, max: 100 };
      const maxDiff = fallbackRange.max - fallbackRange.min;
      normalizedDiff = maxDiff > 0 ? diff / maxDiff : 0;
    }
    normalizedDiff = Math.max(-1, Math.min(1, normalizedDiff));
    return divergingColor(normalizedDiff);
  }

  function weppYearlyValue(mode, row) {
    if (!row) return null;
    const v = Number(row[mode]);
    return Number.isFinite(v) ? v : null;
  }

  function buildWeppYearlyLayers() {
    const activeLayers = weppYearlyLayers
      .filter((l) => l.visible && subcatchmentsGeoJson && weppYearlySummary)
      .map((overlay) => {
        const baseSummary = baseWeppYearlyCache[weppYearlySelectedYear];
        const useComparison =
          comparisonMode &&
          currentScenarioPath &&
          COMPARISON_MEASURES.includes(overlay.mode) &&
          baseSummary;

        return new deck.GeoJsonLayer({
          id: `wepp-yearly-${overlay.key}-${weppYearlySelectedYear}${useComparison ? '-diff' : ''}`,
          data: subcatchmentsGeoJson,
          pickable: true,
          stroked: true,
          filled: true,
          opacity: 0.8,
          getFillColor: (f) => {
            const props = f && f.properties;
            const topaz =
              props &&
              (props.TopazID ||
                props.topaz_id ||
                props.topaz ||
                props.id ||
                props.WeppID ||
                props.wepp_id);
            const row = topaz != null ? weppYearlySummary[String(topaz)] : null;
            if (useComparison) {
              const baseRow = topaz != null ? baseSummary[String(topaz)] : null;
              return weppYearlyComparisonFillColor(overlay.mode, row, baseRow);
            }
            return weppYearlyFillColor(overlay.mode, row);
          },
          getLineColor: (f) => {
            const props = f && f.properties;
            const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
            if (graphHighlightedTopazId && String(topaz) === String(graphHighlightedTopazId)) {
              return [255, 200, 0, 255];
            }
            return [0, 0, 0, 0];
          },
          getLineWidth: (f) => {
            const props = f && f.properties;
            const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
            if (graphHighlightedTopazId && String(topaz) === String(graphHighlightedTopazId)) {
              return 3;
            }
            return 0;
          },
          lineWidthUnits: 'pixels',
          updateTriggers: {
            getFillColor: [weppYearlySelectedYear, comparisonMode, currentScenarioPath, weppYearlyDiffRanges[overlay.mode]],
            getLineColor: [graphHighlightedTopazId],
            getLineWidth: [graphHighlightedTopazId],
          },
        });
      });
    return activeLayers;
  }

  function pickActiveWeppYearlyLayer() {
    for (let i = weppYearlyLayers.length - 1; i >= 0; i--) {
      const layer = weppYearlyLayers[i];
      if (layer.visible) {
        return layer;
      }
    }
    return null;
  }

  function computeWeppYearlyDiffRanges(year) {
    weppYearlyDiffRanges = {};
    if (!weppYearlySummary || !baseWeppYearlyCache[year]) return;
    const baseSummary = baseWeppYearlyCache[year];
    const modes = ['runoff_volume', 'subrunoff_volume', 'baseflow_volume', 'soil_loss', 'sediment_deposition', 'sediment_yield'];

    function computeRobustRange(diffs) {
      if (!diffs.length) return null;
      diffs.sort((a, b) => a - b);
      const p5Idx = Math.floor(diffs.length * 0.05);
      const p95Idx = Math.floor(diffs.length * 0.95);
      const p5 = diffs[p5Idx];
      const p95 = diffs[p95Idx];
      const maxAbs = Math.max(Math.abs(p5), Math.abs(p95));
      return { min: -maxAbs, max: maxAbs, p5, p95 };
    }

    for (const mode of modes) {
      const diffs = [];
      for (const topazId of Object.keys(weppYearlySummary)) {
        const scenarioRow = weppYearlySummary[topazId];
        const baseRow = baseSummary[topazId];
        if (!scenarioRow || !baseRow) continue;
        const scenarioValue = Number(scenarioRow[mode]);
        const baseValue = Number(baseRow[mode]);
        if (!Number.isFinite(scenarioValue) || !Number.isFinite(baseValue)) continue;
        diffs.push(baseValue - scenarioValue);
      }
      const range = computeRobustRange(diffs);
      if (range) {
        weppYearlyDiffRanges[mode] = range;
      }
    }
  }

  async function loadBaseWeppYearlyData(year) {
    if (!Number.isFinite(year)) return null;
    if (baseWeppYearlyCache[year]) {
      return baseWeppYearlyCache[year];
    }
    const columns = [
      'hill.topaz_id AS topaz_id',
      'loss."Runoff Volume" AS runoff_volume',
      'loss."Subrunoff Volume" AS subrunoff_volume',
      'loss."Baseflow Volume" AS baseflow_volume',
      'loss."Soil Loss" AS soil_loss',
      'loss."Sediment Deposition" AS sediment_deposition',
      'loss."Sediment Yield" AS sediment_yield',
    ];
    const payload = {
      datasets: [
        { path: WEPP_YEARLY_PATH, alias: 'loss' },
        { path: 'watershed/hillslopes.parquet', alias: 'hill' },
      ],
      joins: [{ left: 'loss', right: 'hill', on: 'wepp_id', type: 'inner' }],
      columns,
      filters: [{ column: 'loss.year', op: '=', value: year }],
    };
    try {
      const result = await postBaseQueryEngine(payload);
      if (result && result.records) {
        const summary = {};
        for (const row of result.records) {
          const topazId = row.topaz_id;
          if (topazId != null) {
            summary[String(topazId)] = row;
          }
        }
        baseWeppYearlyCache[year] = summary;
        setState({ baseWeppYearlyCache: { ...baseWeppYearlyCache } });
        return summary;
      }
    } catch (err) {
      console.warn('gl-dashboard: failed to load base WEPP yearly data', err);
    }
    return null;
  }

  async function refreshWeppYearlyData() {
    const year = weppYearlySelectedYear;
    if (!Number.isFinite(year)) return;

    if (weppYearlyCache[year]) {
      weppYearlySummary = weppYearlyCache[year];
    } else {
      weppYearlySummary = null;
      const columns = [
        'hill.topaz_id AS topaz_id',
        'loss."Runoff Volume" AS runoff_volume',
        'loss."Subrunoff Volume" AS subrunoff_volume',
        'loss."Baseflow Volume" AS baseflow_volume',
        'loss."Soil Loss" AS soil_loss',
        'loss."Sediment Deposition" AS sediment_deposition',
        'loss."Sediment Yield" AS sediment_yield',
      ];
      const payload = {
        datasets: [
          { path: WEPP_YEARLY_PATH, alias: 'loss' },
          { path: 'watershed/hillslopes.parquet', alias: 'hill' },
        ],
        joins: [{ left: 'loss', right: 'hill', on: 'wepp_id', type: 'inner' }],
        columns,
        filters: [{ column: 'loss.year', op: '=', value: year }],
      };
      try {
        const result = await postQueryEngine(payload);
        if (result && result.records) {
          weppYearlySummary = {};
          for (const row of result.records) {
            const topazId = row.topaz_id;
            if (topazId != null) {
              weppYearlySummary[String(topazId)] = row;
            }
          }
          weppYearlyCache[year] = weppYearlySummary;
        }
      } catch (err) {
        console.warn('gl-dashboard: failed to refresh WEPP yearly data', err);
        weppYearlySummary = null;
      }
    }

    if (weppYearlySummary) {
      computeWeppYearlyRanges();
    }

    if (comparisonMode && currentScenarioPath) {
      await loadBaseWeppYearlyData(year);
      computeWeppYearlyDiffRanges(year);
    } else {
      weppYearlyDiffRanges = {};
    }

    setState({
      weppYearlySummary: weppYearlySummary || null,
      weppYearlyRanges: { ...weppYearlyRanges },
      weppYearlyDiffRanges: { ...weppYearlyDiffRanges },
      baseWeppYearlyCache: { ...baseWeppYearlyCache },
      weppYearlySelectedYear,
    });

    // Re-sync graph controls now that WEPP Yearly data is available so the graph panel
    // opens in split mode instead of staying minimized after the initial toggle.
    syncGraphModeForContext();
  }

  // WEPP Event ranges computed dynamically from weppEventSummary data
  let weppEventRanges = {};

  function computeWeppEventRanges() {
    if (!weppEventSummary) return;
    const modes = ['event_P', 'event_Q', 'event_ET', 'event_peakro', 'event_tdet'];
    weppEventRanges = {};
    for (const mode of modes) {
      let min = Infinity;
      let max = -Infinity;
      for (const key of Object.keys(weppEventSummary)) {
        const row = weppEventSummary[key];
        const v = Number(row[mode]);
        if (Number.isFinite(v)) {
          if (v < min) min = v;
          if (v > max) max = v;
        }
      }
      // Handle edge cases
      if (!Number.isFinite(min)) min = 0;
      if (!Number.isFinite(max)) max = 1;
      if (max <= min) max = min + 0.001;
      weppEventRanges[mode] = { min, max };
    }
  }

  /**
   * Get comparison fill color for WEPP Event layer.
   * @param {string} mode - The WEPP Event metric
   * @param {Object} scenarioRow - Row from scenario WEPP Event summary
   * @param {Object} baseRow - Row from base WEPP Event summary  
   * @returns {Array} RGBA color array
   */
  function weppEventComparisonFillColor(mode, scenarioRow, baseRow) {
    if (!scenarioRow || !baseRow) return [128, 128, 128, 200];
    
    const scenarioValue = Number(scenarioRow[mode]);
    const baseValue = Number(baseRow[mode]);
    
    if (!Number.isFinite(scenarioValue) || !Number.isFinite(baseValue)) {
      return [128, 128, 128, 200];
    }
    
    const diff = baseValue - scenarioValue;
    
    // Normalize using computed difference range for this measure
    // This ensures 0 maps to 0.5 (neutral), with proper scaling for actual data range
    const range = comparisonDiffRanges[mode];
    let normalizedDiff;
    if (range && (range.min !== range.max)) {
      // Scale to -1 to 1 with 0 at the midpoint
      const maxAbs = Math.max(Math.abs(range.min), Math.abs(range.max));
      normalizedDiff = maxAbs > 0 ? diff / maxAbs : 0;
    } else {
      // Fallback: use WEPP Event ranges
      const fallbackRange = weppEventRanges[mode] || { min: 0, max: 100 };
      const maxDiff = fallbackRange.max - fallbackRange.min;
      normalizedDiff = maxDiff > 0 ? diff / maxDiff : 0;
    }
    normalizedDiff = Math.max(-1, Math.min(1, normalizedDiff));
    
    return divergingColor(normalizedDiff);
  }

  function weppEventFillColor(mode, row) {
    if (!row) return [128, 128, 128, 200];
    const value = Number(row[mode]);
    if (!Number.isFinite(value)) return [128, 128, 128, 200];

    const range = weppEventRanges[mode] || { min: 0, max: 100 };
    const normalized = Math.min(1, Math.max(0, (value - range.min) / (range.max - range.min)));
    
    // Use winter colormap for water-related measures, jet2 for soil-related measures
    if (WATER_MEASURES.includes(mode)) {
      return winterColor(normalized);
    } else if (SOIL_MEASURES.includes(mode)) {
      return jet2Color(normalized);
    }
    return viridisColor(normalized);
  }

  function weppEventValue(mode, row) {
    if (!row) return null;
    const v = Number(row[mode]);
    return Number.isFinite(v) ? v : null;
  }

  function buildWeppEventLayers() {
    const activeLayers = weppEventLayers
      .filter((l) => l.visible && subcatchmentsGeoJson && weppEventSummary)
      .map((overlay) => {
        // Check if this is a comparison-capable measure
        const isComparisonMeasure = COMPARISON_MEASURES.includes(overlay.mode);
        const useComparison = comparisonMode && isComparisonMeasure && baseSummaryCache.weppEvent;

        return new deck.GeoJsonLayer({
          id: `wepp-event-${overlay.key}-${weppEventSelectedDate}${comparisonMode ? '-cmp' : ''}`,
          data: subcatchmentsGeoJson,
          pickable: true,
          stroked: false,
          filled: true,
          opacity: 0.8,
          getFillColor: (f) => {
            const props = f && f.properties;
            const topaz =
              props &&
              (props.TopazID ||
                props.topaz_id ||
                props.topaz ||
                props.id ||
                props.WeppID ||
                props.wepp_id);
            const row = topaz != null ? weppEventSummary[String(topaz)] : null;
            if (useComparison) {
              const baseRow = topaz != null ? baseSummaryCache.weppEvent[String(topaz)] : null;
              return weppEventComparisonFillColor(overlay.mode, baseRow, row);
            }
            return weppEventFillColor(overlay.mode, row);
          },
          updateTriggers: {
            getFillColor: [weppEventSelectedDate, comparisonMode, baseSummaryCache.weppEvent, comparisonDiffRanges[overlay.mode]],
          },
        });
      });
    return activeLayers;
  }

  function pickActiveWeppEventLayer() {
    for (let i = weppEventLayers.length - 1; i >= 0; i--) {
      const layer = weppEventLayers[i];
      if (layer.visible) {
        return layer;
      }
    }
    return null;
  }

  async function refreshWeppEventData() {
    if (!weppEventSelectedDate) return;
    const activeLayer = pickActiveWeppEventLayer();
    if (!activeLayer) return;

    // Parse the date to get year, month, day
    const [year, month, day] = weppEventSelectedDate.split('-').map(Number);
    if (!year || !month || !day) return;

    try {
      // Reset cached summary so stale values are not reused on failure
      weppEventSummary = {};
      weppEventRanges = {};

      // Determine which parquet file and column to query based on the mode
      const mode = activeLayer.mode;
      const columns = ['hill.topaz_id AS topaz_id'];
      let filters;

      if (mode === 'event_P' || mode === 'event_Q' || mode === 'event_ET') {
        // H.wat.parquet - aggregate OFEs by hillslope (topaz_id) via hillslopes mapping
        const parquetPath = 'wepp/output/interchange/H.wat.parquet';
        const watColumn = mode === 'event_P' ? 'P' : mode === 'event_Q' ? 'Q' : null;
        const valueExpression =
          mode === 'event_ET'
            ? '(SUM(wat.Ep) + SUM(wat.Es) + SUM(wat.Er))'
            : `SUM(wat.${watColumn})`;
        filters = [
          { column: 'wat.year', op: '=', value: year },
          { column: 'wat.month', op: '=', value: month },
          { column: 'wat.day_of_month', op: '=', value: day },
        ];
        const dataPayload = {
          datasets: [
            { path: parquetPath, alias: 'wat' },
            { path: 'watershed/hillslopes.parquet', alias: 'hill' },
          ],
          joins: [{ left: 'wat', right: 'hill', on: 'wepp_id', type: 'inner' }],
          columns,
          aggregations: [{ sql: valueExpression, alias: 'value' }],
          filters,
          group_by: ['hill.topaz_id'],
        };
        const dataResult = await postQueryEngine(dataPayload);
        if (dataResult && dataResult.records) {
          weppEventSummary = {};
          for (const row of dataResult.records) {
            weppEventSummary[String(row.topaz_id)] = { [mode]: row.value };
          }
          computeWeppEventRanges();
        }
      } else if (mode === 'event_peakro' || mode === 'event_tdet') {
        // H.pass.parquet
        const parquetPath = 'wepp/output/interchange/H.pass.parquet';
        const passColumn = mode === 'event_peakro' ? 'peakro' : 'tdet';
        const valueExpression =
          mode === 'event_peakro' ? `MAX(pass.${passColumn})` : `SUM(pass.${passColumn})`;
        filters = [
          { column: 'pass.year', op: '=', value: year },
          { column: 'pass.month', op: '=', value: month },
          { column: 'pass.day_of_month', op: '=', value: day },
        ];
        const dataPayload = {
          datasets: [
            { path: parquetPath, alias: 'pass' },
            { path: 'watershed/hillslopes.parquet', alias: 'hill' },
          ],
          joins: [{ left: 'pass', right: 'hill', on: 'wepp_id', type: 'inner' }],
          columns,
          aggregations: [{ sql: valueExpression, alias: 'value' }],
          filters,
          group_by: ['hill.topaz_id'],
        };
        const dataResult = await postQueryEngine(dataPayload);
        if (dataResult && dataResult.records) {
          weppEventSummary = {};
          for (const row of dataResult.records) {
            weppEventSummary[String(row.topaz_id)] = { [mode]: row.value };
          }
          computeWeppEventRanges();
        }
      }
      
      // Load base scenario data for comparison mode
      if (comparisonMode && currentScenarioPath) {
        await loadBaseWeppEventData();
      }
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to refresh WEPP Event data', err);
    }
  }

  function rapFillColor(row) {
    if (!row) return [128, 128, 128, 200];
    const value = Number(row);
    if (!Number.isFinite(value)) return [128, 128, 128, 200];
    // RAP values are percentages 0-100
    const normalized = Math.min(1, Math.max(0, value / 100));
    return viridisColor(normalized);
  }

  function rapValue(row) {
    if (row == null) return null;
    const v = Number(row);
    return Number.isFinite(v) ? v : null;
  }

  function buildRapLayers() {
    // In cumulative mode, render a single layer from the cumulative summary
    if (rapCumulativeMode && subcatchmentsGeoJson && rapSummary) {
      // Create a unique ID based on selected bands and year to force re-render
      const selectedBandKeys = rapLayers.filter((l) => l.selected !== false).map((l) => l.bandKey).join('-');
      const layerId = `rap-cumulative-${rapSelectedYear}-${selectedBandKeys}`;
      return [
        new deck.GeoJsonLayer({
          id: layerId,
          data: subcatchmentsGeoJson,
          pickable: true,
          stroked: true,
          filled: true,
          opacity: 0.8,
          getFillColor: (f) => {
            const props = f && f.properties;
            const topaz =
              props &&
              (props.TopazID ||
                props.topaz_id ||
                props.topaz ||
                props.id ||
                props.WeppID ||
                props.wepp_id);
            const row = topaz != null ? rapSummary[String(topaz)] : null;
            return rapFillColor(row);
          },
          getLineColor: (f) => {
            const props = f && f.properties;
            const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
            if (graphHighlightedTopazId && String(topaz) === String(graphHighlightedTopazId)) {
              return [255, 200, 0, 255]; // Bright yellow highlight
            }
            return [0, 0, 0, 0]; // Transparent by default
          },
          getLineWidth: (f) => {
            const props = f && f.properties;
            const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
            if (graphHighlightedTopazId && String(topaz) === String(graphHighlightedTopazId)) {
              return 3;
            }
            return 0;
          },
          lineWidthUnits: 'pixels',
          updateTriggers: {
            getFillColor: [rapSelectedYear, selectedBandKeys],
            getLineColor: [graphHighlightedTopazId],
            getLineWidth: [graphHighlightedTopazId],
          },
        }),
      ];
    }

    // Single band mode
    const activeLayers = rapLayers
      .filter((l) => l.visible && subcatchmentsGeoJson && rapSummary)
      .map((overlay) => {
        return new deck.GeoJsonLayer({
          id: `rap-${overlay.key}-${rapSelectedYear}`,
          data: subcatchmentsGeoJson,
          pickable: true,
          stroked: true,
          filled: true,
          opacity: 0.8,
          getFillColor: (f) => {
            const props = f && f.properties;
            const topaz =
              props &&
              (props.TopazID ||
                props.topaz_id ||
                props.topaz ||
                props.id ||
                props.WeppID ||
                props.wepp_id);
            const row = topaz != null ? rapSummary[String(topaz)] : null;
            return rapFillColor(row);
          },
          getLineColor: (f) => {
            const props = f && f.properties;
            const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
            if (graphHighlightedTopazId && String(topaz) === String(graphHighlightedTopazId)) {
              return [255, 200, 0, 255]; // Bright yellow highlight
            }
            return [0, 0, 0, 0]; // Transparent by default
          },
          getLineWidth: (f) => {
            const props = f && f.properties;
            const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
            if (graphHighlightedTopazId && String(topaz) === String(graphHighlightedTopazId)) {
              return 3;
            }
            return 0;
          },
          lineWidthUnits: 'pixels',
          updateTriggers: {
            getFillColor: [rapSelectedYear],
            getLineColor: [graphHighlightedTopazId],
            getLineWidth: [graphHighlightedTopazId],
          },
        });
      });
    return activeLayers;
  }

  function pickActiveRapLayer() {
    for (let i = rapLayers.length - 1; i >= 0; i--) {
      const layer = rapLayers[i];
      if (layer.visible) {
        return layer;
      }
    }
    return null;
  }

  async function refreshRapData() {
    if (!rapSelectedYear) return;

    // In cumulative mode, load all selected bands and sum them
    if (rapCumulativeMode) {
      const selectedBands = rapLayers.filter((l) => l.selected !== false);
      if (!selectedBands.length) {
        rapSummary = {};
        return;
      }

      try {
        // Query all selected bands at once using IN filter
        const bandIds = selectedBands.map((l) => l.bandId);
        const dataPayload = {
          datasets: [{ path: 'rap/rap_ts.parquet', alias: 'rap' }],
          columns: ['rap.topaz_id AS topaz_id', 'rap.band AS band', 'rap.value AS value'],
          filters: [
            { column: 'rap.year', op: '=', value: rapSelectedYear },
            { column: 'rap.band', op: 'IN', value: bandIds },
          ],
        };
        const dataResult = await postQueryEngine(dataPayload);
        if (dataResult && dataResult.records) {
          // Sum values by topaz_id
          const sumByTopaz = {};
          for (const row of dataResult.records) {
            const tid = String(row.topaz_id);
            if (!sumByTopaz[tid]) {
              sumByTopaz[tid] = 0;
            }
            sumByTopaz[tid] += row.value || 0;
          }
          rapSummary = sumByTopaz;
        }
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn('gl-dashboard: failed to refresh RAP cumulative data', err);
      }
      return;
    }

    // Single band mode
    const activeLayer = pickActiveRapLayer();
    if (!activeLayer) return;
    try {
      const dataPayload = {
        datasets: [{ path: 'rap/rap_ts.parquet', alias: 'rap' }],
        columns: ['rap.topaz_id AS topaz_id', 'rap.value AS value'],
        filters: [
          { column: 'rap.year', op: '=', value: rapSelectedYear },
          { column: 'rap.band', op: '=', value: activeLayer.bandId },
        ],
      };
      const dataResult = await postQueryEngine(dataPayload);
      if (dataResult && dataResult.records) {
        rapSummary = {};
        for (const row of dataResult.records) {
          rapSummary[String(row.topaz_id)] = row.value;
        }
      }
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to refresh RAP data', err);
    }
  }

  /**
   * Load full RAP timeseries data for the graph panel.
   * Queries all years for selected bands and builds series data for each hillslope.
   */
  async function loadRapTimeseriesData() {
    const data = await ensureGraphLoaders().buildRapTimeseriesData();
    if (!data) {
      timeseriesGraph.hide();
      return;
    }
    timeseriesGraph.setData(data);
    syncGraphModeForContext();
  }

  const WEPP_YEARLY_COLUMN_MAP = {
    runoff_volume: '"Runoff Volume"',
    subrunoff_volume: '"Subrunoff Volume"',
    baseflow_volume: '"Baseflow Volume"',
    soil_loss: '"Soil Loss"',
    sediment_deposition: '"Sediment Deposition"',
    sediment_yield: '"Sediment Yield"',
  };

  function weppYearlyGraphColor(normalized, mode) {
    if (WATER_MEASURES.includes(mode)) {
      return winterColor(normalized);
    }
    if (SOIL_MEASURES.includes(mode)) {
      return jet2Color(normalized);
    }
    return viridisColor(normalized);
  }

  async function loadWeppYearlyTimeseriesData() {
    const data = await ensureGraphLoaders().buildWeppYearlyTimeseriesData();
    if (!data) {
      timeseriesGraph.hide();
      return;
    }
    timeseriesGraph.setData(data);
    syncGraphModeForContext();
  }

  // Wire year slider to RAP data refresh
  yearSlider.on('change', async (year) => {
    let needsApply = false;
    const hasActiveRap = rapCumulativeMode || rapLayers.some((l) => l.visible);
    if (hasActiveRap) {
      rapSelectedYear = year;
      await refreshRapData();
      needsApply = true;
      if (timeseriesGraph._source === 'rap') {
        timeseriesGraph.setCurrentYear(rapSelectedYear);
      }
    }
    const activeWeppYearly = pickActiveWeppYearlyLayer();
    if (activeWeppYearly) {
      weppYearlySelectedYear = year;
      setValue('weppYearlySelectedYear', weppYearlySelectedYear);
      await refreshWeppYearlyData();
      needsApply = true;
      if (timeseriesGraph._source === 'wepp_yearly') {
        timeseriesGraph.setCurrentYear(weppYearlySelectedYear);
      }
    }
    if (needsApply) {
      applyLayers();
    }
  });

  function buildLanduseLayers() {
    const activeLayers = landuseLayers
      .filter((l) => l.visible && subcatchmentsGeoJson && landuseSummary)
      .map((overlay) => {
        // Check if comparison mode is active and this is a comparable measure
        const useComparison = comparisonMode && 
                             currentScenarioPath && 
                             COMPARISON_MEASURES.includes(overlay.mode) &&
                             baseSummaryCache.landuse;
        
        return new deck.GeoJsonLayer({
          id: `landuse-${overlay.key}${useComparison ? '-diff' : ''}`,
          data: subcatchmentsGeoJson,
          pickable: true,
          stroked: false,
          filled: true,
          opacity: 0.8,
          getFillColor: (f) => {
            const props = f && f.properties;
            const topaz =
              props &&
              (props.TopazID ||
                props.topaz_id ||
                props.topaz ||
                props.id ||
                props.WeppID ||
                props.wepp_id);
            const row = topaz != null ? landuseSummary[String(topaz)] : null;
            
            if (useComparison) {
              const baseRow = topaz != null ? baseSummaryCache.landuse[String(topaz)] : null;
              return landuseComparisonFillColor(overlay.mode, row, baseRow);
            }
            return landuseFillColor(overlay.mode, row);
          },
          updateTriggers: {
            getFillColor: [comparisonMode, currentScenarioPath, comparisonDiffRanges[overlay.mode]],
          },
        });
      });
    return activeLayers;
  }

  function sampleRaster(layer, lonLat) {
    if (!layer || !layer.values || !layer.width || !layer.height || !layer.bounds) return null;
    const [lon, lat] = lonLat || [];
    if (!Number.isFinite(lon) || !Number.isFinite(lat)) return null;
    const [west, south, east, north] = layer.bounds;
    if (lon < west || lon > east || lat < south || lat > north) {
      return null;
    }
    const x = ((lon - west) / (east - west)) * layer.width;
    const y = ((north - lat) / (north - south)) * layer.height;
    const xi = Math.floor(x);
    const yi = Math.floor(y);
    if (xi < 0 || xi >= layer.width || yi < 0 || yi >= layer.height) return null;
    if (layer.sampleMode === 'rgba') {
      const base = (yi * layer.width + xi) * 4;
      const r = layer.values[base];
      const g = layer.values[base + 1];
      const b = layer.values[base + 2];
      const a = layer.values[base + 3];
      return `rgba(${r}, ${g}, ${b}, ${a})`;
    }
    const idx = yi * layer.width + xi;
    const v = layer.values[idx];
    return Number.isFinite(v) ? v : null;
  }

  function pickActiveRaster() {
    for (let i = detectedLayers.length - 1; i >= 0; i--) {
      const layer = detectedLayers[i];
      if (layer.visible && layer.values) {
        return layer;
      }
    }
    return null;
  }

  function pickActiveLanduseLayer() {
    for (let i = landuseLayers.length - 1; i >= 0; i--) {
      const layer = landuseLayers[i];
      if (layer.visible) {
        return layer;
      }
    }
    return null;
  }

  function pickActiveSoilsLayer() {
    for (let i = soilsLayers.length - 1; i >= 0; i--) {
      const layer = soilsLayers[i];
      if (layer.visible) {
        return layer;
      }
    }
    return null;
  }

  function zoomToBounds(bounds, explicitZoom) {
    if (!bounds || bounds.length !== 4) return;
    const [west, south, east, north] = bounds;

    // Use deck.gl's WebMercatorViewport.fitBounds for accurate zoom calculation
    // This properly accounts for:
    // 1. Viewport dimensions (container width/height)
    // 2. Mercator projection distortion at different latitudes
    // 3. Bounds aspect ratio vs viewport aspect ratio
    const containerWidth = target.clientWidth || 800;
    const containerHeight = target.clientHeight || 600;

    let longitude, latitude, zoom;

    if (explicitZoom != null && Number.isFinite(explicitZoom)) {
      // Use explicit zoom if provided, just center on bounds
      longitude = (west + east) / 2;
      latitude = (south + north) / 2;
      zoom = explicitZoom;
    } else if (deck.WebMercatorViewport) {
      // Use fitBounds for accurate zoom calculation
      // Target ~70% viewport coverage: 15% padding on each side
      const paddingFraction = 0.15;
      const paddingPixels = Math.min(containerWidth, containerHeight) * paddingFraction;

      const viewport = new deck.WebMercatorViewport({
        width: containerWidth,
        height: containerHeight
      });

      const fittedViewport = viewport.fitBounds(
        [[west, south], [east, north]],
        { padding: paddingPixels }
      );

      longitude = fittedViewport.longitude;
      latitude = fittedViewport.latitude;
      // Reduce zoom slightly to ensure watershed edges are fully visible
      zoom = fittedViewport.zoom - 0.5;
    } else {
      // Fallback if WebMercatorViewport is not available
      longitude = (west + east) / 2;
      latitude = (south + north) / 2;
      const span = Math.max(east - west, north - south);
      zoom = Math.max(2, Math.min(16, Math.log2(360 / (span || 0.001)) - 1));
    }

    // Clamp zoom to valid range
    zoom = Math.max(currentViewState.minZoom, Math.min(currentViewState.maxZoom, zoom));

    setViewState({
      longitude,
      latitude,
      zoom,
      bearing: 0,
      pitch: 0,
      minZoom: currentViewState.minZoom,
      maxZoom: currentViewState.maxZoom,
    });
  }

  async function fetchGdalInfo(path) {
    const url = `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/gdalinfo/${path}`;
    const resp = await fetch(url);
    if (!resp.ok) return null;
    return resp.json();
  }

  function colorize(values, width, height, colorMap) {
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx2d = canvas.getContext('2d');
    const imgData = ctx2d.createImageData(width, height);
    const mapEntries =
      colorMap &&
      typeof colorMap !== 'function' &&
      Object.entries(colorMap).reduce((acc, [k, hex]) => {
        const v = Number(k);
        if (!Number.isFinite(v)) return acc;
        const parsed = HEX_RGB_RE.exec(hex || '');
        if (!parsed) return acc;
        const intVal = parseInt(parsed[1], 16);
        acc[v] = [(intVal >> 16) & 255, (intVal >> 8) & 255, intVal & 255];
        return acc;
      }, {});
    const fnCache = new Map();

    if (mapEntries && Object.keys(mapEntries).length) {
      for (let i = 0, j = 0; i < values.length; i++, j += 4) {
        const v = values[i];
        const rgb = mapEntries[v];
        if (rgb) {
          imgData.data[j] = rgb[0];
          imgData.data[j + 1] = rgb[1];
          imgData.data[j + 2] = rgb[2];
          imgData.data[j + 3] = 230;
        } else {
          imgData.data[j + 3] = 0; // transparent for unknown codes
        }
      }
      ctx2d.putImageData(imgData, 0, 0);
      return { canvas, values, width, height, sampleMode: 'scalar' };
    }

    if (typeof colorMap === 'function') {
      for (let i = 0, j = 0; i < values.length; i++, j += 4) {
        const v = values[i];
        if (!Number.isFinite(v)) {
          imgData.data[j + 3] = 0;
          continue;
        }
        let rgb = fnCache.get(v);
        if (!rgb) {
          const hex = colorMap(v);
          const parsed = HEX_RGB_RE.exec(hex || '');
          if (parsed) {
            const intVal = parseInt(parsed[1], 16);
            rgb = [(intVal >> 16) & 255, (intVal >> 8) & 255, intVal & 255];
            fnCache.set(v, rgb);
          }
        }
        if (rgb) {
          imgData.data[j] = rgb[0];
          imgData.data[j + 1] = rgb[1];
          imgData.data[j + 2] = rgb[2];
          imgData.data[j + 3] = 230;
        } else {
          imgData.data[j + 3] = 0;
        }
      }
      ctx2d.putImageData(imgData, 0, 0);
      return { canvas, values, width, height, sampleMode: 'scalar' };
    }

    // Fallback grayscale
    let min = Infinity;
    let max = -Infinity;
    for (let i = 0; i < values.length; i++) {
      const v = values[i];
      if (Number.isFinite(v)) {
        if (v < min) min = v;
        if (v > max) max = v;
      }
    }
    if (!Number.isFinite(min) || !Number.isFinite(max) || min === max) {
      min = 0;
      max = 255;
    }
    const scale = 255 / (max - min || 1);
    for (let i = 0, j = 0; i < values.length; i++, j += 4) {
      const v = values[i];
      const scaled = Math.max(0, Math.min(255, Math.round((v - min) * scale)));
      imgData.data[j] = scaled;
      imgData.data[j + 1] = scaled;
      imgData.data[j + 2] = scaled;
      imgData.data[j + 3] = 200;
    }
    ctx2d.putImageData(imgData, 0, 0);
    return { canvas, values, width, height, sampleMode: 'scalar' };
  }

  async function fetchRasterCanvas(path, colorMap) {
    const url = `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/download/${path}`;
    const resp = await fetch(url);
    if (!resp.ok) {
      throw new Error(`Raster fetch failed: ${resp.status}`);
    }
    const GT = await ensureGeoTiff();
    const array = await resp.arrayBuffer();
    const tiff = await GT.fromArrayBuffer(array);
    const image = await tiff.getImage();
    const width = image.getWidth();
    const height = image.getHeight();
    const data = await image.readRasters({ interleave: true, samples: [0] });
    const values = data;
    return colorize(values, width, height, colorMap);
  }

  async function detectLayers() {
    try {
      const result = await detectRasterLayersData({
        ctx,
        layerDefs,
        loadRaster: fetchRasterCanvas,
        loadSbsImage,
        fetchGdalInfo,
        nlcdColormap: NLCD_COLORMAP,
        soilColorForValue,
      });
      if (!result || !Array.isArray(result.detectedLayers)) {
        return;
      }
      detectedLayers = result.detectedLayers;
      updateLayerList();
      applyLayers();
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to detect raster layers', err);
    }
    // Don't zoom here - let detectLanduseOverlays handle it with subcatchments bounds
  }

  async function detectLanduseOverlays() {
    try {
      const result = await detectLanduseData({ buildScenarioUrl, buildBaseUrl });
      if (!result) return;
      landuseSummary = result.landuseSummary;
      subcatchmentsGeoJson = result.subcatchmentsGeoJson || subcatchmentsGeoJson;
      landuseLayers = result.landuseLayers || [];
      updateLayerList();
      applyLayers();
      // Zoom handled by zoomToSubcatchmentBounds after all detection completes
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load landuse overlays', err);
    }
  }

  async function detectSoilsOverlays() {
    try {
      const result = await detectSoilsData({ buildScenarioUrl, buildBaseUrl, subcatchmentsGeoJson });
      if (!result) return;
      soilsSummary = result.soilsSummary;
      subcatchmentsGeoJson = result.subcatchmentsGeoJson || subcatchmentsGeoJson;
      soilsLayers = result.soilsLayers || [];
      updateLayerList();
      applyLayers();
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load soils overlays', err);
    }
  }

  async function detectHillslopesOverlays() {
    try {
      const result = await detectHillslopesData({ buildScenarioUrl, buildBaseUrl, subcatchmentsGeoJson });
      if (!result) return;
      hillslopesSummary = result.hillslopesSummary;
      subcatchmentsGeoJson = result.subcatchmentsGeoJson || subcatchmentsGeoJson;
      hillslopesLayers = result.hillslopesLayers || [];
      updateLayerList();
      applyLayers();
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load hillslopes overlays', err);
    }
  }

  async function detectWatarOverlays() {
    try {
      const result = await detectWatarData({
        buildBaseUrl,
        postQueryEngine,
        watarPath: WATAR_PATH,
        subcatchmentsGeoJson,
      });
      if (!result || !result.watarSummary) return;

      watarSummary = result.watarSummary;
      if (result.watarRanges) {
        watarRanges = result.watarRanges;
      }
      if (result.subcatchmentsGeoJson) {
        subcatchmentsGeoJson = result.subcatchmentsGeoJson;
      }
      if (result.watarLayers) {
        watarLayers = result.watarLayers;
        updateLayerList();
        applyLayers();
      }
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load WATAR overlays', err);
    }
  }

  async function detectWeppOverlays() {
    try {
      const result = await detectWeppData({
        buildBaseUrl,
        fetchWeppSummary,
        weppStatistic,
        weppLossPath: WEPP_LOSS_PATH,
        subcatchmentsGeoJson,
      });
      if (!result || !result.weppSummary) return;
      weppSummary = result.weppSummary;
      if (result.weppRanges) {
        weppRanges = result.weppRanges;
      }
      if (result.subcatchmentsGeoJson) {
        subcatchmentsGeoJson = result.subcatchmentsGeoJson;
      }
      if (result.weppLayers) {
        weppLayers = result.weppLayers;
        updateLayerList();
        applyLayers();
      }
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load WEPP overlays', err);
    }
  }

  async function detectWeppYearlyOverlays() {
    weppYearlyLayers = [];
    weppYearlySummary = null;
    weppYearlyMetadata = null;
    try {
      const result = await detectWeppYearlyData({
        buildBaseUrl,
        postQueryEngine,
        weppYearlyPath: WEPP_YEARLY_PATH,
        currentSelectedYear: weppYearlySelectedYear,
        subcatchmentsGeoJson,
      });
      if (!result || !result.weppYearlyMetadata) {
        if (result && Array.isArray(result.weppYearlyLayers)) {
          weppYearlyLayers = result.weppYearlyLayers;
        }
        setState({
          weppYearlyLayers: [...weppYearlyLayers],
          weppYearlyMetadata: null,
          weppYearlySelectedYear: null,
          weppYearlySummary: null,
        });
        if (!rapCumulativeMode && !rapLayers.some((l) => l.visible)) {
          yearSlider.hide();
        }
        updateLayerList();
        return;
      }

      weppYearlyMetadata = result.weppYearlyMetadata;
      weppYearlySelectedYear = result.weppYearlySelectedYear;
      subcatchmentsGeoJson = result.subcatchmentsGeoJson || subcatchmentsGeoJson;
      weppYearlyLayers = result.weppYearlyLayers || [];
      setState({
        weppYearlyMetadata,
        weppYearlySelectedYear,
        weppYearlyLayers: [...weppYearlyLayers],
        weppYearlySummary,
        subcatchmentsGeoJson,
      });

      yearSlider.setRange(weppYearlyMetadata.minYear, weppYearlyMetadata.maxYear, weppYearlySelectedYear);
      yearSlider.show();

      await refreshWeppYearlyData();
      updateLayerList();
      applyLayers();
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load WEPP yearly overlays', err);
    }
  }

  async function detectWeppEventOverlays() {
    try {
      const result = await detectWeppEventData({
        buildBaseUrl,
        climateCtx: ctx.climate,
        currentSelectedDate: weppEventSelectedDate,
        subcatchmentsGeoJson,
      });
      if (!result) return;

      if (result.subcatchmentsGeoJson) {
        subcatchmentsGeoJson = result.subcatchmentsGeoJson;
      }
      if (result.weppEventLayers) {
        weppEventLayers = result.weppEventLayers;
      }
      if (result.weppEventMetadata) {
        weppEventMetadata = result.weppEventMetadata;
      }
      if (result.weppEventSelectedDate) {
        weppEventSelectedDate = result.weppEventSelectedDate;
      }

      updateLayerList();
      applyLayers();
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load WEPP Event overlays', err);
    }
  }

  /**
   * Post a JSON payload to the query-engine and return the parsed response.
   * @param {Object} payload - Query engine request body
   * @returns {Promise<Object|null>} Parsed JSON response or null on failure
   */
  async function postQueryEngine(payload) {
    return queryEngine.postQueryEngine(payload);
  }

  async function postBaseQueryEngine(payload) {
    return queryEngine.postBaseQueryEngine(payload);
  }

  async function postQueryEngineForScenario(payload, scenarioPath) {
    return queryEngine.postQueryEngineForScenario(payload, scenarioPath);
  }

  function scenarioColor(idx) {
    const c = GRAPH_COLORS[idx % GRAPH_COLORS.length];
    return [c[0], c[1], c[2], 255];
  }

  function quantile(values, q) {
    if (!values.length) return null;
    const sorted = [...values].sort((a, b) => a - b);
    const pos = (sorted.length - 1) * q;
    const lower = Math.floor(pos);
    const upper = Math.ceil(pos);
    if (lower === upper) return sorted[lower];
    const weight = pos - lower;
    return sorted[lower] * (1 - weight) + sorted[upper] * weight;
  }

  function computeBoxStats(values) {
    const clean = (values || []).filter((v) => Number.isFinite(v));
    if (!clean.length) return null;
    const min = Math.min(...clean);
    const max = Math.max(...clean);
    const q1 = quantile(clean, 0.25);
    const median = quantile(clean, 0.5);
    const q3 = quantile(clean, 0.75);
    return { min, q1, median, q3, max };
  }

  async function loadHillLossScenario(scenarioPath) {
    const key = scenarioPath || '';
    if (hillLossCache[key]) return hillLossCache[key];
    const payload = {
      datasets: [
        { path: 'wepp/output/interchange/loss_pw0.hill.parquet', alias: 'loss' },
        { path: 'watershed/hillslopes.parquet', alias: 'hill' },
      ],
      joins: [{ left: 'loss', right: 'hill', on: 'wepp_id', type: 'inner' }],
      columns: [
        'loss."Hillslope Area" AS area_ha',
        'loss."Soil Loss" AS soil_loss_kg',
        'loss."Runoff Volume" AS runoff_volume_m3',
        'hill.topaz_id AS topaz_id',
      ],
    };
    try {
      const result = await postQueryEngineForScenario(payload, scenarioPath);
      const rows = [];
      if (result && result.records) {
        for (const row of result.records) {
          rows.push({
            area_ha: Number(row.area_ha),
            soil_loss_kg: Number(row.soil_loss_kg),
            runoff_volume_m3: Number(row.runoff_volume_m3),
          });
        }
      }
      hillLossCache[key] = rows;
      const totalArea = rows.reduce((acc, r) => acc + (Number.isFinite(r.area_ha) ? r.area_ha : 0), 0);
      hillslopeAreaCache[key] = totalArea;
      return rows;
    } catch (err) {
      console.warn('gl-dashboard: failed to load hillslope loss data', err);
      hillLossCache[key] = [];
      return [];
    }
  }

  async function loadChannelLossScenario(scenarioPath) {
    const key = scenarioPath || '';
    if (channelLossCache[key]) return channelLossCache[key];
    const payload = {
      datasets: [{ path: 'wepp/output/interchange/loss_pw0.chn.parquet', alias: 'chn' }],
      columns: [
        'chn."Soil Loss" AS soil_loss_kg',
        'chn.chn_enum AS chn_id',
      ],
    };
    try {
      const result = await postQueryEngineForScenario(payload, scenarioPath);
      const rows = [];
      if (result && result.records) {
        for (const row of result.records) {
          rows.push({
            soil_loss_kg: Number(row.soil_loss_kg),
            chn_id: row.chn_id,
          });
        }
      }
      channelLossCache[key] = rows;
      return rows;
    } catch (err) {
      console.warn('gl-dashboard: failed to load channel loss data', err);
      channelLossCache[key] = [];
      return [];
    }
  }

  async function loadOutletScenario(scenarioPath) {
    const key = scenarioPath || '';
    if (outletAllYearsCache[key]) return outletAllYearsCache[key];
    const payload = {
      datasets: [{ path: 'wepp/output/interchange/loss_pw0.all_years.out.parquet', alias: 'out' }],
      columns: ['out.year AS year', 'out.key AS key', 'out.value AS value'],
      order_by: ['year'],
    };
    try {
      const result = await postQueryEngineForScenario(payload, scenarioPath);
      const map = {};
      if (result && result.records) {
        for (const row of result.records) {
          const year = Number(row.year);
          const keyName = String(row.key || '');
          const val = Number(row.value);
          if (!map[keyName]) {
            map[keyName] = {};
          }
          if (Number.isFinite(year)) {
            map[keyName][year] = val;
          }
        }
      }
      outletAllYearsCache[key] = map;
      return map;
    } catch (err) {
      console.warn('gl-dashboard: failed to load outlet data', err);
      outletAllYearsCache[key] = {};
      return {};
    }
  }

  async function getTotalAreaHa(scenarioPath) {
    const key = scenarioPath || '';
    if (hillslopeAreaCache[key] != null) return hillslopeAreaCache[key];
    await loadHillLossScenario(scenarioPath);
    return hillslopeAreaCache[key] || 0;
  }

  function selectOutletKey(outletMap, candidates) {
    const keys = Object.keys(outletMap || {});
    if (!keys.length) return null;
    for (const cand of candidates) {
      const exact = keys.find((k) => k.toLowerCase() === cand.toLowerCase());
      if (exact) return exact;
    }
    for (const cand of candidates) {
      const match = keys.find((k) => k.toLowerCase().includes(cand.toLowerCase()));
      if (match) return match;
    }
    return null;
  }

  async function buildHillSoilLossBoxplot() {
    const series = [];
    for (let i = 0; i < graphScenarios.length; i++) {
      const scenario = graphScenarios[i];
      const rows = await loadHillLossScenario(scenario.path);
      const perArea = rows
        .map((r) => {
          const areaHa = Number(r.area_ha);
          const soilKg = Number(r.soil_loss_kg);
          if (!Number.isFinite(areaHa) || areaHa <= 0 || !Number.isFinite(soilKg)) return null;
          return soilKg / (areaHa * 1000); // tonne/ha
        })
        .filter((v) => Number.isFinite(v));
      const stats = computeBoxStats(perArea);
      if (stats) {
        series.push({ label: scenario.name, stats, color: scenarioColor(i) });
      }
    }
    return {
      type: 'boxplot',
      title: 'Soil Loss (hillslopes)',
      yLabel: 'tonne/ha',
      source: 'omni',
      series,
    };
  }

  async function buildHillRunoffBoxplot() {
    const series = [];
    for (let i = 0; i < graphScenarios.length; i++) {
      const scenario = graphScenarios[i];
      const rows = await loadHillLossScenario(scenario.path);
      const perArea = rows
        .map((r) => {
          const areaHa = Number(r.area_ha);
          const runoffM3 = Number(r.runoff_volume_m3);
          if (!Number.isFinite(areaHa) || areaHa <= 0 || !Number.isFinite(runoffM3)) return null;
          return (runoffM3 * 1000) / (areaHa * 10000); // mm over area
        })
        .filter((v) => Number.isFinite(v));
      const stats = computeBoxStats(perArea);
      if (stats) {
        series.push({ label: scenario.name, stats, color: scenarioColor(i) });
      }
    }
    return {
      type: 'boxplot',
      title: 'Runoff (hillslopes)',
      yLabel: 'mm',
      source: 'omni',
      series,
    };
  }

  async function buildChannelSoilLossBoxplot() {
    const series = [];
    for (let i = 0; i < graphScenarios.length; i++) {
      const scenario = graphScenarios[i];
      const rows = await loadChannelLossScenario(scenario.path);
      const tonnes = rows
        .map((r) => {
          const soilKg = Number(r.soil_loss_kg);
          return Number.isFinite(soilKg) ? soilKg / 1000 : null;
        })
        .filter((v) => Number.isFinite(v));
      const stats = computeBoxStats(tonnes);
      if (stats) {
        series.push({ label: scenario.name, stats, color: scenarioColor(i) });
      }
    }
    return {
      type: 'boxplot',
      title: 'Soil Loss (channels)',
      yLabel: 'tonne',
      source: 'omni',
      series,
    };
  }

  async function buildOutletSedimentBars() {
    const yearsSet = new Set();
    const scenarioData = [];
    for (let i = 0; i < graphScenarios.length; i++) {
      const scenario = graphScenarios[i];
      const outletMap = await loadOutletScenario(scenario.path);
      const keyName = selectOutletKey(outletMap, ['total sediment discharge from outlet', 'sediment discharge from outlet', 'sediment discharge']);
      const areaHa = await getTotalAreaHa(scenario.path);
      scenarioData.push({ scenario, outletMap, keyName, areaHa, color: scenarioColor(i) });
      if (keyName && outletMap[keyName]) {
        for (const yr of Object.keys(outletMap[keyName])) {
          const yNum = Number(yr);
          if (Number.isFinite(yNum)) yearsSet.add(yNum);
        }
      }
    }
    const years = Array.from(yearsSet).sort((a, b) => a - b);
    const series = [];
    for (const data of scenarioData) {
      if (!data.keyName || !years.length) continue;
      const values = years.map((yr) => {
        const raw = data.outletMap[data.keyName] ? Number(data.outletMap[data.keyName][yr]) : null;
        if (!Number.isFinite(raw) || !data.areaHa) return null;
        return raw / data.areaHa; // tonne/ha
      });
      series.push({ label: data.scenario.name, values, color: data.color });
    }
    const lineSeries = {};
    series.forEach((s) => {
      lineSeries[s.label] = { values: s.values, color: s.color };
    });
    return {
      type: 'line',
      title: 'Sediment discharge (outlet)',
      years,
      series: lineSeries,
      xLabel: 'Year',
      yLabel: 'tonne/ha',
      source: 'omni',
    };
  }

  async function buildOutletStreamBars() {
    const yearsSet = new Set();
    const scenarioData = [];
    for (let i = 0; i < graphScenarios.length; i++) {
      const scenario = graphScenarios[i];
      const outletMap = await loadOutletScenario(scenario.path);
      const keyName = selectOutletKey(outletMap, ['water discharge from outlet', 'stream discharge']);
      const areaHa = await getTotalAreaHa(scenario.path);
      scenarioData.push({ scenario, outletMap, keyName, areaHa, color: scenarioColor(i) });
      if (keyName && outletMap[keyName]) {
        for (const yr of Object.keys(outletMap[keyName])) {
          const yNum = Number(yr);
          if (Number.isFinite(yNum)) yearsSet.add(yNum);
        }
      }
    }
    const years = Array.from(yearsSet).sort((a, b) => a - b);
    const series = [];
    for (const data of scenarioData) {
      if (!data.keyName || !years.length) continue;
      const values = years.map((yr) => {
        const raw = data.outletMap[data.keyName] ? Number(data.outletMap[data.keyName][yr]) : null;
        if (!Number.isFinite(raw) || !data.areaHa) return null;
        // raw assumed m^3, convert to mm over watershed area
        return (raw * 1000) / (data.areaHa * 10000);
      });
      series.push({ label: data.scenario.name, values, color: data.color });
    }
    const lineSeries = {};
    series.forEach((s) => {
      lineSeries[s.label] = { values: s.values, color: s.color };
    });
    return {
      type: 'line',
      title: 'Stream discharge (outlet)',
      years,
      series: lineSeries,
      xLabel: 'Year',
      yLabel: 'mm',
      source: 'omni',
    };
  }

  const GRAPH_LOADERS = {
    'omni-soil-loss-hill': buildHillSoilLossBoxplot,
    'omni-soil-loss-chn': buildChannelSoilLossBoxplot,
    'omni-runoff-hill': buildHillRunoffBoxplot,
    'omni-outlet-sediment': buildOutletSedimentBars,
    'omni-outlet-stream': buildOutletStreamBars,
  };

  async function loadGraphDataset(key, { force } = {}) {
    return ensureGraphLoaders().loadGraphDataset(key, { force });
  }

  async function activateGraphItem(key, options = {}) {
    activeGraphKey = key;
    const keepFocus = options.keepFocus || false;
    ensureGraphExpanded();
    try {
      const data = await loadGraphDataset(key, { force: options.force });
      if (data) {
        // Respect caller override; otherwise only focus full-pane for omni graphs.
        if (!keepFocus) {
          setGraphFocus(data.source === 'omni');
        }
        timeseriesGraph.setData(data);
        if (graphEmptyEl) graphEmptyEl.style.display = 'none';
      } else {
        timeseriesGraph.hide();
        if (graphEmptyEl) {
          graphEmptyEl.textContent = 'No data available for this graph.';
          graphEmptyEl.style.display = '';
        }
      }
      syncGraphModeForContext();
    } catch (err) {
      console.warn('gl-dashboard: failed to activate graph', err);
      timeseriesGraph.hide();
      if (graphEmptyEl) {
        graphEmptyEl.textContent = 'Unable to load graph data.';
        graphEmptyEl.style.display = '';
      }
    }
  }

  async function detectRapOverlays() {
    try {
      const result = await detectRapData({
        buildBaseUrl,
        postQueryEngine,
        rapBandLabels: RAP_BAND_LABELS,
        subcatchmentsGeoJson,
        currentSelectedYear: rapSelectedYear,
      });
      if (!result) return;

      if (result.subcatchmentsGeoJson) {
        subcatchmentsGeoJson = result.subcatchmentsGeoJson;
      }
      if (result.rapMetadata) {
        rapMetadata = result.rapMetadata;
      }
      if (result.rapSelectedYear != null) {
        rapSelectedYear = result.rapSelectedYear;
      }
      if (result.rapLayers) {
        rapLayers = result.rapLayers;
      }
      if (rapMetadata && rapMetadata.years && rapMetadata.years.length) {
        const minYear = rapMetadata.years[0];
        const maxYear = rapMetadata.years[rapMetadata.years.length - 1];
        yearSlider.setRange(minYear, maxYear, rapSelectedYear);
      }
      if (result.rapSummary) {
        rapSummary = result.rapSummary;
      }

      updateLayerList();
      applyLayers();
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load RAP overlays', err);
    }
  }

  mapController = createMapController({
    deck,
    target,
    controllerOptions,
    initialViewState,
    layers: [baseLayer],
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
          timeseriesGraph.highlightSubcatchment(String(topaz));
          return;
        }
      }
      timeseriesGraph.clearHighlight();
    },
    getTooltip: (info) => layerUtils.formatTooltip(info),
    onError: (error) => {
      // Keep the stub resilient; surface issues in console.
      // eslint-disable-next-line no-console
      console.error('gl-dashboard render error', error);
    },
  });
  const { deckgl } = mapController;

  // Expose for debugging.
  window.glDashboardDeck = deckgl;

  /**
   * Highlight a subcatchment on the map (called from graph hover).
   * Uses deck.gl updateTriggers mechanism via layer highlighting.
   */
  window.glDashboardHighlightSubcatchment = function (topazId) {
    if (topazId === graphHighlightedTopazId) return;
    graphHighlightedTopazId = topazId;
    // Re-render layers to apply highlight
    applyLayers();
  };

  updateGraphList();

  async function initializeDashboard() {
    bindScenarioSelector();
    bindComparisonToggle();
    const scenarioInitialized = await initializeScenarioFromSelect();
    const detectionTasks = [detectLayers(), detectHillslopesOverlays(), detectWatarOverlays(), detectWeppEventOverlays(), detectRapOverlays()];
    if (!scenarioInitialized) {
      detectionTasks.push(detectLanduseOverlays(), detectSoilsOverlays(), detectWeppOverlays(), detectWeppYearlyOverlays());
    }
    await Promise.all(detectionTasks);
  }

  initializeDashboard().catch((err) => {
    // eslint-disable-next-line no-console
    console.error('gl-dashboard: layer detection failed', err);
  });
})();
