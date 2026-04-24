# Landuse Phase 3 Hardening Parity Tests and Migration Gate

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package, Phase 3 landuse map/catalog/file surfaces can be migrated to rq-engine only when hardening parity is proven by tests and security closure, not by assumption. A user/operator should be able to run Gate 3 suites and see that path containment, archive controls, optimistic concurrency, and atomic rollback behaviors are unchanged after route movement.

## Progress

- [x] (2026-04-24 05:29 UTC) Created package scaffold and active ExecPlan.
- [x] (2026-04-24 05:29 UTC) Created hardening parity matrix artifact with explicit blocking rows.
- [x] (2026-04-24 05:29 UTC) Created dedicated Gate 3 security artifact with open findings and closure criteria.
- [x] (2026-04-24 06:04 UTC) Frozen Flask -> rq-engine Phase 3 route mapping and operation IDs for moved surfaces.
- [x] (2026-04-24 06:04 UTC) Implemented/expanded baseline WEPPcloud hardening tests for all required matrix rows.
- [x] (2026-04-24 06:04 UTC) Implemented rq-engine parity tests for moved Phase 3 surfaces.
- [x] (2026-04-24 06:04 UTC) Updated endpoint discovery/OpenAPI/contracts for moved surfaces.
- [x] (2026-04-24 06:04 UTC) Executed Gate 3 validation suites and closed security findings.
- [x] (2026-04-24 06:04 UTC) Recorded go decision and package closure outcomes.

## Surprises & Discoveries

- Observation: Prior migration package deliberately did not enter Gate 3, so SEC-02 remained open by design.
  Evidence: `docs/work-packages/20260423_landuse_first_class_agent_interface_migration/artifacts/2026-04-24_security_review.md`.

- Observation: Existing Flask landuse routes already implement substantial hardening behavior (run-root containment, archive validation hooks, stale-hash checks, and rollback helpers), which must be preserved exactly during migration.
  Evidence: `wepppy/weppcloud/routes/nodb_api/landuse_bp.py` map/catalog route implementations and current route tests.

- Observation: `schema_defaults_routes.py` failed when read-descriptor overrides used unsupported kwargs (`auth_requirements`) on `_base_run_read_descriptor`.
  Evidence: initial `test_rq_engine_schema_defaults_routes.py` failure and subsequent descriptor fix.

- Observation: Mixed read/mutate rq-engine parity tests require helper-issued scope strings containing both enqueue and read scopes for shared test sessions.
  Evidence: `test_landuse_phase3_catalog_upload_update_delete_via_rq_engine` required `rq:read` for catalog GET after mutating upload.

## Decision Log

- Decision: Gate 3 execution will be test-first; route movement is blocked until baseline hardening parity tests are complete and green.
  Rationale: Avoids migration-by-rewrite that can silently regress security controls.
  Date/Author: 2026-04-24 / Codex.

- Decision: Render routes remain in WEPPcloud throughout this package.
  Rationale: Prior gate decisions fixed route ownership boundaries; this package targets high-risk state APIs only.
  Date/Author: 2026-04-24 / Codex.

- Decision: Complete moved browser surfaces with token-bridge bearer transport and keep rq-engine mutators cookie-fallback-free.
  Rationale: Satisfies CSRF boundary contract while preserving explicit auth policy for moved routes.
  Date/Author: 2026-04-24 / Codex.

## Outcomes & Retrospective

Gate 3 closed with pass verdict (2026-04-24 06:04 UTC).

Hardening parity behaviors proven:
- Path containment and run-root escape rejection for user-defined catalog writes.
- Archive member policy enforcement and upload size boundary handling for `.man`/`.zip`.
- Catalog conflict handling (`CATALOG_CONFLICT`) without partial-write side effects.
- Snapshot freshness with no-store headers and deterministic lookup hashes.
- Optimistic concurrency enforcement (`PRECONDITION_REQUIRED`, `STALE_LOOKUP`).
- Invalid row schema rejection and rollback restoration on `build_managements` failure.
- Clear-override postconditions (relpath reset + file removal + prep timestamp path).

Phase 3 routes moved to rq-engine in this package:
- `/api/runs/{runid}/{config}/landuse-user-defined/catalog`
- `/api/runs/{runid}/{config}/landuse-user-defined/upload`
- `/api/runs/{runid}/{config}/landuse-user-defined/delete`
- `/api/runs/{runid}/{config}/landuse-user-defined/update-description`
- `/api/runs/{runid}/{config}/landuse-map/snapshot`
- `/api/runs/{runid}/{config}/landuse-map/save`
- `/api/runs/{runid}/{config}/landuse-map/clear-override`
- `/api/runs/{runid}/{config}/modify-landuse`

Route ownership explicitly retained in WEPPcloud:
- `/runs/{runid}/{config}/report/landuse`
- `/runs/{runid}/{config}/landuse-user-defined`
- `/runs/{runid}/{config}/landuse-map`

Security findings closure:
- SEC-02/07/08/09/10/11 all closed in package security artifact.
- No unresolved medium/high findings remain for moved surfaces.

Residual risks:
- No accepted medium/high residual security risk for moved surfaces.
- Standard operational risk remains for future contract drift; mitigated by frozen matrix + OpenAPI/schema tests.

## Context and Orientation

This package continues the phased landuse migration from:
- `docs/work-packages/20260423_landuse_first_class_agent_interface_migration/`

Deferred Phase 3 surfaces to migrate only after Gate 3 pass:
- `/runs/{runid}/{config}/api/landuse/user_defined/catalog`
- `/runs/{runid}/{config}/tasks/landuse/user_defined/upload`
- `/runs/{runid}/{config}/tasks/landuse/user_defined/delete`
- `/runs/{runid}/{config}/tasks/landuse/user_defined/update-description`
- `/runs/{runid}/{config}/api/landuse/map_snapshot`
- `/runs/{runid}/{config}/tasks/landuse/map/save`
- `/runs/{runid}/{config}/tasks/landuse/map/clear-override`
- `/runs/{runid}/{config}/tasks/modify_landuse/`

