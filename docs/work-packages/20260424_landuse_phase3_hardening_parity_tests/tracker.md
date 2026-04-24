# Tracker - Landuse Phase 3 Hardening Parity Tests and Migration Gate

> Living document tracking progress, decisions, risks, and verification evidence for this package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-24 05:29 UTC  
**Current phase**: Complete (Gate 3 closed)  
**Last updated**: 2026-04-24 06:04 UTC  
**Next milestone**: None (package complete).  
**Security impact**: `high`  
**Dedicated security review**: `yes`  
**Security artifact**: `docs/work-packages/20260424_landuse_phase3_hardening_parity_tests/artifacts/2026-04-24_security_review.md`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None currently.

### Done
- [x] Created package scaffold (`package.md`, `tracker.md`, `prompts/active/`, `prompts/completed/`, `artifacts/`, `notes/`) (2026-04-24 05:29 UTC).
- [x] Drafted active Gate 3 ExecPlan with hardening parity test tracks and validation gates (2026-04-24 05:29 UTC).
- [x] Drafted hardening parity test matrix artifact (2026-04-24 05:29 UTC).
- [x] Created dedicated security review artifact for Gate 3 entry and SEC-02 closure tracking (2026-04-24 05:29 UTC).
- [x] Added/expanded baseline WEPPcloud hardening tests for Phase 3 rows (path/archive caps/conflicts, map validation/rollback, render-route transport config) in `tests/weppcloud/routes/test_landuse_bp.py` (2026-04-24 06:04 UTC).
- [x] Implemented and validated rq-engine Phase 3 replacements for moved landuse surfaces in `wepppy/microservices/rq_engine/landuse_routes.py` with parity tests in `tests/microservices/test_rq_engine_landuse_routes.py` (2026-04-24 06:04 UTC).
- [x] Completed endpoint discovery/schema/OpenAPI parity updates for moved surfaces (`schema_defaults_routes.py`, schema/default tests, OpenAPI contract budgets/docs) (2026-04-24 06:04 UTC).
- [x] Closed Gate 3 security findings (SEC-02/07/08/09/10/11) with executed validation evidence and no unresolved medium/high findings (2026-04-24 06:04 UTC).

## Timeline

- **2026-04-24 05:29 UTC** - Package created and scoped as dedicated Gate 3 follow-up.
- **2026-04-24 05:29 UTC** - Hardening parity matrix and security gate artifact drafted.
- **2026-04-24 06:04 UTC** - Baseline hardening tests expanded and Phase 3 rq-engine parity suites completed.
- **2026-04-24 06:04 UTC** - Gate 3 validation command set executed successfully; security artifact and matrix closed.

## Decisions Log

### 2026-04-24 05:29 UTC: Split Gate 3 into dedicated package with test-first posture
**Context**: Prior landuse migration package intentionally stopped at Gate 2 and deferred high-risk surfaces.

**Options considered**:
1. Move Phase 3 routes directly and add tests opportunistically.
2. Open a dedicated Gate 3 package and require hardening parity tests before movement.

**Decision**: Option 2.

**Impact**: Makes path/archive/concurrency/atomicity parity a hard precondition rather than post-cutover cleanup.

---

### 2026-04-24 05:29 UTC: Keep render routes explicitly out of Phase 3 scope
**Context**: Route boundary was already established in prior package and must remain stable.

**Options considered**:
1. Re-open render-route migration discussion during Phase 3.
2. Preserve render routes in WEPPcloud and focus only on machine/state map/catalog/file surfaces.

**Decision**: Option 2.

**Impact**: Reduces migration risk and keeps Gate 3 focused on high-risk API surfaces.

---

### 2026-04-24 06:04 UTC: Complete transport cutover for moved surfaces without migrating render routes
**Context**: Moved mutators/reads required bearer token bridge, while render route ownership remained fixed in WEPPcloud.

**Options considered**:
1. Keep map/catalog templates on cookie-bound mutator calls and rely on rq-engine cookie fallback behavior.
2. Require explicit session-token bridge (`requestWithSessionToken`) for moved routes and keep render routes unchanged.

**Decision**: Option 2.

**Impact**: Preserves CSRF/session boundary policy and prevents cookie-mutation fallback on rq-engine mutators while honoring non-negotiable render-route constraints.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Hardening behavior regresses during Flask -> rq-engine movement | High | Medium | Freeze baseline with explicit parity tests before route movement | Closed |
| Missing test coverage for atomic rollback/concurrency edge cases | High | Medium | Add explicit failure-path and stale-precondition tests before cutover | Closed |
| Browser transport drift on moved surfaces | Medium | Medium | Require `requestWithSessionToken` and JS regression checks in Gate 3.2 | Closed |
| Route contract/documentation drift after migration | Medium | Medium | Block closure on OpenAPI/discovery/doc-lint parity gates | Closed |

