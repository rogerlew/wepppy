# gl-dashboard Module Contracts

> Boundaries for the modularized gl-dashboard bundle. See also the user-facing spec at `wepppy/docs/ui-docs/gl-dashboard.md` for full feature/UX details.

## Module Responsibilities
- **config.js** — Static constants (colormaps, registries, defaults); no DOM access; pure exports.
- **colors.js** — Normalization and colormap resolution helpers; pure functions; no DOM/deck usage.
- **state.js** — Central mutable state with subscription helpers; no DOM/deck.
- **data/query-engine.js** — Query Engine HTTP wrappers; no DOM/deck; depends on `ctx` and `window.location`.
- **graphs/timeseries-graph.js** — Canvas graph controller; DOM-bound only to the graph panel/canvas; no Query Engine calls.
- **graphs/graph-loaders.js** — Graph data loaders (Omni/RAP/WEPP); no DOM/deck; consume Query Engine helpers and return datasets.
- **layers/detector.js** — Pure detection of available overlays (fetches summaries/metadata); no DOM/deck; returns descriptor objects.
- **layers/renderer.js** — Sidebar + legend DOM rendering; mutates state only via injected callbacks; no deck.gl usage.
- **map/layers.js** — Deck layer builders, tooltip/legend helpers; pure functions; no DOM access.
- **map/controller.js** — deck.gl wrapper that owns the Deck instance and view state; consumes layer stacks; no business logic.
- **gl-dashboard.js** — Orchestration/wiring, global hooks, event binding; keep business logic inside the modules above.

## Contribution Notes
- Keep module surfaces small and document inputs/outputs with short JSDoc headers.
- Prefer passing callbacks/data into renderer/controller instead of importing state directly.
- Avoid introducing DOM/deck dependencies into config, state, colors, data, graphs, or detector modules.
- When adding exports, update this README and keep the public API stable.

## Critical Conventions
- `syncGraphModeForContext()` must be idempotent: short-circuit on an unchanged context key to avoid recursive loops between `applyLayers()`, `setGraphMode()`, and layer toggles.
- Hoist any init-time variable (`lastGraphContextKey`, etc.) with `var` when it is referenced before declaration to avoid TDZ ReferenceErrors during startup.
- Guard DOM operations (for example, `setGraphCollapsed`) if elements are missing so tests or partial renders do not throw.
- Year slider order: initialize with climate context → bind listeners → run `syncGraphModeForContext()` → allow layer toggles to drive visibility.

## Common Pitfalls
- Mixing state vs. cache: scenario changes should clear cached summaries/graphs but preserve user selections (basemap, graph mode, slider position).
- Forgetting `await` on detector calls leaves overlays empty with no errors; keep detector calls awaited before rendering.
- Letting RAP selection (non-visible bands) keep the graph pane open—graph controls should only be enabled when RAP cumulative is on or a RAP overlay is visible.
- Recomputing legends/tooltips in the renderer: consume payloads from `map/layers` instead of recomputing to avoid drift.

## Troubleshooting + Testing
- If the graph pane oscillates or eats memory, check `syncGraphModeForContext()` for idempotence and ensure graph focus isn’t toggling inside `applyLayers()` loops.
- Playwright smoke: load a run, toggle RAP/WEPP Yearly (graph should split), then switch to Landuse/Soils (graph should minimize).
- Quick lint: `node --check wepppy/weppcloud/static/js/gl-dashboard.js`.
