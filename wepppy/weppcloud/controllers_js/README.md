# Controllers JS Architecture

> **See also:** [AGENTS.md](../../../AGENTS.md) for Front-End Development section and controller bundling overview.  
> Agent workflow specifics live in [controllers_js/AGENTS.md](./AGENTS.md).  
> **Controller Contract:** See [docs/ui-docs/controller-contract.md](../../../docs/ui-docs/controller-contract.md) for explicit requirements all controllers must follow.

This note explains how the controller JavaScript in `wepppy/weppcloud` is organized, how individual controller modules cooperate with the shared infrastructure, and what needs to happen when you extend the system.

## Layout and Bundling
- Authoring happens in `wepppy/weppcloud/controllers_js/*.js` (one file per controller plus shared helpers such as `dom.js`, `http.js`, `forms.js`, `events.js`, `control_base.js`, and `status_stream.js`).
- The browser still downloads a single bundle, `wepppy/weppcloud/static/js/controllers.js`. The bundle is rendered from `controllers_js/templates/controllers.js.j2`, which now loops over the discovered `.js` files automatically; simply dropping a new controller file into the directory is enough for it to be included.
- The `build_controllers_js.py` helper (same directory) renders the template with Jinja, stamps a build date, and writes the bundle just before Gunicorn starts. Core infrastructure files now load in this order to guarantee that controllers see every helper namespace:
  1. `dom.js`, `events.js`, `forms.js`, `http.js`
  2. `utils.js`, `modal.js`, `unitizer_client.js`, `status_stream.js`, `control_base.js`, `project.js`
  3. Remaining controllers alphabetically
- Controllers can assume that `window.WCDom`, `window.WCEvents`, `window.WCForms`, and `window.WCHttp` exist before their module executes.

## Dynamic Mod Loading
**⚠️ Critical for new mod controllers:** When mods are dynamically enabled via the Mods dialog, the controller's singleton instance may be created *before* the DOM elements exist. This causes null references that persist even after the HTML is inserted.

**Required patterns:**
1. **Re-query elements in `bootstrap()`**: Check if critical elements are null and re-query them
2. **Defensive element access**: Always verify elements exist before using them
3. **Test dynamic loading**: Don't just test initial page load—test enabling the mod via checkbox

**See:** [docs/ui-docs/controller-contract.md](../../../docs/ui-docs/controller-contract.md) for explicit contract requirements and [docs/dev-notes/dynamic-mod-loading-patterns.md](../../../docs/dev-notes/dynamic-mod-loading-patterns.md) for comprehensive patterns and alternatives.

**Quick template for new controllers:**
```javascript
controller.bootstrap = function bootstrap(context) {
    // Re-query critical elements if they weren't found during createInstance()
    if (!controller.form || !controller.form.element) {
        var formElement = dom.qs(SELECTORS.form);
        if (formElement) {
            controller.form = formElement;
            // Re-query child elements that depend on form
            controller.button = dom.qs(SELECTORS.button, formElement);
        }
    }
    
    // Now proceed with bootstrap logic
    // ...
};
```

## Vanilla Helper Modules
- **`dom.js` (`window.WCDom`)** — Query helpers (`qs`, `qsa`, `ensureElement`), class/visibility utilities (`show`, `hide`, `toggle`, `toggleClass`), delegated event wiring (`delegate`), and light ARIA helpers. Each function accepts either selector strings or actual nodes and fails fast with descriptive errors when misused.
- **`events.js` (`window.WCEvents`)** — Lightweight event emitter factory with `on/off/once/emit`, DOM bridge (`emitDom`), piping (`forward`), and `useEventMap` for opt-in event name validation during development.
- **`forms.js` (`window.WCForms`)** — Form serialization compatible with jQuery semantics (`serializeForm`, `serializeFields`, `formToJSON`), value hydration (`applyValues`), and CSRF discovery (`findCsrfToken`). Checkboxes become booleans for object/JSON formats and remain URL encoded for query strings.
- **`http.js` (`window.WCHttp`)** — Fetch wrapper that handles `site_prefix`, query params, timeout cancellation, CSRF propagation, and rich error reporting via `HttpError`. Convenience helpers `getJson`, `postJson`, and `postForm` encapsulate the common call patterns used across controllers. **All controller network requests must flow through `WCHttp` (or its helpers) so global interceptors, audit logging, and recorder tooling can observe traffic consistently.**
- **`recorder_interceptor.js`** — Wraps `WCHttp.request` to emit recorder events before/after each backend call. Controllers do not interact with it directly, but the file must load immediately after `http.js` so audit capture stays reliable.

Controllers should destructure what they need from the globals:

```javascript
const { qs, delegate, show, hide } = WCDom;
const { request, postForm, HttpError } = WCHttp;
const { serializeForm, applyValues } = WCForms;
const { createEmitter, forward } = WCEvents;
```

Bundled modules remain global so legacy controllers can incrementally migrate away from jQuery without build tooling changes.

## Singleton Controller Modules
- Each controller file exposes a global (for example `var Project = function () { … }();`). The module keeps a private `instance` and returns an object containing `getInstance`, so we effectively have singletons.
- The singleton pattern avoids repeated DOM wiring and ensures components like WebSocket connections are not duplicated. Callers must use `ControllerName.getInstance()` rather than constructing their own copy.
- Controllers are expected to initialize inside existing forms (usually via document ready hooks in the templates). They usually cache references to form elements (`that.form = $('#wepp_form')`), register AJAX handlers, and expose methods that other controllers can call.

### Bootstrap Contract (2025 refresh)
- Controllers now expose an idempotent `instance.bootstrap(context)` method. The context is a plain object built by the page bootstrapper (`run_page_bootstrap.js.j2`) and contains:
  - `run`, `user`, `mods`, `flags`, and `map` metadata for cross-controller coordination
  - `jobIds` (RQ names → job ids) and `data` (domain flags such as `hasChannels`, `hasRun`, `precipScalingMode`)
  - Optional `controllers[controllerName]` overrides for controller-specific hints (for example default color maps)
- The helper `bootstrap.js` publishes `window.WCControllerBootstrap` so pages can:
  - `setContext(context)` — cache the run context once per page load
  - `bootstrapMany(entries, context)` — resolve controller singletons and call `bootstrap`
  - `resolveJobId(context, key)` / `getControllerContext(context, name)` — utility lookups used by controllers for fallbacks
- Controllers should read only the slices of context they need, e.g. `const climateData = (context.data && context.data.climate) || {};`. Guard against missing keys; the contract intentionally stays flexible so templates can omit data on lightweight pages.
- Every controller continues to operate without `WCControllerBootstrap` (tests stub it out). Always fall back to `context.jobIds` or `context.controllers` data when helpers are absent.
- Page templates must no longer poke controller internals directly. Instead they build the context once, call `bootstrapMany`, and let the controllers wire their own events (job id assignment, report hydration, color map defaults, etc.).

### Project Controller Contract (2024 refresh)

