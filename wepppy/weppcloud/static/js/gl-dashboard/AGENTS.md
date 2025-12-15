# GL Dashboard – Agent Notes
Developer quick-reference for the GL Dashboard modules. Full contracts and conventions live in `README.md` here, and the user-facing spec is at `wepppy/docs/ui-docs/gl-dashboard.md`.

- Read `README.md` for module boundaries (DOM vs. deck vs. data) and critical conventions.
- Keep `syncGraphModeForContext()` idempotent (context-key guard) to avoid recursion/memory spikes.
- Hoist init-time variables with `var` if referenced before declaration to avoid TDZ during startup.
- Guard DOM refs in helpers like `setGraphCollapsed` so tests or partial renders don’t throw.
- Year slider: initialize with climate context, bind listeners, then call `syncGraphModeForContext()`.
- Graph controls should only stay enabled when RAP cumulative is on, a RAP overlay is visible, WEPP Yearly is active, or a graph radio is selected.
- Troubleshooting: if the graph pane loops or stays open, check the context guard and RAP/WEPP visibility checks; if slider is missing, confirm metadata loaded; if legends/tooltips are wrong, consume legend payloads from `map/layers` instead of recomputing.
- Quick checks: Playwright smoke (RAP/WEPP Yearly split; landuse/soils minimize), `node --check wepppy/weppcloud/static/js/gl-dashboard.js`.
