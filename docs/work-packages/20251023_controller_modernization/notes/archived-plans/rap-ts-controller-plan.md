# RAP Time Series Controller Plan
> Status: Completed (helper-first controller migration). See [controllers_js Modernization Retrospective](./controllers_js_jquery_retro.md).

> Contract and follow-up notes for the helper-first RAP time-series control (2025 refresh).

## Current Architecture
- Controller lives in `wepppy/weppcloud/controllers_js/rap_ts.js` and now relies exclusively on `WCDom`, `WCForms`, `WCHttp`, `WCEvents`, `controlBase`, and `controlBase.attach_status_stream`. The singleton exposes `RAP_TS.getInstance()`.
- Templates (`rap_ts.htm`, `rap_ts_pure.htm`) drop inline handlers in favour of delegated hooks:
  - Acquisition button carries `data-rap-action="run"` to keep interactions helper-friendly.
  - Schedule metadata (if any) ships via `<script id="rap_ts_schedule_data" type="application/json" data-rap-schedule>…</script>` for zero-request hydration.
  - Status, hint, stacktrace, and RQ job nodes remain under `#rap_ts_form` so `controlBase` can manage telemetry.
- Flask route `rq/api/acquire_rap_ts` parses payloads through `parse_request_payload`, normalises native booleans/arrays, and enqueues `fetch_and_analyze_rap_ts_rq(payload=…)`.
- Worker task `fetch_and_analyze_rap_ts_rq` accepts an optional payload, logs metadata for observability, and runs the climate-driven RAP acquisition before publishing `RAP_TS_TASK_COMPLETED`.

## Payload Schema
```
POST rq/api/acquire_rap_ts
Content-Type: application/json

{
  "datasets": [string],      // optional; list of dataset identifiers
  "schedule": [...],         // optional; array/object describing queued jobs
  "force_refresh": boolean   // optional; bypass cached rasters when true
}
```
- `datasets` accepts JSON arrays (`["rap_ts", "ndvi"]`) or comma-separated strings (`"rap_ts,ndvi"`); both paths normalise to a list of trimmed strings.
- `schedule` can be any JSON-compatible structure (list or object). Invalid JSON returns `exception_factory("Schedule payload must be valid JSON.")`.
- `force_refresh` is coerced to a native boolean so downstream helpers never inspect `"on"` or `"true"` strings.
- Response echoes the queue metadata:
  ```json
  { "Success": true, "job_id": "job-123", "payload": { ... } }
  ```
  `payload` is omitted when all options are empty.

## Event Contract
- Helper surface: `RAP_TS.getInstance().events = WCEvents.useEventMap([...])` publishing:
  - `rap:schedule:loaded` — fires once during bootstrap with the parsed schedule payload (empty array when none supplied).
  - `rap:timeseries:run:started` / `rap:timeseries:run:completed` / `rap:timeseries:run:error` — lifecycle around job submission and completion.
  - `rap:timeseries:status` — coarse state machine (`started`, `queued`, `completed`, `error`) for dashboards and telemetry bridges.
  - Inherited `job:started`, `job:completed`, `job:error` from `controlBase`.
- Legacy DOM event `RAP_TS_TASK_COMPLETED` is still dispatched (via `StatusStream` trigger) and now mirrored through the helper events.

## Testing Checklist
1. **Frontend**: `wctl run-npm lint`, `wctl run-npm test -- rap_ts`.
2. **Bundle**: `python wepppy/weppcloud/controllers_js/build_controllers_js.py`.
3. **Backend**: `wctl run-pytest tests/weppcloud/routes/test_rq_api_rap_ts.py`.
4. **Integration (as needed)**: run the RQ worker locally (`wctl up weppcloud-rq`) and trigger acquisition to observe StatusStream / WebSocket behaviour.

## Follow-ups / Observations
- Controller currently logs schedule metadata but does not alter run ordering; future work could surface queued jobs in the UI using the `rap:schedule:loaded` payload.
- `fetch_and_analyze_rap_ts_rq` ignores `force_refresh` beyond logging. If cache bypass is required, extend the NoDb helper to clear parquet/rasters when the flag is true.
- StatusStream still emits raw RQ status lines. Consider adding a shared formatter for RAP to provide user-friendly text (mirrors `controlBase.appendStatus`).
- Keep this plan in sync when payload fields, helper dependencies, or event names change; link downstream docs (e.g., `docs/ui-docs/control-components.md`) when the control gains UI affordances.
