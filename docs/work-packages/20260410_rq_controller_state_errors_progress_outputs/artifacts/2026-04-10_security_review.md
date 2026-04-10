# Security Review - RQ Controller State Errors, Progress, and Outputs

> Dedicated security review artifact for `20260410_rq_controller_state_errors_progress_outputs`.

## Metadata

- **Package**: `docs/work-packages/20260410_rq_controller_state_errors_progress_outputs/`
- **Reviewer**: `security_reviewer` subagent (`019d7952-fa94-7431-be5c-b3ac754ba1d6`)
- **Date**: 2026-04-10
- **Scope reviewed**: run-scoped endpoint error catalogs, async progress metadata surfaces, and `/api/runs/{runid}/{config}/outputs` artifact/provenance metadata
- **Commit/branch context**: local working tree for package closeout
- **Related artifacts**:
  - Package tracker: `docs/work-packages/20260410_rq_controller_state_errors_progress_outputs/tracker.md`
  - Completed ExecPlan: `docs/work-packages/20260410_rq_controller_state_errors_progress_outputs/prompts/completed/rq_controller_state_errors_progress_outputs_execplan.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: Error/progress/outputs surfaces expose operational metadata and retrieval handles; controls must preserve run-scope and avoid sensitive disclosure.
- **Threat model assumptions**:
  - Session and bearer token validation remain centralized in rq-engine auth middleware.
  - Run authorization checks are mandatory for run-scoped metadata routes.
  - Output metadata exposes endpoint handles only; no direct internal path disclosure in payload contracts.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Low | Polling auth + progress disclosure | `jobstatus` is open by default and includes progress metadata, enabling unauthenticated visibility of workload timing when `job_id` is known. | `wepppy/microservices/rq_engine/job_routes.py` (`POLL_AUTH_MODE_ENV`, `jobstatus`), `wepppy/rq/job_info.py` progress payload | Follow-up hardening: either require token mode for progress or redact progress in open mode. | Accepted residual |
| SEC-02 | Low | Warning log metadata | Warning logs on outputs mismatch/out-of-scope checks include run/job identifiers and absolute artifact path in log extras. | `wepppy/microservices/rq_engine/schema_defaults_routes.py` warning branches in `_build_features_export_artifact` | Follow-up hardening: sanitize absolute path in warning logs (relative token only). | Accepted residual |

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 2
- **Release recommendation**: proceed.

## Surface Checks

### 1) Auth, Session, and Authorization

- [x] Entry points enforce expected authn/authz checks for changed routes/services.
- [x] Role checks and scope checks are explicit and regression-tested.
- [x] Session/JWT token validation paths preserve canonical contracts.
- [x] CSRF protections unchanged for browser-session mutation paths.

### 2) Input Validation and Output Safety

- [x] Untrusted input is validated at boundaries.
- [x] Validation failures return contract-compliant errors.
- [x] Outputs payload excludes internal filesystem paths while preserving retrieval handles.

### 3) Output Retrieval and Artifact Boundary Safety

- [x] Output handles are run-scoped and route-backed.
- [x] Artifact metadata includes trust/provenance fields (`produced_at`, `source_run_state_revision`, `size_bytes`, `sha256`).
- [x] Artifact containment check rejects paths outside run directory.

### 4) Data Integrity, Locking, and Concurrency

- [x] Metadata reads are revision-tagged.
- [x] Read endpoints maintain run authorization boundaries.
- [x] Progress metadata is deterministic under no-timestamp and partial-tree conditions.

### 5) Logging, Monitoring, and Incident Readiness

- [x] Error paths log context and preserve canonical error responses.
- [x] No silent exception swallowing introduced.

## Validation Evidence

- `wctl run-pytest tests/microservices/test_rq_engine_errors_progress_outputs_routes.py --maxfail=1` (pass)
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` (pass)
- `python tools/check_endpoint_inventory.py` (pass)
- `python tools/check_route_contract_checklist.py` (pass)
- `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1` (pass)
- Final `security_reviewer` pass: no unresolved medium/high findings.

## Residual Risk

- **Accepted residual risks**:
  - Open polling mode currently permits progress visibility for known `job_id` values.
  - Warning logs may expose absolute artifact paths when mismatch/out-of-scope checks trigger.
- **Follow-up packages/issues**:
  - `20260410_rq_controller_state_auth_concurrency` (scope/auth hardening follow-up)

## Sign-off

- **Security reviewer**: `security_reviewer` subagent
- **Package owner**: Codex
