# Ash Control Implementation Plan

## Why Now

- Keep pace with the Pure `runs₀` layout rollout so the ash control can slot into the new shell without Bootstrap shims.
- Consolidate file handling on `wepppy/weppcloud/utils/uploads.py` so future validation changes live in one helper instead of per-control scripts.
- Pay down legacy JS debt (inline scripts, jQuery/Bootstrap dependencies) before additional telemetry and catalog integrations ship later this release.

> Current-state audit and migration blueprint for rebuilding the Wildfire Ash Transport And Risk (WATAR) control on the Pure UI stack.

## UI Inventory (wepppy/weppcloud/templates/controls/ash.htm)

- **Legacy scaffold**: Extends `controls/_base.htm`; form id `ash_form`. Relies on Bootstrap grid classes and inline scripts defined inside the template.
- **Intro copy**: Two `<p>` blocks describing climate requirements and roughness limits (white/black thresholds injected from NoDb). Informational only; not posted.
- **Fire date**: `input#fire_date` (text) seeded with `ash.fire_date`. Included in the submitted `run_ash` payload.
- **Depth mode radios**: Three inline radio buttons (all re-use the same `id="ash_depth_mode"`—a migration risk) representing `Specify Depth (1)`, `Specify Load (0)`, and `Upload Maps (2)`. Each posts the value and uses inline `onchange="Ash.getInstance().handleDepthModeChange(this.value)"`.
- **Depth inputs (`ash_depth_mode1_controls`)**: Fields for black/white initial depths (`ini_black_depth`, `ini_white_depth`) sent when mode=1.
- **Load inputs (`ash_depth_mode0_controls`)**: Fields for black/white initial loads (`ini_black_load`, `ini_white_load`) plus implicit conversion using field bulk densities; posted when mode=0.
- **Upload block (`ash_depth_mode2_controls`)**:
  - File inputs `#input_upload_ash_load` and `#input_upload_ash_type_map` (class `file`, expecting `.img` or `.tif`). Copy clarifies load units (tonne/ha) and ash-type encoding (0/1/2).
  - Inputs attach to the same `run_ash` POST; no dedicated upload endpoint today. No inline validation—backend handles errors silently.
- **Field bulk density inputs**: `field_black_bulkdensity`, `field_white_bulkdensity` (text) posted with every submission; used both for load-to-depth conversion and persisted in NoDb.
- **Advanced Options toggle**: `<a href="#ash_advanced_opts_con" data-toggle="collapse">`. Requires Bootstrap collapse JS.
  - **Wind transport checkbox**: `#checkbox_run_wind_transport` toggled via inline `onchange="Ash.getInstance().set_wind_transport(this.checked);"`.
  - **Model selector**: `<select id="ash_model_select" name="ash_model">` populated from `ash.available_models`. Inline JS `updateAshModelForm()` handles parameter updates.
  - **Transport mode (Alex only)**: `<select id="ash_transport_mode_select" name="transport_mode">` controlling dynamic/static parameter grouping plus description blocks `#dynamic_description` and `#static_description`.
  - **Parameter matrix**: Inputs named `white_*` and `black_*` for both models. `anu-only-param`, `alex-only-param`, `alex-dynamic-param`, `alex-static-param` classes drive display toggles.
- **Run button**: `button#btn_run_ash` triggers `Ash.getInstance().run();`. Includes lock icon `#run_ash_lock` and hint span `#hint_run_ash`.
- **Model preset payload**:
  - Pure template emits a `<script type="application/json" id="ash-model-params-data">` block with calibration parameters; the legacy template still ships a global `modelParams` constant and inline `updateAshModelForm`.
  - All event wiring (model select, transport mode, run button, wind checkbox) now relies on `data-ash-*` hooks rather than inline handlers in the Pure view.

## JavaScript Behavior (wepppy/weppcloud/controllers_js/ash.js)

- **Module pattern**: `Ash` remains a singleton on top of `controlBase()`, but now exposes `initializeForm()` to hydrate Pure controls and legacy markup alike.
- **Dependencies**:
  - jQuery still backs ControlBase status helpers and the AJAX calls, but all DOM wiring happens with vanilla listeners.
  - Global helpers: `controlBase`, `WSClient`, `Project`, `url_for_run`. Bootstrap collapse is still required only for the legacy `_base.htm` template.
  - Browser APIs: `FormData`, `ResizeObserver`, `window.addEventListener`.
