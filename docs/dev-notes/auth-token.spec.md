# WEPPcloud JWT and Auth Contracts

This document is the authoritative contract for WEPPcloud JWTs, including token
classes, required claims, and validation expectations. Response payloads and
error shapes must follow `docs/schemas/rq-response-contract.md`. Browser/session
lifecycle behavior must follow `docs/schemas/weppcloud-session-contract.md`.
CSRF policy must follow `docs/schemas/weppcloud-csrf-contract.md`.

## Normative status (strict and authoritative)
- This specification is normative, strict, and authoritative for JWT/auth behavior.
- Statements using MUST, MUST NOT, SHOULD, and MAY are to be interpreted as
  RFC 2119 requirement levels.
- This document is not aspirational and does not define a future-state wishlist.
- If implementation and this spec diverge, treat it as a defect:
  - Fix the implementation to match this contract, or
  - Update this contract in the same change when behavior is intentionally
    changed.

## Scope
- Applies to rq-engine, query-engine MCP, and service-to-service tokens.
- Defines required claims, token classes, audience usage, and revocation rules.
- Non-auth payload schemas live in their own contracts (see `docs/schemas/rq-response-contract.md`).

## Environment configuration

The token issuer (and any service that validates tokens) relies on the
following environment variables:

| Variable | Description | Default |
| --- | --- | --- |
| `WEPP_AUTH_JWT_SECRET` | **Required.** Shared HMAC secret. | – |
| `WEPP_AUTH_JWT_ALGORITHMS` | Comma separated list of allowed algorithms (`HS256`, `HS384`, `HS512`). | `HS256` |
| `WEPP_AUTH_JWT_ISSUER` | Optional issuer string (`iss` claim). | unset |
| `WEPP_AUTH_JWT_DEFAULT_AUDIENCE` | Optional audience automatically included in tokens. | unset |
| `WEPP_AUTH_JWT_DEFAULT_TTL_SECONDS` | Default lifetime for issued tokens. | `3600` |
| `WEPP_AUTH_JWT_SCOPE_SEPARATOR` | String used to join scope values. | single space |
| `WEPP_AUTH_JWT_LEEWAY` | Validation leeway in seconds for `exp`, `nbf`, `iat`. | `0` |
| `WEPP_AUTH_JWT_SECRETS` | Optional comma-delimited list of secrets for rotation (first is active; overrides `WEPP_AUTH_JWT_SECRET`). | unset |
| `RQ_ENGINE_JWT_AUDIENCE` | Override rq-engine audience enforcement. | `rq-engine` |

## Token classes

### User token
- `token_class=user`
- Required claims: `sub`, `roles`, `groups`, `aud`, `scope`, `iat`, `exp`, `jti`.
- Authorization: use server-side run ownership and role checks; do not embed full run lists.
- Role policy:
  - Minting is restricted to callers with at least one role in `Admin`, `PowerUser`, `Dev`, `Root`.
  - Browse group routes (`/culverts/{uuid}/...`, `/batch/{batch_name}/...`) require
    user tokens to include at least one role in `admin`, `poweruser`, `dev`, `root`
    (case-insensitive match).

### Service token
- `token_class=service`
- Required claims: `sub`, `service_groups`, `aud`, `scope`, `iat`, `exp`, `jti`.
- Authorization: map `service_groups` to scope bundles (for example `culverts`).

### Culvert browse/download service token
- Token source: `POST /rq-engine/api/culverts-wepp-batch/` and
  `POST /rq-engine/api/culverts-wepp-batch/{batch_uuid}/retry/{point_id}` and
  `POST /rq-engine/api/culverts-wepp-batch/{batch_uuid}/finalize`.
- Response fields: `browse_token` and `browse_token_expires_at` (`exp`, Unix
  timestamp seconds).
- Claim contract for `browse_token`:
  - `token_class` MUST be `service`.
  - `aud` MUST include `rq-engine`.
  - `runs` MUST include exactly the submitted `culvert_batch_uuid` scope.
  - `service_groups` MUST include `culverts`.
  - `jti` MUST be present (revocation checks are mandatory).