### Climate Controller Reference (2024 helper migration)
- **DOM contract**: templates expose `data-climate-action` hooks on radios, checkboxes, selects, and buttons plus `data-climate-section` / `data-precip-section` wrappers for conditional panels. Hidden inputs tagged with `data-climate-field` mirror controller state (`climate_catalog_id`, `climate_mode`). Catalog metadata ships via `<script id="climate_catalog_data" type="application/json">` so the controller can hydrate offline datasets without extra requests.
- **Event surface**: `Climate.getInstance().events = WCEvents.useEventMap([...])` emits `climate:dataset:changed`, `climate:dataset:mode`, `climate:station:mode`, `climate:station:selected`, `climate:station:list:loading`, `climate:station:list:loaded`, `climate:build:started`, `climate:build:completed`, `climate:build:failed`, `climate:precip:mode`, `climate:upload:completed`, `climate:upload:failed`, and `climate:gridmet:updated`. Subscribe instead of scraping DOM so status dashboards and RRED tooling stay decoupled.
- **Transport**: all mutations travel through JSON payloads (`WCHttp.postJson`) or `FormData` uploads; the paired Flask routes now call `parse_request_payload` so either JSON bodies or legacy form submissions succeed. `Climate.parse_inputs` receives native ints/bools and persists the catalog selection, spatial mode, precipitation scaling, and single-storm fields.
- **Status + telemetry**: the controller attaches `StatusStream` to the climate panel, feeds `controlBase` for RQ job wiring, and fans out lifecycle events (`CLIMATE_*`) into the emitter so reports refresh once builds finish.
- **Testing**: coverage lives in `controllers_js/__tests__/climate.test.js` (jsdom) and `tests/weppcloud/routes/test_climate_bp.py` (pytest). Keep both suites green when changing payload schemas or UI wiring; add fixtures for new events/endpoints as they appear.

### Map Controller Reference (2025 helper migration)
- **DOM contract**: `map_pure.htm` exposes `data-map-action="go|find-topaz|find-wepp"` on toolbar buttons and keeps status hooks (`#mapstatus`, `#mouseelev`, `#drilldown`, `#sub_legend`, `#sbs_legend`) for helper-driven updates. The inspector tabset sits under `#setloc_form [data-tabset]`—maintain its `role`/ARIA attributes so the controller’s tab manager stays accessible when adding panels.
- **Event surface**: `MapController.getInstance().events = WCEvents.useEventMap([...])` emits `map:ready`, `map:center:requested`, `map:center:changed`, `map:search:requested`, `map:elevation:requested`, `map:elevation:loaded`, `map:elevation:error`, `map:drilldown:requested`, `map:drilldown:loaded`, `map:drilldown:error`, `map:layer:toggled`, `map:layer:refreshed`, and `map:layer:error`. Subscribe to these signals instead of scraping DOM for viewport, drilldown, or overlay state.
- **Transport**: elevation probes POST JSON to `/runs/<run>/<cfg>/elevationquery/`; drilldown summaries fetch HTML via `WCHttp.request`, and remote overlays (USGS gage, SNOTEL, `addGeoJsonOverlay`) refresh through `WCHttp.getJson`, inheriting `site_prefix` automatically.
- **Testing**: `controllers_js/__tests__/map.test.js` exercises tabset activation, delegated toolbar actions, event emission, elevation success/error, overlay refresh, and Leaflet integration using mocked helpers. Extend this suite whenever the map gains new events or touches additional endpoints.

### Subcatchment Delineation Controller (2025 helper migration)
- **DOM contract**: templates surface `data-subcatchment-action="build"` on the primary button, while radios/sliders now ship with `data-subcatchment-role="cmap-option"` / `"scale-range"` so `WCDom.delegate` owns all change events. Legend markup still lives in the map template, but `setSubLegend` abstracts the jQuery/vanilla mismatch in `MapController.sub_legend`.
- **Event surface**: `SubcatchmentDelineation.getInstance().events = WCEvents.useEventMap([...])` exposes `subcatchment:build:started`, `subcatchment:build:completed`, `subcatchment:build:error`, `subcatchment:map:mode`, and `subcatchment:legend:updated`. Legacy `triggerEvent` hooks remain so Channel and WEPP controllers keep responding to `BUILD_SUBCATCHMENTS_TASK_COMPLETED` and `WATERSHED_ABSTRACTION_TASK_COMPLETED`.
- **Transport**: `WCForms.serializeForm(form, { format: "json" })` feeds `WCHttp.postJson("rq/api/build_subcatchments_and_abstract_watershed", payload, { form })`. The Flask route now calls `parse_request_payload`, normalising booleans (`clip_hillslopes`, `walk_flowpaths`, `mofe_buffer`, `bieger2015_widths`) and floats before mutating the `Watershed` singleton and queueing RQ work.
- **Testing**: Jest coverage (`__tests__/subcatchment_delineation.test.js`) locks in build submission, delegated color-map toggles, and error emission; pytest coverage (`tests/weppcloud/routes/test_rq_api_subcatchments.py`) guards RedisPrep/queue integration and batch short-circuit behaviour. Run both alongside the standard `wctl run-npm test` / `wctl run-pytest` cadence.


- **Data hooks**: templates expose `data-project-field`, `data-project-toggle`, `data-project-action`, and `data-project-unitizer` attributes. The controller relies exclusively on `WCDom.delegate` to listen for updates, so avoid inline `on*` handlers when extending the UI.
- **Scoped events**: `Project.getInstance().events` is a `WCEvents.useEventMap` wrapper that emits `project:name:updated`, `project:name:update:failed`, `project:scenario:updated`, `project:scenario:update:failed`, `project:readonly:changed`, `project:readonly:update:failed`, `project:public:changed`, `project:public:update:failed`, `project:unitizer:sync:started`, `project:unitizer:preferences`, `project:unitizer:sync:completed`, and `project:unitizer:sync:failed`. Subscribe through the emitter instead of poking controller internals.
- **Command bar + globals**: the controller routes every status message through `controlBase` and `initializeCommandBar`. The legacy `window.setGlobalUnitizerPreference` helper now delegates to `Project.handleGlobalUnitPreference`, keeping command-bar shortcuts and third-party scripts working without bespoke DOM glue.
- **Backend payloads**: paired routes (`tasks/setname/`, `tasks/setscenario/`, `tasks/set_public`, `tasks/set_readonly`, `tasks/set_unit_preferences/`) all parse requests via `parse_request_payload`. Name/scenario inputs trim whitespace, toggles expect native booleans, and unit preferences accept JSON or form posts containing `{category_key: preferred_unit}`. NoDb setters (`Ron.name`, `Ron.scenario`, `Unitizer.set_preferences`) coerce native types so controllers can post JSON without adding `"on"`/`"off"` shims.

## ControlBase and Job Orchestration
- `control_base.js` provides the common behavior that every controller mixes in. Calling `controlBase()` returns an object with helper methods for:
  - Tracking RQ job state (`set_rq_job_id`, `fetch_job_status`, `render_job_status`).
  - Managing the command button UI (disabling while a job is active, restoring afterwards).
  - Writing stack traces and error messages to the standard output areas.
  - Polling for job status and stopping when work reaches a terminal state.
- `control_base.attach_status_stream` is the preferred way to consume the websocket status channel. It wires spinners, DOM events, and stacktrace enrichment automatically, and fabricates hidden panels when a template only exposes the legacy form shell.
- `StatusStream` (in `status_stream.js`) is the authoritative telemetry surface for both dashboards and controllers. It renders against `[data-status-panel]`/`[data-status-log]` markup, manages reconnection/backoff, emits `status:*` custom events, and hydrates stack traces through optional fetchers—replacing the legacy `WSClient` shim entirely.
- Together, these two components are the contract for any control that launches asynchronous work: provide the DOM IDs, call `set_rq_job_id`, and the infrastructure handles the rest.
- The Project controller applies the same contract when readonly toggles queue `set_run_readonly_rq`; the worker now pushes human-readable updates to `<runid>:command`, which the command bar consumes directly to surface messages such as `manifest.db creation finished` without extra wiring.

