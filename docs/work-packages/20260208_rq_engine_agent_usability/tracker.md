# Tracker - RQ-Engine Agent Usability and Documentation Hardening

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-02-08  
**Current phase**: Agent-facing docs split (developer doc landed)  
**Last updated**: 2026-02-08  
**Next milestone**: Agent-facing rq-engine docs and usersum split

## Task Board

### Ready / Backlog
- [x] Freeze endpoint inventory (`agent-facing`, `internal`, `UI-only`).
- [x] Standardize OpenAPI metadata for agent-facing Bootstrap and queue routes.
- [x] Align auth/token documentation with enforced scope behavior.
- [x] Add/expand regression tests for auth, async enable lifecycle, and lock contention paths.
- [x] Produce artifact checklist for route contracts and test coverage.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Drafted initial plan as a mini work package (2026-02-08).
- [x] Locked policy decisions on endpoint ownership, scope minimums, and polling access (2026-02-08).
- [x] Migrated mini work package to full work-package structure with artifacts/prompt directories (2026-02-08).
- [x] Captured Bootstrap Phase 2 wrap-up artifact and verification snapshot (2026-02-08).
- [x] Standardized OpenAPI metadata for frozen agent-facing routes and added contract budget checks (2026-02-08).
- [x] Added route contract checklist artifact + drift guard tooling/tests (2026-02-08).
- [x] Added canonical rq-engine developer contract doc for agents (2026-02-08).

## Timeline

- **2026-02-08** - Mini work package drafted.
- **2026-02-08** - Decisions locked for Bootstrap endpoint ownership and scopes.
- **2026-02-08** - Migrated to full work-package structure.
- **2026-02-08** - Bootstrap Phase 2 closure snapshot documented.
- **2026-02-08** - Endpoint inventory freeze captured with classification, ownership, auth/access, and mutation semantics.
- **2026-02-08** - Freeze-review remediations landed for Bootstrap scopes, wrapper parity, polling hardening, and inventory drift guard.
- **2026-02-08** - OpenAPI metadata standardized for frozen agent-facing routes with contract/size budget tests.
- **2026-02-08** - Route contract checklist artifact published with automated drift guard.
- **2026-02-08** - Added `docs/dev-notes/rq-engine-agent-api.md` as the canonical developer-facing rq-engine agent contract.

## Decisions Log

### 2026-02-08: Bootstrap endpoint ownership
**Context**: Agent-facing Bootstrap operations were split between Flask and rq-engine.

**Options considered**:
1. Keep split ownership between Flask and rq-engine.
2. Keep Flask as primary and mirror selected routes in rq-engine.
3. Converge agent-facing Bootstrap operations in rq-engine.

**Decision**: Converge agent-facing Bootstrap operations in rq-engine. If currently Flask-only, move or replicate into rq-engine and converge there.

**Impact**: Reduces contract drift and gives agents one canonical API surface.

---

### 2026-02-08: Minimum Bootstrap scope set
**Context**: Read vs mutate Bootstrap operations needed explicit scope boundaries.

**Options considered**:
1. Broad single scope for all Bootstrap endpoints.
2. Explicit per-operation scopes.

**Decision**: Use explicit scopes:
- `bootstrap:enable`
- `bootstrap:token:mint`
- `bootstrap:read`
- `bootstrap:checkout`

**Impact**: Improves least-privilege access and makes auth contracts auditable.

---

### 2026-02-08: Job polling access model
**Context**: Whether to gate job polling behind tokens by default.

**Options considered**:
1. Token-gate all polling endpoints.
2. Keep read-only polling open.

**Decision**: Keep polling endpoints open (`RQ_ENGINE_POLL_AUTH_MODE=open`) across dev/test/prod for now.

**Impact**: Preserves current UX and agent simplicity; threat model relies on UUID4 job ID entropy and read-only semantics.

---

### 2026-02-08: Polling rate-limit backend
**Context**: Polling hardening added rate limiting; backend choice was open.

**Options considered**:
1. Redis-backed distributed limiter.
2. In-process limiter per worker.

**Decision**: Keep the in-process limiter for now.

**Impact**: Fast and low-complexity implementation pre-deploy; cross-worker/global limiting can be revisited post-deploy if needed.

---

### 2026-02-08: Bootstrap Phase 2 stabilization accepted
**Context**: Production-readiness review returned a concrete remediation/test list.

**Decision**: Record remediation outcomes and verification as a package artifact,
and keep Bootstrap as the immediate stabilization priority before new scope.

