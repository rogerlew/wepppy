# runs0 Pure Layout Migration Plan

## 1. Objectives
- Deliver a Pure.css-based replacement for `routes/run_0/templates/0.htm` that composes the converted controls without Bootstrap dependencies.
- Provide a migration scaffold so we can drop in Pure-ready controls as they land while leaving legacy templates untouched until their turn.
- Keep runs0 functional throughout the transition via feature flags/toggles and exhaustive JS compatibility checks (StatusStream, ControlBase, map integrations, etc.).

## 2. Current Progress Snapshot _(2025-02-24)_
- Pure controls embedded on the production runs0 page: Map (`map_pure.htm`), Channel Delineation (`channel_delineation_pure.htm`), Subcatchments (`subcatchments_pure.htm`), Soil Burn Severity, Climate, WEPP, Landuse, Soil, RAP Time Series, RHEM, Debris Flow, Observed Data, DSS Export, Ash/WATAR, Team, Omni scenarios/contrasts, Power User modal, fork/archive consoles, and rangeland modify panels.
- All controls now ship with the Pure scaffold; remaining polish items (map inspector UX, documentation clean-up, smoke scripts) are tracked under the 20251023 Frontend Integration work package.
- Shared infrastructure in place: `control_shell`, `status_panel` / `stacktrace_panel`, tabset utilities, StatusStream bindings, command bar, and the Pure TOC layout.
- Automation focus: bootstrap refactor + smoke testing pipeline (see work package).

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
   - Completed to date: SBS, Climate, WEPP, Landuse, Soil, RAP TS, RHEM, Debris Flow, Observed, DSS Export, Ash, Team, Omni (scenario/contrast shells), Power User modal.
   - Remaining: map + channel/subcatchment cleanup, treatments.
3. **Full Adoption (Completed)**
   - Legacy `0.htm` retired; runs0 now renders Pure layout by default.
   - Legacy CSS/JS shims removed; any future work happens on top of the Pure foundation.

## 5. Feature Flag / Routing Strategy
- Pure layout is the default (no legacy fallback). Future experiments can still use query parameters, but the production path should treat the Pure template as canonical.
- Bootstrap script (`run_page_bootstrap.js.j2`) can assume Pure markup; temporary safeguards for legacy selectors should be removed once the new bootstrap API lands.

## 6. Dependencies & Outstanding Work
- Status streaming: finalise map/delineation cleanup and migrate the treatments suite to the StatusStream pattern prior to swapping templates.
- Global assets: ensure `controllers.js` bundle ships modal manager, StatusStream, tabset helper (done); map-related utilities will need review during the map conversion.
- Styling: extend `ui-foundation.css` with map-panel, delineation, and Omni-specific layout tokens once those controls migrate.
- Documentation: continue updating `control_components.md`, `ash-control-plan.md`, and other module docs as controls move; keep `control-inventory.md` aligned with actual runtime status.

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
1. Finalise migration of high-impact legacy controls:
   - Map cleanup + channel/subcatchment delineation bundle
   - RHEM control
2. Track migration status in this document (append dated notes per control as they go Pure) and update `control-inventory.md` concurrently.
3. Once remaining controls ship, flip the feature flag so `runs0_pure.htm` becomes the default and retire the legacy placeholders.

## 11. Implementation Notes (2025-10-19)
- Implemented `runs0_pure.htm` skeleton with Pure header, TOC scaffold, converted map control, and embedded channel/subcatchment delineation controls. Legacy sections remain placeholders until their migrations land.
- Added query-parameter/config toggle (`?view=pure` or `RUNS0_USE_PURE`) to switch between `0.htm` and the Pure skeleton without disrupting production requests.
- Updated `run_page_bootstrap.js.j2`, `landuse_modify.js`, and `rangeland_cover_modify.js` so the bootstrap logic gracefully short-circuits when the Pure layout is active.
- Migrated channel and subcatchment delineation controls to Pure macros (`control_shell`, `radio_group`, `button_row`), preserving existing IDs so the legacy controllers keep working while eliminating Bootstrap rows/cols.
- Migrated the outlet control to Pure macros (`set_outlet.htm`), reusing `control_shell`, `status_panel`, and `stacktrace_panel` while keeping ControlBase IDs for `outlet.js`. Legacy markup lives in `set_outlet_legacy.htm` so the classic runs0 page remains unchanged.
- Converted `reports/landuse.htm` to Pure table/collapse patterns with event delegation in `landuse.js`; dataset options now come from the new `wepppy.nodb.locales.landuse_catalog` helper.

