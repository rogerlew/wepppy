# Landuse Phase 3 Hardening Parity Tests and Migration Gate

**Status**: Complete (2026-04-24 06:04 UTC)  
**Timezone**: UTC

## Overview
This package prepares and executes Gate 3 for landuse map/catalog/file route migration by making hardening parity test coverage explicit, executable, and blocking. The prior migration package delivered Gate 0-2 and intentionally deferred high-risk surfaces; this package is the required follow-up to prove path, archive, concurrency, and atomic-write parity before any Phase 3 route movement.

## Objectives
- Define and implement a hardening parity test suite for deferred landuse Phase 3 surfaces.
- Establish current WEPPcloud behavior as the parity baseline for security-sensitive outcomes.
- Require parity + security gate pass before moving map/catalog/file surfaces to rq-engine.
- Keep WEPPcloud render routes in WEPPcloud.
- Produce migration-ready evidence so Phase 3 can proceed without bypassing Gate 3.

## Scope

### Included
- Hardening parity test matrix and execution plan for deferred surfaces:
  - `api/landuse/user_defined/catalog`
  - `tasks/landuse/user_defined/upload|delete|update-description`
  - `api/landuse/map_snapshot`
  - `tasks/landuse/map/save|clear-override`
  - `tasks/modify_landuse/`
- Baseline WEPPcloud test coverage expansion where parity behaviors are not yet frozen.
- rq-engine parity test coverage for Phase 3 replacement routes.
- Discovery/OpenAPI contract parity checks for moved Phase 3 operations.
- Security-gate evidence updates and explicit SEC-02 closure criteria.

### Explicitly Out of Scope
- Moving UI render routes from WEPPcloud:
  - `/runs/{runid}/{config}/report/landuse`
  - `/runs/{runid}/{config}/landuse-user-defined`
  - `/runs/{runid}/{config}/landuse-map`
- Introducing cookie-mutation fallback for rq-engine mutators.
- Silent fallback error behavior.
- Legacy Phase 1 mutator removal (handled in dedicated deprecation/removal package).

## Required Gate Outcomes

- **Gate 3.0 (Baseline Freeze)**: Current WEPPcloud hardening behaviors are explicitly frozen in tests.
- **Gate 3.1 (rq-engine Parity)**: rq-engine Phase 3 replacements match frozen hardening behavior and explicit error contracts.
- **Gate 3.2 (Transport/Auth/Discovery)**: browser transport, token policy, and endpoint catalog parity are green for moved surfaces.
- **Gate 3.3 (Security Closure)**: no unresolved medium/high findings for moved surfaces; SEC-02 closed with evidence.

## Hardening Parity Test Matrix
- Canonical matrix artifact: `docs/work-packages/20260424_landuse_phase3_hardening_parity_tests/artifacts/2026-04-24_hardening_parity_test_matrix.md`

## Stakeholders
- **Primary**: WEPPcloud/rq-engine maintainers for landuse route ownership and security posture.
- **Reviewers**: Landuse maintainers and rq-engine contract maintainers.
- **Security Reviewer**: required (`high` impact package).
- **Informed**: agent operators consuming landuse map/catalog/file endpoints.

## Success Criteria
- [x] Hardening parity test matrix is complete, approved, and linked to concrete test modules.
- [x] Baseline WEPPcloud hardening tests are green and capture all Gate 3 threat classes.
- [x] rq-engine Phase 3 parity tests are green for path/archive/concurrency/atomicity and contract behavior.
- [x] Discovery/OpenAPI parity tests are green for all moved Phase 3 operations.
- [x] Dedicated security artifact is complete with no unresolved medium/high findings for moved surfaces.
- [x] Migration/no-go decision is recorded with explicit evidence links.

## Dependencies

### Prerequisites
- Completed package: `docs/work-packages/20260423_landuse_first_class_agent_interface_migration/`
- Security baseline: `docs/work-packages/20260423_landuse_first_class_agent_interface_migration/artifacts/2026-04-24_security_review.md`
- Existing landuse hardening behavior in:
  - `wepppy/weppcloud/routes/nodb_api/landuse_bp.py`
  - `tests/weppcloud/routes/test_landuse_bp.py`

### Blocks
- Phase 3 route movement for map/catalog/file surfaces.
- SEC-02 closure from the prior security review.

## Related Packages
- **Depends on**: [20260423_landuse_first_class_agent_interface_migration](../20260423_landuse_first_class_agent_interface_migration/package.md)
- **Related**: [20260423_landuse_user_defined_management_catalog_map](../20260423_landuse_user_defined_management_catalog_map/package.md)
- **Follow-up**: dedicated Phase 3 cutover package closure, and separate legacy deprecation/removal package when readiness criteria are met.

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions.
- **Complexity**: High.
- **Risk level**: High.

## Security Impact and Review Gate
- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: route movement touches untrusted upload/archive handling, run-root path containment, optimistic concurrency preconditions, and atomic map/catalog mutation behavior.
- **Security review artifact**: `docs/work-packages/20260424_landuse_phase3_hardening_parity_tests/artifacts/2026-04-24_security_review.md`

## Validation Commands (executed)
- `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1`
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js`
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js`
- `wctl doc-lint --path docs/work-packages/20260424_landuse_phase3_hardening_parity_tests --path docs/schemas/rq-engine-agent-api-contract.md --path docs/schemas/rq-response-contract.md --path docs/schemas/weppcloud-csrf-contract.md --path PROJECT_TRACKER.md`

## References
- `docs/work-packages/20260423_landuse_first_class_agent_interface_migration/package.md`
- `docs/work-packages/20260423_landuse_first_class_agent_interface_migration/tracker.md`
- `docs/work-packages/20260423_landuse_first_class_agent_interface_migration/prompts/completed/landuse_first_class_agent_interface_migration_execplan.md`
- `docs/work-packages/20260423_landuse_first_class_agent_interface_migration/artifacts/2026-04-24_security_review.md`
- `wepppy/weppcloud/routes/nodb_api/landuse_bp.py`
- `tests/weppcloud/routes/test_landuse_bp.py`
- `wepppy/microservices/rq_engine/landuse_routes.py`
- `docs/prompt_templates/codex_exec_plans.md`

## Deliverables
- Package scaffold with completed ExecPlan, tracker, and closed security gate artifact.
- Hardening parity test matrix with complete baseline/rq-engine evidence mapping.
- Gate 3 exit criteria linked to executed validation commands and test outcomes.

## Kickoff Prompt
- Completed ExecPlan: `docs/work-packages/20260424_landuse_phase3_hardening_parity_tests/prompts/completed/landuse_phase3_hardening_parity_execplan.md`
