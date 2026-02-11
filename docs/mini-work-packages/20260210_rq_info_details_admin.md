# Mini Work Package: Admin RQ Info Details Snapshot + rq-engine Admin Job Listing Routes
Status: Implemented
Last Updated: 2026-02-10
Primary Areas: `wepppy/weppcloud/routes/rq/info_details/*`, `wepppy/microservices/rq_engine/admin_job_routes.py`, `wepppy/rq/job_listings.py`, `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`

## Objective
- Add an **admin-only** WEPPcloud page at `/weppcloud/rq/info-details` that renders a **static snapshot** (no polling; manual refresh button).
- Provide two **admin-only** rq-engine JSON routes so operators/agents can query job state while debugging:
  - recently completed jobs (lookback window; default 2h)
  - active jobs (complete started + queued set across default and batch queues)

## Scope
- RQ queues inspected: `default`, `batch`
- Recently completed sources: `FinishedJobRegistry`, `FailedJobRegistry` filtered by `job.ended_at >= now - lookback`.
- Active sources: `StartedJobRegistry` + queue `get_job_ids()` (complete list; no UI pagination).

## Non-goals
- No client polling / websocket updates.
- No new enqueue wiring, dependency edges, or changes to RQ job metadata emission.
- No attempt to reconstruct submitter IP beyond what is already available in user records.

## Deliverables

### 1) WEPPcloud UI page
Route:
- `GET /weppcloud/rq/info-details`

Auth:
- `login_required`
- `roles_accepted("Admin", "Root")`

UI:
- Table 1: recently completed (within lookback window)
- Table 2: active (started + queued)
- Columns include: worker, job id (link to job dashboard), function name, run id (link to run), submitter (email or fallback)
- Refresh: header action (reloads the page)

Implementation:
- `wepppy/weppcloud/routes/rq/info_details/routes.py`
- `wepppy/weppcloud/routes/rq/info_details/templates/info_details.htm`

### 2) rq-engine admin JSON endpoints
Routes:
- `GET /rq-engine/api/admin/recently-completed-jobs`
  - Query params: `lookback_seconds` (default 7200), `scan_limit` (default 2000), `queues=default,batch`
- `GET /rq-engine/api/admin/jobs-detail`
  - Query params: `queues=default,batch`

Auth:
- JWT Bearer required
- Scope: `rq:status`
- Role gate: `Admin` or `Root`

Implementation:
- `wepppy/microservices/rq_engine/admin_job_routes.py`
- Registered in `wepppy/microservices/rq_engine/__init__.py`

Inventory drift guard update:
- `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`

### 3) Shared RQ listing helpers
Library module (read-only helpers used by UI + rq-engine routes):
- `wepppy/rq/job_listings.py`

## Submitter Resolution (Best-effort)
Both the UI and rq-engine endpoints try to attach a submitter identifier:
1. If `job.meta["auth_actor"]` is present and `token_class == "user"`, resolve `user_id -> User.email` (fallback: `current_login_ip` / `last_login_ip`).
2. Else if `runid` is present, resolve `runid -> first run owner email` (same IP fallback).
3. Else fallback to a compact `submitter_actor` string (e.g. `user:123`, `session:...`, `service:...`) when available.

Note: RQ jobs do not currently persist client IP; this is intentionally not added in this package.

## Manual Validation
1. WEPPcloud UI:
   - Login as Admin/Root and open `/weppcloud/rq/info-details`.
   - Verify Refresh reloads and that job links open:
     - job dashboard: `/weppcloud/rq/job-dashboard/<job_id>`
     - run: `/weppcloud/runs/<runid>/` (redirects to active config)
2. rq-engine endpoints:
   - Issue a token with `rq:status` scope and an Admin role claim (example via `wctl issue-auth-token ... --scope rq:status --audience rq-engine --claim roles=Admin`).
   - Call:
     - `/rq-engine/api/admin/jobs-detail`
     - `/rq-engine/api/admin/recently-completed-jobs?lookback_seconds=7200`

