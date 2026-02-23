# RQ-Engine Agent API Contract
> Canonical contract for agent clients using the WEPPcloud rq-engine.
> **See also:** `docs/schemas/rq-response-contract.md`, `docs/dev-notes/auth-token.spec.md`, `docs/dev-notes/correlation-id-debugging.md`, `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`, and user-facing `wepppy/weppcloud/routes/usersum/weppcloud/rq-engine.md`.

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
| `rq:status` | Job polling (`jobstatus`, `jobinfo`) and `canceljob`; also bearer path for session-token issuance. |
| `rq:enqueue` | Most run mutations that enqueue background jobs or perform run mutations under rq-engine routes. |
| `rq:export` | Export artifact endpoints under `/runs/{runid}/{config}/export/*`. |
| `bootstrap:enable` | Bootstrap enable endpoint. |
| `bootstrap:token:mint` | Bootstrap token mint endpoint. |
| `bootstrap:read` | Bootstrap read endpoints (`commits`, `current-ref`). |
| `bootstrap:checkout` | Bootstrap checkout endpoint. |
| `culvert:batch:submit` | Culvert batch submit endpoint; also accepted for `/api/canceljob/{job_id}`. |
| `culvert:batch:retry` | Culvert batch retry endpoint. |

Bootstrap routes do not accept `rq:enqueue` as a substitute for `bootstrap:*`.

## Response Contract
rq-engine responses must follow `docs/schemas/rq-response-contract.md`.

Submission/command responses:
- Async submit commonly returns `job_id` and `status_url`.
- Sync operations return `message` and optional `result`.
- Keys use `lower_snake_case`.

Polling responses:
- `jobstatus`: `{job_id, runid, status, started_at, ended_at}`
- `jobinfo`: `{job_id, runid, status, result, started_at, ended_at, description, elapsed_s, exc_info, children, auth_actor?}`

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

## Endpoint Families (Agent-Facing)
For the exact 51-route frozen list, use the contract checklist artifact. The
table below is the practical family map used by agent clients.

| Family | Paths | Typical Execution | Primary Scope |
|---|---|---|---|
| Job control | `/api/jobstatus/{job_id}`, `/api/jobinfo/{job_id}`, `/api/jobinfo`, `/api/canceljob/{job_id}` | Polling is sync/read-only; cancel is sync mutation | `rq:status` (cancel also accepts `culvert:batch:submit`) |
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
frozen 51-route agent-facing checklist.

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
