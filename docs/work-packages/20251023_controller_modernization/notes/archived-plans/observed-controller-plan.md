# Observed Controller Plan
> Status: Completed (helper-first controller migration). See [controllers_js Modernization Retrospective](./controllers_js_jquery_retro.md).

> Modernized control for observed data ingestion and model fitting.

## Overview
- `wepppy/weppcloud/controllers_js/observed.js` is now helper-first: `WCDom.delegate`, `WCForms.serializeForm`, `WCHttp.postJson/getJson`, `WCEvents.useEventMap`, and `controlBase` manage DOM wiring, payloads, and telemetry.
- Flask routes in `wepppy/weppcloud/routes/nodb_api/observed_bp.py` parse payloads via `parse_request_payload(trim_strings=False)` and reject missing bodies with HTTP 400 responses.
- Templates (`controls/observed.htm`, `controls/observed_pure.htm`) drop inline handlers in favour of `data-action="observed-run"` plus the canonical textarea id/name, keeping status/stacktrace panels aligned with other controls.
- Domain contracts and testing guidance now live in `controllers_js/README.md`, `controllers_js/AGENTS.md`, and `tests/weppcloud/routes/test_observed_bp.py`.

## Contract (2025-02-14)
- **DOM hooks**
  - Form shell: `#observed_form` with nested `#status`, `#stacktrace`, `#info`, `#rq_job`, optional `#hint_run_wepp`, and textarea `#observed_text`.
  - Run command: `data-action="observed-run"` button within the form scope; controller delegates via `WCDom`.
  - Visibility toggles: controller operates on the nearest `.controller-section`, so new markup should continue to wrap the form in that container.
- **Events**
  - `observed:data:loaded` – fired whenever the control is shown/hidden or when the climate probe completes; payload `{ available: boolean }`.
  - `observed:model:fit` – payload `{ status: 'started' | 'completed', task: 'observed:model-fit', payload, response? }`.
  - `observed:error` – emitted for HTTP failures or backend validation errors alongside the inherited `job:error`.
  - `job:started`, `job:completed`, `job:error` – inherited from `controlBase` for telemetry dashboards.
- **Transport**
  - Model fit submissions: `POST tasks/run_model_fit/` with JSON body `{ "data": "<CSV text>" }`.
  - Visibility probe: `GET query/climate_has_observed/` expects JSON boolean.
  - Backend accepts either `data` or `observed_text` keys; non-string or missing bodies return 400 with standard error payload.

## Testing & Tooling
- Frontend: `controllers_js/__tests__/observed.test.js` covers delegated wiring, WebSocket lifecycle, event emission, error handling, and visibility toggles. Run with `wctl run-npm test -- observed`.
- Bundle: `python wepppy/weppcloud/controllers_js/build_controllers_js.py` should succeed after edits (the modernization keeps the singleton appended to `globalThis`).
- Backend: `tests/weppcloud/routes/test_observed_bp.py` uses `tests.factories.singleton_factory` + `LockedMixin` to stub the NoDb controller. Execute via `wctl run-pytest tests/weppcloud/routes/test_observed_bp.py`.
- Full suite: `wctl run-pytest tests --maxfail=1` still requires a `node` binary for StatusStream; note failures accordingly until the dependency is vendored into the test harness.

## Open Questions / Follow-Ups
- **Chart refresh**: Model-fit reports currently rely on users visiting the generated link. Consider emitting a dedicated `observed:report:ready` event and wiring the run page to surface a toast.
- **CSV validation UX**: the controller simply forwards backend errors; explore integrating a lightweight CSV validator (client-side) to preflight obvious format issues.
- **Async execution**: the route still runs synchronously; revisit converting `calc_model_fit` into an RQ task so `controlBase` job polling can show progress.
- **Node dependency in tests**: `tests/weppcloud/controllers_js/test_status_stream_js.py` requires a `node` binary. Track progress on bundling node within the Docker image or providing a lightweight stub for environments without Node.

_Last updated: 2025-02-14_
