# RQ Engine Agents Guide

## Authorship
**This document and all AGENTS.md documents are maintained by GitHub Copilot / Codex which retain full authorship rights for all AGENTS.md content revisions. Agents can author AGENTS.md document when and where they see fit.**

## Purpose
`wepppy.microservices.rq_engine` is the FastAPI surface that enqueues RQ jobs for
WEPPcloud run workflows and exposes job polling endpoints. Agents should treat
this service as the canonical async interface for run-scoped operations.

## Entrypoint
- `wepppy/microservices/rq_engine/__init__.py` defines the FastAPI `app`,
  installs the auth-actor hook, and registers every router under `/api`.
- `/health` returns `{status: ok, scope: rq-engine}`.
- Reverse proxies can set `X-Forwarded-Prefix`; the middleware maps that to
  `root_path`.

## Agent Workflow (Recommended)
1. **Issue a session token**: `POST /api/runs/{runid}/{config}/session-token`.
   - Accepts a session cookie or a bearer token with `rq:status` scope.
   - Returns a short-lived bearer token with `rq:enqueue`, `rq:status`, and
     `rq:export` scopes plus `runid`/`config` claims.
2. **Enqueue work** with `Authorization: Bearer <token>` using the run-scoped
   routes (climate, watershed, wepp, landuse, soils, etc.).
3. **Poll jobs**: `GET /api/jobstatus/{job_id}` or `GET /api/jobinfo/{job_id}`.
4. **Cancel jobs**: `POST /api/canceljob/{job_id}` (requires `rq:status`).

## Auth and Access Control
- `auth.py` validates JWTs and supports token classes: `user`, `session`,
  `service`, `mcp`.
- Run-scoped endpoints must call `authorize_run_access(claims, runid)`.
  - `user` tokens are checked against run owners or public runs.
  - `session` tokens are validated via Redis DB 11
    `auth:session:run:{runid}:{session_id}` markers.
  - `service`/`mcp` tokens must include the run id in `runs`/`runid` claims.
- Admin-only endpoints use `require_roles(..., ["Admin"])` (ex: run sync).
- `require_jwt()` sets the auth actor; `install_rq_auth_actor_hook()` writes that
  payload into `job.meta["auth_actor"]` for auditing.

## Response Contract (Must)
- Follow `docs/schemas/rq-response-contract.md`.
- Use canonical keys (`job_id`, `job_ids`, `message`, `warnings`, `result`).
- Error payloads must be:
  ```json
  {"error": {"message": "...", "code": "optional", "details": "..."}}
  ```
- Prefer helpers in `responses.py` (`error_response`,
  `error_response_with_traceback`, `validation_error_response`).

## Payload Handling
- Use `parse_request_payload()` to accept JSON or form submissions.
- Pass `boolean_fields={...}` for payload flags that must normalize to bool.
- Keep string trimming on unless a route explicitly needs raw text.

## Queue + Timeouts
- RQ uses Redis DB 9 (`RedisDB.RQ`) via `redis_connection_kwargs`.
- Most enqueue routes honor `RQ_ENGINE_RQ_TIMEOUT` (default 216000s).
- Run sync uses:
  - `RQ_ENGINE_RUN_SYNC_TIMEOUT` (default 86400s)
  - `RQ_ENGINE_MIGRATIONS_TIMEOUT` (default 7200s)
- Avoid silent fallbacks for missing dependencies; fail loudly so debugging is
  explicit.

## Key Route Modules (Run-Scoped)
- `session_routes.py` - issues session tokens.
- `job_routes.py` - job status/info/cancel.
- `climate_routes.py`, `watershed_routes.py`, `wepp_routes.py` - core run flow.
- `landuse_routes.py`, `soils_routes.py`, `treatments_routes.py` - inputs.
- `upload_*_routes.py` - file uploads for batch/climate/landuse inputs.
- `run_sync_routes.py` - admin-only run sync + migrations.

## Adding or Extending Routes
- Define `router = APIRouter()` and export it via `__all__ = ["router"]`.
- Register the router in `__init__.py` with `prefix="/api"`.
- Use `require_jwt` + `authorize_run_access` early; return canonical errors.
- Log exceptions (`logger.exception`) before returning `error_response_with_traceback`.

## Tests
- Tests live in `tests/microservices/test_rq_engine_*.py`.
- Typical run: `wctl run-pytest tests/microservices/test_rq_engine_<module>.py`.
