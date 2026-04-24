# Security Review - Landuse Phase 3 Hardening Parity Tests and Migration Gate

> Dedicated security gate artifact for Gate 3 map/catalog/file route movement.

## Metadata

- **Package**: `docs/work-packages/20260424_landuse_phase3_hardening_parity_tests/`
- **Reviewer**: Codex
- **Date**: 2026-04-24
- **Scope reviewed (planned movement)**:
  - `wepppy/weppcloud/routes/nodb_api/landuse_bp.py`
  - `wepppy/microservices/rq_engine/landuse_routes.py`
  - `wepppy/microservices/rq_engine/schema_defaults_routes.py`
  - `wepppy/weppcloud/controllers_js/landuse.js`
  - `wepppy/weppcloud/controllers_js/landuse_modify_gl.js`
  - `tests/weppcloud/routes/test_landuse_bp.py`
  - `tests/microservices/test_rq_engine_landuse_routes.py`
- **Commit/branch context**: local working tree (`master`) at package scaffolding time
- **Related artifacts**:
  - Prior package security review: `docs/work-packages/20260423_landuse_first_class_agent_interface_migration/artifacts/2026-04-24_security_review.md`
  - Hardening parity matrix: `docs/work-packages/20260424_landuse_phase3_hardening_parity_tests/artifacts/2026-04-24_hardening_parity_test_matrix.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: Phase 3 moves upload/map/catalog/file mutation surfaces with path/archive/concurrency/atomicity risk.

## Gate Status Summary

- **Gate 3.0 (baseline hardening freeze)**: PASS (2026-04-24 06:04 UTC)
- **Gate 3.1 (rq-engine hardening parity)**: PASS (2026-04-24 06:04 UTC)
- **Gate 3.2 (transport/auth/discovery parity)**: PASS (2026-04-24 06:04 UTC)
- **Gate 3.3 (security closure)**: PASS (2026-04-24 06:04 UTC)

## Findings

| ID | Severity | Surface | Description | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| SEC-02 | High | File/path/archive hardening | Movement could regress containment, archive policy, and upload boundary controls. | Pass HP-01/02/03/04/05 matrix rows in both baseline and rq-engine suites. | Closed |
| SEC-07 | High | Concurrency + stale-write integrity | Movement could regress stale-hash/precondition enforcement and allow stale overwrite. | Pass HP-07/08 matrix rows with explicit status/code/details parity. | Closed |
| SEC-08 | High | Atomic rollback guarantees | Save-path failures could leave partially applied override state. | Pass HP-10 matrix row proving rollback to previous file + relpath. | Closed |
| SEC-09 | Medium | Auth scope widening | Route movement may widen mutation access to unintended token classes/scopes. | Enforce and test token/scope/token-class policy on moved mutators (HP-13). | Closed |
| SEC-10 | Medium | Browser boundary regression | Browser migration may reintroduce cookie mutation fallback on rq-engine mutators. | Enforce token-bridge transport and JS regression checks (HP-14). | Closed |
| SEC-11 | Medium | Discovery/contract drift | Moved routes may ship undocumented or with response-code mismatches. | Pass HP-15/16 matrix rows and contract checks. | Closed |

## Surface Checks

### 1) Auth, Session, and Authorization
- [x] Moved mutators enforce explicit scope/token-class/run-access policy.
- [x] No auth widening vs prior package policy.

### 2) Input Validation and Output Safety
- [x] Upload/map payload boundaries remain explicit and contract-compliant.
- [x] Error payloads preserve canonical contract and explicit failures.

### 3) File System and Run-Tree Boundaries
- [x] Run-root containment is preserved for user-defined catalog and map override writes.
- [x] Archive extraction/write operations remain inside intended run scope.

### 4) Data Integrity, Locking, and Concurrency
- [x] Optimistic concurrency (`if_match_sha256`) parity is preserved.
- [x] Atomic rollback semantics are preserved under failure paths.

### 5) Agentic Tooling and Discovery Surfaces
- [x] Endpoint catalog/OpenAPI parity is complete for moved surfaces.
- [x] No silent fallback wrappers added.

## Validation Evidence

Command evidence for closure:
- `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1`
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js`
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js`
- `wctl doc-lint --path docs/work-packages/20260424_landuse_phase3_hardening_parity_tests --path docs/schemas/rq-engine-agent-api-contract.md --path docs/schemas/rq-response-contract.md --path docs/schemas/weppcloud-csrf-contract.md --path PROJECT_TRACKER.md`

Observed results (2026-04-24):
- `test_landuse_bp.py`: `24 passed`
- `test_rq_engine_landuse_routes.py`: `39 passed`
- `test_rq_engine_schema_defaults_routes.py`: `54 passed`
- `test_rq_engine_openapi_contract.py`: `10 passed`
- `landuse.test.js`: `20 passed`
- `landuse_modify_gl.test.js`: `3 passed`
- Doc lint: `10 files validated, 0 errors, 0 warnings`

## Verdict

- **Current verdict**: `pass`
- **Release recommendation**: `proceed` for moved Phase 3 surfaces (map/catalog/file/mutate APIs) under existing render-route ownership boundaries.

## Residual Risk and Follow-up

- No unresolved medium/high findings remain for moved surfaces.
- Residual note: render routes intentionally remain in WEPPcloud (`/report/landuse`, `/landuse-user-defined`, `/landuse-map`) by package constraint.

## Sign-off

- **Security reviewer**: Codex
- **Sign-off date**: 2026-04-24
