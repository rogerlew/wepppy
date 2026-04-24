# Tracker - Landuse First-Class Agent Interface Migration

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-24 04:01 UTC  
**Current phase**: Completed (Gate 0-2 passed; Gate 3 intentionally not entered)  
**Last updated**: 2026-04-24 05:29 UTC  
**Next milestone**: Execute follow-up package `20260424_landuse_phase3_hardening_parity_tests` and pass Gate 3.  
**Security impact**: `high`  
**Dedicated security review**: `yes`  
**Security artifact**: `docs/work-packages/20260423_landuse_first_class_agent_interface_migration/artifacts/2026-04-24_security_review.md`

## Task Board

### Ready / Backlog
- [ ] Execute follow-up package `docs/work-packages/20260424_landuse_phase3_hardening_parity_tests/` for Gate 3 hardening parity and security closure.

### In Progress
- [ ] None.

### Blocked
- [ ] None currently.

### Done
- [x] Created package scaffold and active artifacts (2026-04-24 04:01 UTC).
- [x] Finalized Gate 0 decisions (PUP/active-root, token-class policy, browser transport policy) (2026-04-24 04:26 UTC).
- [x] Implemented Phase 1 rq-engine replacements for `set-landuse-mode`, `set-landuse-db`, `modify-landuse-coverage` (2026-04-24 04:31 UTC).
- [x] Migrated WEPPcloud browser caller transport to `requestWithSessionToken` for Phase 1 moved routes (2026-04-24 04:31 UTC).
- [x] Implemented Phase 2 read/discovery parity (`controllers/landuse/state` + endpoint catalog coverage) (2026-04-24 04:31 UTC).
- [x] Documented legacy Flask compatibility/deprecation policy with explicit sunset criteria (2026-04-24 04:36 UTC).
- [x] Recorded Phase 3 no-go disposition for this package (surfaces remain in WEPPcloud; Gate 3 not entered) (2026-04-24 04:36 UTC).
- [x] Updated package/contract docs and project tracker lifecycle state; moved ExecPlan to completed (2026-04-24 04:36 UTC).
- [x] Revised legacy deprecation policy to remove calendar hold (no-delay removal posture) (2026-04-24 05:02 UTC).
- [x] Prepared dedicated Gate 3 follow-up package scaffold (`20260424_landuse_phase3_hardening_parity_tests`) (2026-04-24 05:29 UTC).

## Timeline

- **2026-04-24 04:01 UTC** - Package initialized with ExecPlan, tracker, security artifact.
- **2026-04-24 04:26 UTC** - Gate 0 decisions recorded and approved for implementation scope.
- **2026-04-24 04:31 UTC** - Phase 1 + Phase 2 code and tests landed.
- **2026-04-24 04:36 UTC** - Closure docs completed, security artifact updated, project tracker updated, ExecPlan moved to `prompts/completed/`.
- **2026-04-24 05:29 UTC** - Dedicated Gate 3 follow-up package created with hardening parity test matrix and security gate scaffold.

## Decisions Log

### 2026-04-24 04:26 UTC: PUP/active-root strategy
**Decision**: rq-engine migrated landuse routes resolve run root from `get_wd(runid, prefer_active=False)` and honor optional `?pup=` only under `_pups/` with containment checks; composite runids (`;;`) ignore `pup` and use encoded context.

**Impact**: Preserves run-scope behavior while preventing traversal and ambiguous context targeting.

---

### 2026-04-24 04:26 UTC: Token-class/scope policy for migrated mutators
**Decision**: `rq:enqueue` required, run access required, and token class must be one of `user`, `session`, `service`, `mcp`.

**Impact**: Prevents unknown token classes and keeps mutation auth explicit.

---

### 2026-04-24 04:26 UTC: Browser transport strategy
**Decision**: moved browser mutators call `/rq-engine/api/...` using `requestWithSessionToken`; no cookie-mutation fallback added to rq-engine mutators.

**Impact**: Keeps bearer-token mutation contract for rq-engine and avoids CSRF-coupled fallback paths.

---

### 2026-04-24 04:36 UTC: Phase 3 disposition
**Decision**: Gate 3 not entered in this package; map/catalog/file surfaces remain in WEPPcloud.

**Impact**: High-risk surface movement deferred to follow-up package with required hardening parity tests and security closure.

---

### 2026-04-24 05:02 UTC: Remove calendar-based deprecation delay
**Decision**: Legacy Flask landuse mutator deprecation keeps immediate effect and no fixed-date hold; removal package can proceed as soon as readiness criteria are met.

