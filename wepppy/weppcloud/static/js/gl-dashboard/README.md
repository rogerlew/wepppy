# gl-dashboard Module Contracts

> Boundaries for the modularized gl-dashboard bundle. See also `wepppy/docs/ui-docs/gl-dashboard.md` for the user-facing spec.

## Module Responsibilities (post-refactor)
- **config.js** — Constants (colormaps, layer defs, graph defs); pure exports.
- **colors.js** — Colormap + normalization helpers; pure; no DOM/deck.
- **state.js** — Central mutable state + subscriptions; no DOM/deck.
- **scenario/manager.js** — Scenario + comparison switching, base data loads, diff ranges; injected callbacks for apply/legend updates.
- **data/query-engine.js** — Query Engine HTTP helpers (sitePrefix-aware).
- **data/wepp-data.js** — WEPP stat/yearly/event fetchers, ranges, base/comparison loads; uses injected Query Engine and picker helpers.
- **ui/graph-mode.js** — Graph mode/layout controller; year-slider placement; idempotent sync; DOM guarded.
- **ui/year-slider.js** — Slider controller (init/show/hide/playback); DOM guarded.
- **graphs/timeseries-graph.js** — Canvas graph controller; DOM-bound to panel/canvas.
- **graphs/graph-loaders.js** — Graph data loaders (Omni/RAP/WEPP); no DOM/deck.
- **layers/detector.js** — Overlay detection (raster/vector) with fetch; no DOM/deck.
- **layers/orchestrator.js** — Detection sequencing + state wiring; no DOM.
- **layers/renderer.js** — Sidebar + legends DOM; uses injected callbacks/state.
- **map/layers.js** — Deck layer builders + tooltip/legend helpers; pure.
- **map/controller.js** — deck.gl wrapper for view state + layer stack.
- **map/raster-utils.js** — GeoTIFF/SBS loaders, gdalinfo fetch; sitePrefix-aware.
- **gl-dashboard.js** — Orchestrator wiring: imports, DI, DOM lookups, event binding, initializeDashboard, global hooks.

## Critical Conventions
- All fetches honor `ctx.sitePrefix` (browse/gdalinfo/query-engine) to avoid missing-run errors.
- `syncGraphLayout()` must be idempotent (context-key guard) to prevent applyLayers/graph mode loops.
- Year slider placement: climate/outlet graphs → bottom; RAP/WEPP Yearly → top; cumulative/omni → hidden; hide when no timeline context.
- Guard DOM operations (sliders, graph panel, buttons) so partial renders/tests do not throw.
- Use injected callbacks/state (`getState`, `setValue`, `applyLayers`, etc.); avoid new globals.
- Query Engine endpoints are root-scoped (`/query-engine/...`); do **not** prepend `ctx.sitePrefix` when calling them.

## Module Contracts (injection signatures)
- `createScenarioManager({ ctx, getState, setValue, setState, postQueryEngine, postBaseQueryEngine, fetchWeppSummary, weppDataManager, onScenarioChange, onComparisonChange })`
- `createGraphModeController({ getState, setValue, domRefs, yearSlider, timeseriesGraph, onModeChange })`
- `createYearSlider({ el, input, valueEl, minEl, maxEl, playBtn })`
- `createWeppDataManager({ ctx, getState, setValue, setState, postQueryEngine, postBaseQueryEngine, pickActiveWeppEventLayer, WEPP_YEARLY_PATH, WEPP_LOSS_PATH })`
- `colors.js` exports: `normalizeModeValue`, `resolveColormapName`, `hslToHex`, `soilColorForValue`, `hexToRgbaArray`, `rgbaStringToArray`, `normalizeColorEntry`, `createColorScales`, `viridisColor`, `winterColor`, `jet2Color`, `divergingColor`, `rdbuColor`

## Common Pitfalls
- Forgetting `await` on detector/data calls leaves overlays empty with no error.
- Bypassing state setters (direct mutation) skips subscribers and legends/apply updates.
- Recomputing legends/tooltips in the renderer: consume payloads from `map/layers` instead.
- Comparison mode relies on base data + diff ranges; ensure `weppDataManager` is injected into scenario manager.