**Impact**: Preserves implementation context while fresh and creates a stable
handoff point for further API usability work.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Route ownership drift between Flask and rq-engine | High | Medium | Converge agent endpoints in rq-engine and document ownership in tracker + package | Open |
| OpenAPI drift from implemented behavior | Medium | Medium | Add route-level schema checks and regression assertions against documented responses | Open |
| Scope checks inconsistent across endpoints | High | Medium | Enforce common auth helper usage and add targeted `401/403` tests | Open |
| Lock semantics under concurrent agents may regress | Medium | Medium | Add lock contention tests and publish retry guidance in docs | Open |

## Verification Checklist

### Code Quality
- [x] Targeted pytest suites pass for touched modules.
- [ ] Frontend tests pass for Bootstrap controller updates.
- [x] No new auth or contract regressions in rq-engine responses.

### Documentation
- [ ] `docs/dev-notes/auth-token.spec.md` updated for scope/audience expectations.
- [ ] `docs/weppcloud-bootstrap-spec.md` reflects current endpoint ownership and async behavior.
- [ ] `wepppy/weppcloud/routes/usersum/weppcloud/bootstrap.md` reflects user-facing workflow and constraints.
- [ ] OpenAPI descriptions/examples cover agent-facing routes.

### Testing
- [x] Auth failures (`401`, `403`) covered for protected Bootstrap routes.
- [x] Invalid/expired/audience-mismatch token cases covered.
- [x] Async enable `queued -> finished/failed` behavior covered.
- [x] Lock contention and canonical error payloads covered.

### Deployment
- [ ] Changes validated in `docker-compose.dev.yml` environment.
- [ ] If behavior changes materially, run smoke flow against forest test production before closure.

## Progress Notes

### 2026-02-08: Package migration setup
**Agent/Contributor**: Codex

**Work completed**:
- Created full work-package structure under `docs/work-packages/20260208_rq_engine_agent_usability/`.
- Migrated planning content from the mini work package into `package.md` and `tracker.md`.
- Added standard directories for prompts and artifacts.

**Blockers encountered**:
- None.

**Next steps**:
- Start endpoint inventory pass and define first implementation artifact.

**Test results**: `wctl doc-lint` passed for `package.md`, `tracker.md`, and `PROJECT_TRACKER.md`.

### 2026-02-08: Bootstrap Phase 2 wrap-up capture
**Agent/Contributor**: Codex

**Work completed**:
- Added closure snapshot to `docs/weppcloud-bootstrap-spec.md` with implemented
  remediations and verification summary.
- Added artifact:
  `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/bootstrap_phase2_wrapup_20260208.md`.

**Next steps**:
- Re-run the targeted Bootstrap suite to refresh local verification signal before
  any final wrap-up commit.

**Test results**:
- `wctl doc-lint` passed for:
  - `docs/weppcloud-bootstrap-spec.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/tracker.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/bootstrap_phase2_wrapup_20260208.md`
- `wctl run-pytest` passed for:
  - `tests/weppcloud/routes/test_bootstrap_bp.py`
  - `tests/weppcloud/routes/test_bootstrap_auth_integration.py`
  - `tests/microservices/test_rq_engine_bootstrap_routes.py`
  - `tests/rq/test_bootstrap_enable_rq.py`
  - `tests/weppcloud/bootstrap/test_enable_jobs.py`
  - `tests/rq/test_bootstrap_autocommit_rq.py`
  - `tests/weppcloud/bootstrap/test_pre_receive.py`
  - Result: `60 passed`

### 2026-02-08: Endpoint inventory freeze
**Agent/Contributor**: Codex

**Work completed**:
- Added freeze artifact:
  `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`.
- Enumerated all route decorators in:
  - `wepppy/microservices/rq_engine/*.py`
  - `wepppy/weppcloud/routes/bootstrap.py`
- Classified each endpoint (`agent-facing`, `internal`, `ui-only`) and recorded canonical owner.
- Captured per-endpoint auth/access model (JWT/open/login/basic auth, scopes, run-access/role gates).
- Captured mutation semantics (read-only vs mutating, async enqueue/job-response behavior).
- Documented Bootstrap duplication/convergence state and frozen decisions.

**Open follow-ups**:
- Converge or retire duplicate Flask Bootstrap wrapper endpoints once deployment telemetry exists.
- Decide whether Flask-only `bootstrap/disable` should remain Flask-owned or move into rq-engine after first deploy.