- **State wiring**:
  - `initializeForm()` grabs references (form, radios, selects, file inputs, status hint) and parses model presets from a `<script type="application/json" id="ash-model-params-data">` payload (falls back to the legacy `window.modelParams`).
  - User edits are cached per model and per ash color so toggling between Srivastava (`multi`) and Watanabe (`alex`) restores the last values entered instead of resetting to defaults.
- **Actions**:
  - `run()`: Clears validation hints, enforces upload size/extension rules when “Upload Maps” is selected, then posts `FormData` to `rq/api/run_ash` and tracks the job via WebSocket.
  - `set_wind_transport(state)`: Posts JSON to `tasks/set_ash_wind_transport/`; both the Pure checkbox and legacy inline handler call the same method.
  - `report()`: Pulls `report/run_ash/`, writes summary HTML, and reapplies preferred units.
  - `hideStacktrace()`: Resets stacktrace output after errors.
- **Interplay**:
  - `setAshDepthMode()` normalises duplicate radio wiring, keeps the selected value in sync, and toggles the three mode containers without jQuery `show/hide`.
  - `updateModelForm()` merges defaults + cached overrides, flips Alex-only panels based on the selected transport mode, and is exported to `window.updateAshModelForm` so legacy inline hooks keep working.
- **Bootstrap wiring (run_page_bootstrap.js.j2)**:
  - Binds change listeners to `[name='ash_depth_mode']` to call `ash.setAshDepthMode()`.
  - Calls `ash.report()` when `ron.has_ash_results` is true.
  - Restores RQ job ids (`rq_job_ids["run_ash_rq"]`) and initial depth mode (`ash.setAshDepthMode({{ ash.ash_depth_mode }})`).
  - Ensures `ash.showHideControls()` runs on load.
- **Legacy selectors/plugins**:
  - File inputs rely on `.file` class (Bootstrap FileInput plugin, still referenced globally).
  - Pure migration should replace these with the shared `ui.file_upload` macro (e.g., `{{ ui.file_upload("input_upload_ash_load", ... ) }}`) so styling and readonly wiring follow the Pure stack.
  - `data-toggle="collapse"` uses Bootstrap’s jQuery plugin, so Pure rewrite must replace or polyfill collapse behavior.

## Backend Mapping

- **Primary RQ endpoint**: `POST /runs/<runid>/<config>/rq/api/run_ash`
  - Validates `ash_depth_mode`, calculates initial depths (direct entry, load-to-depth conversion, or placeholder for raster mode).
  - Persists calibration parameters via `Ash.parse_inputs(dict(form))`.
  - For map uploads (`ash_depth_mode == 2`):
    - Calls `_task_upload_ash_map(wd, request, field)` which writes the raw file into `ash.ash_dir` with `secure_filename` (resulting in paths like `{wd}/ash/<filename>.tif`).
    - Switches `Ash._spatial_mode` to `Gridded` and stores the relative filenames in `_ash_load_fn`/`_ash_type_map_fn`. Later, `Ash.run_ash` reads `ash.ash_load_fn` / `ash.ash_type_map_fn` to crop rasters before simulation starts.
    - Uploads occur within the same RQ submission; there is no dedicated upload endpoint today.
  - Enqueues `run_ash_rq` with `Ash` fire date / init depths and registers job id through `RedisPrep`.
- **Ancillary endpoints (watar_bp.py)**:
  - `tasks/set_ash_wind_transport` toggles `ash.run_wind_transport`.
  - `report/run_ash` renders summary page (used after task completion).
  - `report/ash` and `report/ash_contaminant` supply deeper analytics (not triggered directly from control UI but part of Ash feature set).
  - `hillslope/<topaz_id>/ash` runs an on-demand per-hillslope simulation (used elsewhere).
