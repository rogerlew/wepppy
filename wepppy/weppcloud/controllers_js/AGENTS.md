# controllers_js Agent Playbook

> Audience: AI coding agents working inside `wepppy/weppcloud/controllers_js/`.

## Mission Snapshot
- Maintain the run-controller bundle that powers WEPPcloud dashboards.
- Keep every controller aligned with the modernization program (helpers, unified payloads, documented contracts).
- Ensure the bundle build pipeline (`build_controllers_js.py`) and Jest suite stay green after every change.

## Foundations (read before coding)
See `docs/dev-notes/controller_foundations.md` for the canonical vision. Key pillars:
- **Shared UI primitives**: structure markup around `data-*` hooks so `WCDom`/`WCEvents` manage toggles, buttons, and lifecycle events consistently.
- **Unified payload schemas**: every controller/route pair runs through `parse_request_payload`; NoDb `parse_inputs` now expect native booleans/ints/floats (never `"on"` strings). Keep per-domain docs up to date.
- **Evolving `controlBase`**: treat it as the declarative job runner—prefer its lifecycle events (`job:started`, `job:completed`, `job:error`) over ad-hoc polling.
- **Documentation alignment**: when you add primitives or change payloads/events, update `controllers_js/README.md`, this playbook, and the domain contract doc.
- **Tooling expectations**: lint (`wctl run-npm lint`), test (`wctl run-npm test`), rebuild bundle, and run targeted pytest suites before handoff. Add Jest coverage when primitives or controller patterns evolve.

> Controllers should focus on domain logic while helpers + documented contracts handle the boilerplate. If you find yourself re-implementing plumbing, improve the shared primitives instead.

## Primary Assets
- Helpers: `dom.js`, `events.js`, `forms.js`, `http.js` (global namespaces exposed via IIFEs).
- Infrastructure: `control_base.js`, `status_stream.js`, `ws_client.js`, `unitizer_client.js`.
- Controllers: one file per control (`project.js`, `path_ce.js`, etc.).
- Template: `templates/controllers.js.j2` (rendered by `build_controllers_js.py`).
- Tests: `__tests__/` directory (Jest, jsdom environment).

## Standard Workflow
Follow `docs/dev-notes/module_refactor_workflow.md` for end-to-end instructions. Highlights:
1. **Scope**: audit jQuery usage, templates, backend routes, and domain documentation before editing.
2. **Plan**: decide which helpers (`WCDom`, `WCForms`, `WCHttp`, `WCEvents`, `controlBase`) you need and whether payloads switch to JSON.
3. **Implement**:
   - Use helper namespaces instead of direct DOM APIs; keep controllers wrapped in IIFEs that attach to `window`.
   - Update paired Flask routes in the same change using `parse_request_payload`; normalize booleans/arrays and adjust NoDb methods to read native types.
   - Remove inline jQuery bootstrap from templates; rely on module-level init or `DOMContentLoaded`.
4. **Document**: update `README.md`, this playbook, and any domain contract doc when behavior or payloads change.
5. **Validate**:
   - `wctl run-npm lint`, `wctl run-npm test` (or `wctl run-npm check`)
   - `python wepppy/weppcloud/controllers_js/build_controllers_js.py`
   - `wctl run-pytest tests/weppcloud/...` (targeted) and `wctl run-pytest tests --maxfail=1` when broad changes land.
   - Manual smoke test in the dev environment when practical.

## Controller Migration Tips
- Replace `$(selector)` with `WCDom.qs/qsa`, `delegate` for event delegation, and `toggle/hide/show` for visibility flips.
- Swap `$.ajax` or `$.get` with `WCHttp.request/getJson/postForm`.
- Use `WCForms.serializeForm` instead of `form.serialize()` and `WCForms.applyValues` for hydration.
- When controllers need event buses, prefer `WCEvents.createEmitter` or `WCEvents.emitDom`; `wepp.js` now emits `wepp:run:*` and `wepp:report:loaded` so neighbouring modules subscribe without polling DOM state.
- After refactoring, search for leftover `$(` in the module to ensure the jQuery dependency was removed.

