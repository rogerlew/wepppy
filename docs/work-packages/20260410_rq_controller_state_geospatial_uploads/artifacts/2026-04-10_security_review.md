# Security Review - RQ Controller State Geospatial and Upload Metadata

> Dedicated security review artifact for `20260410_rq_controller_state_geospatial_uploads`.

## Metadata

- **Package**: `docs/work-packages/20260410_rq_controller_state_geospatial_uploads/`
- **Reviewer**: `security_reviewer` (independent subagent)
- **Date**: 2026-04-10
- **Scope reviewed**:
  - `GET /api/runs/{runid}/{config}/geospatial-metadata`
  - Upload metadata contract surfaces for `rq_engine_upload_dem`, `rq_engine_upload_cli`, `rq_engine_upload_sbs`, and `rq_engine_upload_cover_transform`
  - Live upload handler behavior for DEM/CLI/SBS/cover-transform (`max_bytes` parity with metadata)
- **Commit/branch context**: local working tree for package closeout
- **Related artifacts**:
  - Package tracker: `docs/work-packages/20260410_rq_controller_state_geospatial_uploads/tracker.md`
  - Completed ExecPlan: `docs/work-packages/20260410_rq_controller_state_geospatial_uploads/prompts/completed/rq_controller_state_geospatial_uploads_execplan.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: Upload metadata and geospatial defaults influence file validation and route/parameter selection for autonomous execution; disclosure and validation-contract boundaries require explicit review.
- **Threat model assumptions**:
  - Session and bearer token validation remains centralized in rq-engine auth middleware.
  - Run authorization checks are mandatory for all run-scoped metadata routes.
  - Metadata payloads must avoid exposing secrets, filesystem paths, or internal-only debugging fields.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Medium | Upload routes (`upload_dem`, `upload_cli`, `upload_sbs`, `upload_cover_transform`) | Upload handlers accepted unbounded payload sizes (`max_bytes=None`) which enabled authenticated storage/processing DoS risk. | `wepppy/microservices/rq_engine/watershed_routes.py`, `upload_climate_routes.py`, `upload_disturbed_routes.py`; descriptor `max_bytes` fields in `schema_defaults_routes.py`. | Add per-route byte ceilings, align descriptor metadata, and add oversize regression tests. | Resolved |
| SEC-02 | Low | Geospatial metadata payload | Potential path-like disclosure risk for `uploaded_dem_filename` if stored value included path segments. | `wepppy/microservices/rq_engine/schema_defaults_routes.py` runtime-state assembly. | Sanitize to basename + safe filename before payload emission. | Resolved |
| SEC-03 | Low | Test coverage depth | Filename sanitization branch in `_load_runtime_state` has no dedicated path-like-value regression test. | Security re-review note; implementation includes sanitization but no direct branch test. | Add direct sanitization test in follow-up when `_load_runtime_state` branch harnessing is expanded. | Accepted-risk |

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 1 (`SEC-03`, accepted risk)
- **Release recommendation**: proceed for this package; medium/high security gate satisfied.

## Surface Checks

### 1) Auth, Session, and Authorization

- [x] Entry points enforce expected authn/authz checks for changed routes/services.
- [x] Role checks and scope checks are explicit, least-privilege, and regression-tested.
- [x] Session/JWT token validation paths preserve canonical contracts.
- [x] CSRF protections are preserved for browser session mutation paths.

### 2) Input Validation and Output Safety

- [x] Untrusted input is validated at boundaries (types, ranges, enum membership).
- [x] Failing validation returns explicit contract-compliant errors.
- [x] Metadata payloads do not expose restricted fields (secrets, file-system paths, internal-only metadata).

### 3) File System and Upload Boundary Safety

- [x] Upload metadata does not imply unsupported file handling behavior.
- [x] File constraints (format/extensions/size/CRS/extent/resolution/value semantics) align with live upload handlers.
- [x] No path traversal or out-of-scope file references are introduced in metadata payloads.

### 4) Data Integrity, Locking, and Concurrency

- [x] Metadata reads are internally consistent and revision-tagged as required by contract.
- [x] Read endpoints do not bypass existing locking or authorization boundaries.
- [x] Concurrent state changes do not produce unsafe or misleading metadata snapshots.

### 5) Logging, Monitoring, and Incident Readiness

- [x] Error paths log enough context for debugging without exposing secrets.
- [x] New handlers do not swallow exceptions silently.

## Validation Evidence

- `wctl run-pytest tests/microservices/test_rq_engine_geospatial_upload_metadata_routes.py --maxfail=1` -> pass (`21 passed`)
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` -> pass (`9 passed`)
- `wctl run-pytest tests/microservices/test_rq_engine_upload_climate_routes.py tests/microservices/test_rq_engine_upload_disturbed_routes.py tests/microservices/test_rq_engine_watershed_routes.py --maxfail=1` -> pass (`37 passed`)
- `python tools/check_endpoint_inventory.py` -> pass
- `python tools/check_route_contract_checklist.py` -> pass
- `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1` -> pass (`2 passed`)

## Residual Risk

- **Accepted residual risks**:
  - `SEC-03` low: explicit branch test coverage for filename-sanitization path is not yet isolated.
- **Follow-up packages/issues**:
  - `20260410_rq_controller_state_auth_concurrency`
  - `20260410_rq_controller_state_errors_progress_outputs`

## Sign-off

- **Security reviewer**: `security_reviewer` (re-review passed; no unresolved medium/high)
- **Package owner**: Codex
