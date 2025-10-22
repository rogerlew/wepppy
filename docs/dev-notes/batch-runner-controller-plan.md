# Batch Runner Controller Notes
> Living contract for the batch runner controller (`wepppy/weppcloud/controllers_js/batch_runner.js`) and paired routes. Update this document whenever payloads, events, or helper usage changes.

## Current State (2025 Q2)
- **Helpers everywhere.** The controller is fully migrated onto `WCDom`, `WCForms`, `WCHttp`, `WCEvents`, and `controlBase`; no jQuery dependencies remain. DOM wiring relies on `data-action="batch-upload|batch-validate|batch-run"` and `data-run-directive="<slug>"` hooks, while resource/validation panels keep using the established `data-role` markers (`resource-*`, `validation-*`).
- **Event emitter.** `BatchRunner.getInstance().emitter = WCEvents.useEventMap([...])` broadcasts:
  - `batch:upload:started`, `batch:upload:completed`, `batch:upload:failed`
  - `batch:template:validate-started`, `batch:template:validate-completed`, `batch:template:validate-failed`
  - `batch:run-directives:updated`, `batch:run-directives:update-failed`
  - `batch:run:started`, `batch:run:failed`, `batch:run:completed`
  - `controlBase` lifecycle relays: `job:started`, `job:completed`, `job:error`
  WebSocket notifications (`BATCH_RUN_COMPLETED`, `END_BROADCAST`, `BATCH_WATERSHED_TASK_COMPLETED`) simply trigger `refreshJobInfo()` so dashboards stay in sync without bespoke polling.
- **Backend alignment.** Flask routes now call `parse_request_payload`; `BatchRunner.update_run_directives` coerces `"true"/"false"/"on"/"off"/"0"/"1"` into native booleans. The controller posts `FormData` uploads to `/batch/_/<name>/upload-geojson`, JSON payloads to `/validate-template` and `/run-directives`, and submits batch runs to `/rq/api/run-batch`. Job telemetry polls `/weppcloud/rq/api/jobinfo` using tracked IDs with `AbortController` support for restarts.
- **Testing.** Jest coverage (`controllers_js/__tests__/batch_runner.test.js`) exercises upload/validate flows, directive toggles, run submission, event emission, and job-info polling. Backend tests live in `tests/weppcloud/test_batch_runner_endpoints.py` (upload, validation, directives) and `tests/weppcloud/routes/test_rq_api_batch_runner.py` (queue wiring) using the shared `rq_environment` + `singleton_factory`.

## Key Design Points
- **controlBase integration.** The controller delegates button state, job status rendering, and lifecycle events to `controlBase`. Override hooks (`set_rq_job_id`, `handle_job_status_response`, `triggerEvent`) only layer on job-info refreshes and WebSocket hygiene.
- **Job telemetry.** `jobInfo` state tracks `trackedIds`, `completedIds`, last payloads, and the pending fetch; always route new logic through `_registerTrackedJobId(s)` to keep abort/cancel semantics intact.
- **Run directives.** Checkbox state serialises to `{slug: boolean}` before POSTing. Treat the response snapshot as authoritative—controllers should re-render based on `payload.snapshot.run_directives`.
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
- `WSClient` is still the legacy adapter; consider modernising it so batch runner (and the remaining controllers) can drop jQuery-era affordances entirely.
- Explore promoting the job-info polling logic into a reusable helper once other RQ-heavy controllers migrate.
- Template validation preview still builds table rows by hand; evaluate whether a shared tabular render helper would reduce duplication.