## Views and DOM Contract
- The HTML that controllers operate on lives under `wepppy/weppcloud/templates/controls/`. Each control has its own template (Pure variants such as `wepp_pure.htm`, `landuse_pure.htm`, etc.) and they extend the markup defined in `_pure_base.htm` (legacy `_base.htm` remains only for archived Bootstrap views).
- `_pure_base.htm` defines the canonical form structure: `#status`, `#info`, `#rq_job`, `#stacktrace`, `#preflight_status`, and other fields that the JS expects. As long as new controls keep those IDs, `controlBase` can update the UI without per-controller duplication. Legacy `_base.htm` persists only for archived Bootstrap-era controls.
- Higher-level pages (for example `templates/controls/poweruser_panel.htm`) compose multiple control templates, which in turn rely on the singleton controllers to bind behavior once the bundle loads.

## Build Script and Startup Integration
- `wepppy/weppcloud/controllers_js/build_controllers_js.py` is the entry point for producing the bundle. It configures Jinja to treat the controller files as literal text (so existing `{{ }}` tokens meant for client-side templating survive), renders `controllers.js.j2`, and writes the output to `static/js/controllers.js`.
- Production images call the builder during `docker build` (see `docker/Dockerfile`), so the resulting image always contains a current bundle even before the container starts.
- Development containers (Compose using `Dockerfile.dev`) run `docker/weppcloud-entrypoint.sh` before Gunicorn boots. The entrypoint rebuilds the bundle on the live filesystem—handy when the source tree is bind-mounted in dev—and aborts the startup if rendering fails.
- Production deployments can optionally execute the entrypoint (or `build_controllers_js.py`) as a pre-start hook, but it's no longer invoked automatically once the image is built.
- Bare-metal or Kubernetes deployments can execute the same script as a pre-start hook; the only requirement is that the Python environment in use has Jinja and the rest of the stack already installed.
- You can run the same command manually inside the virtualenv: `python wepppy/weppcloud/controllers_js/build_controllers_js.py`. The generated file header includes a UTC build timestamp so you can confirm the rebuild in the browser.

## Working With Controllers
- When adding a controller, create a new `controllers_js/<name>.js` and add the matching template under `templates/controls/`. The bundler will auto-include the new module the next time it runs. Reuse the `_base.htm` structure or extend it if you need additional UI elements.
- Keep controller methods focused on DOM wiring and async orchestration. Shared logic should live in helper modules under `controllers_js/` so that other controllers can `include` them via the bundle template.
- Because the bundle is rebuilt when the entrypoint runs (container start or explicit call), restart the container or rerun the script whenever you edit controller sources. `.vscode/settings.json` is configured to ignore the built
`controllers.js` file.
- `control_base.js` now uses `WCHttp`/`WCDom` internally. Controllers may continue supplying legacy jQuery objects, but new code should pass native elements (the base normalises both).

## Project Controller Modernization
- `project.js` now consumes `WCDom`, `WCHttp`, and `WCForms` exclusively—jQuery hooks have been replaced with delegated listeners that target `data-project-field`, `data-project-toggle`, and `data-project-action` attributes in the header and power-user templates. Update templates with those attributes instead of inline `on*` handlers when expanding the control.
- Command bar feedback and unitizer integration are still exposed through `Project.getInstance()`, but outbound network calls flow through `WCHttp.postForm`/`postJson`, enabling native Promise semantics and shared error handling.
- Regression coverage lives in `controllers_js/__tests__/project.test.js`. Run it via `wctl run-npm test` (wrapper for `npm --prefix wepppy/weppcloud/static-src test`). The suite verifies name/scenario saves, debounce behaviour, and failure handling so future refactors can rely on automated guardrails.
- Style checks: `wctl run-npm lint` lints `controllers_js/**/*.js`; `wctl run-npm check` runs lint followed by Jest in one step.

## WEPP Controller Modernization
- `wepp.js` now uses the helper namespaces exclusively. Templates advertise `data-wepp-action` and `data-wepp-routine` attributes so the controller wires event listeners without inline handlers, and network calls go through `WCHttp`.
- File uploads (user cover transforms) move through `FormData` bodies handled by `WCHttp.request`, matching the conventions used elsewhere in the bundle.
- Jest coverage in `controllers_js/__tests__/wepp.test.js` exercises run submission, advanced option toggles, phosphorus defaults, and summary fetches. Execute it with `wctl run-npm test`.

## Ash Controller Modernization (2024 helper-first baseline)
- `ash.js` eliminates jQuery entirely—DOM wiring travels through `WCDom.delegate` listening to `data-ash-*` hooks (`data-ash-depth-mode`, `data-ash-action`, `data-ash-upload`). Template JSON (`#ash-model-params-data`) hydrates calibration defaults without global scripts.
- The controller registers `ash.events = WCEvents.useEventMap([...])` and emits lifecycle signals: `ash:mode:changed`, `ash:model:changed`, `ash:transport:mode`, `ash:run:started`, `ash:run:completed`, and `ash:model:values:capture`. Downstream consumers should subscribe to these instead of poking private properties.
- Long-running work posts `FormData` via `WCHttp.request` so raster uploads survive, while lightweight toggles (`set_ash_wind_transport`) send JSON through `WCHttp.postJson`. The paired Flask route (`/rq/api/run_ash`) now uses `parse_request_payload` and `Ash.parse_inputs` accepts native booleans/ints/floats.
- Jest coverage lives in `controllers_js/__tests__/ash.test.js` (depth mode toggles, cache restores, run submission, error handling). Backend parsing is exercised by `tests/weppcloud/routes/test_rq_api_ash.py`. Run these alongside linting when editing the controller:
  ```bash
  wctl run-npm lint
  wctl run-npm test -- ash
  python wepppy/weppcloud/controllers_js/build_controllers_js.py
  wctl run-pytest tests/weppcloud/routes/test_rq_api_ash.py
  ```

Keep this document updated when the bundling flow or controller contract changes.

## Migration Patterns
- Replace jQuery DOM calls with `WCDom` helpers (`qs`, `qsa`, `delegate`, `show`, `hide`, `toggleClass`). This keeps selectors scoped, plays nicely with document fragments, and matches our progressive enhancement strategy.
- Swap `$.ajax`/`$.get` with `WCHttp.request` or the convenience wrappers (`getJson`, `postJson`, `postForm`) so CSRF, timeouts, and Accept headers stay consistent across controllers.
- Use `WCForms.serializeForm(..., { format: 'json' })` when controllers need native booleans/arrays and `FormData` only when file uploads are involved.
- When controllers still rely on `controlBase` UI adapters, follow the pattern introduced in `landuse.js` and `soil.js`—wrap raw DOM nodes in lightweight adapters that expose `show/hide/text/html` to preserve legacy expectations without reintroducing jQuery.
- Audit templates for inline `$()` usage during migrations; move bootstrap logic to dedicated modules so controllers can initialise via `DOMContentLoaded` or direct module execution.

## Testing & Tooling Notes
- Run `wctl run-npm lint` before committing controller changes; ESLint is configured to flag remaining jQuery dependencies.
- Execute `wctl run-npm test` (or `wctl run-npm check` for lint + test) to keep the jsdom suites green. Tests live under `wepppy/weppcloud/controllers_js/__tests__/`.
- The Landuse migration added `__tests__/landuse.test.js` covering delegated report events, FormData submissions, and helper-driven error handling. Treat it as the template for future controller suites—each test boots the controller with stubbed helpers and asserts against helper calls rather than DOM snapshots.
- The WEPP migration introduced a scoped `WCEvents` emitter (`wepp:run:*`, `wepp:report:loaded`) and expanded `__tests__/wepp.test.js` to exercise lifecycle signals, delegated uploads, and error propagation. Use this suite when adding new run-control behaviours or subscribing to WEPP events from neighbouring modules.
- The Soils migration added `__tests__/soil.test.js`, which validates mode toggles, ksflag updates, and disturbed payload routing via the helper stack; reuse its setup when migrating remaining run controls.
- Rebuild the bundle with `python wepppy/weppcloud/controllers_js/build_controllers_js.py` after large refactors to catch syntax errors outside of Jest.

