# Tracker - Cross-Service Auth Token Integration Hardening

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-02-19  
**Current phase**: Complete (validation closed)  
**Last updated**: 2026-02-19  
**Next milestone**: Handoff and review

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Created work-package scaffold (`package.md`, `tracker.md`, prompts directories) (2026-02-19).
- [x] Authored active ExecPlan for integrated campaign execution (2026-02-19).
- [x] Added package entry to `PROJECT_TRACKER.md` backlog (2026-02-19).
- [x] Added compatibility matrix artifact: `artifacts/token_compatibility_matrix.md` (2026-02-19).
- [x] Added shared integration harness under `tests/integration/conftest.py` with deterministic JWT env, Redis double (`setex`/TTL), and cross-service token issuers (2026-02-19).
- [x] Added matrix-driven portability suite in `tests/integration/test_cross_service_auth_portability.py` (2026-02-19).
- [x] Added lifecycle suite in `tests/integration/test_cross_service_auth_lifecycle.py` (2026-02-19).
- [x] Added auth primitive unit-gap coverage in `tests/weppcloud/test_auth_tokens.py` and `tests/microservices/test_rq_engine_auth.py` (2026-02-19).
- [x] Created lifecycle evidence artifact `artifacts/lifecycle_validation_results.md` (2026-02-19).
- [x] Updated compatibility matrix rows with linked test IDs and policy resolution notes (2026-02-19).
- [x] Added grouped/composite runid cookie round-trip integration coverage (`MX-L4`) from rq-engine issuance to browse consumption (2026-02-19).
- [x] Added `tests/integration/__init__.py` for directory consistency with package-style test layout (2026-02-19).

## Timeline

- **2026-02-19** - Package created and scoped from cross-service auth review findings.
- **2026-02-19** - Initial execution plan drafted under `prompts/active/`.
- **2026-02-19** - Matrix-driven integration and lifecycle tests implemented and validated.
- **2026-02-19** - Primitive unit-gap tests and full validation gates completed.

## Decisions

### 2026-02-19: Start with executable contract matrix before broad test writing
**Context**: Multiple findings were caused by assumptions about which token classes should be accepted by each service.

**Options considered**:
1. Add tests opportunistically without a matrix.
2. Freeze matrix first, then implement tests against it.

**Decision**: Freeze and publish a compatibility matrix first, then implement tests directly from that matrix.

**Impact**: Reduced rework and avoided contradictory test assumptions.

---

### 2026-02-19: Keep MCP token class restrictions as canonical on MCP routes
**Context**: Review findings proposed acceptance of user tokens by MCP, but implementation requires `token_class=mcp`.

**Options considered**:
1. Change MCP policy to accept user tokens.
2. Keep MCP policy and test/document it explicitly.

**Decision**: Keep current MCP policy and codify it in matrix/tests/docs unless a separate policy change is requested.

**Impact**: Preserved scope discipline and current implementation contracts.

---

### 2026-02-19: Patch Redis as an autouse integration fixture
**Context**: First portability run failed (`AttributeError: 'RecordingRedis' object has no attribute 'setex'`) because tests not explicitly requesting the fixture fell back to the global suite stub.

**Options considered**:
1. Add `integration_redis` fixture argument to every integration test.
2. Make the integration Redis fixture autouse for the integration suite.

**Decision**: Make integration Redis fixture autouse.

**Impact**: Ensured consistent `setex`/TTL/revocation behavior for all integration cases.

---

### 2026-02-19: Document rq-engine conditional acceptance of WEPP-signed `token_class=mcp`
**Context**: rq-engine run access currently does not reject `token_class=mcp` when run scope and required scopes pass.

**Options considered**:
1. Change code to reject `mcp` class on rq-engine run routes.
2. Preserve behavior and document it as conditional.

**Decision**: Preserve behavior and document/test it (`MX-A5`) without contract broadening.

**Impact**: Maintained current auth contract while removing ambiguity in the matrix.

---

### 2026-02-19: Leave `token_class=mcp` behavior unchanged for now
**Context**: Follow-up policy direction requested whether to change rq-engine handling for WEPP-signed tokens carrying `token_class=mcp`.

**Options considered**:
1. Change implementation now to reject `token_class=mcp` on rq-engine run routes.
2. Leave behavior unchanged and keep conditional test/doc coverage.

**Decision**: Leave behavior unchanged for now.

**Impact**: Keeps current contracts stable and avoids a scope-expanding auth policy change in this package.

---

### 2026-02-19: Public browse access should remain permitted within existing root-only protections
**Context**: Follow-up policy direction clarified expected behavior for PUBLIC runs.

**Options considered**:
1. Harden public browse to fail on stale/invalid cookie contexts.
2. Preserve permissive public browse semantics.

**Decision**: Preserve permissive semantics for PUBLIC browse access on anonymous-eligible, non-root-only paths.

**Impact**: Public runs remain accessible on anonymous-eligible, non-root-only paths even when cookie auth state is stale or invalid and no valid bearer token is present.

---

### 2026-02-19: Add explicit grouped-cookie integration round-trip coverage
**Context**: External review flagged that composite runid cookie behavior was covered by route-level suites but not by integration-level round-trip tests.

**Options considered**:
1. Keep existing per-service tests only.
2. Add a dedicated integration lifecycle case proving issuance-to-browse cookie round-trip for grouped runids.

