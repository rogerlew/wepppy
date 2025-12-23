# WEPPcloud Project Archiving Details

> **See also:** [AGENTS.md](../../AGENTS.md) for RQ Background Tasks and Adding an RQ Background Task sections.  
> **Related:** [weppcloud-project-forking.md](weppcloud-project-forking.md), [controller-contract.md](controller-contract.md), [trigger-refactor.md](../mini-work-packages/completed/trigger-refactor.md)

## Introduction
The archiving system lets project owners capture point-in-time snapshots of a WEPPcloud run and later restore them. Archives are stored as zip bundles within each run's working directory, under an `archives/` subfolder. The front end provides a dedicated dashboard so users can trigger archiving, monitor progress over websockets, and restore previous snapshots without leaving the run.

## Dashboard UI
Template: `wepppy/weppcloud/routes/archive_dashboard/templates/rq-archive-dashboard.htm`  
Control: `wepppy/weppcloud/templates/controls/archive_console_control.htm`

- Uses `control_shell` + `status_panel` + `stacktrace_panel` (Pure UI macros).
- Accepts an optional 40-character archive comment (stored in zip metadata).
- Lists existing archives with comment, size, timestamp, download link, and Restore/Delete actions.
- Uses native `window.confirm` for restore/delete confirmation.
- Streams job progress into the status panel through the websocket channel `<runid>:archive`.
- Status panel renders job status + start/end timestamps via polling (`#rq_job` element).

## Front-End Orchestration
Script: `wepppy/weppcloud/static/js/archive_console.js`

- Uses StatusStream for live logs + trigger events (`ARCHIVE_COMPLETE`, `ARCHIVE_FAILED`, `RESTORE_COMPLETE`, `RESTORE_FAILED`).
- Uses `controlBase` (from `controllers-gl.js`) as a polling fallback for job status:
  - `set_rq_job_id(...)` starts polling `/weppcloud/rq/api/jobstatus/<job_id>`.
  - `job:completed`/`job:error` dispatches funnel into the same handlers (idempotent guard).
  - Failure polling fetches `/weppcloud/rq/api/jobinfo/<job_id>` to populate stacktrace.
- `setActiveJob(...)` is called on submit and when `rq_archive_list` reports `in_progress` so polling resumes after reloads.
- Fetches archive/restore/delete/list with `fetch` (requests are not routed through WCHttp).

## Blueprint
Module: `wepppy/weppcloud/routes/archive_dashboard/archive_dashboard.py`

- Blueprint name: `archive`.
- Routes:
  - `rq_archive_dashboard`: renders the dashboard template and ensures the user is authorized for the run.
  - `rq_archive_list`: returns JSON describing the run's archive zips (including comments). Creates `archives/` on demand, enumerates zip entries, and records `archive_job_id` state (so the dashboard can disable buttons while a job is running).

## RQ API
Module: `wepppy/weppcloud/routes/rq/api/api.py`

- `api_archive` (POST): queues `archive_rq` and accepts an optional `comment` value (JSON or form) trimmed to 40 chars. Rejects missing runs, active `.nodb` locks, or an already running archive job (`RedisPrep.get_archive_job_id()`).
- `api_restore_archive` (POST, login required): queues `restore_archive_rq`. Rejects missing runs, active locks, missing archive files, or a running archive job. Accepts `archive_name`.
- `api_delete_archive` (POST, login required): synchronously removes a selected archive. Same guards as restore.
- Enqueue operations publish `ENQUEUED` status messages; deletes emit `Archive deleted: <name>` on the status stream.

## RQ Jobs
Module: `wepppy/rq/project_rq.py`

- `archive_rq(runid, comment)`: creates a timestamped zip under `archives/`, excluding any paths under `archives/`, and streams `Adding ...` status lines. Emits `ARCHIVE_COMPLETE` or `ARCHIVE_FAILED` trigger events; also emits `EXCEPTION` status on failure. Always clears `archive_job_id` in Redis.
- `restore_archive_rq(runid, archive_name)`: validates the zip, wipes everything except `archives/`, expands files with per-file status lines, and clears NoDb file cache. Emits `RESTORE_COMPLETE` or `RESTORE_FAILED` trigger events; emits `EXCEPTION` on failure. Always clears `archive_job_id` in Redis.

## Additional Details
- Lock enforcement uses `wepppy.nodb.base.lock_statuses(runid)` to detect locked `.nodb` files before destructive operations.
- Archive + restore share a single websocket channel: `<runid>:archive`.
- Archive metadata comments are UTF-8 encoded and limited to 40 characters (zip comment constraint).
- Restore keeps `archives/` intact and blocks path traversal by validating zip entry destinations.