**Impact**: Reduces operational overhead from maintaining long-lived dual route contracts while preserving explicit readiness and security criteria.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| PUP/active-root context drift in migrated routes | High | Medium | Explicit `?pup=` strategy with containment checks + tests | Closed (Gate 0/1) |
| Loss of existing map/catalog hardening during route move | High | Medium | Keep surfaces in WEPPcloud; require Gate 3 for future move | Deferred to follow-up |
| Browser transport regression for moved routes | Medium | High | `requestWithSessionToken` migration + JS tests | Closed (Gate 1) |
| Auth-surface widening for `service`/`mcp` tokens | Medium | Medium | Explicit token-class policy + negative tests | Closed (Gate 1) |
| Endpoint discovery drift (undocumented migrated ops) | Medium | Medium | Added operation metadata + openapi/discovery tests | Closed (Gate 2) |
| `wctl run-pytest` instability (exit 137) reduced container-based evidence | Medium | Medium | Verified equivalent suites via `.venv/bin/pytest`; recorded both command outcomes | Accepted residual environment risk |

## Verification Checklist

### Code Quality
- [x] Targeted tests pass for migrated Phase 1/2 routes.
- [x] OpenAPI and endpoint-catalog contracts updated for migrated operations.
- [x] No silent fallbacks introduced in migrated rq-engine routes.

### Security
- [x] Security impact triage documented (`high`) with rationale.
- [x] Dedicated security artifact updated through closure.
- [x] No unresolved medium/high findings for moved surfaces (Phase 1/2).
- [x] Auth/session/CSRF boundary changes validated for moved surfaces.

### Documentation
- [x] Package/tracker/ExecPlan/security artifact updated through closure.
- [x] Contract docs updated with behavior changes.
- [x] Legacy compatibility/deprecation policy documented with explicit sunset criteria.

### Testing
- [x] Auth matrix tests added/passing for migrated routes.
- [x] Browser transport tests for migrated routes passing.
- [x] Discovery/openapi parity tests passing.
- [x] Required WEPPcloud landuse route tests passing.
- [ ] Phase 3 hardening-parity tests not run in this package (Gate 3 not entered).

### Deployment
- [x] Validation evidence collected for shipped Phase 1/2 scope.
- [x] Roll-forward/rollback posture documented via phased gate model.

## Progress Notes

### 2026-04-24 04:31 UTC: Phase 1 + 2 implementation and parity
**Agent/Contributor**: Codex

**Work completed**:
- Added rq-engine mutator routes for:
  - `POST /api/runs/{runid}/{config}/set-landuse-mode`
  - `POST /api/runs/{runid}/{config}/set-landuse-db`
  - `POST /api/runs/{runid}/{config}/modify-landuse-coverage`
- Added rq-engine read route:
  - `GET /api/runs/{runid}/{config}/controllers/landuse/state`
- Added token-class helper in rq-engine auth and enforced token-class policy on migrated mutators.
- Added endpoint catalog/schema/default coverage for migrated landuse operations and existing `modify-landuse-mapping`.
- Updated `landuse.js` to call migrated rq-engine routes with `requestWithSessionToken`.

**Validation evidence**:
- `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1` -> exit `137`; fallback `.venv/bin/pytest ...` -> `28 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` -> exit `137`; fallback `.venv/bin/pytest ...` -> `10 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` -> exit `137`; fallback `.venv/bin/pytest ...` -> `54 passed`.
- `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1` -> exit `137`; fallback `.venv/bin/pytest ...` -> `19 passed`.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js` -> `20 passed`.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js` -> `3 passed`.

### 2026-04-24 04:36 UTC: Package closure
**Agent/Contributor**: Codex

**Work completed**:
- Updated package and schema contracts for Gate 0/1/2 outcomes.
- Documented explicit compatibility/deprecation policy and sunset criteria.
- Updated security artifact finding status and gate disposition.
- Moved ExecPlan to `prompts/completed/` with closure outcomes.
- Updated `PROJECT_TRACKER.md` from Backlog -> In Progress -> Done lifecycle state.

**Validation evidence**:
- `wctl doc-lint --path docs/work-packages/20260423_landuse_first_class_agent_interface_migration --path docs/schemas/rq-engine-agent-api-contract.md --path docs/schemas/rq-response-contract.md --path docs/schemas/weppcloud-csrf-contract.md --path PROJECT_TRACKER.md` -> pass (recorded at closure).

### 2026-04-24 05:02 UTC: Documentation policy revision (no code changes)
**Agent/Contributor**: Codex

**Work completed**:
- Updated package docs to remove date-gated deprecation delay for legacy Flask landuse mutator routes.
- Replaced calendar hold language with readiness-based removal criteria.
- Recorded decision and rationale in tracker and completed ExecPlan.

**Validation evidence**:
- `wctl doc-lint --path docs/work-packages/20260423_landuse_first_class_agent_interface_migration` -> pass.

## Communication Log

### 2026-04-24 04:16 UTC: Execution kickoff
**Participants**: User, Codex  
**Question/Topic**: Execute work package end-to-end with phased gates and security constraints.  
**Outcome**: Gate-based implementation executed; package closed with Phase 1/2 delivered and Phase 3 explicitly deferred by no-go gate.
