# WEPPcloud rq-engine
> How WEPPcloud accepts run work, tracks progress, and returns results for UI users and API users.
> **See also:** `wepppy/weppcloud/routes/usersum/weppcloud/bootstrap.md` and `docs/schemas/rq-engine-agent-api-contract.md`.

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

Polling routes are open by default and governed by `RQ_ENGINE_POLL_AUTH_MODE`:
`open` accepts anonymous polling, `token_optional` accepts anonymous polling but
validates a supplied bearer token, and `required` requires a bearer token with
`rq:status`. Successful `jobstatus` responses may include an optional advisory
`queue` snapshot for the next queued member of the requested registered tree.
It is a current queue-list observation, not an ETA; clients must continue to
use `status` as the lifecycle authority and must not treat an omitted snapshot
as job failure.

Admin debugging routes require bearer JWT + admin role:
- `GET /rq-engine/api/admin/recently-completed-jobs`
- `GET /rq-engine/api/admin/jobs-detail`

These power the admin snapshot page at:
- `/weppcloud/rq/info-details`

The snapshot is available only to Admin and Root users. It is static until
refreshed. Active work is separated into one panel per requested queue; the
default view shows `default` first and `batch` second. Recently completed and
failed jobs remain combined tables with a Queue column.

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

### 4. Project-owned config update backend

The project config update API is dormant unless
`WEPPPY_PROJECT_CONFIG_UPDATE_ENABLED` is explicitly enabled. Availability is
a read-only run-access check. Preview and apply additionally require the
current project owner or an Admin/Root user. The worker rechecks that authority.

Updates have three preview kinds:

- `additive` adds all registered attributes missing from the recorded project
  chain without overwriting existing values;
- `capability_refresh` copies the current same-locale capability envelope into
  an eligible schema-v3 Config Builder project; and
- `combined` applies both as one atomic transaction.

Capability refresh is never automatic. It preserves the project's selected
climate, station database, terrain, soil, land cover, model tuple, WEPP binary,
and mods. If one no longer fits the current envelope, refresh is unavailable
instead of silently changing the selection. Schema-v2 and named-preset projects
cannot capability-refresh.

- `GET /rq-engine/api/runs/{runid}/{config}/project-config/update-availability`
- `GET /rq-engine/api/runs/{runid}/{config}/project-config/update-preview`
- `POST /rq-engine/api/runs/{runid}/{config}/project-config/update-apply`

Apply always accepts the exact opaque `preview_id`. An additive or combined
preview also requires one reviewed `{section, option}` trigger. Capability or
combined preview requires this explicit acknowledgment:

> I understand that refreshing capability authority changes this project's
> modeling envelope, diminishes strict provenance continuity with its original
> configuration, and may expose Preview or otherwise unstable features.

The checkbox begins unchecked and resets whenever preview state changes. Apply
returns one asynchronous `job_id`, except an exact replay of the latest already-
committed preview returns the recovered result without creating another job or
amendment.

Clients must refresh after `stale_config_preview`, wait for the active job
after `config_update_in_progress`, and treat `config_update_unavailable` as a
non-mutating refusal. Missing/wrong capability acknowledgment returns
`capability_refresh_acknowledgment_required` before a job is reserved.

On run pages, this API is progressive enhancement in the shared header. A
read-only page-load check reveals an update notice, a nonblocking provenance
digest warning, or both. Opening the notice loads the complete additions and/or
capability delta. Capability refresh explicitly diminishes strict creation-time
provenance continuity, but the original creation record remains and one
reversible amendment records the acknowledged old/new authority. The refreshed
graph freezes again; later changes require another acknowledged refresh.

Nothing is applied until the user confirms the preview. The panel reports the
queued job through terminal state. If a worker fails around the atomic commit,
the panel rechecks current and last-update digests and reports whether the
change was not applied, committed/recovered, or indeterminate. Nested Omni
pages link to the top-level project's config authority rather than creating
child updates.

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
  - `docs/schemas/rq-engine-agent-api-contract.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

## When to Read Which Document
- You are learning the platform workflow:
  - Start here, then read `bootstrap.md` if you need Git-based input control.
- You are building an automation client:
  - Use `docs/schemas/rq-engine-agent-api-contract.md` as the primary contract.
