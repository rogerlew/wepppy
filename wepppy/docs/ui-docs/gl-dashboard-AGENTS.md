# GL Dashboard - Agent Development Guide
> Developer notes, pitfalls, and conventions for working with the WEPPcloud GL Dashboard

**Audience:** AI coding agents, human developers  
**Scope:** `wepppy/weppcloud/static/js/gl-dashboard.js` and module tree  
**Last Updated:** 2025-12-15

## Table of Contents
- [Critical Conventions](#critical-conventions)
- [Architecture Patterns](#architecture-patterns)
- [Common Pitfalls](#common-pitfalls)
- [Troubleshooting Checklist](#troubleshooting-checklist)
- [Testing Setup](#testing-setup)
- [Module Modification Guidelines](#module-modification-guidelines)
- [Query Engine Integration](#query-engine-integration)
- [Performance Guardrails](#performance-guardrails)

## Critical Conventions

### Idempotent State Synchronization
**Rule:** `syncGraphModeForContext()` MUST be idempotent to prevent infinite recursion.

**Pattern:**
```javascript
function syncGraphModeForContext() {
  const st = getState();
  const contextKey = `${graphCapable}-${rapActive}-${yearlyActive}-${userOverride}-${activeGraphKey}`;
  
  // CRITICAL: Early return if context unchanged
  if (contextKey === lastGraphContextKey) {
    return;
  }
  lastGraphContextKey = contextKey;
  
  // ... proceed with mode updates
}
```

**Why:** This function is called from:
- `setGraphMode()` → `setGraphFocus()` → `syncGraphModeForContext()`
- `applyLayers()` → `syncGraphModeForContext()`
- Layer toggle handlers → `applyLayers()` → `syncGraphModeForContext()`

Without the context key check, these call chains form loops.

### TDZ (Temporal Dead Zone) Avoidance
**Issue:** ES6 `let`/`const` declarations are not hoisted, causing ReferenceError if accessed before declaration line.

**Bad:**
```javascript
syncGraphModeForContext(); // Called during init
// ... 50 lines later ...
let lastGraphContextKey = null; // ❌ TDZ error
```

**Good:**
```javascript
// Use var to hoist declaration to function scope
var lastGraphContextKey = null; // eslint-disable-line no-var
// ... initialization code ...
syncGraphModeForContext(); // ✅ Safe, variable exists
```

**Location:** `gl-dashboard.js:73`  
**Rule:** Any variable referenced during module init or in recursive functions should use `var`.

### setGraphCollapsed Guards
**Rule:** Always check if `graphPanelEl` exists before manipulating classes.

**Pattern:**
```javascript
function setGraphCollapsed(collapsed, options = {}) {
  if (!graphPanelEl) return; // Guard against missing DOM element
  
  graphPanelEl.classList.toggle('is-collapsed', collapsed);
  
  // ... rest of logic
}
```

**Why:** In test environments or when dashboard loads before DOM ready, elements may not exist. Silent failures are preferable to crashes.

### Year Slider Init Ordering
**Critical Sequence:**
1. Initialize slider with climate context (start/end years)
2. Attach event listeners
3. Call `syncGraphModeForContext()` to set initial visibility
4. Only then allow layer toggles to modify slider state

**Code:**
```javascript
// 1. Init slider
if (climateCtx && climateCtx.startYear != null) {
  yearSlider.init({
    startYear: climateCtx.startYear,
    endYear: climateCtx.endYear,
    hasObserved: climateCtx.hasObserved,
  });
}

// 2. Attach listeners
yearSlider.on('change', (year) => {
  setValue('rapSelectedYear', year);
  refreshRapData();
});

// 3. Initial sync
syncGraphModeForContext();

// 4. Bind layer toggles
bindLayerToggles();
```

**Why:** If slider isn't initialized before `syncGraphModeForContext()`, visibility checks fail silently. If listeners aren't attached, year changes don't propagate.

## Architecture Patterns

### Module Boundaries
**Principle:** Keep concerns separated across module files.

| Module | Responsibility | Should NOT Contain |
|--------|---------------|-------------------|
| `state.js` | State storage, change notifications | DOM access, fetch calls |
| `config.js` | Static constants, definitions | Runtime state, mutations |
| `detector.js` | Data fetching, layer discovery | Rendering logic, deck.gl calls |
| `renderer.js` | Layer construction | Data fetching, state mutations |
| `controller.js` | deck.gl wrapper | Business logic, data transforms |
| `timeseries-graph.js` | Canvas rendering | Query Engine calls, state updates |

**Violation Example:**
```javascript
// ❌ Bad: State mutation in detector module
export async function detectRapOverlays() {
  const data = await fetch(...);
  setValue('rapSummary', data); // Wrong module for state changes
}

// ✅ Good: Detector returns data, caller updates state
export async function detectRapOverlays() {
  const data = await fetch(...);
  return { rapSummary: data }; // Caller decides what to do
}
```

### State vs. Cached Data
**Rule:** Distinguish between "state" (user selections, UI mode) and "cached data" (query results, summaries).

**State Properties (in `state.js`):**
- `currentBasemapKey`: User selection
- `graphMode`: UI mode (minimized/split/full)
- `rapSelectedYear`: Slider position

**Cached Data (also in `state.js` but semantically different):**
- `rapSummary`: Query result for current year
- `weppYearlySummary`: Query result for current year
- `graphDataCache`: Expensive graph datasets

**Pattern:** When scenario changes, clear cached data but preserve state.

```javascript
async function setScenario(scenarioPath) {
  currentScenarioPath = scenarioPath;
  
  // Clear cached data
  setState({
    rapSummary: null,
    weppYearlySummary: null,
    graphDataCache: {},
    hillLossCache: {},
  });
  
  // Preserve state
  // rapSelectedYear, graphMode, etc. stay intact
  
  await detectOverlays();
}
```

### Subscription Pattern (Unused But Available)
**Current:** State changes trigger synchronous updates via direct function calls.  
**Available:** `subscribe(callback, keys)` allows modules to listen for specific state keys.

**Example (Future Enhancement):**
```javascript
// In timeseries-graph.js
subscribe((state, changedKeys) => {
  if (changedKeys.includes('rapSelectedYear')) {
    timeseriesGraph.setCurrentYear(state.rapSelectedYear);
  }
}, ['rapSelectedYear']);
```

**Why Not Used:** Main script orchestrates updates via explicit function calls for clarity. Subscriptions add indirection that complicates debugging.

## Common Pitfalls

### Pitfall 1: Forgetting `await` on Async Layer Detection
**Symptom:** Layers don't appear after toggling checkbox, no errors logged.

**Cause:**
```javascript
layerCheckbox.addEventListener('change', (e) => {
  detectRapOverlays(); // ❌ Missing await, function returns immediately
  applyLayers(); // Called before detection completes
});
```

**Fix:**
```javascript
layerCheckbox.addEventListener('change', async (e) => {
  await detectRapOverlays(); // ✅ Wait for fetch to complete
  applyLayers();
});
```

### Pitfall 2: Mutating GeoJSON in-place
**Symptom:** Deck.gl layer doesn't update after data change.

**Cause:** Deck.gl uses shallow reference equality to detect changes. Mutating `subcatchmentsGeoJson.features` doesn't trigger re-render.

**Bad:**
```javascript
subcatchmentsGeoJson.features.forEach(f => {
  f.properties.value = newValue; // ❌ Mutation doesn't trigger update
});
```

**Good:**
```javascript
subcatchmentsGeoJson = {
  ...subcatchmentsGeoJson,
  features: subcatchmentsGeoJson.features.map(f => ({
    ...f,
    properties: { ...f.properties, value: newValue }
  }))
}; // ✅ New reference triggers update
```

**Better:** Don't modify GeoJSON at all. Store attribute data in separate summary objects and join in `getFillColor` callback.

### Pitfall 3: updateTriggers with Inline Functions
**Symptom:** Layer re-renders on every frame (performance tank).

**Cause:**
```javascript
new deck.GeoJsonLayer({
  id: 'wepp-runoff',
  getFillColor: (f) => colorForValue(f.properties.TopazID),
  updateTriggers: {
    getFillColor: [() => colorForValue] // ❌ New function every render
  }
});
```

**Fix:**
```javascript
new deck.GeoJsonLayer({
  id: 'wepp-runoff',
  getFillColor: (f) => colorForValue(f.properties.TopazID),
  updateTriggers: {
    getFillColor: [weppSummary, weppStatistic, weppRanges.runoff_volume] // ✅ Stable references
  }
});
```

**Rule:** `updateTriggers` should contain only primitive values or stable object references. Never inline functions or `new Object()`.

### Pitfall 4: Clearing Year Slider Too Early
**Symptom:** Year slider disappears when toggling between RAP bands.

**Cause:**
```javascript
function deselectAllSubcatchmentOverlays() {
  // ...
  yearSlider.hide(); // ❌ Hides slider even when switching between RAP bands
}
```

**Fix:**
```javascript
function deselectAllSubcatchmentOverlays() {
  rapLayers.forEach(l => l.visible = false);
  rapCumulativeMode = false;
  // Don't hide slider here, let syncGraphModeForContext() decide
}

function syncGraphModeForContext() {
  // ...
  if (rapActive || yearlyActive) {
    yearSlider.show();
  } else {
    yearSlider.hide(); // ✅ Centralized visibility logic
  }
}
```

**Rule:** Year slider visibility should ONLY be controlled by `syncGraphModeForContext()`.

### Pitfall 5: Graph Data Race Conditions
**Symptom:** Graph renders stale data when rapidly clicking graph radios.

**Cause:**
```javascript
async function activateGraphItem(key) {
  const data = await loadGraphDataset(key); // Slow async call
  timeseriesGraph.setData(data); // By the time this runs, user clicked another graph
}
```

**Fix:** Track active request and cancel stale renders:
```javascript
let activeGraphRequest = null;

async function activateGraphItem(key, options = {}) {
  const requestId = Date.now();
  activeGraphRequest = requestId;
  
  const data = await loadGraphDataset(key, options);
  
  // Check if this request is still current
  if (activeGraphRequest !== requestId) {
    return; // User clicked another graph, discard this data
  }
  
  timeseriesGraph.setData(data);
}
```

**Status:** Not currently implemented, known issue. Document for future enhancement.

### Pitfall 6: Memory Leak in Event Listeners
**Symptom:** After switching scenarios multiple times, dashboard becomes sluggish.

**Cause:** Event listeners not cleaned up when rebuilding UI.

**Bad:**
```javascript
function updateLayerList() {
  layerListEl.innerHTML = ''; // Clear DOM
  // ... rebuild checkboxes ...
  checkboxes.forEach(cb => {
    cb.addEventListener('change', handler); // ❌ Old listeners still attached
  });
}
```

**Good:**
```javascript
const layerHandlers = new WeakMap();

function updateLayerList() {
  // Remove old listeners
  layerListEl.querySelectorAll('input').forEach(input => {
    const handler = layerHandlers.get(input);
    if (handler) {
      input.removeEventListener('change', handler);
    }
  });
  
  layerListEl.innerHTML = ''; // Clear DOM
  
  // ... rebuild checkboxes ...
  checkboxes.forEach(cb => {
    const handler = (e) => { /* ... */ };
    layerHandlers.set(cb, handler);
    cb.addEventListener('change', handler); // ✅ Tracked for cleanup
  });
}
```

**Status:** Current implementation uses `dataset.glBound` flags to prevent duplicate bindings. Acceptable but not ideal for dynamic list updates.

## Troubleshooting Checklist

### Graph Panel Stuck in Minimized Mode
**Check:**
1. Is `graphControlsEnabled` true? (Console: `window.glDashboardGraphControlsEnabled`)
2. Is a graph-capable layer active? (RAP, WEPP Yearly, or Omni graph)
3. Is `graphModeUserOverride` set to 'minimized'? (Console: `window.glDashboardGraphModeUserOverride`)
4. Are mode buttons getting `is-disabled` class? (Inspect button elements)

**Fix:**
```javascript
// In browser console
window.glDashboardSetGraphMode('split', { source: 'user' });
window.glDashboardGraphControlsEnabled = true;
```

### Year Slider Not Appearing
**Check:**
1. Is slider initialized? (Console: `window.glDashboardYearSlider._initialized`)
2. Is RAP or WEPP Yearly layer active? (Console: `window.rapLayers`, `window.weppYearlyLayers`)
3. Does metadata have valid years? (Console: `window.rapMetadata.years`)
4. Is slider element hidden via CSS? (Inspect `#gl-year-slider` classes)

**Fix:**
```javascript
// In browser console
const slider = window.glDashboardYearSlider;
slider.init({ startYear: 2000, endYear: 2023 });
slider.show();
```

### Layers Not Rendering After Toggle
**Check:**
1. Did checkbox state change? (Inspect checkbox `checked` attribute)
2. Was `applyLayers()` called? (Add `console.log` in function)
3. Is summary data loaded? (Console: `window.weppSummary`, `window.rapSummary`)
4. Is deck.gl layer in stack? (Console: `window.glDashboardMapController.deckgl.layers`)
5. Are there JavaScript errors in console?

**Debug:**
```javascript
// In gl-dashboard.js, add logging
function applyLayers() {
  const stack = layerUtils.buildLayerStack(baseLayer);
  console.log('Applying layers:', stack.length, stack.map(l => l.id));
  mapController.applyLayers(stack);
}
```

### Memory Spike When Loading RAP Timeseries
**Check:**
1. How many years? (Console: `window.rapMetadata.years.length`)
2. How many subcatchments? (Console: `window.subcatchmentsGeoJson.features.length`)
3. Payload size: years × bands × subcatchments × 8 bytes (rough estimate)

**Mitigation:**
- Aggregate by region (sum subcatchments into larger groups)
- Load only visible years (year range slider)
- Use binary format (parquet) instead of JSON
- Offload processing to Web Worker

**Temporary Fix:**
```javascript
// Limit graph to subset of subcatchments
function loadRapTimeseriesData() {
  const topazIds = Object.keys(rapSummary).slice(0, 50); // Only first 50
  // ... build series for subset
}
```

### Comparison Mode Not Showing Differences
**Check:**
1. Is comparison toggle checked? (Console: `window.comparisonMode`)
2. Are base summaries loaded? (Console: `window.baseSummaryCache`)
3. Are diff ranges computed? (Console: `window.comparisonDiffRanges`)
4. Is rdbu colormap applied? (Inspect layer `updateTriggers.getFillColor`)

**Debug:**
```javascript
// In browser console
console.log('Comparison mode:', window.comparisonMode);
console.log('Base cache:', Object.keys(window.baseSummaryCache || {}));
console.log('Diff ranges:', window.comparisonDiffRanges);
```

## Testing Setup

### Mocking deck.gl for Unit Tests
**Pattern:** Stub deck global with minimal mock classes.

```javascript
// tests/gl-dashboard/mocks/deck-mock.js
export const mockDeck = {
  Deck: class MockDeck {
    constructor(props) {
      this.props = props;
      this.layers = props.layers || [];
    }
    setProps(props) {
      Object.assign(this.props, props);
      if (props.layers) this.layers = props.layers;
    }
  },
  GeoJsonLayer: class MockGeoJsonLayer {
    constructor(props) {
      this.id = props.id;
      this.props = props;
    }
  },
  TileLayer: class MockTileLayer {
    constructor(props) {
      this.id = props.id;
      this.props = props;
    }
  },
  BitmapLayer: class MockBitmapLayer {
    constructor(props) {
      this.id = props.id;
      this.props = props;
    }
  },
  TextLayer: class MockTextLayer {
    constructor(props) {
      this.id = props.id;
      this.props = props;
    }
  }
};

// In test setup
beforeEach(() => {
  global.deck = mockDeck;
  global.createColormap = (opts) => {
    // Return fake colormap
    return Array.from({ length: 256 }, (_, i) => [i, i, i, 255]);
  };
});
```

### Stubbing Query Engine
**Pattern:** Mock fetch calls with fixture data.

```javascript
// tests/gl-dashboard/mocks/query-engine-mock.js
import rapSummaryFixture from '../fixtures/rap-summary.json';

beforeEach(() => {
  global.fetch = jest.fn((url, options) => {
    if (url.includes('/query-engine/') && options.method === 'POST') {
      const payload = JSON.parse(options.body);
      
      // Match query by dataset path
      if (payload.datasets.some(d => d.path.includes('rap.parquet'))) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ records: rapSummaryFixture })
        });
      }
    }
    
    return Promise.reject(new Error('Unmocked fetch: ' + url));
  });
});
```

### Fixture Data Format
**RAP Summary:**
```json
[
  { "topaz_id": "123", "year": 2000, "AFG": 12.5, "PFG": 8.3, "BGR": 5.1 },
  { "topaz_id": "123", "year": 2001, "AFG": 13.2, "PFG": 8.9, "BGR": 5.3 },
  { "topaz_id": "456", "year": 2000, "AFG": 10.1, "PFG": 7.2, "BGR": 4.8 }
]
```

**WEPP Summary:**
```json
{
  "123": {
    "runoff_volume": 45.2,
    "soil_loss": 2.1,
    "sediment_yield": 1.8
  },
  "456": {
    "runoff_volume": 32.8,
    "soil_loss": 1.5,
    "sediment_yield": 1.2
  }
}
```

### Playwright Selector Stability
**Rule:** Use stable IDs or data attributes, not CSS classes.

**Good:**
```javascript
await page.click('#layer-RAP-AFG'); // ✅ ID won't change
await page.click('[data-layer-key="AFG"]'); // ✅ Explicit attribute
```

**Bad:**
```javascript
await page.click('.gl-layer-item input'); // ❌ Matches all layers
await page.click('details:nth-child(2) input'); // ❌ Breaks if list reorders
```

**Smoke Test Pattern:**
```javascript
test('layer toggle updates legends', async ({ page }) => {
  await page.goto('/runs/test/dev_unit_1/gl-dashboard');
  
  // Wait for initial render
  await page.waitForSelector('#gl-layer-list');
  await page.waitForTimeout(1000); // Allow detection to complete
  
  // Find first RAP layer checkbox
  const rapCheckbox = await page.$('input[id^="layer-RAP-"]');
  expect(rapCheckbox).not.toBeNull();
  
  // Toggle and wait for render
  await rapCheckbox.click();
  await page.waitForTimeout(2000); // Allow data fetch
  
  // Verify legend appeared
  const legend = await page.$('.gl-legend-item:not([style*="display: none"])');
  expect(legend).not.toBeNull();
  
  const legendTitle = await legend.$eval('h5', el => el.textContent);
  expect(legendTitle).toContain('RAP');
});
```

## Module Modification Guidelines

### Adding a New Layer Type
**Checklist:**
1. Add detector function in `layers/detector.js` (e.g., `detectMyLayerOverlays()`)
2. Add layer builder in `layers/renderer.js` or `map/layers.js`
3. Add state properties in `state.js` (e.g., `myLayerSummary`, `myLayerLayers`)
4. Call detector in main script initialization
5. Bind checkboxes in `updateLayerList()`
6. Update `deselectAllSubcatchmentOverlays()` if mutually exclusive
7. Add legend rendering logic in `updateLegendsPanel()`
8. Add to `syncGraphModeForContext()` if layer supports timeseries graphs

**Code Template:**
```javascript
// In layers/detector.js
export async function detectMyLayerOverlays({ buildBaseUrl, postQueryEngine }) {
  const payload = {
    datasets: [{ path: 'my-layer/data.parquet', alias: 'ml' }],
    columns: ['ml.topaz_id', 'ml.value'],
    group_by: ['ml.topaz_id']
  };
  const result = await postQueryEngine(payload);
  if (!result || !result.records) return null;
  
  const summary = {};
  result.records.forEach(row => {
    summary[String(row.topaz_id)] = { value: row.value };
  });
  
  return {
    myLayerSummary: summary,
    myLayerLayers: [
      { key: 'my-layer', label: 'My Layer', mode: 'value', visible: false }
    ]
  };
}

// In main script
async function detectAllOverlays() {
  // ... existing detectors ...
  const myLayerResult = await detectMyLayerOverlays({ buildBaseUrl, postQueryEngine });
  if (myLayerResult) {
    setState({
      myLayerSummary: myLayerResult.myLayerSummary,
      myLayerLayers: myLayerResult.myLayerLayers
    });
  }
}
```

### Adding a New Graph Type
**Checklist:**
1. Add graph definition in `config.js` `GRAPH_DEFS` array
2. Add loader function in `graphs/graph-loaders.js`
3. Update `loadGraphDataset()` dispatcher
4. Add rendering case in `timeseries-graph.js` (e.g., `_renderMyGraph()`)
5. Update `setData()` validation in `_hasData()`
6. Add tooltip formatter if custom format needed

**Code Template:**
```javascript
// In config.js
export const GRAPH_DEFS = [
  // ... existing defs ...
  {
    key: 'my-graphs',
    title: 'My Custom Graphs',
    items: [
      { key: 'my-graph-scatter', label: 'Scatter Plot', type: 'scatter' }
    ]
  }
];

// In graphs/graph-loaders.js
async function loadMyGraphScatter() {
  const result = await postQueryEngine({
    datasets: [{ path: 'my-data.parquet', alias: 'md' }],
    columns: ['md.x', 'md.y']
  });
  
  return {
    type: 'scatter',
    title: 'Scatter Plot',
    source: 'custom',
    points: result.records.map(r => ({ x: r.x, y: r.y }))
  };
}

// In timeseries-graph.js
_hasData(data) {
  // ... existing checks ...
  if (data.type === 'scatter') {
    return Array.isArray(data.points) && data.points.length > 0;
  }
}

render() {
  const type = this._data.type || 'line';
  if (type === 'scatter') return this._renderScatter();
  // ... existing types ...
}

_renderScatter() {
  const { points } = this._data;
  // ... draw points on canvas ...
}
```

### Modifying State Schema
**Rule:** When adding new state properties, update ALL of these:

1. **state.js:** Add to initial state object
2. **gl-dashboard.js:** Add to `bindStateKeys()` array if exposing globally
3. **AGENTS.md (this file):** Update state table in spec
4. **gl-dashboard.md:** Update state table in spec

**Pattern:**
```javascript
// 1. In state.js
const state = {
  // ... existing properties ...
  myNewProperty: null, // Add here
};

// 2. In gl-dashboard.js
bindStateKeys([
  // ... existing keys ...
  'myNewProperty', // Add here
]);

// 3. In spec docs
Update state tables with:
myNewProperty: null  // Description of property
```

## Query Engine Integration

### Query Payload Best Practices

**DO:**
- Use aliases for clarity: `{ path: 'wepp/output/loss/hill_loss.parquet', alias: 'loss' }`
- Specify columns explicitly: `columns: ['loss.sedyld', 'hill.topaz_id']`
- Filter early: `filters: [{ column: 'loss.year', op: '=', value: 2023 }]`
- Aggregate when possible: `aggregations: [{ sql: 'SUM(loss.sedyld)', alias: 'total' }]`

**DON'T:**
- Select `*` without aggregation (returns entire table)
- Join without `on` clause (cartesian product)
- Forget `group_by` when using aggregations (query fails)
- Use raw SQL strings in filters (use structured format)

**Example - Good Query:**
```javascript
const payload = {
  datasets: [
    { path: 'wepp/output/loss/hill_loss.parquet', alias: 'loss' },
    { path: 'watershed/hillslopes.parquet', alias: 'hill' }
  ],
  joins: [
    { left: 'loss', right: 'hill', on: 'wepp_id', type: 'inner' }
  ],
  columns: ['hill.topaz_id'],
  aggregations: [
    { sql: 'AVG(loss.sedyld)', alias: 'avg_sediment' },
    { sql: 'SUM(loss.runoff)', alias: 'total_runoff' }
  ],
  filters: [
    { column: 'loss.year', op: '>=', value: 2020 }
  ],
  group_by: ['hill.topaz_id'],
  order_by: [
    { column: 'hill.topaz_id', direction: 'ASC' }
  ]
};
```

### Error Handling
**Pattern:** Always check response status and handle missing data gracefully.

```javascript
async function fetchSummary() {
  try {
    const result = await postQueryEngine(payload);
    
    if (!result || !result.records) {
      console.warn('Query returned no records');
      return null;
    }
    
    if (result.error) {
      console.error('Query error:', result.error);
      return null;
    }
    
    return result.records;
  } catch (err) {
    console.error('Query Engine fetch failed:', err);
    return null;
  }
}
```

**Fallback Strategy:**
1. Log warning to console (user can inspect)
2. Return null or empty object
3. Caller checks return value and handles missing data
4. UI shows "No data available" message, not crash

### Caching Strategy
**Pattern:** Cache expensive queries, invalidate on scenario change.

```javascript
const hillLossCache = {};

async function loadHillLoss(scenarioPath) {
  const cacheKey = scenarioPath || 'base';
  
  if (hillLossCache[cacheKey]) {
    return hillLossCache[cacheKey]; // Cache hit
  }
  
  const result = await postQueryEngineForScenario(payload, scenarioPath);
  hillLossCache[cacheKey] = result; // Store in cache
  
  return result;
}

// Invalidate on scenario change
function setScenario(scenarioPath) {
  hillLossCache = {}; // Clear all caches
  // ... rest of logic
}
```

## Performance Guardrails

### Render Budget
**Target:** 60 FPS (16.67ms per frame)  
**Budget Allocation:**
- deck.gl layer updates: 5-8ms
- Canvas graph render: 3-5ms
- DOM updates (legends, UI): 2-3ms
- JavaScript logic: 1-2ms
- Slack: 3-5ms

**Profiling:**
```javascript
function applyLayers() {
  const t0 = performance.now();
  const stack = layerUtils.buildLayerStack(baseLayer);
  const t1 = performance.now();
  mapController.applyLayers(stack);
  const t2 = performance.now();
  
  if (t2 - t0 > 16) {
    console.warn(`applyLayers took ${(t2 - t0).toFixed(2)}ms (budget: 16ms)`);
    console.log(`  - buildLayerStack: ${(t1 - t0).toFixed(2)}ms`);
    console.log(`  - deck.setProps: ${(t2 - t1).toFixed(2)}ms`);
  }
}
```

### Layer Count Limits
**Recommendation:**
- Max basemap + 5 vector overlays + 2 raster layers
- Beyond 8 layers, performance degrades on mobile

**Enforcement:**
```javascript
function buildLayerStack(baseLayer) {
  const layers = [baseLayer];
  
  // Add subcatchments (always visible)
  if (subcatchmentsVisible) {
    layers.push(buildSubcatchmentsLayer());
  }
  
  // Add overlays (mutually exclusive enforced elsewhere)
  const overlays = [
    ...buildLanduseLayers(),
    ...buildSoilsLayers(),
    ...buildWeppLayers(),
    // ... etc
  ].filter(Boolean);
  
  if (overlays.length > 5) {
    console.warn(`Too many overlays (${overlays.length}), limiting to 5`);
    layers.push(...overlays.slice(0, 5));
  } else {
    layers.push(...overlays);
  }
  
  return layers;
}
```

### Query Timeout Escalation
**Pattern:** Start with short timeout, retry with longer timeout on failure.

```javascript
async function fetchWithRetry(url, payload, options = {}) {
  const timeouts = [15000, 30000, 60000]; // 15s, 30s, 60s
  
  for (let i = 0; i < timeouts.length; i++) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeouts[i]);
      
      const resp = await fetch(url, {
        ...options,
        signal: controller.signal,
        body: JSON.stringify(payload)
      });
      
      clearTimeout(timeoutId);
      
      if (resp.ok) {
        return await resp.json();
      }
    } catch (err) {
      if (i === timeouts.length - 1) {
        throw err; // Last retry, give up
      }
      console.warn(`Query timeout at ${timeouts[i]}ms, retrying...`);
    }
  }
}
```

### Memory Pressure Monitoring
**Pattern:** Track cache sizes and evict when exceeding threshold.

```javascript
const MAX_CACHE_SIZE_MB = 100;

function getCacheSizeMB() {
  const caches = [
    graphDataCache,
    hillLossCache,
    channelLossCache,
    weppYearlyCache,
    rapSummary
  ];
  
  const json = JSON.stringify(caches);
  const bytes = new Blob([json]).size;
  return bytes / (1024 * 1024);
}

function evictOldestCache() {
  // Simple LRU: clear least recently used cache
  const candidates = [
    { name: 'graphDataCache', value: graphDataCache, lastAccess: lastGraphDataAccess },
    { name: 'hillLossCache', value: hillLossCache, lastAccess: lastHillLossAccess },
    // ... etc
  ];
  
  candidates.sort((a, b) => a.lastAccess - b.lastAccess);
  const oldest = candidates[0];
  
  console.warn(`Evicting cache: ${oldest.name} (last access: ${oldest.lastAccess})`);
  Object.keys(oldest.value).forEach(k => delete oldest.value[k]);
}

function checkMemoryPressure() {
  const sizeMB = getCacheSizeMB();
  if (sizeMB > MAX_CACHE_SIZE_MB) {
    console.warn(`Cache size: ${sizeMB.toFixed(2)} MB, evicting oldest...`);
    evictOldestCache();
  }
}

// Call after large data loads
async function loadRapTimeseriesData() {
  // ... fetch data ...
  checkMemoryPressure();
}
```

---

## Quick Reference Card

### When Adding Code:
- [ ] Check for TDZ issues (use `var` if referenced early)
- [ ] Add idempotency guards to recursive functions
- [ ] Use stable references in `updateTriggers`
- [ ] Add null checks before DOM manipulation
- [ ] Await async detector functions
- [ ] Update both `.md` spec files if changing API

### When Debugging:
- [ ] Check console for fetch errors
- [ ] Verify state via `window.*` globals
- [ ] Inspect deck.gl layer stack: `window.glDashboardMapController.deckgl.layers`
- [ ] Profile with `performance.now()` if sluggish
- [ ] Test in isolation (disable other layers)

### When Testing:
- [ ] Mock deck.gl global
- [ ] Mock fetch with fixtures
- [ ] Use stable selectors (IDs, data attributes)
- [ ] Wait for async operations (`waitForTimeout`, `waitForSelector`)
- [ ] Check both happy path and error cases

---

**Maintenance:** Update this document when adding new patterns or discovering pitfalls. Keep examples concise and runnable.