### Landuse Modify Controller Reference (2025 helper migration)
- **DOM contract**: `modify_landuse.htm` now exposes `data-landuse-modify-action="toggle-selection|submit"` and `data-landuse-modify-field="topaz-ids|landuse-code"`. Selection mode wiring runs through `WCDom.delegate`, and map interactions continue to depend on `MapController`/Leaflet—use the existing hooks rather than reintroducing inline handlers when the UI grows.
- **Event surface**: `LanduseModify.getInstance().events = WCEvents.useEventMap(['landuse:modify:started', 'landuse:modify:completed', 'landuse:modify:error', 'landuse:selection:changed', 'job:started', 'job:completed', 'job:error'])`. Consumers should subscribe to these signals instead of scraping textarea values or controller internals.
- **Transport**: modification requests post JSON (`{ topaz_ids: [...], landuse: '<code>' }`) to `tasks/modify_landuse/`. Rectangle selections post JSON extents to `tasks/sub_intersection/`, and the backend normalises payloads via `_coerce_topaz_ids`/`_coerce_landuse_code` before calling `Landuse.modify`. Successful runs refresh dependent controllers (`Landuse`, `SubcatchmentDelineation`) via the emitter/`controlBase` lifecycle events.
- **Testing**: Jest coverage lives in `controllers_js/__tests__/landuse_modify.test.js` (selection toggles, event emission, error handling). Backend expectations sit in `tests/weppcloud/routes/test_landuse_bp.py`; include both in your `wctl run-npm test` and targeted `wctl run-pytest` runs whenever payload contracts change.

### Omni Controller Reference (2024 helper migration)
- **DOM contract**: templates expose `data-omni-action` hooks for primary buttons (`add-scenario`, `run-scenarios`, `delete-selected`, `confirm-delete`) plus delegated selectors tagged with `data-omni-role="scenario-select"` and per-row checkboxes marked `data-omni-role="scenario-select-toggle"` with controls hosted under `data-omni-scenario-controls`. The controller renders scenario rows at runtime—no inline scripts remain—so keep markup minimal and document any new `data-omni-*` attributes whenever scenarios or controls expand.
- **Event surface**: `Omni.getInstance().events = WCEvents.useEventMap([...])` emits `omni:scenario:added`, `omni:scenario:removed`, `omni:scenario:updated`, `omni:scenarios:loaded`, `omni:run:started`, `omni:run:completed`, and `omni:run:error`. Subscribe to these instead of scraping DOM state when other controls (unitizer, dashboards) need to react to Omni runs.
- **Transport**: scenario submissions build a `FormData` payload containing a JSON `scenarios` list plus any SBS uploads. The paired Flask endpoints (`/rq/api/run_omni`, `/rq/api/run_omni_contrasts`) now call `parse_request_payload` so JSON and multipart payloads share a single parser; SBS files stage under `omni/_limbo/{idx}` before Omni clones scenarios.
- **Validation**: SBS uploads are screened client-side (extension + 100 MB limit) before requests fire; backend helpers mirror those guards via `save_run_file`. Errors drive `omni:run:error` and populate the legacy status/stacktrace panels through `controlBase`.
- **Testing**: Jest coverage lives in `controllers_js/__tests__/omni.test.js` (FormData serialization, scenario hydration, validation). Backend regression tests reside in `tests/weppcloud/routes/test_rq_api_omni.py` covering JSON payloads, upload handling, and Redis queue wiring. Run them alongside `wctl run-npm test -- omni` and `wctl run-pytest tests/weppcloud/routes/test_rq_api_omni.py`.

### Outlet Controller Reference (2025 helper migration)
- **DOM contract**: the template exposes `data-outlet-root` to scope delegated listeners, `data-outlet-mode-section` for cursor/entry panels, `data-outlet-entry-field` on the coordinate input, and `data-outlet-action="cursor-toggle|entry-submit"` on command buttons. Panels start hidden via the `hidden` attribute; visibility toggles through `WCDom.toggle` so avoid reinstating inline CSS.
- **Event surface**: `Outlet.getInstance().events = WCEvents.useEventMap([...])` emits `outlet:mode:change`, `outlet:cursor:toggle`, `outlet:set:start`, `outlet:set:queued`, `outlet:set:success`, `outlet:set:error`, and `outlet:display:refresh`. These sit alongside `controlBase` lifecycle events (`job:started`, `job:completed`, `job:error`) for orchestration telemetry.
- **Transport**: submissions hit `rq/api/set_outlet` with JSON `{ latitude, longitude }` or a `{ coordinates: { lat, lng } }` envelope. The Flask route now consumes payloads via `parse_request_payload`, normalises floats, clears `RedisPrep` timestamps, and enqueues `set_outlet_rq`.
- **Testing**: Jest coverage in `controllers_js/__tests__/outlet.test.js` exercises mode toggling, delegated actions, job submission, and completion events. Backend regression tests live in `tests/weppcloud/routes/test_rq_api_outlet.py`. Run `wctl run-npm test -- outlet` (or the full suite) plus `wctl run-pytest tests/weppcloud/routes/test_rq_api_outlet.py`.

### BAER Controller Reference (2025 helper migration)
- **DOM contract**: radio groups, buttons, and fire-date actions publish hooks via `data-baer-*`. Radios expose `data-baer-mode` so `Baer` can drive `WCDom.show/hide` on `#sbs_mode{0,1}_controls`. Command buttons use `data-baer-action="upload|remove|build-uniform|set-firedate|modify-classes|modify-color-map"` with optional `data-baer-uniform` (severity) and `data-baer-target` (selector) metadata. The legend container (`#sbs_legend`) hosts a generated slider (`#baer-opacity-slider`) that emits `input/change` events back through the controller.
- **Event surface**: `Baer.getInstance().events = WCEvents.useEventMap([...])` emits `baer:mode:changed`, `baer:upload:started`, `baer:upload:completed`, `baer:upload:error`, `baer:remove:started`, `baer:remove:completed`, `baer:remove:error`, `baer:uniform:started`, `baer:uniform:completed`, `baer:uniform:error`, `baer:firedate:updated`, `baer:firedate:error`, `baer:classes:updated`, `baer:classes:error`, `baer:color-map:updated`, `baer:color-map:error`, `baer:map:shown`, `baer:map:error`, and `baer:map:opacity`. These pair with `controlBase` lifecycle notifications (`job:started`, `job:completed`, `job:error`) so RQ dashboards and telemetry stay in sync.
- **Transport**: uploads send a `FormData` payload to `tasks/upload_sbs/`; removals hit `tasks/remove_sbs`; uniform rasters call `tasks/build_uniform_sbs/<value>`. JSON mutations (`tasks/set_firedate/`, `tasks/modify_burn_class`, `tasks/modify_color_map`) now flow through `parse_request_payload`, which delivers trimmed strings plus native integers for class breaks before reaching the NoDb mods. Map previews read from `query/baer_wgs_map/` and refresh legends via `resources/legends/sbs/` without jQuery.
- **Testing**: Jest coverage (`controllers_js/__tests__/baer.test.js`) validates delegated events, HTTP dispatch, slider opacity updates, and error handling. Backend parsing and response semantics live in `tests/weppcloud/routes/test_disturbed_bp.py`. Run `wctl run-npm test -- baer`, `python wepppy/weppcloud/controllers_js/build_controllers_js.py`, and `wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py` to exercise the stack.

