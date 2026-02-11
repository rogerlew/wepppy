# WEPPcloud rq-engine
> How WEPPcloud accepts run work, tracks progress, and returns results for UI users and API users.
> **See also:** `wepppy/weppcloud/routes/usersum/weppcloud/bootstrap.md` and `docs/dev-notes/rq-engine-agent-api.md`.

## Overview
`rq-engine` is the API layer that starts most run work in WEPPcloud. When you
click buttons like build, run, upload, export, or Bootstrap no-prep actions, the
UI usually sends a request to `rq-engine`.

Think of `rq-engine` as the "job dispatcher":
1. You request work.
2. A background job is created.
3. You poll job status until completion.
4. You read results or error details.

## UI vs API: What Changes?
- UI users:
  - Usually do not call `rq-engine` directly.
  - WEPPcloud pages call it for you.
  - Progress appears in status panels and logs.
- API or automation users:
  - Call `rq-engine` endpoints directly.
  - Provide bearer tokens when required.
  - Poll job endpoints (`jobstatus`, `jobinfo`) to track execution.

If you are not automating workflows, stay in the UI.

## URL Shape
In WEPPcloud deployments behind Caddy, routes are usually under:
- `/rq-engine/api/...`

Examples:
- `POST /rq-engine/api/runs/{runid}/{config}/run-wepp`
- `GET /rq-engine/api/jobstatus/{job_id}`
- `GET /rq-engine/api/admin/jobs-detail` (admin debugging)

## Job Lifecycle Mental Model
Most run operations are asynchronous (background jobs).

Typical flow:
1. `POST` to an action route.
2. Response returns `job_id` and often `status_url`.
3. Poll `GET /rq-engine/api/jobstatus/{job_id}` for state.
4. If failed, inspect `GET /rq-engine/api/jobinfo/{job_id}` for details.

Common status progression:
- `queued`
- `started`
- terminal state (`finished`, `failed`, `canceled`, or `stopped`)

## Tokens and Access
Many routes require a bearer token with required scopes.

Common scopes:
- `rq:enqueue` for most run mutations.
- `rq:status` for job polling and cancel.
- `rq:export` for export routes.
- `bootstrap:*` scopes for Bootstrap operations.

Polling routes are currently open by default in WEPPcloud policy, but this can
be tightened with environment settings.

Admin debugging routes require bearer JWT + admin role:
- `GET /rq-engine/api/admin/recently-completed-jobs`
- `GET /rq-engine/api/admin/jobs-detail`

These power the admin snapshot page at:
- `/weppcloud/rq/info-details`

## Common User Workflows
### 1. Standard WEPPcloud UI run
1. Configure controls in the UI.
2. Click run/build button.
3. UI enqueues work via `rq-engine`.
4. UI polls job status and shows completion.

### 2. Scripted run request
1. Obtain a valid bearer token.
2. `POST` the run route.
3. Store returned `job_id`.
4. Poll until terminal status.
5. Read results or errors.

### 3. Bootstrap no-prep run
1. Push input-file commit via Bootstrap Git flow.
2. Use Bootstrap no-prep run action.
3. `rq-engine` runs with checked-out commit inputs.
4. Poll and review outputs in WEPPcloud.

## Error Handling Expectations
rq-engine uses a canonical error payload:

```json
{
  "error": {
    "message": "Human-readable summary",
    "code": "optional_code",
    "details": "additional details or traceback"
  }
}
```

Practical guidance:
- Treat non-2xx as failure.
- Use `error.message` for user-facing summaries.
- Use `error.details` for troubleshooting.

## Operational Notes
- Polling endpoints include rate limiting.
- Job IDs are UUID-like identifiers; keep them if you need to recover status.
- Route-level auth and status contracts are documented in:
  - `docs/dev-notes/rq-engine-agent-api.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

## When to Read Which Document
- You are learning the platform workflow:
  - Start here, then read `bootstrap.md` if you need Git-based input control.
- You are building an automation client:
  - Use `docs/dev-notes/rq-engine-agent-api.md` as the primary contract.
