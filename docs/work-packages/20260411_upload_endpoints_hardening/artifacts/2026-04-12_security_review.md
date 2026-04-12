# Security Review - Upload Endpoints Hardening

> Final security review disposition after implementation and validation gates.

## Metadata

- **Package**: `docs/work-packages/20260411_upload_endpoints_hardening/`
- **Reviewer**: Codex
- **Date**: 2026-04-12
- **Scope reviewed**:
  - `wepppy/microservices/rq_engine/culvert_routes.py`
  - `wepppy/microservices/culvert_payload_validator.py`
  - `wepppy/microservices/rq_engine/upload_huc_fire_routes.py`
  - `wepppy/microservices/rq_engine/upload_batch_runner_routes.py`
  - `wepppy/microservices/rq_engine/upload_climate_routes.py`
  - `wepppy/microservices/rq_engine/landuse_routes.py`
  - `wepppy/microservices/rq_engine/treatments_routes.py`
  - `wepppy/microservices/rq_engine/upload_disturbed_routes.py`
  - `wepppy/microservices/rq_engine/watershed_routes.py`
  - `wepppy/weppcloud/routes/nodb_api/roads_bp.py`
  - `wepppy/microservices/rq_engine/responses.py`
  - `wepppy/microservices/rq_engine/upload_helpers.py`
  - `wepppy/weppcloud/utils/helpers.py`
