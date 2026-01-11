# RQ Response Contract
> Authoritative contract for rq-engine and weppcloud rq/api JSON responses.

## Scope
- Applies to rq-engine (FastAPI) and weppcloud rq/api (Flask).
- Defines canonical keys, error shapes, and job submission/polling payloads.
- Clients (controllers_js, static, profile_recorder) must normalize to this contract.

## Canonical keys
- All keys use lower_snake_case.
- Job identifiers: `job_id` (single), `job_ids` (multi).
- Optional helper keys: `status_url`, `message`, `warnings`, `result`.

## Job submission responses
- Use HTTP 202 for async job submission; 200 only for synchronous updates (no job enqueued).
- Single job:
  - Required: `job_id`
  - Optional: `job_ids` (if present, must include `job_id` as the first element)
- Multiple jobs:
  - Required: `job_ids` (non-empty)
  - Optional: `job_id` (primary job id; if present, must be `job_ids[0]`)
- Specialized fields (allowed but not authoritative):
  - `sync_job_id`, `migration_job_id`, etc. must be accompanied by `job_id` or `job_ids`.
- Backward compatibility:
  - `jobId` may be emitted for legacy clients but is deprecated.

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

## Job polling responses
- Job status (jobstatus):
  - `{id, runid, status, started_at, ended_at}`
  - During deprecation window, unknown jobs return HTTP 200 with `status: "not_found"`.
  - A future 404 for unknown jobs is allowed only after client updates.
- Job info (jobinfo):
  - `{id, runid, status, result, started_at, ended_at, description, elapsed_s, exc_info, children}`

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
    "details": { "optional": "context" }
  }
}
```
- Validation error list:
```json
{
  "error": { "message": "Validation failed", "code": "validation_error" },
  "errors": [
    { "code": "missing_field", "message": "payload.zip is required.", "path": "payload.zip" }
  ]
}
```
- Debug stacktraces (dev-only):
  - `stacktrace: [ "line 1", "line 2" ]`

## Deprecated keys (compat only)
- `Success`, `success`, `Error`, `StackTrace`, `jobId`.
- Emit only while supporting legacy clients; new clients must not depend on them.

## Non-JSON responses
- File downloads may return non-JSON payloads on success; errors must still conform to the error schema.

## Compatibility rules (must)
- Servers MAY emit legacy keys, but MUST emit canonical keys.
- Clients MUST normalize legacy keys into canonical keys before use.
- If both `job_id` and `job_ids` are present, `job_ids[0]` MUST equal `job_id`.
