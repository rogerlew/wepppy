# Security Review - RQ Controller State Schema and Defaults

> Dedicated security review artifact for `20260410_rq_controller_state_schema_defaults`.

## Metadata

- **Package**: `docs/work-packages/20260410_rq_controller_state_schema_defaults/`
- **Reviewer**: `security_reviewer` subagent
- **Date**: 2026-04-10
- **Scope reviewed**:
  - `wepppy/microservices/rq_engine/schema_defaults_routes.py`
  - `tests/microservices/test_rq_engine_schema_defaults_routes.py`
  - `tests/microservices/test_rq_engine_openapi_contract.py`
  - `tools/rq_engine_contract_rules.py`
  - frozen endpoint/checklist artifacts for rq-engine agent-facing routes
- **Commit/branch context**: local working tree (package closeout state, 2026-04-10)
- **Related artifacts**:
  - Package tracker: `docs/work-packages/20260410_rq_controller_state_schema_defaults/tracker.md`
  - Completed ExecPlan: `docs/work-packages/20260410_rq_controller_state_schema_defaults/prompts/completed/rq_controller_state_schema_defaults_execplan.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: New run-scoped controller/endpoint metadata reads expose machine-consumable constraints/defaults that drive autonomous operation selection and payload construction.
- **Threat model assumptions**:
  - JWT/session validation remains centralized in rq-engine auth helpers.
  - Run authorization checks are mandatory before metadata read access.
  - Metadata payloads must avoid secrets, filesystem paths, and internal-only debug fields.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Low | Output safety | Reflected controller/operation identifiers in `404` messages could become a downstream injection sink if clients render error text unsafely. | `schema_defaults_routes.py` controller/operation not-found branches (pre-fix) | Emit generic not-found messages without reflecting raw path input. | Resolved |
| SEC-02 | Low | Metadata disclosure | `deployment_revision` in schema/default responses can disclose internal revision details if configured with sensitive values. | `schema_defaults_routes.py` `_base_payload()` / `_deployment_revision()` | Keep env value non-sensitive/public, or omit/coarsen for non-admin callers. | Accepted-risk |
| SEC-03 | Low | Error classification | Unexpected auth-boundary exceptions map to `401`, collapsing some internal failures into auth failures. | `schema_defaults_routes.py` auth gate exception blocks | Tighten taxonomy in auth-concurrency follow-on package (`500` for unexpected faults). | Accepted-risk |

Risk acceptance authority: package owner acceptance recorded in tracker; no medium/high findings remain.

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 2 (`SEC-02`, `SEC-03`, both accepted-risk; `SEC-01` resolved)
- **Release recommendation**: ship with documented low-risk acceptance and planned auth-concurrency follow-on tightening.

## Surface Checks

### 1) Auth, Session, and Authorization

- [x] Entry points enforce expected authn/authz checks for changed routes/services.
- [x] Role/scope checks remain explicit and regression-tested.
- [x] Session/JWT validation path remains canonical.
- [x] CSRF mutation boundaries unchanged (read-only routes only).

### 2) Input Validation and Output Safety

- [x] Path inputs and controller/operation IDs are validated with explicit contract-compliant error responses.
- [x] Metadata payloads avoid secret or filesystem disclosure and expose only planner-safe fields.
- [x] Error payloads stay within canonical `error_response` contract.

### 3) Data Integrity, Locking, and Concurrency

- [x] Run-state revision and etag values are emitted from deterministic state snapshots.
- [x] Metadata availability predicates now align with disturbed-mod support boundaries (including `/upload-sbs`).

### 4) Queue, Worker, and Subprocess Surfaces

- [x] No queue wiring changes were introduced in this package.
- [x] Failure handling preserves canonical response/error contracts.

### 5) Logging, Monitoring, and Incident Readiness

- [x] Route boundary failures are not silently swallowed.
- [x] Error paths preserve actionable diagnostics without exposing sensitive values.

## Validation Evidence

- Automated checks run:
  - `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` (`43 passed`)
  - `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` (`9 passed`)
  - `python tools/check_endpoint_inventory.py` (pass)
  - `python tools/check_route_contract_checklist.py` (pass)
  - `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1` (`2 passed`)
- Manual checks run:
  - Independent security subagent review + remediation verification (no unresolved medium/high findings).

## Residual Risk

- **Accepted residual risks**:
  - `SEC-02`: keep `RQ_ENGINE_DEPLOYMENT_REVISION` as a non-sensitive public build label.
  - `SEC-03`: temporary broad `401` compatibility at auth-boundary exception paths.
- **Follow-up packages/issues**:
  - `20260410_rq_controller_state_auth_concurrency` (auth scope/taxonomy tightening)

## Sign-off

- **Security reviewer**: `security_reviewer` subagent, 2026-04-10
- **Package owner**: Codex, 2026-04-10
