# Tracker – Frontend Integration & Smoke Automation

## Timeline
- **2025-02-24** – Work package created; scope defined for Pure migrations, bootstrap overhaul, and smoke commands.

## Task Board
### Ready / Backlog
- [ ] Evaluate automation tooling (Playwright/Cypress) for broader E2E coverage beyond the initial Playwright smoke seed.

### In Progress
- [ ] **Issue 1**: Legend visual styling - 2-column layout with swatches (map_pure.htm #sub_legend, #sbs_legend)
- [ ] **Issue 2**: Report table visual styling - standardize .wc-table wrappers and modifiers across all report templates

### Completed
- [x] **Issue 3**: Restore preflight TOC indicator - add data-toc-emoji-value attributes to runs0_pure.htm TOC anchors ✅ 2025-10-27
- [x] **Issue 4**: Verify soils control ordering - ensure landuse appears before soils in both TOC and content sections ✅ 2025-10-27
- [x] **Issue 5**: Enable map layer radios based on preflight - wire subcatchment_delineation.js to window.lastPreflightChecklist ✅ 2025-10-27
- [x] **Issue 7**: Controller hint deduplication - show job dashboard link in hints, remove from status cards, eliminate message duplication ✅ 2025-10-27

### Deferred
- [ ] **Issue 6**: Revise help icon fields - migrate inline <a data-toggle="tooltip"> to Pure macro inline_help parameter (marked "save for later" - large scope)

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

## Notes – 2025-10-27
**Detailed Issue Analysis Completed - 7 Issues Identified**

Seven outstanding issues identified and documented in `package.md` with comprehensive technical specifications:

1. **Legend Visual Styling**: Need 2-column grid layout for map legends using swatch pattern from BAER classify control. Affects `#sub_legend` and `#sbs_legend` in map_pure.htm.

2. **Report Table Styling**: Standardize all report tables to use `.wc-table-wrapper` + `.wc-table` classes with appropriate modifiers (--dense, --compact, --striped). Survey shows multiple report templates missing consistent styling.

3. **Preflight TOC Indicators**: Restore emoji completion checkmarks in runs0_pure.htm TOC by adding `data-toc-emoji-value` attributes to anchor elements. preflight.js `setTocEmojiState()` function already exists and expects this markup pattern.

4. **Control Ordering**: Verify landuse/soils section order in runs0_pure.htm matches standard workflow (landuse → climate → soils). Current template structure appears correct but TOC needs verification.

5. **Map Layer Radio Enablement**: Wire subcatchment color map radios (Slope/Aspect, Dominant Landcover, Dominant Soil) to preflight state. Implement `updateLayerAvailability()` function in subcatchment_delineation.js that reads `window.lastPreflightChecklist` and calls existing `disableRadio()` helper.

6. **Inline Help Icons**: Migrate legacy `<a data-toggle="tooltip">` pattern to Pure macro `inline_help` parameter. Requires:
   - Enhancing `_pure_macros.html` field macros with `inline_help` argument
   - Creating `.wc-field__help-trigger` button component
   - Lightweight JS tooltip handler (no Bootstrap dependency)
   - Migrating 12+ instances in climate.htm and 4+ in channel_delineation_pure.htm

7. **Controller Hint Deduplication**: Fix message duplication between status logs and hint elements. Currently hints echo status messages with raw RQ job IDs. Solution:
   - Update `control_base.js` `onAppend` callback to stop duplicating summary into hints
   - Update `onTrigger` callback to populate hints with job dashboard link on task completion
   - Remove job dashboard link from `render_job_status()` status card output (line 498)
   - Provides cleaner UX: hints show clickable job link, status shows task progress
   - Affects 11 controllers (soil, channel_delineation, treatments, ash, observed, debris_flow, rhem, dss_export, rap_ts, path_ce, omni)

Each issue includes:
- Exact file locations and line numbers
- Current state vs. required fix
- Technical implementation details with code examples
- Alternative approaches where applicable
- Files to create/modify
- Testing checklists
- Accessibility considerations where applicable

Ready for implementation work to begin on any of the seven issues.

---

## Notes – 2025-10-23
- `run_page_bootstrap.js.j2` now builds a `runContext` once, stores it via `WCControllerBootstrap.setContext`, and bootstraps controllers through `bootstrapMany`. Legacy DOM pokes were removed in favor of controller-owned initialization.
- Controllers fall back to `context.jobIds`/`context.data` when helpers are absent so Jest can exercise `bootstrap` without extra stubs.
- Manual walkthrough confirmed map, channel delineation, subcatchments, and treatments render correctly with StatusStream; `control-inventory.md` adjusted to reflect Pure-only status.
- Lint (`wctl run-npm lint`), Jest (`wctl run-npm test`), and Playwright smoke seed (`npm run smoke` with `TEST_SUPPORT_ENABLED=true`, `SMOKE_RUN_ROOT` override) all pass after the refactor.
- Docker dev compose now sets `TEST_SUPPORT_ENABLED=${TEST_SUPPORT_ENABLED:-false}` so test endpoints can be toggled from `.env`.
- Drafted smoke harness spec (`prompts/active/smoke_harness_spec.md`) and quick profile (`tests/smoke/profiles/quick.yml`); next step is wiring profiles into `wctl`.
