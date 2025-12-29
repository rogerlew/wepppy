# Mini Work Package: rq-engine jobinfo polling offload

**Status:** Complete  
**Last Updated:** 2025-12-23  
**Primary Areas:** `wepppy/microservices/rq_engine.py`, `wepppy/weppcloud/routes/rq/api/jobinfo.py`, `wepppy/rq/job_info.py`, `wepppy/weppcloud/controllers_js/*`, `docker/docker-compose.*.yml`, `docker/caddy/Caddyfile`, docs

---

## Objective
Move high-frequency job polling endpoints into a dedicated FastAPI service (rq-engine) and route them via Caddy at `/rq-engine/api/...` to reduce weppcloud load. Keep the existing `/weppcloud/rq/api/...` endpoints as redundant backups. Clients should try `/rq-engine/api/...` first and fall back to `/weppcloud/rq/api/...` on any error.

## Target Endpoints
New rq-engine routes (proxied by Caddy):
- `GET /rq-engine/api/jobstatus/{job_id}`
- `GET /rq-engine/api/jobinfo/{job_id}`
- `POST /rq-engine/api/jobinfo` (batch)

Legacy endpoints remain:
- `GET /weppcloud/rq/api/jobstatus/{job_id}`
- `GET /weppcloud/rq/api/jobinfo/{job_id}`
- `POST /weppcloud/rq/api/jobinfo`

## Current Polling Call Sites
Primary poll sources to update for rq-engine priority + fallback:
- `wepppy/weppcloud/controllers_js/control_base.js` (jobstatus + jobinfo GET)
- `wepppy/weppcloud/controllers_js/status_stream.js` (jobinfo GET for stacktrace)
- `wepppy/weppcloud/controllers_js/batch_runner.js` (jobinfo POST batch)
- `wepppy/weppcloud/routes/rq/job_dashboard/templates/dashboard.htm` (jobinfo polling)
- `wepppy/weppcloud/templates/reports/deval_loading.htm` + `wepppy/weppcloud/routes/weppcloudr.py` (jobstatus polling)
- `wepppy/profile_recorder/playback.py` (jobstatus/jobinfo polling)
- Controller Jest tests in `wepppy/weppcloud/controllers_js/__tests__/*` that assert `/weppcloud/rq/api/jobinfo...`

Docs referencing jobinfo endpoints:
- `wepppy/weppcloud/routes/rq/api/doc/land_and_soils.md`

---

## Plan (multi-phase)

### Phase 1 - Service design + shared helpers
1. Implement rq-engine as `wepppy/microservices/rq_engine.py` on port `8042`.
2. Extract shared request parsing helpers from `wepppy/weppcloud/routes/rq/api/jobinfo.py` into a shared module (for example `wepppy/rq/jobinfo_payloads.py`) so Flask and FastAPI stay in sync.
3. Define response parity with Flask routes using `wepppy.rq.job_info` helpers; include a lightweight `/health` endpoint.

## Phase 1 Handoff Summary
- Added shared job-id parsing helpers in `wepppy/rq/jobinfo_payloads.py` with a matching stub in `wepppy/rq/jobinfo_payloads.pyi`.
- Updated `wepppy/weppcloud/routes/rq/api/jobinfo.py` to reuse the shared parser so Flask and FastAPI stay aligned.

### Phase 2 - Implement rq-engine FastAPI service
1. Build FastAPI app in `wepppy/microservices/rq_engine.py` with endpoints under `/api` (read-only; no auth layer required):
   - `GET /api/jobstatus/{job_id}`
   - `GET /api/jobinfo/{job_id}`
   - `POST /api/jobinfo`
2. Return the same JSON payloads as Flask (including `not_found` cases and batch `job_ids` ordering).
3. Wire Redis configuration via `wepppy.config.redis_settings` and reuse `wepppy.rq.job_info` helpers.
4. Add a service README and minimal tests (unit tests for request parsing + response shapes).

## Phase 2 Handoff Summary
- Implemented `wepppy/microservices/rq_engine.py` FastAPI app with `/health` plus `/api/jobstatus`, `/api/jobinfo` (GET/POST) endpoints using `wepppy.rq.job_info` and shared parsing helpers.

### Phase 3 - Infra wiring (Docker + Caddy)
1. Add rq-engine service to `docker/docker-compose.dev.yml` and `docker/docker-compose.prod.yml` (uvicorn, port `8042`).
2. Add Caddy `handle_path /rq-engine*` reverse proxy to rq-engine with `X-Forwarded-Prefix: /rq-engine` and `X-Forwarded-Proto` headers.
3. Document the new service and routing in `docker/README.md` and `wepppy/weppcloud/README.md`.

