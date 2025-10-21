# Omni Control Migration Plan

> Current-state audit and migration blueprint for refactoring the Omni scenario runner and contrast tooling onto the Pure `runs₀` stack.

## Why Now

- Omni is the largest control still tied to the legacy `runs₀` layout; documenting it now unblocks the final Pure rollout.
- Scenario orchestration overlaps with newly migrated Pure controls (climate, ash, RAP TS), so aligning Omni prevents divergent UX patterns.
- Support teams already field questions about Pure parity—capturing gaps lets us communicate timelines and dependencies clearly.

## Scope & Objectives

- Document the full behaviour of the legacy Omni control before any Pure rewrite, covering UI fragments, JavaScript orchestration, NoDb interactions, RQ workflows, and file uploads.
- Identify coupling points (scenario builder, contrast definitions, uploads, status streaming) that must survive migration to the Pure component model.
- Produce a phased migration plan—with testing strategy and open questions—to guide the conversion from the Bootstrap-era control to a Pure-first implementation.

## UI Inventory

### Scenario Runner (`wepppy/weppcloud/templates/controls/omni/omni_scenarios.htm`)

- Extends `controls/_base.htm`; the form id is `omni_form`, so controlBase wire-up and WebSocket routing hinge on this identifier. Sections sit within Bootstrap grid classes (`row`, `col-md-*`, `card`).
- Scenario list container: `<div id="scenario-container"></div>`; children are dynamically injected `.scenario-item` rows. Remove buttons call `this.parentElement.parentElement.remove()` inline—no custom events fired.
- Run trigger: `button#btn_run_omni` with inline `onclick="Omni.getInstance().run_omni_scenarios()"`. Status and hint fields reuse `#status`, `#stacktrace`, and `#hint_run_omni` from `_base.htm`.
- Inline `<style>` block defines layout for `.scenario-item`, `.remove-btn-col`, and `.scenario-controls`; still Bootstrap-dependent.
- The control is only rendered on the legacy run page (`routes/run_0/templates/0.htm`). `runs0_pure.htm` has no Omni slot yet, so the control remains outside the Pure layout.

### Inline Scenario Builder Script (same template)

- Declares a global `const scenarios` map describing available scenario types, labels, and control metadata. Options include `uniform_*`, `sbs_map`, `undisturbed`, `prescribed_fire`, `thinning`, and `mulch`.
- Conditional availability leverages global controllers: e.g., `condition: () => Disturbed.getInstance()?.has_sbs() || false`. This assumes `Disturbed` has already been bootstrapped and introduces tight coupling.
- `addScenario()` creates a `.scenario-item` with a repeated `id="scenario-select"` and a `<select name="scenario">`. Options are filtered using the `condition` callbacks at render time.
- `updateControls(select)` populates `.scenario-controls` with `<select>` or `<input type="file">` elements according to the scenario metadata. Generated controls reuse `id` values equal to the `name`, so duplicates appear across items.
- The script exposes `addScenario` and `updateControls` as globals referenced by inline attributes (`onclick`, `onchange`). There is no module encapsulation and no hook for restoring server-saved state other than direct DOM manipulation.

### Contrast Definition Panel (`wepppy/weppcloud/templates/controls/omni/omni_contrasts_definition.htm`)

- Also extends `_base.htm` with `form_id` `omni_form`, so both scenario runner and contrast definitions share a single form instance.
- UI relies on Bootstrap tooltips (`data-toggle="tooltip"`) and icon images for inline help. Inputs:
  - `select#omni_contrast_objective_parameter` supplies metric choices (`Soil_Loss_kg`, `Runoff_mm`, etc.) but both the control and help icon reference the same id. When multiple Omni panels render (legacy vs preview), this produces duplicate ids that must be resolved.
  - Two `<select>` elements meant for control and contrast scenarios both use `id="omni_control_scenario"` (duplicate id). Option values such as `mulching30` are legacy naming and do not match the current `mulch` scenario metadata.
  - Numeric input `#contrast_cumulative_obj_param_threshold_fraction`. Name lacks the `omni_` prefix expected by the NoDb parser.