- Access contract:
  - Bearer usage: `Authorization: Bearer <browse_token>`.
  - Browse: `/weppcloud/culverts/{batch_uuid}/browse/...`
  - Download: `/weppcloud/culverts/{batch_uuid}/download/{subpath}`
  - Batch archive path (current MVP): `/weppcloud/culverts/{batch_uuid}/download/weppcloud_run_skeletons.zip`
  - Cross-batch use (`runs` scope mismatch) MUST return `403`.

### Session token (anonymous runs)
- `token_class=session`
- Required claims: `sub` (session id), `runid`, `session_id`, `aud`, `scope`, `iat`, `exp`, `jti`.
- Optional authenticated-session claims: `user_id` (int), `roles` (`list[str]`).
- Authorization: run-scoped access only, optionally validated against the active session store.

### MCP token (query-engine)
- `token_class=mcp`
- Preferred issued shape (WEPPcloud): include `token_class=mcp`, `sub`,
  `scope`, `jti`, `iat`, `exp`, and `runs`.
- Enforced by query-engine MCP middleware:
  - `sub` is required.
  - `jti` is required (revocation denylist check).
  - `exp`/`iat`/`nbf` are validated when present.
  - `runs` is required for run-scoped endpoints (`/mcp/runs/{runid}/...`).
  - `token_class` MUST be `mcp`.
- Audience contract:
  - When `WEPP_MCP_JWT_AUDIENCE` is configured, tokens MUST include that
    audience value (recommended: `query-engine`).
  - When `WEPP_MCP_JWT_AUDIENCE` is unset, audience checks are not enforced.
- Validation: query-engine MCP uses `WEPP_MCP_JWT_*` config; secrets are wired
  from `WEPP_AUTH_JWT_SECRET`.

## Policy defaults
- **Audience**:
  - rq-engine tokens: `aud=rq-engine` (default enforcement via
    `RQ_ENGINE_JWT_AUDIENCE`).
  - MCP tokens: `aud=<WEPP_MCP_JWT_AUDIENCE>` when configured (recommended
    `query-engine`).
  - Multi-service tokens: use an `aud` list and require intersection on each service.
- **TTL contracts** (set via config or explicit `expires_in`):
  - Profile-issued user tokens: fixed 90 days (`7776000` seconds).
  - Session tokens: fixed 4 days (`345600` seconds).
  - Command-bar-issued MCP tokens: uses `WEPP_AUTH_JWT_DEFAULT_TTL_SECONDS`
    unless an explicit `expires_in` is added.
  - Service-token TTLs are endpoint-specific.

## Claims

Issued tokens contain the following fields:

- `sub` – Subject (user/service/session identifier).
- `token_class` – `user|service|session|mcp`.
- `scope` – Space-separated list of scopes (e.g. `runs:read queries:execute`).
- `aud` – Audience string or list. Defaults to `WEPP_AUTH_JWT_DEFAULT_AUDIENCE`.
- `iss`, `iat`, `exp`, `nbf` – Standard JWT time/issuer claims.
- `jti` – Token identifier required for revocation checks.
- `runs` – Optional list of run identifiers (service tokens only; avoid on user tokens).
- `runid` – Single run identifier (session tokens only).
- `roles`, `groups` – User token claims.
- `service_groups` – Service token claim.
- `session_id` – Session token claim.
- `user_id`, `roles` – Optional authenticated session-token claims.
- Additional custom claims are preserved verbatim.

Downstream services should verify signatures using
`WEPP_AUTH_JWT_SECRET` and ensure the audience and scopes are
appropriate for the requested operation.

## RQ job auth actor metadata
rq-engine tags enqueued RQ jobs with a sanitized auth actor payload stored in
`job.meta["auth_actor"]` so jobinfo/jobstatus tooling can identify who or what
started a job without exposing JWTs or email.

Schema (optional):
```json
{
  "token_class": "user|session|service|mcp",
  "user_id": 123,
  "session_id": "session-abc",
  "sub": "service-name",
  "service_groups": ["culverts"]
}
```

Rules:
- `token_class=user` uses `user_id` only; `sub` must parse as int or the actor is omitted.
- `token_class=session` uses `session_id` from `session_id` or `sub`.
- `token_class=service` uses `sub` and optional `service_groups`.
- `token_class=mcp` uses `sub` only.
- Never store JWTs, email, or Authorization headers in job metadata.

## Token issuance utility

The script `_scripts/issue_auth_token.py` issues tokens from the CLI:

