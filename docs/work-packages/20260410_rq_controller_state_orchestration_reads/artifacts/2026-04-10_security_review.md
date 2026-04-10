# Security Review - RQ Controller State Orchestration Reads

> Dedicated security review artifact for `20260410_rq_controller_state_orchestration_reads`.

## Metadata

- **Package**: `docs/work-packages/20260410_rq_controller_state_orchestration_reads/`
- **Reviewer**: `security_reviewer` subagent (Volta)
- **Date**: 2026-04-10
- **Scope reviewed**:
  - `wepppy/microservices/rq_engine/orchestration_read_routes.py`
  - `tests/microservices/test_rq_engine_orchestration_read_routes.py`
  - `tests/microservices/test_rq_engine_openapi_contract.py`
  - `tools/rq_engine_contract_rules.py`
  - frozen endpoint/checklist artifacts for rq-engine agent-facing routes
- **Commit/branch context**: local working tree (package closeout state, 2026-04-10)
- **Related artifacts**:
  - Package tracker: `docs/work-packages/20260410_rq_controller_state_orchestration_reads/tracker.md`
  - Completed ExecPlan: `docs/work-packages/20260410_rq_controller_state_orchestration_reads/prompts/completed/rq_controller_state_orchestration_reads_execplan.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: New run-scoped, agent-facing orchestration read APIs (`/pipeline`, `/readiness`) expose readiness, blocker, and invalidation state that directly influences autonomous action planning.
- **Threat model assumptions**:
  - JWT/session validation remains centralized in rq-engine auth helpers.
  - Run authorization checks are mandatory before orchestration state access.
  - Payloads avoid leaking internal traceback content or sensitive internals in canonical error surfaces.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Low | Route error classification | Broad `ValueError` handling at route boundary could mask internal faults as `404 not_found`. | `orchestration_read_routes.py` route handlers (pre-fix) | Introduce dedicated mismatch exception and narrow `404` handling. | Resolved |
| SEC-02 | Low | Scope compatibility | `rq:status` currently remains accepted for orchestration reads in addition to `rq:read`. | `ORCHESTRATION_ALLOWED_SCOPES` in `orchestration_read_routes.py` | Track explicit accepted-risk and tighten in auth-concurrency follow-on package. | Accepted-risk |

Risk acceptance authority: package owner acceptance recorded in tracker; low-risk compatibility retained for roadmap continuity.

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 1 (`SEC-02`, accepted-risk)
- **Release recommendation**: ship with documented low-risk compatibility acceptance and planned follow-on tightening.

## Surface Checks

### 1) Auth, Session, and Authorization

- [x] Entry points enforce expected authn/authz checks for changed routes/services.
- [x] Role/scope checks are explicit and regression-tested.
- [x] Session/JWT validation path remains canonical.
- [x] CSRF mutation boundaries unchanged (read-only routes only).

### 2) Input Validation and Output Safety

- [x] Path inputs are validated with explicit run/config mismatch handling.
- [x] Non-not-found value failures return canonical `500` after remediation.
- [x] Last-attempt payloads redact raw traceback text (`exc_info`) from response fields.

### 3) Data Integrity, Locking, and Concurrency

- [x] Run-state revision/etag derivation remains deterministic under empty-timeline and fan-out-job cases.
- [x] Child-job status folding prevents premature completion classification for parent orchestration jobs.

### 4) Queue, Worker, and Subprocess Surfaces

- [x] No queue wiring changes were introduced in this package.
- [x] Failure handling preserves canonical response/error contracts.

### 5) Logging, Monitoring, and Incident Readiness

- [x] Error paths retain logged context with canonical response boundaries.
- [x] No silent exception swallowing introduced in route boundary code.

## Validation Evidence

- Automated checks run:
  - `wctl run-pytest tests/microservices/test_rq_engine_orchestration_read_routes.py --maxfail=1` (`25 passed`)
  - `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` (`9 passed`)
  - `python tools/check_endpoint_inventory.py` (pass)
  - `python tools/check_route_contract_checklist.py` (pass)
  - `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1` (`2 passed`)
- Manual checks run:
  - Independent security subagent review + re-review after remediation (no unresolved medium/high findings).

## Residual Risk

- **Accepted residual risks**:
  - `SEC-02`: temporary compatibility acceptance for `rq:status` on orchestration reads during roadmap transition.
- **Follow-up packages/issues**:
  - `20260410_rq_controller_state_auth_concurrency` (scope tightening / cutover enforcement)

## Sign-off

- **Security reviewer**: `security_reviewer` subagent (Volta), 2026-04-10
- **Package owner**: Codex, 2026-04-10
