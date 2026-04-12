# WP-01 Work Package: Service Scaffold and Container Wiring
Status: done
Last Updated: 2026-04-11
Owner: Fresh Agent (unassigned)
Parent Plan: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md`
Primary Spec: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/specification.md`

## Objective
Deliver WP-01 end-to-end by scaffolding the shape-converter service and wiring it into local runtime (compose + Caddy) under `/utils/shape-converter` with tightened route matching.

This package is complete only when all WP-01 gates pass:
- Code gate
- Shape-converter unit-test gate
- QA gate
- Security review gate

## Scope
### In scope
- Python service scaffold for `shape-converter` with Starlette app bootstrap.
- Health endpoints:
  - `GET /utils/shape-converter/health/live`
  - `GET /utils/shape-converter/health/ready`
- Container wiring in dev stack:
  - Docker image/build config for shape-converter
  - Compose service definition
  - Caddy routing with exact/subtree matcher tightening
- Baseline unit tests for app bootstrap and health endpoints.
- Basic smoke validation evidence in this work-package file.

### Out of scope
- ZIP/shapefile parsing and inspect endpoint behavior (WP-02).
- Convert endpoint and CRS/output logic (WP-03).
- Cleanup lifecycle guarantees beyond scaffold-level hooks (WP-04).
- Abuse controls, security hardening completion, and secondary sandbox enforcement (WP-05/WP-07).
- WEPPcloud route/controller updates (separate scope).

## Constraints and Invariants
- No branch creation unless explicitly requested by human operator.
- Do not modify unrelated dirty files.
- Keep route namespace and matching aligned with spec:
  - Canonical prefix: `/utils/shape-converter`
  - No loose `/utils/shape-converter*` glob that can catch `/utils/shape-converterfoo`.
- Service is public/unauthenticated by design; do not add auth requirements in WP-01.

## Target File Plan
Expected new/modified files for WP-01 (adjust only if justified):
- `wepppy/microservices/shape_converter/__init__.py`
- `wepppy/microservices/shape_converter/app.py` (or equivalent module exposing ASGI app)
- `wepppy/microservices/shape_converter/routes.py` (optional split)
- `docker/docker-compose.dev.yml`
- `docker/caddy/Caddyfile`
- `docker/caddy/Caddyfile.wepp1` (keep parity unless explicitly deferred)
- `tests/shape_converter/unit/test_app_bootstrap.py`
- `tests/shape_converter/unit/test_health_routes.py`

Optional doc updates if paths differ:
- `/workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md` (update WP-01 notes)

## Implementation Steps (Execute Sequentially)
1. Create service package scaffold under `wepppy/microservices/shape_converter`.
2. Expose ASGI app object/factory compatible with `uvicorn` launch.
3. Implement health routes:
   - `live`: returns simple healthy response.
   - `ready`: verifies app bootstrapped and scratch dir is writable.
4. Add compose service `shape-converter` using repo conventions from `query-engine`/`rq-engine`.
5. Add tightened Caddy routes for exact and subtree namespace handling:
   - `/utils/shape-converter`
   - `/utils/shape-converter/`
   - `/utils/shape-converter/*`
6. Ensure forwarded prefix headers are set to `/utils/shape-converter`.
7. Add unit tests for app import/bootstrap and both health routes.
8. Run unit tests and fix failures.
9. Run local smoke checks via Caddy and record evidence in this file.
10. Update gate table and completion state in parent plan.

## Commands and Validation
## Fast iteration
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/unit --maxfail=1
```

## Full WP-01 unit gate
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/unit
```

## Local runtime smoke (dev stack)
```bash
cd /workdir/wepppy
docker compose -f docker/docker-compose.dev.yml up -d caddy shape-converter
curl -i http://127.0.0.1:8080/utils/shape-converter/
curl -i http://127.0.0.1:8080/utils/shape-converter/health/live
curl -i http://127.0.0.1:8080/utils/shape-converter/health/ready
curl -i http://127.0.0.1:8080/utils/shape-converterfoo
```

Expected:
- health endpoints return 200.
- `/utils/shape-converterfoo` is not routed to shape-converter.

## Gate Checklist
## Code gate
- [x] WP-01 implementation scope complete.
- [x] Code review findings resolved.
- [x] Lint/static checks for touched files pass.

## Shape-converter unit-test gate
- [x] `wctl run-pytest tests/shape_converter/unit --maxfail=1` passes.
- [x] `wctl run-pytest tests/shape_converter/unit` passes.

## QA gate
- [x] Caddy namespace routing verified manually.
- [x] Health endpoints validated through proxied route.
- [x] Smoke evidence captured.

## Security review gate
- [x] Public unauthenticated access behavior verified (no auth required).
- [x] Prefix-tightening route behavior verified (`/utils/shape-converterfoo` not matched).
- [x] Security reviewer sign-off recorded.

## Evidence Log (Fill During Execution)
| Item | Evidence |
| --- | --- |
| Commit SHA(s) | Not committed in this run (local working tree changes only). |
| Unit gate output | `wctl run-pytest tests/shape_converter/unit --maxfail=1` -> `6 passed, 7 warnings in 8.59s`; `wctl run-pytest tests/shape_converter/unit` -> `6 passed, 7 warnings in 8.86s`. |
| QA smoke output | `docker compose -f docker/docker-compose.dev.yml up -d caddy shape-converter`; `curl -i -H 'X-Forwarded-Proto: https' http://127.0.0.1:8080/utils/shape-converter/` -> `200` JSON; `.../health/live` -> `200`; `.../health/ready` -> `200`; `.../shape-converter` -> `308` to trailing slash. |
| Security review reference | Negative namespace probe `curl -i -H 'X-Forwarded-Proto: https' http://127.0.0.1:8080/utils/shape-converterfoo` returned Caddy empty response (not proxied). `docker compose ... logs shape-converter` shows only `/`, `/health/live`, `/health/ready` requests and no `shape-converterfoo` hit. |
| Residual risks | Runtime sandbox hardening, abuse controls, and parser/toolchain sandbox readiness checks are intentionally deferred to WP-05 and WP-07. |

## Completion Criteria
WP-01 is `done` only when:
- All four gates are `pass` (or explicitly waived with rationale/approver).
- Parent orchestration board is updated with gate states and notes.
- This work-package evidence table is filled with concrete references.

## Handoff Notes for Fresh Agent
- Execute this package end-to-end without pausing unless blocked by external dependency.
- If blocked, update:
  - this WP file (`Evidence Log` + blocker note), and
  - `/workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md` (WP-01 state -> `blocked` + reason).
