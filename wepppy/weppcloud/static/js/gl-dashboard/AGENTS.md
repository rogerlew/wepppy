# GL Dashboard – Agent Notes

Developer quick-reference for the GL Dashboard modules. Full contracts and conventions live in `README.md` here, and the user-facing spec is at `wepppy/docs/ui-docs/gl-dashboard.md`.

## Active Refactoring Initiative

**See [`REFACTOR_PLAN.md`](./REFACTOR_PLAN.md)** for the multi-phase plan to split `gl-dashboard.js` (4,513 lines) into cohesive submodules.

### Test URLs for Regression Validation
- **Primary:** `https://wc.bearhive.duckdns.org/weppcloud/runs/minus-farce/disturbed9002_wbt/gl-dashboard`
- **Secondary:** `https://wc.bearhive.duckdns.org/weppcloud/runs/walk-in-obsessive-compulsive/disturbed9002_wbt/gl-dashboard`

### Quick Test Commands
```bash
cd wepppy/weppcloud/static-src
GL_DASHBOARD_URL="https://wc.bearhive.duckdns.org/weppcloud/runs/minus-farce/disturbed9002_wbt/gl-dashboard" \
  npm run smoke -- tests/smoke/gl-dashboard-*.spec.js
```

## Core Conventions

- Read `README.md` for module boundaries (DOM vs. deck vs. data) and critical conventions.
- Keep `syncGraphModeForContext()` idempotent (context-key guard) to avoid recursion/memory spikes.
- Hoist init-time variables with `var` if referenced before declaration to avoid TDZ during startup.
- Guard DOM refs in helpers like `setGraphCollapsed` so tests or partial renders don't throw.
- Year slider: initialize with climate context, bind listeners, then call `syncGraphModeForContext()`.
- Graph controls should only stay enabled when RAP cumulative is on, a RAP overlay is visible, WEPP Yearly is active, or a graph radio is selected.

## Troubleshooting

- **Graph pane loops/stays open:** Check the context guard in `syncGraphLayout()` and RAP/WEPP visibility checks.
- **Slider missing:** Confirm metadata loaded via `rapMetadata` or `weppYearlyMetadata`.
- **Legends/tooltips wrong:** Consume legend payloads from `map/layers` instead of recomputing.

## Quick Checks

```bash
# Syntax validation
node --check wepppy/weppcloud/static/js/gl-dashboard.js

# Playwright smoke tests
cd wepppy/weppcloud/static-src
npm run smoke -- tests/smoke/gl-dashboard-state-transitions.spec.js
npm run smoke -- tests/smoke/gl-dashboard-graph-modes.spec.js
```

## Refactoring Guidelines

When extracting code to new modules:

1. **Prefer callback injection over direct imports** - Pass `applyLayers`, `setValue`, etc. as callbacks to maintain testability.
2. **Guard all DOM operations** - `if (!el) return;`
3. **Maintain state reactivity** - All state changes through `setValue()` to trigger subscribers.
4. **Test after each extraction** - Run Playwright suite before committing.
5. **Tag rollback points** - `git tag gl-dashboard-phaseN-complete`
