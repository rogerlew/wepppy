# Security Review - RQ Controller State Setup Discovery

## Metadata

- **Package**: `docs/work-packages/20260410_rq_controller_state_setup_discovery/`
- **Reviewer**: Codex (with independent `security_reviewer` subagent)
- **Date**: 2026-04-10
- **Scope reviewed**:
  - `wepppy/microservices/rq_engine/setup_discovery_routes.py`
  - `tests/microservices/test_rq_engine_setup_discovery_routes.py`
  - `tests/microservices/test_rq_engine_openapi_contract.py`
  - `tools/rq_engine_contract_rules.py`
  - setup-discovery contract/freeze docs updated by this package
- **Commit/branch context**: `master`, pre-closeout working tree for package handoff
- **Related artifacts**:
  - QA/reviewer finding disposition in:
    - `docs/work-packages/20260410_rq_controller_state_setup_discovery/tracker.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: This package introduces six new agent-facing setup endpoints and publishes auth/descriptor metadata used by agents before mutation calls, so auth/scope/session and error-contract semantics are security-relevant.
- **Threat model assumptions**:
  - Setup discovery remains read-only and must not leak filesystem paths, secrets, or token internals.
  - Endpoint metadata must not claim stronger replay/idempotency guarantees than runtime actually enforces.
  - `rq:status` rollout compatibility remains bounded to read-only setup/controller-state endpoints.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Medium | `/create/` descriptor parity | Setup discovery initially advertised `idempotency_policy.supported=true` for `rq_engine_create` without runtime enforcement. | `wepppy/microservices/rq_engine/setup_discovery_routes.py`, `wepppy/microservices/rq_engine/project_routes.py` | Align descriptor/schema metadata to runtime (`supported=false`, no dedupe key locations, redirect-only success contract). | Resolved |
| SEC-02 | Medium | Error-contract boundary | Setup detail routes could emit non-canonical framework 500 responses on internal failures. | `wepppy/microservices/rq_engine/setup_discovery_routes.py` | Add explicit route-boundary exception handling and return canonical `error_response(..., status_code=500)` payloads; add regression tests. | Resolved |
| SEC-03 | Low | Scope compatibility risk | Setup discovery accepts bearer tokens with `rq:status` during rollout compatibility, including session token class when claims include allowed scope. | `wepppy/microservices/rq_engine/setup_discovery_routes.py`, `docs/schemas/rq-engine-agent-api-contract.md` | Keep compatibility scope as documented for this package; record bounded rollout and defer strict `rq:read`/token-class narrowing to `20260410_rq_controller_state_auth_concurrency`. | Accepted-risk |

Risk acceptance authority: `SEC-03` accepted by package owner and security reviewer for compatibility with explicit roadmap sunset controls.

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 1 (`SEC-03` accepted-risk)
- **Release recommendation**: `ship-with-conditions`

Conditions:
- Keep `rq:status` compatibility bounded to read-only setup/controller-state surfaces.
- Enforce alias sunset and auth parity gates in `20260410_rq_controller_state_auth_concurrency`.

## Surface Checks

### 1) Auth, Session, and Authorization

- [x] Setup endpoints enforce bearer auth and scope checks (`rq:status` or `rq:read`).
- [x] No auth widening to mutating/export/admin/bootstrap routes.
- [x] Error responses do not disclose token contents.

### 3) Input Validation and Output Safety

- [x] Path parameters and dynamic catalog lookups return explicit canonical 404 errors.
- [x] Failure paths now return contract-compliant canonical 500 payloads.

### 7) Network and External Integrations

- [x] No new outbound network dependencies introduced by setup routes.

### 10) Logging, Monitoring, and Incident Readiness

- [x] New route-boundary exception handlers log context via `logger.exception(...)`.
- [x] Canonical error contracts are preserved across handled failures.

## Validation Evidence

- Automated checks run:
  - `wctl run-pytest tests/microservices/test_rq_engine_setup_discovery_routes.py --maxfail=1`
  - `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1`
  - `python tools/check_endpoint_inventory.py`
  - `python tools/check_route_contract_checklist.py`
- Manual checks run:
  - Metadata/runtime parity review for `rq_engine_create` idempotency and redirect semantics - pass
  - Setup endpoint auth/scope/session implications review against `rq-engine-agent-api-contract.md` - pass with documented accepted risk (`SEC-03`)

## Residual Risk

- **Accepted residual risks**:
  - `SEC-03`: `rq:status` setup-read compatibility remains active by design until auth-concurrency package sunset gate.
- **Follow-up packages/issues**:
  - `20260410_rq_controller_state_auth_concurrency` - enforce alias sunset and final auth-mode parity checks.

## Sign-off

- **Security reviewer**: Codex + `security_reviewer` subagent, 2026-04-10
- **Package owner**: Codex, 2026-04-10
