# RQ-Engine Agent API Contract
> Canonical contract for agent clients using the WEPPcloud rq-engine.
> **Status:** Canonical path under `docs/schemas/` as of 2026-04-10 (moved from `docs/dev-notes/`).
> **Operator usability note (2026-04-11):** API-operator hardening for non-browser token bootstrap and smoke reliability shipped in `docs/work-packages/20260411_rq_operator_experience_hardening/`.
> **See also:** `docs/schemas/rq-response-contract.md`, `docs/dev-notes/auth-token.spec.md`, `docs/schemas/weppcloud-csrf-contract.md`, `docs/dev-notes/correlation-id-debugging.md`, `docs/schemas/rq-controller-state-contract.md`, `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`, and user-facing `wepppy/weppcloud/routes/usersum/weppcloud/rq-engine.md`.

## Purpose
This document defines how agents should call rq-engine safely and predictably.
It is the developer-facing contract for auth, scopes, response semantics, job
lifecycle polling, and route ownership.

## Canonical Surface
- Service: `wepppy/microservices/rq_engine/` (FastAPI).
- Direct app paths use `/api/...` (for example `/api/jobstatus/{job_id}`).
- Via WEPPcloud reverse proxy, endpoints are under `/rq-engine/api/...`.
- OpenAPI:
  - Direct service: `/openapi.json`
  - Proxied: `/rq-engine/openapi.json`
- Stable OpenAPI operation IDs use the `rq_engine_` prefix.