- **NoDb controller (wepppy/nodb/mods/ash_transport/ash.py)**:
  - `Ash.parse_inputs` mutates model parameters depending on selected model (`multi` vs `alex`) and updates field bulk densities.
  - `Ash.run_ash` handles raster cropping (`raster_stacker`), climate and hydrology collection, per-hillslope model execution (optionally multiprocessed), and triggers `AshPost.run_post` plus Redis telemetry.
  - `Ash.ash_depth_mode`, `Ash.ash_load_fn`, `Ash.ash_type_map_fn`, and contaminant dictionaries drive persistence for subsequent UI renders.
- **Data structures driving UI**:
  - `ash.available_models` supplies label/value pairs.
  - `ash.anu_*` / `ash.alex_*` objects provide the parameter dictionaries serialized into `modelParams`.
  - `Ash.meta` contains hillslope metadata (burn class, ash type) used by reports; not surfaced in UI yet but relevant for deeper features.

## Locale & Mod Coverage

- **Feature gating**: Control injected into the run page only when `'ash' in ron.mods` (see `run_page_bootstrap.js.j2`).
- **Model availability**:
  - Default modes are always `multi` (Srivastava 2023) and `alex` (Watanabe 2025). Locale-specific catalog overrides should not hide either option so analysts can compare calibrations.
  - `ash.transport_mode` (dynamic vs static) currently stored only in Alex parameter objects; UI exposes global selector but backend expects per-color fields (`white_transport_mode`, `black_transport_mode`). Needs clarification/cleanup during migration.
- **Related mods**:
  - RAP time-series (`rap_ts`) shares RQ job list and UI area but does not interact directly with ash control.
  - Disturbed / BAER controllers provide burn severity data consumed implicitly by `Ash`.
- **Contaminant workflows**: `Ash.parse_cc_inputs` supports follow-on contaminant control; ensure new UI leaves hooks for those panels if they co-exist in certain locales.

## Upload Workflow (Legacy vs uploads.py)

- **Current path**:
  1. User selects “Upload Maps” depth mode.
  2. File inputs appended to `FormData` by `Ash.run()`.
  3. `_task_upload_ash_map` saves file directly under `{wd}/ash/<filename>` without:
     - Extension filtering.
     - Size checks.
     - Post-save validation (e.g., raster compatibility).
  4. Filenames persisted into `Ash` attributes; subsequent run uses `raster_stacker` to align rasters.
- **Available infrastructure**: `wepppy/weppcloud/utils/uploads.py` offers `save_run_file()` with extension allowlists, overwrite control, size limits, and post-save hooks.
- **Migration opportunities**:
  - Replace `_task_upload_ash_map` with `save_run_file(runid=..., form_field='input_upload_ash_load', allowed_extensions=('tif','tiff','img'), dest_subdir='ash', max_bytes=100 * 1024 * 1024)`.
  - Apply the same helper to `input_upload_ash_type_map`; no additional projection/resolution/nodata validation is required for this scope.
  - Keep uploads synchronous with `run_ash`; the helper enforces size/extension checks before the RQ job enqueues (no separate task needed).
  - Return structured JSON using `upload_success` / `upload_failure` for asynchronous uploads if Pure UI decouples uploads from the main `run_ash` action later.
- **Client UX**:
  - Pure controller now warns when uploads exceed 100 MB or use unsupported extensions before the request is sent; legacy template still lacks this preflight check.

## Pain Points & TODOs

- **Inline script sprawl**: Model parameter JSON and `updateAshModelForm()` live inside the template, making bundling/testing difficult.
- **Duplicate element IDs**: Resolved in the Pure template; legacy `_base.htm` markup still reuses `id="ash_depth_mode"` until it is retired.
- **Accessiblity gaps**: `<input input ...>` typos, missing `aria-describedby`, inconsistent label/field relationships, collapsed sections lacking focus management.
- **Mixed event wiring**: Pure component centralises listeners; legacy template continues to rely on inline handlers until it is removed.
- **Parameter mismatch**: Alex transport mode select posts `transport_mode`, but backend fields expect `white_transport_mode` / `black_transport_mode`; migration should preserve per-color fields so toggling between models or transport modes does not discard user-edited values.
- **Upload validation**: Client-side checks enforce extension/size and the backend now uses `save_run_file`; legacy template still lacks pre-submit hints.
- **jQuery dependence**: Control still hinges on Bootstrap/jQuery; migrating to Pure will require replacing collapse, AJAX, and DOM updates.
- **Hard-coded text**: Units and explanations embedded in template; migrating to dynamic components may warrant i18n-ready structure.
- **Telemetry UX**: Status/hint fields rely on text injection without consistent spinners or progress indicators.
- **Documentation gap**: No current high-level UI doc summarizing behavior—this plan fills that void but backend assumptions (e.g., expected raster statistics) remain implicit.

