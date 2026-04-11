# RQ-Engine Agent API Contract
> Canonical contract for agent clients using the WEPPcloud rq-engine.
> **Status:** Canonical path under `docs/schemas/` as of 2026-04-10 (moved from `docs/dev-notes/`).
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
  `20260410_rq_controller_state_contract_cutover` closed on 2026-04-10 with
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
For the exact frozen route list (currently 67 routes), use the contract
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
| Project create | `/create/` | Sync redirect (`303`) plus resource creation | `rq:enqueue` token path or CAPTCHA |

## Internal Admin Debug Endpoints
These routes are intentionally **internal/admin** and are not part of the
frozen 67-route agent-facing checklist.

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
  completed on 2026-04-10 with freeze/checklist/OpenAPI/doc parity evidence.
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