**Decision**: Added `MX-L4` integration lifecycle test and linked it in the compatibility matrix.

**Impact**: Composite runid cookie success criterion is now covered at integration level, not only by isolated route tests.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Token class portability assumptions drift across services | High | Medium | Matrix rows now mapped to executable tests and integrated case IDs | Mitigated |
| Revocation handling diverges between services | High | Medium | `MX-L2` validates denylist behavior across rq-engine, browse, and MCP | Mitigated |
| Rotation behavior differs by service config | Medium | Medium | `MX-L3` validates overlap + retirement for WEPP auth consumers | Mitigated |
| Integration tests become flaky due to fixture coupling | Medium | Low | Shared deterministic harness and autouse Redis fixture | Low residual |

## Verification Checklist

### Code Quality
- [x] `wctl run-pytest tests/integration/test_cross_service_auth_portability.py -q`
- [x] `wctl run-pytest tests/integration/test_cross_service_auth_lifecycle.py -q`
- [x] `wctl run-pytest tests/weppcloud/test_auth_tokens.py tests/microservices/test_rq_engine_auth.py -q`
- [x] `wctl run-pytest tests/weppcloud/routes/test_rq_engine_token_api.py tests/microservices/test_rq_engine_session_routes.py tests/microservices/test_browse_auth_routes.py tests/query_engine/test_mcp_auth.py`

### Frontend and Documentation
- [x] `wctl run-npm test -- http`
- [x] `wctl doc-lint --path docs/work-packages/20260219_cross_service_auth_tokens`
- [x] `wctl doc-lint --path docs/dev-notes/auth-token.spec.md`

### Behavioral Acceptance
- [x] Browser renewal fallback path validated in integrated tests (`MX-L1`).
- [x] Revoked tokens rejected consistently by rq-engine, browse, and MCP (`MX-L2`).
- [x] Rotation overlap and retirement validated with deterministic fixtures (`MX-L3`).

## Progress Notes

### 2026-02-19: Package bootstrap
**Agent/Contributor**: Codex

**Work completed**:
- Created package scaffold.
- Drafted package brief/tracker.
- Authored active ExecPlan.
- Added backlog entry in `PROJECT_TRACKER.md`.

**Blockers encountered**:
- None.

**Next steps**:
- Build matrix and execute integration milestones.

**Test results**:
- Pending (docs setup only).

### 2026-02-19: Compatibility matrix draft
**Agent/Contributor**: Codex

**Work completed**:
- Added initial matrix artifact.
- Captured compatibility assumptions and open policy questions.

**Blockers encountered**:
- None.

**Next steps**:
- Convert matrix into executable portability/lifecycle tests.

**Test results**:
- `wctl doc-lint --path docs/work-packages/20260219_cross_service_auth_tokens` (initially pending).

### 2026-02-19: Integrated implementation and validation closeout
**Agent/Contributor**: Codex

**Work completed**:
- Landed integration harness + portability + lifecycle suites.
- Landed primitive unit-gap coverage.
- Linked every matrix row to concrete test case IDs.
- Recorded command evidence in `artifacts/lifecycle_validation_results.md`.
- Ran all campaign validation gates to green.

**Blockers encountered**:
- Initial portability run failed because the non-autouse integration Redis fixture was bypassed; fixed by making it autouse.

**Next steps**:
- Handoff and policy review only (no blocking engineering work remains in this package).

**Test results**:
- Portability suite: pass (`6 passed`).
- Lifecycle suite: pass (`3 passed`).
- Primitive unit-gap suite: pass (`35 passed`).
- Broader auth slice: pass (`120 passed`).
- Frontend fallback tests: pass (`13 passed`).
- Doc lint (package + spec): pass.

### 2026-02-19: Post-closeout follow-up from external review
**Agent/Contributor**: Codex

**Work completed**:
- Added grouped/composite runid lifecycle integration case (`MX-L4`) in `tests/integration/test_cross_service_auth_lifecycle.py`.
- Added integration package marker file `tests/integration/__init__.py`.
- Updated matrix case index and cookie-surface mappings to include `MX-L4`.
- Recorded follow-up validation evidence in `artifacts/lifecycle_validation_results.md`.

**Blockers encountered**:
- None.

**Next steps**:
- None required for this package scope.

**Test results**:
- `wctl run-pytest tests/integration/test_cross_service_auth_lifecycle.py -q`: pass (`4 passed`).
- `wctl run-pytest tests/integration/test_cross_service_auth_portability.py -q`: pass (`6 passed`).
- `wctl doc-lint --path docs/work-packages/20260219_cross_service_auth_tokens`: pass.

## Watch List

- **Policy baseline**: keep `token_class=mcp` handling unchanged unless a separate auth policy package is approved.
- **Policy baseline**: PUBLIC browse access should remain permitted on anonymous-eligible, non-root-only paths; do not regress to auth-hard-fail behavior for anonymous public browsing.
- **Coverage growth**: consider a dedicated run-mutation/export route integration slice if enforcement diverges from shared auth helpers.

## Communication Log

### 2026-02-19: Campaign request
**Participants**: User, Codex  
**Question/Topic**: Execute cross-service auth token hardening package end-to-end.  
**Outcome**: Milestones completed with validation evidence and synchronized package artifacts.
