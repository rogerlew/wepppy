# Tracker – Frontend Integration & Smoke Automation

## Timeline
- **2025-02-24** – Work package created; scope defined for Pure migrations, bootstrap overhaul, and smoke commands.

## Task Board
### Ready / Backlog
- [ ] Evaluate automation tooling (Playwright/Cypress) for broader E2E coverage beyond the initial Playwright smoke seed.

### In Progress
- [ ] Sort out miscellaneous rendering bugs across controllers
- [ ] Validate reports (WEPP reports, loss summaries, visualizations)

### Blocked
- None.

- Work package scaffold established.
- [x] Drafted new `run_page_bootstrap.js.j2` API and `WCControllerBootstrap` helper.
- [x] Refactored controllers to use `instance.bootstrap(context)` plus job-id fallbacks; run-page script now builds a single context and calls `bootstrapMany`.
- [x] Verified map/channel/subcatchment Pure controls + docs (no bootstrap dependencies, StatusStream intact).
- [x] Confirmed treatments control runs on Pure scaffold with StatusStream helpers; documentation updated.
- [x] Seed Playwright smoke run documented (full automation moved to 20251023_smoke_tests).
- [x] Updated front-end guidance docs (control-ui-styling, AGENTS, tests README) to reflect new bootstrap flow and smoke hand-off.
- [x] Controller documentation polished to reflect bootstrap changes.

## Decisions Log
- *2025-02-24* – Use controller-defined bootstrap hooks and StatusStream emitters as the foundation for the new run-page bootstrap.
- *2025-02-24* – Smoke testing will begin as scripted manual commands; automation framework evaluation follows once the scripts are stable.
- *2025-10-23* – Centralise run context construction in `run_page_bootstrap.js.j2`; controllers own job wiring/report hydration via their `bootstrap` implementation. `WCControllerBootstrap` mediates context access and testing defaults.

## Risks / Watch List
- Map/delineation conversion may expose missing Pure CSS tokens; be prepared to extend `ui-foundation.css`.
- Bootstrap refactor must maintain compatibility with legacy page until Pure template fully replaces it.
- Smoke script execution time needs to stay short (<5 minutes) so it’s practical for agents.

## Verification Checklist
- [x] Pure templates render without bootstrap dependencies (map/treatments).
- [x] Controllers initialize via new bootstrap without console errors.
- [ ] Smoke script runs and reports pass/fail results (extend scenarios & integrate into CI).
- [x] Documentation reflects new workflow.

## Notes – 2025-10-23
- `run_page_bootstrap.js.j2` now builds a `runContext` once, stores it via `WCControllerBootstrap.setContext`, and bootstraps controllers through `bootstrapMany`. Legacy DOM pokes were removed in favor of controller-owned initialization.
- Controllers fall back to `context.jobIds`/`context.data` when helpers are absent so Jest can exercise `bootstrap` without extra stubs.
- Manual walkthrough confirmed map, channel delineation, subcatchments, and treatments render correctly with StatusStream; `control-inventory.md` adjusted to reflect Pure-only status.
- Lint (`wctl run-npm lint`), Jest (`wctl run-npm test`), and Playwright smoke seed (`npm run smoke` with `TEST_SUPPORT_ENABLED=true`, `SMOKE_RUN_ROOT` override) all pass after the refactor.
- Docker dev compose now sets `TEST_SUPPORT_ENABLED=${TEST_SUPPORT_ENABLED:-false}` so test endpoints can be toggled from `.env`.
- Drafted smoke harness spec (`prompts/active/smoke_harness_spec.md`) and quick profile (`tests/smoke/profiles/quick.yml`); next step is wiring profiles into `wctl`.
