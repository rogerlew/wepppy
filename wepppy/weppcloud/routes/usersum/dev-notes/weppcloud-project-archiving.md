# WEPPcloud Project Archiving Details

## Introduction
The archiving system lets project owners capture point-in-time snapshots of a WEPPcloud run and later restore them. Archives are stored as zip bundles within each run’s working directory, under an `archives/` subfolder. The front end provides a dedicated dashboard so users can trigger archiving, monitor progress over websockets, and restore previous snapshots without leaving the run.

## Dashboard
Template: `wepppy/weppcloud/routes/archive_dashboard/templates/rq-archive-dashboard.j2`

- Accepts an optional 40-character archive comment that is saved with the zip metadata.
- Lists existing archives with comment, size, timestamp, download link, and Restore/Delete actions.
- Submits archive requests via `/rq/api/archive`, restore requests via `/rq/api/restore-archive`, and delete requests via `/rq/api/delete-archive`.
- Uses Bootstrap modals to confirm destructive restores and deletes, explaining the impact of each action.
- Streams job progress into the status panel through the websocket channel `<runid>:archive`.
- Reacts to `ARCHIVE_COMPLETE` and `RESTORE_COMPLETE` events to refresh the table, re-enable buttons, and show a quick link (`#bottom`) back to the project.

## Blueprint
Module: `wepppy/weppcloud/routes/archive_dashboard/archive_dashboard.py`

- Blueprint name: `archive`.
- Routes:
  - `rq_archive_dashboard`: renders the dashboard template and ensures the user is authorized for the run.
  - `rq_archive_list`: returns JSON describing the run’s archive zips (including comments). Creates `archives/` on demand, enumerates zip entries, and records `archive_job_id` state (so the dashboard can disable buttons while a job is running).

## RQ API
Module: `wepppy/weppcloud/routes/rq/api/api.py`

- `api_archive` (POST): queues `archive_rq` and accepts an optional `comment` value (JSON or form) that is trimmed to 40 characters. Rejects the request if the run directory is missing, any `.nodb` lock files are active, or another archiving/restore job is already queued/active (checked via `RedisPrep.get_archive_job_id()`).
- `api_restore_archive` (POST): queues `restore_archive_rq`. Shares the same guard rails—missing run, active locks, missing archive file, or an already running job. Accepts either JSON or form payload containing `archive_name`.
- `api_delete_archive` (POST): synchronously removes a selected archive (login required). Shares the same authorization and lock checks as restore.
- Archive and restore enqueue operations publish status messages using `StatusMessenger` so the websocket stream gets an `ENQUEUED` notification, and deletes emit a synchronous "Archive deleted" update for the dashboard log.

## RQ Jobs
Module: `wepppy/rq/project_rq.py`

- `archive_rq(runid, comment)`: creates a timestamped zip under `archives/`, persisting the optional comment in the archive metadata. Walks the working directory, excluding any paths under `archives/`, and emits “Adding …” status lines. On success publishes `ARCHIVE_COMPLETE`, on failure publishes `EXCEPTION`. Always clears `archive_job_id` in Redis.
- `restore_archive_rq(runid, archive_name)`: validates the requested zip, wipes everything except `archives/`, then expands the archive while streaming per-file progress (“Restored file …”). Rejects attempts to extract outside the run directory, respects archive permissions when possible, and finishes with `RESTORE_COMPLETE`. Also clears the shared job id on exit.

## Additional Details
- Lock enforcement uses `wepppy.nodb.base.lock_statuses(runid)` to detect locked `.nodb` files before destructive operations.
- All status messaging flows through the `<runid>:archive` websocket channel, so both archive and restore jobs share the same dashboard feed.
- The dashboard reuses `runs0` for the “Load Project” link when a restore completes, keeping URL generation server-driven instead of hardcoding the host.
- Archive metadata comments are UTF-8 encoded and limited to 40 characters to fit within the zip comment constraint.
- The archive and delete confirmation modals rely on Bootstrap’s bundled JS; no additional dependencies were introduced.
