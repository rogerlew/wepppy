# GL Dashboard Refactoring Plan

> **Objective:** Systematically extract cohesive subsystems from `gl-dashboard.js` (4,513 lines) into separate modules, validated by Playwright regression testing at each phase.

## Test URLs for Regression Validation

All phases must pass the existing Playwright smoke tests against these runs:

- **Primary:** `https://wc.bearhive.duckdns.org/weppcloud/runs/minus-farce/disturbed9002_wbt/gl-dashboard`
- **Secondary:** `https://wc.bearhive.duckdns.org/weppcloud/runs/walk-in-obsessive-compulsive/disturbed9002_wbt/gl-dashboard`

### Running Tests

```bash
# Full suite against both runs
cd wepppy/weppcloud/static-src
GL_DASHBOARD_URL="https://wc.bearhive.duckdns.org/weppcloud/runs/minus-farce/disturbed9002_wbt/gl-dashboard" \
  npm run smoke -- tests/smoke/gl-dashboard-*.spec.js

GL_DASHBOARD_URL="https://wc.bearhive.duckdns.org/weppcloud/runs/walk-in-obsessive-compulsive/disturbed9002_wbt/gl-dashboard" \
  npm run smoke -- tests/smoke/gl-dashboard-*.spec.js

# Quick sanity check (state transitions only)
GL_DASHBOARD_URL="..." npm run smoke -- tests/smoke/gl-dashboard-state-transitions.spec.js
```

---

## Current Architecture Analysis

### File Size Breakdown (gl-dashboard.js ~4513 lines)

| Section | Line Range | Lines | Description |
|---------|------------|-------|-------------|
| Module imports & init | 1-75 | ~75 | Dynamic module loading |
| State bindings | 75-250 | ~175 | `bindStateKeys`, global accessors |
| Basemap & View State | 250-400 | ~150 | `createBaseLayer`, `setBasemap`, `toggleSubcatchments` |
| **Scenario/Comparison** | 400-800 | ~400 | `setScenario`, `setComparisonMode`, diff range computation |
| **Graph Mode Control** | 800-1050 | ~250 | `setGraphFocus`, `setGraphMode`, `syncGraphLayout`, mode buttons |
| **Year Slider** | 1230-1430 | ~200 | Slider controller object |
| Graph Controls UI | 1050-1230 | ~180 | Cumulative/Climate option rendering |
| **Color Functions** | 1530-2100 | ~570 | NLCD, viridis, winter, jet2, diverging, HSL helpers |
| **Layer Builders** | 2100-3200 | ~1100 | `build*Layers()`, fill/value functions per overlay type |
| **Data Refresh** | 3200-3500 | ~300 | `refresh*Data()`, `computeWeppYearlyRanges()` |
| **Graph Loaders** | 4000-4350 | ~350 | Omni graph builders (boxplots, outlet bars) |
| Detection & Init | 3800-4513 | ~700 | `detect*Overlays()`, `mapController` setup, `initializeDashboard()` |

### Already Modularized (in `gl-dashboard/` folder)

| Module | Purpose | Status |
|--------|---------|--------|
| `config.js` | Static constants | ✅ Complete |
| `state.js` | Reactive state store | ✅ Complete |
| `colors.js` | Color normalization helpers | ✅ Partial (some functions still in main file) |
| `data/query-engine.js` | Query Engine HTTP wrappers | ✅ Complete |
| `graphs/timeseries-graph.js` | Canvas graph rendering | ✅ Complete |
| `graphs/graph-loaders.js` | RAP/WEPP/Climate data loaders | ✅ Complete |
| `layers/detector.js` | Overlay detection | ✅ Complete |
| `layers/renderer.js` | Sidebar DOM rendering | ✅ Complete |
| `map/layers.js` | Deck layer builders + tooltip | ✅ Partial |
| `map/controller.js` | Deck.gl instance wrapper | ✅ Complete |

### Remaining in gl-dashboard.js (to extract)

1. **Year Slider Controller** (~200 lines) - Generic slider with play/pause
2. **Color Scale Functions** (~300 lines) - Colormap implementations still in main file
3. **WEPP/Layer Data Functions** (~600 lines) - Refresh handlers, range computation
4. **Init & Wiring** (~300 lines) - Detection orchestration, global hooks

---

## Phased Refactor Plan

### Phase 0: Pre-Refactor Baseline
**Duration:** 30 minutes

