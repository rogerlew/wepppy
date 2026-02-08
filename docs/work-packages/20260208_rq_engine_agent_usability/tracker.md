# Tracker - RQ-Engine Agent Usability and Documentation Hardening

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-02-08  
**Current phase**: Discovery  
**Last updated**: 2026-02-08  
**Next milestone**: Freeze endpoint inventory and annotate agent-facing routes

## Task Board

### Ready / Backlog
- [ ] Freeze endpoint inventory (`agent-facing`, `internal`, `UI-only`).
- [ ] Standardize OpenAPI metadata for agent-facing Bootstrap and queue routes.
- [ ] Align auth/token documentation with enforced scope behavior.
- [ ] Add/expand regression tests for auth, async enable lifecycle, and lock contention paths.
- [ ] Produce artifact checklist for route contracts and test coverage.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Drafted initial plan as a mini work package (2026-02-08).
- [x] Locked policy decisions on endpoint ownership, scope minimums, and polling access (2026-02-08).
- [x] Migrated mini work package to full work-package structure with artifacts/prompt directories (2026-02-08).
- [x] Captured Bootstrap Phase 2 wrap-up artifact and verification snapshot (2026-02-08).

## Timeline

- **2026-02-08** - Mini work package drafted.
- **2026-02-08** - Decisions locked for Bootstrap endpoint ownership and scopes.
- **2026-02-08** - Migrated to full work-package structure.
- **2026-02-08** - Bootstrap Phase 2 closure snapshot documented.

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

**Decision**: Keep polling endpoints open for now.

**Impact**: Preserves current UX and agent simplicity; threat model relies on UUID4 job ID entropy and read-only semantics.

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
