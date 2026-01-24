# Batch Runner Controller Notes
> Status: Completed (helper-first controller migration). See [controllers_js Modernization Retrospective](../../../../dev-notes/controllers_js_jquery_retro.md).

> Living contract for the batch runner controller (`wepppy/weppcloud/controllers_js/batch_runner.js`) and paired routes. Update this document whenever payloads, events, or helper usage changes.

## Current State (2026 Q1)
- **Helpers everywhere.** The controller is fully migrated onto `WCDom`, `WCForms`, `WCHttp`, `WCEvents`, and `controlBase`; no jQuery dependencies remain. DOM wiring relies on `data-action="batch-upload|batch-validate|batch-run"` and `data-run-directive="<slug>"` hooks, while resource/validation panels keep using the established `data-role` markers (`resource-*`, `validation-*`).
- **Event emitter.** `BatchRunner.getInstance().emitter = WCEvents.useEventMap([...])` broadcasts:
  - `batch:upload:started`, `batch:upload:completed`, `batch:upload:failed`
  - `batch:template:validate-started`, `batch:template:validate-completed`, `batch:template:validate-failed`
  - `batch:run-directives:updated`, `batch:run-directives:update-failed`
  - `batch:run:started`, `batch:run:failed`, `batch:run:completed`
  - `controlBase` lifecycle relays: `job:started`, `job:completed`, `job:error`
  WebSocket notifications (`BATCH_RUN_COMPLETED`, `END_BROADCAST`, `BATCH_WATERSHED_TASK_COMPLETED`) trigger `refreshRunstate()` so dashboards stay in sync with the polling loop.
- **Backend alignment.** Flask routes now call `parse_request_payload`; `BatchRunner.update_run_directives` coerces `"true"/"false"/"on"/"off"/"0"/"1"` into native booleans. The controller posts `FormData` uploads to `/rq-engine/api/batch/_/<name>/upload-geojson` (and `/upload-sbs-map`), JSON payloads to `/batch/_/<name>/validate-template` and `/batch/_/<name>/run-directives`, and submits batch runs to `/rq-engine/api/batch/_/<name>/run-batch`. Job telemetry uses the status stream plus `/batch/_/<name>/runstate` polling (10s) instead of job-info endpoints.
- **Testing.** Jest coverage (`controllers_js/__tests__/batch_runner.test.js`) exercises upload/validate flows, directive toggles, run submission, event emission, and runstate polling. Backend tests live in `tests/weppcloud/test_batch_runner_endpoints.py` (upload, validation, directives, runstate) and `tests/weppcloud/routes/test_rq_api_batch_runner.py` (queue wiring) using the shared `rq_environment` + `singleton_factory`.

## Key Design Points
- **controlBase integration.** The controller delegates button state, job status rendering, and lifecycle events to `controlBase`. Override hooks (`set_rq_job_id`, `handle_job_status_response`, `triggerEvent`) only layer on runstate refreshes and WebSocket hygiene.
- **Runstate telemetry.** The runstate panel renders a CLI-style report in a 5-column responsive grid; polling is fixed at 10s and marked "LPT (largest area first)" to match enqueue order.
- **Run directives.** Checkbox state serializes to `{slug: boolean}` before POSTing. Treat the response snapshot as authoritative—controllers should re-render based on `payload.snapshot.run_directives`.
- **Template validation.** Stored previews/summary render from the backend payload; controller-only changes should avoid mutating that structure.

## Backend Checklist (when touching routes)
- Use `parse_request_payload(request, trim_strings=True)` for JSON/form duality.
- Return `{ success, message?, snapshot? }` so the controller can diff state without additional requests.
- When adding new directives or metadata, update:
  - `BatchRunner.DEFAULT_TASKS`
  - Template rendering (card lists, labels)
  - Jest fixtures and backend tests
  - Event contracts in this note and `controllers_js/README.md`

## Testing Checklist
- `wctl run-npm lint`
- `wctl run-npm test -- batch_runner`
- `python wepppy/weppcloud/controllers_js/build_controllers_js.py`
- `wctl run-pytest tests/weppcloud/test_batch_runner_endpoints.py tests/weppcloud/routes/test_rq_api_batch_runner.py`
- `wctl run-pytest tests --maxfail=1` when changes spill into shared helpers or control base

## Follow-ups / Ideas
- BatchRunner now attaches status streams via `controlBase.attach_status_stream`; the legacy adapter has been removed.
- Explore promoting the job-info polling logic into a reusable helper once other RQ-heavy controllers migrate.
- Template validation preview still builds table rows by hand; evaluate whether a shared tabular render helper would reduce duplication.
