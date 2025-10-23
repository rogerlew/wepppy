# Tracker – Frontend Integration & Smoke Automation

## Timeline
- **2025-02-24** – Work package created; scope defined for Pure migrations, bootstrap overhaul, and smoke commands.

## Task Board
### Ready / Backlog
- [ ] Finalize Pure templates for map + channel/subcatchment bundle.
- [ ] Convert treatments control to Pure & StatusStream helpers.
- [ ] Author smoke test script/command covering map, landuse build, WEPP run, StatusStream checks.
- [ ] Document smoke workflow in `control-ui-styling/AGENTS.md` and package tracker.
- [ ] Evaluate automation tooling (Playwright/Cypress) and capture plan.

### In Progress
- None yet.

### Blocked
- None.

### Done
- Work package scaffold established.
- [x] Drafted new `run_page_bootstrap.js.j2` API and `WCControllerBootstrap` helper.
- [x] Refactored controllers to use `instance.bootstrap(context)` plus job-id fallbacks; run-page script now builds a single context and calls `bootstrapMany`.

## Decisions Log
- *2025-02-24* – Use controller-defined bootstrap hooks and StatusStream emitters as the foundation for the new run-page bootstrap.
- *2025-02-24* – Smoke testing will begin as scripted manual commands; automation framework evaluation follows once the scripts are stable.
- *2025-10-23* – Centralise run context construction in `run_page_bootstrap.js.j2`; controllers own job wiring/report hydration via their `bootstrap` implementation. `WCControllerBootstrap` mediates context access and testing defaults.

## Risks / Watch List
- Map/delineation conversion may expose missing Pure CSS tokens; be prepared to extend `ui-foundation.css`.
- Bootstrap refactor must maintain compatibility with legacy page until Pure template fully replaces it.
- Smoke script execution time needs to stay short (<5 minutes) so it’s practical for agents.

## Verification Checklist
- [ ] Pure templates render without bootstrap dependencies (map/treatments).
- [x] Controllers initialize via new bootstrap without console errors.
- [ ] Smoke script runs and reports pass/fail results.
- [x] Documentation reflects new workflow.

## Notes – 2025-10-23
- `run_page_bootstrap.js.j2` now builds a `runContext` once, stores it via `WCControllerBootstrap.setContext`, and bootstraps controllers through `bootstrapMany`. Legacy DOM pokes were removed in favor of controller-owned initialization.
- Controllers fall back to `context.jobIds`/`context.data` when helpers are absent so Jest can exercise `bootstrap` without extra stubs.
- Lint (`wctl run-npm lint`) and Jest (`wctl run-npm test`) pass after the refactor; new tests cover bootstrap behaviour for map, channel, landuse, soil, climate, observed, wepp, outlet, disturbed, and baer controllers.
