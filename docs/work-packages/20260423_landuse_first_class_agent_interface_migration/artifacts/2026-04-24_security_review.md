# Security Review - Landuse First-Class Agent Interface Migration (Phased rq-engine Cutover)

> Dedicated security gate artifact for phased migration of landuse machine/state APIs.

## Metadata

- **Package**: `docs/work-packages/20260423_landuse_first_class_agent_interface_migration/`
- **Reviewer**: Codex
- **Date**: 2026-04-24
- **Scope reviewed**:
  - `wepppy/weppcloud/routes/nodb_api/landuse_bp.py`
  - `wepppy/microservices/rq_engine/landuse_routes.py`
  - `wepppy/microservices/rq_engine/schema_defaults_routes.py`
  - `wepppy/microservices/rq_engine/auth.py`
  - `wepppy/weppcloud/controllers_js/landuse.js`
  - `wepppy/weppcloud/controllers_js/landuse_modify_gl.js`
  - `wepppy/weppcloud/templates/controls/landuse_map.htm`
  - `wepppy/weppcloud/templates/controls/landuse_user_defined.htm`
  - `wepppy/weppcloud/routes/_run_context.py`
  - `wepppy/weppcloud/utils/helpers.py`
- **Commit/branch context**: local working tree (`master`) during package execution and closeout
- **Related artifacts**:
  - Tracker: `docs/work-packages/20260423_landuse_first_class_agent_interface_migration/tracker.md`
  - ExecPlan (completed): `docs/work-packages/20260423_landuse_first_class_agent_interface_migration/prompts/completed/landuse_first_class_agent_interface_migration_execplan.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: migration touches auth/session/CSRF boundaries for landuse state mutation routes and includes potential future movement of file/path/archive-sensitive endpoints.

## Gate Status Summary

- **Gate 0 (strategy preconditions)**: PASS
- **Gate 1 (Phase 1 mutators)**: PASS
- **Gate 2 (Phase 2 read/discovery parity)**: PASS
- **Gate 3 (map/catalog/file movement)**: NOT ENTERED (no high-risk surface moved in this package)

## Findings

| ID | Severity | Surface | Description | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| SEC-01 | High | Run scope / context | rq-engine run-root resolution could drift from WEPPcloud `pup` semantics. | Finalize and test explicit strategy. | **Closed** - `_resolve_run_root_for_request` enforces `?pup=` normalization, containment, and existence checks; composite runid handling documented/tested. |
| SEC-02 | High | File/path/archive hardening | Moving map/catalog/file surfaces could regress containment, archive policy, concurrency preconditions, and atomic writes. | Gate 3 parity checklist + abuse/concurrency tests before movement. | **Deferred (Gate 3 not entered)** - surfaces intentionally remain in WEPPcloud in this package. |
| SEC-03 | Medium | CSRF/session boundary | Browser callers for moved routes required bearer-token bridge transport and no cookie fallback. | Use `requestWithSessionToken`; keep rq-engine mutators bearer-only. | **Closed** - migrated browser calls in `landuse.js` now use `requestWithSessionToken`; no cookie mutation fallback added. |
| SEC-04 | Medium | Authorization expansion | Route migration could unintentionally widen non-user token mutation access. | Explicit token-class policy + negative tests. | **Closed** - mutators require `rq:enqueue` + token class in `{user,session,service,mcp}` + run access; unknown token class rejected in tests. |
| SEC-05 | Medium | Test control gap | Stubbed auth flows reduced confidence for regression detection. | Add auth matrix coverage for moved routes. | **Closed** - added route-level scope/token-class/rejection coverage in `test_rq_engine_landuse_routes.py` and helper tests in `test_rq_engine_auth.py`. |
| SEC-06 | Medium | Agent discoverability | Endpoint catalog omitted landuse operation(s), creating contract drift. | Add operation metadata and tests. | **Closed** - operation docs/schema/defaults now include migrated landuse operations and `modify-landuse-mapping`; discovery/openapi tests updated. |

## Surface Checks

### 1) Auth, Session, and Authorization

- [x] Migrated routes enforce bearer auth + expected scope checks.
- [x] Token-class policy is explicit on migrated mutators.
- [x] Run-access checks remain enforced.
- [x] CSRF boundary unchanged for rq-engine bearer routes.

### 2) Input Validation and Output Safety

- [x] Migrated payloads preserve explicit validation errors.
- [x] Canonical error payload behavior preserved.
- [x] No silent fallback wrappers introduced.

### 3) File System and Run-Tree Boundaries

- [x] PUP/active-root strategy for moved routes documented and tested.
- [x] Phase 1/2 moved routes stay within run root resolution policy.
- [ ] Phase 3 file/path/archive movement not in this package.

### 4) Agentic Tooling and Discovery Surfaces

- [x] Migrated landuse operations are discoverable via endpoint catalogs.
- [x] Endpoint docs/schema/defaults are synchronized for migrated operations.
- [x] OpenAPI contract tests updated to reflect inventory deltas.

## Validation Evidence

Required command evidence captured during closeout:

- `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1` -> exit `137` (environment instability); fallback `.venv/bin/pytest ...` -> `28 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` -> exit `137`; fallback `.venv/bin/pytest ...` -> `10 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` -> exit `137`; fallback `.venv/bin/pytest ...` -> `54 passed`.
- `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1` -> exit `137`; fallback `.venv/bin/pytest ...` -> `19 passed`.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js` -> `20 passed`.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js` -> `3 passed`.
- `wctl doc-lint --path docs/work-packages/20260423_landuse_first_class_agent_interface_migration --path docs/schemas/rq-engine-agent-api-contract.md --path docs/schemas/rq-response-contract.md --path docs/schemas/weppcloud-csrf-contract.md --path PROJECT_TRACKER.md` -> pass.

## Verdict

- **Package verdict for shipped scope (Gate 0-2)**: `pass`
- **Gate 3 verdict**: `blocked/deferred` (not entered by design)
- **Unresolved findings affecting moved surfaces**:
  - High: 0
  - Medium: 0
- **Residual deferred finding**:
  - SEC-02 remains open only for future Phase 3 route movement.

## Residual Risk and Follow-up

- **Accepted residual risk**: Environment-level instability of `wctl run-pytest` (`137`) required `.venv` pytest fallback for evidence in this run.
- **Mandatory follow-up before any Phase 3 movement**:
  1. Complete hardening parity tests for path containment, archive policy, optimistic concurrency, and atomic rollback semantics.
  2. Re-open Gate 3 security review and close SEC-02 with concrete test and abuse evidence.

## Sign-off

- **Security reviewer**: Codex (package execution reviewer)
- **Package owner**: Codex (execution session)
- **Sign-off date**: 2026-04-24