### Project controller reference
- DOM hooks live on `data-project-field`, `data-project-toggle`, `data-project-action`, and `data-project-unitizer`. When the UI grows, add new `data-*` attributes and wire them through `WCDom.delegate` rather than binding inline handlers.
- `Project.getInstance().events` exposes a `WCEvents` emitter. Emitters currently surface `project:name:*`, `project:scenario:*`, `project:readonly:*`, `project:public:*`, and `project:unitizer:*` lifecycle events—subscribe instead of reading private state like `_currentName`.
- Unitizer integration now posts JSON payloads to `/tasks/set_unit_preferences/` and the backend returns the persisted preferences in `Content.preferences`. The global `window.setGlobalUnitizerPreference` helper simply forwards to `Project.handleGlobalUnitPreference`, so external scripts continue to function.
- Jest coverage for the controller lives in `__tests__/project.test.js`. When events, payloads, or data hooks change, expand that suite alongside template updates to lock in behaviour.

### Climate controller reference
- DOM hooks rely on `data-climate-action`, `data-climate-section`, and `data-precip-section` attributes plus the JSON seed embedded in `#climate_catalog_data`. Keep templates free of inline `on*` handlers—delegate through the controller instead.
- `Climate.getInstance().events` wraps `WCEvents.useEventMap` and currently publishes `climate:dataset:changed`, `climate:dataset:mode`, `climate:station:mode`, `climate:station:selected`, `climate:station:list:loading`, `climate:station:list:loaded`, `climate:build:started`, `climate:build:completed`, `climate:build:failed`, `climate:precip:mode`, `climate:upload:completed`, `climate:upload:failed`, and `climate:gridmet:updated`. Use these signals for dashboards and downstream automation.
- Network flows run through `WCHttp.postJson`/`request`; paired Flask routes now call `parse_request_payload` so JSON and form submissions behave the same. Update `wepppy/weppcloud/routes/nodb_api/climate_bp.py` alongside controller changes.
- Jest coverage lives in `controllers_js/__tests__/climate.test.js`; pytest coverage for the routes sits in `tests/weppcloud/routes/test_climate_bp.py`. Run both suites when editing climate code: `wctl run-npm test -- climate` (or the full suite) and `wctl run-pytest tests/weppcloud/routes/test_climate_bp.py`.
- After touching the controller, rebuild the bundle with `python wepppy/weppcloud/controllers_js/build_controllers_js.py` so the dev container picks up changes before you reload the UI.

### Subcatchment controller reference
- Markup now uses `data-subcatchment-action="build"` on the command button and `data-subcatchment-role` (`cmap-option`, `scale-range`) on radios/sliders. Avoid resurrecting inline `onclick` handlers—delegate through `WCDom`.
- `SubcatchmentDelineation.getInstance().events = WCEvents.useEventMap([...])` exposes `subcatchment:build:started`, `subcatchment:build:completed`, `subcatchment:build:error`, `subcatchment:map:mode`, and `subcatchment:legend:updated`. The controller still forwards `BUILD_SUBCATCHMENTS_TASK_COMPLETED` and `WATERSHED_ABSTRACTION_TASK_COMPLETED` through `triggerEvent` so Channel/WEPP integrations stay intact.
- Build requests post JSON with `WCHttp.postJson("rq/api/build_subcatchments_and_abstract_watershed", WCForms.serializeForm(form, { format: "json" }))`. The Flask route runs through `parse_request_payload`, converting booleans (`clip_hillslopes`, `walk_flowpaths`, `mofe_buffer`, `bieger2015_widths`) and floats before mutating the `Watershed` singleton and queueing RQ work.
- Keep tests updated: `controllers_js/__tests__/subcatchment_delineation.test.js` (jsdom) exercises build submission, delegated map toggles, and error propagation; `tests/weppcloud/routes/test_rq_api_subcatchments.py` (pytest) covers RedisPrep/queue wiring and batch short-circuiting. Run them with the standard `wctl run-npm test` / `wctl run-pytest tests/weppcloud/routes/test_rq_api_subcatchments.py` cadence and rebuild the bundle afterwards.