## Verification Checklist

### Hardening Parity
- [x] Path containment checks parity is tested and green.
- [x] Archive upload abuse checks parity is tested and green.
- [x] Optimistic concurrency (`if_match_sha256` / stale lookup) parity is tested and green.
- [x] Atomic write/rollback parity is tested and green.

### Auth and Transport
- [x] rq-engine token/scope/token-class matrix is tested for moved Phase 3 routes.
- [x] Browser client routes moved in Phase 3 use `requestWithSessionToken`.
- [x] No cookie-mutation fallback introduced for rq-engine mutators.

### Contracts and Discovery
- [x] Endpoint catalog/defaults/schema entries include all moved Phase 3 operations.
- [x] OpenAPI required response codes align with route behavior.
- [x] `rq-engine-agent-api-contract.md`, `rq-response-contract.md`, and `weppcloud-csrf-contract.md` updated.

### Security
- [x] Dedicated security artifact updated through Gate 3 closure.
- [x] No unresolved medium/high findings for moved surfaces.
- [x] SEC-02 from prior package is explicitly closed with evidence.

## Progress Notes

### 2026-04-24 05:29 UTC: Package preparation
**Agent/Contributor**: Codex

**Work completed**:
- Created a dedicated Gate 3 package scaffold.
- Added package brief and active ExecPlan with explicit hardening parity gates.
- Added hardening parity test matrix artifact and dedicated security review artifact.
- Prepared tracker tasks for test-first Phase 3 execution.

**Blockers encountered**:
- None.

**Next steps**:
- Validate/adjust final Phase 3 endpoint path mapping.
- Implement and run baseline + parity hardening tests.
- Start controlled route movement only after Gate 3.0/3.1 criteria pass.

**Test results**:
- Not run (documentation/scaffolding only).

### 2026-04-24 06:04 UTC: Gate 3 execution and closure
**Agent/Contributor**: Codex

**Work completed**:
- Completed Phase 3 rq-engine route movement for deferred landuse surfaces:
  - `/landuse-user-defined/catalog|upload|delete|update-description`
  - `/landuse-map/snapshot|save|clear-override`
  - `/modify-landuse`
- Expanded baseline WEPPcloud hardening tests to freeze previously uncovered rows (upload size caps/conflicts, invalid-row validation, rollback restoration, and render route rq-engine transport config).
- Updated browser transport for moved surfaces to session-token bridge bearer policy (including `landuse_map` template and landuse controllers).
- Updated endpoint discovery/schema defaults and OpenAPI contract budgets to keep moved surfaces represented and validated.
- Closed dedicated security review findings with evidence.

**Blockers encountered**:
- `schema_defaults_routes.py` initially passed unsupported `auth_requirements` kwargs into `_base_run_read_descriptor`; fixed by using default read-auth descriptor contract.
- `test_rq_engine_landuse_routes.py` phase-3 helper token lacked read scope; fixed helper to issue `rq:enqueue rq:read` for mixed read/mutate parity tests.

**Test results**:
- `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1` -> `24 passed`
- `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1` -> `39 passed`
- `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` -> `54 passed`
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` -> `10 passed`
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js` -> `20 passed`
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js` -> `3 passed`
- `wctl doc-lint --path docs/work-packages/20260424_landuse_phase3_hardening_parity_tests --path docs/schemas/rq-engine-agent-api-contract.md --path docs/schemas/rq-response-contract.md --path docs/schemas/weppcloud-csrf-contract.md --path PROJECT_TRACKER.md` -> `10 files validated, 0 errors, 0 warnings`

## Communication Log

### 2026-04-24 05:29 UTC: User request
**Participants**: User, Codex  
**Question/Topic**: Prepare a work-package for Phase 3 with hardening parity tests.  
**Outcome**: New dedicated Gate 3 package scaffolded with active ExecPlan, parity test matrix, and security gate artifact.

### 2026-04-24 06:04 UTC: Package execution request
**Participants**: User, Codex  
**Question/Topic**: Execute active Gate 3 package end-to-end and close lifecycle artifacts.  
**Outcome**: Gate 3.0/3.1/3.2/3.3 all passed, security findings closed, required validations green, and package marked complete.
