# Security Review - SHR-05 Pure UI Unitizer Preferences Contract

## Metadata

- **Package**:
  `docs/work-packages/20260728_pure_ui_unitizer_preferences_contract/`
- **Reviewer**: `/root/shr05_review` (independent, read-only)
- **Date**: 2026-07-28
- **Scope reviewed**: Unitizer template/client/Project event ownership,
  run-scoped preference mutation, validation, NoDb persistence, and tests
- **Commit/branch context**: uncommitted SHR-05 diff on `master` from
  `d47862334`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: yes
- **Triage rationale**: SHR-05 verifies an authenticated, CAP-gated,
  run-scoped preference mutation. The repair changes browser event ownership
  but does not change the route or authorization policy.
- **Threat model assumptions**:
  - callers must retain existing run authorization and CAP verification;
  - submitted categories and units remain limited to backend registries; and
  - accepted state must persist atomically within the active run.

## Findings

| ID | Severity | Surface | Description | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| SEC-01 | Medium | Browser mutation/data integrity | Correcting legacy shell selectors would activate duplicate handlers beside Project and risk redundant/stale writes. | Keep Project as the sole change-event owner and prove one persistence request. | Resolved |

## Verdict

- **Gate status**: pass
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Release recommendation**: ship

## Surface Checks

- Existing authorization, CAP, CSRF, and run-scoped `load_run_context`
  boundaries are unchanged.
- Backend category/value allowlisting and compatible partial filtering are
  unchanged.
- Unitizer mutation remains inside the NoDb locked dump contract.
- Project is the sole delegated change-event owner; report shells retain only
  one-time reload synchronization.
- No secrets, logging disclosure, path expansion, external egress, dependency,
  RQ/worker/subprocess, CI/CD, or supply-chain surface changed.

## Validation Evidence

- A bubbled global-radio change invokes `handleGlobalUnitPreference` once and
  posts preferences once.
- Direct source/render evidence prevents obsolete selectors or duplicate shell
  listeners from returning.
- Focused render, client/map, Project, route, and NoDb suites pass.
- Full frontend lint/test passes.

## Residual Risk

No new residual risk beyond the existing synchronous authenticated preference
endpoint behavior.

## Sign-off

- **Security reviewer**: `/root/shr05_review`, 2026-07-28
- **Package owner**: Codex, 2026-07-28
