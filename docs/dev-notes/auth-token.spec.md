# WEPPcloud JWT and Auth Contracts

This document is the authoritative contract for WEPPcloud JWTs, including token
classes, required claims, and validation expectations. Response payloads and
error shapes must follow `docs/schemas/rq-response-contract.md`.

## Scope
- Applies to rq-engine, query-engine MCP, and service-to-service tokens.
- Defines required claims, token classes, audience usage, and revocation rules.
- Non-auth payload schemas live in their own contracts (see `docs/schemas/rq-response-contract.md`).

## Implementation status (2026-02-08)
- **Implemented**
  - `auth_tokens` HMAC JWT utilities (`wepppy/weppcloud/utils/auth_tokens.py`).
  - Query-engine MCP JWT validation (`wepppy/query_engine/app/mcp/auth.py`).
  - CLI token issuance script (`wepppy/weppcloud/_scripts/issue_auth_token.py`).
  - CLI token revocation script (`wepppy/weppcloud/_scripts/revoke_auth_token.py`).
  - `wctl issue-auth-token` / `wctl revoke-auth-token` wrappers (`tools/wctl2/commands/auth.py`).
  - Session JWT issuance endpoint (`/rq-engine/api/runs/<runid>/<config>/session-token`).
  - Session-token endpoint sets an HttpOnly browse cookie scoped to `/weppcloud/runs/<runid>/<config>/`.
  - Profile JWT issuance endpoint (`POST /profile/mint-token`) for authenticated users.
  - rq-engine JWT enforcement on `canceljob` and culvert batch submit/retry routes (includes jti denylist).
  - Flask `/rq/api/*` routes removed; rq-engine owns queue-triggering endpoints.
  - Secret rotation via `WEPP_AUTH_JWT_SECRETS` (multiple validation secrets).
- **In progress / planned**
  - Rotation playbook rollout communication.

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

### Service token
- `token_class=service`
- Required claims: `sub`, `service_groups`, `aud`, `scope`, `iat`, `exp`, `jti`.
- Authorization: map `service_groups` to scope bundles (for example `culverts`).

### Session token (anonymous runs)
- `token_class=session`
- Required claims: `sub` (session id), `runid`, `session_id`, `aud`, `scope`, `iat`, `exp`, `jti`.
- Optional authenticated-session claims: `user_id` (int), `roles` (`list[str]`).
- Authorization: run-scoped access only, optionally validated against the active session store.

### MCP token (query-engine)
- `token_class=mcp`
- Required claims: `sub`, `aud=query-engine`, `scope`, `iat`, `exp`, `jti`.
- Validation: query-engine MCP uses `WEPP_MCP_JWT_*` config; secrets are wired from `WEPP_AUTH_JWT_SECRET`.

## Policy defaults
- **Audience**:
  - rq-engine tokens: `aud=rq-engine`.
  - MCP tokens: `aud=query-engine`.
  - Multi-service tokens: use an `aud` list and require intersection on each service.
- **TTL targets** (set via config or explicit `expires_in`):
  - User tokens: 4 days (345600s).
  - Profile-issued user tokens: 90 days (7776000s).
  - Session tokens: 4 days (345600s).
  - Service tokens: variable; culvert target 90 days (7776000s).
  - MCP tokens: 60 days (5184000s).
- Recommended: set `WEPP_AUTH_JWT_DEFAULT_TTL_SECONDS=345600` for user/session tokens; pass explicit `expires_in` for service and MCP tokens.

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
- Legacy endpoint (Flask): removed; session tokens are issued by rq-engine only.
- Behavior:
  - Requires run authorization (public or owner).
  - Issues a session JWT (`token_class=session`) scoped to the run.
  - If a Flask login session is present, includes `user_id` and `roles` claims from Redis-backed session data.
  - Default session scopes: `rq:status`, `rq:enqueue`, `rq:export`.
  - Stores a Redis marker `auth:session:run:<runid>:<session_id>` (DB 11) with TTL.
  - Sets an HttpOnly cookie (default key `wepp_browse_jwt`, configurable via `WEPP_BROWSE_JWT_COOKIE_NAME`) scoped to `/weppcloud/runs/<runid>/<config>/`.

## Profile token issuance
- Endpoint: `POST /profile/mint-token` (Flask route, authenticated user required).
- Behavior:
  - Issues a user JWT (`token_class=user`) with subject set to the current user ID.
  - Includes user claims: `email`, `roles`, `groups`.
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
  - `RQ_ENGINE_POLL_RATE_LIMIT_COUNT=120`
  - `RQ_ENGINE_POLL_RATE_LIMIT_WINDOW_SECONDS=60`

## Service scopes

| Scope | Purpose |
| --- | --- |
| `runs:read` | List or fetch metadata about accessible runs. |
| `queries:validate` | Validate payloads against dataset schema. |
| `queries:execute` | Execute queries (POST to `/query`). |
| `rq:status` | Poll job status/info. |
| `rq:enqueue` | Submit RQ jobs (future). |
| `rq:export` | Request rq-engine export artifacts. |
| `bootstrap:enable` | Enqueue Bootstrap enable for eligible runs. |
| `bootstrap:token:mint` | Mint Bootstrap git access token URLs. |
| `bootstrap:read` | Read Bootstrap commit history and current ref metadata. |
| `bootstrap:checkout` | Checkout a Bootstrap commit under run lock. |
| `culvert:batch:submit` | Submit culvert batch payloads. |
| `culvert:batch:retry` | Retry culvert runs. |
| `culvert:batch:read` | Read culvert batch/job metadata. |

Scopes are additive; downstream services should check presence before
performing an operation.