## Proposed Migration Steps (Pure stack)

1. **Confirm backend contracts**
   - Validate required form fields, expected types, and clarify transport-mode semantics with backend owners.
   - Confirm locale rules and parameter persistence expectations before altering form data structures.
   - Decide how `modelParams` (or equivalent) will be exposed post-migration—prefer JSON from a backend endpoint rather than embedding inline scripts.
   - Document desired raster validation rules (band types, nodata handling) before wiring uploads to new helper.
2. **Design Pure component**
   - Map legacy sections to Pure layout components (fire date, depth modes, advanced accordion).
   - Define state model capturing selected mode, parameters, and file metadata.
3. **Refactor JavaScript**
   - Port `Ash` controller into ES module that:
     - Manages state via Pure patterns (likely `@bearhive/pure` store or existing hooking).
     - Replaces jQuery/inline handlers with event listeners.
     - Reads calibration presets from inline Jinja payloads (or their successor) and exposes helpers so legacy inline hooks keep working.
     - Maintains per-model/per-color parameter caches so switching among `multi`, `alex`, dynamic, and static modes restores previously entered values.
4. **Integrate upload helper**
   - Keep uploads within the existing `run_ash` submission but validate using `save_run_file` with the new size/extension limits (done).
   - Surface pre-submit validation messaging (inline errors/toasts) when files exceed 100 MB or use unsupported extensions before the RQ job is enqueued (done in Pure controller; legacy template still pending).
   - Optional follow-up: explore staged uploads only if UX testing shows the combined submission is insufficient.
5. **Template conversion**
   - Move off `_base.htm`; create Pure-compatible template (likely `runs0_pure.htm` inclusion) with component mount point.
   - Ensure collapse/accordion behavior implemented via Pure components instead of Bootstrap.
6. **Accessibility & UX polish**
   - Normalize ids, labels, aria attributes.
   - Replace text inputs for dates with validated date picker or pattern masking.
   - Offer model parameter reset and diffing to highlight deviations from defaults.
7. **Testing & telemetry**
   - Add frontend tests (e.g., Jest/Playwright) for mode toggles and uploads.
   - Extend backend tests to cover upload validation and parameter persistence via new endpoints.
   - Verify websocket integration still triggers report refresh on job completion.
8. **Documentation & rollout**
   - Update `README.md` and this plan with final architecture.
   - Provide migration notes for operations (e.g., new upload requirements).

## Open Questions / Follow-Ups

- Are additional locales/mods expected to contribute bespoke parameter presets or hide sections (e.g., RONs without white ash)? Capture requirements once locale catalog work resumes.
- Confirm whether an existing backend endpoint can expose `modelParams`; if not, scope a lightweight JSON route to feed the Pure controller. *(Resolved: continue relying on inline Jinja payloads until backend changes require otherwise.)*

## Decisions & Action Items (2025-10-20)

- Keep separate `white_*` / `black_*` transport-mode fields and persist per-model parameter caches so toggling between calibrations retains user changes.
- Maintain map uploads inside the `run_ash` submission; enforce `<100 MB` size and `.tif`, `.tiff`, or `.img` extensions via `save_run_file`.
- Replace legacy `.file` inputs with the shared `ui.file_upload` macro when migrating to Pure and add inline error messaging for upload failures.
- Verify catalog settings expose both ash models (`multi`, `alex`) across all locales for consistency.

## References

- `docs/ui-docs/control-ui-styling/control-inventory.md`
- `docs/ui-docs/control-ui-styling/final-implementation-blueprint.md`
- `docs/ui-docs/control-ui-styling/runs0_pure_plan.md`
- `docs/ui-docs/ui-style-guide.md`
- `wepppy/nodb/mods/ash_transport/README.md`

*This document is an analysis pass only; no code changes accompany it.*
