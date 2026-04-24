# Landuse First-Class Agent Interface Migration (Phased rq-engine Cutover)

**Status**: Complete (2026-04-24)  
**Timezone**: UTC

## Overview
Landuse machine/state APIs were migrated to first-class rq-engine interfaces in phased gates. WEPPcloud render routes remain in WEPPcloud. Phase 1 delivered low-risk mutator cutover; Phase 2 delivered read/discovery parity; Phase 3 high-risk map/catalog/file movement was intentionally deferred because Gate 3 was not entered in this package.

## Objectives
- Migrate landuse machine/state APIs to rq-engine with explicit gate controls.
- Preserve canonical auth/contracts for agent clients.
- Keep WEPPcloud render routes in WEPPcloud.
- Finalize Gate 0 decisions before migration code.
- Deliver Phase 1 and Phase 2 outcomes with validation evidence.
- Document explicit compatibility/deprecation policy for legacy Flask routes.

## Final Scope Disposition

### Delivered in this package
- **Gate 0 strategy decisions finalized**:
  - PUP/active-root strategy for migrated routes.
  - token-class/scope policy for migrated mutators.
  - browser transport strategy (`requestWithSessionToken`) for moved browser calls.
- **Phase 1**:
  - rq-engine replacements for:
    - `tasks/set_landuse_mode/` -> `POST /api/runs/{runid}/{config}/set-landuse-mode`
    - `tasks/set_landuse_db/` -> `POST /api/runs/{runid}/{config}/set-landuse-db`
    - `tasks/modify_landuse_coverage/` -> `POST /api/runs/{runid}/{config}/modify-landuse-coverage`
  - WEPPcloud browser caller cutover for moved routes in `landuse.js` via `requestWithSessionToken`.
- **Phase 2**:
  - `GET /api/runs/{runid}/{config}/controllers/landuse/state`
  - endpoint catalog/schema/default coverage for migrated landuse operations.

### Explicitly retained in WEPPcloud (not moved)
- `/runs/{runid}/{config}/report/landuse`
- `/runs/{runid}/{config}/landuse-user-defined`
- `/runs/{runid}/{config}/landuse-map`

### Deferred to follow-up package (Gate 3 required)
- `api/landuse/user_defined/catalog`
- `api/landuse/map_snapshot`
- `tasks/landuse/user_defined/upload|delete|update-description`
- `tasks/landuse/map/save|clear-override`
- `tasks/modify_landuse/` (if still required by UX)

## Gate Outcomes

- **Gate 0**: PASS (strategy decisions recorded in ExecPlan + tracker + security artifact)
- **Gate 1**: PASS (Phase 1 route/auth/transport tests passed)
- **Gate 2**: PASS (discovery/openapi parity tests passed)
- **Gate 3**: NOT ENTERED (no high-risk surface moved)

## Legacy Compatibility and Deprecation Policy

Legacy Flask compatibility routes are deprecated immediately and queued for prioritized removal:
- `/runs/{runid}/{config}/tasks/set_landuse_mode/`
- `/runs/{runid}/{config}/tasks/set_landuse_db/`
- `/runs/{runid}/{config}/tasks/modify_landuse_coverage[/]`

### Policy
- Effective deprecation start: **2026-04-24**.
- No calendar hold is required before removal.
- Removal must occur in a dedicated follow-up package.

### Sunset Criteria (all required)
1. No in-repo browser or service caller still targets the legacy Flask landuse mutator routes.
2. rq-engine replacement route tests for mode/db/coverage and auth matrix are green in the removal change set.
3. Endpoint-discovery docs continue to advertise canonical rq-engine operations for these actions.
4. Security artifact for the removal package confirms no unresolved medium/high findings on affected surfaces.
5. Route removal/change notes update:
   - `docs/schemas/rq-engine-agent-api-contract.md`
   - `docs/schemas/rq-response-contract.md`
   - `docs/schemas/weppcloud-csrf-contract.md`

## Contract and Schema Updates
Updated as part of this package:
- `docs/schemas/rq-engine-agent-api-contract.md`
- `docs/schemas/rq-response-contract.md`
- `docs/schemas/weppcloud-csrf-contract.md`

## Validation Evidence

Required validations executed:
- `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1` -> exit `137`; fallback `.venv/bin/pytest ...` -> `28 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` -> exit `137`; fallback `.venv/bin/pytest ...` -> `10 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` -> exit `137`; fallback `.venv/bin/pytest ...` -> `54 passed`.
- `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1` -> exit `137`; fallback `.venv/bin/pytest ...` -> `19 passed`.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js` -> `20 passed`.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js` -> `3 passed`.
- `wctl doc-lint --path docs/work-packages/20260423_landuse_first_class_agent_interface_migration --path docs/schemas/rq-engine-agent-api-contract.md --path docs/schemas/rq-response-contract.md --path docs/schemas/weppcloud-csrf-contract.md --path PROJECT_TRACKER.md` -> pass.

## Deliverables
- Completed phased Gate 0-2 implementation and validation evidence.
- Updated package tracker, completed ExecPlan, and security artifact.
- Updated schema/contract docs for migrated routes and auth/transport policy.
- Explicit compatibility/deprecation policy with no-delay removal posture and sunset criteria.

## Follow-up Work
- Execute dedicated Gate 3 package [20260424_landuse_phase3_hardening_parity_tests](../20260424_landuse_phase3_hardening_parity_tests/package.md) to migrate map/catalog/file surfaces only after hardening parity and security checks pass.
- Open a dedicated legacy route removal package as soon as sunset criteria are met.