Route ownership and freeze artifacts:
- Frozen endpoint inventory:
  `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
- Route contract checklist:
  `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`
- Drift guards:
  - `tools/check_endpoint_inventory.py`
  - `tools/check_route_contract_checklist.py`

## Auth Model
Accepted token classes follow `docs/dev-notes/auth-token.spec.md`:
- `user`
- `session`
- `service`
- `mcp` (where route scope/claims allow)

Run-scoped routes enforce run access in addition to scope checks:
- User tokens: owner/public-run checks.
- Session tokens: Redis session marker validation for run scope.
- Service/MCP tokens: run claims must permit the target run.

### Polling Auth Modes
Polling routes:
- `GET /api/jobstatus/{job_id}`
- `GET /api/jobinfo/{job_id}`
- `POST /api/jobinfo`

Mode switch via `RQ_ENGINE_POLL_AUTH_MODE`:
- `open` (default) - no token required.
- `token_optional` - validate JWT when bearer token is sent.
- `required` - bearer token required; must include `rq:status`.

Polling hardening:
- In-memory rate limiter (`endpoint + caller + ip`).
- Default limit: `400` requests per `60` seconds.
- Env vars:
  - `RQ_ENGINE_POLL_RATE_LIMIT_COUNT`
  - `RQ_ENGINE_POLL_RATE_LIMIT_WINDOW_SECONDS`

## Scope Contract
Core scopes used by agent-facing routes:

| Scope | Used for |
|---|---|
| `rq:status` | Job polling (`jobstatus`, `jobinfo`) and `canceljob`; also bearer path for session-token issuance and setup-discovery compatibility (`/api/configs`, `/api/endpoints*`). |
| `rq:read` | Read-only setup/controller-state metadata surfaces (`/api/configs`, `/api/endpoints*`, `/api/runs/{runid}/{config}/pipeline`, `/api/runs/{runid}/{config}/readiness`, `/api/runs/{runid}/{config}/controllers*`, `/api/runs/{runid}/{config}/endpoints*`, `/api/runs/{runid}/{config}/geospatial-metadata`, `/api/runs/{runid}/{config}/outputs`). |
| `rq:enqueue` | Most run mutations that enqueue background jobs or perform run mutations under rq-engine routes. |
| `rq:export` | Export artifact endpoints under `/runs/{runid}/{config}/export/*`. |
| `bootstrap:enable` | Bootstrap enable endpoint. |
| `bootstrap:token:mint` | Bootstrap token mint endpoint. |
| `bootstrap:read` | Bootstrap read endpoints (`commits`, `current-ref`). |
| `bootstrap:checkout` | Bootstrap checkout endpoint. |
| `culvert:batch:submit` | Culvert batch submit endpoint; also accepted for `/api/canceljob/{job_id}`. |
| `culvert:batch:retry` | Culvert batch retry endpoint. |

Bootstrap routes do not accept `rq:enqueue` as a substitute for `bootstrap:*`.
- Controller-state cutover package
  `20260410_rq_controller_state_contract_cutover` closed on 2026-04-11 with
  auth-scope parity evidence and keeps `rq:status` + `rq:read` compatibility
  for read-only controller-state routes in the frozen baseline.
- `rq:status` compatibility is bounded to read-only controller-state endpoints
  and MUST NOT broaden access to mutation/export/admin/bootstrap-control
  endpoint families.
- Explicit cutover policy decision: session-token minting continues to accept
  bearer `rq:status` and mint broader run-scoped session scopes for
  compatibility. Treat this as an accepted residual/design risk until a
  follow-on policy package updates route + descriptor + contract together.

## Response Contract
rq-engine responses must follow `docs/schemas/rq-response-contract.md`.

Submission/command responses:
- Async submit commonly returns `job_id` and `status_url`.
- Async status codes vary by endpoint contract (`200` or `202`); treat
  `job_id`/`job_ids` as the canonical async signal.
- Sync operations return `message` and optional `result`.
- Keys use `lower_snake_case`.

Polling responses:
- `jobstatus`: `{job_id, runid, status, started_at, ended_at}`
- `jobinfo`: `{job_id, runid, status, result, started_at, ended_at, description, elapsed_s, exc_info, children, auth_actor?}`
- Canonical `status` values in successful polling payloads:
  - non-terminal: `queued`, `started`, `deferred`, `scheduled`
  - terminal success: `finished`
  - terminal failure: `failed`, `stopped`, `canceled`
- `not_found` is surfaced as HTTP `404` with canonical error payload (not a
  successful polling status value).

Errors:
- Status-code-first semantics (4xx input/auth/access; 5xx server failures).
- Canonical shape:

```json
{
  "error": {
    "message": "Human-readable summary",
    "code": "optional_code",
    "details": "error detail or traceback"
  }
}
```

Common route-level status requirements are enforced by
`tests/microservices/test_rq_engine_openapi_contract.py`.

## Agent Workflow (Recommended)
1. Acquire a token:
   - User/service token (pre-issued), or
   - Run-scoped session token from `POST /api/runs/{runid}/{config}/session-token`.
2. Submit work to an agent-facing endpoint under `/api/...`.
3. If response includes `job_id`, poll `GET /api/jobstatus/{job_id}`.
4. On failure/debug needs, fetch `GET /api/jobinfo/{job_id}`.
5. Optionally cancel with `POST /api/canceljob/{job_id}`.

## Dev-Agent Local Workflow
- Canonical local account + credential-file convention:
  - `wepppy/weppcloud/static-src/tests/smoke/AGENTS.md`
- Preferred local secret file:
  - `docker/secrets/dev-agent.env`
- Typical setup:
  1. Sign in as `dev-agent@example.com`.
  2. Mint a bearer token from `POST /weppcloud/profile/mint-token` (session + CSRF).
  3. Use that token for `/rq-engine/api/*` calls.
- Admin sanity endpoint for role/scope verification:
  - `GET /rq-engine/api/admin/recently-completed-jobs`

## API Operator Bootstrap Contract (No `wctl`)

For non-developer API operators, auth bootstrap MUST be executable with standard
HTTP clients (`curl`, `python requests`, or equivalent) and MUST NOT require
`wctl`.

Target-profile requirements (owned by `20260411_rq_operator_experience_hardening`):
- Token bootstrap for API operators MUST have at least one documented machine
  path that does not depend on browser DOM/HTML scraping.
- Runbooks and schema docs MUST include a fully API-only bootstrap example with
  redaction guidance for secrets/tokens.
- Operator bootstrap MUST support least-privilege scope selection for the
  target action family (`rq:read`, `rq:status`, `rq:enqueue`, `rq:export`) and
  MUST document required scopes per flow.
- Machine-safe bootstrap MUST require a strong authenticated caller boundary
  (authenticated user principal, trusted service principal, or equivalent);
  anonymous token minting is prohibited.
- Cookie-auth bootstrap paths MUST enforce same-origin/CSRF rules per
  `docs/schemas/weppcloud-csrf-contract.md`.
- Machine-safe bootstrap endpoints MUST be `POST`-only, rate-limited, and
  audited.
- Machine-safe bootstrap tokens SHOULD default to short TTL unless an explicit
  longer-lived policy is documented for that flow.
- If a route remains browser/session-bound (for example CSRF-gated same-origin
  flows), docs MUST label it explicitly as browser-oriented and MUST provide
  the machine-safe alternative.
- Scope grant contract for machine-safe bootstrap:
  - `granted_scopes = requested_scopes ∩ authorized_scopes`;
  - mint routes MUST NOT silently add scopes not present in `requested_scopes`;
  - unknown or unauthorized requested scopes MUST return canonical `4xx`
    errors;
  - read-oriented operator flows SHOULD default to `rq:read` (and include
    `rq:status` only when polling compatibility is required and documented).

Shipped machine-safe bootstrap surface:
- `POST /weppcloud/api/auth/rq-engine-operator-token`
  - bearer-auth only (`Authorization: Bearer <token>`, audience `rq-engine`);
  - source bearer token MUST include a `jti` claim (missing `jti` returns `401`);
  - source bearer token revocation is checked against the JWT denylist
    (`revoked` returns `403`);
  - accepted caller token classes: `user`, `service`;
  - allowed operator scopes: `rq:read`, `rq:status`, `rq:enqueue`, `rq:export`;
  - request body (optional): `{"requested_scopes":[...]}`.
- Scope grant semantics are strict:
  - `granted_scopes = requested_scopes ∩ authorized_scopes`;
  - no silent scope expansion;
  - unknown requested scopes return `400`;
  - unauthorized requested scopes return `403`.
  - example: if caller bearer has only `rq:status`, then
    `{"requested_scopes":["rq:read"]}` returns `403`; request
    `{"requested_scopes":["rq:status"]}` instead.
- Defaults and guardrails:
  - defaults to read-oriented scope when request body omits `requested_scopes`;
  - callers SHOULD send explicit `requested_scopes` that are a subset of source
    bearer scopes to avoid avoidable `403` responses;
  - short-lived token default (`900s`, env-tunable);
  - rate limited and audit logged;
  - revocation backend unavailability returns `503` with retry guidance (`Retry-After`);
  - response uses `Cache-Control: no-store`.
- Run-scoped passthrough:
  - when caller token includes `runid`/`config`/`runs`, minted token preserves
    those claims to maintain rq-engine run authorization behavior.

Browser/session compatibility surface (still supported):
- `POST /weppcloud/profile/mint-token` remains valid for browser-oriented
  session + CSRF flows.
- Browser renewal bridge (`/weppcloud/api/auth/rq-engine-token`) remains for UI
  compatibility and should be treated as browser/session-bound.

## Correlation ID Debugging

- Send `X-Correlation-ID` on submission requests to make cross-service tracing deterministic.
- Confirm `X-Correlation-ID` is echoed on rq-engine responses.
- Use `GET /api/jobinfo/{job_id}` together with worker logs to validate enqueue metadata continuity.
- For end-to-end commands and troubleshooting patterns, use `docs/dev-notes/correlation-id-debugging.md`.

## Browser Renewal Contract (UI clients)
For WEPPcloud browser traffic using `WCHttp.requestWithSessionToken(...)`, token
acquisition is resilient by contract:

1. Attempt run-scoped session token:
   - `POST /api/runs/{runid}/{config}/session-token` (proxied as `/rq-engine/api/...`).
2. If token issuance returns `401` or `403`, transparently fall back to:
   - `POST /weppcloud/api/auth/rq-engine-token` (same-origin Flask endpoint).
3. Retry the original rq-engine request with the fallback bearer token.

Notes:
- This renewal path is intended for authenticated WEPPcloud browser sessions.
- Anonymous/CAPTCHA flows (for example public fork) remain route-specific and do
  not use `/api/auth/rq-engine-token`.
- Fallback token scopes are `rq:enqueue`, `rq:status`, `rq:export`.
- Client-side fallback token cache is short-lived; callers should still treat
  401/403 responses as authoritative when both primary and fallback paths fail.
- CSRF/same-origin behavior for this bridge is governed by
  `docs/schemas/weppcloud-csrf-contract.md`.

## Endpoint Families (Agent-Facing)
For the exact frozen route list (currently 79 routes), use the contract
checklist artifact. The
table below is the practical family map used by agent clients.

| Family | Paths | Typical Execution | Primary Scope |
|---|---|---|---|
| Job control | `/api/jobstatus/{job_id}`, `/api/jobinfo/{job_id}`, `/api/jobinfo`, `/api/canceljob/{job_id}` | Polling is sync/read-only; cancel is sync mutation | `rq:status` (cancel also accepts `culvert:batch:submit`) |
| Setup discovery | `/api/configs`, `/api/configs/{config}`, `/api/endpoints`, `/api/endpoints/{operation_id}/{schema\\|defaults\\|errors}` | Sync read-only discovery | `rq:status` or `rq:read` |
| Bootstrap | `/api/runs/{runid}/{config}/bootstrap/*` plus `run-*-noprep` endpoints | Mix of sync no-queue (`checkout`, reads, mint) and async (`enable`, no-prep runs) | `bootstrap:*` and `rq:enqueue` |
| Build/prep | `/api/runs/{runid}/{config}/build-*`, `fetch-dem-and-build-channels`, `set-outlet` | Mostly async enqueue | `rq:enqueue` |
| Model runs | `/api/runs/{runid}/{config}/run-*` (`wepp`, `wepp-watershed`, `swat`, `rhem`, `ash`, `debris-flow`, `omni`) | Mostly async enqueue; some sync dry-run paths | `rq:enqueue` |
| Upload tasks | `/api/runs/{runid}/{config}/tasks/upload-*` | Sync for upload/validation or async enqueue depending on route | `rq:enqueue` |
| Export | `/api/runs/{runid}/{config}/export/*` | Sync read-only file delivery | `rq:export` |
| Archive/fork | `/api/runs/{runid}/{config}/archive`, `/restore-archive`, `/delete-archive`, `/fork` | Mostly async enqueue; some sync mutation paths | `rq:enqueue` |
| External TS | `/api/runs/{runid}/{config}/acquire-openet-ts`, `/acquire-rap-ts` | Async enqueue | `rq:enqueue` |
| Culvert batch | `/api/culverts-wepp-batch/`, `/api/culverts-wepp-batch/{batch_uuid}/retry/{point_id}` | Async enqueue | `culvert:batch:*` |
| Project create | `/create/` (alias `/api/create/`) | Sync redirect (`303`) plus resource creation | `rq:enqueue` token path or CAPTCHA |

Watershed map-input normalization (`fetch-dem-and-build-channels`):
- For `set_extent_mode` `0`/`1`, agents may submit `map_bounds` without
  `map_center`/`map_zoom`.
- The backend derives missing `map_center` (bbox midpoint) and missing
  `map_zoom` (fit zoom from bounds).
- Explicitly supplied `map_center`/`map_zoom` still override derived values.

## Internal Admin Debug Endpoints
These routes are intentionally **internal/admin** and are not part of the
frozen 79-route agent-facing checklist.

| Method | Path | Purpose | Auth |
|---|---|---|---|
| `GET` | `/api/admin/recently-completed-jobs` | Recently completed jobs across `default` and `batch` queues (lookback/filter support). | JWT Bearer, `rq:status`, `Admin`/`Root` role |
| `GET` | `/api/admin/jobs-detail` | Complete started + queued jobs across `default` and `batch` queues. | JWT Bearer, `rq:status`, `Admin`/`Root` role |

Inventory source of truth for these internal routes remains:
`docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`.

## Bootstrap + Flask Exceptions
Agent-facing Bootstrap operations are canonically owned by rq-engine. Two
Bootstrap endpoints remain intentionally Flask-owned for infrastructure/UI
reasons:
- `/api/bootstrap/verify-token` (Caddy `forward_auth`)
- `/runs/<runid>/<config>/bootstrap/disable` (admin UI control)

## Stability and Change Control
- Route inventory and checklist artifacts are the frozen baseline.
- OpenAPI guard coverage includes:
  - metadata completeness
  - operation ID convention
  - required response code documentation
  - size budgets to prevent OpenAPI bloat
- Any contract change must update:
  - route implementation/OpenAPI metadata
  - freeze/checklist artifacts
  - guard tests
  - this document when behavior changes for clients

## Controller-State Contract Status
- Controller-state/schema/orchestration contract for agent clients is tracked in
  `docs/schemas/rq-controller-state-contract.md`.
- Roadmap cutover row 8 (`20260410_rq_controller_state_contract_cutover`)
  completed on 2026-04-11 with freeze/checklist/OpenAPI/doc parity evidence.
- Implemented additive subset includes:
  - setup discovery: `/api/configs`, `/api/endpoints*`
  - orchestration reads: `/api/runs/{runid}/{config}/pipeline`,
    `/api/runs/{runid}/{config}/readiness`
  - schema/default discovery:
    `/api/runs/{runid}/{config}/controllers*`,
    `/api/runs/{runid}/{config}/endpoints*`
  - geospatial/output metadata:
    `/api/runs/{runid}/{config}/geospatial-metadata`,
    `/api/runs/{runid}/{config}/outputs`
- Remaining additive scope stays planned in
  `docs/schemas/rq-controller-state-contract.md` and must follow the same
  freeze/checklist/OpenAPI guard workflow.

## End-to-End Smoke Runbook
- Canonical smoke runbook for the row-8 frozen baseline:
  `docs/work-packages/20260410_rq_controller_state_contract_cutover/artifacts/2026-04-11_rq_controller_state_e2e_smoke_runbook.md`
- Use this runbook for:
  - deterministic pre-smoke contract/guard regression checks,
  - manual end-to-end API surface smoke sequence (`/api/configs` through
    run-scoped controller-state endpoints and outputs).
- Smoke-runbook contract requirements:
  - pass/fail assertions MUST be based on command exit status and contract-shape
    checks, not hard-coded historical pass counts;
  - expected test-count strings MAY be reported as examples but MUST NOT be the
    correctness gate;
  - endpoint-call evidence MUST record method/path/status with UTC timestamps.