1. Run full Playwright suite against both test URLs
2. Document baseline pass/fail counts
3. Create git tag: `gl-dashboard-refactor-baseline`
4. Verify `node --check wepppy/weppcloud/static/js/gl-dashboard.js` passes (from repo root)

```bash
# Baseline recording (run from repo root: /workdir/wepppy)
cd wepppy/weppcloud/static-src
npm run smoke -- tests/smoke/gl-dashboard-*.spec.js 2>&1 | tee baseline-results.txt
```

---

### Phase 1: Scenario & Comparison Module
**Risk:** Low | **Lines:** ~400 | **Duration:** 2-3 hours  
**Status:** Complete – logic extracted to `gl-dashboard/scenario/manager.js` with injected deps; Playwright smoke passed.

**Extract to:** `gl-dashboard/scenario/manager.js`

**Functions to move:**
- `buildScenarioUrl(relativePath)`
- `buildBaseUrl(relativePath)`
- `setScenario(scenarioPath)`
- `setComparisonMode(enabled)`
- `loadBaseScenarioData()`
- `computeComparisonDiffRanges()`

> **Note:** `loadBaseWeppEventData()` and `computeWeppEventDiffRanges()` are moved to Phase 5 (WEPP Data) to keep all WEPP event logic consolidated. The scenario manager will call into the WEPP data manager for event comparison operations.

**New module contract:**
```javascript
// gl-dashboard/scenario/manager.js
export function createScenarioManager({
  ctx,
  getState,
  setValue,
  setState,
  postQueryEngine,
  postBaseQueryEngine,
  fetchWeppSummary,
  weppDataManager,    // injected: for loadBaseWeppEventData/computeWeppEventDiffRanges
  onScenarioChange,   // callback: triggers detect* and applyLayers
  onComparisonChange, // callback: triggers updateLegendsPanel
}) {
  return {
    buildScenarioUrl,
    buildBaseUrl,
    setScenario,
    setComparisonMode,
    loadBaseScenarioData,
    computeComparisonDiffRanges,
  };
}
```

**Regression tests:**
- `gl-dashboard-state-transitions.spec.js` - scenario selector changes
- Manual: Toggle comparison mode, verify diff colors

**Acceptance criteria:**
- [ ] Playwright suite green
- [ ] Scenario dropdown changes layers correctly
- [ ] Comparison toggle shows diverging colormaps
- [ ] No console errors

---

### Phase 2: Graph Mode Controller
**Risk:** Medium | **Lines:** ~250 | **Duration:** 2-3 hours  
**Status:** Complete – controller lives in `gl-dashboard/ui/graph-mode.js`; graph mode wiring updated; smoke passed.

**Extract to:** `gl-dashboard/ui/graph-mode.js`

**Functions to move:**
- `clearGraphModeOverride()`
- `isRapActive(stateObj)`
- `isWeppYearlyActive(stateObj)`
- `GRAPH_CONTEXT_DEFS`
- `positionYearSlider(position)`
- `resolveGraphContext(stateObj)`
- `setGraphFocus(enabled, options)`
- `ensureGraphExpanded()`
- `setGraphCollapsed(collapsed, options)`
- `toggleGraphPanel()`
- `currentGraphSource()`
- `updateGraphModeButtons(mode)`
- `setGraphControlsEnabled(enabled)`
- `applyGraphMode(mode, options)`
- `setGraphMode(mode, options)`
- `syncGraphLayout(options)` / `syncGraphModeForContext(options)`

**New module contract:**
```javascript
// gl-dashboard/ui/graph-mode.js
export function createGraphModeController({
  getState,
  setValue,
  domRefs,  // glMainEl, graphPanelEl, graphModeButtons
  yearSlider,
  timeseriesGraph,
  onModeChange,  // callback: apply layers when graph mode affects rendering
}) {
  return {
    clearGraphModeOverride,
    setGraphFocus,
    setGraphCollapsed,
    toggleGraphPanel,
    setGraphMode,
    syncGraphLayout,
    resolveGraphContext,
    updateGraphModeButtons,
  };
}
```

**Regression tests:**
- `gl-dashboard-graph-modes.spec.js` - all mode transitions
- `gl-dashboard-state-transitions.spec.js` - RAP→Landuse collapses

**Critical invariant:** `syncGraphLayout()` must remain idempotent (context-key guard)

---

### Phase 3: Year Slider Controller
**Risk:** Low | **Lines:** ~200 | **Duration:** 1-2 hours

