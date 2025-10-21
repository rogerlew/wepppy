# Controllers JS Architecture

> **See also:** [AGENTS.md](../../../AGENTS.md) for Front-End Development section and controller bundling overview.

This note explains how the controller JavaScript in `wepppy/weppcloud` is organized, how individual controller modules cooperate with the shared infrastructure, and what needs to happen when you extend the system.

## Layout and Bundling
- Authoring happens in `wepppy/weppcloud/controllers_js/*.js` (one file per controller plus shared helpers such as `control_base.js`, `ws_client.js`, and `status_stream.js`).
- The browser still downloads a single bundle, `wepppy/weppcloud/static/js/controllers.js`. The bundle is rendered from `controllers_js/templates/controllers.js.j2`, which now loops over the discovered `.js` files automatically; simply dropping a new controller file into the directory is enough for it to be included.
- The `build_controllers_js.py` helper (same directory) renders the template with Jinja, stamps a build date, and writes the bundle just before Gunicorn starts. Core infrastructure files (`utils.js`, `control_base.js`, `project.js`, etc.) are emitted first to preserve dependencies; the remainder are appended alphabetically.

## Singleton Controller Modules
- Each controller file exposes a global (for example `var Project = function () { … }();`). The module keeps a private `instance` and returns an object containing `getInstance`, so we effectively have singletons.
- The singleton pattern avoids repeated DOM wiring and ensures components like WebSocket connections are not duplicated. Callers must use `ControllerName.getInstance()` rather than constructing their own copy.
- Controllers are expected to initialize inside existing forms (usually via document ready hooks in the templates). They usually cache references to form elements (`that.form = $('#wepp_form')`), register AJAX handlers, and expose methods that other controllers can call.

## ControlBase and Job Orchestration
- `control_base.js` provides the common behavior that every controller mixes in. Calling `controlBase()` returns an object with helper methods for:
  - Tracking RQ job state (`set_rq_job_id`, `fetch_job_status`, `render_job_status`).
  - Managing the command button UI (disabling while a job is active, restoring afterwards).
  - Writing stack traces and error messages to the standard output areas.
  - Polling for job status and stopping when work reaches a terminal state.
- `WSClient` (in `ws_client.js`) is the legacy companion that listens for WebSocket broadcasts. Messages are passed through NoDbBase subclass loggers through redis and status microservice. Controllers assign `that.ws_client = new WSClient(formId, channel)` and `controlBase.manage_ws_client` will connect whenever a job is running so live status text, trigger events, and exception information stream into the panel.
- `StatusStream` (in `status_stream.js`) is the new lightweight alternative used by console dashboards and upcoming control migrations. It renders against `[data-status-panel]`/`[data-status-log]` markup, manages reconnection/backoff, emits `status:*` custom events, and hydrates stack traces through optional fetchers. ControlBase will move to `StatusStream` once run controls adopt the new macros.
- Together, these two components are the contract for any control that launches asynchronous work: provide the DOM IDs, call `set_rq_job_id`, and the infrastructure handles the rest.
- The Project controller applies the same contract when readonly toggles queue `set_run_readonly_rq`; the worker now pushes human-readable updates to `<runid>:command`, which the command bar consumes directly to surface messages such as `manifest.db creation finished` without extra wiring.

## Views and DOM Contract
- The HTML that controllers operate on lives under `wepppy/weppcloud/templates/controls/`. Each control has its own template (`wepp.htm`, `landuse.htm`, etc.) and they all extend the markup defined in `_base.htm`.
- `_base.htm` defines the canonical form structure: `#status`, `#info`, `#rq_job`, `#stacktrace`, `#preflight_status`, and other fields that the JS expects. As long as new controls keep those IDs, `controlBase` can update the UI without per-controller duplication.
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

Keep this document updated when the bundling flow or controller contract changes.