### Ash controller reference
- DOM hooks rely on `data-ash-*` attributes (`data-ash-depth-mode`, `data-ash-action`, `data-ash-upload`) plus the JSON seed in `#ash-model-params-data`. Remove inline `on*` handlers—delegate through `WCDom`.
- `Ash.getInstance().events = WCEvents.useEventMap([...])` emits `ash:mode:changed`, `ash:model:changed`, `ash:transport:mode`, `ash:run:started`, `ash:run:completed`, and `ash:model:values:capture`. Emit new signals instead of mutating controller internals so dashboards can subscribe cleanly.
- The `/rq/api/run_ash` route now runs everything through `parse_request_payload` and `Ash.parse_inputs` consumes native booleans/ints/floats. Keep routes and NoDb signatures aligned when payloads evolve.
- Lint/test cadence: `wctl run-npm lint`, `wctl run-npm test -- ash`, `python wepppy/weppcloud/controllers_js/build_controllers_js.py`, and `wctl run-pytest tests/weppcloud/routes/test_rq_api_ash.py`. The Jest suite exercises depth-mode toggles, cache persistence, run submission, and error handling; pytest covers payload normalisation and RQ enqueue logic.

### Landuse Modify controller reference
- DOM hooks now live on `data-landuse-modify-action="toggle-selection|submit"` and `data-landuse-modify-field="topaz-ids|landuse-code"` inside `modify_landuse.htm`. Selection mode relies on delegated listeners (`WCDom.delegate`) plus Leaflet overlays from `MapController`; add future map behaviours through helper-friendly data attributes rather than inline scripts.
- Events: `LanduseModify.getInstance().events = WCEvents.useEventMap(['landuse:modify:started', 'landuse:modify:completed', 'landuse:modify:error', 'landuse:selection:changed', 'job:started', 'job:completed', 'job:error'])`. Subscribe to these topics (or the inherited `controlBase` lifecycle events) instead of inspecting internal sets when other modules need to react to landuse updates.
- Transport: modification submissions post JSON to `tasks/modify_landuse/` (`{ topaz_ids: [...], landuse: '<code>' }`) via `WCHttp.postJson`. Rectangle selections call `tasks/sub_intersection/` with a JSON extent; the Flask route now normalises IDs through `_coerce_topaz_ids` / `_coerce_landuse_code`. Keep payload schemas documented in `docs/dev-notes/landuse-modify-controller-plan.md` when they evolve.
- Testing: Jest coverage (`controllers_js/__tests__/landuse_modify.test.js`) exercises selection toggles, event emission, and error handling with stubbed MapController/Leaflet helpers. Backend behaviour is locked down in `tests/weppcloud/routes/test_landuse_bp.py`—run those alongside `wctl run-npm test` and `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py tests/weppcloud/routes/test_rq_api_landuse.py` during refactors.

### Omni controller reference
- DOM hooks now rely on `data-omni-action` (`add-scenario`, `run-scenarios`), delegated scenario selectors tagged with `data-omni-role="scenario-select"`, and per-row containers marked `data-omni-scenario-controls`. Templates no longer ship inline scripts—let the controller render scenario cards dynamically and document any new `data-omni-*` hooks when requirements change.
- `Omni.getInstance().events = WCEvents.useEventMap([...])` publishes `omni:scenario:added`, `omni:scenario:removed`, `omni:scenario:updated`, `omni:scenarios:loaded`, `omni:run:started`, `omni:run:completed`, and `omni:run:error`. Subscribe to these lifecycle signals instead of reading internal state when other controls (status panels, unitizer) need to react.
- Scenario submissions build a `FormData` payload containing `scenarios` JSON plus optional SBS uploads; backend routes `/rq/api/run_omni` and `/rq/api/run_omni_contrasts` call `parse_request_payload` so JSON and multipart submissions share one parser. SBS files stage in `omni/_limbo/{idx}` via `save_run_file`, and payloads hydrate `Omni.parse_scenarios` with native values (no `"on"` strings).
- Validation happens client-side for SBS uploads (allowed extensions + 100 MB cap) before hitting the network; failures emit `omni:run:error` and surface in the legacy status area via `controlBase`.
- Testing cadence: `wctl run-npm lint`, `wctl run-npm test -- omni`, `python wepppy/weppcloud/controllers_js/build_controllers_js.py`, and `wctl run-pytest tests/weppcloud/routes/test_rq_api_omni.py`. The Jest suite (`__tests__/omni.test.js`) covers FormData serialization, scenario hydration, and validation; pytest exercises JSON vs multipart payloads, Redis queue wiring, and SBS upload staging.