**Extract to:** `gl-dashboard/ui/year-slider.js`

**Move:** The entire `yearSlider` object literal

**New module contract:**
```javascript
// gl-dashboard/ui/year-slider.js
export function createYearSlider({
  el,  // #gl-year-slider
  input,  // #gl-year-slider-input
  valueEl,  // #gl-year-slider-value
  minEl,  // #gl-year-slider-min
  maxEl,  // #gl-year-slider-max
  playBtn,  // #gl-year-slider-play
}) {
  return {
    init(config),
    show(context),  // 'climate' | 'layer'
    hide(),
    setRange(min, max, current),
    getValue(),
    setValue(year),
    on(event, callback),
    off(event, callback),
    play(),
    pause(),
    toggle(),
  };
}
```

**Regression tests:**
- `gl-dashboard-graph-modes.spec.js` - slider visibility per context
- Year slider playback test

---

### Phase 4: Color Scale Consolidation
**Risk:** Low | **Lines:** ~300 | **Duration:** 1-2 hours

**Expand:** `gl-dashboard/colors.js`

**Functions to move from main file:**
- `hslToHex(h, s, l)`
- `soilColorForValue(value)`
- `hexToRgbaArray(hex, alpha)`
- `rgbaStringToArray(str, alphaOverride)`
- `normalizeColorEntry(entry, alpha)`
- `viridisColor(val)`
- `winterColor(val)`
- `jet2Color(val)`
- `divergingColor(normalizedDiff)`
- `rdbuColor(normalized)`

**Already in colors.js:** `normalizeModeValue()`, `resolveColormapName()`

**New exports:**
```javascript
// gl-dashboard/colors.js (expanded)
export {
  normalizeModeValue,
  resolveColormapName,
  hslToHex,
  soilColorForValue,
  hexToRgbaArray,
  rgbaStringToArray,
  normalizeColorEntry,
  createColorScales,  // factory that returns viridisColor, winterColor, etc.
};
```

**Regression tests:**
- Manual: verify all layer coloring matches pre-refactor
- Landuse dominant colors
- WEPP runoff (winter) vs soil loss (jet2)
- Comparison mode diverging colors

---

### Phase 5: WEPP Data Handlers
**Risk:** Medium | **Lines:** ~600 | **Duration:** 3-4 hours

**Extract to:** `gl-dashboard/data/wepp-data.js`

**Functions to move (all WEPP data, including Event base/diff logic moved from Phase 1):**
- `buildWeppAggregations(statistic)`
- `fetchWeppSummary(statistic, options)`
- `refreshWeppStatisticData()`
- `computeWeppRanges()`
- `computeWeppYearlyRanges()`
- `computeWeppYearlyDiffRanges(year)`
- `loadBaseWeppYearlyData(year)`
- `refreshWeppYearlyData()`
- `computeWeppEventRanges()`
- `computeWeppEventDiffRanges()` *(moved from Phase 1)*
- `loadBaseWeppEventData()` *(moved from Phase 1)*
- `refreshWeppEventData()`

**New module contract:**
```javascript
// gl-dashboard/data/wepp-data.js
export function createWeppDataManager({
  ctx,
  getState,
  setValue,
  setState,
  postQueryEngine,
  postBaseQueryEngine,
  pickActiveWeppEventLayer,  // injected: needed for event queries
  WEPP_YEARLY_PATH,
  WEPP_LOSS_PATH,
}) {
  return {
    fetchWeppSummary,
    refreshWeppStatisticData,
    computeWeppRanges,
    computeWeppYearlyRanges,
    refreshWeppYearlyData,
    loadBaseWeppYearlyData,
    // WEPP Event functions
    computeWeppEventRanges,     // added to keep range normalization callable
    computeWeppEventDiffRanges,
    loadBaseWeppEventData,
    refreshWeppEventData,
  };
}
```

**Regression tests:**
- WEPP statistic dropdown changes (mean, p90, cv)
- WEPP Yearly slider changes
- WEPP Event date picker changes

---

### Phase 6: Initialization Cleanup
**Risk:** Low | **Lines:** ~300 | **Duration:** 1-2 hours

**Objective:** Reduce orchestrator to pure wiring

After phases 1-5, `gl-dashboard.js` should contain only:
- Dynamic module imports
- Module instantiation with dependency injection
- DOM element lookups
- Event listener wiring
- `initializeDashboard()` call
- Global hook exposure (`window.glDashboard*`)

