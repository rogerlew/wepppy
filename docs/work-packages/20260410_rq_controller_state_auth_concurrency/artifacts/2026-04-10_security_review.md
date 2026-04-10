# Security Review - RQ Controller State Auth and Concurrency

> Dedicated security review artifact for `20260410_rq_controller_state_auth_concurrency`.

## Metadata

- **Package**: `docs/work-packages/20260410_rq_controller_state_auth_concurrency/`
- **Reviewer**: `security_reviewer` subagent (`019d798f-8864-7fb1-813e-3150176cd535`)
- **Date**: 2026-04-10
- **Scope reviewed**: auth scope rollout for controller-state reads, session-token descriptor/runtime parity, optimistic concurrency preconditions, and idempotency replay/mismatch handling
- **Commit/branch context**: local working tree for package closeout
- **Related artifacts**:
  - Package tracker: `docs/work-packages/20260410_rq_controller_state_auth_concurrency/tracker.md`
  - Completed ExecPlan: `docs/work-packages/20260410_rq_controller_state_auth_concurrency/prompts/completed/rq_controller_state_auth_concurrency_execplan.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: This package modifies auth boundaries and stale-write protections on agent-facing rq-engine surfaces; drift can cause privilege and data-integrity failures.
- **Threat model assumptions**:
  - Session and bearer token validation remains centralized in rq-engine auth middleware.
  - Concurrency conflict paths must stay explicit and canonical.
  - Idempotency replay/mismatch handling must remain deterministic and non-bypassable.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Medium | Session token scope bridge | Bearer tokens with `rq:status` can mint run-scoped session tokens carrying broader scopes (`rq:enqueue`, `rq:export`). This is explicit in implementation and contract metadata and currently intentional. | `wepppy/microservices/rq_engine/session_routes.py` (`SESSION_TOKEN_SCOPES`, `SESSION_TOKEN_REQUIRED_SCOPES`, `issue_session_token`), `wepppy/microservices/rq_engine/schema_defaults_routes.py` (`rq_engine_issue_session_token` descriptor), `docs/schemas/rq-controller-state-contract.md` session-token operation block | Track as policy-level least-privilege decision for cutover package; if policy changes, update route + descriptor + contract together. | Accepted residual/design risk |

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**:
  - High defects: 0
  - Medium defects: 0
  - Low defects: 0
- **Accepted residual/design risks**:
  - Medium: 1 (`SEC-01`)
- **Release recommendation**: proceed.

## Surface Checks

### 1) Auth, Session, and Authorization

- [x] Entry points enforce expected authn/authz checks for changed routes/services.
- [x] Scope checks (`rq:read` rollout and compatibility boundaries) are explicit and regression-tested.
- [x] Session/JWT token validation paths preserve canonical contracts.
- [x] CSRF/same-origin protections remain intact for session-cookie path.

### 2) Concurrency and Idempotency Safety

- [x] Optimistic concurrency precondition checks are enforced where required.
- [x] Conflict responses are canonical and do not mask stale-write rejection.
- [x] Idempotency replay/mismatch behavior aligns with declared policy and is regression-tested.
- [x] Retry/replay behavior cannot bypass authorization or validation checks.

### 3) Input Validation and Output Safety

- [x] Untrusted input is validated at boundaries.
- [x] Failing validation returns explicit contract-compliant errors.
- [x] Error payloads preserve canonical contract fields.

### 4) Data Integrity, Locking, and Concurrency

- [x] Mutating operations with declared preconditions reject stale run-state revisions.
- [x] Concurrency and idempotency semantics are deterministic under duplicate retry scenarios (including public fallback mode).
- [x] Recovery paths preserve consistent run-state expectations.

### 5) Logging, Monitoring, and Incident Readiness

- [x] Conflict/replay denials are observable without exposing secrets.
- [x] No silent exception swallowing introduced.

## Validation Evidence

- `wctl run-pytest tests/microservices/test_rq_engine_auth_concurrency_routes.py --maxfail=1` (pass, `17 passed`)
- `wctl run-pytest tests/microservices/test_rq_engine_auth.py tests/microservices/test_rq_engine_session_routes.py --maxfail=1` (pass, `58 passed`)
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` (pass, `9 passed`)
- `python tools/check_endpoint_inventory.py` (pass)
- `python tools/check_route_contract_checklist.py` (pass)
- `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1` (pass, `2 passed`)
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` (pass)
- Final `security_reviewer` pass: no unresolved medium/high defects; one accepted residual design risk.

## Residual Risk

- **Accepted residual risks**:
  - Contract-defined session-token scope bridge (`rq:status` -> minted session token includes `rq:enqueue`/`rq:export`) remains in place for compatibility.
- **Follow-up packages/issues**:
  - `20260410_rq_controller_state_contract_cutover`

## Sign-off

- **Security reviewer**: `security_reviewer` subagent
- **Package owner**: Codex