- **Commit/branch context**: local working tree (post-implementation validation complete)
- **Related artifacts**:
  - Work package tracker: `docs/work-packages/20260411_upload_endpoints_hardening/tracker.md`
  - Active ExecPlan: `docs/work-packages/20260411_upload_endpoints_hardening/prompts/active/upload_endpoints_hardening_execplan.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: untrusted upload parsing, ZIP extraction boundaries, filesystem writes, and error disclosure contracts are in scope.
- **Threat model assumptions**:
  - Upload endpoints are reachable by authenticated users/operators and process untrusted files.
  - Attackers can craft ZIP/member metadata and large payloads to target traversal or resource exhaustion.
  - Rejection behavior must be deterministic and non-leaky to support safe automation.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | High | Archive extraction | Culvert ZIP ingest used insufficient member-policy validation and `extractall` path, leaving archive abuse gaps. | Implemented shared validated archive controls in `wepppy/microservices/shape_converter/archive_validation.py` and adopted them in `wepppy/microservices/rq_engine/culvert_routes.py`; validated by `tests/microservices/test_rq_engine_culverts.py` abuse fixtures. | Reuse/adapt `shape_converter` archive validation/extraction controls and add abuse fixture tests. | Resolved (2026-04-12 06:27 UTC) |
| SEC-02 | High | Upload quotas | Multiple upload routes accepted unbounded payload writes before validation. | Added explicit pre-write max-byte guards in upload routes; verified by route-level size regression tests. | Enforce explicit pre-write max-byte caps and route-level regression tests. | Resolved (2026-04-12 06:27 UTC) |
| SEC-03 | Medium | Input allowlists | Disturbed SBS upload allowed arbitrary extensions due empty allowlist. | Updated `UPLOAD_SBS_ALLOWED_EXTENSIONS` to explicit raster extensions in `upload_disturbed_routes.py`; validated by upload-route tests. | Require explicit extension allowlist and verify behavior in tests. | Resolved (2026-04-12 06:27 UTC) |
| SEC-04A | High | Upload error envelope | Upload-facing error payloads did not consistently include required `error.code` and top-level `error_id`. | Hardened `rq_engine/responses.py`, `rq_engine/upload_helpers.py`, roads upload helper path (`weppcloud/utils/helpers.py`) and roads upload route to emit canonical fields for upload failures; regression assertions added in upload tests. | Enforce required upload envelope fields on all scoped upload failures. | Resolved (2026-04-12 18:35 UTC) |
| SEC-04B | High | Observability correlation | Server-side traceback logging for exception-driven upload failures was not consistently correlated with returned `error_id`. | Added helper-level traceback/error-id correlation logging and regression tests proving response `error_id` matches log context (`test_rq_engine_upload_climate_routes.py`, `test_roads_bp.py`). | Ensure exception-driven failures log full traceback with matching `error_id`. | Resolved (2026-04-12 18:53 UTC) |
| SEC-04C | Medium | Upload error detail completeness | Some upload error responses omitted `error.details`. | Shared helper hardening now always populates `error.details`; route tests assert `error.details` presence/value for representative failures. | Ensure `error.details` is always populated on upload-facing failures. | Resolved (2026-04-12 18:35 UTC) |
| SEC-04D | Medium | Contract documentation alignment | Package docs still asserted strict traceback redaction despite contract allowing traceback payloads (`MAY include traceback`). | Updated package/tracker/ExecPlan/security artifact language to observability-first policy and contract-compliant traceback stance. | Align docs with current contract and logging expectations. | Resolved (2026-04-12 19:02 UTC) |
| SEC-04E | Low | Validation messaging | Residual generic missing-file messages remained in landuse/treatments upload paths. | Replaced with field-specific messages in `landuse_routes.py` and `treatments_routes.py`; added regression coverage in corresponding route tests. | Preserve specific, field-level validation reasons. | Resolved (2026-04-12 18:37 UTC) |

Risk acceptance authority: `Accepted-risk` requires security reviewer recommendation plus explicit package owner acknowledgment in Sign-off.

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Release recommendation**: approved for merge/closeout; no accepted medium/high residual risk required.

## Surface Checks

### 1) Auth, Session, and Authorization

- [x] Entry points keep existing authn/authz boundary checks in scope (no planned auth widening).
- [x] Role/scope regressions retested after upload hardening changes.

### 2) Secrets and Credential Handling

- [x] No new secret-handling changes planned.

### 3) Input Validation and Output Safety

- [x] Untrusted upload boundaries enforce explicit size/type/archive-member policy controls before write/extract.
- [x] Validation failures are explicit and contract-compliant.

### 4) File System and Run-Tree Boundaries

- [x] Archive extraction remains inside intended roots with traversal/symlink/special-entry rejection.
- [x] Upload writes remain bounded and path-safe for all scoped routes.

### 5) Queue, Worker, and Subprocess Surfaces

- [x] No queue-wiring changes planned in this package.

### 6) Agentic Tooling and MCP Surfaces

- [x] No MCP permission widening changes planned.

### 7) Network and External Integrations

- [x] No new outbound integration planned.

### 8) CI/CD and Supply Chain

- [x] No external dependency additions planned; reuse existing in-repo validated logic.

### 9) Data Integrity, Locking, and Concurrency

- [x] Route updates preserve existing lock and run-root semantics after upload guard additions.

### 10) Logging, Monitoring, and Incident Readiness

- [x] Upload error responses include `error_id` and stable codes.
- [x] Exception-driven upload failures log full traceback server-side with matching `error_id`.
- [x] Traceback payload behavior is contract-compliant (`MAY include traceback`); observability correlation is required.

## Validation Evidence

- Automated checks run:
  - `wctl run-pytest tests/microservices/test_rq_engine_upload_climate_routes.py tests/microservices/test_rq_engine_upload_disturbed_routes.py tests/microservices/test_rq_engine_upload_huc_fire_routes.py tests/microservices/test_rq_engine_upload_batch_runner_routes.py tests/microservices/test_rq_engine_landuse_routes.py tests/microservices/test_rq_engine_treatments_routes.py tests/microservices/test_rq_engine_watershed_routes.py tests/microservices/test_rq_engine_culverts.py tests/weppcloud/routes/test_roads_bp.py --maxfail=1` (`120 passed`)
  - `wctl run-pytest tests --maxfail=1` (`3524 passed`, `36 skipped`)
  - `wctl doc-lint --path docs/work-packages/20260411_upload_endpoints_hardening/package.md --path docs/work-packages/20260411_upload_endpoints_hardening/tracker.md --path docs/work-packages/20260411_upload_endpoints_hardening/prompts/active/upload_endpoints_hardening_execplan.md --path docs/work-packages/20260411_upload_endpoints_hardening/artifacts/2026-04-12_security_review.md --path docs/schemas/upload-endpoint-contract.md --path docs/schemas/rq-response-contract.md` (`6 files validated`, `0 errors`, `0 warnings`)
- Manual checks run:
  - Reviewed scoped endpoint inventory against package scope and confirmed no `shape_converter` endpoint behavior changes were introduced.

## Residual Risk

- **Accepted residual risks**:
  - None.
- **Follow-up packages/issues**:
  - Consider follow-up package to centralize reusable upload-size/type helper policies across all rq-engine routes for future consistency work.

## Sign-off

- **Security reviewer**: Codex (2026-04-12 19:06 UTC)
- **Package owner**: pending human acknowledgment