## 12. Implementation Notes (2025-10-20)
- Climate control now renders via `controls/climate_pure.htm` with catalog-driven sections, StatusStream logging, and the steady-state architecture documented in `docs/dev-notes/climate-control.md`. Legacy markup stays in `controls/climate.htm` for the classic runs page.
- WEPP control migrated to `controls/wepp_pure.htm` with Pure advanced-option partials, StatusStream support in `wepp.js`, and catalog-driven cover-transform options supplied by `run_0_bp`. The classic `_base.htm` control remains in place for `0.htm`.
- Soil Burn Severity upload panel converted to `controls/disturbed_sbs_pure.htm`, wired into the Pure TOC, and backed by delegated handlers in `baer.js`. The legacy Bootstrap panel stays at `baer_upload.htm` so the classic runs page is unaffected.

## 13. Implementation Notes (2025-10-21)
- PowerUser modal (`controls/poweruser_panel.htm`) now uses the Pure `.wc-modal` scaffold with a responsive four-column resource grid. Resource rows are rendered via a local `resource_block` macro that keeps lock icons and NODB/LOG actions aligned with the foundation button styles.
- Modal sizing targets 90% viewport width/height with a fixed footer height so command buttons stay pinned while the body scrolls. Documentation updates landed in `control-components.md` to capture the new modal guidance.
- Observed data control migrated to `controls/observed_pure.htm`, replacing Bootstrap rows with Pure macros, StatusStream panels, and delegated handlers in `observed.js`. The Pure runs page now renders the control in place of the placeholder while the classic template stays intact for `0.htm`.
- RAP Time Series control moved to `controls/rap_ts_pure.htm` with a compact Pure shell, StatusStream wiring, and delegated button handling in `rap_ts.js`. The Pure runs page now surfaces the acquisition button when the mod is enabled; the legacy `_base.htm` template remains for `0.htm`.
- Debris Flow control converted to `controls/debris_flow_pure.htm`, reusing StatusStream panels and delegated events in `debris_flow.js`. The section now renders on the Pure runs page for PowerUsers when the mod is enabled, while the legacy template continues to serve the classic layout.
- DSS Export control now lives in `controls/dss_export_pure.htm`, replacing Bootstrap rows with radio/checkbox macros and delegated handlers in `dss_export.js`. The Pure runs page includes the control (with TOC entry) while the legacy `_base.htm` version continues to power `0.htm`.
- Ash/WATAR control rebuilt as `controls/ash_pure.htm`; `ash.js` now hydrates Pure markup, caches per-model edits, and performs client-side validation. Legacy template remains available for the classic runs page but no longer carries inline scripts.
- Backend upload endpoints for Ash now use the shared `save_run_file` helper, aligning validation with the Pure control.

## 14. Implementation Notes (2025-10-22)
- Map, landuse, soil, set outlet, and channel/subcatchment controls were renamed to the `_pure.htm` convention and wired directly into `runs0_pure.htm`; the legacy `0.htm` template was removed.
- Treatments control migrated to `controls/treatments_pure.htm`, adopting Pure macros, delegated JS events, and shared upload validation via `save_run_file`.
- Omni scenarios and contrast controls now render through `omni_scenarios_pure.htm` / `omni_contrasts_pure.htm`; documentation and inventory entries updated accordingly.