### Outlet controller reference
- DOM hooks now rely on `data-outlet-root` to scope delegated listeners, `data-outlet-mode-section` for cursor vs entry panels, `data-outlet-entry-field` on the coordinate input, and `data-outlet-action="cursor-toggle|entry-submit"` on mode buttons. Keep markup helper-friendly—no inline handlers or hard-coded `display: none`.
- `Outlet.getInstance().events = WCEvents.useEventMap([...])` emits `outlet:mode:change`, `outlet:cursor:toggle`, `outlet:set:start`, `outlet:set:queued`, `outlet:set:success`, `outlet:set:error`, and `outlet:display:refresh`. Pair these domain events with the `controlBase` lifecycle signals (`job:started`, `job:completed`, `job:error`) for dashboards and dependent controllers.
- Submissions call `WCHttp.request("rq/api/set_outlet", { json: { latitude, longitude }, form })`; the Flask route consumes JSON/form payloads through `parse_request_payload`, normalises floats, clears `RedisPrep` timestamps, and enqueues `set_outlet_rq`.
- Testing cadence mirrors the modernization workflow: `wctl run-npm lint`, `wctl run-npm test -- outlet`, rebuild with `python wepppy/weppcloud/controllers_js/build_controllers_js.py`, and run `wctl run-pytest tests/weppcloud/routes/test_rq_api_outlet.py` (plus the broader suite as needed).

### BAER controller reference
- DOM hooks: radios expose `data-baer-mode` and control panels `#sbs_mode{0,1}_controls`; buttons advertise intent via `data-baer-action="upload|remove|build-uniform|set-firedate|modify-classes|modify-color-map"` plus `data-baer-uniform` (severity) and optional `data-baer-target` selectors. The opacity slider is generated under `#sbs_legend` as `#baer-opacity-slider`.
- Events: `Baer.getInstance().events = WCEvents.useEventMap([...])` publishes `baer:*` topics covering mode changes, SBS uploads/removals/uniform builds, fire-date updates, class/color-map edits, and map visibility (`baer:map:shown|error|opacity`). Combine these with `controlBase` lifecycle events for RQ telemetry.
- Transport: uploads submit `FormData` to `tasks/upload_sbs/`; removals hit `tasks/remove_sbs`; uniform maps call `tasks/build_uniform_sbs/<value>`. JSON endpoints (`tasks/set_firedate/`, `tasks/modify_burn_class`, `tasks/modify_color_map`) flow through `parse_request_payload` so class breaks arrive as ints and nodata tokens stay trimmed. Map previews request `query/baer_wgs_map/` followed by `resources/legends/sbs/`.
- Tests: update `controllers_js/__tests__/baer.test.js` for UI/HTTP behaviour and `tests/weppcloud/routes/test_disturbed_bp.py` for backend parsing. Always run `wctl run-npm lint`, `wctl run-npm test -- baer` (or the full suite), rebuild the bundle, and execute the disturbed blueprint pytest cases when BAER changes land.
- Documentation: capture new payload fields, emitted events, and helper expectations in `docs/dev-notes/baer-controller-plan.md` alongside this playbook.

