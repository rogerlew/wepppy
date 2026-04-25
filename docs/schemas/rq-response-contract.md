# RQ Response Contract
> Authoritative contract for rq-engine JSON responses (legacy weppcloud rq/api is removed).
> **See also:** `docs/schemas/weppcloud-session-contract.md` for browser/session lifecycle rules.

## Scope
- Applies to rq-engine (FastAPI) and WEPPcloud JSON error helpers that emit the
  canonical error envelope (`wepppy/weppcloud/utils/helpers.py`).
- Legacy weppcloud rq/api routes are removed.
- Defines canonical keys, error shapes, and job submission/polling payloads.
- Clients (controllers_js, static, profile_recorder) must normalize to this contract.

## Auth expectations
- Export endpoints require `rq:export` and run access checks.
- Job polling endpoints are open by default under
  `RQ_ENGINE_POLL_AUTH_MODE=open`.
- When polling auth mode validates bearer tokens
  (`token_optional`/`required`), tokens must include `rq:status`.

## Canonical keys
- All keys use lower_snake_case.
- Job identifiers: `job_id` (single), `job_ids` (multi).
- Optional helper keys: `status_url`, `message`, `warnings`, `result`.

## Job submission responses
- Async job submission endpoints may return HTTP `200` or `202` depending on
  the route contract; async responses must include canonical job keys
  (`job_id` or `job_ids`).
- Prefer HTTP `202` for new async endpoints when contract changes are
  acceptable.
- Synchronous 200 responses must use `message` (and optional `result`/`warnings`); do not return legacy keys like `Content`.
- Single job:
  - Required: `job_id`
  - Optional: `job_ids` (if present, must include `job_id` as the first element)
- Multiple jobs:
  - Required: `job_ids` (non-empty)
  - Optional: `job_id` (primary job id; if present, must be `job_ids[0]`)
- Specialized fields (allowed but not authoritative):
  - `sync_job_id`, `migration_job_id`, etc. must be accompanied by `job_id` or `job_ids`.

Example (single job):
```json
{
  "job_id": "rq-123",
  "status_url": "/rq-engine/api/jobstatus/rq-123",
  "message": "Job enqueued."
}
```

Example (multi job):
```json
{
  "job_ids": ["rq-123", "rq-456"],
  "job_id": "rq-123",
  "message": "Jobs enqueued."
}
```

Example (sync update):
```json
{
  "message": "Already up to date."
}
```

Landuse first-class route notes (2026-04-24):
- Phase 1 synchronous mutators
  (`set-landuse-mode`, `set-landuse-db`, `modify-landuse-coverage`) return
  HTTP `200` with canonical `{"message": ...}` on success and canonical error
  payloads on failure.
- Phase 2 read endpoint
  (`GET /api/runs/{runid}/{config}/controllers/landuse/state`) returns
  controller-state metadata including:
  - `controller`
  - `state`
  - `run_state_domain`
  - `run_state_vector`
  - `run_state_revision`
  - optional weak `etag` for client cache/coherency signaling.
- Legacy Flask landuse compatibility machine/state routes were removed on
  `2026-04-24`; callers should expect routing-level `404` from removed Flask
  endpoints and use rq-engine routes as the canonical contract surface.
- Phase 3 catalog/map mutators return HTTP `200` with explicit message-bearing
  payloads and route-specific result fields:
  - catalog upload/delete/update-description: `message`, `items`,
    `catalog_count` (+ route-specific fields such as `imported_files` or
    `deleted`)
  - map save/clear-override: `message` (+ `lookup_sha256` on save)
  - modify-landuse: `message`, `topaz_count`
- Phase 3 hardening error contracts are explicit:
  - `PRECONDITION_REQUIRED` (`428`) for missing map save preconditions
  - `STALE_LOOKUP` (`409`) for stale optimistic-concurrency hashes
  - `CATALOG_CONFLICT` (`409`) for conflicting user-defined filename uploads
  - `validation_error` / route-specific explicit `400` payloads for invalid row
    schemas or input coercion failures.

## Job polling responses
- Job status (jobstatus):
  - `{job_id, runid, status, started_at, ended_at}`
- Job info (jobinfo):
  - `{job_id, runid, status, result, started_at, ended_at, description, elapsed_s, exc_info, children, auth_actor}`
  - `auth_actor` is optional and only includes non-PII identifiers (no JWTs, no email).

## Error responses
- Use status-code-first semantics:
  - 4xx for validation/input errors.
  - 5xx for server errors.
- Canonical error payload:
```json
{
  "error": {
    "message": "Human-readable summary",
    "code": "optional_code",
    "details": "Stacktrace string or error details"
  },
  "error_id": "optional-correlation-id"
}
```
- `error.details` is required for 4xx responses; include a human-readable summary for validation/auth/access failures (structured details belong in `errors`).
- For 5xx responses, include traceback text in `error.details` when available. When traceback details are intentionally omitted from the client response, return `error_id` and ensure logs preserve traceback/error context for that identifier.
- `error_id` is **required for all HTTP 5xx responses** so operators can correlate client-visible failures to server logs and failure sites.
- For 5xx responses, observability requirements are:
  - return a stacktrace in `error.details`, or
  - return a stable `error_id` and ensure the server logs contain traceback/error context tagged with that same `error_id`.
- `error_id` is optional for generic 4xx responses, but **required** for upload-facing errors (see `docs/schemas/upload-endpoint-contract.md`).
- Job polling not-found:
  - `/rq-engine/api/jobstatus/<job_id>` and `/rq-engine/api/jobinfo/<job_id>` return HTTP 404 with the canonical error payload and `error.code="not_found"`.
- Validation error list:
```json
{
  "error": {
    "message": "Validation failed",
    "code": "validation_error",
    "details": "payload.zip is required."
  },
  "errors": [
    { "code": "missing_field", "message": "payload.zip is required.", "path": "payload.zip" }
  ]
}
```

## Non-JSON responses
- File downloads may return non-JSON payloads on success; errors must still conform to the error schema.

## Compatibility rules (must)
- Servers MUST emit canonical keys only.
- Clients MUST rely on canonical keys.
- If both `job_id` and `job_ids` are present, `job_ids[0]` MUST equal `job_id`.
