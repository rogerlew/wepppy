# Mini Work Package: rq-engine JWT implementation (Phase 6 auth)
Status: Complete
Last Updated: 2026-01-12
Primary Areas: `wepppy/microservices/rq_engine/*`, `wepppy/weppcloud/utils/auth_tokens.py`, `tools/wctl2/commands/*`, `docs/dev-notes/auth-token.spec.md`, `docs/culvert-at-risk-integration/*`

## Objective
Implement JWT auth for rq-engine (FastAPI) and align it with session-based access so controllers can rely on `/rq-engine/api/*`. Provide a semi-permanent JWT flow for Culvert_web_app, a host-side `wctl` command to mint tokens, and a first-class revocation path.

## Scope
- rq-engine JWT validation and scope enforcement on culvert ingestion + job polling routes.
- Shared token contract and scopes using the existing WEPP_AUTH_JWT configuration.
- Flask `/rq/api/*` routes removed; JWT enforcement lives in rq-engine.
- `wctl` command to mint JWTs from the host with configurable TTL and claims.
- Minimal docs refresh so new agents can find the JWT surface area quickly.

## Non-goals
- rq/api migration tracked separately (see `docs/mini-work-packages/20260112_rq_api_migration.md`).
- OAuth or user-facing login changes.
- Reworking existing agent JWT flows (AGENT_JWT_*).
- Full webhook implementation beyond Phase 6 planning notes (tracked but not delivered here).

## Current JWT inventory (for new agents)
- HMAC JWT utilities: `wepppy/weppcloud/utils/auth_tokens.py` + stub.
  - Env config: `WEPP_AUTH_JWT_*` (see `docs/dev-notes/auth-token.spec.md`).
  - CLI issuer: `wepppy/weppcloud/_scripts/issue_auth_token.py`.
  - Used by `wepppy/weppcloud/routes/command_bar/command_bar.py` to mint Query Engine MCP tokens.
- Query Engine MCP auth: `wepppy/query_engine/app/mcp/auth.py` (separate env prefix `WEPP_MCP_JWT_*`; compose wires `WEPP_MCP_JWT_SECRET` from `WEPP_AUTH_JWT_SECRET`).
- Agent JWTs (Flask-JWT-Extended): `wepppy/weppcloud/utils/agent_auth.py`, `wepppy/weppcloud/routes/agent.py`, `wepppy/mcp/base.py` (AGENT_JWT_* env vars).
- Docker defaults: `docker/docker-compose.dev.yml`, `docker/docker-compose.prod.yml` define `WEPP_AUTH_JWT_SECRET` and propagate to query-engine.
- Tests: `tests/weppcloud/test_auth_tokens.py`, `tests/query_engine/test_mcp_auth.py`.
- No rq-engine auth yet: `wepppy/microservices/rq_engine/*` has no JWT enforcement.

## Token model (proposed)
- Issuer/validation: reuse `WEPP_AUTH_JWT_*` config and `auth_tokens.decode_token`.
- Audience: require `aud` includes `rq-engine` (or `wepp-services` if we choose a shared audience).
- Required claims: `sub`, `iat`, `exp`, `scope`, `aud` (plus `iss` if configured).
- Optional claims:
  - `runs`: list of run IDs for run-scoped RQ endpoints.
  - `culvert_batches`: list of batch UUIDs for culvert batch polling.
  - `session_id`: optional session identifier for anonymous session tokens.
  - `token_class`: `user|service|session` to simplify downstream policy checks.
  - `jti`: token ID (future revocation/rotation hooks).
- Scope set (initial):
  - `rq:status` - poll jobstatus/jobinfo.
  - `rq:enqueue` - enqueue jobs outside culvert flow (future).
  - `culvert:batch:submit` - POST `/culverts-wepp-batch/`.
  - `culvert:batch:retry` - POST `/culverts-wepp-batch/{batch}/retry/{point_id}`.
  - `culvert:batch:read` - read batch/job metadata.