### Disturbed controller reference
- DOM hooks: Pure SBS markup now depends on `data-sbs-action`, `data-sbs-uniform`, and `[data-disturbed-action]` plus the legacy hint nodes (`#hint_upload_sbs`, `#hint_remove_sbs`, `#hint_low_sbs`, `#hint_moderate_sbs`, `#hint_high_sbs`). Keep new affordances helper-friendly—no inline handlers.
- Events: `Disturbed.getInstance().events = WCEvents.useEventMap(['disturbed:mode:changed', 'disturbed:sbs:state', 'disturbed:lookup:reset', 'disturbed:lookup:extended', 'disturbed:lookup:error', 'disturbed:upload:started', 'disturbed:upload:completed', 'disturbed:upload:error', 'disturbed:remove:started', 'disturbed:remove:completed', 'disturbed:remove:error', 'disturbed:uniform:started', 'disturbed:uniform:completed', 'disturbed:uniform:error', 'disturbed:firedate:updated', 'disturbed:firedate:error'])`. The controller also dispatches `CustomEvent('disturbed:has_sbs_changed')` for legacy listeners and triggers `controlBase` job events with task IDs prefixed `disturbed:`.
- Transport: lookup resets/extends issue `POST` requests with empty bodies; uniform builds post JSON to `tasks/build_uniform_sbs` (`{"value": int}`) while the `<value>` route remains for older clients; fire dates post JSON to `tasks/set_firedate/`; uploads remain `FormData`; `has_sbs` polls `api/disturbed/has_sbs/`. All routes parse through `parse_request_payload` so downstream code receives native types.
- Tests: front-end coverage in `controllers_js/__tests__/disturbed.test.js`; backend regression in `tests/weppcloud/routes/test_disturbed_bp.py` using `tests/factories.singleton_factory` + `rq_environment`. Run `wctl run-npm lint`, `wctl run-npm test -- disturbed`, rebuild the bundle, `wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py`, and `wctl run-pytest tests --maxfail=1` when shared modules are touched.

### Debris Flow controller reference
- DOM hooks: the run button in both legacy and pure templates now exposes `data-debris-action="run"` inside `#debris_flow_form`. Add future controls under a `data-debris-*` namespace and rely on `WCDom.delegate` rather than inline handlers.
- Events: `DebrisFlow.getInstance().events = WCEvents.useEventMap(['debris:run:started', 'debris:run:completed', 'debris:run:error'])`. Emit these alongside the `controlBase` lifecycle events (`job:started|completed|error`) whenever runs queue, finish, or fail so dashboards and neighbours stay aligned.
- Transport: submissions call `WCHttp.postJson("rq/api/run_debris_flow", payload)`; the Flask route now runs the body through `parse_request_payload`, coercing optional `clay_pct` / `liquid_limit` floats and an optional `datasource` string before enqueuing `run_debris_flow_rq(runid, payload=…)`. The RQ task forwards the native values to `DebrisFlow.run_debris_flow(cc=…, ll=…, req_datasource=…)`—no more `"on"` checks.
- Tests: frontend coverage in `controllers_js/__tests__/debris_flow.test.js`; backend validation in `tests/weppcloud/routes/test_rq_api_debris_flow.py` and `tests/rq/test_project_rq_debris_flow.py`. During edits run `wctl run-npm lint`, `wctl run-npm test -- debris_flow`, rebuild the bundle, and execute the targeted pytest suites.
- Documentation: `docs/dev-notes/debris-flow-controller-plan.md` tracks the payload schema, event contracts, and follow-up tasks. Update it alongside this playbook when behaviour changes.