### Disturbed Controller Reference (2025 helper migration)
- **DOM contract**: `controls/disturbed_sbs_pure.htm` shares the BAER shell but now leans entirely on helper hooks—`data-sbs-action`, `data-sbs-uniform`, and `[data-disturbed-action]` drive uploads, removals, uniform rasters, fire-date updates, and power-user lookup actions. Hint nodes (`#hint_upload_sbs`, `#hint_remove_sbs`, `#hint_low_sbs`, `#hint_moderate_sbs`, `#hint_high_sbs`) replace modal alerts for inline feedback.
- **Event surface**: `Disturbed.getInstance().events = WCEvents.useEventMap(['disturbed:mode:changed', 'disturbed:sbs:state', 'disturbed:lookup:reset', 'disturbed:lookup:extended', 'disturbed:lookup:error', 'disturbed:upload:started', 'disturbed:upload:completed', 'disturbed:upload:error', 'disturbed:remove:started', 'disturbed:remove:completed', 'disturbed:remove:error', 'disturbed:uniform:started', 'disturbed:uniform:completed', 'disturbed:uniform:error', 'disturbed:firedate:updated', 'disturbed:firedate:error'])`. The controller also dispatches `CustomEvent('disturbed:has_sbs_changed')` for legacy listeners and propagates `controlBase` lifecycle events with task identifiers such as `disturbed:upload` and `disturbed:lookup:reset`.
- **Transport**: lookup reset/extend tasks now `POST` empty payloads; uniform rasters post JSON to `tasks/build_uniform_sbs` (`{"value": int}`) while retaining the legacy `<value>` path; fire dates post JSON to `tasks/set_firedate/`; uploads remain `FormData`; `has_sbs` polls `api/disturbed/has_sbs/`. Every route runs through `parse_request_payload`, delivering native booleans/ints to the NoDb layer.
- **Testing**: Jest coverage (`controllers_js/__tests__/disturbed.test.js`) verifies delegated wiring, event emission, cache refresh, and HTTP payload shape. Backend regression lives in `tests/weppcloud/routes/test_disturbed_bp.py`, now powered by `tests/factories.singleton_factory` and `tests/factories.rq_environment`. Execute `wctl run-npm test -- disturbed`, rebuild the bundle, `wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py`, and `wctl run-pytest tests --maxfail=1` when shared infrastructure shifts.

### Debris Flow Controller Reference (2025 helper migration)
- **DOM contract**: `debris_flow.htm` and `debris_flow_pure.htm` expose `data-debris-action="run"` on the command button inside `#debris_flow_form`. Templates no longer ship inline `onclick` handlers—`WCDom.delegate` now owns wiring, so future UI tweaks should add new `data-debris-*` hooks instead of global listeners.
- **Event surface**: `DebrisFlow.getInstance().events = WCEvents.useEventMap(['debris:run:started', 'debris:run:completed', 'debris:run:error'])`. Pair these with `controlBase` lifecycle broadcasts (`job:started|completed|error`) and the existing `DEBRIS_FLOW_RUN_TASK_COMPLETED` WebSocket trigger to keep telemetry dashboards and neighbouring controllers in sync.
- **Transport**: runs post JSON via `WCHttp.postJson("rq/api/run_debris_flow", {})`. The Flask route now relies on `parse_request_payload`, coercing optional `clay_pct` and `liquid_limit` floats plus an optional `datasource` string before enqueuing `run_debris_flow_rq(runid, payload=…)`. The RQ task accepts those native values and forwards them to `DebrisFlow.run_debris_flow(cc=…, ll=…, req_datasource=…)`, eliminating the last `"on"` checks.
- **Testing**: Jest coverage lives in `controllers_js/__tests__/debris_flow.test.js` (delegated wiring, lifecycle events, error handling). Backend assertions sit in `tests/weppcloud/routes/test_rq_api_debris_flow.py` (route parsing and queue wiring) and `tests/rq/test_project_rq_debris_flow.py` (task payload handling). Run them alongside `wctl run-npm test -- debris_flow`, `python wepppy/weppcloud/controllers_js/build_controllers_js.py`, and the targeted pytest commands when you revisit this control.

### DSS Export Controller Reference (2025 helper migration)
- **DOM contract**: Legacy and Pure templates expose `data-action="dss-export-mode"` on the mode radios, `data-action="dss-export-run"` on the command button, and reuse `#dss_export_mode1_controls` / `#dss_export_mode2_controls` wrappers so `WCDom.show/hide` can toggle between channel lists and order filters. Status, stacktrace, info, and hint panels still live inside `#dss_export_form` for `controlBase` integration, and the run TOC entry is shown/hidden through the controller rather than inline jQuery.
- **Event surface**: `DssExport.getInstance().events = WCEvents.useEventMap(['dss:mode:changed', 'dss:export:started', 'dss:export:completed', 'dss:export:error', 'job:started', 'job:completed', 'job:error'])`. Domain listeners consume the `dss:*` events (mode switches, queue lifecycle, errors) while `controlBase` continues to raise `job:*` for dashboards and status widgets.
- **Transport**: submissions post JSON via `WCHttp.postJson("rq/api/post_dss_export_rq", { dss_export_mode, dss_export_channel_ids, dss_export_exclude_orders })`. The Flask route now relies solely on `parse_request_payload`, coalescing JSON or legacy form posts into native ints/booleans, deriving channel IDs from `Watershed.chns_summary` when mode 2 is requested, and persisting via NoDb property setters (`wepp.dss_export_mode`, `wepp.dss_excluded_channel_orders`, `wepp.dss_export_channel_ids`).
- **Testing**: Jest coverage (`controllers_js/__tests__/dss_export.test.js`) exercises delegated wiring, payload assembly, WebSocket completion handling, and error paths. Backend assertions live in `tests/weppcloud/routes/test_rq_api_dss_export.py` using `tests/factories.singleton_factory` + `tests/factories.rq` to validate queue wiring and NoDb updates. Run `wctl run-npm test -- dss_export`, rebuild the bundle, and execute `wctl run-pytest tests/weppcloud/routes/test_rq_api_dss_export.py` (plus the full suite when shared helpers change).

### Observed Controller Reference (2025 helper migration)
- **DOM contract**: The legacy and Pure templates expose a shared `#observed_form` shell with status (`#status`), stacktrace (`#stacktrace`), info (`#info`), and RQ job (`#rq_job`) nodes so `controlBase` can drive telemetry. The run button publishes delegated clicks via `data-action="observed-run"`, while the textarea keeps its canonical id/name (`observed_text`) for `WCForms.serializeForm`. Visibility toggles occur on the nearest `.controller-section`, so the controller can hide or show the control without inline jQuery.
- **Event surface**: `Observed.getInstance().events = WCEvents.useEventMap(['observed:data:loaded', 'observed:model:fit', 'observed:error', 'job:started', 'job:completed', 'job:error'])`. `observed:data:loaded` fires whenever the controller shows or hides the control (including the climate post-run probe), `observed:model:fit` emits `status: 'started' | 'completed'`, and `observed:error` surfaces both HTTP failures and backend validation issues. `controlBase` still raises the standard `job:*` lifecycle events for dashboards.
- **Transport**: Submissions call `WCHttp.postJson("tasks/run_model_fit/", { data })`, where `data` is captured from the textarea via `WCForms.serializeForm(form, { format: "json" })`. `onWeppRunCompleted` checks `query/climate_has_observed/` through `WCHttp.getJson`, toggling panel visibility based on the boolean response. Flask routes now parse bodies with `parse_request_payload(trim_strings=False)`, accept either `data` or `observed_text`, and return 400s when no payload is supplied.
- **Testing**: Jest coverage lives in `controllers_js/__tests__/observed.test.js` (delegated run wiring, telemetry, error propagation, visibility updates). Backend assertions live in `tests/weppcloud/routes/test_observed_bp.py`, which uses `tests.factories.singleton_factory` to stub the NoDb controller. Run `wctl run-npm test -- observed`, rebuild the bundle (`python wepppy/weppcloud/controllers_js/build_controllers_js.py`), and execute `wctl run-pytest tests/weppcloud/routes/test_observed_bp.py` when iterating on the observed domain.

