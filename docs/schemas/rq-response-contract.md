# RQ Response Contract
> Authoritative contract for rq-engine JSON responses (legacy weppcloud rq/api is removed).

## Scope
- Applies to rq-engine (FastAPI). Legacy weppcloud rq/api routes are removed.
- Defines canonical keys, error shapes, and job submission/polling payloads.
- Clients (controllers_js, static, profile_recorder) must normalize to this contract.

## Auth expectations
- Export endpoints require `rq:export` and run access checks.
- Job polling endpoints require `rq:status`.

## Canonical keys
- All keys use lower_snake_case.
- Job identifiers: `job_id` (single), `job_ids` (multi).
- Optional helper keys: `status_url`, `message`, `warnings`, `result`.

## Job submission responses
- Use HTTP 202 for async job submission; 200 only for synchronous updates (no job enqueued).
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
  }
}
```
- `error.details` is required for error responses; include a stacktrace (string) for exception-driven failures and a human-readable summary for validation errors (structured details belong in `errors`).
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
