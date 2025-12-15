# gl-dashboard Module Contracts

> Boundaries for the modularized gl-dashboard bundle. Keep modules focused and avoid cross-cutting side effects.

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
