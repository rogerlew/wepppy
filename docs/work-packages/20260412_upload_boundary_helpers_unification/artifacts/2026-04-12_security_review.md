# Security Review - Upload Boundary Helpers Unification

> Final security review artifact for upload boundary helper unification closeout.

## Metadata

- **Package**: `docs/work-packages/20260412_upload_boundary_helpers_unification/`
- **Reviewer**: Codex
- **Date**: 2026-04-12
- **Last updated**: 2026-04-12 16:39 UTC
- **Scope reviewed**:
  - `wepppy/microservices/upload_boundary.py`
  - `wepppy/microservices/rq_engine/upload_helpers.py`
  - `wepppy/microservices/rq_engine/ash_routes.py`
  - `wepppy/microservices/rq_engine/omni_routes.py`
  - `wepppy/weppcloud/routes/nodb_api/roads_bp.py`
  - `wepppy/microservices/shape_converter/archive_validation.py` (ZIP canonical reference only; unchanged)
- **Commit/branch context**: `master` package closeout
- **Related artifacts**:
  - Work package tracker: `docs/work-packages/20260412_upload_boundary_helpers_unification/tracker.md`
  - Active ExecPlan: `docs/work-packages/20260412_upload_boundary_helpers_unification/prompts/active/upload_boundary_helpers_unification_execplan.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: package modifies shared untrusted upload boundary logic used by multiple API routes and filesystem write paths.
- **Threat model assumptions**:
  - Attackers can submit malformed, oversized, or extension-bypass payloads to authenticated upload endpoints.
  - Route-level behavior consistency is required for operator safety and client predictability.
  - ZIP canonical controls must remain centralized to prevent validator drift.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | High | Upload boundary consistency | Duplicated helper implementations can drift in filename/type/size handling, creating inconsistent acceptance/rejection behavior. | Pre-migration helper stacks in `ash_routes.py`, `omni_routes.py`, and `roads_bp.py`. | Consolidate non-ZIP boundary logic into canonical helper path and migrate duplicated routes. | Closed |
| SEC-02 | High | Shared helper migration risk | Refactor may accidentally change response/status contracts for existing routes. | Existing routes mixed 400/413 behavior and different helper error paths. | Add parity tests and explicit status mapping checks for migrated endpoints. | Closed |
| SEC-03 | Medium | ZIP helper drift | Upload helper unification could unintentionally introduce a parallel ZIP path. | Package scope spans upload helpers broadly. | Keep ZIP boundary authority in `shape_converter/archive_validation.py` and assert this in package acceptance criteria/tests. | Closed |

### Finding Disposition Notes

- **SEC-01 closure**: Implemented canonical non-ZIP helper layer in `wepppy/microservices/upload_boundary.py`; migrated `upload_helpers.py`, `ash_routes.py`, `omni_routes.py`, and `roads_bp.py` to shared helpers.
- **SEC-02 closure**: Added helper-level and route-level parity tests including invalid extension and oversize upload paths with explicit `413` checks for migrated routes.
- **SEC-03 closure**: No changes were made to ZIP validator ownership/behavior; culvert ZIP ingestion remains on `archive_validation.py` + `culvert_payload_validator.py`.

Risk acceptance authority: `Accepted-risk` requires security reviewer recommendation plus explicit package owner acknowledgment in Sign-off.

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Release recommendation**: approve package closure.

## Surface Checks

### 1) Auth, Session, and Authorization

- [x] Entry points keep existing authn/authz boundary behavior.
- [x] Role/scope checks remain unchanged.

### 2) Secrets and Credential Handling

- [x] No secret-handling changes.

### 3) Input Validation and Output Safety

- [x] Shared helper enforces filename/extension/size boundaries for migrated routes.
- [x] Validation failures remain contract-compliant and non-leaky.

### 4) File System and Run-Tree Boundaries

- [x] Writes remain run-scoped and destination-controlled.

### 5) Queue, Worker, and Subprocess Surfaces

- [x] No queue wiring changes.

### 6) Agentic Tooling and MCP Surfaces

- [x] No MCP permission scope changes.

### 7) Network and External Integrations

- [x] No new outbound integrations.

### 8) CI/CD and Supply Chain

- [x] No dependency additions.

### 9) Data Integrity, Locking, and Concurrency

- [x] Route-level orchestration and locking semantics unchanged.

### 10) Logging, Monitoring, and Incident Readiness

- [x] Upload-facing error payloads remain canonical and non-traceback.

## Validation Evidence

- Automated checks run:
  - `wctl run-pytest tests/microservices/test_upload_boundary_helpers.py tests/microservices/test_rq_engine_upload_disturbed_routes.py tests/microservices/test_rq_engine_upload_huc_fire_routes.py tests/microservices/test_rq_engine_upload_batch_runner_routes.py tests/microservices/test_rq_engine_landuse_routes.py tests/microservices/test_rq_engine_treatments_routes.py tests/microservices/test_rq_engine_culverts.py tests/microservices/test_rq_engine_ash_routes.py tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_roads_bp.py --maxfail=1` -> `137 passed`.
  - `wctl run-pytest tests --maxfail=1` -> `3511 passed`, `36 skipped`.
- Manual checks run:
  - Verified canonical ZIP controls remain in `wepppy/microservices/shape_converter/archive_validation.py`.
  - Verified no edits to `wepppy/microservices/culvert_payload_validator.py`.
  - Verified dirty `wepppy/weppcloud/routes/usersum/generated/docs_index.json` remained untouched.

## Residual Risk

- **Accepted residual risks**:
  - Low: some route-level fallback logic still supports legacy `ValueError` message checks for `413` mapping; primary path now uses explicit `status_code`.
- **Follow-up packages/issues**:
  - Optional future cleanup package can remove message-based fallback once all upload call sites emit typed upload boundary errors only.

## Sign-off

- **Security reviewer**: Codex, 2026-04-12 16:39 UTC
- **Package owner**: Pending human acknowledgment