### Token classes (new requirement)
- **User token**
  - Claims: `sub` (user id), `roles` (list), `groups` (list), optional `email`.
  - Authorization: rq-engine should resolve user roles/groups against the same logic as Flask (run ownership, Admin role, public run).
  - Avoid embedding full run lists (too long); use live checks against user/run metadata.
- **Service token**
  - Claims: `sub` (service id), `service_groups` (list), optional `env`/`purpose`.
  - Authorization: map `service_groups` to scope bundles (for example `culverts` grants culvert-specific scopes).
  - Use for Culvert_web_app and other service-to-service clients.
- **Session token (anonymous runs)**
  - Claims: `sub` (session id), `runid` (single run), `session_id`, `token_class="session"`.
  - Authorization: rq-engine allows run-scoped endpoints only when token matches `runid` and (optionally) the session is still active in Redis.
  - TTL: short-lived (15-60 minutes) and refreshable; `jti` required for revocation.

### Revocation and rotation (required)
- Require `jti` on issued tokens and validate against a denylist.
- Store revoked `jti` values in Redis DB 0 or 13 with TTL matching `exp`.
- Add rotation hooks (multiple secrets, or a primary + secondary secret list) so issued tokens can be rotated without downtime.
- Provide a minimal admin CLI to revoke a token by `jti` (or subject + issued-at window).

## Plan
### Phase 1 - Spec alignment + docs
- Extend `docs/dev-notes/auth-token.spec.md` with:
  - Token classes (user vs service), `service_groups` claim.
  - Revocation/rotation requirements (jti + denylist + TTL).
  - rq-engine scopes and audience guidance.
- Confirm the canonical error payloads follow `docs/schemas/rq-response-contract.md` (complete).

### Phase 2 - Shared rq-engine auth helpers
- Add `wepppy/microservices/rq_engine/auth.py`:
  - Parse Authorization header (Bearer token).
  - Validate token with `auth_tokens.decode_token` and enforce `aud`, `iss`, and scopes.
  - Resolve token class (user vs service) and normalize claims.
  - Helper functions: `require_scope`, `require_run_claim`, `require_culvert_batch_claim`.
  - Configurable auth mode: `RQ_ENGINE_AUTH_MODE=required|optional|disabled`.
- Keep helpers thin and avoid fallback wrappers that mask config errors.

### Phase 3 - Enforce JWT on rq-engine routes
- Apply dependencies in `wepppy/microservices/rq_engine/culvert_routes.py` and `job_routes.py`.
- Requirements:
  - `culverts-wepp-batch/`: `culvert:batch:submit`
  - `culverts-wepp-batch/{batch}/retry/{point_id}`: `culvert:batch:retry`
  - `canceljob`: secure with `rq:status` (or a new `rq:cancel` scope if desired).
- Explicitly leave `jobstatus/jobinfo` unsecured (read-only polling for agents).
- Batch/job claim checks:
  - Use job meta `culvert_batch_uuid` (already stored) to validate `culvert_batches` claim.
  - For run-scoped jobs, compare `job.meta["runid"]` to `runs` claim or allow if claim missing and auth mode is optional.
- Error responses must use rq response contract (`error`/`errors` keys).
 - Add `POST /rq-engine/api/canceljob/{job_id}` (parity with Flask, but secured).

### Phase 4 - Flask `/rq/api/*` removal (completed)
- Flask `/rq/api/*` endpoints were removed instead of retrofitting JWT helpers.
- All queue-triggering routes now live in rq-engine, which enforces JWT claims directly.
- Legacy `rq_auth.py` helpers were dropped along with the Flask routes.

**Completed now:**
- `POST /rq-engine/api/runs/<runid>/<config>/session-token` issues a session JWT and sets the Redis marker.
- Job dashboard cancel now uses `/rq-engine/api/canceljob` with a session token.
- rq-engine culvert ingestion/retry routes now require JWT scopes (`culvert:batch:submit`, `culvert:batch:retry`).
- Flask `/rq/api/*` routes removed; controllers now target rq-engine endpoints only.

