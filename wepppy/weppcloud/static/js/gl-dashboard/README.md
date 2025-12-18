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
