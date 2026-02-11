# Files Agent API
> Agent-friendly JSON endpoints for file discovery and metadata within WEPPcloud runs.
> **See also:** `docs/schemas/rq-response-contract.md` for canonical error payloads.

## Goals
- Provide predictable, JSON-only file browsing for automation agents.
- Maintain strict path safety within a run config root.
- Preserve existing `/browse/` HTML behavior (no breaking changes).

## Scope
- **Base path:** `/weppcloud/runs/{runid}/{config}/files/`
- **Content type:** JSON only (`application/json`).
- **Auth:** JWT-authenticated access (no anonymous mode).

## Endpoints

### List directory contents
```
GET /weppcloud/runs/{runid}/{config}/files/
GET /weppcloud/runs/{runid}/{config}/files/{path:path}
```

Lists entries in a directory relative to the run config root.
If `{path}` resolves to a file, return HTTP 400 with `error.code="not_a_directory"`.

### Get metadata (file or directory)
```
GET /weppcloud/runs/{runid}/{config}/files/{path:path}?meta=true
```

Returns metadata for a single file or directory. No `entries` list is included.

## Query parameters
| Param | Type | Default | Description |
| --- | --- | --- | --- |
| `limit` | int | 1000 | Max entries to return (1..10000). |
| `offset` | int | 0 | Skip first N entries. |
| `pattern` | string | null | Glob filter on entry **name** (e.g., `*.parquet`, `p1.*`). |
| `sort` | string | `name` | Sort by `name`, `date`, or `size`. |
| `order` | string | `asc` | Sort order: `asc`, `desc`. |
| `meta` | bool | false | When true, return metadata for a single path. |

Notes:
- `pattern` uses glob matching on the entry basename (fnmatch semantics). Matching is case-sensitive (`fnmatchcase`) on Linux.
- `pattern` may include any fnmatch literals (including leading `-` or negated classes like `[!a]`); path separators and null bytes are rejected.
- `limit` must be 1..10000. Invalid values return HTTP 400 with a canonical error payload.
## Response format
- All keys are `lower_snake_case`.
- Timestamps are ISO 8601 UTC with `Z` suffix.
- `download_url` values are relative paths (clients build full URLs).

### List response (200)
```json
{
  "runid": "cardiac-existentialism",
  "config": "disturbed9002_wbt",
  "path": "wepp/output",
  "entries": [
    {
      "name": "loss.txt",
      "path": "wepp/output/loss.txt",
      "type": "file",
      "size_bytes": 12480,
      "modified_iso": "2026-01-31T14:22:00Z",
      "content_type": "text/plain",
      "download_url": "/weppcloud/runs/.../download/wepp/output/loss.txt"
    },
    {
      "name": "plots",
      "path": "wepp/output/plots",
      "type": "directory",
      "child_count": 42,
      "modified_iso": "2026-01-31T14:20:00Z"
    },
    {
      "name": "latest",
      "path": "wepp/output/latest",
      "type": "symlink",
      "symlink_target": "wepp/output/2026-01-31"
    }
  ],
  "total": 144,
  "limit": 1000,
  "offset": 0,
  "has_more": false,
  "cached": true
}
```

### Metadata response (200)
```json
{
  "runid": "cardiac-existentialism",
  "config": "disturbed9002_wbt",
  "name": "totalwatsed.parquet",
  "type": "file",
  "path": "wepp/output/totalwatsed.parquet",
  "size_bytes": 284672,
  "modified_iso": "2026-01-31T14:22:00Z",
  "content_type": "application/octet-stream",
  "download_url": "/weppcloud/runs/.../download/wepp/output/totalwatsed.parquet",
  "preview_available": true
}
```

## Entry fields
- **name** (string, required): Basename of the entry.
- **path** (string, required): Path relative to the run config root.
- **type** (string, required): `file`, `directory`, or `symlink`.
- **size_bytes** (int, optional): For files only.
- **modified_iso** (string, optional): Mtime in UTC.
- **content_type** (string, optional): MIME guess; fall back `application/octet-stream`.
- **download_url** (string, optional): Only for files.
- **child_count** (int, optional): For directories if available.
- **symlink_target** (string, optional): Only for symlinks; relative to run root when safe.
- **symlink_is_dir** (bool, optional): Only for symlinks; true when the target is a directory.
- **preview_available** (bool, optional): True when server can provide a safe preview.

