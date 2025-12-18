# GL Dashboard Specification
> WebGL-accelerated geospatial dashboard for WEPPcloud runs using deck.gl, providing interactive maps, timeseries graphs, and multi-scenario comparison

**Version:** 1.0  
**Last Updated:** 2026-02-XX  
**Status:** Production

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Component Map](#component-map)
- [UI Structure](#ui-structure)
- [Data Flow](#data-flow)
- [Layer System](#layer-system)
- [Graph System](#graph-system)
- [State Management](#state-management)
- [Interaction Patterns](#interaction-patterns)
- [Performance Considerations](#performance-considerations)
- [Testing Strategy](#testing-strategy)
- [Known Issues and Workarounds](#known-issues-and-workarounds)

## Overview

The GL Dashboard is a WebGL-powered visualization tool that provides real-time exploration of WEPPcloud modeling results. It replaces legacy Leaflet-based controls with a deck.gl renderer capable of handling large datasets efficiently. The dashboard supports multiple layer types (raster, vector, timeseries), scenario comparison, and interactive graph generation.

**Primary Use Cases:**
1. Visual inspection of landuse, soils, and watershed delineation
2. WEPP model output analysis (yearly, event-based, cumulative)
3. RAP (Rangeland Analysis Platform) timeseries exploration
4. WATAR (Wildfire Ash Transport) overlay visualization
5. Multi-scenario comparison with differential colormaps

**Key Features:**
- **Basemap Selection:** Google Terrain, Google Satellite, OpenStreetMap
- **Layer Detection:** Automatic discovery of available datasets (landuse/nlcd.tif, soils/ssurgo.tif, WEPP outputs, RAP parquet files)
- **Stacked Layout:** Map viewport above a collapsible graph panel; graph focus hides the map to give the canvas full height
- **Year Slider:** Interactive timeline control for RAP and WEPP Yearly layers
- **Legends Panel:** Floating, collapsible panel showing active layer colormaps
- **Omni Graph Integration:** Boxplot/bar chart visualizations for scenario analysis

## Architecture

### Technology Stack
- **Rendering:** deck.gl 9.x (WebGL2 tile layer, GeoJSON layer, bitmap layer)
- **Module System:** ES6 modules with dynamic imports
- **State Management:** Centralized mutable state with subscription notifications
- **Query Engine:** DuckDB-powered backend for parquet/GeoJSON queries
- **Color Scales:** colormap library (viridis, rdbu, winter, jet2) + custom NLCD/soil palettes

### File Structure (modularized)
```
wepppy/weppcloud/static/js/gl-dashboard/
├── config.js                    # Constants, layer/graph defs, colormaps
├── state.js                     # Centralized state + subscriptions
├── colors.js                    # Colormap + normalization helpers
├── scenario/manager.js          # Scenario/comparison switching + diff ranges
├── data/
│   ├── query-engine.js          # Query Engine fetch helpers (sitePrefix-aware)
│   └── wepp-data.js             # WEPP stat/yearly/event fetch + base/comparison
├── ui/
│   ├── graph-mode.js            # Graph mode/layout controller + slider placement
│   └── year-slider.js           # Timeline control (show/hide/playback)
├── graphs/
│   ├── timeseries-graph.js      # Canvas-based graph renderer
│   └── graph-loaders.js         # Data loaders for Omni/RAP/WEPP graphs
├── layers/
│   ├── detector.js              # Overlay detection (raster, vector, overlays)
│   ├── orchestrator.js          # Detection sequencing + state wiring
│   └── renderer.js              # Sidebar/legend DOM rendering
├── map/
│   ├── controller.js            # deck.gl wrapper
│   ├── layers.js                # Layer stack builder, tooltips, legends
│   └── raster-utils.js          # GeoTIFF/SBS loaders, gdalinfo fetch
└── gl-dashboard.js              # Thin orchestrator (imports, DI, DOM binding)

wepppy/weppcloud/templates/
└── gl_dashboard.htm             # Jinja template with CSS and HTML structure
```

### Module Dependencies (high level)
```
gl-dashboard.js (main)
  ├── config.js
  ├── state.js
  ├── scenario/manager.js
  ├── data/query-engine.js
  ├── data/wepp-data.js
  ├── ui/graph-mode.js
  ├── ui/year-slider.js
  ├── graphs/timeseries-graph.js
  ├── graphs/graph-loaders.js
  ├── layers/detector.js
  ├── layers/orchestrator.js
  ├── layers/renderer.js
  ├── map/layers.js
  ├── map/controller.js
  └── map/raster-utils.js
```

**Initialization Flow:**
1. Load context from `window.GL_DASHBOARD_CONTEXT` (injected by Flask template)
2. Dynamic `import()` of modules; instantiate controllers with dependency injection (state getters/setters, fetch helpers, render callbacks)
3. Initialize deck.gl controller with basemap tile layer
4. Kick off detection (raster gdalinfo + parquet summaries) asynchronously; render placeholder layer controls immediately, then populate once detection resolves (non-blocking page load)
5. Bind UI event listeners (basemap selector, scenario/comparison, layer toggles, graph mode buttons, year slider)
6. Apply initial layer stack (subcatchments visible by default); graph layout sync is idempotent

## Component Map

### Core Modules

#### `state.js`
**Purpose:** Single source of truth for all runtime state  
**Exports:**
- `getState()` → Returns state object
- `getValue(key)` → Get single value
- `setState(updates)` → Batch update with change notification
- `setValue(key, value)` → Single key update

**Key State Properties:**
```javascript
{
  currentBasemapKey: 'googleTerrain',
  currentViewState: { longitude, latitude, zoom, pitch, bearing },
  subcatchmentsVisible: true,
  subcatchmentLabelsVisible: false,
  
  // Graph state
  graphMode: 'minimized' | 'split' | 'full',
  graphFocus: false,
  activeGraphKey: null,
  
  // Scenario state
  currentScenarioPath: '',
  comparisonMode: false,
  
  // Layer summaries (loaded from Query Engine)
  landuseSummary: { [topaz_id]: { dom: value, ... } },
  soilsSummary: { [topaz_id]: { mukey: value } },
  weppSummary: { [topaz_id]: { runoff_volume, soil_loss, ... } },
  rapSummary: { [topaz_id]: { AFG: value, PFG: value, ... } },
  
  // RAP state
  rapMetadata: { years: [2000, 2001, ...], bands: [...] },
  rapSelectedYear: 2023,
  rapCumulativeMode: false,
  rapLayers: [{ key, label, band, visible, ... }],
  
  // WEPP Yearly state
  weppYearlyMetadata: { years: [...], minYear, maxYear },
  weppYearlySelectedYear: 2023,
  weppYearlySummary: { [topaz_id]: { runoff, sedyld, ... } },
  weppYearlyLayers: [{ key, label, mode, visible, ... }],
  
  // Cached data
  graphDataCache: {},
  hillLossCache: {},
  channelLossCache: {},
  weppYearlyCache: {},
}
```

#### `config.js`
**Purpose:** Static configuration and constants  
**Exports:**
- `COMPARISON_MEASURES`: Array of measure keys for scenario diff
- `WATER_MEASURES`, `SOIL_MEASURES`: Categorization for colormaps
- `BASE_LAYER_DEFS`: Raster layer paths (landuse/nlcd.tif, soils/ssurgo.tif)
- `GRAPH_DEFS`: Graph definitions for sidebar (Omni scenarios)
- `createBasemapDefs()`: Basemap tile URL templates
- `createColorScales(colormapFn)`: Viridis, rdbu, winter, jet2 scales

#### `layers/detector.js`
**Purpose:** Detect available datasets from run directory  
**Key Functions:**
- `detectRasterLayers()`: Fetch gdalinfo for nlcd.tif, ssurgo.tif, sbs map
- `detectLanduseOverlays()`: Query landuse summary via Query Engine
- `detectSoilsOverlays()`: Query soils summary
- `detectHillslopesOverlays()`: Query hillslope summary (area, aspect, slope)
- `detectWeppOverlays()`: Query WEPP summary (runoff, sediment)
- `detectWeppYearlyOverlays()`: Query WEPP yearly metadata and years
- `detectWeppEventOverlays()`: Query WEPP event metadata and dates
- `detectRapOverlays()`: Query RAP metadata and bands
- `detectWatarOverlays()`: Query WATAR summary (ash loading, sediment)

**Detection Strategy:**
1. Fetch gdalinfo JSON for each raster path
2. Compute WGS84 bounds from corner coordinates
3. Load subcatchments GeoJSON if not cached
4. Query parquet files via Query Engine for vector overlays
5. Build layer descriptor objects with visibility flags

#### `map/controller.js`
**Purpose:** Thin wrapper around deck.gl instance  
**Exports:** `createMapController(options)`  
**Methods:**
- `applyLayers(nextLayers)`: Update deck.gl layer stack
- `setViewState(viewState)`: Programmatic camera control

#### `map/layers.js`
**Purpose:** Layer stack builder and utility functions  
**Exports:** `createLayerUtils(options)`  
**Methods:**
- `buildLayerStack(baseLayer)`: Construct ordered layer array
- `formatTooltip(info)`: Generate hover tooltip HTML
- `buildLanduseLayer(summary, colorMap)`: GeoJSON layer with NLCD fill colors
- `buildSoilsLayer(summary, colorFn)`: GeoJSON layer with mukey colors
- `buildWeppLayer(summary, mode, colorScale, ranges)`: WEPP overlay with viridis/rdbu
- `buildRapLayer(summary, band, colorScale, ranges)`: RAP band overlay
- `buildWatarLayer(summary, mode, colorScale, ranges)`: WATAR overlay
- `buildRasterLayer(layerDef)`: Bitmap layer from GeoTIFF

**Layer Ordering (bottom to top):**
1. Basemap tiles (Google Terrain / Satellite / ESRI / OSM / OTM)
2. Raster overlays (landuse GeoTIFF, soils GeoTIFF, SBS map)
3. Subcatchments GeoJSON (boundaries)
4. Vector overlays (landuse, soils, WEPP, RAP, WATAR summaries)
5. Subcatchment labels (TextLayer with topaz_id)

#### `graphs/timeseries-graph.js`
**Purpose:** Canvas-based timeseries renderer (line, boxplot, bars)  
**Exports:** `createTimeseriesGraph(options)`  
**Methods:**
- `init()`: Bind canvas, attach mouse listeners, resize handler
- `setData(data)`: Accept graph dataset and trigger render
- `setCurrentYear(year)`: Update year cursor for line graphs
- `highlightSubcatchment(topazId)`: Emphasize line in graph
- `render()`: Dispatch to `_renderLine()`, `_renderBoxplot()`, or `_renderBars()`

**Graph Data Format:**
```javascript
{
  type: 'line' | 'boxplot' | 'bars',
  title: 'Graph Title',
  source: 'rap' | 'wepp-yearly' | 'omni',
  years: [2000, 2001, ...],
  series: {
    [topaz_id]: [value1, value2, ...],  // for line graphs
    // OR
    [topaz_id]: { stats: { min, q1, median, q3, max } }  // for boxplot
  },
  categories: ['Base', 'Scenario1', ...],  // for bars
  currentYear: 2023,
  tooltipFormatter: (data) => '<div>...',
}
```

#### `graphs/graph-loaders.js`
**Purpose:** Fetch and transform data for graphs  
**Exports:** `createGraphLoaders(options)`  
**Methods:**
- `loadGraphDataset(key, options)`: Dispatcher for graph types
- `loadOmniSoilLossHillGraph()`: Boxplot of hillslope soil loss across scenarios
- `loadOmniSoilLossChnGraph()`: Boxplot of channel soil loss
- `loadOmniRunoffHillGraph()`: Boxplot of hillslope runoff
- `loadOmniOutletSedimentGraph()`: Bar chart of outlet sediment discharge
- `loadOmniOutletStreamGraph()`: Bar chart of outlet stream discharge

  **Query Pattern (Omni Graphs):**
  1. For each scenario, query the interchange parquet files (`wepp/output/interchange/loss_pw0.hill.parquet`, `loss_pw0.chn.parquet`, `loss_pw0.all_years.out.parquet`).
  2. Join with hillslope area (in m²) from `watershed/hillslopes.parquet` for unit conversions.
  3. Apply unit conversions:
     - Water measures (runoff, subrunoff, baseflow): `(m³ / area_m²) * 1000 = mm` (depth)
     - Soil measures (soil_loss, sediment_deposition, sediment_yield): `(kg / area_m²) * 10 = t/ha` (mass per area)
  4. Compute statistics (min, q1, median, q3, max) per scenario for boxplots; outlet bars come from `loss_pw0.all_years.out.parquet`.
  5. Return boxplot series keyed by scenario and outlet bar series keyed by year.

#### `data/query-engine.js`
**Purpose:** Abstracts Query Engine HTTP calls  
**Exports:** `createQueryEngine(ctx)`  
**Methods:**
- `postQueryEngine(payload)`: POST to `/query-engine/runs/{runid}/{scenario}/query`
- `postBaseQueryEngine(payload)`: POST to base run (no scenario path)
- `postQueryEngineForScenario(payload, scenarioPath)`: POST to specific scenario

**Query Payload Format:**
```javascript
{
  datasets: [
    { path: 'wepp/output/interchange/loss_pw0.hill.parquet', alias: 'hill' },
    { path: 'watershed/hillslopes.parquet', alias: 'meta' }
  ],
  joins: [
    { left: 'hill', right: 'meta', on: 'wepp_id', type: 'inner' }
  ],
  columns: ['meta.topaz_id', 'hill."Soil Loss" AS sedyld'],
  aggregations: [
    { sql: 'SUM(hill."Soil Loss")', alias: 'total_sediment' }
  ],
  filters: [
    { column: 'hill.year', op: '=', value: 2023 }
  ],
  group_by: ['meta.topaz_id']
}
```

### UI Components

#### Basemap Selector
**Element:** `#gl-basemap-select` (custom dropdown)  
**Options:** googleTerrain, googleSatellite, osm  
**Handler:** `setBasemap(key)` → rebuilds basemap tile layer and calls `applyLayers()`

#### Scenario Selector
**Element:** `#gl-scenario-select` (select dropdown)  
**Options:** Base (empty path) + Omni scenarios from `ctx.omniScenarios`  
**Handler:** `setScenario(scenarioPath)` → updates state, refetches overlays, recalculates comparison diff ranges

#### Comparison Toggle
**Element:** `#gl-comparison-toggle` (checkbox)  
**Handler:** `setComparisonMode(enabled)` → loads base scenario summaries, computes diff ranges for rdbu colormaps

#### Subcatchments Toggle
**Element:** `#gl-subcatchments-toggle` (checkbox)  
**Handler:** `toggleSubcatchments(visible)` → shows/hides all subcatchment-based overlays

#### Subcatchment Labels Toggle
**Element:** `#gl-subcatchment-labels-toggle` (checkbox)  
**Handler:** `toggleSubcatchmentLabels(visible)` → renders TextLayer with topaz_id centroids

#### Layer List
**Element:** `#gl-layer-list`  
**Structure:**
```html
<ul id="gl-layer-list">
  <details class="gl-layer-details" open>
    <summary>Landuse</summary>
    <ul class="gl-layer-items">
      <li class="gl-layer-item">
        <input type="checkbox" id="layer-Landuse-dom" />
        <label for="layer-Landuse-dom">Dominant Cover</label>
      </li>
    </ul>
  </details>
  <details class="gl-layer-details">
    <summary>WEPP Yearly</summary>
    <div class="gl-wepp-stat">
      <div class="gl-wepp-stat__label">Statistic</div>
      <div class="gl-wepp-stat__options">
        <label><input type="radio" name="wepp-stat" value="mean" checked> Mean (Annual Average)</label>
        <label><input type="radio" name="wepp-stat" value="p90"> 90th Percentile (Risk)</label>
        <label><input type="radio" name="wepp-stat" value="sd"> Std. Deviation (Variability)</label>
        <label><input type="radio" name="wepp-stat" value="cv"> CV % (Instability)</label>
      </div>
    </div>
    <ul class="gl-layer-items">
      <li class="gl-layer-item">
        <input type="checkbox" id="layer-WEPP-Yearly-runoff" />
        <label for="layer-WEPP-Yearly-runoff">Runoff (mm)</label>
      </li>
      <li class="gl-layer-item">
        <input type="checkbox" id="layer-WEPP-Yearly-subrunoff" />
        <label for="layer-WEPP-Yearly-subrunoff">Lateral Flow (mm)</label>
      </li>
      <li class="gl-layer-item">
        <input type="checkbox" id="layer-WEPP-Yearly-baseflow" />
        <label for="layer-WEPP-Yearly-baseflow">Baseflow (mm)</label>
      </li>
      <li class="gl-layer-item">
        <input type="checkbox" id="layer-WEPP-Yearly-soil_loss" />
        <label for="layer-WEPP-Yearly-soil_loss">Soil Loss (t/ha)</label>
      </li>
      <li class="gl-layer-item">
        <input type="checkbox" id="layer-WEPP-Yearly-sediment_deposition" />
        <label for="layer-WEPP-Yearly-sediment_deposition">Sediment Deposition (t/ha)</label>
      </li>
      <li class="gl-layer-item">
        <input type="checkbox" id="layer-WEPP-Yearly-sediment_yield" />
        <label for="layer-WEPP-Yearly-sediment_yield">Sediment Yield (t/ha)</label>
      </li>
    </ul>
  </details>
  <details class="gl-layer-details">
    <summary>RAP</summary>
    <div class="gl-rap-mode">
      <input type="radio" name="rap-mode" id="layer-RAP-cumulative" />
      <label for="layer-RAP-cumulative">Cumulative Cover</label>
    </div>
    <ul class="gl-layer-items">
      <li class="gl-layer-item">
        <input type="checkbox" id="layer-RAP-AFG" />
        <label for="layer-RAP-AFG">Annual Forbs/Grasses (%)</label>
      </li>
    </ul>
  </details>
</ul>
```

**Handler Pattern:**
1. Toggle checkbox → update `layer.visible` flag in state
2. Call `deselectAllSubcatchmentOverlays()` if switching to new category (mutually exclusive)
3. Call `applyLayers()` → rebuilds deck.gl stack
4. Call `syncGraphModeForContext()` → determines if year slider should appear

#### Graph List
**Element:** `#gl-graph-list`  
**Structure:**
```html
<ul id="gl-graph-list">
  <details class="gl-layer-details" open>
    <summary>Omni Scenarios</summary>
    <ul class="gl-layer-items">
      <li class="gl-layer-item">
        <input type="radio" name="graph-selection" id="graph-omni-soil-loss-hill" />
        <label for="graph-omni-soil-loss-hill">Soil Loss (hillslopes, tonne/ha)</label>
      </li>
    </ul>
  </details>
</ul>
```

**Handler:** `activateGraphItem(key)` → fetches data, calls `timeseriesGraph.setData()`, ensures graph panel is expanded

#### Graph Panel
**Element:** `#gl-graph`  
**Classes:** `.is-collapsed` (minimized mode)  
**Controls:**
- **Mode Buttons:** `[data-graph-mode="minimized|split|full"]`
  - Minimized: Panel height 48px, graph hidden
  - Split: Panel height ~640px, graph sits below the map in the stacked layout
  - Full: Graph focus hides the map viewport; graph stretches vertically (80vh canvas)
- **Canvas:** `#gl-graph-canvas` (520px height, devicePixelRatio scaling)
- **Tooltip:** `#gl-graph-tooltip` (positioned absolute on hover)

**State Transitions:**
```
Map-only overlays (Landuse/Soils/WEPP/WEPP Event/WATAR)
  ↓ auto
Graph minimized (controls disabled; slider hidden)
  ↓ RAP cumulative or any visible RAP overlay OR any visible WEPP Yearly overlay
Graph split (controls enabled; slider visible)
  ↓ Omni graph activated OR user clicks full
Graph full (focus; map hidden; split button disabled while Omni focused)
  ↓ user minimizes
Graph minimized
  ↓ switch back to map-only overlays
Graph minimized (controls disabled; slider hidden)
```

### Graph Panel Modes

#### Minimized
**State:** `graphMode = 'minimized'`, `graphFocus = false`  
**UI:** Panel height 48px, content hidden, only header visible  
**Trigger:** User clicks minimize, or no graph-capable layers active (map-only overlays)

#### Split
**State:** `graphMode = 'split'`, `graphFocus = false`  
**UI:** Panel height ~640px, map stacked above graph  
**Trigger:** User clicks split, or RAP cumulative/visible RAP overlay, or WEPP Yearly overlay becomes active

#### Full
**State:** `graphMode = 'full'`, `graphFocus = true`  
**UI:** Graph focus hides the map viewport (graph stretches vertically)  
**Trigger:** User clicks full, or any of the following are active:
- Omni graphs (`omni-*` sources) or Cumulative Contribution → always force full by default
- Climate Yearly graph → full by default
- Explicit user override via layout buttons

#### Year Slider
**Element:** `#gl-year-slider` (single instance reused across contexts)  
**Placement & Visibility (context-aware):**
- **Climate Yearly** → slider is moved **inside** `#gl-graph-container`, pinned to the **bottom**; container gets `.has-bottom-slider` to add padding. Graph defaults to **full** pane.
- **RAP / WEPP Yearly** → slider stays in the dedicated slot **above** the graph pane (`#gl-graph-year-slider`) at 100% width; never overlaps the graph header. Graph defaults to **split** view.
- Hidden when no RAP/WEPP/Climate Yearly graph context is active.

**Controls:**
- Input: `#gl-year-slider-input` (range slider)
- Min/Max: `#gl-year-slider-min` / `#gl-year-slider-max`
- Current: `#gl-year-slider-value`
- Play: `#gl-year-slider-play` (▶ / ⏸)

**Behavior:**
- On input change → emit `change` → refresh active RAP/WEPP Yearly layers and update the graph year.
- Play mode: advance 1 year every 3 seconds; loops to min when exceeding max.
- Range sourced from context metadata:
  - Climate: `ctx.climate.startYear` / `endYear`
  - RAP: `rapMetadata.years`
  - WEPP Yearly: `weppYearlyMetadata.minYear` / `maxYear`
- Graph mode re-syncs on context changes; in-flight graph loads are de-duped per key to prevent reload loops.

**Integration:**
- RAP: updates `rapSelectedYear`, refreshes overlays, and updates graph year when source is `rap`.
- WEPP Yearly: updates `weppYearlySelectedYear`, refreshes overlays, and updates graph year when source is `wepp_yearly`.
- Climate Yearly: updates `climateYearlySelectedYear`, refreshes the climate graph, keeps full-pane focus.

#### Legends Panel
**Element:** `#gl-legends-panel`  
**Position:** Absolute top-right corner of map (0.75rem offset)  
**Classes:** `.is-collapsed` (toggled via header button)  
**Content:** `#gl-legends-content` (vertical list of `.gl-legend-item` blocks)

**Legend Format:**
```html
<div class="gl-legend-item" style="display: none;">
  <h5>Runoff (mm)</h5>  <!-- Units shown: mm for water, t/ha for soil, % for cover -->
  <div class="gl-legend-gradient">
    <div class="gl-legend-stops">
      <span style="background: rgb(68,1,84)"></span>
      <span style="background: rgb(253,231,37)"></span>
    </div>
    <div class="gl-legend-labels">
      <span>0.0</span>
      <span>100.5</span>
    </div>
  </div>
</div>
```

**Unit Display:**
- Water measures: `mm` (runoff_volume, subrunoff_volume, baseflow_volume)
- Soil measures: `t/ha` (soil_loss, sediment_deposition, sediment_yield)
- CV statistic: `%` (coefficient of variation, dimensionless percentage)

**Update Trigger:** `updateLegendsPanel()` called after `applyLayers()`  
**Display Logic:**
- Show legend for each visible layer
- Discrete legends (NLCD, soils) → color swatches with labels
- Continuous legends (WEPP, RAP, WATAR) → horizontal gradient bar with min/max

## Data Flow

### Layer Activation Flow
```
User clicks layer checkbox
  ↓
Event handler toggles layer.visible
  ↓
deselectAllSubcatchmentOverlays() if switching category
  ↓
applyLayers() → layerUtils.buildLayerStack()
  ↓
  For each visible layer:
    - Fetch summary if not cached
    - Apply colormap (viridis, rdbu, NLCD, soil)
    - Build GeoJSON layer with getFillColor callback
  ↓
mapController.applyLayers(stack)
  ↓
deck.gl re-renders
  ↓
updateLegendsPanel() → show/hide legends
  ↓
syncGraphModeForContext() → year slider visibility
```

### Graph Activation Flow
```
User clicks graph radio button
  ↓
activateGraphItem(key)
  ↓
ensureGraphExpanded() → remove .is-collapsed
  ↓
loadGraphDataset(key) → graphLoaders dispatch
  ↓
  For Omni graphs:
    - Query each scenario's parquet files
    - Compute boxplot stats (min, q1, median, q3, max)
    - Join with hillslope area for normalization
  ↓
timeseriesGraph.setData(data)
  ↓
setGraphFocus(data.source === 'omni')
  ↓
  If focus=true:
    - glMainEl.classList.add('graph-focus')
    - Graph panel expands to 70% width
    - Map shrinks to 30% width
  ↓
timeseriesGraph.render()
  ↓
syncGraphModeForContext() updates mode buttons
```

### Scenario Comparison Flow
```
User selects scenario from dropdown
  ↓
setScenario(scenarioPath)
  ↓
currentScenarioPath = scenarioPath
  ↓
If comparisonMode enabled:
  - loadBaseSummaries() (landuse, soils, WEPP, RAP, WATAR)
  - computeComparisonDiffRanges() (percentile-based scaling)
  ↓
Detect overlays with new scenario path
  ↓
applyLayers() with rdbu colormap if comparison active
  ↓
Legends show "Δ" prefix and -max/+max range
```

### Year Slider Flow
```
User drags year slider or clicks play
  ↓
yearSlider._emit('change', year)
  ↓
Event listener updates state:
  - rapSelectedYear = year (for RAP)
  - weppYearlySelectedYear = year (for WEPP Yearly)
  ↓
refreshRapData() or refreshWeppYearlyData()
  ↓
Query Engine with year filter:
  {
    filters: [
      { column: 'rap.year', op: '=', value: year }
    ]
  }
  ↓
rapSummary or weppYearlySummary updated
  ↓
applyLayers() → rebuild GeoJSON with new data
  ↓
timeseriesGraph.setCurrentYear(year) → update cursor in graph
```

## Layer System

### Layer Types

#### Raster Layers
**Sources:** GeoTIFF files loaded via geotiff.js  
**Rendering:** deck.gl BitmapLayer with RGBA array from canvas  
**Examples:** landuse/nlcd.tif, soils/ssurgo.tif, BAER SBS map  

**Load Process:**
1. Fetch gdalinfo JSON to get bounds and dimensions
2. Load GeoTIFF via `GeoTIFF.fromArrayBuffer()`
3. Read raster data → Uint8Array or Float32Array
4. Apply colormap (NLCD discrete, viridis continuous)
5. Render to canvas → extract RGBA ImageData
6. Pass to BitmapLayer with bounds

**Colormap Application:**
```javascript
function applyColormap(rasterData, colorMap) {
  const rgba = new Uint8ClampedArray(rasterData.length * 4);
  for (let i = 0; i < rasterData.length; i++) {
    const value = rasterData[i];
    const color = colorMap[value] || [0, 0, 0, 0];
    rgba[i * 4] = color[0];
    rgba[i * 4 + 1] = color[1];
    rgba[i * 4 + 2] = color[2];
    rgba[i * 4 + 3] = color[3];
  }
  return rgba;
}
```

#### Vector Overlays (Subcatchment-based)
**Sources:** Parquet datasets queried via Query Engine  
**Rendering:** deck.gl GeoJsonLayer with subcatchments geometry + attribute join  
**Examples:** Landuse dom, Soils mukey, WEPP runoff, RAP AFG, WATAR ash_loading

**WEPP Output Units:**
- **Raw data** in parquet files: Water volumes in m³, soil mass in kg
- **Display units** after conversion: Water depth in mm, soil mass in t/ha
- **Conversion formulas:**
  - Water: `(value_m³ / hillslope_area_m²) * 1000 = mm`
  - Soil: `(value_kg / hillslope_area_m²) * 10 = t/ha`
- Hillslope areas are retrieved from `watershed/hillslopes.parquet` and joined on `wepp_id`

**Data Structure:**
```javascript
// Summary from Query Engine (after conversion)
{
  "123": { runoff_volume: 45.2, soil_loss: 2.1 },  // mm, t/ha
  "456": { runoff_volume: 32.8, soil_loss: 1.5 }   // mm, t/ha
}

// GeoJSON features
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": { "TopazID": "123", ... },
      "geometry": { "type": "Polygon", "coordinates": [...] }
    }
  ]
}
```

**Rendering Function:**
```javascript
function buildWeppLayer(summary, mode, colorScale, ranges) {
  const range = ranges[mode] || { min: 0, max: 100 };
  return new deck.GeoJsonLayer({
    id: `wepp-${mode}`,
    data: subcatchmentsGeoJson,
    filled: true,
    getFillColor: (feature) => {
      const topazId = feature.properties.TopazID;
      const row = summary[topazId];
      if (!row) return [128, 128, 128, 100]; // Gray for missing
      const value = row[mode];
      if (!Number.isFinite(value)) return [128, 128, 128, 100];
      const normalized = (value - range.min) / (range.max - range.min);
      const idx = Math.floor(normalized * 255);
      const color = colorScale[idx] || colorScale[255];
      return [color[0], color[1], color[2], 230];
    },
    pickable: true,
    stroked: true,
    lineWidthMinPixels: 1,
    getLineColor: [180, 180, 180, 255],
    updateTriggers: {
      getFillColor: [summary, mode, colorScale, ranges]
    }
  });
}
```

#### Comparison Layers (Differential Colormaps)
**Mode:** Activated via comparison toggle  
**Colormap:** rdbu (red-blue diverging scale)  
**Calculation:** Δ = Base - Scenario (positive = scenario reduces measure)

**Range Computation:**
```javascript
function computeComparisonDiffRanges() {
  const diffs = [];
  for (const topazId of Object.keys(weppSummary)) {
    const scenarioValue = weppSummary[topazId].soil_loss;
    const baseValue = baseSummaryCache.wepp[topazId].soil_loss;
    if (Number.isFinite(scenarioValue) && Number.isFinite(baseValue)) {
      diffs.push(baseValue - scenarioValue);
    }
  }
  diffs.sort((a, b) => a - b);
  const p5 = diffs[Math.floor(diffs.length * 0.05)];
  const p95 = diffs[Math.floor(diffs.length * 0.95)];
  const maxAbs = Math.max(Math.abs(p5), Math.abs(p95));
  comparisonDiffRanges.soil_loss = { min: -maxAbs, max: maxAbs };
}
```

### Layer Lifecycle

#### Detection Phase
**Trigger:** Page load, scenario change  
**Functions:** `detectRasterLayers()`, `detectLanduseOverlays()`, etc.  
**Output:** Populate state arrays (landuseLayers, soilsLayers, rapLayers, etc.)

#### Rendering Phase
**Trigger:** User toggles layer checkbox, year slider change  
**Functions:** `applyLayers()` → `buildLayerStack()` → `mapController.applyLayers()`  
**Steps:**
1. Collect all visible layers from state
2. For each layer type, call corresponding builder (buildWeppLayer, buildRapLayer, etc.)
3. Order layers (basemap → rasters → subcatchments → overlays → labels)
4. Pass array to deck.gl controller
5. Update legends panel

#### Cleanup Phase
**Trigger:** Layer deselected, scenario change  
**Actions:**
- Remove layer from deck.gl stack
- Clear cached summary if scenario path changed
- Hide corresponding legend

### Mutual Exclusivity Rules
**Subcatchment-based overlays are mutually exclusive within categories:**
- Landuse: Only one landuse layer visible at a time (dom, mukey, etc.)
- Soils: Only one soils layer visible
- WEPP: Multiple WEPP measures can coexist (runoff + soil_loss)
- RAP: Cumulative mode XOR individual bands (enforced via radio button)

**Implementation:**
```javascript
function deselectAllSubcatchmentOverlays() {
  landuseLayers.forEach(l => l.visible = false);
  soilsLayers.forEach(l => l.visible = false);
  // ... (repeat for all categories)
  rapCumulativeMode = false;
  yearSlider.hide();
}
```

## Graph System

### Graph Types

#### Line Graph (Timeseries)
**Use Case:** RAP bands over time, WEPP Yearly measures over time  
**Data Format:**
```javascript
{
  type: 'line',
  title: 'Annual Forbs/Grasses (%)',
  years: [2000, 2001, ..., 2023],
  series: {
    "123": [12.5, 13.2, 11.8, ...],
    "456": [8.3, 9.1, 8.7, ...]
  },
  currentYear: 2023
}
```

**Rendering:**
- X-axis: Years (evenly spaced)
- Y-axis: Value range (auto-scaled from min/max)
- Lines: One per subcatchment (topaz_id), color from GRAPH_COLORS palette
- Cursor: Vertical line at currentYear
- Hover: Highlight line, show tooltip with topaz_id + value
- Legend: Color swatches with topaz_id labels (right side)

#### Boxplot
**Use Case:** Omni scenario comparison (soil loss, runoff across hillslopes)  
**Data Format:**
```javascript
{
  type: 'boxplot',
  title: 'Soil Loss (hillslopes, tonne/ha)',
  source: 'omni',
  categories: ['Base', 'Low Severity', 'Moderate Severity'],
  series: {
    "123": { stats: { min: 0.5, q1: 1.2, median: 1.8, q3: 2.5, max: 3.2 } },
    "456": { stats: { min: 0.3, q1: 0.9, median: 1.3, q3: 1.9, max: 2.6 } }
  }
}
```

**Rendering:**
- X-axis: Categories (scenarios)
- Y-axis: Measure value (auto-scaled)
- Boxes: One per scenario, drawn with whiskers (min/max), box (q1/q3), median line
- Hover: Show stats for hovered scenario
- Color: Alternating shades from GRAPH_COLORS

#### Bar Chart
**Use Case:** Omni outlet discharge (sediment, stream)  
**Data Format:**
```javascript
{
  type: 'bars',
  title: 'Sediment discharge (tonne/ha)',
  source: 'omni',
  categories: ['Base', 'Low Severity', 'Moderate Severity'],
  series: [
    { label: 'Base', value: 12.5 },
    { label: 'Low Severity', value: 18.3 },
    { label: 'Moderate Severity', value: 24.7 }
  ]
}
```

**Rendering:**
- X-axis: Categories
- Y-axis: Value (auto-scaled)
- Bars: Vertical bars with fill color, hover highlight
- Hover: Show value with 2 decimal precision

#### Cumulative Contribution (Omni)
**Use Case:** Rank hillslopes by per-area contribution for a selected measure and plot cumulative contribution by percent of total hillslope area.  
**Data Sources:** `wepp/output/interchange/loss_pw0.hill.parquet` + `watershed/hillslopes.parquet` (per scenario).  
**Measures:** Runoff (m³), Lateral Flow (m³), Baseflow (m³), Soil Loss (t), Sed Deposition (t), Sed Yield (t).  
**Controls (sidebar → Graphs → Cumulative Contribution detail):**
- **Measure** dropdown (`CUMULATIVE_MEASURE_OPTIONS`) to choose the variable.
- **Select Scenarios** checkboxes (all Omni scenarios plus implicit Base); Base is always included even if unchecked/unchecked logic defaults to selected set.
**Computation:**
- For each scenario independently, compute per-area derivative = measure / area_ha, sort descending, cumulative sum by area and value.
- Values converted to tonne for soil measures; water values stay in m³.
- Percent-of-area axis uses a fixed 0.5% step (0 → 100) and each scenario is linearly interpolated onto that axis (prevents jagged traces when scenarios have different hillslope counts).
**Data Format:**
```javascript
{
  type: 'line',
  title: 'Cumulative Contribution — Soil Loss (t)',
  years: [0, 0.5, ..., 100], // percent of total hillslope area
  series: {
    base: { label: 'Base', values: [...], color: [r,g,b,a] },
    'omni/path': { label: 'mulch_15', values: [...], color: [r,g,b,a] }
  },
  xLabel: 'Percent of Total Hillslope Area',
  yLabel: 'Soil Loss (t)',
  source: 'omni',
  tooltipFormatter: (id, value, pct) => `${label}: ${value} t @ ${pct}% area`
}
```
**Rendering:**
- X-axis: Percent of total hillslope area.
- Y-axis: Cumulative measure.
- Lines: One per scenario; Base always shown. Legend uses scenario names.
- Hover: Shows scenario, cumulative value, and percent-of-area for the nearest point.

#### Climate Yearly (precip + temp)
**Purpose:** Visualize yearly climate by month with support for calendar year or water year start. Two stacked subplots share the month axis.  
**Data Source:** `climate/wepp_cli.parquet` (queried via `query-engine`; supports base and scenario paths). Required columns: `year`, `month` (or `mo`), `prcp`, `tmin`, `tmax`.  
**Controls (Graphs → Climate Yearly detail):**
- Year mode toggle: `Calendar Year` or `Water Year` (default).  
- `Water Year start month` select (default October, disabled when Calendar Year is selected).  
- Year slider fixed in the graph pane; highlights the selected year.
**Computation:**
- Water Year: months are rotated to start at the selected month; months ≥ start month are assigned to `year+1` to group a WY. Calendar Year forces start month to January.  
- Monthly precip: sum per month (no cumulative).  
- Monthly temp: average Tmin/Tmax per month.  
- Per-year series are color-coded (precip: magenta tones; Tmin: blue; Tmax: red). Highlighted year uses thicker strokes/opacity (shared with year slider).
**Data Format:**
```javascript
{
  type: 'climate-yearly',
  months: ['Oct', 'Nov', ..., 'Sep'], // rotated when WY
  years: [2000, 2001, ...],
  precipSeries: { 2000: { values: [mm...], color }, ... },
  tempSeries: { 2000: { tmin: [...], tmax: [...], colors: { tmin, tmax } }, ... },
  selectedYear: 2023,
  currentYear: 2023,
  waterYear: true,
  startMonth: 10,
  source: 'climate_yearly'
}
```
**Rendering:**
- Top subplot: monthly precip lines for all years; Y auto-scales to max monthly total.  
- Bottom subplot: monthly Tmin/Tmax lines for all years; Y auto-scales to min/max across both Tmin/Tmax.  
- Month labels use 3-char abbreviations; rotated for Water Year.  
- Legend shows highlighted year + Tmin/Tmax keys; year slider hover updates the highlight.  
- Hover tooltip returns nearest month/year with `P`, `Tmin`, `Tmax` values.

### Graph Panel Modes

#### Minimized
**State:** `graphMode = 'minimized'`, `graphFocus = false`  
**UI:** Panel height 48px, content hidden, only header visible  
**Trigger:** User clicks minimize button, or no graph-capable layers active

#### Split
**State:** `graphMode = 'split'`, `graphFocus = false`  
**UI:** Panel height ~640px, map width 70%, graph width 30%  
**Trigger:** User clicks split button, or RAP/WEPP Yearly layer activated

#### Full
**State:** `graphMode = 'full'`, `graphFocus = true`  
**UI:** Panel height ~640px, map width 30%, graph width 70%  
**Trigger:** User clicks full button, or Omni graph activated

### Mode Transition Logic

**`syncGraphModeForContext()` Function:**
```javascript
function syncGraphModeForContext() {
  const rapActive = isRapActive(state);
  const yearlyActive = isWeppYearlyActive(state);
  const graphCapable = rapActive || yearlyActive || !!state.activeGraphKey;
  
  // Generate context key for idempotency check
  const contextKey = `${graphCapable}-${rapActive}-${yearlyActive}-${graphModeUserOverride}-${state.activeGraphKey}`;
  if (contextKey === lastGraphContextKey) return; // No-op if context unchanged
  lastGraphContextKey = contextKey;
  
  if (!graphCapable) {
    // No graph data available
    setGraphControlsEnabled(false);
    setGraphMode('minimized', { source: 'auto' });
    yearSlider.hide();
    return;
  }
  
  // Graph data available
  setGraphControlsEnabled(true);
  const targetMode = graphModeUserOverride || 'split';
  setGraphMode(targetMode, { source: graphModeUserOverride ? 'user' : 'auto' });
  
  // Year slider visible only for RAP or WEPP Yearly
  if (rapActive || yearlyActive) {
    yearSlider.show();
  } else {
    yearSlider.hide();
  }
}
```

**Key Points:**
- **Idempotency:** Context key prevents redundant mode changes (avoids recursive toggles)
- **User Override:** `graphModeUserOverride` preserves manual mode selection
- **Auto Mode:** When context changes (layer activation), mode resets unless user override set

### Graph Data Caching

**Purpose:** Avoid redundant Query Engine calls  
**Cache Keys:**
- `graphDataCache[graphKey]`: Full graph dataset (Omni graphs)
- `hillLossCache[scenarioPath]`: Hill loss parquet for scenario
- `channelLossCache[scenarioPath]`: Channel loss parquet for scenario
- `outletAllYearsCache[scenarioPath]`: Outlet discharge timeseries

**Invalidation:**
- Scenario change → clear all caches
- Force reload → `loadGraphDataset(key, { force: true })`

## State Management

### State Updates
**Pattern:** Always use `setValue(key, value)` or `setState(updates)` to trigger change notifications  
**Subscribers:** Interested components can subscribe via `subscribe(callback, keys)`

**Example:**
```javascript
// Update single value
setValue('rapSelectedYear', 2023);

// Batch update
setState({
  rapSelectedYear: 2023,
  rapCumulativeMode: false
});

// Subscribe to changes
subscribe((state, changedKeys) => {
  if (changedKeys.includes('rapSelectedYear')) {
    console.log('Year changed to', state.rapSelectedYear);
  }
}, ['rapSelectedYear']);
```

### Property Binding
**Pattern:** Expose state keys as global window properties for external access

```javascript
bindStateKeys([
  'currentScenarioPath',
  'comparisonMode',
  'rapSelectedYear',
  'weppYearlySelectedYear',
  // ...
]);

// Now accessible globally
window.rapSelectedYear = 2022; // Triggers setValue internally
console.log(window.rapSelectedYear); // Reads from state
```

### State Persistence
**Not Implemented:** State is ephemeral (resets on page reload)  
**Future Enhancement:** Save state to localStorage or URL query params for session continuity

## Interaction Patterns

### Layer Toggle Pattern
1. User clicks checkbox `#layer-Landuse-dom`
2. Event handler fires:
   ```javascript
   layerCheckbox.addEventListener('change', async (e) => {
     const layerKey = e.target.dataset.layerKey;
     const category = e.target.dataset.category;
     const layer = landuseLayers.find(l => l.key === layerKey);
     
     if (e.target.checked) {
       // Deselect other layers in category
       deselectAllSubcatchmentOverlays();
       layer.visible = true;
       
       // Load summary if not cached
       if (!landuseSummary) {
         await detectLanduseOverlays({ ... });
       }
     } else {
       layer.visible = false;
     }
     
     applyLayers();
     syncGraphModeForContext();
   });
   ```

### RAP Cumulative Mode Pattern
**Behavior:** Radio button toggles between cumulative cover and individual bands

1. User clicks "Cumulative Cover" radio
2. Handler sets `rapCumulativeMode = true`, deselects all band checkboxes
3. Fetch cumulative summary (sum of AFG, PFG, BGR)
4. Apply layer with cumulative colormap
5. Year slider remains visible (cumulative data varies by year)

**Mutual Exclusivity:**
- Cumulative mode: Single overlay showing sum of all bands
- Band mode: Multiple band overlays can be visible simultaneously (AFG + PFG + BGR)

### Year Slider Pattern
**Continuous Update:**
1. User drags slider → input event fires continuously
2. Debounce or throttle update to avoid excessive re-renders
3. Update `rapSelectedYear` or `weppYearlySelectedYear`
4. Query new data for selected year
5. Rebuild layer with new summary
6. Update graph cursor if timeseries visible

**Play Mode:**
1. User clicks play button
2. Start interval timer (3-second delay)
3. Increment year, loop back to min year when reaching max
4. Emit 'change' event for each step
5. User can pause or manually adjust slider to interrupt

### Graph Hover Pattern
1. Mouse moves over canvas → `_onCanvasHover(e)` fires
2. Calculate mouse position in data coordinates
3. Find nearest line or box to cursor
4. Highlight that series (increase line width, draw highlight box)
5. Show tooltip with subcatchment ID and value
6. If hovering over subcatchment in graph → call `onHighlightSubcatchment(topazId)`
7. Map layer highlights corresponding feature (bold stroke)

### Scenario Comparison Pattern
1. User selects scenario from dropdown
2. User enables comparison toggle
3. Dashboard loads base scenario summaries (if not cached)
4. Compute difference: Δ = Base - Scenario
5. Calculate percentile-based ranges (p5, p95) for scaling
6. Apply rdbu colormap (red = negative Δ, blue = positive Δ)
7. Legend shows "Δ Soil Loss" with -maxAbs / +maxAbs labels

## Performance Considerations

### Memory Management

#### Large Payload Handling
**Issue:** RAP timeseries (24 years × 8 bands × 500 subcatchments) can exceed 96 MB  
**Solution:**
- Load summary on-demand (only when layer activated)
- Clear cache when switching scenarios
- Use binary parquet format instead of JSON

#### GeoTIFF Loading
**Issue:** Large rasters (4096×4096 RGBA) consume 64 MB per layer  
**Solution:**
- Load rasters only when checkbox toggled
- Release raster data after rendering to canvas (keep only canvas reference)
- Limit number of simultaneous raster layers (max 2-3)

#### Graph Rendering
**Issue:** Rendering 500+ lines at 60 FPS causes frame drops  
**Solution:**
- Aggregate subcatchments by region (hillslope → watershed)
- Draw only visible lines (clip to viewport)
- Use canvas compositing (layered rendering)
- Throttle hover updates (requestAnimationFrame)

### Render Optimization

#### Layer Update Triggers
**Pattern:** Explicit `updateTriggers` in deck.gl layers to control re-renders

```javascript
new deck.GeoJsonLayer({
  id: 'wepp-runoff',
  data: subcatchmentsGeoJson,
  getFillColor: (f) => colorForValue(f.properties.TopazID),
  updateTriggers: {
    getFillColor: [weppSummary, weppStatistic, weppRanges.runoff_volume]
  }
});
```

**Avoid:** Passing unstable references (inline functions, new objects) in updateTriggers

#### Debouncing Year Slider
**Pattern:** Throttle year slider updates to max 10 Hz (100ms interval)

```javascript
let sliderTimeout = null;
yearSlider.input.addEventListener('input', (e) => {
  clearTimeout(sliderTimeout);
  sliderTimeout = setTimeout(() => {
    const year = parseInt(e.target.value, 10);
    setValue('rapSelectedYear', year);
    refreshRapData();
  }, 100);
});
```

### Known Bottlenecks

1. **Query Engine Latency:** 200-500ms per query (network + DuckDB execution)
   - Mitigation: Pre-fetch summaries on page load, cache aggressively
   
2. **Canvas Redraw:** 50-100ms for complex graphs (500+ lines)
   - Mitigation: Use offscreen canvas, render in chunks, skip frames if behind

3. **Layer Stack Rebuild:** 30-50ms when toggling layers (GeoJSON layer construction)
   - Mitigation: Reuse layer instances where possible, only update data prop

## Testing Strategy

- Smoke (Playwright): run from `wepppy/weppcloud/static-src`
  - `gl-dashboard-state-transitions.spec.js`
  - `gl-dashboard-graph-modes.spec.js`
  - `gl-dashboard-layers.spec.js`
  - `gl-dashboard-cumulative.spec.js`
  - URLs:
    - `GL_DASHBOARD_URL="https://wc.bearhive.duckdns.org/weppcloud/runs/minus-farce/disturbed9002_wbt/gl-dashboard" npm run smoke -- tests/smoke/gl-dashboard-*.spec.js`
    - `GL_DASHBOARD_URL="https://wc.bearhive.duckdns.org/weppcloud/runs/walk-in-obsessive-compulsive/disturbed9002_wbt/gl-dashboard" npm run smoke -- tests/smoke/gl-dashboard-*.spec.js`
- Unit/Integration: mock deck.gl and Query Engine; validate state updates, detector URL construction (sitePrefix-aware), color scales, graph layout idempotence, slider placement rules.
- Visual checks: comparison mode shows diverging legend when base/diff ranges available; slider placement matches context (climate/outlet bottom; RAP/WEPP Yearly top; cumulative/omni hidden).
- Fixtures: `tests/gl-dashboard/fixtures/` holds gdalinfo/parquet/GeoJSON stubs and canned Query Engine responses for local tests.

## Known Issues and Workarounds

### Issue 1: TDZ (Temporal Dead Zone) in Graph Mode Sync
**Symptom:** `ReferenceError: Cannot access 'lastGraphContextKey' before initialization`  
**Cause:** `syncGraphModeForContext()` called during module init before `lastGraphContextKey` declared with `let`  
**Workaround:** Use `var lastGraphContextKey = null;` to hoist declaration  
**Location:** `gl-dashboard.js:73`

**Code:**
```javascript
// Use var to avoid TDZ issues if syncGraphModeForContext fires early during init.
var lastGraphContextKey = null; // eslint-disable-line no-var
```

### Issue 2: Recursive Graph Toggle Loop
**Symptom:** Clicking graph mode button triggers infinite `setGraphMode()` calls  
**Cause:** `setGraphMode()` calls `setGraphFocus()` which calls `syncGraphModeForContext()` which calls `setGraphMode()` again  
**Workaround:** Idempotency check in `syncGraphModeForContext()` prevents recursion  
**Location:** `gl-dashboard.js:1059-1065`

**Code:**
```javascript
function syncGraphModeForContext() {
  const contextKey = `${graphCapable}-${rapActive}-${yearlyActive}-${graphModeUserOverride}-${activeGraphKey}`;
  if (contextKey === lastGraphContextKey) {
    return; // No-op if context unchanged
  }
  lastGraphContextKey = contextKey;
  // ... proceed with mode change
}
```

### Issue 3: Year Slider Visibility Flicker
**Symptom:** Slider appears/disappears rapidly when toggling RAP layers  
**Cause:** Multiple async `refreshRapData()` calls in flight, each calling `syncGraphModeForContext()`  
**Workaround:** Guard slider visibility changes with flag to prevent redundant show/hide  
**Location:** `gl-dashboard.js:1080-1086`

**Code:**
```javascript
// Year slider visible only for RAP or WEPP Yearly contexts
if (rapActive || yearlyActive) {
  if (!yearSlider._visible) yearSlider.show(); // Guard prevents flicker
} else {
  if (yearSlider._visible) yearSlider.hide();
}
```

### Issue 4: Graph Panel Re-Enter After Minimize
**Symptom:** Graph panel re-expands when clicking any layer after minimizing  
**Cause:** `syncGraphModeForContext()` resets mode to 'split' if `graphCapable` and no user override  
**Workaround:** Track `graphModeUserOverride` to preserve user-selected minimize  
**Location:** `gl-dashboard.js:804-830`

**Code:**
```javascript
function setGraphMode(mode, options = {}) {
  const { source = 'auto' } = options;
  if (source === 'user') {
    graphModeUserOverride = mode; // Preserve user selection
  }
  const targetMode = graphModeUserOverride || mode;
  setValue('graphMode', targetMode);
  // ...
}
```

### Issue 5: Omni Graph Activation Toggles Twice
**Symptom:** Clicking Omni graph radio triggers two render cycles  
**Cause:** `activateGraphItem()` calls `setGraphFocus(true)`, which triggers mode change, which calls `handleGraphPanelToggle()`, which calls `activateGraphItem()` again  
**Workaround:** Pass `keepFocus` option to skip redundant focus change  
**Location:** `gl-dashboard.js:3803-3828`

**Code:**
```javascript
async function activateGraphItem(key, options = {}) {
  const keepFocus = options.keepFocus || false;
  ensureGraphExpanded();
  const data = await loadGraphDataset(key, { force: options.force });
  if (!keepFocus) {
    setGraphFocus(data.source === 'omni'); // Only set focus if not preserved
  }
  timeseriesGraph.setData(data);
  syncGraphModeForContext();
}
```

### Issue 6: Large Payload Timeout
**Symptom:** RAP timeseries fetch times out after 30 seconds  
**Cause:** Query Engine processes 500+ subcatchments × 24 years × 8 bands (96k rows)  
**Workaround:** Increase fetch timeout, or paginate query with year range filters  
**Location:** `data/query-engine.js:18-28`

**Mitigation:**
```javascript
const resp = await fetch(targetUrl, {
  method: 'POST',
  headers: { ... },
  body: JSON.stringify(payload),
  signal: AbortSignal.timeout(60000) // Increase to 60s
});
```

### Issue 7: Subcatchment Label Duplication
**Symptom:** Multiple labels appear for same subcatchment (MultiPolygon features)  
**Cause:** GeoJSON has multiple features per topaz_id (split geometries)  
**Workaround:** Track seen IDs in `buildSubcatchmentLabelsLayer()` and skip duplicates  
**Location:** `gl-dashboard.js:2163-2180`

**Code:**
```javascript
function buildSubcatchmentLabelsLayer() {
  const seenIds = new Set();
  const labelData = [];
  features.forEach((feature) => {
    const topazId = feature.properties.TopazID;
    const idKey = String(topazId);
    if (seenIds.has(idKey)) return; // Skip duplicates
    seenIds.add(idKey);
    // ... compute centroid and add label
  });
  return new deck.TextLayer({ data: labelData });
}
```

## Future Enhancements

### Planned Features
1. **URL State Persistence:** Encode layer selections, year, scenario in query params
2. **Export Tools:** Download current view as PNG/PDF, export graph data as CSV
3. **Animation Recording:** Capture year slider playback as video
4. **Custom Basemap Upload:** Allow users to add custom tile layers
5. **3D Terrain Overlay:** Use deck.gl TerrainLayer for elevation visualization
6. **Real-time Updates:** WebSocket connection for live model runs

### Performance Optimizations
1. **Web Worker Offloading:** Move colormap computation to worker thread
2. **Progressive Loading:** Render low-res version first, then upgrade
3. **Virtualized Layer List:** Render only visible layers in long category lists
4. **IndexedDB Caching:** Persist summaries in browser for offline access

### Accessibility Improvements
1. **Keyboard Navigation:** Arrow keys to navigate layer list, tab to graph controls
2. **Screen Reader Support:** ARIA labels for all interactive elements
3. **High Contrast Mode:** Respect `prefers-contrast` media query
4. **Legend Text Alternatives:** Provide tabular legend data for screen readers

---

## Appendix A: Key File Paths

| Component | Path |
|-----------|------|
| Main script | `wepppy/weppcloud/static/js/gl-dashboard.js` |
| State management | `wepppy/weppcloud/static/js/gl-dashboard/state.js` |
| Configuration | `wepppy/weppcloud/static/js/gl-dashboard/config.js` |
| Layer detection | `wepppy/weppcloud/static/js/gl-dashboard/layers/detector.js` |
| Layer rendering | `wepppy/weppcloud/static/js/gl-dashboard/layers/renderer.js` |
| Map controller | `wepppy/weppcloud/static/js/gl-dashboard/map/controller.js` |
| Layer utilities | `wepppy/weppcloud/static/js/gl-dashboard/map/layers.js` |
| Timeseries graph | `wepppy/weppcloud/static/js/gl-dashboard/graphs/timeseries-graph.js` |
| Graph loaders | `wepppy/weppcloud/static/js/gl-dashboard/graphs/graph-loaders.js` |
| Query Engine | `wepppy/weppcloud/static/js/gl-dashboard/data/query-engine.js` |
| Template | `wepppy/weppcloud/templates/gl_dashboard.htm` |
| Smoke tests | `tests/gl-dashboard-exploration.spec.mjs` |

## Appendix B: Selector Reference

| Element | Selector | Purpose |
|---------|----------|---------|
| Map container | `#gl-dashboard-map` | deck.gl render target |
| Layer list | `#gl-layer-list` | Sidebar layer checkboxes |
| Graph list | `#gl-graph-list` | Sidebar graph radios |
| Legends panel | `#gl-legends-panel` | Floating legends overlay |
| Legends content | `#gl-legends-content` | Legend items container |
| Graph panel | `#gl-graph` | Bottom graph panel |
| Graph canvas | `#gl-graph-canvas` | Canvas element for rendering |
| Graph tooltip | `#gl-graph-tooltip` | Hover tooltip |
| Year slider | `#gl-year-slider` | Year slider container |
| Year slider input | `#gl-year-slider-input` | Range input |
| Year slider value | `#gl-year-slider-value` | Current year display |
| Basemap selector | `#gl-basemap-select` | Basemap dropdown |
| Scenario selector | `#gl-scenario-select` | Scenario dropdown |
| Comparison toggle | `#gl-comparison-toggle` | Comparison checkbox |
| Subcatchments toggle | `#gl-subcatchments-toggle` | Subcatchments checkbox |
| Subcatchment labels toggle | `#gl-subcatchment-labels-toggle` | Labels checkbox |
| Graph mode buttons | `[data-graph-mode]` | Min/split/full buttons |

## Appendix C: Query Engine Payload Examples

### Landuse Summary
```json
{
  "datasets": [
    { "path": "landuse/out.parquet", "alias": "landuse" },
    { "path": "watershed/hillslopes.parquet", "alias": "hill" }
  ],
  "joins": [
    { "left": "landuse", "right": "hill", "on": "wepp_id", "type": "inner" }
  ],
  "columns": ["hill.topaz_id"],
  "aggregations": [
    { "sql": "MODE(landuse.dom)", "alias": "dom" }
  ],
  "group_by": ["hill.topaz_id"]
}
```

### WEPP Yearly (Year Filter)
```json
{
  "datasets": [
    { "path": "wepp/output/loss/hill_loss.parquet", "alias": "loss" },
    { "path": "watershed/hillslopes.parquet", "alias": "hill" }
  ],
  "joins": [
    { "left": "loss", "right": "hill", "on": "wepp_id", "type": "inner" }
  ],
  "columns": ["hill.topaz_id"],
  "aggregations": [
    { "sql": "SUM(loss.runoff)", "alias": "runoff" },
    { "sql": "SUM(loss.sedyld)", "alias": "sedyld" }
  ],
  "filters": [
    { "column": "loss.year", "op": "=", "value": 2023 }
  ],
  "group_by": ["hill.topaz_id"]
}
```

### RAP Timeseries (All Years)
```json
{
  "datasets": [
    { "path": "rap/rap.parquet", "alias": "rap" },
    { "path": "watershed/hillslopes.parquet", "alias": "hill" }
  ],
  "joins": [
    { "left": "rap", "right": "hill", "on": "wepp_id", "type": "inner" }
  ],
  "columns": ["hill.topaz_id", "rap.year"],
  "aggregations": [
    { "sql": "AVG(rap.AFG)", "alias": "AFG" }
  ],
  "group_by": ["hill.topaz_id", "rap.year"],
  "order_by": [
    { "column": "rap.year", "direction": "ASC" }
  ]
}
```

---

**Document Status:** Complete  
**Review:** Ready for developer onboarding and testing team handoff  
**Maintenance:** Update when new layer types or graph modes added