```bash
python -m wepppy.weppcloud._scripts.issue_auth_token user123 \
  --scope runs:read --scope queries:execute \
  --runs run-1,run-2 --audience query-engine --expires-in 900 \
  --json
```

Environment variables above must be set before running the script. The
`--json` flag prints both the token and the resolved claims, which is
handy for auditing.

## Validation

Token validation utilities live in `wepppy/weppcloud/utils/auth_tokens.py`.
They expose `decode_token` and reuse the shared configuration so
services can enforce identical requirements (issuer/audience/leeway).

For Python callers:

```python
from wepppy.weppcloud.utils.auth_tokens import decode_token

claims = decode_token(token, audience="query-engine")
```

If validation fails a `JWTDecodeError` is raised.

## Session token issuance
- Preferred endpoint: `POST /rq-engine/api/runs/<runid>/<config>/session-token`
- Additional minting path: Flask run bootstrap path
  (`runs0_nocfg`, `wepppy/weppcloud/routes/run_0/run_0_bp.py`) sets the same
  run-scoped browse JWT cookie when rendering run pages.
- Behavior:
  - Requires run authorization (public or owner).
  - Issues a session JWT (`token_class=session`) scoped to the run.
  - If a Flask login session is present, includes `user_id` and `roles` claims from Redis-backed session data.
  - Default session scopes: `rq:status`, `rq:enqueue`, `rq:export`.
  - Stores a Redis marker `auth:session:run:<runid>:<session_id>` (DB 11) with TTL.
  - Sets an HttpOnly cookie (default key `wepp_browse_jwt`, configurable via
    `WEPP_BROWSE_JWT_COOKIE_NAME`) with path/key scoping rules:
    - Non-composite runids: cookie key `wepp_browse_jwt`; path `/weppcloud/runs/<runid>/<config>/`.
    - Composite runids (contains `;`): cookie key `wepp_browse_jwt_<sha256(runid + "\\n" + config)[:16]>`; path `/weppcloud/runs/`.
    - Validators SHOULD check the derived composite key first, then the legacy base key for backward compatibility.
    - Implementations MUST NOT rely on `/runs/<runid>/<config>/` cookie paths for composite runids; encoded semicolons in `Path` can cause browser mismatches and redirect loops on browse routes.
  - Cookie `Secure` behavior defaults to request/proxy scheme and can be
    overridden with `WEPP_AUTH_SESSION_COOKIE_SECURE`.
  - Cookie `SameSite` is controlled by `WEPP_AUTH_SESSION_COOKIE_SAMESITE`
    (`lax` default).

## UI token renewal (transparent)
- Endpoint: `POST /weppcloud/api/auth/rq-engine-token`
- Purpose: allow browser clients to recover from stale/invalid run-scoped
  session-token minting without forcing logout/login.
- Caller requirements:
  - Existing authenticated WEPPcloud login session (`current_user` not anonymous).
  - Same-origin request with CSRF protection as defined in `docs/schemas/weppcloud-csrf-contract.md`.
- Issued token shape:
  - `token_class=user`
  - `aud=rq-engine`
  - scopes: `rq:enqueue`, `rq:status`, `rq:export`
  - user claims: `email`, `roles`, `jti`, plus standard JWT claims.
- Response:
  - Success: `200` with `{ "token": "<jwt>" }`
  - Anonymous caller: `401` canonical error payload (`Authentication required.`)
  - JWT config failure: `500` canonical error payload.

### Browser renewal sequence
- `WCHttp.getSessionToken(runid, config)` first calls
  `POST /rq-engine/api/runs/<runid>/<config>/session-token`.
- If that call returns `401` or `403`, client automatically calls
  `POST /weppcloud/api/auth/rq-engine-token`.
- The fallback token is cached client-side (short-lived cache, ~10 minutes when
  `exp` is not provided) and used for the pending request.
- `WCHttp.requestWithSessionToken(...)` retries the original rq-engine call with
  `Authorization: Bearer <fallback-token>`.
- Renewal is transparent to users; manual logout/login is not a required recovery path.