### Rangeland Cover Controller Reference (2025 helper migration)
- **DOM contract**: `rangeland_cover.htm` and the pure template now expose helper-friendly hooks. The shared `#rangeland_cover_form` shell still houses status (`#status`), stacktrace (`#stacktrace`), info (`#info`), hint (`#hint_build_rangeland_cover`), and RQ job (`#rq_job`) nodes so `controlBase` can manage telemetry. Mode radios carry `data-rangeland-role="mode"` / `data-rangeland-mode="<value>"`, the RAP year container is tagged with `data-rangeland-rap-section`, the year input uses `data-rangeland-input="rap-year"`, and the build button exposes `data-rangeland-action="build"`. These hooks let `WCDom.delegate` own all interactions (including readonly checks) without inline handlers.
- **Event surface**: `RangelandCover.getInstance().events = WCEvents.useEventMap(['rangeland:config:loaded', 'rangeland:mode:changed', 'rangeland:rap-year:changed', 'rangeland:run:started', 'rangeland:run:completed', 'rangeland:run:failed', 'rangeland:report:loaded', 'rangeland:report:failed'])`. The controller still dispatches the legacy `RANGELAND_COVER_BUILD_TASK_COMPLETED` DOM event for Subcatchment listeners but now mirrors it with helper-first `rangeland:run:*` emissions so dashboards and neighbouring modules subscribe without scraping state.
- **Transport**: Mode updates post JSON to `tasks/set_rangeland_cover_mode/` via `WCHttp.postJson`, sending `{ mode, rap_year }`. Builds post JSON to `tasks/build_rangeland_cover/` with `{ rap_year, defaults: { bunchgrass, forbs, sodgrass, shrub, basal, rock, litter, cryptogams } }`. The paired Flask routes rely on `parse_request_payload` for JSON/legacy form inputs, coerce ints/floats before assigning to the NoDb controller, and continue returning `success_factory()` payloads so legacy consumers stay compatible.
- **Testing**: Jest coverage in `controllers_js/__tests__/rangeland_cover.test.js` verifies helper bootstrap, delegated handlers, lifecycle events, Subcatchment integration, and error handling. Backend assertions live in `tests/weppcloud/routes/test_rangeland_cover_bp.py`, which uses `tests.factories.singleton_factory` to validate payload coercion and form fallbacks. Run `wctl run-npm test -- rangeland_cover`, rebuild the bundle (`python wepppy/weppcloud/controllers_js/build_controllers_js.py`), and execute `wctl run-pytest tests/weppcloud/routes/test_rangeland_cover_bp.py` when iterating on this control.

### Rangeland Cover Modify Controller Reference (2025 helper migration)
- **DOM contract**: `modify_rangeland_cover.htm` now exposes helper-first hooks instead of inline jQuery IDs. The shared `#modify_rangeland_cover_form` shell keeps the status (`#status`), stacktrace (`#stacktrace`), and RQ job (`#rq_job`) nodes for `controlBase`, while the selection toggle advertises `data-rcm-action="toggle-selection"`, the submit button uses `data-rcm-action="submit"`, the Topaz textarea carries `data-rcm-field="topaz-ids"`, and each cover input maps to `data-rcm-field="<measure>"` (`bunchgrass`, `forbs`, `sodgrass`, `shrub`, `basal`, `rock`, `litter`, `cryptogams`). Map mode relies on the same checkbox to attach Leaflet listeners, with `WCDom.delegate` wiring every interaction.
- **Event surface**: `RangelandCoverModify.getInstance().events = WCEvents.useEventMap(['rangeland:modify:loaded', 'rangeland:modify:selection:changed', 'rangeland:modify:run:started', 'rangeland:modify:run:completed', 'rangeland:modify:run:error', 'rangeland:modify:error', 'job:started', 'job:progress', 'job:completed', 'job:error', 'RANGELAND_COVER_MODIFY_TASK_COMPLETED'])`. Subscribe to the helper-first events for selection, summary hydration, and run lifecycle updates; the legacy DOM event remains for historical Subcatchment wiring. `controlBase.triggerEvent` still relays the `job:*` lifecycle so dashboards stay in sync.
- **Transport**: Selection summaries post JSON to `query/rangeland_cover/current_cover_summary/` (returning the canonical cover mix). Box selections stream extents to `tasks/sub_intersection/`. Submit calls `tasks/modify_rangeland_cover/` with `{ topaz_ids, covers }`, where the controller already coerces covers to native floats and deduplicates Topaz IDs. The Flask route now uses `parse_request_payload`, normalises ID arrays, validates that every cover falls within `0–100`, and returns `exception_factory` payloads when validation fails or an unknown Topaz ID is supplied.
- **Telemetry & refresh**: Job lifecycle flows through `controlBase` (`job:*` events, RQ badge updates). Successful runs still emit `RANGELAND_COVER_MODIFY_TASK_COMPLETED` and immediately refresh `SubcatchmentDelineation` (color map + raster overlay) and `RangelandCover.report()` so downstream views stay current. Summary/box-select errors push stacktraces via `controlBase.pushResponseStacktrace` while emitting `rangeland:modify:error` for observers.
- **Testing**: Jest coverage lives in `controllers_js/__tests__/rangeland_cover_modify.test.js`, exercising summary hydration, payload composition, event emission, and validation failures. Backend assertions sit in `tests/weppcloud/routes/test_rangeland_cover_bp.py`, which now validates Topaz ID normalisation, cover range checks, and legacy form fallbacks for the modify route. Run `wctl run-npm test -- rangeland_cover_modify`, rebuild the bundle, and execute `wctl run-pytest tests/weppcloud/routes/test_rangeland_cover_bp.py` when iterating on this controller, updating `docs/work-packages/20251023_controller_modernization/notes/archived-plans/rangeland-cover-modify-controller-plan.md` with any contract changes.