## Phase 3 Handoff Summary
- Added `rq-engine` services to `docker/docker-compose.dev.yml` and `docker/docker-compose.prod.yml` (port 8042).
- Added `/rq-engine*` proxy routing to `docker/caddy/Caddyfile` with `X-Forwarded-Prefix` headers.
- Documented rq-engine routing in `docker/README.md`, `wepppy/weppcloud/README.md`, and `wepppy/microservices/README.md`.

### Phase 4 - Client updates with fallback
1. Add a shared helper in `wepppy/weppcloud/controllers_js/http.js` (or `utils.js`) to:
   - bypass `site_prefix` for `/rq-engine`
   - try `/rq-engine/api/...` first and fall back to `/weppcloud/rq/api/...`
   - treat any error response as a fallback trigger
2. Update polling call sites to use the helper:
   - `control_base.js` (jobstatus + jobinfo GET)
   - `status_stream.js` (jobinfo GET)
   - `batch_runner.js` (jobinfo POST)
   - `job_dashboard` template
   - `deval_loading` template and `weppcloudr.py` context
3. Update profile playback polling to prefer rq-engine with fallback.
4. Update Jest tests to accept `/rq-engine/api/...` primary and fallback paths.

## Phase 4 Handoff Summary
- Added `/rq-engine` bypass and fallback helpers in `wepppy/weppcloud/controllers_js/http.js`.
- Updated polling call sites to prefer `/rq-engine/api` with fallback:
  - `wepppy/weppcloud/controllers_js/control_base.js`
  - `wepppy/weppcloud/controllers_js/status_stream.js`
  - `wepppy/weppcloud/controllers_js/batch_runner.js`
  - `wepppy/weppcloud/routes/rq/job_dashboard/templates/dashboard.htm`
  - `wepppy/weppcloud/templates/reports/deval_loading.htm`
  - `wepppy/profile_recorder/playback.py`
- Updated Jest coverage for the new jobinfo POST fallback (`wepppy/weppcloud/controllers_js/__tests__/batch_runner.test.js`) and rq-engine prefix bypass (`wepppy/weppcloud/controllers_js/__tests__/http.test.js`).
- Documented rq-engine jobinfo usage in `wepppy/weppcloud/routes/rq/api/doc/land_and_soils.md`.

### Phase 5 - Validation + rollout
1. Build controllers bundle and run `wctl run-npm test` for updated tests.
2. Add/adjust pytest coverage for rq-engine endpoints if needed.
3. Smoke test:
   - `curl https://wc.bearhive.duckdns.org/rq-engine/health`
   - `curl https://wc.bearhive.duckdns.org/rq-engine/api/jobstatus/<jobid>`
4. Confirm Caddy routing order and HAProxy health check behavior on forest.

---

### Phase 6 - Test coverage (reviewer request)
1. Add unit coverage for `normalize_job_id_inputs` and `extract_job_ids` in `tests/rq/test_jobinfo_payloads.py`.
2. Add microservice coverage for rq-engine in `tests/microservices/test_rq_engine.py` using TestClient + monkeypatch stubs.

## Phase 6 Handoff Summary
- Added unit tests for job-id parsing and extraction in `tests/rq/test_jobinfo_payloads.py`.
- Added FastAPI TestClient coverage for rq-engine endpoints and error handling in `tests/microservices/test_rq_engine.py`.
- `wctl run-pytest tests/rq/test_jobinfo_payloads.py` and `wctl run-pytest tests/microservices/test_rq_engine.py` are clean.

## Author Review Summary
- Change: `jobinfo_payloads.py` now normalizes dict payload values via `list(payload.values())` when no `job_ids`/`jobs`/`ids` key is present.
- Tests added: `tests/rq/test_jobinfo_payloads.py`, `tests/microservices/test_rq_engine.py`.
- Tests run: `wctl run-pytest tests/rq/test_jobinfo_payloads.py`, `wctl run-pytest tests/microservices/test_rq_engine.py`.
- Warnings: existing deprecations from pytz, pyparsing, and httpx raw content upload.
- Reviewer handoff: new unit + microservice coverage validates job ID parsing and rq-engine endpoints (error handling, invalid JSON fallback).

## Final Handoff Summary
- Manual end-to-end validation: stopped rq-engine with `wctl down rq-engine`, confirmed clients fell back to `/weppcloud/rq/api`, restarted rq-engine and confirmed primary `/rq-engine/api` polling resumed.
- Test suites clean: `wctl run-pytest` and `wctl run-npm test`.

## Open Questions
- None; logging/metrics explicitly out of scope.
