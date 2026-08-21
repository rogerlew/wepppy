# Correctness Review — WEPPcloudR Execution Backend Refactor

**Review state**: Pending implementation
**Gate**: FAIL (open review; package must not close)
**Reviewer**: Unassigned independent correctness reviewer
**Date opened**: 2026-08-21

## Review Questions

- Does the Compose adapter preserve command, cache, result, exception, and
  artifact behavior?
- Are current Compose files and rendered mounts unchanged?
- Is backend selection explicit and stable for legacy queued jobs?
- Do Kubernetes state transitions cover create, observe, retry, reconcile,
  cancel, timeout, missing Job, malformed response, and stale completion?
- Does `run_root` support normal and PUP-linked runs without widening scope?
- Are the route and canonical RQ response contracts unchanged?
- Does the forest evidence prove the designated render used Docker exec?

## Required Scenario Matrix

| Scenario | Expected result | Evidence |
|---|---|---|
| Existing valid cached artifact | Contract-compatible cache result | Pending |
| Forced/no-cache render | One fenced publish and valid HTML | Pending |
| Legacy queued Compose arguments | Compatible Docker-exec execution | Pending |
| Normal run and PUP parent links | Valid run-WD resolution | Pending |
| Invalid backend/path/request | Explicit contract error, no fallback | Pending |
| Retry/reconcile/cancel/timeout | Deterministic terminal state | Pending |
| Authorized forest report | Successful Docker-exec artifact, mounts equal | Pending |

## Open Findings

| ID | Severity | Finding / evidence required | Disposition |
|---|---|---|---|
| COR-01 | High | Compose parity has not yet been established. | Open |
| COR-02 | High | Kubernetes state-machine implementation/tests do not yet exist. | Open |
| COR-03 | Medium | Forest integrated result and mount comparison are pending. | Open |

## Gate Decision

FAIL until an independent reviewer completes the matrix and all medium/high
findings are resolved or accepted by the authorized owner.