## Path safety and normalization
- `{path}` is URL-decoded, normalized as a POSIX relative path, and **must** stay within the run config root.
- Requests that resolve outside the root (including `..` or absolute paths) return HTTP 400 with `error.code="path_outside_root"`.
- Symlinks are not traversed for listings. Symlinks are returned as `type="symlink"` entries.
- If a symlink target resolves outside the run root, `symlink_target` is omitted.
- Listings include dotfiles (excluding `.` and `..`).
- **Edge behavior:** some proxy/WAF layers may normalize dot segments or intercept traversal attempts before the API handler. In those cases, the response may be HTML (CAPTCHA or "Run Not Found") instead of the canonical JSON error. Agents should avoid traversal probes and treat non-JSON responses as upstream rejections.

## Sorting and pagination
- `total` counts entries **after** filters and **before** pagination.
- Pagination is stable for a given snapshot: apply a deterministic tie-breaker (`name`) when primary sort fields match.
- Sorting by `name` is case-insensitive; when names compare equal ignoring case, the original name is the final tie-breaker.
- Directories are listed before files.
## Error responses
Errors follow `docs/schemas/rq-response-contract.md`.
If an upstream proxy intercepts the request (for example, dot-segment traversal), the response may be non-JSON and not conform to the error schema.

### Examples
- **404 run not found**
```json
{
  "error": {
    "message": "Run 'nonexistent' not found",
    "code": "run_not_found",
    "details": "No run directory for runid=nonexistent"
  }
}
```

- **404 not found**
```json
{
  "error": {
    "message": "Directory 'wepp/invalid' does not exist",
    "code": "path_not_found",
    "details": "No entry at wepp/invalid"
  }
}
```

- **400 validation error**
```json
{
  "error": {
    "message": "Validation failed",
    "code": "validation_error",
    "details": "limit must be <= 10000"
  },
  "errors": [
    {
      "code": "invalid_value",
      "message": "limit must be <= 10000",
      "path": "limit"
    }
  ]
}
```

## Content negotiation
- `/files/` endpoints are JSON-only.
- If `Accept` does not include a JSON-capable media range with `q>0` (`application/json`, `application/*`, `*/*`, or `+json`), return HTTP 406 with a canonical error payload.
- Existing `/browse/` routes remain HTML-only and unchanged.

## Caching and manifest-backed runs
- When entries are served from the manifest cache, include `"cached": true` at the list response top level. Metadata responses are filesystem-based and omit the cached flag.
- Implementations may include `cache_source` and `cache_updated_iso` for additional transparency.

## Authentication
- `/files/` routes require authenticated JWT context and reject anonymous access.
- Accepted token classes are `user` and `service`.
- `session` tokens are not accepted on `/files/` endpoints.
- Tokens must pass run-authorization checks for the target run.
- Failures return HTTP `401`/`403` with canonical error payloads.

## Rate limits
- If rate limiting is enabled, return HTTP 429 with a canonical error payload.

## Download URL construction
- `download_url` must be the full relative path, including runid/config/path, so agents can use it directly.
- Do not emit placeholders or ellipses in production responses.

## Implementation checklist (browse-safe)
- [x] Implement `/files/` routes as new handlers (no changes to `/browse/` handlers/templates).
- [x] Add a shared path normalization helper for `/files/` only (reject `..`, absolute paths, and escapes outside run root).
- [x] Reuse `_manifest_get_page_entries()` / `get_page_entries()` without altering their behavior.
- [x] Shape JSON responses from existing entry dicts (no new discovery logic).
- [x] Emit canonical error payloads (`run_not_found`, `path_not_found`, `not_a_directory`, `validation_error`).
- [x] Add JSON-only content negotiation for `/files/` (return 406 when `Accept` excludes `application/json`).
- [x] Add tests for `/files/` list + meta success cases.
- [x] Add tests for invalid params, run not found, path escape, and symlink-outside-root behavior.
- [x] Assert `/browse/` HTML responses remain unchanged.
- [x] Document upstream proxy behavior when traversal attempts are intercepted before the handler.