### Phase 5 - wctl token minting command
- Add a Typer command in `tools/wctl2/commands/` (new `auth.py` or extend `python_tasks.py`):
  - `wctl issue-auth-token <subject> --scope ... --runs ... --audience ... --expires-in ... --claim key=value --json`
  - Runs `python -m wepppy.weppcloud._scripts.issue_auth_token` inside the `weppcloud` container so `WEPP_AUTH_JWT_*` config is available.
  - `--expires-in` supports semi-permanent culvert tokens (example: 90-180 days).
- Document in `wctl/README.md` with culvert-focused examples.

**Completed now:**
- `wctl issue-auth-token` added (wrapper for `wepppy/weppcloud/_scripts/issue_auth_token.py`).
- `wctl/README.md` updated with the auth token command example.

### Phase 6 - Revocation workflow + admin tooling
- Add a simple revocation CLI:
  - `wctl revoke-auth-token --jti <id>` (or `--subject <sub> --since <ts>`).
  - Stores revoked entries in Redis with TTL (exp - now).
- Add auth middleware checks for `jti` denylist in rq-engine and Flask helpers.
- Document rotation playbook (dual secrets or `WEPP_AUTH_JWT_SECRETS` list).
- Add a culvert JWT note to `docs/culvert-at-risk-integration/dev-package/README.md` (Bearer token, scopes, TTL guidance).

**Completed now:**
- `wctl revoke-auth-token` added (wrapper for `wepppy/weppcloud/_scripts/revoke_auth_token.py`).
- Revocation entries stored in Redis DB 0 (`auth:jwt:revoked:<jti>`) with TTL.
- rq-engine checks the denylist during JWT validation.
- Rotation playbook added to `docs/dev-notes/auth-token.spec.md`.

**Still pending:** none.

### Phase 7 - Webhook follow-on (tracked here, implemented later)
- Decide webhook registration surface (payload field vs `/rq-engine/api/webhooks`).
- Define payload schema + HMAC header (e.g., `X-WEPP-Signature`, `X-WEPP-Timestamp`, `X-WEPP-Event`).
- Store webhook config in `batch_metadata.json` or `culverts_runner.nodb`.
- Implement retry policy (exponential backoff, max attempts, final failure logged to batch root).
- Add tests with a mock HTTP endpoint and verify HMAC signatures.

## Culvert_app semi-permanent JWT guidance (MVP)
- Mint a service token scoped to `aud=rq-engine` with:
  - `scope=culvert:batch:submit culvert:batch:retry rq:status culvert:batch:read`
  - `sub=culvert-app` (or service identifier)
  - `service_groups=["culverts"]`
  - `jti=<uuid>` (required for revocation)
  - `expires-in` long TTL (target 90-180 days, confirm with security).
- Store in Culvert_web_app config and rotate when the TTL window elapses.

## Verification checklist
- rq-engine rejects missing/invalid tokens when `RQ_ENGINE_AUTH_MODE=required`.
- jobstatus/jobinfo remain read-only and open (no token required).
- culvert ingestion enforces `culvert:batch:submit`.
- Flask `/rq/api/*` is removed; session access is handled via rq-engine session tokens.
- revocation denylist blocks revoked `jti` values.
- `wctl issue-auth-token --json` prints token + claims and respects `--expires-in`.
- Tests added for rq-engine auth dependency + basic token validation paths.

## Open questions
- TTL for the culvert service token (90 vs 180 days) and rotation cadence.
- Should rq-engine use `aud=rq-engine` or a shared `aud=wepp-services`?
- Do we need multi-secret validation to support rotation (e.g., `WEPP_AUTH_JWT_SECRETS`)?
- Should anonymous jobstatus/jobinfo remain allowed in optional mode, or require tokens everywhere?
- Where should user-token authorization live for rq-engine (shared database access vs a thin authz service)?