**Target size:** ~500-800 lines (down from 4,513)

---

## Risk Mitigation

### Testing Strategy

| Phase | Primary Test | Secondary Tests |
|-------|-------------|-----------------|
| 1 | Scenario changes layers | Comparison toggle |
| 2 | Graph mode buttons | RAP→Landuse collapse |
| 3 | Slider visibility | Playback advances year |
| 4 | Manual color inspection | Compare screenshots |
| 5 | WEPP statistic refresh | Yearly data loading |
| 6 | Full init sequence | All prior tests |

### Rollback Points

Each phase creates a git commit with working state:
- `git tag gl-dashboard-phase1-complete`
- `git tag gl-dashboard-phase2-complete`
- etc.

### Critical Paths to Protect

1. **Graph mode idempotence:** `syncGraphLayout()` must short-circuit on unchanged context-key
2. **State reactivity:** All `setValue()` calls must trigger subscribers
3. **Layer ordering:** `buildLayerStack()` must maintain correct z-order
4. **Year slider context:** 'climate' → bottom, 'layer' → top

---

## New Module Structure (Post-Refactor)

```
gl-dashboard/
├── config.js                 # Static constants (unchanged)
├── state.js                  # Reactive state (unchanged)
├── colors.js                 # EXPANDED: all colormap functions
├── data/
│   ├── query-engine.js       # Query Engine HTTP (unchanged)
│   └── wepp-data.js          # NEW: WEPP data fetching/computation
├── graphs/
│   ├── timeseries-graph.js   # Canvas rendering (unchanged)
│   └── graph-loaders.js      # Data loaders (unchanged)
├── layers/
│   ├── detector.js           # Overlay detection (unchanged)
│   └── renderer.js           # Sidebar DOM (unchanged)
├── map/
│   ├── layers.js             # Deck builders (unchanged)
│   └── controller.js         # Deck.gl wrapper (unchanged)
├── scenario/
│   └── manager.js            # NEW: scenario/comparison logic
├── ui/
│   ├── graph-mode.js         # NEW: mode state machine
│   └── year-slider.js        # NEW: slider controller
├── AGENTS.md                 # Updated with new modules
├── README.md                 # Updated module contracts
└── REFACTOR_PLAN.md          # This document
```

---

## Schedule Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| 0 (Baseline) | 30 min | None |
| 1 (Scenario) | 2-3 hrs | Phase 0 |
| 2 (Graph Mode) | 2-3 hrs | Phase 1 |
| 3 (Year Slider) | 1-2 hrs | Phase 2 |
| 4 (Colors) | 1-2 hrs | Phase 3 |
| 5 (WEPP Data) | 3-4 hrs | Phase 4 |
| 6 (Cleanup) | 1-2 hrs | Phase 5 |
| **Total** | **11-17 hrs** | |

---

## Verification Checklist (Per Phase)

- [ ] `node --check wepppy/weppcloud/static/js/gl-dashboard.js` passes (from repo root)
- [ ] `npm run lint` passes (from `wepppy/weppcloud/static-src/`)
- [ ] Playwright `gl-dashboard-state-transitions.spec.js` passes (both URLs)
- [ ] Playwright `gl-dashboard-graph-modes.spec.js` passes (both URLs)
- [ ] Manual: load dashboard, toggle 3+ layer types
- [ ] Manual: no console errors
- [ ] Git commit with descriptive message
- [ ] Git tag for rollback point

---

## Notes for Implementers

1. **Import order matters:** Dynamic imports in main file use `${moduleBase}` path resolution. New modules should follow the same pattern or use relative imports internally.

2. **State access:** Prefer passing `getState` callback over importing `state.js` directly to maintain testability.

3. **Callback injection:** Functions that trigger side effects (applyLayers, updateLegendsPanel) should be passed as callbacks, not imported.

4. **DOM guard pattern:** All DOM operations should guard against missing elements:
   ```javascript
   if (!el) return;
   ```

5. **Async consistency:** Keep `async/await` usage consistent - don't mix `.then()` chains.

---

## References

- [gl-dashboard README.md](./README.md) - Module contracts
- [gl-dashboard AGENTS.md](./AGENTS.md) - Developer quick-reference
- [state-transition.spec.md](./state-transition.spec.md) - State machine spec
- [ui-docs/gl-dashboard.md](../../../docs/ui-docs/gl-dashboard.md) - User-facing feature spec
