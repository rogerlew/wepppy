# runs0 Pure Layout Migration Plan

## 1. Objectives
- Deliver a Pure.css-based replacement for `routes/run_0/templates/0.htm` that composes the converted controls without Bootstrap dependencies.
- Provide a migration scaffold so we can drop in Pure-ready controls as they land while leaving legacy templates untouched until their turn.
- Keep runs0 functional throughout the transition via feature flags/toggles and exhaustive JS compatibility checks (StatusStream, ControlBase, map integrations, etc.).

## 2. Current Progress Snapshot _(2025-10-19)_
- Pure controls in production: map, fork console, archive console, rangeland/landuse modify panels (embedded inside the map tabset), outlet control.
- Landuse report now renders via Pure components and the shared dataset catalog (`Landuse.available_datasets`).
- Landuse control migrated to Pure macros (`control_shell`, `radio_group`, `select_field`, `collapsible_card`) and now consumes catalog metadata for both landcover and management selections.
- Landcover dataset options (NLCD, CORINE, locale overrides) now live in `wepppy.nodb.locales.landuse_catalog` so both the legacy control and Pure views can consume the same metadata.
- Shared infrastructure: `control_shell` overrides, `status_panel` / `stacktrace_panel`, `tabset`, `color_scale`, `StatusStream`.
- Remaining legacy controls: climate, soils, treatments, WEPP main form, debris flow, Omni, etc. All still rely on `_base.htm`.

## 3. Proposed Page Skeleton (`runs0_pure.htm`)
```
base_pure.htm
└─ runs0_pure.htm
   ├─ Header: reuse Pure run header macros (`header_text_field`, toolbar actions)
   ├─ Layout grid:
   │   ├─ Left column: Table of contents (Pure sticky list)
   │   └─ Right column: stack of control sections
   ├─ Command bar slot (Pure styling, same JS entry point)
   └─ Footer / scripts (load controllers.js, StatusStream, run bootstrap)
```
- Each control section renders as:
  - Converted control → included directly (Pure template).
  - Legacy control → placeholder include w/ note (or legacy template wrapped in compatibility shim) until its migration completes.

## 4. Incremental Migration Workflow
1. **Skeleton (Phase 0)**
   - Create `runs0_pure.htm` with Pure layout + header + command bar.
   - Mount only the controls already converted (map, console-style panels) and stub the rest (`TODO: legacy climate control` comments).
   - Add conditional route toggle (query param or environment flag) so developers can opt into the Pure page without affecting production.
2. **Control Rollout (Phase 1+)**
   - For each control:
     - Convert template to Pure macros.
     - Update companion JS (StatusStream, event bindings).
     - Swap placeholder include → real control in `runs0_pure.htm`.
     - Update `control-inventory.md`.
3. **Full Adoption (Phase Final)**
   - When all controls migrated, replace references to `0.htm` with `runs0_pure.htm`.
   - Remove legacy route toggles and unused CSS/JS shims.

## 5. Feature Flag / Routing Strategy
- Keep `run_0_bp.runs0` serving legacy page by default.
- Introduce toggle (ordered by preference):
  1. Query parameter `?view=pure` for developer testing.
  2. Config flag in `settings.py` (e.g., `RUNS0_USE_PURE`) for staging environments.
- Bootstrap script (`run_page_bootstrap.js.j2`) must detect which template is active and initialise controls accordingly (e.g., skip legacy-only selectors when `runs0_pure` is active).

## 6. Dependencies & Outstanding Work
- Status streaming: convert remaining controls to `StatusStream` before they move into the Pure page.
- Global assets: ensure `controllers.js` bundle ships modal manager, StatusStream, tabset helper.
- Styling: extend `ui-foundation.css` with TOC + layout utilities (`wc-run-layout`, sticky list) referenced in the plan but not yet implemented.
- Documentation: after skeleton lands, update `control_components.md` with any new layout macros and add migration status to `control-inventory.md`.

## 7. Testing Plan
- Manual smoke:
  - Toggle between legacy and Pure pages verifying map, fork, archive, modify panels.
  - Confirm navigation anchors (TOC -> sections) and command bar actions.
- Automated:
  - Existing JS unit tests (StatusStream, tabset) already cover generic behaviour.
  - Add Cypress or Playwright scenario once more controls migrate (loading, job submission, status streaming).
  - Ensure Node-based `status_stream_test.js` continues to run via CI.

## 8. Risks / Mitigations
- **Hybrid state confusion**: Document clearly which controls are Pure vs legacy, avoid mixing columns within a single section. Use placeholders with explicit comments to prevent accidental reliance on legacy markup inside the Pure skeleton.
- **JS regressions**: Wrap initialisation logic so missing selectors on the Pure page do not crash controllers still awaiting migration.
- **Layout drift**: Keep skeleton aligned with `final-implementation-blueprint.md` and update as spacing tokens evolve.

## 9. References
- `docs/ui-docs/control-ui-styling/control-components.md`
- `docs/ui-docs/control-ui-styling/final-implementation-blueprint.md`
- `docs/ui-docs/control-ui-styling/map_control_plan.md`
- `docs/ui-docs/control-ui-styling/status_stacktrace_component_plan.md`
- `docs/ui-docs/control-ui-styling/control-inventory.md`

## 10. Next Actions
1. Implement `runs0_pure.htm` skeleton with toggled route (Phase 0).
2. Track migration status in `runs0_pure_plan.md` (append dated notes per control as they go Pure).
3. Continue converting controls in priority order (climate → soils → WEPP core → Omni, etc.) referencing this plan for integration steps.

## 11. Implementation Notes (2025-10-19)
- Implemented `runs0_pure.htm` skeleton with Pure header, TOC scaffold, converted map control, and embedded channel/subcatchment delineation controls. Legacy sections remain placeholders until their migrations land.
- Added query-parameter/config toggle (`?view=pure` or `RUNS0_USE_PURE`) to switch between `0.htm` and the Pure skeleton without disrupting production requests.
- Updated `run_page_bootstrap.js.j2`, `landuse_modify.js`, and `rangeland_cover_modify.js` so the bootstrap logic gracefully short-circuits when the Pure layout is active.
- Migrated channel and subcatchment delineation controls to Pure macros (`control_shell`, `radio_group`, `button_row`), preserving existing IDs so the legacy controllers keep working while eliminating Bootstrap rows/cols.
- Migrated the outlet control to Pure macros (`set_outlet.htm`), reusing `control_shell`, `status_panel`, and `stacktrace_panel` while keeping ControlBase IDs for `outlet.js`. Legacy markup lives in `set_outlet_legacy.htm` so the classic runs0 page remains unchanged.
- Converted `reports/landuse.htm` to Pure table/collapse patterns with event delegation in `landuse.js`; dataset options now come from the new `wepppy.nodb.locales.landuse_catalog` helper.
