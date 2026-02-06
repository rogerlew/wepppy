# Mini Work Package: Run TTL Lifecycle + GC
Status: Draft
Last Updated: 2026-02-06
Primary Areas: `wepppy/weppcloud/utils/run_ttl.py`, `wepppy/weppcloud/routes/weppcloud_site.py`, `wepppy/weppcloud/routes/nodb_api/project_bp.py`, `wepppy/rq/project_rq.py`, `wepppy/weppcloud/templates/header/_run_header_fixed.htm`

## Objective
Introduce a durable run TTL lifecycle with a `wd/TTL` metadata file that:
- Defaults to a rolling 90-day expiration on creation.
- Resets on run access based on access log timestamps.
- Disables TTL for readonly runs.
- Excludes batch runs from TTL.
- Allows PowerUser/Admin overrides to disable TTL deletion.
- Marks deletion intent and DB cleanup state.
- Enables a GC job to purge expired runs.

## Cursory Observations
- NFS + open FDs can block deletion; TTL metadata should track delete intent even when `rmtree` fails.
- Access log cadence is acceptable for TTL refresh (no per-request hooks needed).
- Existing `READONLY`/`PUBLIC` marker files set precedent for simple run-scope metadata files.

## Scope
- Implement TTL metadata storage at `wd/TTL` (JSON) with explicit policy and delete state.
- Touch TTL from access log aggregation (`_build_run_location_dataset`).
- Add PowerUser/Admin endpoint to toggle TTL deletion.
- Add UI toggle in the More menu (after Public).
- Add delete touchpoints (mark `delete_state` + `db_cleared`).
- Add run GC job to delete expired runs.

## Non-goals
- Refactor delete behavior to rename-to-trash (tracked separately).
- Real-time TTL updates on every request.
- Global DB schema changes for TTL.

## TTL File Schema
Location: `wd/TTL`

```json
{
  "version": 1,
  "ttl_days": 90,
  "policy": "rolling_90d",
  "created_at": "2026-02-06T19:04:00Z",
  "last_accessed_at": "2026-02-06T19:04:00Z",
  "expires_at": "2026-05-07T19:04:00Z",
  "user_disabled": false,
  "disabled_by_user_id": null,
  "disabled_reason": null,
  "delete_state": "active",
  "db_cleared": false,
  "updated_at": "2026-02-06T19:04:00Z",
  "last_touched_by": "create"
}
```

Policy meanings:
- `rolling_90d`: TTL applies, `expires_at = last_accessed_at + 90 days`.
- `disabled`: TTL does not apply (`readonly` or user override).
- `excluded`: TTL does not apply (`batch` runs).

## Touch Points
- **Create**: initialize TTL after `Ron` is created.
- **Access log**: `_build_run_location_dataset` updates `last_accessed_at`/`expires_at`.
- **Readonly**: `set_run_readonly_rq` syncs TTL policy after toggle.
- **User override**: `tasks/set_ttl_disabled` updates `user_disabled` + `disabled_by_user_id`.
- **Delete**: mark `delete_state=queued`, clear DB/cache/locks, and return success without waiting on filesystem deletion (GC handles physical delete). Update `db_cleared` if DB is removed while directory persists.
  - Re-enabling TTL via UI resets `last_accessed_at` and `expires_at` from the toggle timestamp.

## API + UI
- Endpoint: `POST /runs/<runid>/<config>/tasks/set_ttl_disabled` (PowerUser/Admin/Root only)
- Payload: `{ "ttl_disabled": true | false }`
- UI: “Disable TTL Deletion” checkbox in the More menu after “Public”.

## Run GC
- RQ job: `gc_runs_rq(root="/wc1/runs", limit=200, dry_run=false)`.
- Scans for `wd/TTL` records with `policy=rolling_90d` and `expires_at <= now`, plus runs flagged `delete_state=queued`.
- Calls `delete_run_rq(delete_files=True)` for expired/queued runs and logs failures to `gc:ttl` status channel.
- Scheduled via `wepppy.tools.scheduler` sidecar in compose, configured in `docker/scheduled-tasks.yml` to enqueue daily.

**Implementation Status**
- Implemented `wd/TTL` lifecycle helpers in `wepppy/weppcloud/utils/run_ttl.py`.
- Wired TTL initialization for run creation (rq-engine create, HUC fire, test support) and fork reset.
- Synced TTL policy on readonly toggles via `set_run_readonly_rq`.
- Touches TTL from access-log aggregation in `_build_run_location_dataset`.
- Added TTL disable endpoint + UI toggle (PowerUser/Admin/Root).
- Added delete touchpoints (mark `delete_state=queued`, record `db_cleared`).
- Delete job is now logical-only; GC handles physical deletion on NFS.
- Access-log dataset hides runs with `delete_state != active`.
- Added GC job `gc_runs_rq` to purge expired runs.
- Added scheduler sidecar to enqueue GC from `docker/scheduled-tasks.yml`.

**Checklist**
- [x] Add TTL metadata file and helpers.
- [x] Initialize TTL on create (rq-engine, HUC fire, test support) and reset on fork.
- [x] Sync TTL policy on readonly toggle.
- [x] Touch TTL from access log aggregation.
- [x] Add TTL disable endpoint + UI toggle.
- [x] Add delete touchpoints to mark delete state.
- [x] Treat delete jobs as logical deletes (GC removes files).
- [x] Add GC job for expired runs.
- [x] Schedule GC job via compose scheduler sidecar.
- [ ] Decide on rename-to-trash deletion fallback for NFS `EBUSY`.

## Validation
- Create a run and confirm `wd/TTL` is created with `expires_at` set.
- Touch access log and confirm TTL extends.
- Toggle readonly on/off and confirm TTL policy flips to disabled and back.
- Toggle TTL disable as PowerUser/Admin and confirm user override persists.
- Run GC in dry-run mode and verify expected candidates.

## Follow-ups
- Rename-to-trash deletion fallback for NFS `EBUSY`.
- Dedicated UI to display TTL metadata and delete state.
- Tune GC schedule, jitter, and limits as usage grows.