## Profile token issuance
- Endpoint: `POST /profile/mint-token` (Flask route, authenticated user required).
- Behavior:
  - Caller must have at least one role in `Admin`, `PowerUser`, `Dev`, `Root`; others receive `403`.
  - Issues a user JWT (`token_class=user`) with subject set to the current user ID.
  - Includes user claims: `email`, `roles`, `groups` (current role names from the caller session/user record).
  - Sets audiences to `rq-engine` and `query-engine`.
  - Sets scopes to `runs:read`, `queries:validate`, `queries:execute`, `rq:status`, `rq:enqueue`, `rq:export`.
  - Uses a fixed TTL of 90 days (`7776000` seconds).

## Revocation and rotation
- Services MUST enforce `jti` denylist checks.
- Revoked `jti` values live in Redis with TTL matching `exp`.
- Rotation uses `WEPP_AUTH_JWT_SECRETS` (first is active, remainder accepted for validation).

### Revocation storage (recommended)
- Redis DB: `RedisDB.LOCK` (0) with a dedicated prefix.
- Key format: `auth:jwt:revoked:<jti>`
- Value: JSON `{sub, token_class, revoked_at, exp, reason}` (for audit).
- TTL: `exp - now + leeway` (minimum 1 hour).

### Session validation (anonymous runs)
- Issue session JWTs from weppcloud and store a Redis marker:
  - Redis DB: `RedisDB.SESSION` (11).
  - Key format: `auth:session:run:<runid>:<session_id>`.
  - TTL: 4 days; refresh on activity when practical.
- rq-engine validates the JWT and requires the Redis marker to exist (fail closed).

### Rotation playbook
1. Generate a new secret and prepend it to `WEPP_AUTH_JWT_SECRETS`, keeping prior secrets after it.
2. Deploy the updated env to all services that issue or validate JWTs.
3. Re-issue long-lived service tokens (culvert, MCP) so they use the new active secret.
4. Wait out the longest token TTL (or revoke known `jti` values early).
5. Remove the retired secrets from `WEPP_AUTH_JWT_SECRETS` once no active tokens use them.

## Bootstrap scopes (2026-02-08)
- rq-engine Bootstrap endpoints use operation-specific scopes:
  - `bootstrap:enable`
  - `bootstrap:token:mint`
  - `bootstrap:read`
  - `bootstrap:checkout`
- `rq:enqueue` is not accepted as a substitute for Bootstrap operations.

## Polling endpoint auth modes (rq-engine)
- Applies to:
  - `GET /rq-engine/api/jobstatus/{job_id}`
  - `GET /rq-engine/api/jobinfo/{job_id}`
  - `POST /rq-engine/api/jobinfo`
- Mode switch:
  - `RQ_ENGINE_POLL_AUTH_MODE=open` (default, backward compatible)
  - `RQ_ENGINE_POLL_AUTH_MODE=token_optional` (validate JWT when present)
  - `RQ_ENGINE_POLL_AUTH_MODE=required` (JWT + `rq:status` required)
- Current policy sets `open` in dev/test/prod until deployment requirements
  change.
- Operational hardening:
  - In-process rate limiting per endpoint/caller/IP.
  - Audit logging includes endpoint, status, success/failure, job id, caller,
    and client IP.
- Rate limit defaults:
  - `RQ_ENGINE_POLL_RATE_LIMIT_COUNT=400`
  - `RQ_ENGINE_POLL_RATE_LIMIT_WINDOW_SECONDS=60`

## Service scopes

| Scope | Purpose |
| --- | --- |
| `runs:read` | List or fetch metadata about accessible runs. |
| `queries:validate` | Validate payloads against dataset schema. |
| `queries:execute` | Execute queries (POST to `/query`). |
| `runs:activate` | Trigger query-engine catalog activation via MCP. |
| `rq:status` | Poll job status/info and cancel jobs. |
| `rq:enqueue` | Submit run-scoped RQ jobs. |
| `rq:export` | Request rq-engine export artifacts. |
| `bootstrap:enable` | Enqueue Bootstrap enable for eligible runs. |
| `bootstrap:token:mint` | Mint Bootstrap git access token URLs. |
| `bootstrap:read` | Read Bootstrap commit history and current ref metadata. |
| `bootstrap:checkout` | Checkout a Bootstrap commit under run lock. |
| `culvert:batch:submit` | Submit culvert batch payloads; also accepted for `/api/canceljob/{job_id}`. |
| `culvert:batch:retry` | Retry culvert runs and enqueue batch finalizers. |
| `culvert:batch:read` | Read culvert batch/job metadata. |

Scopes are additive; downstream services should check presence before
performing an operation.
