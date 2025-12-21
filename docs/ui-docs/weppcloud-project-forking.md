# WEPPcloud Project Forking Details

> **See also:** [AGENTS.md](../../AGENTS.md) for RQ Background Tasks and Adding an RQ Background Task sections.  
> **Related:** [weppcloud-project-archiving.md](weppcloud-project-archiving.md), [controller-contract.md](controller-contract.md), [trigger-refactor.md](../mini-work-packages/completed/trigger-refactor.md)

## Introduction
The forking system clones an existing WEPPcloud run into a new run directory. The fork console lets users submit a fork job, monitor live status output, and open the new run when the job completes. Forking can optionally "undisturbify" the run by clearing disturbance artifacts, rebuilding landuse/soils, and rerunning WEPP.

## Fork Console UI
Template: `wepppy/weppcloud/routes/fork_console/templates/rq-fork-console.htm`  
Control: `wepppy/weppcloud/templates/controls/fork_console_control.htm`

- Uses `control_shell` with a console-style status panel and stacktrace panel.
- Shows source run ID (read-only), an undisturbify checkbox, and submit/cancel controls.
- Emits live status updates via the `<runid>:fork` StatusStream channel.
- Renders job status plus start/end timestamps in the status panel (`#rq_job`) via polling fallback.

## Front-End Orchestration
Script: `wepppy/weppcloud/static/js/fork_console.js`

- Reads run context from `data-fork-console-config` and the form.
- Submits the fork request with `fetch` to `/runs/<runid>/<config>/rq/api/fork` (form-encoded `undisturbify`).
- Starts StatusStream on channel `fork` and uses `controlBase` polling to keep job status fresh:
  - `set_rq_job_id(...)` polls `/weppcloud/rq/api/jobstatus/<job_id>` for status/started/ended timestamps.
  - Polling failures fetch `/weppcloud/rq/api/jobinfo/<job_id>` to populate stacktraces.
  - `job:completed`/`job:error` fallback handlers are idempotent.
- Completion updates the console with the new run link; failure surfaces the status log + stacktrace panel.
- Cancel uses `/weppcloud/rq/canceljob/<job_id>` to request termination.

## Blueprint
Module: `wepppy/weppcloud/routes/fork_console/fork_console.py`

- Blueprint name: `fork`.
- Route:
  - `rq_fork_console`: renders the console template, parses optional `undisturbify` query param, and authorizes the run.

## RQ API
Module: `wepppy/weppcloud/routes/rq/api/api.py`

- `api_fork` (POST): queues `fork_rq` for the source run.
  - Payload: form fields `undisturbify` and optional `target_runid`.
  - Validates permissions (run owners, admin users, public runs, or ownerless runs).
  - Allocates a new run ID via `awesome_codename` when no target is supplied.
  - Registers the new run in the user database (when available).
  - Responds with `{ Success, job_id, new_runid, undisturbify }`.

## RQ Jobs
Module: `wepppy/rq/project_rq.py`

- `fork_rq(runid, new_runid, undisturbify)`:
  - Uses `rsync` to clone the run directory and streams rsync output to `<runid>:fork`.
  - Rewrites `.nodb` paths and clears locks, `READONLY`, and `PUBLIC` markers.
  - When `undisturbify=True`, removes SBS artifacts, rebuilds landuse/soils, and enqueues WEPP; completion is emitted by `_finish_fork_rq` after WEPP finishes.
  - Emits `FORK_COMPLETE` on success and `FORK_FAILED` on failure.
- `_finish_fork_rq(runid)`: publishes the final completion trigger once dependent jobs finish.

## Additional Details
- Status messages and triggers are published on the source run channel `<runid>:fork`.
- Fork completion can arrive from StatusStream or polling; the console uses guarded handlers to prevent duplicate completion flows.
- The new run ID is surfaced via both the status panel link and the console action panel.
