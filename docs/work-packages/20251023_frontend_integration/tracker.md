# Tracker – Frontend Integration & Smoke Automation

## Timeline
- **2025-02-24** – Work package created; scope defined for Pure migrations, bootstrap overhaul, and smoke commands.

## Task Board
### Ready / Backlog
- [ ] Evaluate automation tooling (Playwright/Cypress) for broader E2E coverage beyond the initial Playwright smoke seed.

### In Progress
- None.

### Completed
- [x] **Issue 1**: Legend visual styling - 2-column layout with swatches (map_pure.htm #sub_legend, #sbs_legend) ✅ 2025-10-27
- [x] **Issue 2**: Report table visual styling - standardize .wc-table wrappers and modifiers across all report templates ✅ 2025-10-27
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

1. **Legend Visual Styling** ✅ COMPLETED: Implemented 2-column grid layout for map legends with color swatches.
   - Created new CSS classes: `.wc-legend`, `.wc-legend-item`, `.wc-legend-item__swatch`, `.wc-legend-item__label`
   - Updated templates: `color_legend.htm`, `landuse.htm`, `soil.htm`, `slope_aspect.htm`
   - Swatches use CSS custom property `--legend-color` for inline color assignment
   - Removed Bootstrap grid classes (`col-sm-*`) and inline styles
   - Added header styling (`.wc-map-legend__header`) and image wrapper (`.wc-map-legend__image`)
   - 3rem fixed-width swatch column + flexible description column
   - Maintains accessibility with proper `aria-label` on swatches

2. **Report Table Styling** ✅ COMPLETED: Standardized all report tables with `.wc-table` classes and visual improvements.
   - Added comprehensive table CSS in `ui-foundation.css` (lines 2640-2695)
   - Base styles: full width, border-collapse, consistent padding
   - Header styling: bold weight (700 !important), white background
   - Border placement: 1px solid black under units row (tbody tr[data-sort-position="top"])
   - Table modifiers:
     - `--striped`: alternating row backgrounds for readability
     - `--dense`: reduced padding for compact layouts  
     - `--compact`: auto width with 50% minimum
   - Updated three report templates:
     - `summary.htm`: Watershed Loss Summary (3 tables with striping)
     - `return_periods.htm`: Return Periods Report (simple + extraneous tables with striping/compact)
     - `avg_annuals_by_landuse.htm`: Summary by Landuse (striping)
   - User feedback iterations: white headers, black border under units, bold text
   - Headers use `font-weight: 700 !important` to override any interference

3. **Preflight TOC Indicators** ✅ COMPLETED: Restored emoji completion checkmarks in runs0_pure.htm TOC.

4. **Control Ordering** ✅ COMPLETED: Verified landuse/soils section order.

5. **Map Layer Radio Enablement** ✅ COMPLETED: Wired subcatchment color map radios to preflight state.

6. **Inline Help Icons**: Migrate legacy `<a data-toggle="tooltip">` pattern to Pure macro `inline_help` parameter. (DEFERRED - large scope)

7. **Controller Hint Deduplication** ✅ COMPLETED: Fixed message duplication between status logs and hint elements.

---

## Notes – 2025-10-23
- `run_page_bootstrap.js.j2` now builds a `runContext` once, stores it via `WCControllerBootstrap.setContext`, and bootstraps controllers through `bootstrapMany`. Legacy DOM pokes were removed in favor of controller-owned initialization.
- Controllers fall back to `context.jobIds`/`context.data` when helpers are absent so Jest can exercise `bootstrap` without extra stubs.
- Manual walkthrough confirmed map, channel delineation, subcatchments, and treatments render correctly with StatusStream; `control-inventory.md` adjusted to reflect Pure-only status.
- Lint (`wctl run-npm lint`), Jest (`wctl run-npm test`), and Playwright smoke seed (`npm run smoke` with `TEST_SUPPORT_ENABLED=true`, `SMOKE_RUN_ROOT` override) all pass after the refactor.
- Docker dev compose now sets `TEST_SUPPORT_ENABLED=${TEST_SUPPORT_ENABLED:-false}` so test endpoints can be toggled from `.env`.
- Drafted smoke harness spec (`prompts/active/smoke_harness_spec.md`) and quick profile (`tests/smoke/profiles/quick.yml`); next step is wiring profiles into `wctl`.