### Treatments Controller Reference (2025 helper migration)
- **DOM contract**: `treatments_pure.htm` tags `#treatments_form` with `data-treatments-form`, scopes mode radios via `data-treatments-role="mode"` + `data-treatments-mode`, and wraps selection/upload stacks with `data-treatments-panel="selection"` / `"upload"`. The select, file input, status hint, and RQ job badge expose `data-treatments-role` hooks so `WCDom.delegate` owns interactions without inline handlers while `controlBase` keeps telemetry wired through the form shell.
- **Event surface**: `Treatments.getInstance().events = WCEvents.useEventMap(['treatments:list:loaded', 'treatments:scenario:updated', 'treatments:mode:changed', 'treatments:mode:error', 'treatments:selection:changed', 'treatments:run:started', 'treatments:run:submitted', 'treatments:run:error', 'treatments:job:started', 'treatments:job:completed', 'treatments:job:failed', 'treatments:status:updated'])`. Consumers should subscribe to these helper-first signals instead of scraping DOM text or reading private controller fields.
- **Transport**: Mode changes post JSON to `tasks/set_treatments_mode/` with `{ mode, single_selection }`. The Flask route now uses `parse_request_payload`, accepts JSON or legacy form posts, coerces `mode` to the `TreatmentsMode` enum, and continues returning `success_factory()` for compatibility. Build submissions still stream `FormData` (plus optional rasters) to `rq/api/build_treatments`, with the controller emitting run lifecycle events and forwarding StatusStream job telemetry.
- **Telemetry**: The controller attaches to the `treatments` channel via `controlBase.attach_status_stream` (including stacktrace enrichment). `appendStatus` keeps status, hint, and RQ job nodes synchronized while emitting `treatments:status:updated` payloads for dashboards and observers.
- **Testing**: Jest coverage lives in `controllers_js/__tests__/treatments.test.js` (helper bootstrap, delegated mode/selection updates, job orchestration, and error handling). Backend assertions are in `tests/weppcloud/routes/test_treatments_bp.py`, which relies on `tests.factories.singleton_factory` to confirm enum coercion and legacy form fallbacks. Run `wctl run-npm lint`, `wctl run-npm test -- treatments`, rebuild the bundle (`python wepppy/weppcloud/controllers_js/build_controllers_js.py`), and execute `wctl run-pytest tests/weppcloud/routes/test_treatments_bp.py` before handoff, updating `docs/work-packages/20251023_controller_modernization/notes/archived-plans/treatments-controller-plan.md` with any contract changes.

### RHEM Controller Reference (2025 helper migration)
- **DOM contract**: `rhem.htm` and `rhem_pure.htm` expose the run trigger through `data-rhem-action="run"`, keep status, stacktrace, hint, and RQ job nodes scoped to `#rhem_form`, and render report content inside `#rhem-results`. Optional stage toggles (`clean`, `prep`, `run`) use native checkbox inputs so `WCForms.serializeForm(form, { format: "object" })` yields real booleans for the backend.
- **Event surface**: `Rhem.getInstance().events = WCEvents.useEventMap(['rhem:config:loaded', 'rhem:run:started', 'rhem:run:queued', 'rhem:run:completed', 'rhem:run:failed', 'rhem:status:updated'])`, while the inherited `job:*` lifecycle events continue to flow from `controlBase`. Subscribe to these helper-first signals instead of scraping DOM text or relying on legacy WebSocket messages.
- **Transport**: Job submissions call `WCHttp.postJson("rq/api/run_rhem_rq", WCForms.serializeForm(form, { format: "object" }))`. The Flask route normalises JSON or form posts via `parse_request_payload`, coercing the `clean`, `prep`, and `run` flags before enqueuing `run_rhem_rq(payload=…)`. The RQ task honours those booleans, skipping `clean()`, `prep_hillslopes()`, or `run_hillslopes()` when a flag is `False` while still publishing StatusStream telemetry.
- **Telemetry**: `controlBase.attach_status_stream` streams logs and stack traces on the `rhem` channel. `rhem.appendStatus` keeps DOM panels updated and emits `rhem:status:updated` payloads so dashboards stay in sync with queue progress.
- **Testing**: Jest coverage in `controllers_js/__tests__/rhem.test.js` exercises helper bootstrap, delegated interactions, lifecycle events, and error handling. Backend assertions live in `tests/weppcloud/routes/test_rhem_bp.py` (report/query endpoints) and `tests/weppcloud/routes/test_rq_api_rhem.py` (queue wiring + payload coercion) using the shared singleton and RQ factories. Run `wctl run-npm lint`, `wctl run-npm test -- rhem`, rebuild the bundle (`python wepppy/weppcloud/controllers_js/build_controllers_js.py`), and execute `wctl run-pytest tests/weppcloud/routes/test_rhem_bp.py` / `wctl run-pytest tests/weppcloud/routes/test_rq_api_rhem.py` before handoff, recording any contract changes in `docs/work-packages/20251023_controller_modernization/notes/archived-plans/rhem-controller-plan.md`.

### Team Controller Reference (2026 helper migration)
- **DOM contract**: `team.htm` / `team_pure.htm` expose helper hooks (`data-team-action="invite"`, `data-team-action="remove"`, `data-team-field="email"`) and keep status, stacktrace, info, and hint nodes inside `#team_form` so `controlBase` and StatusStream continue to drive telemetry. Removal buttons rendered in `reports/users.htm` inherit `disable-readonly`, letting readonly projects hide destructive affordances without additional controller logic.
- **Events**: `Team.getInstance().events = WCEvents.useEventMap(['team:list:loading', 'team:list:loaded', 'team:list:failed', 'team:invite:started', 'team:invite:sent', 'team:invite:failed', 'team:member:remove:started', 'team:member:removed', 'team:member:remove:failed', 'team:status:updated'])`. Legacy DOM events (`TEAM_ADDUSER_TASK_COMPLETED`, `TEAM_REMOVEUSER_TASK_COMPLETED`) and `job:*` triggers still bubble via `controlBase.triggerEvent` for backward compatibility.
- **Transport**: Invites post JSON to `tasks/adduser/` with `{ email }` (legacy `adduser-email` form payloads remain accepted). Removals post `{ user_id }` to `tasks/removeuser/`. The project blueprint normalises inputs with `parse_request_payload`, consults `user_datastore.find_user`, handles duplicate membership idempotently (`Content.already_member` / `Content.already_removed`), and preserves historical logging/exception semantics through `success_factory` / `error_factory`.
- **Testing**: Jest coverage in `controllers_js/__tests__/team.test.js` exercises initial hydration, invite/remove flows, event emission, and error handling. Backend assertions live in `tests/weppcloud/routes/test_team_bp.py`, which stubs the datastore/query layers to validate payload coercion and messaging. Run `wctl run-npm lint`, `wctl run-npm test -- team`, rebuild the bundle, and execute `wctl run-pytest tests/weppcloud/routes/test_team_bp.py` when iterating on this domain.
- **Docs**: Contract details, payload schemas, and open follow-ups are tracked in `docs/work-packages/20251023_controller_modernization/notes/archived-plans/team-controller-plan.md`; update it alongside controller or route changes.

### RAP Time Series Controller Reference (2025 helper migration)
- **DOM contract**: `rap_ts.htm` (legacy) and `rap_ts_pure.htm` wire the acquisition button through `data-rap-action="run"` and expose schedule metadata via `<script id="rap_ts_schedule_data" type="application/json" data-rap-schedule>…</script>`. Status, stacktrace, hint, and RQ job nodes remain under `#rap_ts_form` so `controlBase` and `StatusStream` can manage telemetry without inline handlers.
- **Event surface**: `RAP_TS.getInstance().events = WCEvents.useEventMap(['rap:schedule:loaded', 'rap:timeseries:run:started', 'rap:timeseries:run:completed', 'rap:timeseries:run:error', 'rap:timeseries:status', 'job:started', 'job:completed', 'job:error'])`. Subscribe to these helper-first emissions—or the inherited `job:*` lifecycle events—in dashboards and neighbouring modules instead of scraping DOM text or listening for the legacy `RAP_TS_TASK_COMPLETED` trigger.
- **Transport**: Job submissions call `WCHttp.postJson("rq/api/acquire_rap_ts", WCForms.serializeForm(form, { format: "json" }))`. The Flask route normalises optional `datasets`, `schedule`, and `force_refresh` fields via `parse_request_payload` before enqueuing `fetch_and_analyze_rap_ts_rq(payload=…)`, which logs the metadata then runs the climate-driven acquisition pipeline.
- **Testing**: Jest coverage (`controllers_js/__tests__/rap_ts.test.js`) exercises helper bootstrap, payload submission, lifecycle events, and error handling. Backend assertions (`tests/weppcloud/routes/test_rq_api_rap_ts.py`) rely on the shared RQ + singleton factories to verify payload coercion and job bookkeeping. Run `wctl run-npm test -- rap_ts`, rebuild the bundle, and execute `wctl run-pytest tests/weppcloud/routes/test_rq_api_rap_ts.py` before handing off changes.