- Submission button `#btn_define_omni_contrasts` calls `Omni.getInstance().run_omni_define_contrasts()`, but no such method exists in the shipped JavaScript. As a result, the contrast UI is effectively inert in production.
- Hints and lock indicators reuse `#hint_run_omni` from the scenario runner, causing mixed messaging when both sections coexist.

### Other Touch Points

- `routes/run_0/templates/run_page_bootstrap.js.j2` instantiates `Omni` on page load, calls `omni.load_scenarios_from_backend()`, reapplies saved RQ job ids, and conditionally fetches the scenarios report if runs already exist.
- `controls/poweruser_panel.htm` surfaces a “Migrate to Omni” button (`Project.getInstance().migrate_to_omni()`), which triggers `GET /tasks/omni_migration`.

## JavaScript Behaviour (`wepppy/weppcloud/controllers_js/omni.js` + inline helpers)

- Module pattern: Immediately invoked `Omni` singleton layered on `controlBase()`. Requires global jQuery, Bootstrap tooltips, `WSClient`, and helpers such as `url_for_run`, `Project`, and `controlBase`.
- DOM wiring: caches `#omni_form`, `#info`, `#status`, `#stacktrace`, `#rq_job`, and command button `btn_run_omni`. Instantiates `new WSClient('omni_form', 'omni')` and overrides `triggerEvent` to handle `OMNI_SCENARIO_RUN_TASK_COMPLETED` (pull report) and `END_BROADCAST` (disconnect socket).
- Exported methods and helpers:
  - `serializeScenarios()` – iterate `.scenario-item` nodes, gather `<select name="scenario">` and related inputs, append files as `scenarios[{index}][name]`, and stringify the scenario list into `FormData`.
  - `run_omni_scenarios()` – submit multipart payload via `$.post` to `/rq/api/run_omni`, update status text, and record the returned job id.
  - `load_scenarios_from_backend()` – fetch `/api/omni/get_scenarios`, create DOM rows with global `addScenario()`, hydrate inputs, and silently skip file paths (cannot be restored).
  - `report_scenarios()` – defined twice; the second definition fetches `/report/omni_scenarios/` and injects HTML into `#info`, effectively shadowing the earlier placeholder.
  - `triggerEvent()` override – keeps default `controlBase` behaviour while adding report refresh/disconnect logic.
- Inline helpers (defined inside the template) supply `addScenario()`, `updateControls()`, and the mutable `scenarios` catalog; these live on `window`.
- Missing behaviour: No implementation for `run_omni_define_contrasts()` or any front-end call to `/rq/api/run_omni_contrasts`, so the contrasts button does nothing.

## Backend Mapping

- **`GET /api/omni/get_scenarios`** → `Omni.getInstance(wd).scenarios`. Returns the persisted list of scenario dictionaries (string `type` plus ancillary fields or file paths).
- **`GET /api/omni/get_scenario_run_state`** → exposes `Omni.scenario_run_state` and `Omni.scenario_dependency_tree`, allowing clients to render dependency graphs or progress indicators (unused by current UI).
- **`GET /tasks/omni_migration`** → Adds `omni` (and optionally `treatments`) to `Ron._mods`, seeds `omni.nodb` and `treatments.nodb`.
- **`GET /report/omni_scenarios`** → Builds a summary view by pulling `Omni.scenarios_report()` (aggregated `loss_pw0.out.parquet`) and rendering `templates/reports/omni/omni_scenarios_summary.htm`.
- **`POST /rq/api/run_omni`**:
  - Expects multipart FormData with `scenarios` JSON.
  - Persists uploads to `wd/omni/_limbo/{idx:02d}/{secure_filename}` before scenarios run.
  - Maps each entry to `(OmniScenario, params)` and calls `Omni.parse_scenarios`.
  - During execution, files are copied into `_pups/omni/scenarios/<scenario_name>/disturbed/{filename}` and removed from `_limbo`.
  - Queues `run_omni_scenarios_rq` and stores job metadata in `RedisPrep` (Task `run_omni_scenarios`).
- **`POST /rq/api/run_omni_contrasts`**:
  - Currently identical to `run_omni`—it parses scenarios and queues `run_omni_scenarios_rq`. No distinct contrasts workflow is triggered, hinting at an incomplete migration.