**Test results**:
- `wctl doc-lint` executed (wrapper runs `markdown-doc lint --staged`; no staged files in this session).
- File-level lint validated with:
  - `markdown-doc lint --path docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md --path docs/work-packages/20260208_rq_engine_agent_usability/tracker.md --path docs/work-packages/20260208_rq_engine_agent_usability/package.md`
  - Result: `3 files validated, 0 errors, 0 warnings`

### 2026-02-08: Endpoint-freeze remediation implementation
**Agent/Contributor**: Codex

**Work completed**:
- Enforced strict Bootstrap scopes in rq-engine routes:
  - `bootstrap:enable`
  - `bootstrap:token:mint`
  - `bootstrap:read`
  - `bootstrap:checkout`
- Refactored Flask Bootstrap duplicate routes into thin wrappers around shared
  logic in `wepppy/weppcloud/bootstrap/api_shared.py`.
- Kept Flask-owned exceptions intact:
  - `/api/bootstrap/verify-token`
  - `/runs/<runid>/<config>/bootstrap/disable`
- Added parity tests for Flask wrapper vs rq-engine on:
  - enable
  - mint-token
  - commits
  - current-ref
  - checkout
- Hardened polling endpoints with:
  - auth mode switch (`open`, `token_optional`, `required`)
  - rate limiting defaults (`120` requests / `60` seconds)
  - structured audit logging fields (endpoint, status, success/failure, job id,
    caller, IP)
- Added inventory drift guard:
  - `tools/check_endpoint_inventory.py`
  - `tests/tools/test_endpoint_inventory_guard.py`

**Open follow-ups**:
- Set Flask wrapper retirement milestones once first production deployment
  telemetry is available.
- Keep route-ownership drift guard in pytest for now; revisit broader CI wiring
  after initial deploy.

**Test results**:
- `wctl run-pytest tests/weppcloud/routes/test_bootstrap_bp.py tests/weppcloud/routes/test_bootstrap_auth_integration.py tests/microservices/test_rq_engine_bootstrap_routes.py tests/microservices/test_rq_engine_jobinfo.py tests/rq/test_bootstrap_enable_rq.py tests/weppcloud/bootstrap/test_enable_jobs.py tests/rq/test_bootstrap_autocommit_rq.py tests/weppcloud/bootstrap/test_pre_receive.py tests/tools/test_endpoint_inventory_guard.py`
  - Result: `80 passed, 8 warnings`
- `wctl doc-lint --path docs/weppcloud-bootstrap-spec.md --path docs/dev-notes/auth-token.spec.md --path docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md --path docs/work-packages/20260208_rq_engine_agent_usability/tracker.md --path docs/work-packages/20260208_rq_engine_agent_usability/package.md`
  - Result: `5 files validated, 0 errors, 0 warnings`

### 2026-02-08: Route contract checklist artifact + guard
**Agent/Contributor**: Codex

**Work completed**:
- Added artifact:
  `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`
  with one checklist row per frozen `agent-facing` `rq-engine` route
  (`51` rows).
- Added checklist drift guard:
  `tools/check_route_contract_checklist.py`.
- Added pytest coverage for checklist drift guard:
  `tests/tools/test_route_contract_checklist_guard.py`.
- Enforced checklist quality gates:
  - parity with frozen inventory route set
  - non-empty contract fields
  - required auth error codes (`401/403/500`) plus a success code
  - required linkage to OpenAPI contract coverage test module

**Next steps**:
- Add/expand agent-facing rq-engine API docs and user-facing split docs.

**Test results**:
- `python tools/check_route_contract_checklist.py`
  - Result: `Route contract checklist check passed`
- `wctl run-pytest tests/tools/test_route_contract_checklist_guard.py tests/tools/test_endpoint_inventory_guard.py tests/microservices/test_rq_engine_openapi_contract.py`
  - Result: `9 passed`

### 2026-02-08: rq-engine developer contract doc
**Agent/Contributor**: Codex

**Work completed**:
- Added `docs/dev-notes/rq-engine-agent-api.md` with:
  - canonical rq-engine API surface and OpenAPI access paths
  - auth model and polling mode contract
  - scope contract summary
  - response/error payload expectations
  - recommended agent workflow
  - endpoint-family map linked to frozen checklist/inventory artifacts

**Open follow-ups**:
- Add the complementary usersum page for non-API user workflow framing.

**Validation results**:
- `wctl doc-lint --path docs/dev-notes/rq-engine-agent-api.md --path docs/work-packages/20260208_rq_engine_agent_usability/tracker.md --path docs/work-packages/20260208_rq_engine_agent_usability/package.md`
  - Result: `3 files validated, 0 errors, 0 warnings`
