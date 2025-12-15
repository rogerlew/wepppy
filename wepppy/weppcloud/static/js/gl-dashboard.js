(function () {
  const ctx = window.GL_DASHBOARD_CONTEXT || {};
  const target = document.getElementById('gl-dashboard-map');

  if (!target) {
    return;
  }

  if (typeof deck === 'undefined' || !deck.Deck) {
    target.innerHTML = '<div style="padding:1rem;color:#e11d48;">deck.gl script failed to load.</div>';
    return;
  }

  // ============================================================================
  // Omni Scenario and Comparison Mode State
  // ============================================================================
  let currentScenarioPath = ''; // Empty string = base scenario
  let comparisonMode = false;
  let baseSummaryCache = {}; // Cache for base scenario data when in comparison mode
  let comparisonDiffRanges = {}; // Cache for computed difference ranges per measure
  
  // Measures that support comparison (difference) mapping
  const COMPARISON_MEASURES = [
    'cancov', 'inrcov', 'rilcov',  // Landuse covers
    'runoff_volume', 'subrunoff_volume', 'baseflow_volume', 'soil_loss', 'sediment_deposition', 'sediment_yield',  // WEPP
    'event_P', 'event_Q', 'event_ET', 'event_peakro', 'event_tdet'  // WEPP Event
  ];
  
  // Water-related measures use winter (blue→green) colormap
  const WATER_MEASURES = [
    'runoff_volume', 'subrunoff_volume', 'baseflow_volume',  // WEPP
    'event_P', 'event_Q', 'event_ET', 'event_peakro'  // WEPP Event
  ];
  
  // Soil-related measures use jet2 (cyan→yellow→red) colormap
  const SOIL_MEASURES = [
    'soil_loss', 'sediment_deposition', 'sediment_yield',  // WEPP
    'event_tdet'  // WEPP Event
  ];
  
  // Create colormaps for different measure types
  const rdbuScale =
    typeof createColormap === 'function'
      ? createColormap({ colormap: 'rdbu', nshades: 256, format: 'rgba' })
      : null;
  const winterScale =
    typeof createColormap === 'function'
      ? createColormap({ colormap: 'winter', nshades: 256, format: 'rgba' })
      : null;
  const jet2Scale =
    typeof createColormap === 'function'
      ? createColormap({ colormap: 'jet2', nshades: 256, format: 'rgba' })
      : null;

  const defaultTileTemplate =
    ctx.tileUrl || 'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png';
  let subcatchmentsVisible = true;

  // Basemap definitions - Google endpoints match wepppy/weppcloud/controllers_js/map.js
  const GOOGLE_SUBDOMAINS = ['mt0', 'mt1', 'mt2', 'mt3'];
  let subdomainIndex = 0;
  function nextGoogleSubdomain() {
    const sub = GOOGLE_SUBDOMAINS[subdomainIndex % GOOGLE_SUBDOMAINS.length];
    subdomainIndex++;
    return sub;
  }

  const BASEMAP_DEFS = {
    osm: {
      label: 'OpenStreetMap',
      template: 'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png',
      getUrl: function (x, y, z) {
        return this.template
          .replace('{x}', String(x))
          .replace('{y}', String(y))
          .replace('{z}', String(z));
      }
    },
    googleTerrain: {
      label: 'Google Terrain',
      template: 'https://{s}.google.com/vt/lyrs=p&x={x}&y={y}&z={z}',
      getUrl: function (x, y, z) {
        const sub = nextGoogleSubdomain();
        return this.template
          .replace('{s}', sub)
          .replace('{x}', String(x))
          .replace('{y}', String(y))
          .replace('{z}', String(z));
      }
    },
    googleSatellite: {
      label: 'Google Satellite',
      template: 'https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
      getUrl: function (x, y, z) {
        const sub = nextGoogleSubdomain();
        return this.template
          .replace('{s}', sub)
          .replace('{x}', String(x))
          .replace('{y}', String(y))
          .replace('{z}', String(z));
      }
    }
  };

  let currentBasemapKey = ctx.basemap || 'googleTerrain';
  if (!BASEMAP_DEFS[currentBasemapKey]) {
    currentBasemapKey = 'googleTerrain';
  }

  // Use map extent/center from ron.nodb if available
  // Note: We intentionally ignore ctx.mapZoom - it reflects the user's last
  // interactive zoom which may be zoomed into a small area. For the dashboard
  // we always want to show the full watershed extent.
  const mapCenter = ctx.mapCenter; // [longitude, latitude]
  const mapExtent = ctx.mapExtent; // [west, south, east, north]

  // Calculate initial zoom from extent to show full watershed
  let initialZoom = ctx.zoom || 5;
  if (mapExtent && mapExtent.length === 4 && mapExtent.every(Number.isFinite)) {
    const [west, south, east, north] = mapExtent;
    const span = Math.max(east - west, north - south);
    // Zoom to fit watershed with some padding
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

  const controllerOptions = {
    dragPan: true,
    dragRotate: false,
    scrollZoom: true,
    touchZoom: true,
    touchRotate: false,
    doubleClickZoom: true,
    keyboard: true,
  };
  let currentViewState = initialViewState;

  function setViewState(viewState) {
    currentViewState = viewState;
    deckgl.setProps({ viewState: currentViewState });
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

  function setGraphFocus(enabled) {
    graphFocus = !!enabled;
    if (glMainEl) {
      if (graphFocus) {
        glMainEl.classList.add('graph-focus');
      } else {
        glMainEl.classList.remove('graph-focus');
      }
    }
  }

  function ensureGraphExpanded() {
    if (graphPanelEl) {
      graphPanelEl.classList.remove('is-collapsed');
    }
  }

  function setGraphCollapsed(collapsed) {
    if (!graphPanelEl) return;
    graphPanelEl.classList.toggle('is-collapsed', collapsed);
    if (typeof window.glDashboardGraphToggled === 'function') {
      window.glDashboardGraphToggled(!graphPanelEl.classList.contains('is-collapsed'));
    }
    if (collapsed) {
      setGraphFocus(false);
    } else {
      setGraphFocus(true);
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
    setGraphCollapsed(collapsing);
  }

  window.glDashboardToggleGraphPanel = toggleGraphPanel;

  const layerDefs = [
    {
      key: 'landuse',
      label: 'Landuse (nlcd.tif)',
      // NoDbBase.lc_fn
      paths: ['landuse/nlcd.tif'],
    },
    {
      key: 'soils',
      label: 'Soils (ssurgo.tif)',
      // NoDbBase.ssurgo_fn
      paths: ['soils/ssurgo.tif'],
    },
  ];

  const detectedLayers = [];
  const landuseLayers = [];
  const soilsLayers = [];
  const hillslopesLayers = [];
  const watarLayers = [];
  const weppLayers = [];
  const weppYearlyLayers = [];
  const weppEventLayers = [];
  const rapLayers = [];
  const graphDefs = [
    {
      key: 'omni',
      title: 'Omni Scenarios',
      items: [
        { key: 'omni-soil-loss-hill', label: 'Soil Loss (hillslopes, tonne/ha)', type: 'boxplot' },
        { key: 'omni-soil-loss-chn', label: 'Soil Loss (channels, tonne)', type: 'boxplot' },
        { key: 'omni-runoff-hill', label: 'Runoff (hillslopes, mm)', type: 'boxplot' },
        { key: 'omni-outlet-sediment', label: 'Sediment discharge (tonne/ha)', type: 'bars' },
        { key: 'omni-outlet-stream', label: 'Stream discharge (mm)', type: 'bars' },
      ],
    },
  ];
  const omniScenarios = Array.isArray(ctx.omniScenarios) ? ctx.omniScenarios : [];
  const graphScenarios = [{ name: 'Base', path: '' }].concat(
    omniScenarios.map((s) => ({ name: s.name || s.path || 'Scenario', path: s.path || '' }))
  );
  let graphFocus = false;
  let activeGraphKey = null;
  const hillLossCache = {};
  const channelLossCache = {};
  const outletAllYearsCache = {};
  const hillslopeAreaCache = {};
  const graphDataCache = {};
  let landuseSummary = null;
  let soilsSummary = null;
  let hillslopesSummary = null;
  let watarSummary = null;
  let weppSummary = null;
  let weppStatistic = 'mean'; // mean | p90 | sd | cv
  let weppYearlyMetadata = null; // { years: [], minYear, maxYear }
  let weppYearlySelectedYear = null;
  let weppYearlySummary = null;
  let weppYearlyDiffRanges = {};
  let weppYearlyCache = {};
  let baseWeppYearlyCache = {};
  let weppEventSummary = null;
  let weppEventMetadata = null; // { available, startDate, endDate }
  let weppEventSelectedDate = null; // "YYYY-MM-DD" string
  let rapSummary = null;
  let rapMetadata = null;
  let rapSelectedYear = null;
  let rapCumulativeMode = false; // true = show sum of selected bands
  let subcatchmentsGeoJson = null;
  let subcatchmentLabelsVisible = false;
  let graphHighlightedTopazId = null; // Subcatchment highlighted from graph hover
  const layerListEl = document.getElementById('gl-layer-list');
  const layerEmptyEl = document.getElementById('gl-layer-empty');
  const graphListEl = document.getElementById('gl-graph-list');
  const graphEmptyEl = document.getElementById('gl-graph-empty');
  const glMainEl = document.querySelector('.gl-main');
  const graphPanelEl = document.getElementById('gl-graph');
  let geoTiffLoader = null;

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

  // ============================================================================
  // Timeseries Graph Controller (for RAP and other timeseries data)
  // ============================================================================
  const timeseriesGraph = {
    canvas: null,
    ctx2d: null,
    container: document.getElementById('gl-graph-container'),
    emptyEl: document.getElementById('gl-graph-empty'),
    _emptyDefault: '',
    tooltipEl: document.getElementById('gl-graph-tooltip'),
    _visible: false,
    _data: null, // { years: [], series: { topazId: { values: [], color: [r,g,b] } } }
    _highlightedId: null,
    _hoveredId: null, // from canvas hover
    _currentYear: null,
    _source: null,
    _tooltipFormatter: null,
    _padding: { top: 32, right: 160, bottom: 80, left: 100 },
    _lineWidth: 1.5,
    _highlightWidth: 3,

    init() {
      this.canvas = document.getElementById('gl-graph-canvas');
      if (this.emptyEl) {
        this.emptyEl.textContent = '';
      }
      if (this.canvas) {
        this.ctx2d = this.canvas.getContext('2d');
        this.canvas.addEventListener('mousemove', (e) => this._onCanvasHover(e));
        this.canvas.addEventListener('mouseleave', () => this._onCanvasLeave());
        // Handle resize
        window.addEventListener('resize', () => {
          if (this._visible && this._data) {
            this._resizeCanvas();
            this.render();
          }
        });
      }
    },

    show() {
      if (this.container) {
        this.container.style.display = 'block';
      }
      if (this.emptyEl) {
        this.emptyEl.style.display = 'none';
        this.emptyEl.textContent = '';
      }
      this._visible = true;
      this._resizeCanvas();
    },

    hide() {
      if (this.container) {
        this.container.style.display = 'none';
      }
      if (this.emptyEl) {
        this.emptyEl.textContent = this._emptyDefault;
        this.emptyEl.style.display = 'block';
      }
      this._visible = false;
      this._data = null;
      this._currentYear = null;
      this._source = null;
      this._tooltipFormatter = null;
    },

    _resizeCanvas() {
      if (!this.canvas || !this.container) return;
      const rect = this.container.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      const width = Math.max(rect.width, 400);
      const height = graphFocus ? Math.max(rect.height * 0.8 || 0, 320) : 200;
      this.canvas.width = width * dpr;
      this.canvas.height = height * dpr;
      this.canvas.style.width = width + 'px';
      this.canvas.style.height = height + 'px';
      if (this.ctx2d) {
        this.ctx2d.setTransform(1, 0, 0, 1, 0, 0);
        this.ctx2d.scale(dpr, dpr);
      }
    },

    setData(data) {
      this._data = data;
      const headerEl = document.querySelector('#gl-graph h4');
      if (headerEl) {
        headerEl.textContent = data && data.title ? data.title : 'Graph';
      }
      this._currentYear = data && data.currentYear != null ? data.currentYear : null;
      this._source = data && data.source ? data.source : null;
      this._tooltipFormatter = data && typeof data.tooltipFormatter === 'function' ? data.tooltipFormatter : null;
      if (this._hasData(data)) {
        if (graphPanelEl && graphPanelEl.classList.contains('is-collapsed')) {
          graphPanelEl.classList.remove('is-collapsed');
          if (typeof window.glDashboardGraphToggled === 'function') {
            window.glDashboardGraphToggled(true);
          }
        }
        // Full-pane focus only for omni graphs; keep split view for RAP/WEPP yearly.
        setGraphFocus(data.source === 'omni');
        this.show();
        this.render();
      } else {
        this.hide();
      }
    },

    setCurrentYear(year) {
      this._currentYear = year;
      if (this._visible && this._data) {
        this.render();
      }
    },

    /**
     * Highlight a specific subcatchment line (from map hover).
     */
    highlightSubcatchment(topazId) {
      if (this._highlightedId !== topazId) {
        this._highlightedId = topazId;
        if (this._visible && this._data) {
          this.render();
        }
      }
    },

    clearHighlight() {
      if (this._highlightedId !== null) {
        this._highlightedId = null;
        if (this._visible && this._data) {
          this.render();
        }
      }
    },

    render() {
      if (!this.ctx2d || !this._data) return;
      const type = this._data.type || 'line';
      if (type === 'boxplot') {
        return this._renderBoxplot();
      }
      if (type === 'bars') {
        return this._renderBars();
      }
      return this._renderLine();
    },

    _hasData(data) {
      if (!data) return false;
      const type = data.type || 'line';
      if (type === 'boxplot') {
        return Array.isArray(data.series) && data.series.some((s) => s && s.stats);
      }
      if (type === 'bars') {
        return Array.isArray(data.series) && data.series.length && Array.isArray(data.categories) && data.categories.length;
      }
      return data.years && data.series && Object.keys(data.series).length > 0;
    },

    _renderLine() {
      if (!this.ctx2d || !this._data || !this._data.years || !this._data.series) return;
      const theme = this._getTheme();
      const ctx = this.ctx2d;
      const dpr = window.devicePixelRatio || 1;
      const width = this.canvas.width / dpr;
      const height = this.canvas.height / dpr;
      const pad = { ...this._padding, bottom: Math.max(this._padding.bottom, 60) };
      const plotWidth = width - pad.left - pad.right;
      const plotHeight = height - pad.top - pad.bottom;

      ctx.clearRect(0, 0, width, height);

      const years = this._data.years;
      const series = this._data.series;
      const seriesIds = Object.keys(series);
      if (years.length === 0 || seriesIds.length === 0) return;

      const xMin = Math.min(...years);
      const xMax = Math.max(...years);
      const xRange = xMax - xMin || 1;
      const xScale = (yr) => pad.left + ((yr - xMin) / xRange) * plotWidth;

      let yMin = Infinity, yMax = -Infinity;
      for (const id of seriesIds) {
        for (const v of series[id].values) {
          if (v != null && isFinite(v)) {
            if (v < yMin) yMin = v;
            if (v > yMax) yMax = v;
          }
        }
      }
      if (!isFinite(yMin)) yMin = 0;
      if (!isFinite(yMax)) yMax = 100;
      const yPad = (yMax - yMin) * 0.1 || 5;
      yMin = Math.max(0, yMin - yPad);
      yMax = yMax + yPad;
      const yRange = yMax - yMin || 1;
      const yScale = (v) => pad.top + plotHeight - ((v - yMin) / yRange) * plotHeight;

      this._xScale = xScale;
      this._yScale = yScale;
      this._plotBounds = { left: pad.left, right: width - pad.right, top: pad.top, bottom: height - pad.bottom };
      this._yMin = yMin;
      this._yMax = yMax;

      ctx.strokeStyle = theme.axis;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(pad.left, pad.top);
      ctx.lineTo(pad.left, height - pad.bottom);
      ctx.lineTo(width - pad.right, height - pad.bottom);
      ctx.stroke();

      ctx.fillStyle = theme.muted;
      ctx.font = '13px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      const xTicks = this._computeTicks(xMin, xMax, 6, true);
      for (const tick of xTicks) {
        const x = xScale(tick);
        ctx.beginPath();
        ctx.moveTo(x, height - pad.bottom);
        ctx.lineTo(x, height - pad.bottom + 4);
        ctx.stroke();
        ctx.fillText(String(tick), x, height - pad.bottom + 6);
      }

      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      const yTicks = this._computeTicks(yMin, yMax, 5, false);
      for (const tick of yTicks) {
        const y = yScale(tick);
        ctx.beginPath();
        ctx.moveTo(pad.left - 4, y);
        ctx.lineTo(pad.left, y);
        ctx.stroke();
        ctx.fillText(tick.toFixed(0), pad.left - 6, y);
        ctx.strokeStyle = theme.grid;
        ctx.beginPath();
        ctx.moveTo(pad.left, y);
        ctx.lineTo(width - pad.right, y);
        ctx.stroke();
        ctx.strokeStyle = theme.axis;
      }

      if (this._data.xLabel) {
        ctx.fillStyle = theme.muted;
        ctx.font = '14px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText(this._data.xLabel, pad.left + plotWidth / 2, height - 12);
      }

      if (this._data.yLabel) {
        ctx.save();
        ctx.translate(12, pad.top + plotHeight / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.fillStyle = theme.muted;
        ctx.font = '14px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText(this._data.yLabel, 0, 0);
        ctx.restore();
      }

      const highlightId = this._highlightedId || this._hoveredId;
      for (const id of seriesIds) {
        if (id === String(highlightId)) continue;
        this._drawLine(ctx, years, series[id], xScale, yScale, false);
      }

      if (highlightId && series[String(highlightId)]) {
        this._drawLine(ctx, years, series[String(highlightId)], xScale, yScale, true);
      }

      if (this._currentYear && this._currentYear >= xMin && this._currentYear <= xMax) {
        const x = xScale(this._currentYear);
        ctx.strokeStyle = '#ffcc00';
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(x, pad.top);
        ctx.lineTo(x, height - pad.bottom);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Legend: only for omni scenario graphs (flagged via source)
      if (this._data && this._data.source === 'omni') {
        const legendItems = seriesIds.map((id) => {
          const s = series[id] || {};
          return {
            label: s.label || id,
            color: s.color || [100, 150, 200, 180],
            id,
          };
        });
        if (legendItems.length) {
          const legendX = width - pad.right + 10;
          let legendY = pad.top;
          ctx.textAlign = 'left';
          ctx.textBaseline = 'middle';
          ctx.font = '13px sans-serif';
          legendItems.forEach((item) => {
            const color = item.color;
            ctx.fillStyle = `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.9)`;
            ctx.fillRect(legendX, legendY, 14, 14);
            ctx.fillStyle = theme.text;
            ctx.fillText(item.label, legendX + 18, legendY + 7);
            legendY += 18;
          });
        }
      }
    },

    _renderBoxplot() {
      if (!this.ctx2d || !this._data || !Array.isArray(this._data.series)) return;
      const series = this._data.series.filter((s) => s && s.stats);
      if (!series.length) return;
      const theme = this._getTheme();
      const ctx = this.ctx2d;
      const dpr = window.devicePixelRatio || 1;
      const width = this.canvas.width / dpr;
      const height = this.canvas.height / dpr;
      const pad = { ...this._padding, bottom: Math.max(this._padding.bottom, 200) };
      const plotWidth = width - pad.left - pad.right;
      const plotHeight = height - pad.top - pad.bottom;

      ctx.clearRect(0, 0, width, height);

      let yMin = Infinity;
      let yMax = -Infinity;
      for (const s of series) {
        const stats = s.stats;
        yMin = Math.min(yMin, stats.min);
        yMax = Math.max(yMax, stats.max);
      }
      if (!isFinite(yMin)) yMin = 0;
      if (!isFinite(yMax)) yMax = 1;
      const yPad = (yMax - yMin) * 0.1 || 5;
      yMin = yMin - yPad;
      yMax = yMax + yPad;
      const yRange = yMax - yMin || 1;
      const yScale = (v) => pad.top + plotHeight - ((v - yMin) / yRange) * plotHeight;

      ctx.strokeStyle = theme.axis;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(pad.left, pad.top);
      ctx.lineTo(pad.left, height - pad.bottom);
      ctx.lineTo(width - pad.right, height - pad.bottom);
      ctx.stroke();

      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = theme.muted;
      ctx.font = '15px sans-serif';
      const yTicks = this._computeTicks(yMin, yMax, 5, false);
      for (const tick of yTicks) {
        const y = yScale(tick);
        ctx.beginPath();
        ctx.moveTo(pad.left - 4, y);
        ctx.lineTo(pad.left, y);
        ctx.stroke();
        ctx.fillText(tick.toFixed(1), pad.left - 6, y);
        ctx.strokeStyle = theme.grid;
        ctx.beginPath();
        ctx.moveTo(pad.left, y);
        ctx.lineTo(width - pad.right, y);
        ctx.stroke();
        ctx.strokeStyle = theme.axis;
      }

      if (this._data.yLabel) {
        ctx.save();
        ctx.translate(12, pad.top + plotHeight / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.fillStyle = theme.muted;
        ctx.font = '16px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText(this._data.yLabel, 0, 0);
        ctx.restore();
      }

      const boxWidth = Math.max(20, Math.min(60, plotWidth / Math.max(series.length * 1.5, 1)));
      const gap = (plotWidth - boxWidth * series.length) / (series.length + 1);
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = theme.text;
      ctx.font = '16px sans-serif';

      series.forEach((s, idx) => {
        const xCenter = pad.left + gap * (idx + 1) + boxWidth * idx + boxWidth / 2;
        const { min, q1, median, q3, max } = s.stats;
        const color = s.color || [99, 179, 237];
        const rgba = `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.85)`;

        const yMinPos = yScale(min);
        const yMaxPos = yScale(max);
        const yQ1 = yScale(q1);
        const yQ3 = yScale(q3);
        const yMedian = yScale(median);

        ctx.strokeStyle = rgba;
        ctx.fillStyle = rgba;
        ctx.lineWidth = 1.5;

        // Whiskers
        ctx.beginPath();
        ctx.moveTo(xCenter, yMaxPos);
        ctx.lineTo(xCenter, yQ3);
        ctx.moveTo(xCenter, yQ1);
        ctx.lineTo(xCenter, yMinPos);
        ctx.stroke();

        // Caps
        ctx.beginPath();
        ctx.moveTo(xCenter - boxWidth * 0.3, yMaxPos);
        ctx.lineTo(xCenter + boxWidth * 0.3, yMaxPos);
        ctx.moveTo(xCenter - boxWidth * 0.3, yMinPos);
        ctx.lineTo(xCenter + boxWidth * 0.3, yMinPos);
        ctx.stroke();

        // Box
        ctx.fillRect(xCenter - boxWidth / 2, yQ3, boxWidth, yQ1 - yQ3);
        ctx.strokeRect(xCenter - boxWidth / 2, yQ3, boxWidth, yQ1 - yQ3);

        // Median line
        ctx.strokeStyle = '#0f172a';
        ctx.beginPath();
        ctx.moveTo(xCenter - boxWidth / 2, yMedian);
        ctx.lineTo(xCenter + boxWidth / 2, yMedian);
        ctx.stroke();

        // Label
        ctx.save();
        ctx.translate(xCenter, height - pad.bottom + 26);
        ctx.rotate(-Math.PI / 4);
        ctx.fillStyle = theme.text;
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        ctx.fillText(s.label || `S${idx + 1}`, 0, 0);
        ctx.restore();
      });
    },

  _renderBars() {
    if (!this.ctx2d || !this._data || !Array.isArray(this._data.categories) || !Array.isArray(this._data.series)) return;
    const categories = this._data.categories;
    const series = this._data.series;
    if (!categories.length || !series.length) return;

    const theme = this._getTheme();
    const ctx = this.ctx2d;
      const dpr = window.devicePixelRatio || 1;
      const width = this.canvas.width / dpr;
      const height = this.canvas.height / dpr;
      const pad = this._padding;
      const plotWidth = width - pad.left - pad.right - 80; // reserve space for legend
      const plotHeight = height - pad.top - pad.bottom;

      ctx.clearRect(0, 0, width, height);

      let yMax = 0;
      for (const s of series) {
        for (const v of s.values) {
          if (v != null && isFinite(v)) {
            if (v > yMax) yMax = v;
          }
        }
      }
      yMax = yMax || 1;
      const yPad = yMax * 0.1;
      const yScale = (v) => pad.top + plotHeight - ((v) / (yMax + yPad)) * plotHeight;

      ctx.strokeStyle = theme.axis;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(pad.left, pad.top);
      ctx.lineTo(pad.left, height - pad.bottom);
      ctx.lineTo(pad.left + plotWidth, height - pad.bottom);
      ctx.stroke();

      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = theme.muted;
      ctx.font = '13px sans-serif';
      const yTicks = this._computeTicks(0, yMax, 5, false);
      for (const tick of yTicks) {
        const y = yScale(tick);
        ctx.beginPath();
        ctx.moveTo(pad.left - 4, y);
        ctx.lineTo(pad.left, y);
        ctx.stroke();
        ctx.fillText(tick.toFixed(1), pad.left - 6, y);
        ctx.strokeStyle = theme.grid;
        ctx.beginPath();
        ctx.moveTo(pad.left, y);
        ctx.lineTo(pad.left + plotWidth, y);
        ctx.stroke();
        ctx.strokeStyle = theme.axis;
      }

      const groupWidth = plotWidth / Math.max(categories.length, 1);
      const barWidth = Math.max(6, Math.min(24, groupWidth / Math.max(series.length, 1) - 4));

      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = theme.text;
      ctx.font = '13px sans-serif';

      categories.forEach((cat, idx) => {
        const groupStart = pad.left + groupWidth * idx + groupWidth * 0.1;
        series.forEach((s, sIdx) => {
          const val = s.values[idx];
          if (val == null || !isFinite(val)) return;
          const color = s.color || [99, 179, 237];
          const x = groupStart + sIdx * (barWidth + 4);
          const y = yScale(val);
          const h = (height - pad.bottom) - y;
          ctx.fillStyle = `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.8)`;
          ctx.fillRect(x, y, barWidth, h);
        });
        ctx.fillStyle = theme.text;
        ctx.fillText(String(cat), groupStart + (barWidth + 4) * series.length / 2, height - pad.bottom + 6);
      });

      // Legend
      const legendX = pad.left + plotWidth + 10;
      let legendY = pad.top;
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.font = '13px sans-serif';
      series.forEach((s) => {
        const color = s.color || [99, 179, 237];
        ctx.fillStyle = `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.9)`;
        ctx.fillRect(legendX, legendY, 14, 14);
        ctx.fillStyle = theme.text;
        ctx.fillText(s.label || 'Series', legendX + 18, legendY + 7);
        legendY += 18;
      });

      if (this._data.yLabel) {
        ctx.save();
        ctx.translate(12, pad.top + plotHeight / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.fillStyle = theme.muted;
        ctx.font = '14px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText(this._data.yLabel, 0, 0);
        ctx.restore();
      }
    },

    _drawLine(ctx, years, seriesData, xScale, yScale, highlighted) {
      const values = seriesData.values;
      const color = seriesData.color || [100, 150, 200, 180];
      ctx.strokeStyle = highlighted
        ? `rgba(${color[0]}, ${color[1]}, ${color[2]}, 1)`
        : `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.5)`;
      ctx.lineWidth = highlighted ? this._highlightWidth : this._lineWidth;
      ctx.beginPath();
      let started = false;
      for (let i = 0; i < years.length; i++) {
        const v = values[i];
        if (v == null || !isFinite(v)) continue;
        const x = xScale(years[i]);
        const y = yScale(v);
        if (!started) {
          ctx.moveTo(x, y);
          started = true;
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.stroke();
    },

    _computeTicks(min, max, count, integers) {
      const range = max - min;
      if (range === 0) return [min];
      const step = range / (count - 1);
      const ticks = [];
      for (let i = 0; i < count; i++) {
        let tick = min + step * i;
        if (integers) tick = Math.round(tick);
        ticks.push(tick);
      }
      return [...new Set(ticks)]; // Remove duplicates
    },

    _getTheme() {
      const root = getComputedStyle(document.documentElement);
      const text = root.getPropertyValue('--wc-color-text').trim() || '#e5e7eb';
      const muted = root.getPropertyValue('--wc-color-text-muted').trim() || '#94a3b8';
      const axis = root.getPropertyValue('--wc-color-border').trim() || '#334155';
      const grid = root.getPropertyValue('--wc-color-border-muted').trim() || 'rgba(148, 163, 184, 0.35)';
      const highlight = root.getPropertyValue('--wc-color-accent').trim() || '#ffcc00';
      return { text, muted, axis, grid, highlight };
    },

    _onCanvasHover(e) {
      if (!this._data || (this._data.type && this._data.type !== 'line')) return;
      if (!this._xScale || !this._plotBounds) return;
      const rect = this.canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const bounds = this._plotBounds;

      if (x < bounds.left || x > bounds.right || y < bounds.top || y > bounds.bottom) {
        this._onCanvasLeave();
        return;
      }

      // Find closest line
      const years = this._data.years;
      const series = this._data.series;
      const seriesIds = Object.keys(series);
      let closestId = null;
      let closestDist = Infinity;
      let closestValue = null;
      let closestYear = null;

      for (const id of seriesIds) {
        const values = series[id].values;
        for (let i = 0; i < years.length; i++) {
          const v = values[i];
          if (v == null || !isFinite(v)) continue;
          const px = this._xScale(years[i]);
          const py = this._yScale(v);
          const dist = Math.sqrt((px - x) ** 2 + (py - y) ** 2);
          if (dist < closestDist && dist < 20) {
            closestDist = dist;
            closestId = id;
            closestValue = v;
            closestYear = years[i];
          }
        }
      }

      if (closestId !== this._hoveredId) {
        this._hoveredId = closestId;
        this.render();
      }

      // Show tooltip
      if (closestId && this.tooltipEl) {
        this.tooltipEl.style.display = 'block';
        this.tooltipEl.style.left = (x + 10) + 'px';
        this.tooltipEl.style.top = (y - 10) + 'px';
        if (this._tooltipFormatter) {
          this.tooltipEl.textContent = this._tooltipFormatter(closestId, closestValue, closestYear);
        } else {
          this.tooltipEl.textContent = `Hillslope ${closestId}: ${closestValue.toFixed(1)}% (${closestYear})`;
        }
      }

      // Emit event for map to highlight
      if (typeof window.glDashboardHighlightSubcatchment === 'function') {
        window.glDashboardHighlightSubcatchment(closestId ? parseInt(closestId, 10) : null);
      }
    },

    _onCanvasLeave() {
      this._hoveredId = null;
      if (this.tooltipEl) {
        this.tooltipEl.style.display = 'none';
      }
      if (this._visible && this._data) {
        this.render();
      }
      // Clear map highlight
      if (typeof window.glDashboardHighlightSubcatchment === 'function') {
        window.glDashboardHighlightSubcatchment(null);
      }
    },
  };

  // Initialize graph controller
  timeseriesGraph.init();

  // Expose for external use
  window.glDashboardTimeseriesGraph = timeseriesGraph;

  // Callback when graph panel is toggled
  window.glDashboardGraphToggled = async function (visible) {
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
  };

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

  async function detectSbsLayer() {
    const url = `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/query/baer_wgs_map`;
    try {
      const resp = await fetch(url);
      if (!resp.ok) {
        return;
      }
      const payload = await resp.json();
      if (!payload || payload.Success !== true || !payload.Content) {
        return;
      }
      let bounds = payload.Content.bounds;
      const imgurl = payload.Content.imgurl;
      if (!bounds || !imgurl) {
        return;
      }
      // Normalize bounds: API returns [[lat1, lon1], [lat2, lon2]]
      if (Array.isArray(bounds) && bounds.length === 2 && Array.isArray(bounds[0]) && Array.isArray(bounds[1])) {
        const [lat1, lon1] = bounds[0];
        const [lat2, lon2] = bounds[1];
        bounds = [lon1, lat1, lon2, lat2];
      }
      if (!Array.isArray(bounds) || bounds.length !== 4 || bounds.some((v) => !Number.isFinite(v))) {
        return;
      }
      // Fetch the PNG so we can sample pixel values on hover.
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
      detectedLayers.push({
        key: 'sbs',
        label: 'SBS Map',
        path: 'query/baer_wgs_map',
        bounds,
        canvas,
        width: canvas.width,
        height: canvas.height,
        values: imgData.data,
        sampleMode: 'rgba',
        visible: false,
      });
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load SBS map', err);
    }
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
    yearSlider.setRange(minYear, maxYear, weppYearlySelectedYear);
    yearSlider.show();
    await refreshWeppYearlyData();
  }

  function updateLayerList() {
    if (!layerListEl) return;
    layerListEl.innerHTML = '';
    const subcatchmentSections = [];
    // Rasters: append specific rasters to Landuse/Soils groups
    const landuseRasters = detectedLayers
      .filter((l) => l.key === 'landuse' || l.key === 'sbs')
      .map((r) => ({ ...r, isRaster: true, rasterRef: r }));
    const soilsRasters = detectedLayers
      .filter((l) => l.key === 'soils')
      .map((r) => ({ ...r, isRaster: true, rasterRef: r }));

    if (landuseLayers.length || landuseRasters.length) {
      subcatchmentSections.push({ title: 'Landuse', items: [...landuseLayers, ...landuseRasters], isSubcatchment: true });
    }
    if (soilsLayers.length || soilsRasters.length) {
      subcatchmentSections.push({ title: 'Soils', items: [...soilsLayers, ...soilsRasters], isSubcatchment: true });
    }
    if (rapLayers.length) {
      // RAP uses special rendering with cumulative mode + checkboxes
      subcatchmentSections.push({ title: 'RAP', items: rapLayers, isSubcatchment: true, isRap: true });
    }
    if (weppLayers.length) {
      subcatchmentSections.push({ title: 'WEPP', items: weppLayers, isSubcatchment: true });
    }
    if (weppYearlyLayers.length) {
      subcatchmentSections.push({ title: 'WEPP Yearly', idPrefix: 'WEPP-Yearly', items: weppYearlyLayers, isSubcatchment: true, isWeppYearly: true });
    }
    if (weppEventLayers.length) {
      // WEPP Event uses special rendering with date input + radio options
      subcatchmentSections.push({ title: 'WEPP Event', items: weppEventLayers, isSubcatchment: true, isWeppEvent: true });
    }
    if (watarLayers.length) {
      subcatchmentSections.push({ title: 'WATAR', items: watarLayers, isSubcatchment: true });
    }
    const allSections = [...subcatchmentSections];
    if (!allSections.length) {
      if (layerEmptyEl) {
        layerEmptyEl.hidden = false;
      }
      return;
    }
    if (layerEmptyEl) {
      layerEmptyEl.hidden = true;
    }
    // Add subcatchment section header if we have any
    if (subcatchmentSections.length) {
      const groupHeader = document.createElement('li');
      groupHeader.className = 'gl-layer-group-header';
      groupHeader.textContent = 'Subcatchment Overlays';
      layerListEl.appendChild(groupHeader);
    }
    allSections.forEach((section, idx) => {
      // Create collapsible details element
      const details = document.createElement('details');
      details.className = 'gl-layer-details';
      // Open the first section by default, or sections with visible items
      const hasVisibleItem = section.items.some((l) => l.visible);
      details.open = idx === 0 || hasVisibleItem || (section.isRap && rapCumulativeMode);

      const summary = document.createElement('summary');
      summary.className = 'gl-layer-group';
      summary.textContent = section.title;
      details.appendChild(summary);

      // Special handling for RAP section
      if (section.isRap) {
        renderRapSection(details, section);
        layerListEl.appendChild(details);
        return;
      }

      // Special handling for WEPP Event section
      if (section.isWeppEvent) {
        renderWeppEventSection(details, section);
        layerListEl.appendChild(details);
        return;
      }

      if (section.title === 'WEPP') {
        const statWrapper = document.createElement('div');
        statWrapper.className = 'gl-wepp-stat';
        statWrapper.innerHTML = `
          <div class="gl-wepp-stat__label">Statistic</div>
          <div class="gl-wepp-stat__options">
            <label><input type="radio" name="wepp-stat" value="mean" ${weppStatistic === 'mean' ? 'checked' : ''}> Mean (Annual Average)</label>
            <label><input type="radio" name="wepp-stat" value="p90" ${weppStatistic === 'p90' ? 'checked' : ''}> 90th Percentile (Risk)</label>
            <label><input type="radio" name="wepp-stat" value="sd" ${weppStatistic === 'sd' ? 'checked' : ''}> Std. Deviation (Variability)</label>
            <label><input type="radio" name="wepp-stat" value="cv" ${weppStatistic === 'cv' ? 'checked' : ''}> CV % (Instability)</label>
          </div>
        `;
        const statInputs = statWrapper.querySelectorAll('input[name="wepp-stat"]');
        statInputs.forEach((inputEl) => {
          inputEl.addEventListener('change', async (event) => {
            const nextStat = event.target.value;
            if (nextStat === weppStatistic) return;
            weppStatistic = nextStat;
            await refreshWeppStatisticData();
          });
        });
        details.appendChild(statWrapper);
      }

      const itemList = document.createElement('ul');
      itemList.className = 'gl-layer-items';

      section.items.forEach((layer) => {
        const li = document.createElement('li');
        li.className = 'gl-layer-item';
        const input = document.createElement('input');
        // Use radio for subcatchment overlays (landuse/soils), checkbox for rasters
        const isRaster = layer.isRaster === true;
        input.type = section.isSubcatchment && !isRaster ? 'radio' : 'checkbox';
        if (section.isSubcatchment && !isRaster) {
          input.name = 'subcatchment-overlay';
        }
        input.checked = layer.visible;
        const idPrefix = section.idPrefix || section.title;
        input.id = `layer-${idPrefix}-${layer.key}`;
        input.addEventListener('change', async () => {
          if (section.isSubcatchment && !isRaster) {
            // Radio behavior: deselect all, then select this one
            deselectAllSubcatchmentOverlays();
            layer.visible = true;
            input.checked = true;
            if (section.isWeppYearly) {
              await activateWeppYearlyLayer();
            }
          } else {
            const target = layer.rasterRef || layer;
            target.visible = input.checked;
            // Keep copied flags in sync so UI reflects state
            layer.visible = input.checked;
          }
          setGraphFocus(false);
          applyLayers();
          const graphEl = document.getElementById('gl-graph');
          const graphVisible = graphEl && !graphEl.classList.contains('is-collapsed');
          if (graphVisible && section.isWeppYearly && layer.visible) {
            await loadWeppYearlyTimeseriesData();
          } else if (graphVisible && !section.isSubcatchment && (rapCumulativeMode || rapLayers.some((l) => l.visible))) {
            // Keep RAP graph in sync when switching out of subcatchment overlays
            await loadRapTimeseriesData();
          }
        });
        const label = document.createElement('label');
        label.setAttribute('for', input.id);
        const name = layer.label || layer.key;
        const path = layer.path || '';
        label.innerHTML = `<span class="gl-layer-name">${name}</span><br><span class="gl-layer-path">${path}</span>`;
        li.appendChild(input);
        li.appendChild(label);
        itemList.appendChild(li);
      });

      details.appendChild(itemList);
      layerListEl.appendChild(details);
    });
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
  function renderRapSection(details, section) {
    const itemList = document.createElement('ul');
    itemList.className = 'gl-layer-items';

    // Cumulative Cover radio option
    const cumulativeLi = document.createElement('li');
    cumulativeLi.className = 'gl-layer-item';
    const cumulativeInput = document.createElement('input');
    cumulativeInput.type = 'radio';
    cumulativeInput.name = 'subcatchment-overlay';
    cumulativeInput.checked = rapCumulativeMode;
    cumulativeInput.id = 'layer-RAP-cumulative';
    cumulativeInput.addEventListener('change', async () => {
      if (cumulativeInput.checked) {
        deselectAllSubcatchmentOverlays();
        rapCumulativeMode = true;
        // Re-check the cumulative radio since deselectAll cleared it
        cumulativeInput.checked = true;
        setGraphFocus(false);
        setGraphCollapsed(false);
        if (rapMetadata && rapMetadata.years && rapMetadata.years.length) {
          const minYear = rapMetadata.years[0];
          const maxYear = rapMetadata.years[rapMetadata.years.length - 1];
          if (!rapSelectedYear || rapSelectedYear < minYear || rapSelectedYear > maxYear) {
            rapSelectedYear = maxYear;
          }
          yearSlider.setRange(minYear, maxYear, rapSelectedYear);
        }
        // Show year slider
        yearSlider.show();
        await refreshRapData();
        applyLayers();
        // Load graph data if graph is visible
        const graphEl = document.getElementById('gl-graph');
        if (graphEl && !graphEl.classList.contains('is-collapsed')) {
          await loadRapTimeseriesData();
        }
      }
    });
    const cumulativeLabel = document.createElement('label');
    cumulativeLabel.setAttribute('for', 'layer-RAP-cumulative');
    cumulativeLabel.innerHTML = '<span class="gl-layer-name">Cumulative Cover</span><br><span class="gl-layer-path">Sum of selected bands (0-100%)</span>';
    cumulativeLi.appendChild(cumulativeInput);
    cumulativeLi.appendChild(cumulativeLabel);
    itemList.appendChild(cumulativeLi);

    // Band checkboxes (indented under cumulative)
    const bandContainer = document.createElement('li');
    bandContainer.style.cssText = 'padding-left: 1.5rem; margin-top: 0.25rem;';
    const bandList = document.createElement('ul');
    bandList.className = 'gl-layer-items';
    bandList.style.cssText = 'gap: 0.15rem;';

    section.items.forEach((layer) => {
      const li = document.createElement('li');
      li.className = 'gl-layer-item';
      const input = document.createElement('input');
      input.type = 'checkbox';
      input.checked = layer.selected !== false; // Default to selected unless explicitly false
      input.id = `layer-RAP-band-${layer.key}`;
      input.addEventListener('change', async () => {
        layer.selected = input.checked;
        if (rapCumulativeMode) {
          await refreshRapData();
          applyLayers();
          // Reload graph data if graph is visible
          const graphEl = document.getElementById('gl-graph');
          if (graphEl && !graphEl.classList.contains('is-collapsed')) {
            await loadRapTimeseriesData();
          }
        }
      });
      const label = document.createElement('label');
      label.setAttribute('for', input.id);
      const name = layer.label || layer.key;
      label.innerHTML = `<span class="gl-layer-name" style="font-size:0.85rem;">${name}</span>`;
      li.appendChild(input);
      li.appendChild(label);
      bandList.appendChild(li);
    });

    bandContainer.appendChild(bandList);
    itemList.appendChild(bandContainer);

    // Individual band radio options (for viewing single bands)
    const separatorLi = document.createElement('li');
    separatorLi.style.cssText = 'border-top: 1px solid #1f2c44; margin: 0.5rem 0; padding: 0;';
    itemList.appendChild(separatorLi);

    const individualHeader = document.createElement('li');
    individualHeader.style.cssText = 'font-size: 0.75rem; color: #6b7fa0; padding: 0.25rem 0;';
    individualHeader.textContent = 'Or view single band:';
    itemList.appendChild(individualHeader);

    section.items.forEach((layer) => {
      const li = document.createElement('li');
      li.className = 'gl-layer-item';
      const input = document.createElement('input');
      input.type = 'radio';
      input.name = 'subcatchment-overlay';
      input.checked = layer.visible && !rapCumulativeMode;
      input.id = `layer-RAP-${layer.key}`;
      input.addEventListener('change', async () => {
        if (input.checked) {
          deselectAllSubcatchmentOverlays();
          rapCumulativeMode = false;
          layer.visible = true;
          input.checked = true;
          setGraphFocus(false);
          setGraphCollapsed(false);
          if (rapMetadata && rapMetadata.years && rapMetadata.years.length) {
            const minYear = rapMetadata.years[0];
            const maxYear = rapMetadata.years[rapMetadata.years.length - 1];
            if (!rapSelectedYear || rapSelectedYear < minYear || rapSelectedYear > maxYear) {
              rapSelectedYear = maxYear;
            }
            yearSlider.setRange(minYear, maxYear, rapSelectedYear);
          }
          // Show year slider
          yearSlider.show();
          // Load data for the selected band
          if (layer.bandId && rapSelectedYear) {
            try {
              const dataPayload = {
                datasets: [{ path: 'rap/rap_ts.parquet', alias: 'rap' }],
                columns: ['rap.topaz_id AS topaz_id', 'rap.value AS value'],
                filters: [
                  { column: 'rap.year', op: '=', value: rapSelectedYear },
                  { column: 'rap.band', op: '=', value: layer.bandId },
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
              console.warn('gl-dashboard: failed to load RAP band data', err);
            }
          }
          applyLayers();
          // Reload graph data if graph is visible
          const graphEl = document.getElementById('gl-graph');
          if (graphEl && !graphEl.classList.contains('is-collapsed')) {
            await loadRapTimeseriesData();
          }
        }
      });
      const label = document.createElement('label');
      label.setAttribute('for', input.id);
      const name = layer.label || layer.key;
      label.innerHTML = `<span class="gl-layer-name">${name}</span><br><span class="gl-layer-path">${layer.path || ''}</span>`;
      li.appendChild(input);
      li.appendChild(label);
      itemList.appendChild(li);
    });

    details.appendChild(itemList);
  }

  /**
   * Render the WEPP Event section with date input + metric radio options.
   */
  function renderWeppEventSection(details, section) {
    const itemList = document.createElement('ul');
    itemList.className = 'gl-layer-items';

    // Date input row
    const dateLi = document.createElement('li');
    dateLi.className = 'gl-layer-item';
    dateLi.style.cssText = 'flex-direction: column; align-items: flex-start; gap: 0.25rem;';
    const dateLabel = document.createElement('label');
    dateLabel.textContent = 'Event Date:';
    dateLabel.style.cssText = 'font-size: 0.85rem; color: #8fa0c2;';
    const dateInput = document.createElement('input');
    dateInput.type = 'date';
    dateInput.id = 'gl-wepp-event-date';
    dateInput.style.cssText = 'width: 100%; padding: 0.25rem; background: #1f2c44; border: 1px solid #3f5070; border-radius: 4px; color: #d0d7e8; font-size: 0.85rem;';
    if (weppEventSelectedDate) {
      dateInput.value = weppEventSelectedDate;
    }
    if (weppEventMetadata && weppEventMetadata.startDate) {
      dateInput.min = weppEventMetadata.startDate;
    }
    if (weppEventMetadata && weppEventMetadata.endDate) {
      dateInput.max = weppEventMetadata.endDate;
    }
    dateInput.addEventListener('change', async () => {
      weppEventSelectedDate = dateInput.value;
      // Reload data for the currently active WEPP Event layer
      const activeLayer = pickActiveWeppEventLayer();
      if (activeLayer && weppEventSelectedDate) {
        await refreshWeppEventData();
        applyLayers();
      }
    });
    dateLi.appendChild(dateLabel);
    dateLi.appendChild(dateInput);
    itemList.appendChild(dateLi);

    // Separator
    const separatorLi = document.createElement('li');
    separatorLi.style.cssText = 'border-top: 1px solid #1f2c44; margin: 0.5rem 0; padding: 0;';
    itemList.appendChild(separatorLi);

    // Radio options for each metric
    section.items.forEach((layer) => {
      const li = document.createElement('li');
      li.className = 'gl-layer-item';
      const input = document.createElement('input');
      input.type = 'radio';
      input.name = 'subcatchment-overlay';
      input.checked = layer.visible;
      input.id = `layer-WEPP-Event-${layer.key}`;
      input.addEventListener('change', async () => {
        if (input.checked) {
          deselectAllSubcatchmentOverlays();
          layer.visible = true;
          input.checked = true;
          setGraphFocus(false);
          // Load data if we have a date selected
          if (weppEventSelectedDate) {
            await refreshWeppEventData();
          }
          applyLayers();
        }
      });
      const label = document.createElement('label');
      label.setAttribute('for', input.id);
      const name = layer.label || layer.key;
      const path = layer.path || '';
      label.innerHTML = `<span class="gl-layer-name">${name}</span><br><span class="gl-layer-path">${path}</span>`;
      li.appendChild(input);
      li.appendChild(label);
      itemList.appendChild(li);
    });

    details.appendChild(itemList);
  }

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
    const activeRasterLayers = detectedLayers
      .filter((layer) => layer.visible)
      .map((layer) => {
        if (layer.imageUrl) {
          const cacheBusted = `${layer.imageUrl}${layer.imageUrl.includes('?') ? '&' : '?'}t=${Date.now()}`;
          return new deck.BitmapLayer({
            id: `raster-${layer.key}`,
            image: cacheBusted,
            bounds: layer.bounds,
            pickable: false,
            opacity: 0.8,
          });
        }
        if (layer.canvas) {
          return new deck.BitmapLayer({
            id: `raster-${layer.key}`,
            image: layer.canvas,
            bounds: layer.bounds,
            pickable: false,
            opacity: 0.8,
          });
        }
        return null;
      })
      .filter(Boolean);
    const landuseDeckLayers = subcatchmentsVisible ? buildLanduseLayers() : [];
    const soilsDeckLayers = subcatchmentsVisible ? buildSoilsLayers() : [];
    const hillslopesDeckLayers = subcatchmentsVisible ? buildHillslopesLayers() : [];
    const watarDeckLayers = subcatchmentsVisible ? buildWatarLayers() : [];
    const weppDeckLayers = subcatchmentsVisible ? buildWeppLayers() : [];
    const weppYearlyDeckLayers = subcatchmentsVisible ? buildWeppYearlyLayers() : [];
    const weppEventDeckLayers = subcatchmentsVisible ? buildWeppEventLayers() : [];
    const rapDeckLayers = subcatchmentsVisible ? buildRapLayers() : [];
    const labelLayers = subcatchmentLabelsVisible && subcatchmentsVisible ? buildSubcatchmentLabelsLayer() : [];
    deckgl.setProps({
      layers: [baseLayer, ...landuseDeckLayers, ...soilsDeckLayers, ...hillslopesDeckLayers, ...watarDeckLayers, ...weppDeckLayers, ...weppYearlyDeckLayers, ...weppEventDeckLayers, ...rapDeckLayers, ...activeRasterLayers, ...labelLayers],
    });
    // Update legends panel after layer changes
    updateLegendsPanel();
  }

  // ============================================================================
  // Legends Panel Rendering
  // ============================================================================

  // SBS burn class colors and labels (matches baer.py / disturbed.py)
  const SBS_CLASSES = [
    { color: '#00734A', label: 'Unburned' },
    { color: '#4DE600', label: 'Low' },
    { color: '#FFFF00', label: 'Moderate' },
    { color: '#FF0000', label: 'High' },
  ];

  // Units for continuous layers
  const LAYER_UNITS = {
    cancov: '%',
    inrcov: '%',
    rilcov: '%',
    clay: '%',
    sand: '%',
    rock: '%',
    bd: 'g/cm³',
    slope_scalar: 'rise/run',
    length: 'm',
    aspect: '°',
    runoff_volume: 'mm',
    subrunoff_volume: 'mm',
    baseflow_volume: 'mm',
    soil_loss: 't/ha',
    sediment_deposition: 't/ha',
    sediment_yield: 't/ha',
    wind_transport: 't/ha',
    water_transport: 't/ha',
    ash_transport: 't/ha',
    // WEPP Event metrics
    event_P: 'mm',
    event_Q: 'mm',
    event_ET: 'mm',
    event_peakro: 'm³/s',
    event_tdet: 'kg',
  };

  // RAP band units
  const RAP_UNITS = {
    afgc: '%',
    pfgc: '%',
    tree: '%',
    shr: '%',
    bgr: '%',
    ltr: '%',
  };

  function getActiveLayerForLegend() {
    // Find the first visible layer from each category
    const active = [];
    
    if (subcatchmentsVisible) {
      // Landuse
      for (const layer of landuseLayers) {
        if (layer.visible) {
          active.push({ ...layer, category: 'Landuse' });
          break;
        }
      }
      // Soils
      for (const layer of soilsLayers) {
        if (layer.visible) {
          active.push({ ...layer, category: 'Soils' });
          break;
        }
      }
      // Hillslopes/Watershed
      for (const layer of hillslopesLayers) {
        if (layer.visible) {
          active.push({ ...layer, category: 'Watershed' });
          break;
        }
      }
      // RAP - handle cumulative mode
      if (rapCumulativeMode) {
        const selectedBands = rapLayers.filter((l) => l.selected !== false);
        const bandNames = selectedBands.map((l) => RAP_BAND_LABELS[l.bandKey] || l.bandKey).join(' + ');
        active.push({
          key: 'rap-cumulative',
          label: `Cumulative Cover (${bandNames})`,
          category: 'RAP',
          isCumulative: true,
        });
      } else {
        for (const layer of rapLayers) {
          if (layer.visible) {
            active.push({ ...layer, category: 'RAP' });
            break;
          }
        }
      }
      // WEPP
      for (const layer of weppLayers) {
        if (layer.visible) {
          active.push({ ...layer, category: 'WEPP' });
          break;
        }
      }
      // WEPP Yearly
      for (const layer of weppYearlyLayers) {
        if (layer.visible) {
          active.push({ ...layer, category: 'WEPP Yearly' });
          break;
        }
      }
      // WEPP Event
      for (const layer of weppEventLayers) {
        if (layer.visible) {
          active.push({ ...layer, category: 'WEPP Event' });
          break;
        }
      }
      // WATAR
      for (const layer of watarLayers) {
        if (layer.visible) {
          active.push({ ...layer, category: 'WATAR' });
          break;
        }
      }
    }
    // Raster layers (SBS, etc.)
    for (const layer of detectedLayers) {
      if (layer.visible) {
        active.push({ ...layer, category: 'Raster' });
      }
    }
    return active;
  }

  function computeRangeFromSummary(summary, mode) {
    if (!summary) return { min: 0, max: 100 };
    let min = Infinity;
    let max = -Infinity;
    for (const key of Object.keys(summary)) {
      const row = summary[key];
      const v = Number(row[mode]);
      if (Number.isFinite(v)) {
        if (v < min) min = v;
        if (v > max) max = v;
      }
    }
    if (!Number.isFinite(min)) min = 0;
    if (!Number.isFinite(max)) max = 100;
    if (max <= min) max = min + 1;
    return { min, max };
  }

  function formatLegendValue(value, decimals = 1) {
    if (!Number.isFinite(value)) return '—';
    return value.toFixed(decimals);
  }

  function getUsedNlcdClasses(layer) {
    // Extract unique NLCD classes from the raster values array
    const classes = new Set();
    if (!layer || !layer.values) return [];
    const values = layer.values;
    for (let i = 0; i < values.length; i++) {
      const v = values[i];
      if (Number.isFinite(v) && v > 0 && NLCD_COLORMAP[v]) {
        classes.add(v);
      }
    }
    // Sort numerically and return as legend items
    return Array.from(classes).sort((a, b) => a - b).map(code => ({
      color: NLCD_COLORMAP[code],
      label: NLCD_LABELS[code] || `Class ${code}`,
    }));
  }

  function getUsedSoilClasses(layer) {
    // Extract unique soil codes from the SSURGO raster values array
    // and try to match them with soilsSummary for labels
    const codes = new Set();
    if (!layer || !layer.values) return [];
    const values = layer.values;
    for (let i = 0; i < values.length; i++) {
      const v = values[i];
      if (Number.isFinite(v) && v > 0) {
        codes.add(v);
      }
    }
    if (codes.size === 0) return [];
    
    // Build a map from mukey integer prefix to soil info from soilsSummary
    const mukeyToInfo = new Map();
    if (soilsSummary) {
      for (const topazId of Object.keys(soilsSummary)) {
        const row = soilsSummary[topazId];
        if (!row || !row.mukey) continue;
        // mukey format: "762983-loam-forest" - extract the numeric prefix
        const mukeyParts = String(row.mukey).split('-');
        const mukeyNum = parseInt(mukeyParts[0], 10);
        if (Number.isFinite(mukeyNum) && !mukeyToInfo.has(mukeyNum)) {
          mukeyToInfo.set(mukeyNum, {
            desc: row.simple_texture || row.desc || `Soil ${mukeyNum}`,
            mukey: row.mukey,
          });
        }
      }
    }
    
    // Sort numerically and return as legend items
    return Array.from(codes).sort((a, b) => a - b).map(code => {
      const color = soilColorForValue(code);
      const label = String(code);
      return { color, label };
    });
  }

  function getUsedLanduseClasses() {
    // Extract unique landuse classes from landuseSummary with their color and description
    const classMap = new Map(); // key -> { color, desc }
    if (!landuseSummary) return classMap;
    for (const topazId of Object.keys(landuseSummary)) {
      const row = landuseSummary[topazId];
      if (!row) continue;
      const key = row.key ?? row._map;
      if (key == null) continue;
      if (classMap.has(key)) continue;
      // Extract color and description
      const color = row.color;
      const desc = row.desc || `Class ${key}`;
      classMap.set(key, { color, desc });
    }
    return classMap;
  }

  function getUsedSoilsClasses() {
    // Extract unique soil classes from soilsSummary with their color and description
    // Deduplicate by mukey (e.g., "762991-silt loam-forest")
    const classMap = new Map(); // mukey -> { color, desc }
    if (!soilsSummary) return classMap;
    for (const topazId of Object.keys(soilsSummary)) {
      const row = soilsSummary[topazId];
      if (!row) continue;
      const mukey = row.mukey;
      if (mukey == null) continue;
      if (classMap.has(mukey)) continue;
      // Extract color and description
      const color = row.color;
      const desc = row.desc || mukey;
      classMap.set(mukey, { color, desc });
    }
    return classMap;
  }

  function rgbaArrayToCss(colorArr, alphaOverride) {
    if (!Array.isArray(colorArr) || colorArr.length < 3) return null;
    const r = Number(colorArr[0]);
    const g = Number(colorArr[1]);
    const b = Number(colorArr[2]);
    const a = alphaOverride != null ? alphaOverride : (colorArr[3] != null ? Number(colorArr[3]) / 255 : 1);
    if (![r, g, b].every(Number.isFinite)) return null;
    return `rgba(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)}, ${a.toFixed(2)})`;
  }

  function renderCategoricalLegend(items) {
    const container = document.createElement('div');
    container.className = 'gl-legend-categorical';
    for (const item of items) {
      const row = document.createElement('div');
      row.className = 'gl-legend-categorical__item';
      const swatch = document.createElement('span');
      swatch.className = 'gl-legend-categorical__swatch';
      swatch.style.backgroundColor = item.color;
      const label = document.createElement('span');
      label.textContent = item.label;
      row.appendChild(swatch);
      row.appendChild(label);
      container.appendChild(row);
    }
    return container;
  }

  function renderContinuousLegend(minVal, maxVal, unit, colormap) {
    const container = document.createElement('div');
    container.className = 'gl-legend-continuous';
    
    const barWrapper = document.createElement('div');
    barWrapper.className = 'gl-legend-continuous__bar-wrapper';
    const bar = document.createElement('div');
    // Apply appropriate colormap class
    let barClass = 'gl-legend-continuous__bar';
    if (colormap === 'winter') {
      barClass += ' gl-legend-continuous__bar--winter';
    } else if (colormap === 'jet2') {
      barClass += ' gl-legend-continuous__bar--jet2';
    }
    bar.className = barClass;
    barWrapper.appendChild(bar);
    container.appendChild(barWrapper);
    
    const labels = document.createElement('div');
    labels.className = 'gl-legend-continuous__labels';
    const minLabel = document.createElement('span');
    minLabel.textContent = formatLegendValue(minVal);
    const maxLabel = document.createElement('span');
    maxLabel.textContent = formatLegendValue(maxVal);
    labels.appendChild(minLabel);
    labels.appendChild(maxLabel);
    container.appendChild(labels);
    
    if (unit) {
      const unitEl = document.createElement('div');
      unitEl.className = 'gl-legend-continuous__unit';
      unitEl.textContent = unit;
      container.appendChild(unitEl);
    }
    
    return container;
  }

  // Diverging legend for comparison mode (blue-white-red)
  // mode parameter allows looking up the computed difference range
  function renderDivergingLegend(unit, label, mode, rangeOverride) {
    const container = document.createElement('div');
    container.className = 'gl-legend-continuous gl-legend-diverging';
    
    const barWrapper = document.createElement('div');
    barWrapper.className = 'gl-legend-continuous__bar-wrapper';
    const bar = document.createElement('div');
    bar.className = 'gl-legend-continuous__bar gl-legend-diverging__bar';
    // Blue (#2166AC) -> White -> Red (#B2182B) gradient
    bar.style.background = 'linear-gradient(to right, #2166AC, #F7F7F7 50%, #B2182B)';
    barWrapper.appendChild(bar);
    container.appendChild(barWrapper);
    
    // Get the computed difference range for this mode
    const range = rangeOverride || (mode ? comparisonDiffRanges[mode] : null);
    const hasRange = range && Number.isFinite(range.min) && Number.isFinite(range.max);
    
    /**
     * Format a numeric value for legend display.
     * Uses appropriate precision based on magnitude.
     */
    function formatLegendValue(val) {
      const absVal = Math.abs(val);
      if (absVal >= 10000) return val.toFixed(0);
      if (absVal >= 100) return val.toFixed(1);
      if (absVal >= 1) return val.toFixed(2);
      return val.toFixed(3);
    }
    
    const labels = document.createElement('div');
    labels.className = 'gl-legend-continuous__labels';
    labels.style.justifyContent = 'space-between';
    
    const leftLabel = document.createElement('span');
    if (hasRange) {
      // Show min value (negative = scenario higher)
      leftLabel.textContent = formatLegendValue(range.min);
    } else {
      leftLabel.textContent = 'Scenario > Base';
    }
    leftLabel.style.color = '#2166AC';
    
    const centerLabel = document.createElement('span');
    centerLabel.textContent = '0';
    centerLabel.style.color = 'var(--gl-text-secondary, #8fa0c2)';
    
    const rightLabel = document.createElement('span');
    if (hasRange) {
      // Show max value (positive = base higher)
      rightLabel.textContent = '+' + formatLegendValue(range.max);
    } else {
      rightLabel.textContent = 'Base > Scenario';
    }
    rightLabel.style.color = '#B2182B';
    
    labels.appendChild(leftLabel);
    labels.appendChild(centerLabel);
    labels.appendChild(rightLabel);
    container.appendChild(labels);
    
    if (unit) {
      const unitEl = document.createElement('div');
      unitEl.className = 'gl-legend-continuous__unit';
      unitEl.textContent = `Difference (${unit})`;
      container.appendChild(unitEl);
    }
    
    if (label) {
      const labelEl = document.createElement('div');
      labelEl.style.cssText = 'font-size:0.7rem;color:var(--gl-text-secondary, #8fa0c2);margin-top:4px;text-align:center;';
      labelEl.textContent = label;
      container.appendChild(labelEl);
    }
    
    return container;
  }

  // Aspect legend using swatches for cardinal directions (HSL hue wheel)
  function renderAspectLegend() {
    // Cardinal/intercardinal directions with degrees (0=N, 90=E, 180=S, 270=W)
    const directions = [
      { label: 'N (0°)', degrees: 0 },
      { label: 'NE (45°)', degrees: 45 },
      { label: 'E (90°)', degrees: 90 },
      { label: 'SE (135°)', degrees: 135 },
      { label: 'S (180°)', degrees: 180 },
      { label: 'SW (225°)', degrees: 225 },
      { label: 'W (270°)', degrees: 270 },
      { label: 'NW (315°)', degrees: 315 },
    ];
    
    // Convert aspect degrees to RGB using same logic as hillslopesFillColor
    function aspectToRgb(degrees) {
      const hue = degrees % 360;
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
      return `rgb(${Math.round(r + 55)}, ${Math.round(g + 55)}, ${Math.round(b + 55)})`;
    }
    
    const items = directions.map(d => ({
      label: d.label,
      color: aspectToRgb(d.degrees)
    }));
    
    return renderCategoricalLegend(items);
  }

  function renderLegendForLayer(layer) {
    const section = document.createElement('div');
    section.className = 'gl-legend-section';
    
    const title = document.createElement('h5');
    title.className = 'gl-legend-section__title';
    title.textContent = layer.label || layer.key;
    section.appendChild(title);

    // Determine legend type based on layer mode
    const mode = layer.mode || '';
    
    // Check if this is comparison mode for a comparison-enabled measure
    const isComparisonMeasure = COMPARISON_MEASURES.includes(mode);
    const diffRangeOverride = layer.category === 'WEPP Yearly' ? weppYearlyDiffRanges[mode] : null;
    const divergingMode = diffRangeOverride ? mode : (layer.category === 'WEPP Yearly' ? null : mode);
    if (comparisonMode && isComparisonMeasure && currentScenarioPath) {
      // Render diverging legend for comparison mode
      const unit = LAYER_UNITS[mode] || '';
      section.appendChild(renderDivergingLegend(unit, 'Base − Scenario', divergingMode, diffRangeOverride));
      return section;
    }
    
    // Categorical: dominant landuse
    if (mode === 'dominant' && layer.category === 'Landuse') {
      const classMap = getUsedLanduseClasses();
      const items = [];
      for (const [key, info] of classMap.entries()) {
        // Color is a hex string from API (e.g., "#1c6330")
        const colorCss = info.color || '#888888';
        items.push({ color: colorCss, label: info.desc || `Class ${key}` });
      }
      if (items.length) {
        section.appendChild(renderCategoricalLegend(items));
      }
      return section;
    }
    
    // Categorical: dominant soil
    if (mode === 'dominant' && layer.category === 'Soils') {
      const classMap = getUsedSoilsClasses();
      const items = [];
      for (const [mukey, info] of classMap.entries()) {
        // Color is a hex string from API (e.g., "#d11141")
        const colorCss = info.color || '#888888';
        items.push({ color: colorCss, label: info.desc || mukey });
      }
      if (items.length) {
        section.appendChild(renderCategoricalLegend(items));
      }
      return section;
    }
    
    // NLCD raster (landuse/nlcd.tif)
    if (layer.key === 'landuse' && layer.category === 'Raster') {
      const nlcdItems = getUsedNlcdClasses(layer);
      if (nlcdItems.length) {
        section.appendChild(renderCategoricalLegend(nlcdItems));
      } else {
        const note = document.createElement('p');
        note.style.cssText = 'font-size:0.75rem;color:#8fa0c2;margin:0;';
        note.textContent = 'NLCD land cover classes';
        section.appendChild(note);
      }
      return section;
    }
    
    // SSURGO raster (soils/ssurgo.tif)
    if (layer.key === 'soils' && layer.category === 'Raster') {
      const soilItems = getUsedSoilClasses(layer);
      if (soilItems.length) {
        section.appendChild(renderCategoricalLegend(soilItems));
      } else {
        const note = document.createElement('p');
        note.style.cssText = 'font-size:0.75rem;color:#8fa0c2;margin:0;';
        note.textContent = 'SSURGO soil types';
        section.appendChild(note);
      }
      return section;
    }
    
    // SBS raster
    if (layer.key === 'sbs') {
      section.appendChild(renderCategoricalLegend(SBS_CLASSES));
      return section;
    }
    
    // Continuous layers
    let minVal = 0;
    let maxVal = 100;
    let unit = LAYER_UNITS[mode] || '';
    
    // Landuse cover layers (0-1 range in data, colormap uses value directly)
    if (['cancov', 'inrcov', 'rilcov'].includes(mode)) {
      minVal = 0;
      maxVal = 100;
      unit = '%';
    }
    // Soils continuous - use colormap normalization ranges, not data ranges
    else if (['clay', 'sand', 'rock'].includes(mode) && soilsSummary) {
      minVal = 0;
      maxVal = 100;
      unit = '%';
    }
    else if (mode === 'bd' && soilsSummary) {
      minVal = 0.5;
      maxVal = 2.0;
      unit = 'g/cm³';
    }
    else if (mode === 'soil_depth' && soilsSummary) {
      minVal = 0;
      maxVal = 2000;
      unit = 'mm';
    }
    // Hillslopes/Watershed continuous - use HILLSLOPES_RANGES constants
    else if (mode === 'slope_scalar' && hillslopesSummary) {
      minVal = 0;
      maxVal = 100;  // HILLSLOPES_RANGES.slope_scalar is 0-1, display as %
      unit = '%';
    }
    else if (mode === 'length' && hillslopesSummary) {
      minVal = 0;
      maxVal = 1000;  // HILLSLOPES_RANGES.length
      unit = 'm';
    }
    else if (mode === 'aspect' && hillslopesSummary) {
      // Aspect uses a circular hue colormap - render as swatches
      section.appendChild(renderAspectLegend());
      return section;
    }
    // WATAR layers - dynamic ranges
    else if (watarRanges && watarRanges[mode]) {
      minVal = watarRanges[mode].min;
      maxVal = watarRanges[mode].max;
    }
    // WEPP layers - these use dynamic data ranges, which is correct
    else if (weppRanges && weppRanges[mode]) {
      minVal = weppRanges[mode].min;
      maxVal = weppRanges[mode].max;
    }
    else if (weppYearlyRanges && weppYearlyRanges[mode]) {
      minVal = weppYearlyRanges[mode].min;
      maxVal = weppYearlyRanges[mode].max;
    }
    // WEPP Event layers - use dynamic weppEventRanges
    else if (weppEventRanges && weppEventRanges[mode]) {
      minVal = weppEventRanges[mode].min;
      maxVal = weppEventRanges[mode].max;
      unit = LAYER_UNITS[mode] || '';
    }
    // RAP cumulative mode - use 0-100% (clamped at colormap level)
    else if (layer.isCumulative) {
      minVal = 0;
      maxVal = 100;
      unit = '%';
    }
    // RAP layers - use 0-100% (rapFillColor normalizes by /100)
    else if (layer.bandKey && rapSummary) {
      minVal = 0;
      maxVal = 100;
      unit = '%';
    }
    
    // Determine colormap based on measure type
    let colormap = 'viridis';  // default
    if (WATER_MEASURES.includes(mode)) {
      colormap = 'winter';
    } else if (SOIL_MEASURES.includes(mode)) {
      colormap = 'jet2';
    } else if (layer.category === 'WATAR') {
      colormap = 'jet2';
    }
    
    section.appendChild(renderContinuousLegend(minVal, maxVal, unit, colormap));
    return section;
  }

  function updateLegendsPanel() {
    const contentEl = document.getElementById('gl-legends-content');
    const emptyEl = document.getElementById('gl-legend-empty');
    if (!contentEl) return;

    const activeLayers = getActiveLayerForLegend();
    
    // Clear existing content except empty message
    const children = Array.from(contentEl.children);
    for (const child of children) {
      if (child.id !== 'gl-legend-empty') {
        child.remove();
      }
    }
    
    if (!activeLayers.length) {
      if (emptyEl) emptyEl.style.display = '';
      return;
    }
    
    if (emptyEl) emptyEl.style.display = 'none';
    
    for (const layer of activeLayers) {
      const legendSection = renderLegendForLayer(layer);
      contentEl.appendChild(legendSection);
    }
  }

  // Expose for external use
  window.glDashboardUpdateLegends = updateLegendsPanel;

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

  // WATAR (ash transport) overlays
  function computeWatarRanges() {
    if (!watarSummary) return;
    const modes = ['wind_transport', 'water_transport', 'ash_transport'];
    watarRanges = {};
    for (const mode of modes) {
      let min = Infinity;
      let max = -Infinity;
      for (const key of Object.keys(watarSummary)) {
        const row = watarSummary[key];
        const v = Number(row[mode]);
        if (Number.isFinite(v)) {
          if (v < min) min = v;
          if (v > max) max = v;
        }
      }
      if (!Number.isFinite(min)) min = 0;
      if (!Number.isFinite(max)) max = 1;
      if (max <= min) max = min + 1;
      watarRanges[mode] = { min, max };
    }
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

  // RAP band labels for display
  const RAP_BAND_LABELS = {
    annual_forb_grass: 'Annual Forb & Grass',
    bare_ground: 'Bare Ground',
    litter: 'Litter',
    perennial_forb_grass: 'Perennial Forb & Grass',
    shrub: 'Shrub',
    tree: 'Tree',
  };

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
    if (!rapCumulativeMode && !rapLayers.some((l) => l.visible)) {
      timeseriesGraph.hide();
      return;
    }

    const selectedBands = rapCumulativeMode
      ? rapLayers.filter((l) => l.selected !== false)
      : [pickActiveRapLayer()].filter(Boolean);

    if (!selectedBands.length) {
      timeseriesGraph.hide();
      return;
    }

    try {
      const bandIds = selectedBands.map((l) => l.bandId);
      // Query all years for selected bands
      const dataPayload = {
        datasets: [{ path: 'rap/rap_ts.parquet', alias: 'rap' }],
        columns: ['rap.topaz_id AS topaz_id', 'rap.year AS year', 'rap.band AS band', 'rap.value AS value'],
        filters: [{ column: 'rap.band', op: 'IN', value: bandIds }],
        order_by: ['year'],
      };
      const dataResult = await postQueryEngine(dataPayload);
      if (!dataResult || !dataResult.records || dataResult.records.length === 0) {
        timeseriesGraph.hide();
        return;
      }

      // Build series data structure
      // { years: [2016, 2017, ...], series: { topazId: { values: [...], color: [r,g,b,a] } } }
      const yearSet = new Set();
      const rawData = {}; // { topazId: { year: sumValue } }

      for (const row of dataResult.records) {
        const tid = String(row.topaz_id);
        const year = row.year;
        const value = row.value || 0;
        yearSet.add(year);

        if (!rawData[tid]) {
          rawData[tid] = {};
        }
        // Sum values if cumulative mode (multiple bands per year)
        rawData[tid][year] = (rawData[tid][year] || 0) + value;
      }

      const years = Array.from(yearSet).sort((a, b) => a - b);
      const series = {};

      // Compute min/max for color mapping
      let minVal = Infinity, maxVal = -Infinity;
      for (const tid of Object.keys(rawData)) {
        for (const yr of years) {
          const v = rawData[tid][yr];
          if (v != null && isFinite(v)) {
            if (v < minVal) minVal = v;
            if (v > maxVal) maxVal = v;
          }
        }
      }
      if (!isFinite(minVal)) minVal = 0;
      if (!isFinite(maxVal)) maxVal = 100;
      const valRange = maxVal - minVal || 1;

      // Build series with colors matching the map's colormap
      for (const tid of Object.keys(rawData)) {
        const values = years.map((yr) => rawData[tid][yr] ?? null);
        // Use the latest value for color assignment (or average)
        const latestVal = values.filter((v) => v != null).pop() || 0;
        const normalized = Math.min(1, Math.max(0, (latestVal - minVal) / valRange));
        const color = viridisColor(normalized);
        series[tid] = { values, color };
      }

      const bandLabel = rapCumulativeMode
        ? 'Cumulative (' + selectedBands.map((l) => RAP_BAND_LABELS[l.bandKey] || l.bandKey).join('+') + ')'
        : RAP_BAND_LABELS[selectedBands[0].bandKey] || selectedBands[0].bandKey;

      timeseriesGraph.setData({
        years,
        series,
        xLabel: 'Year',
        yLabel: bandLabel + ' %',
        currentYear: rapSelectedYear,
        source: 'rap',
        tooltipFormatter: (id, value, yr) => {
          const numeric = Number.isFinite(value) ? value.toFixed(1) : value;
          return `Hillslope ${id}: ${numeric}% (${yr}) — ${bandLabel}`;
        },
      });
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load RAP timeseries', err);
      timeseriesGraph.hide();
    }
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
    const overlay = pickActiveWeppYearlyLayer();
    if (!overlay || !weppYearlyMetadata || !weppYearlyMetadata.years || !weppYearlyMetadata.years.length) {
      timeseriesGraph.hide();
      return;
    }

    try {
      const valueColumn = WEPP_YEARLY_COLUMN_MAP[overlay.mode] || overlay.mode;
      const dataPayload = {
        datasets: [
          { path: WEPP_YEARLY_PATH, alias: 'loss' },
          { path: 'watershed/hillslopes.parquet', alias: 'hill' },
        ],
        joins: [{ left: 'loss', right: 'hill', on: 'wepp_id', type: 'inner' }],
        columns: ['hill.topaz_id AS topaz_id', 'loss.year AS year', `loss.${valueColumn} AS value`],
        order_by: ['year'],
      };
      const dataResult = await postQueryEngine(dataPayload);
      if (!dataResult || !dataResult.records || dataResult.records.length === 0) {
        timeseriesGraph.hide();
        return;
      }

      const yearSet = new Set();
      const rawData = {};
      for (const row of dataResult.records) {
        const tid = String(row.topaz_id);
        const year = row.year;
        const value = row.value;
        if (!Number.isFinite(value)) continue;
        yearSet.add(year);
        if (!rawData[tid]) rawData[tid] = {};
        rawData[tid][year] = value;
      }

      const years = Array.from(yearSet).sort((a, b) => a - b);
      if (!years.length) {
        timeseriesGraph.hide();
        return;
      }

      let minVal = Infinity;
      let maxVal = -Infinity;
      for (const tid of Object.keys(rawData)) {
        for (const yr of years) {
          const v = rawData[tid][yr];
          if (v != null && isFinite(v)) {
            if (v < minVal) minVal = v;
            if (v > maxVal) maxVal = v;
          }
        }
      }
      if (!isFinite(minVal)) minVal = 0;
      if (!isFinite(maxVal)) maxVal = 1;
      const range = maxVal - minVal || 1;

      const series = {};
      for (const tid of Object.keys(rawData)) {
        const values = years.map((yr) => (rawData[tid][yr] != null ? rawData[tid][yr] : null));
        const latestVal = values.filter((v) => v != null).pop() || 0;
        const normalized = Math.min(1, Math.max(0, (latestVal - minVal) / range));
        const color = weppYearlyGraphColor(normalized, overlay.mode);
        series[tid] = { values, color };
      }

      const tooltipFormatter = (id, value, yr) => {
        const label = overlay.label || overlay.mode;
        const numeric = Number.isFinite(value) ? value.toFixed(2) : value;
        return `Hillslope ${id}: ${numeric} (${yr}) — ${label}`;
      };

      timeseriesGraph.setData({
        years,
        series,
        xLabel: 'Year',
        yLabel: overlay.label || overlay.mode,
        currentYear: weppYearlySelectedYear,
        source: 'wepp_yearly',
        tooltipFormatter,
      });
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load WEPP yearly timeseries', err);
      timeseriesGraph.hide();
    }
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

  function computeBoundsFromGdal(info) {
    const wgs84 = info && info.wgs84Extent && info.wgs84Extent.coordinates;
    if (Array.isArray(wgs84) && wgs84.length && Array.isArray(wgs84[0])) {
      const ring = wgs84[0];
      let west = Infinity;
      let south = Infinity;
      let east = -Infinity;
      let north = -Infinity;
      for (const pt of ring) {
        if (!Array.isArray(pt) || pt.length < 2) continue;
        const [lon, lat] = pt;
        if (!Number.isFinite(lon) || !Number.isFinite(lat)) continue;
        if (lon < west) west = lon;
        if (lon > east) east = lon;
        if (lat < south) south = lat;
        if (lat > north) north = lat;
      }
      if ([west, south, east, north].every((v) => Number.isFinite(v))) {
        return [west, south, east, north];
      }
    }
    const cc = info && info.cornerCoordinates;
    if (!cc) return null;
    const ll = cc.lowerLeft || cc.lowerleft || cc.LowerLeft;
    const ur = cc.upperRight || cc.upperright || cc.UpperRight;
    if (!ll || !ur) return null;
    const west = Math.min(ll[0], ur[0]);
    const east = Math.max(ll[0], ur[0]);
    const south = Math.min(ll[1], ur[1]);
    const north = Math.max(ll[1], ur[1]);
    if (![west, south, east, north].every(Number.isFinite)) return null;
    return [west, south, east, north];
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
    await detectSbsLayer();
    for (const def of layerDefs) {
      let found = null;
      for (const path of def.paths) {
        try {
          const info = await fetchGdalInfo(path);
          if (!info) continue;
          const bounds = computeBoundsFromGdal(info);
          if (!bounds) continue;
          const colorMap = def.key === 'landuse' ? NLCD_COLORMAP : def.key === 'soils' ? soilColorForValue : null;
          const raster = await fetchRasterCanvas(path, colorMap);
          found = {
            key: def.key,
            label: def.label,
            path,
            bounds,
            canvas: raster.canvas,
            width: raster.width,
            height: raster.height,
            values: raster.values,
            sampleMode: raster.sampleMode,
            visible: false,
          };
          break;
        } catch (err) {
          // eslint-disable-next-line no-console
          console.warn(`gl-dashboard: failed to load ${def.label} at ${path}`, err);
        }
      }
      if (found) {
        detectedLayers.push(found);
      }
    }
    updateLayerList();
    applyLayers();
    // Don't zoom here - let detectLanduseOverlays handle it with subcatchments bounds
  }

  async function detectLanduseOverlays() {
    const url = buildScenarioUrl(`query/landuse/subcatchments`);
    // Geometry is shared across scenarios - always use base URL
    const geoUrl = buildBaseUrl(`resources/subcatchments.json`);
    try {
      const [subResp, geoResp] = await Promise.all([fetch(url), fetch(geoUrl)]);
      if (!subResp.ok || !geoResp.ok) return;
      landuseSummary = await subResp.json();
      subcatchmentsGeoJson = await geoResp.json();
      if (!landuseSummary || !subcatchmentsGeoJson) return;
      const basePath = 'landuse/landuse.parquet';
      landuseLayers.length = 0;
      landuseLayers.push(
        { key: 'lu-dominant', label: 'Dominant landuse', path: basePath, mode: 'dominant', visible: true },
        { key: 'lu-cancov', label: 'Canopy cover (cancov)', path: basePath, mode: 'cancov', visible: false },
        { key: 'lu-inrcov', label: 'Interrill cover (inrcov)', path: basePath, mode: 'inrcov', visible: false },
        { key: 'lu-rilcov', label: 'Rill cover (rilcov)', path: basePath, mode: 'rilcov', visible: false },
      );
      updateLayerList();
      applyLayers();
      // Zoom handled by zoomToSubcatchmentBounds after all detection completes
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load landuse overlays', err);
    }
  }

  async function detectSoilsOverlays() {
    const url = buildScenarioUrl(`query/soils/subcatchments`);
    // Geometry is shared across scenarios - always use base URL
    const geoUrl = buildBaseUrl(`resources/subcatchments.json`);
    try {
      const [subResp, geoResp] = await Promise.all([fetch(url), fetch(geoUrl)]);
      if (!subResp.ok || !geoResp.ok) return;
      soilsSummary = await subResp.json();
      // subcatchmentsGeoJson may already be loaded by detectLanduseOverlays
      if (!subcatchmentsGeoJson) {
        subcatchmentsGeoJson = await geoResp.json();
      }
      if (!soilsSummary || !subcatchmentsGeoJson) return;
      const basePath = 'soils/soils.parquet';
      soilsLayers.length = 0;
      soilsLayers.push(
        { key: 'soil-dominant', label: 'Dominant soil (color)', path: basePath, mode: 'dominant', visible: false },
        { key: 'soil-clay', label: 'Clay content (%)', path: basePath, mode: 'clay', visible: false },
        { key: 'soil-sand', label: 'Sand content (%)', path: basePath, mode: 'sand', visible: false },
        { key: 'soil-bd', label: 'Bulk density (g/cm³)', path: basePath, mode: 'bd', visible: false },
        { key: 'soil-rock', label: 'Rock content (%)', path: basePath, mode: 'rock', visible: false },
        { key: 'soil-depth', label: 'Soil depth (mm)', path: basePath, mode: 'soil_depth', visible: false },
      );
      updateLayerList();
      applyLayers();
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load soils overlays', err);
    }
  }

  async function detectHillslopesOverlays() {
    const url = buildScenarioUrl(`query/watershed/subcatchments`);
    // Geometry is shared across scenarios - always use base URL
    const geoUrl = buildBaseUrl(`resources/subcatchments.json`);
    try {
      const [subResp, geoResp] = await Promise.all([fetch(url), fetch(geoUrl)]);
      if (!subResp.ok || !geoResp.ok) return;
      hillslopesSummary = await subResp.json();
      // subcatchmentsGeoJson may already be loaded by detectLanduseOverlays or detectSoilsOverlays
      if (!subcatchmentsGeoJson) {
        subcatchmentsGeoJson = await geoResp.json();
      }
      if (!hillslopesSummary || !subcatchmentsGeoJson) return;
      const basePath = 'watershed/hillslopes.parquet';
      hillslopesLayers.length = 0;
      hillslopesLayers.push(
        { key: 'hillslope-slope', label: 'Slope (rise/run)', path: basePath, mode: 'slope_scalar', visible: false },
        { key: 'hillslope-length', label: 'Hillslope length (m)', path: basePath, mode: 'length', visible: false },
        { key: 'hillslope-aspect', label: 'Aspect (degrees)', path: basePath, mode: 'aspect', visible: false },
      );
      updateLayerList();
      applyLayers();
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load hillslopes overlays', err);
    }
  }

  async function detectWatarOverlays() {
    // Geometry is shared across scenarios - always use base URL
    const geoUrl = buildBaseUrl(`resources/subcatchments.json`);
    try {
      const payload = {
        datasets: [{ path: WATAR_PATH, alias: 'wtr' }],
        columns: [
          'wtr.topaz_id AS topaz_id',
          'wtr."wind_transport (tonne/ha)" AS wind_transport',
          'wtr."water_transport (tonne/ha)" AS water_transport',
          'wtr."ash_transport (tonne/ha)" AS ash_transport',
        ],
      };
      const result = await postQueryEngine(payload);
      if (!result || !result.records || !result.records.length) return;

      watarSummary = {};
      for (const row of result.records) {
        const topazId = row.topaz_id;
        if (topazId != null) {
          watarSummary[String(topazId)] = row;
        }
      }
      computeWatarRanges();

      if (!subcatchmentsGeoJson) {
        const geoResp = await fetch(geoUrl);
        if (geoResp.ok) {
          subcatchmentsGeoJson = await geoResp.json();
        }
      }
      if (!subcatchmentsGeoJson) return;

      watarLayers.length = 0;
      watarLayers.push(
        { key: 'watar-wind', label: 'Wind Transport (tonne/ha)', path: WATAR_PATH, mode: 'wind_transport', visible: false },
        { key: 'watar-water', label: 'Water Transport (tonne/ha)', path: WATAR_PATH, mode: 'water_transport', visible: false },
        { key: 'watar-ash', label: 'Ash Transport (tonne/ha)', path: WATAR_PATH, mode: 'ash_transport', visible: false },
      );

      updateLayerList();
      applyLayers();
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load WATAR overlays', err);
    }
  }

  async function detectWeppOverlays() {
    // Geometry is shared across scenarios - always use base URL
    const geoUrl = buildBaseUrl(`resources/subcatchments.json`);
    try {
      const geoPromise = subcatchmentsGeoJson
        ? Promise.resolve(subcatchmentsGeoJson)
        : fetch(geoUrl).then((resp) => (resp.ok ? resp.json() : null));
      const [weppData, geoJson] = await Promise.all([fetchWeppSummary(weppStatistic), geoPromise]);
      weppSummary = weppData;
      if (!subcatchmentsGeoJson && geoJson) {
        subcatchmentsGeoJson = geoJson;
      }
      if (!weppSummary || !subcatchmentsGeoJson) return;
      // Compute dynamic ranges from the loaded data
      computeWeppRanges();
      const basePath = WEPP_LOSS_PATH;
      weppLayers.length = 0;
      weppLayers.push(
        { key: 'wepp-runoff', label: 'Runoff Volume (mm)', path: basePath, mode: 'runoff_volume', visible: false },
        { key: 'wepp-subrunoff', label: 'Subrunoff Volume (mm)', path: basePath, mode: 'subrunoff_volume', visible: false },
        { key: 'wepp-baseflow', label: 'Baseflow Volume (mm)', path: basePath, mode: 'baseflow_volume', visible: false },
        { key: 'wepp-soil-loss', label: 'Soil Loss (tonnes/ha)', path: basePath, mode: 'soil_loss', visible: false },
        { key: 'wepp-sed-dep', label: 'Sediment Deposition (tonnes/ha)', path: basePath, mode: 'sediment_deposition', visible: false },
        { key: 'wepp-sed-yield', label: 'Sediment Yield (tonnes/ha)', path: basePath, mode: 'sediment_yield', visible: false },
      );
      updateLayerList();
      applyLayers();
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load WEPP overlays', err);
    }
  }

  async function detectWeppYearlyOverlays() {
    // Geometry is shared across scenarios - always use base URL
    const geoUrl = buildBaseUrl(`resources/subcatchments.json`);
    weppYearlyLayers.length = 0;
    weppYearlySummary = null;
    weppYearlyMetadata = null;
    try {
      const yearsPayload = {
        datasets: [{ path: WEPP_YEARLY_PATH, alias: 'loss' }],
        columns: ['DISTINCT loss.year AS year'],
        order_by: ['year'],
      };
      const yearsResult = await postQueryEngine(yearsPayload);
      if (!yearsResult || !yearsResult.records || !yearsResult.records.length) {
        if (!rapCumulativeMode && !rapLayers.some((l) => l.visible)) {
          yearSlider.hide();
        }
        updateLayerList();
        return;
      }

      const years = yearsResult.records
        .map((r) => Number(r.year))
        .filter((y) => Number.isFinite(y))
        .sort((a, b) => a - b);
      if (!years.length) {
        if (!rapCumulativeMode && !rapLayers.some((l) => l.visible)) {
          yearSlider.hide();
        }
        updateLayerList();
        return;
      }

      if (!subcatchmentsGeoJson) {
        const geoResp = await fetch(geoUrl);
        if (geoResp.ok) {
          subcatchmentsGeoJson = await geoResp.json();
        }
      }
      if (!subcatchmentsGeoJson) {
        if (!rapCumulativeMode && !rapLayers.some((l) => l.visible)) {
          yearSlider.hide();
        }
        updateLayerList();
        return;
      }

      weppYearlyMetadata = {
        years,
        minYear: years[0],
        maxYear: years[years.length - 1],
      };
      if (weppYearlySelectedYear == null || weppYearlySelectedYear < weppYearlyMetadata.minYear || weppYearlySelectedYear > weppYearlyMetadata.maxYear) {
        weppYearlySelectedYear = weppYearlyMetadata.maxYear;
      }

      weppYearlyLayers.length = 0;
      weppYearlyLayers.push(
        { key: 'wepp-yearly-runoff', label: 'Runoff Volume (mm)', path: WEPP_YEARLY_PATH, mode: 'runoff_volume', visible: false },
        { key: 'wepp-yearly-subrunoff', label: 'Subrunoff Volume (mm)', path: WEPP_YEARLY_PATH, mode: 'subrunoff_volume', visible: false },
        { key: 'wepp-yearly-baseflow', label: 'Baseflow Volume (mm)', path: WEPP_YEARLY_PATH, mode: 'baseflow_volume', visible: false },
        { key: 'wepp-yearly-soil-loss', label: 'Soil Loss (tonnes/ha)', path: WEPP_YEARLY_PATH, mode: 'soil_loss', visible: false },
        { key: 'wepp-yearly-sed-dep', label: 'Sediment Deposition (tonnes/ha)', path: WEPP_YEARLY_PATH, mode: 'sediment_deposition', visible: false },
        { key: 'wepp-yearly-sed-yield', label: 'Sediment Yield (tonnes/ha)', path: WEPP_YEARLY_PATH, mode: 'sediment_yield', visible: false },
      );

      await refreshWeppYearlyData();
      if (comparisonMode && currentScenarioPath) {
        await loadBaseWeppYearlyData(weppYearlySelectedYear);
        computeWeppYearlyDiffRanges(weppYearlySelectedYear);
      }

      updateLayerList();
      applyLayers();
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load WEPP yearly overlays', err);
    }
  }

  async function detectWeppEventOverlays() {
    // Geometry is shared across scenarios - always use base URL
    const geoUrl = buildBaseUrl(`resources/subcatchments.json`);
    try {
      // Use climate context for date range (already available, avoids slow parquet query)
      const climateCtx = ctx.climate;
      if (!climateCtx || !climateCtx.startYear || !climateCtx.endYear) {
        // eslint-disable-next-line no-console
        console.warn('gl-dashboard: no climate context available for WEPP Event');
        return;
      }

      const minYear = climateCtx.startYear;
      const maxYear = climateCtx.endYear;

      // Set up metadata with date range (using Jan 1 of min year to Dec 31 of max year)
      weppEventMetadata = {
        available: true,
        startDate: `${minYear}-01-01`,
        endDate: `${maxYear}-12-31`,
      };

      // Default to first day of simulation
      if (!weppEventSelectedDate) {
        weppEventSelectedDate = weppEventMetadata.startDate;
      }

      // Ensure subcatchments are loaded
      if (!subcatchmentsGeoJson) {
        const geoResp = await fetch(geoUrl);
        if (geoResp.ok) {
          subcatchmentsGeoJson = await geoResp.json();
        }
      }
      if (!subcatchmentsGeoJson) return;

      // Build layer definitions for WEPP Event metrics
      weppEventLayers.length = 0;
      weppEventLayers.push(
        { key: 'wepp-event-P', label: 'Precipitation (P)', path: 'wepp/output/interchange/H.wat.parquet', mode: 'event_P', visible: false },
        { key: 'wepp-event-Q', label: 'Runoff (Q)', path: 'wepp/output/interchange/H.wat.parquet', mode: 'event_Q', visible: false },
        { key: 'wepp-event-ET', label: 'Total ET (Ep+Es+Er)', path: 'wepp/output/interchange/H.wat.parquet', mode: 'event_ET', visible: false },
        { key: 'wepp-event-peakro', label: 'Peak Runoff Rate', path: 'wepp/output/interchange/H.pass.parquet', mode: 'event_peakro', visible: false },
        { key: 'wepp-event-tdet', label: 'Total Detachment', path: 'wepp/output/interchange/H.pass.parquet', mode: 'event_tdet', visible: false },
      );

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
    const origin = window.location.origin || `${window.location.protocol}//${window.location.host}`;
    // Build scenario-aware query URL
    // For scenarios, the path is the full scenario directory path (e.g., _pups/omni/scenarios/mulch_15)
    let queryPath = `runs/${ctx.runid}`;
    if (currentScenarioPath) {
      // currentScenarioPath is already the full path like '_pups/omni/scenarios/mulch_15'
      queryPath += `/${currentScenarioPath}`;
    }
    const targetUrl = `${origin}/query-engine/${queryPath}/query`;
    const resp = await fetch(targetUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) return null;
    return resp.json();
  }

  async function postBaseQueryEngine(payload) {
    const origin = window.location.origin || `${window.location.protocol}//${window.location.host}`;
    const targetUrl = `${origin}/query-engine/runs/${ctx.runid}/query`;
    const resp = await fetch(targetUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) return null;
    return resp.json();
  }

  async function postQueryEngineForScenario(payload, scenarioPath) {
    const origin = window.location.origin || `${window.location.protocol}//${window.location.host}`;
    let queryPath = `runs/${ctx.runid}`;
    if (scenarioPath) {
      queryPath += `/${scenarioPath}`;
    }
    const targetUrl = `${origin}/query-engine/${queryPath}/query`;
    const resp = await fetch(targetUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) return null;
    return resp.json();
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
    if (!force && graphDataCache[key]) {
      return graphDataCache[key];
    }
    const loader = GRAPH_LOADERS[key];
    if (!loader) return null;
    const data = await loader();
    graphDataCache[key] = data;
    return data;
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
    // Geometry is shared across scenarios - always use base URL
    const geoUrl = buildBaseUrl(`resources/subcatchments.json`);
    try {
      // Query for available years
      const yearsPayload = {
        datasets: [{ path: 'rap/rap_ts.parquet', alias: 'rap' }],
        columns: ['DISTINCT rap.year AS year'],
        order_by: ['year'],
      };
      const yearsResult = await postQueryEngine(yearsPayload);
      if (!yearsResult || !yearsResult.records || !yearsResult.records.length) return;

      // Query for available bands
      const bandsPayload = {
        datasets: [{ path: 'rap/rap_ts.parquet', alias: 'rap' }],
        columns: ['DISTINCT rap.band AS band'],
        order_by: ['band'],
      };
      const bandsResult = await postQueryEngine(bandsPayload);
      if (!bandsResult || !bandsResult.records || !bandsResult.records.length) return;

      const years = yearsResult.records.map((r) => r.year);
      const bands = bandsResult.records.map((r) => r.band);

      // Build rapMetadata from query results
      const RAP_BAND_ID_TO_KEY = {
        1: 'annual_forb_grass',
        2: 'bare_ground',
        3: 'litter',
        4: 'perennial_forb_grass',
        5: 'shrub',
        6: 'tree',
      };
      rapMetadata = {
        available: true,
        years,
        bands: bands.map((id) => ({ id, label: RAP_BAND_ID_TO_KEY[id] || `band_${id}` })),
      };

      // Set default year to most recent
      if (years.length) {
        rapSelectedYear = years[years.length - 1];
      }

      // Ensure subcatchments are loaded
      if (!subcatchmentsGeoJson) {
        const geoResp = await fetch(geoUrl);
        if (geoResp.ok) {
          subcatchmentsGeoJson = await geoResp.json();
        }
      }
      if (!subcatchmentsGeoJson) return;

      // Build layer definitions for each band
      // Default selected: tree and shrub
      const DEFAULT_SELECTED_BANDS = ['tree', 'shrub'];
      const basePath = 'rap/rap_ts.parquet';
      rapLayers.length = 0;
      for (const band of rapMetadata.bands) {
        const label = RAP_BAND_LABELS[band.label] || band.label;
        rapLayers.push({
          key: `rap-${band.label}`,
          label: `${label} (%)`,
          path: basePath,
          bandId: band.id,
          bandKey: band.label,
          visible: false,
          selected: DEFAULT_SELECTED_BANDS.includes(band.label), // For cumulative mode checkboxes
        });
      }

      // Sync year slider with RAP years if available
      if (years.length) {
        const minYear = years[0];
        const maxYear = years[years.length - 1];
        yearSlider.setRange(minYear, maxYear, rapSelectedYear);
      }

      // Load initial data for the first band via query-engine
      if (rapLayers.length && rapSelectedYear) {
        const firstBand = rapLayers[0];
        const dataPayload = {
          datasets: [{ path: 'rap/rap_ts.parquet', alias: 'rap' }],
          columns: ['rap.topaz_id AS topaz_id', 'rap.value AS value'],
          filters: [
            { column: 'rap.year', op: '=', value: rapSelectedYear },
            { column: 'rap.band', op: '=', value: firstBand.bandId },
          ],
        };
        const dataResult = await postQueryEngine(dataPayload);
        if (dataResult && dataResult.records) {
          rapSummary = {};
          for (const row of dataResult.records) {
            rapSummary[String(row.topaz_id)] = row.value;
          }
        }
      }

      updateLayerList();
      applyLayers();
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load RAP overlays', err);
    }
  }

  const deckgl = new deck.Deck({
    parent: target,
    controller: controllerOptions,
    initialViewState,
    onViewStateChange: ({ viewState }) => {
      setViewState({
        ...viewState,
        minZoom: initialViewState.minZoom,
        maxZoom: initialViewState.maxZoom,
      });
    },
    onHover: (info) => {
      // Highlight corresponding line in graph when hovering over subcatchment
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
    layers: [baseLayer],
    getTooltip: (info) => {
      if (!info) return null;
      const luOverlay = pickActiveLanduseLayer();
      if (info.object && luOverlay && landuseSummary) {
        const props = info.object && info.object.properties;
        const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
        const row = topaz != null ? landuseSummary[String(topaz)] : null;
        const val = landuseValue(luOverlay.mode, row);
        if (val !== null) {
          const label =
            luOverlay.mode === 'dominant'
              ? `Landuse: ${val}`
              : `${luOverlay.mode}: ${typeof val === 'number' ? val.toFixed(3) : val}`;
          return `Layer: ${luOverlay.path}\nTopazID: ${topaz}\n${label}`;
        }
      }
      const soilOverlay = pickActiveSoilsLayer();
      if (info.object && soilOverlay && soilsSummary) {
        const props = info.object && info.object.properties;
        const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
        const row = topaz != null ? soilsSummary[String(topaz)] : null;
        const val = soilsValue(soilOverlay.mode, row);
        if (val !== null) {
          let label;
          if (soilOverlay.mode === 'dominant') {
            label = `Soil: ${val}`;
          } else if (soilOverlay.mode === 'bd') {
            label = `Bulk density: ${typeof val === 'number' ? val.toFixed(2) : val} g/cm³`;
          } else if (soilOverlay.mode === 'soil_depth') {
            label = `Soil depth: ${typeof val === 'number' ? val.toFixed(0) : val} mm`;
          } else {
            label = `${soilOverlay.mode}: ${typeof val === 'number' ? val.toFixed(1) : val}%`;
          }
          return `Layer: ${soilOverlay.path}\nTopazID: ${topaz}\n${label}`;
        }
      }
      const hillslopesOverlay = pickActiveHillslopesLayer();
      if (info.object && hillslopesOverlay && hillslopesSummary) {
        const props = info.object && info.object.properties;
        const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
        const row = topaz != null ? hillslopesSummary[String(topaz)] : null;
        const val = hillslopesValue(hillslopesOverlay.mode, row);
        if (val !== null) {
          let label;
          if (hillslopesOverlay.mode === 'slope_scalar') {
            label = `Slope: ${typeof val === 'number' ? (val * 100).toFixed(1) : val}%`;
          } else if (hillslopesOverlay.mode === 'length') {
            label = `Length: ${typeof val === 'number' ? val.toFixed(1) : val} m`;
          } else if (hillslopesOverlay.mode === 'aspect') {
            label = `Aspect: ${typeof val === 'number' ? val.toFixed(0) : val}°`;
          } else {
            label = `${hillslopesOverlay.mode}: ${typeof val === 'number' ? val.toFixed(2) : val}`;
          }
          return `Layer: ${hillslopesOverlay.path}\nTopazID: ${topaz}\n${label}`;
        }
      }
      const watarOverlay = pickActiveWatarLayer();
      if (info.object && watarOverlay && watarSummary) {
        const props = info.object && info.object.properties;
        const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
        const row = topaz != null ? watarSummary[String(topaz)] : null;
        const val = watarValue(watarOverlay.mode, row);
        if (val !== null) {
          const label = `${watarOverlay.label}: ${typeof val === 'number' ? val.toFixed(2) : val}`;
          return `Layer: ${watarOverlay.path}\nTopazID: ${topaz}\n${label}`;
        }
      }
      const weppOverlay = pickActiveWeppLayer();
      if (info.object && weppOverlay && weppSummary) {
        const props = info.object && info.object.properties;
        const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
        const row = topaz != null ? weppSummary[String(topaz)] : null;
        const val = weppValue(weppOverlay.mode, row);
        if (val !== null) {
          let label;
          if (weppOverlay.mode === 'runoff_volume') {
            label = `Runoff: ${typeof val === 'number' ? val.toFixed(1) : val} mm`;
          } else if (weppOverlay.mode === 'subrunoff_volume') {
            label = `Subrunoff: ${typeof val === 'number' ? val.toFixed(1) : val} mm`;
          } else if (weppOverlay.mode === 'baseflow_volume') {
            label = `Baseflow: ${typeof val === 'number' ? val.toFixed(1) : val} mm`;
          } else if (weppOverlay.mode === 'soil_loss') {
            label = `Soil Loss: ${typeof val === 'number' ? val.toFixed(2) : val} tonnes/ha`;
          } else if (weppOverlay.mode === 'sediment_deposition') {
            label = `Sed. Deposition: ${typeof val === 'number' ? val.toFixed(2) : val} tonnes/ha`;
          } else if (weppOverlay.mode === 'sediment_yield') {
            label = `Sed. Yield: ${typeof val === 'number' ? val.toFixed(2) : val} tonnes/ha`;
          } else {
            label = `${weppOverlay.mode}: ${typeof val === 'number' ? val.toFixed(2) : val}`;
          }
          return `Layer: ${weppOverlay.path}\nTopazID: ${topaz}\n${label}`;
        }
      }
      const weppYearlyOverlay = pickActiveWeppYearlyLayer();
      if (info.object && weppYearlyOverlay && weppYearlySummary) {
        const props = info.object && info.object.properties;
        const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
        const row = topaz != null ? weppYearlySummary[String(topaz)] : null;
        const val = weppYearlyValue(weppYearlyOverlay.mode, row);
        if (val !== null) {
          let label;
          if (weppYearlyOverlay.mode === 'runoff_volume') {
            label = `Runoff: ${typeof val === 'number' ? val.toFixed(1) : val} mm`;
          } else if (weppYearlyOverlay.mode === 'subrunoff_volume') {
            label = `Subrunoff: ${typeof val === 'number' ? val.toFixed(1) : val} mm`;
          } else if (weppYearlyOverlay.mode === 'baseflow_volume') {
            label = `Baseflow: ${typeof val === 'number' ? val.toFixed(1) : val} mm`;
          } else if (weppYearlyOverlay.mode === 'soil_loss') {
            label = `Soil Loss: ${typeof val === 'number' ? val.toFixed(2) : val} tonnes/ha`;
          } else if (weppYearlyOverlay.mode === 'sediment_deposition') {
            label = `Sed. Deposition: ${typeof val === 'number' ? val.toFixed(2) : val} tonnes/ha`;
          } else if (weppYearlyOverlay.mode === 'sediment_yield') {
            label = `Sed. Yield: ${typeof val === 'number' ? val.toFixed(2) : val} tonnes/ha`;
          } else {
            label = `${weppYearlyOverlay.mode}: ${typeof val === 'number' ? val.toFixed(2) : val}`;
          }
          const yearLine = weppYearlySelectedYear != null ? `Year: ${weppYearlySelectedYear}\n` : '';
          return `Layer: ${weppYearlyOverlay.path}\n${yearLine}TopazID: ${topaz}\n${label}`;
        }
      }
      // WEPP Event tooltip
      const weppEventOverlay = pickActiveWeppEventLayer();
      if (info.object && weppEventOverlay && weppEventSummary) {
        const props = info.object && info.object.properties;
        const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
        const row = topaz != null ? weppEventSummary[String(topaz)] : null;
        const val = weppEventValue(weppEventOverlay.mode, row);
        if (val !== null) {
          let label;
          if (weppEventOverlay.mode === 'event_P') {
            label = `Precipitation: ${typeof val === 'number' ? val.toFixed(2) : val} mm`;
          } else if (weppEventOverlay.mode === 'event_Q') {
            label = `Runoff: ${typeof val === 'number' ? val.toFixed(2) : val} mm`;
          } else if (weppEventOverlay.mode === 'event_ET') {
            label = `Total ET: ${typeof val === 'number' ? val.toFixed(2) : val} mm`;
          } else if (weppEventOverlay.mode === 'event_peakro') {
            label = `Peak Runoff Rate: ${typeof val === 'number' ? val.toFixed(4) : val} m\u00b3/s`;
          } else if (weppEventOverlay.mode === 'event_tdet') {
            label = `Total Detachment: ${typeof val === 'number' ? val.toFixed(2) : val} kg`;
          } else {
            label = `${weppEventOverlay.mode}: ${typeof val === 'number' ? val.toFixed(2) : val}`;
          }
          return `Layer: ${weppEventOverlay.path}\nDate: ${weppEventSelectedDate}\nTopazID: ${topaz}\n${label}`;
        }
      }
      // RAP tooltip - handle both cumulative and single band modes
      if (info.object && rapSummary && (rapCumulativeMode || pickActiveRapLayer())) {
        const props = info.object && info.object.properties;
        const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
        const row = topaz != null ? rapSummary[String(topaz)] : null;
        const val = rapValue(row);
        if (val !== null) {
          if (rapCumulativeMode) {
            const selectedBands = rapLayers.filter((l) => l.selected !== false);
            const bandNames = selectedBands.map((l) => RAP_BAND_LABELS[l.bandKey] || l.bandKey).join(' + ');
            const label = `Cumulative (${bandNames}): ${typeof val === 'number' ? val.toFixed(1) : val}%`;
            return `Layer: Cumulative Cover\nYear: ${rapSelectedYear}\nTopazID: ${topaz}\n${label}`;
          } else {
            const rapOverlay = pickActiveRapLayer();
            const bandLabel = RAP_BAND_LABELS[rapOverlay.bandKey] || rapOverlay.bandKey;
            const label = `${bandLabel}: ${typeof val === 'number' ? val.toFixed(1) : val}%`;
            return `Layer: ${rapOverlay.path}\nYear: ${rapSelectedYear}\nTopazID: ${topaz}\n${label}`;
          }
        }
      }
      const rasterLayer = pickActiveRaster();
      if (info.coordinate && rasterLayer) {
        const val = sampleRaster(rasterLayer, info.coordinate);
        if (val !== null) {
          return `Layer: ${rasterLayer.path}\nValue: ${val}`;
        }
      }
      if (info.tile) {
        return `Tile z${info.tile.z}`;
      }
      return null;
    },
    onError: (error) => {
      // Keep the stub resilient; surface issues in console.
      // eslint-disable-next-line no-console
      console.error('gl-dashboard render error', error);
    },
  });

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

  Promise.all([detectLayers(), detectLanduseOverlays(), detectSoilsOverlays(), detectHillslopesOverlays(), detectWatarOverlays(), detectWeppOverlays(), detectWeppYearlyOverlays(), detectWeppEventOverlays(), detectRapOverlays()])
    .catch((err) => {
      // eslint-disable-next-line no-console
      console.error('gl-dashboard: layer detection failed', err);
    });
})();