- **RQ worker (`wepppy/rq/omni_rq.py`)**:
  - `run_omni_scenarios_rq` decides whether to execute sequentially or via the job pool. Publishes `OMNI_SCENARIO_RUN_TASK_COMPLETED` and `END_BROADCAST` events to the Omni WebSocket channel.
  - `run_omni_scenario_rq` (worker helper) handles per-scenario execution, dependency hashing, and run-state persistence.
- **NoDb (`wepppy/nodb/mods/omni/omni.py`)**:
  - Stores `scenarios`, `contrasts`, dependency trees, run states, and numerous contrast parameters (`_contrast_*`).
  - `run_omni_scenarios()` clones working directories into `_pups/omni/scenarios/<scenario_name>/`, applies treatments (`Treatments`, `Disturbed`, `Landuse`, `Soils`), and runs WEPP. Each scenario writes `_pups/omni/scenarios/<scenario_name>/wepp/output/loss_pw0.out.parquet`; combined output persists as `_pups/omni/scenarios.out.parquet`.
  - `run_omni_contrasts()` builds contrasts, writes NDJSON audit trails to `_pups/omni/contrasts/build_report.ndjson`, and invokes `_run_contrast` to clone sibling runs into `_pups/omni/contrasts/{contrast_id}/`.
  - Uploads are consumed during scenario execution—`SBSmap` files move from `_limbo` into the scenario Disturbed directory.

## Uploads & External Dependencies

- SBS map scenarios rely on user-provided rasters uploaded through the scenario builder. Files are saved via `secure_filename` but there is no size, extension, or content validation beyond `accept=".tif,.img"` on the `<input>`. `_limbo` directories remain after job completion unless cleanup occurs elsewhere.
- Upload code bypasses shared helpers in `weppcloud/utils/uploads.py`; instead, the RQ route manually writes files.
- Omni scenario execution depends on multiple controllers: `Disturbed.getInstance(new_wd)`, `Landuse`, `Soils`, `Treatments`, and `Wepp`. Treatment application expects keys like `mulch_15` or `thinning_40_93`, derived from inline option strings.
- Worker orchestration expects Redis (status messenger) and optional Discord notifications (`send_discord_message`) if installed.

## Pain Points

| Area | Issue | Impact |
|------|-------|--------|
| UI structure | Inline scripts, shared `omni_form`, duplicate ids (`scenario-select`, `omni_control_scenario`, `hint_run_omni`, repeated labels) | Breaks accessibility; hard to port into Pure components |
| JavaScript | Globals (`addScenario`, `updateControls`, `scenarios`), missing `run_omni_define_contrasts`, duplicate `report_scenarios`, jQuery AJAX dependency | Difficult to test; contrasts button is inert |
| Backend | `/rq/api/run_omni_contrasts` enqueues scenarios job; uploads bypass shared helpers; `_limbo` cleanup undefined | Contrasts never run; orphaned files accumulate |
| RQ coupling | `use_rq_job_pool_concurrency` hidden from UI; WebSocket events assumed by `controlBase` | Limits visibility of background progress in new UI |
| Data model | Legacy values (`mulching30`, `mulching60`) and missing `omni_*` prefixes in posted fields | Parser inconsistencies and runtime errors |
| Pure integration | No Pure template inclusion; Bootstrap tooltips and cards unfriendly to Pure styling | Requires full design work before migration |

## Migration Blueprint

1. **Confirm domain contracts**
   - Inventory final scenario types, parameter requirements, and treatment mappings with product/domain owners.
   - Decide how contrast definitions should work (including advanced filters) and whether `/rq/api/run_omni_contrasts` needs a dedicated worker.
   - Clarify expectations for persisted uploads (retention policy, validation limits, clean-up).
2. **Refactor backend APIs**
   - Split contrasts into a separate endpoint that calls a new `run_omni_contrasts_rq`.
   - Expose a `GET /api/omni/scenario-catalog` (JSON metadata) so the front-end no longer embeds the `scenarios` map inline.
   - Normalize form payloads (use consistent `omni_*` prefixes, ensure enums match `OmniScenario.parse`).
   - Adopt `save_run_file` / upload helper utilities with extension and size validation; stream uploads to `_limbo` deterministically.
