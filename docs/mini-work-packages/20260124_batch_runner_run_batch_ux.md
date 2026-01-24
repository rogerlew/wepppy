# Mini Work Package: Batch Runner Run Batch UX + Progress Polling
Status: Draft
Last Updated: 2026-01-24
Primary Areas: `wepppy/rq/batch_rq.py`, `wepppy/nodb/batch_runner.py`, `wepppy/weppcloud/routes/batch_runner/*`, `wepppy/weppcloud/controllers_js/batch_runner.js`

## Objective
Align the Batch Runner "Run Batch" experience with the controller contract: show a persistent RQ job hint link, hydrate job state after reloads, replace the per-job pill status panel with a meaningful CLI-style progress report, and keep polling alive even when individual child runs fail.

## Scope
- **Job hint + reload hydration**
  - Persist the root `run_batch_rq` job id in `BatchRunner` state.
  - Pass persisted job ids through the batch runner bootstrap context.
  - Hydrate `set_rq_job_id` on load so the RQ dashboard link appears after reloads.
- **Progress polling**
  - Add `/batch/_/<name>/runstate` endpoint that returns the CLI-style runstate report.
  - Render the report in the Summary panel using a monospace `<pre>` and a responsive 5-column grid layout.
  - Poll at a low cadence (10s) and refresh on batch triggers; display the interval + LPT ordering note in the UI.
- **Child job failure handling**
  - Guard per-watershed batch jobs so exceptions are captured, logged, and recorded, but do not fail the RQ job.
  - Emit `EXCEPTION_JSON` + `BATCH_WATERSHED_TASK_COMPLETED` so the status stream and runstate polling keep moving.

## Non-goals
- Full visual redesign of the Batch Runner page.
- Changing batch task semantics or WEPP processing behavior.
- Adding new metrics or charts beyond the CLI report output.

## Implementation Plan
1. **Backend state + reporting**
   - Store `rq_job_ids["run_batch_rq"]` on `BatchRunner`.
   - Update `_build_batch_runner_snapshot` to include job ids.
   - Adjust `generate_runstate_cli_report()` to return a string (no terminal clear/print).
   - Add `GET /batch/_/<name>/runstate` to serve the CLI report payload.
2. **Batch RQ guardrails**
   - In `run_batch_rq`, persist the root job id to `BatchRunner`.
   - In `run_batch_watershed_rq`, catch exceptions, write `run_metadata.json`, emit `EXCEPTION_JSON`, and return `(False, elapsed)` without raising.
3. **Frontend UX**
   - Switch Run Batch hint to `data-job-hint` (job link only).
   - Add a separate status chip for Run Batch messages.
   - Replace job-info pills with a `<pre>` runstate display.
   - Implement polling and refresh hooks for the runstate endpoint.

## Validation
- Reload the Batch Runner page while a batch is running; the RQ job link stays visible and the Run Batch button stays locked.
- Run a batch with one failing child; the UI continues to update and the status stream shows the error payload.
- Summary panel shows the CLI emoji report in a responsive grid and updates every 10 seconds.

## Follow-ups
- Consider surfacing per-run failures next to the emoji table (if needed).
- Decide whether to clear stored `run_batch_rq` job ids after completion.
