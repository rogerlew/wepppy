# Landuse Legacy Flask State Route Removal (Post Gate 3)

**Status**: Complete (2026-04-24 06:33 UTC)  
**Timezone**: UTC

## Overview
Gate 3 has passed for Phase 3 landuse map/catalog/file migration. This package removes legacy Flask compatibility state routes from `landuse_bp` so rq-engine is the only machine/state API surface for landuse operations. Render routes remain in WEPPcloud.

## Objectives
- Remove deprecated Flask landuse state/mutator compatibility routes now superseded by rq-engine.
- Keep WEPPcloud render routes intact and functional.
- Ensure no in-repo callers target removed Flask compatibility endpoints.
- Preserve explicit error contracts and transport/auth boundaries after removal.
- Close deprecation lifecycle for landuse legacy state routes.

## Scope

### Included
- Remove legacy Flask compatibility routes in `wepppy/weppcloud/routes/nodb_api/landuse_bp.py` for migrated state/mutator operations.
- Update any in-repo callers/tests/docs that still reference removed Flask endpoints.
- Update route docs and schema contracts to reflect rq-engine as sole state API owner.
- Add regression coverage proving removed endpoints are no longer used and canonical rq-engine paths remain green.

### Explicitly Out of Scope
- Render route migration from WEPPcloud:
  - `/runs/{runid}/{config}/report/landuse`
  - `/runs/{runid}/{config}/landuse-user-defined`
  - `/runs/{runid}/{config}/landuse-map`
- New behavior/features for landuse processing.
- Any cookie-mutation fallback introduction for rq-engine mutators.

## Candidate Route Removal Set

Phase 1 legacy compatibility routes:
- `/runs/{runid}/{config}/tasks/set_landuse_mode/`
- `/runs/{runid}/{config}/tasks/set_landuse_db/`
- `/runs/{runid}/{config}/tasks/modify_landuse_coverage[/]`

Phase 3 legacy compatibility routes (if still present in Flask):
- `/runs/{runid}/{config}/api/landuse/user_defined/catalog`
- `/runs/{runid}/{config}/tasks/landuse/user_defined/upload`
- `/runs/{runid}/{config}/tasks/landuse/user_defined/delete`
- `/runs/{runid}/{config}/tasks/landuse/user_defined/update-description`
- `/runs/{runid}/{config}/api/landuse/map_snapshot`
- `/runs/{runid}/{config}/tasks/landuse/map/save`
- `/runs/{runid}/{config}/tasks/landuse/map/clear-override`
- `/runs/{runid}/{config}/tasks/modify_landuse/`
- `/runs/{runid}/{config}/tasks/modify_landuse_mapping/` (audit-driven; remove only if no in-repo callers)

## Completion Summary
- All candidate Flask compatibility routes above were removed from `wepppy/weppcloud/routes/nodb_api/landuse_bp.py`.
- WEPPcloud render routes remained in place and passed required render-route validation.
- rq-engine test suites, browser controller suites, and package/doc lint checks all passed.
- Dedicated security review closed with no unresolved medium/high findings.

## Stakeholders
- **Primary**: WEPPcloud/rq-engine maintainers owning landuse API boundaries.
- **Reviewers**: Landuse route and controller maintainers.
- **Security Reviewer**: required (`high` impact package).
- **Informed**: agent operators and UI maintainers.

## Success Criteria
- [x] Deprecated Flask state/mutator routes in scope are removed from `landuse_bp`.
- [x] Render routes remain unchanged and green.
- [x] No in-repo browser/service caller references removed Flask endpoints.
- [x] rq-engine route tests and WEPPcloud render tests pass after removal.
- [x] Contract docs/schemas and route README are updated to reflect final ownership.
- [x] Dedicated security review reports no unresolved medium/high findings.

## Dependencies

### Prerequisites
- Gate 3 completion package: `docs/work-packages/20260424_landuse_phase3_hardening_parity_tests/`.
- Prior deprecation policy and sunset criteria: `docs/work-packages/20260423_landuse_first_class_agent_interface_migration/package.md`.

### Blocks
- Final closure of legacy landuse dual-route operation.

## Related Packages
- **Depends on**: [20260424_landuse_phase3_hardening_parity_tests](../20260424_landuse_phase3_hardening_parity_tests/package.md)
- **Depends on**: [20260423_landuse_first_class_agent_interface_migration](../20260423_landuse_first_class_agent_interface_migration/package.md)
- **Related**: [20260423_landuse_user_defined_management_catalog_map](../20260423_landuse_user_defined_management_catalog_map/package.md)
- **Follow-up**: none expected if removal closes successfully.

## Timeline Estimate
- **Expected duration**: 1-3 focused sessions.
- **Complexity**: Medium.
- **Risk level**: High.

## Security Impact and Review Gate
- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: route-surface removal changes auth/session boundary and can accidentally reintroduce fallback behavior or leave stale exposed endpoints.
- **Security review artifact**: `docs/work-packages/20260424_landuse_legacy_flask_state_route_removal/artifacts/2026-04-24_security_review.md`

## Validation Commands (executed)
- `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1`
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1`
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js`
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js`
- `wctl doc-lint --path docs/work-packages/20260424_landuse_legacy_flask_state_route_removal --path wepppy/weppcloud/routes/nodb_api/README.md --path docs/schemas/rq-engine-agent-api-contract.md --path docs/schemas/rq-response-contract.md --path docs/schemas/weppcloud-csrf-contract.md --path PROJECT_TRACKER.md`

## References
- `docs/work-packages/20260423_landuse_first_class_agent_interface_migration/package.md`
- `docs/work-packages/20260424_landuse_phase3_hardening_parity_tests/package.md`
- `wepppy/weppcloud/routes/nodb_api/landuse_bp.py`
- `wepppy/weppcloud/routes/nodb_api/README.md`
- `wepppy/microservices/rq_engine/landuse_routes.py`
- `tests/weppcloud/routes/test_landuse_bp.py`
- `tests/microservices/test_rq_engine_landuse_routes.py`

## Deliverables
- Legacy Flask landuse state-route removal patch.
- Updated test coverage proving no in-repo dependency on removed endpoints.
- Updated route contract docs and package lifecycle artifacts.

## Kickoff Prompt
- Completed ExecPlan: `docs/work-packages/20260424_landuse_legacy_flask_state_route_removal/prompts/completed/landuse_legacy_flask_state_route_removal_execplan.md`