## Adding New Layers or Graphs
- **Map layers (raster/vector):**
  - Add paths/labels to `config.BASE_LAYER_DEFS` (rasters) or implement a detector that fetches summaries/geojson and returns layer descriptors with `visible` flags.
  - Keep detection pure (no DOM); wire it through `layers/orchestrator.js` and update state via `setState`.
  - Extend `map/layers.js` with a builder for the new layer type and legends/tooltip helpers; update renderer legend handling only if format changes.
  - Ensure URLs use `buildBaseUrl`/`buildScenarioUrl` and include `ctx.sitePrefix`.
  - Update smoke tests to assert the layer appears in the sidebar and toggles affect legends/deck layer stack.
- **Graph layers (graphs list):**
  - Add entries to `config.GRAPH_DEFS` with keys/labels.
  - Provide a loader in `graphs/graph-loaders.js` (use Query Engine helpers; avoid DOM).
  - Register graph activation in the orchestrator and ensure `graph-mode` handles context/layout; update legends if new sources impact diverging/slider placement.
  - Add Playwright coverage for the new graph selection and expected layout (mode + slider).

## Troubleshooting + Testing
- Syntax check: `node --check wepppy/weppcloud/static/js/gl-dashboard.js`.
- Playwright smoke (run from `wepppy/weppcloud/static-src`):
  - `GL_DASHBOARD_URL="https://wc.bearhive.duckdns.org/weppcloud/runs/minus-farce/disturbed9002_wbt/gl-dashboard" npm run smoke -- tests/smoke/gl-dashboard-*.spec.js`
  - `GL_DASHBOARD_URL="https://wc.bearhive.duckdns.org/weppcloud/runs/walk-in-obsessive-compulsive/disturbed9002_wbt/gl-dashboard" npm run smoke -- tests/smoke/gl-dashboard-*.spec.js`
- Targeted checks: graph-modes (layout/slider), layers (subcatchment labels toggle, rasters detected), diverging legend in comparison runs.
## Querying Omni Scenario Data

**CRITICAL**: Scenario data is queried via the `scenario` body parameter, NOT URL path manipulation.

### Architecture

The query flow for scenarios:

1. **Frontend**: `scenarioPath(scenario)` builds a path like `_pups/omni/scenarios/mulch_30`
2. **HTTP Helper**: `postQueryEngineForScenario(path, payload)` extracts the scenario name from the path and adds `{ scenario: "mulch_30" }` to the request body
3. **Server**: Extracts `scenario` from body and passes to `resolve_run_context()`
4. **Query Engine**: Resolves `{run_root}/_pups/omni/scenarios/mulch_30/` and overlays scenario parquet files

### Correct Usage

```javascript
// In graph-loaders.js - use scenarioPath() + postQueryEngineForScenario()
const path = scenarioPath(scenario);  // "_pups/omni/scenarios/mulch_30"
const result = await postQueryEngineForScenario(path, payload);
```

### Common Mistakes (AVOID)

```javascript
// ❌ WRONG: Appending scenario path to URL - server will reject with 400
const url = `${baseUrl}/_pups/omni/scenarios/mulch_30/query`;
await fetch(url, { body: JSON.stringify(payload) });

// ❌ WRONG: Using postQueryEngine with modified URL
await postQueryEngine(payload, `${prefix}/_pups/omni/scenarios/mulch_30`);
```

### Debugging Identical Scenario Data

If boxplots/cumulative graphs show identical values for all scenarios:

1. **Check browser DevTools Network tab**: Verify requests include `"scenario": "name"` in the body
2. **Verify server log**: Confirm `scenario=name` is logged in resolve_run_context calls
3. **Test directly with curl**:
   ```bash
   # Base (no scenario)
   curl -X POST /query-engine/runs/RUNID/CONFIG/query \
     -d '{"datasets": ["wepp/output/interchange/loss_pw0.hill.parquet"]}'

   # Scenario (should return different data)
   curl -X POST /query-engine/runs/RUNID/CONFIG/query \
     -d '{"scenario": "mulch_30_sbs_map", "datasets": ["wepp/output/interchange/loss_pw0.hill.parquet"]}'
   ```
4. **Verify scenario directory exists**: `ls -la {run_path}/_pups/omni/scenarios/mulch_30_sbs_map/`

### Related Files

- `data/query-engine.js` - HTTP helpers including `postQueryEngineForScenario()`
- `graphs/graph-loaders.js` - `scenarioPath()` and scenario data loading
- `wepppy/query_engine/README.md` - Server-side scenario query documentation
- `wepppy/query_engine/app/server.py` - Server endpoint implementation
