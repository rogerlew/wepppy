# WEPPcloud Project Archiving Details

## Introduction
The archiving system lets project owners capture point-in-time snapshots of a WEPPcloud run and later restore them. Archives are stored as zip bundles within each run’s working directory, under an `archives/` subfolder. The front end provides a dedicated dashboard so users can trigger archiving, monitor progress over websockets, and restore previous snapshots without leaving the run.

## Dashboard
Template: `wepppy/weppcloud/templates/controls/rq-archive-dashboard.j2`

- Lists existing archives with size, timestamp, download link, and a Restore action.
- Submits archive requests via `/rq/api/archive` and restore requests via `/rq/api/restore-archive`.
- Uses a Bootstrap modal to confirm destructive restores, explaining that all files except `archives/` will be replaced.
- Streams job progress into the status panel through the websocket channel `<runid>:archive`.
- Reacts to `ARCHIVE_COMPLETE` and `RESTORE_COMPLETE` events to refresh the table, re-enable buttons, and show a quick link (`#bottom`) back to the project.

## Blueprint
Module: `wepppy/weppcloud/routes/archive.py`

- Blueprint name: `archive`.
- Routes:
  - `rq_archive_dashboard`: renders the dashboard template and ensures the user is authorized for the run.
  - `rq_archive_list`: returns JSON describing the run’s archive zips. Creates `archives/` on demand, enumerates zip entries, and records `archive_job_id` state (so the dashboard can disable buttons while a job is running).

## RQ API
Module: `wepppy/weppcloud/routes/rq/api/api.py`

- `api_archive` (POST): queues `archive_rq`. Rejects the request if the run directory is missing, any `.nodb` lock files are active, or another archiving/restore job is already queued/active (checked via `RedisPrep.get_archive_job_id()`).
- `api_restore_archive` (POST): queues `restore_archive_rq`. Shares the same guard rails—missing run, active locks, missing archive file, or an already running job. Accepts either JSON or form payload containing `archive_name`.
- Both endpoints publish status messages using `StatusMessenger` so the websocket stream gets an `ENQUEUED` notification.

## RQ Jobs
Module: `wepppy/rq/project_rq.py`

- `archive_rq(runid)`: creates a timestamped zip under `archives/`. Walks the working directory, excluding any paths under `archives/`, and emits “Adding …” status lines. On success publishes `ARCHIVE_COMPLETE`, on failure publishes `EXCEPTION`. Always clears `archive_job_id` in Redis.
- `restore_archive_rq(runid, archive_name)`: validates the requested zip, wipes everything except `archives/`, then expands the archive while streaming per-file progress (“Restored file …”). Rejects attempts to extract outside the run directory, respects archive permissions when possible, and finishes with `RESTORE_COMPLETE`. Also clears the shared job id on exit.

## Additional Details
- Lock enforcement uses `wepppy.nodb.base.lock_statuses(runid)` to detect locked `.nodb` files before destructive operations.
- All status messaging flows through the `<runid>:archive` websocket channel, so both archive and restore jobs share the same dashboard feed.
- The dashboard reuses `runs0` for the “Load Project” link when a restore completes, keeping URL generation server-driven instead of hardcoding the host.
- The archive modal relies on Bootstrap’s bundled JS; no additional dependencies were introduced.