3. **Design Pure components**
   - Create a Pure panel (`<wc-omni-scenarios>`) for scenario management with subcomponents for the list, scenario editor, and add/remove actions.
   - Build a separate contrast definition component with accessible form controls, contextual help, and error states.
   - Introduce a status panel summarizing queued/running/completed scenarios using `scenarios_run_state`.
4. **Modernize JavaScript**
   - Rewrite the controller as an ES module that exports lifecycle hooks for Pure. Replace jQuery AJAX with `fetch` (`multipart/form-data` still required).
   - Encapsulate scenario state in a store (e.g., reactive signal) that keeps per-scenario form data, including staging for uploads.
   - Wire WebSocket events through the shared `WSClient` wrapper but publish state changes to Pure components instead of manipulating DOM directly.
   - Implement `defineContrasts()` front-end logic to call the new contrasts endpoint and surface progress feedback.
5. **UI/UX Improvements**
   - Replace Bootstrap tooltips and cards with Pure equivalents; enforce unique ids and accessible labels.
   - Provide inline validation for missing parameters, incompatible base scenarios, and duplicate scenario combinations.
   - Support drag-to-reorder or grouping if analysts need deterministic execution order (verify requirement).
6. **Backend & contrasts remediation**
   - Ship a working `run_omni_define_contrasts()` (or equivalent) that calls a corrected `/rq/api/run_omni_contrasts` endpoint *before* porting the UI.
   - Create a dedicated RQ worker (`run_omni_contrasts_rq`) that consumes persisted contrast definitions and emits WebSocket updates.
   - Backfill unit tests to confirm contrasts enqueue properly and populate `_pups/omni/contrasts/*` outputs.
7. **Data & file management**
   - Persist scenario definitions with stable identifiers so editing/reordering in Pure never loses association with prior uploads.
   - Add cleanup hooks for `_limbo` after jobs run (perhaps in `run_omni_scenario_rq`), logging what was removed.
8. **Testing Strategy**
   - **Backend**: Extend `tests/omni/run_contrasts.py` and add new tests covering `parse_scenarios`, `run_omni_contrasts` endpoint, and upload validation logic.
   - **Front-end**: Add Jest (or Vitest) coverage for scenario store utilities and serialization logic; include integration tests that mock fetch responses.
   - **Manual**: Exercise scenario permutations (uniform burn, thinning, mulching with uploads) and confirm WebSocket-driven status updates render in the Pure UI.
9. **Rollout**
   - Ship the Pure control behind a feature flag or per-run toggle; keep the legacy control available until parity is validated.
   - Update documentation (`control-inventory`, run guides) and train power users on new flows.

## Open Questions / Assumptions

- Do analysts require additional scenario types (e.g., `mulching30`, `mulching60`) beyond the current `mulch` with parameters, or can we deprecate legacy naming?
- Should the contrast workflow remain coupled to scenario definitions, or can contrasts be defined independently after runs complete?
- What is the desired retention policy for uploaded SBS rasters—should they live alongside run artifacts or be purged post-run?
- Does the team expect real-time progress per scenario (job pool concurrency) in the UI, implying additional status endpoints?
- Are there non-default locale or unit requirements (metric vs imperial) that should be addressed during the Pure migration?

## Summary

- Omni today mixes inline scripts, duplicated ids, and jQuery-era patterns across scenario building, contrasts, and uploads, with no Pure integration.
- Scenario execution relies on multipart submissions to `/rq/api/run_omni`, manual `_limbo` file staging, and RQ workers that clone run directories and apply treatments through multiple NoDb controllers.
- The contrasts UI is incomplete—front-end handlers and the RQ entry point are missing—so the plan prioritises backend/API fixes (see step 6) before the Pure rewrite proceeds.
- Migrating to Pure requires untangling inline metadata, modernizing JavaScript, formalizing endpoints (especially for contrasts), and introducing upload validation and cleanup.
- With backend contracts clarified and a staged plan in place, we can build a Pure component suite that surfaces scenario status, supports accessible forms, and leverages shared upload helpers while maintaining existing analytical capabilities.