### Path CE Controller Reference (2025 helper migration)
- **DOM contract**: `path_cost_effective_pure.htm` exposes helper-friendly hooks: thresholds and filters ship with `name` attributes so `WCForms.serializeForm` can hydrate, table rows are rendered through a delegated `<tbody>` driven by `data-pathce-field` inputs, and all user actions run through buttons tagged with `data-pathce-action="save-config" | "run" | "add-treatment" | "remove-treatment"`. Status, hint, stacktrace, and job metadata continue to live under the `#path_ce_form` shell so `controlBase` can manage telemetry without inline handlers.
- **Event surface**: `PathCE.getInstance().events = WCEvents.useEventMap(['pathce:config:loaded', 'pathce:config:saved', 'pathce:config:error', 'pathce:treatment:added', 'pathce:treatment:removed', 'pathce:treatment:updated', 'pathce:status:update', 'pathce:results:update', 'pathce:run:started', 'pathce:run:completed', 'pathce:run:error', 'job:started', 'job:completed', 'job:error'])`. Subscribe to these emissions instead of polling DOM text when dashboards or neighbouring controllers need to react to configuration, treatment table, or run lifecycle changes.
- **Transport**: Configuration loads via `WCHttp.getJson("api/path_ce/config")` and saves through `WCHttp.postJson("api/path_ce/config", WCForms.serializeForm(form, { format: 'json' }))` augmented with harvested treatment rows. Run submissions call `WCHttp.postJson("tasks/path_cost_effective_run", {})`; job telemetry leans on `controlBase` plus `api/path_ce/status`/`api/path_ce/results`. The Flask blueprint now delegates request coercion to `parse_request_payload`, normalising floats, slope ranges, severity filters, and JSON treatment payloads before assigning to the NoDb controller.
- **Testing**: Jest coverage in `controllers_js/__tests__/path_ce.test.js` exercises config hydration, treatment table interactions, lifecycle events, and error handling. Backend assertions live in `tests/weppcloud/routes/test_path_ce_bp.py`, combining `tests.factories.singleton_factory` and the shared `rq_environment` helpers to validate payload normalisation and RQ enqueuing. Run `wctl run-npm test -- path_ce`, rebuild the bundle (`python wepppy/weppcloud/controllers_js/build_controllers_js.py`), and execute `wctl run-pytest tests/weppcloud/routes/test_path_ce_bp.py` when iterating on the PATH Cost-Effective domain.

### Batch Runner Controller Reference (2025 helper migration)
- **DOM contract**: The Pure template (`batch_runner_pure.htm`) exposes delegated hooks via `data-action="batch-upload"`, `data-action="batch-validate"`, and `data-action="batch-run"`. Run-directive checkboxes render with `data-run-directive="<slug>"`, while the resource and validation panels rely on the existing `data-role="upload-status"`, `data-role="resource-*"` (meta, schema, samples) and `data-role="validation-*"` nodes. Status, stacktrace, and job info live under `#batch_runner_form` so `controlBase` plus the controller manage telemetry without inline handlers.
- **Event surface**: `BatchRunner.getInstance().emitter = WCEvents.useEventMap([...])` emits `batch:upload:started`, `batch:upload:completed`, `batch:upload:failed`, `batch:template:validate-started`, `batch:template:validate-completed`, `batch:template:validate-failed`, `batch:run-directives:updated`, `batch:run-directives:update-failed`, `batch:run:started`, `batch:run:failed`, and `batch:run:completed`, alongside the inherited `controlBase` lifecycle events (`job:started`, `job:completed`, `job:error`). Subscribe to these events instead of scraping DOM state when dashboards or admin views need to react.
- **Transport**: uploads stream `FormData` to `/batch/_/<name>/upload-geojson`; template checks post JSON to `/batch/_/<name>/validate-template`; directive toggles post JSON to `/batch/_/<name>/run-directives`; batch submissions post JSON to `/batch/_/<name>/rq/api/run-batch`. Flask routes now consume payloads via `parse_request_payload`, and `BatchRunner.update_run_directives` coerces stringy truths (`"true"`, `"false"`, `"on"`, `"off"`) to native booleans so NoDb state stays clean. Job telemetry requests hit `/weppcloud/rq/api/jobinfo` with the tracked job IDs managed by the controller.
- **Testing**: Jest coverage in `controllers_js/__tests__/batch_runner.test.js` exercises upload/validate flows, directive persistence, run submission, event emission, and job-info polling. Backend expectations live in `tests/weppcloud/test_batch_runner_endpoints.py` (upload, validation, directives) and `tests/weppcloud/routes/test_rq_api_batch_runner.py` (queue wiring and error handling). Run `wctl run-npm test -- batch_runner`, rebuild the bundle (`python wepppy/weppcloud/controllers_js/build_controllers_js.py`), and execute `wctl run-pytest tests/weppcloud/test_batch_runner_endpoints.py tests/weppcloud/routes/test_rq_api_batch_runner.py` before handing off changes.

## Run-Scoped URL Construction

All API endpoints that operate within a run context **MUST** use `url_for_run()` from `utils.js`:

```javascript
// ✅ Correct - run-scoped endpoints
http.postJson(url_for_run("rq/api/build_climate"), payload, { form: formElement })
http.request(url_for_run("tasks/set_landuse_db"), { method: "POST", body: params })
http.get(url_for_run("query/delineation_pass"))
http.get(url_for_run("resources/subcatchments.json"))

// ❌ Wrong - missing run context
http.postJson("rq/api/build_climate", payload)
http.get("resources/subcatchments.json")
```

**Why:** Flask routes expect `/runs/<runid>/<config>/...` structure. The helper reads `window.runId` and `window.config` to build proper paths.

**Scope:** Applies to ALL endpoints under:
- `rq/api/*` - Background job triggers (build_climate, run_wepp, build_landuse, etc.)
- `tasks/*` - Task endpoints (set_*, acquire_*, modify_*, etc.)
- `query/*` - Status/data queries (delineation_pass, outlet, wepp/phosphorus_opts, etc.)
- `resources/*` - GeoJSON, legends, static data (subcatchments.json, netful.json, legends/sbs/, etc.)

**Exceptions:** Endpoints that are NOT run-scoped:
- `/batch/` routes (cross-run operations)
- `/api/` global endpoints (user prefs, system status)
- `/auth/` authentication routes
- Root routes (`/`, `/index`)

### Bulk Fix Pattern

When modernizing controllers or migrating to Pure templates, use this regex pattern to wrap unwrapped endpoints:

```python
import re
from pathlib import Path

# Pattern matches unwrapped endpoint strings (not already inside url_for_run())
pattern = r'(?<!url_for_run\()"(rq/api/|tasks/|query/|resources/)([^"]+)"'
replacement = r'url_for_run("\1\2")'

content = path.read_text()
new_content = re.sub(pattern, replacement, content)
path.write_text(new_content)
```

**Verification:**
```bash
# Check for unwrapped endpoints
grep -rh '"rq/api/\|"tasks/\|"query/\|"resources/' wepppy/weppcloud/controllers_js/*.js | grep -v url_for_run

# After fixing, restart container to rebuild controllers.js
wctl restart weppcloud

# Verify rebuild
docker logs weppcloud | grep "Building controllers"
```
