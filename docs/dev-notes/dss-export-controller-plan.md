# DSS Export Controller Modernization Plan
> Working notes for migrating `dss_export.js` and its paired routes/templates to the helper-first controller stack.

## Current State (2025-02)
- Controller relies on jQuery selectors/event binding (`$("#dss_export_form")`, `$.post`) and overrides `triggerEvent` to react to `DSS_EXPORT_TASK_COMPLETED`.
- Templates ship inline event handlers (`onclick`, `onchange`) and Bootstrap-centric markup; Pure macros already remove inline JS but keep legacy IDs.
- Route `rq/api/post_dss_export_rq` consumes `parse_request_payload` but still performs manual coercion for integers/lists and writes to `_dss_*` private attributes inside a `with wepp.locked()` block.
- No dedicated Jest coverage; pytest only exercises DSS exports indirectly through `test_wepp_bp.py`.

## Refactor Goals
- Replace jQuery usage with `WCDom`, `WCForms`, `WCHttp`, `WCEvents`, and `controlBase` helpers.
- Introduce delegated `data-action` hooks for mode switching and export submission; emit scoped events (`dss:mode:changed`, `dss:export:*`) alongside base job lifecycle events.
- Post JSON payloads via `WCHttp.postJson`, preserving compatibility with legacy form posts.
- Update route (and related helpers) to consume native Python types, leverage property setters (`wepp.dss_export_mode`, etc.), and rely on `parse_request_payload` for booleans/arrays.
- Ensure `controlBase` job telemetry stays intact (`controlBase.attach_status_stream` wiring, status panel updates, download link refresh).

## Testing Checklist
- Jest: cover mode toggles, payload assembly, event emission, and network error handling with mocked helpers.
- Pytest: add focused suite for `api_post_dss_export_rq` using `tests/factories/rq_environment.py` + `singleton_factory`.
- Lint/build: `wctl run-npm lint`, `wctl run-npm test`, `python wepppy/weppcloud/controllers_js/build_controllers_js.py`.
- Backend: `wctl run-pytest tests/weppcloud/routes/test_dss_export_api.py` (new) plus regression run across `tests --maxfail=1` if shared modules touched.

## Follow-Ups / Questions
- Confirm whether other modules (prep runners, post-run pipelines) consume the new `dss:export:*` events.
- Evaluate if `controlBase` needs a higher-level `submitJob` helper once DSS migration completes.
- Consider documenting DSS payload schema in a shared location (`docs/dev-notes/controller_foundations.md`) after verifying downstream consumers.

## 2025-02 Implementation Notes
- **Controller**: Replaced jQuery with helper primitives—`WCDom.delegate` wires `data-action="dss-export-mode"` / `data-action="dss-export-run"`, payloads funnel through `WCForms.serializeForm` + `WCHttp.postJson`, and a scoped emitter surfaces `dss:mode:changed`, `dss:export:started`, `dss:export:completed`, and `dss:export:error` alongside inherited `job:*` lifecycle events. WebSocket completions now call `handleExportTaskCompleted`, which disconnects from the StatusStream helper, emits completion events, and refreshes the download link.
- **Templates**: Legacy and Pure variants dropped inline handlers in favour of helper-friendly `data-*` hooks; status/stacktrace/info markup stays intact so `controlBase` continues to manage telemetry.
- **Backend**: `api_post_dss_export_rq` now relies solely on `parse_request_payload`, accepts JSON bodies or legacy form posts, derives mode-2 channel IDs from `Watershed.chns_summary`, and persists through the public setters (`wepp.dss_export_mode`, `wepp.dss_excluded_channel_orders`, `wepp.dss_export_channel_ids`).
- **Tests**: Added `controllers_js/__tests__/dss_export.test.js` (delegated wiring, payload assembly, lifecycle events) and `tests/weppcloud/routes/test_rq_api_dss_export.py` (NoDb updates + queue wiring via shared factories). Validation run: `wctl run-npm lint`, `wctl run-npm test`, `python wepppy/weppcloud/controllers_js/build_controllers_js.py`, `wctl run-pytest tests/weppcloud/routes/test_rq_api_dss_export.py`, and `wctl run-pytest tests --maxfail=1` (fails when `node` is unavailable for `test_status_stream_node`; rerun once Node is installed).