### DSS Export controller reference
- DOM hooks: radios expose `data-action="dss-export-mode"` + `data-dss-export-mode="<1|2>"`, the command button uses `data-action="dss-export-run"`, and the mode stacks stay under `#dss_export_mode1_controls` / `#dss_export_mode2_controls` so `WCDom.show/hide` handles toggles. Keep status/stacktrace/info within `#dss_export_form` for `controlBase` and `WSClient`.
- Events: `DssExport.getInstance().events = WCEvents.useEventMap(['dss:mode:changed', 'dss:export:started', 'dss:export:completed', 'dss:export:error', 'job:started', 'job:completed', 'job:error'])`. Emit the `dss:*` events for domain listeners (dashboards, run completion prompts) while the inherited `job:*` events keep telemetry pipelines in sync.
- Transport: queue submissions call `WCHttp.postJson("rq/api/post_dss_export_rq", { dss_export_mode, dss_export_channel_ids, dss_export_exclude_orders })`. The Flask route now leans entirely on `parse_request_payload`, normalizes JSON or legacy form posts to native ints/booleans, derives channel IDs from `Watershed.chns_summary` for mode 2, and persists via `wepp.dss_export_mode`, `wepp.dss_excluded_channel_orders`, and `wepp.dss_export_channel_ids`.
- Tests: front-end assertions in `controllers_js/__tests__/dss_export.test.js`; backend coverage in `tests/weppcloud/routes/test_rq_api_dss_export.py` using `tests/factories.singleton_factory` + `tests/factories.rq`. Execute `wctl run-npm lint`, `wctl run-npm test -- dss_export`, rebuild the bundle, and run the targeted pytest plus `wctl run-pytest tests --maxfail=1` (requires `node` for StatusStream) before handoff. Sync the domain note `docs/dev-notes/dss-export-controller-plan.md` with new payloads/events.

### Batch Runner controller reference
- DOM hooks: templates expose `data-action="batch-upload"`, `data-action="batch-validate"`, and `data-action="batch-run"` for the primary buttons plus `data-run-directive="<slug>"` on task checkboxes. Resource and validation panels rely on the existing `data-role="resource-*"` / `data-role="validation-*"` markers, while status/stacktrace/job info panels stay under `#batch_runner_form` so `controlBase` can drive telemetry. Keep new UI affordances under a `data-batch-*` namespace and wire them through `WCDom.delegate`.
- Events: `BatchRunner.getInstance().emitter = WCEvents.useEventMap([...])` surfaces `batch:upload:started|completed|failed`, `batch:template:validate-started|completed|failed`, `batch:run-directives:updated|update-failed`, `batch:run:started|failed|completed`, plus the inherited `controlBase` lifecycle events (`job:started`, `job:completed`, `job:error`). Subscribe to these events rather than reading internal state or private fields.
- Transport: uploads stream `FormData` to `/batch/_/<name>/upload-geojson`; template validation and directive updates post JSON to `/validate-template` and `/run-directives`; run submissions post JSON to `/rq/api/run-batch`. The Flask routes now call `parse_request_payload`, and `BatchRunner.update_run_directives` converts `"true"/"false"` style strings to native booleans before persisting state.
- Tests: front-end coverage in `controllers_js/__tests__/batch_runner.test.js`; backend coverage in `tests/weppcloud/test_batch_runner_endpoints.py` (upload/validation/directives) and `tests/weppcloud/routes/test_rq_api_batch_runner.py` (queue wiring). Run `wctl run-npm test -- batch_runner`, rebuild the bundle, and execute the targeted pytest suites when touching this controller. Keep `docs/dev-notes/batch-runner-controller-plan.md` updated with payload schemas, event contracts, and open questions.


## Testing & Tooling Notes
- Jest config lives in `static-src/jest.config.mjs` (jsdom + ESM). Execute via `wctl run-npm test`; the script sets `NODE_OPTIONS=--experimental-vm-modules` automatically.
- ESLint config lives in `.eslintrc.cjs`. Run `wctl run-npm lint` (add `-- --fix` for auto-fixes) and prefer `wctl run-npm check` before handoff.
- Add new suites under `controllers_js/__tests__/` and keep them self-contained (each suite should import the helper(s) it exercises).
- If the bundle grows new helpers, document both usage and ordering in `README.md` and extend test coverage to guard the public API.
- `__tests__/landuse.test.js`, `__tests__/soil.test.js`, and `__tests__/wepp.test.js` exercise helper-based controllers; mirror their setup when migrating additional controls away from jQuery (stub helpers, bootstrap DOM, assert on helper calls, and verify lifecycle events).

## Communication
- If a change affects other repos (e.g., static assets build), annotate the summary so downstream maintainers can align.
- When you discover missing specs or conflicting docs, update this playbook and `README.md` together to keep humans and agents synchronized.
- Capture new primitives or helper upgrades in `docs/dev-notes/controller_foundations.md` so future agents inherit the context automatically.
