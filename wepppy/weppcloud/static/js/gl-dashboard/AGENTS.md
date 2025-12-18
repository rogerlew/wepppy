# GL Dashboard – Agent Notes

Developer quick-reference for the GL Dashboard modules. Full contracts and conventions live in `README.md` here, and the user-facing spec is at `wepppy/docs/ui-docs/gl-dashboard.md`.

## Status

Refactor complete; main file is thin wiring. See [`REFACTOR_PLAN.md`](./REFACTOR_PLAN.md) for history, and `README.md` here for current module contracts.

### Test URLs for Regression Validation
- **Primary:** `https://wc.bearhive.duckdns.org/weppcloud/runs/minus-farce/disturbed9002_wbt/gl-dashboard`
- **Secondary:** `https://wc.bearhive.duckdns.org/weppcloud/runs/walk-in-obsessive-compulsive/disturbed9002_wbt/gl-dashboard`

### Quick Test Commands
```bash
cd wepppy/weppcloud/static-src
GL_DASHBOARD_URL="https://wc.bearhive.duckdns.org/weppcloud/runs/minus-farce/disturbed9002_wbt/gl-dashboard" \
  npm run smoke -- tests/smoke/gl-dashboard-*.spec.js
GL_DASHBOARD_URL="https://wc.bearhive.duckdns.org/weppcloud/runs/walk-in-obsessive-compulsive/disturbed9002_wbt/gl-dashboard" \
  npm run smoke -- tests/smoke/gl-dashboard-*.spec.js
```

## Core Conventions

- Read `README.md` for module boundaries (DOM vs. deck vs. data) and critical conventions.
- Apply `ctx.sitePrefix` to all fetches (browse, gdalinfo, query-engine).
- Keep graph layout idempotent: `syncGraphLayout()` must short-circuit on unchanged context key.
- Year slider placement: climate/outlet → bottom; RAP/WEPP Yearly → top; cumulative/omni → hidden; hide when no timeline.
- Guard DOM refs (slider, graph panel, buttons) so partial renders/tests don’t throw.
- Graph controls enabled only when RAP cumulative, a RAP/WEPP Yearly overlay is active, or a graph radio is selected.

## Page Load Pipeline

1. **Bootstrap** – `initGlDashboard()` fetches run metadata, builds `ctx`, and calls `initMap()`.
2. **Layer detection** – `detectRasterLayers()` + `detectLanduseOverlays()` probe browse/gdalinfo endpoints to populate available layers.
3. **State hydration** – URL hash parsed; default state merged; `setValue()` seeds reactive store.
4. **Map render** – Deck.gl viewport created; base raster + vector overlays applied via `applyLayers()`.
5. **UI wiring** – Sidebar controls, year slider, graph panel bound to state subscribers.
6. **Ready** – First paint complete; user interactions trigger `setValue()` → subscriber cascade.

## Troubleshooting

- **Rasters/layers missing:** Confirm `BASE_LAYER_DEFS` paths resolve via `ctx.sitePrefix`; check `detectRasterLayers`/`detectLanduseOverlays` await paths.
- **Graph pane loops/stays open:** Verify `syncGraphLayout()` context guard and RAP/WEPP visibility checks.
- **Slider missing:** Confirm `rapMetadata`/`weppYearlyMetadata` are loaded; ensure slider placement rules run.
- **Legends/tooltips wrong:** Consume legend payloads from `map/layers` instead of recomputing.
- **Comparison colors wrong:** Ensure `weppDataManager` is injected into scenario manager; diff ranges set before apply.

## Quick Checks

```bash
# Syntax validation
node --check wepppy/weppcloud/static/js/gl-dashboard.js

# Playwright smoke tests
cd wepppy/weppcloud/static-src
npm run smoke -- tests/smoke/gl-dashboard-state-transitions.spec.js
npm run smoke -- tests/smoke/gl-dashboard-graph-modes.spec.js
npm run smoke -- tests/smoke/gl-dashboard-layers.spec.js
```

## Refactoring Guidelines

When extracting code to new modules:

1. **Prefer callback injection over direct imports** - Pass `applyLayers`, `setValue`, etc. as callbacks to maintain testability.
2. **Guard all DOM operations** - `if (!el) return;`
3. **Maintain state reactivity** - All state changes through `setValue()` to trigger subscribers.
4. **Test after each extraction** - Run Playwright suite before committing.
5. **Tag rollback points** - `git tag gl-dashboard-phaseN-complete`