Core source files:
- `wepppy/weppcloud/routes/nodb_api/landuse_bp.py`
- `wepppy/microservices/rq_engine/landuse_routes.py`
- `wepppy/microservices/rq_engine/schema_defaults_routes.py`
- `wepppy/microservices/rq_engine/auth.py`
- `wepppy/weppcloud/controllers_js/landuse.js`
- `wepppy/weppcloud/controllers_js/landuse_modify_gl.js`

Core test files:
- `tests/weppcloud/routes/test_landuse_bp.py`
- `tests/microservices/test_rq_engine_landuse_routes.py`
- `tests/microservices/test_rq_engine_schema_defaults_routes.py`
- `tests/microservices/test_rq_engine_openapi_contract.py`
- `wepppy/weppcloud/controllers_js/__tests__/landuse.test.js`
- `wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js`

Hardening parity matrix:
- `docs/work-packages/20260424_landuse_phase3_hardening_parity_tests/artifacts/2026-04-24_hardening_parity_test_matrix.md`

## Plan of Work

### Milestone 1: Gate 3.0 Baseline hardening freeze
Freeze current WEPPcloud behavior as source-of-truth by ensuring every required matrix row has explicit baseline test coverage and deterministic assertions.

Work:
- Review each required matrix row and map it to existing baseline tests.
- Add missing baseline tests in `tests/weppcloud/routes/test_landuse_bp.py`.
- Verify baseline tests assert status codes, error codes, and side-effect behavior (file state, metadata state, hash semantics).

Acceptance:
- Every required matrix row has a baseline test reference.
- Baseline suite passes.

### Milestone 2: Gate 3.1 rq-engine hardening parity implementation
Implement/migrate Phase 3 rq-engine endpoints and add parity tests asserting behavior equivalence to baseline.

Work:
- Add Phase 3 routes in `wepppy/microservices/rq_engine/landuse_routes.py`.
- Preserve explicit error contracts and no silent fallbacks.
- Add/expand rq-engine tests for each required matrix row.

Acceptance:
- rq-engine tests pass for all required rows.
- Any behavior delta vs baseline is explicitly justified and approved in Decision Log.

### Milestone 3: Gate 3.2 auth/transport/discovery parity
Ensure moved routes preserve browser transport and auth boundaries and are represented in catalogs/OpenAPI/docs.

Work:
- Update browser callers to `requestWithSessionToken` for moved routes.
- Enforce token-class/scope policy on moved mutators.
- Update schema/defaults endpoint catalog coverage.
- Update OpenAPI contract and docs schemas.

Acceptance:
- JS tests pass for moved browser surfaces.
- OpenAPI/discovery/contract tests pass.
- No cookie-mutation fallback introduced.

### Milestone 4: Gate 3.3 security closure and go/no-go
Close security findings and record final disposition.

Work:
- Update security artifact with concrete evidence for each finding.
- Close SEC-02 and related open findings when parity evidence is complete.
- Record route movement outcome and residual risk in package docs.

Acceptance:
- No unresolved medium/high findings for moved surfaces.
- Gate 3 verdict recorded as pass/no-go with rationale.

## Concrete Steps

Run commands from `/home/workdir/wepppy`.

1. Baseline freeze:
   - `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1`

2. rq-engine parity:
   - `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1`

3. Discovery/OpenAPI parity:
   - `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1`
   - `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1`

4. Browser transport parity:
   - `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js`
   - `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js`

5. Documentation and closeout:
   - `wctl doc-lint --path docs/work-packages/20260424_landuse_phase3_hardening_parity_tests --path docs/schemas/rq-engine-agent-api-contract.md --path docs/schemas/rq-response-contract.md --path docs/schemas/weppcloud-csrf-contract.md --path PROJECT_TRACKER.md`

## Validation and Acceptance

Gate 3 is accepted only when all are true:
1. Every required hardening parity matrix row has passing baseline and rq-engine tests.
2. Auth/transport/discovery tests are passing for moved surfaces.
3. Security artifact reports no unresolved medium/high findings for moved surfaces.
4. Docs and contract artifacts are updated and lint-clean.

## Idempotence and Recovery

- Test-first sequencing is safe to rerun; failing rows should block route movement.
- If migration introduces parity regression, revert moved route handling and keep baseline tests as source-of-truth.
- Keep route movement incremental so rollback can be done per-surface without invalidating unrelated surfaces.

## Artifacts and Notes

- Hardening parity matrix: `docs/work-packages/20260424_landuse_phase3_hardening_parity_tests/artifacts/2026-04-24_hardening_parity_test_matrix.md`
- Security gate artifact: `docs/work-packages/20260424_landuse_phase3_hardening_parity_tests/artifacts/2026-04-24_security_review.md`
- Tracker: `docs/work-packages/20260424_landuse_phase3_hardening_parity_tests/tracker.md`

## Interfaces and Dependencies

- Preserve canonical response envelope and error explicitness from:
  - `docs/schemas/rq-response-contract.md`
- Preserve CSRF/session boundary and browser transport policy from:
  - `docs/schemas/weppcloud-csrf-contract.md`
- Preserve agent-facing endpoint contract/docs parity from:
  - `docs/schemas/rq-engine-agent-api-contract.md`

### Revision Notes
- 2026-04-24 / Codex: Initial ExecPlan authored for dedicated Gate 3 hardening parity package.
- 2026-04-24 / Codex: Gate 3 execution completed; plan marked complete and ready to move to `prompts/completed/`.
