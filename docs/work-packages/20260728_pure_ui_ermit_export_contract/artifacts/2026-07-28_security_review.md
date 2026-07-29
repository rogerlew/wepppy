# Security Review - SURF-16 Pure UI ERMiT Export Contract

## Metadata

- **Package**:
  `docs/work-packages/20260728_pure_ui_ermit_export_contract/`
- **Reviewer**: `/root/surf16_review` (independent, read-only)
- **Date**: 2026-07-28
- **Scope reviewed**: session-token retry, submit/poll/download lifecycle,
  rq-engine authorization and run/job association, worker metadata, and tests
- **Commit/branch context**: uncommitted SURF-16 diff on `master` from
  `8c0af64e4`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: yes
- **Triage rationale**: The retained production repair changes recovery around
  the session token used for authenticated queue submission, job polling, and
  protected artifact download.
- **Threat model assumptions**:
  - cookie-authenticated token minting remains same-origin protected;
  - minted tokens retain run scope plus `rq:export` and `rq:status`;
  - submit/download retain run authorization; and
  - download retains job/run/finished-state and confined-artifact checks.

## Findings

| ID | Severity | Surface | Description | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| SEC-01 | Low | Test integrity | Wrong-run fixture could have returned the expected 404 later because its artifact result was incomplete. | Supply a valid artifact/result so only the run-association guard produces 404. | Resolved |

## Verdict

- **Gate status**: pass
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Release recommendation**: ship

## Surface Checks

- Retry clears only the per-attempt cached token promise.
- One token remains shared across submit, poll, and download within an attempt.
- Retry is actionable only after an error and hides synchronously on restart.
- Same-origin token minting and bearer API CSRF semantics are unchanged.
- Submit retains `rq:export` scope and run authorization.
- Download reauthorizes the run and verifies job ownership and finished state.
- Artifact resolution remains confined beneath the active run directory.
- Worker metadata remains run-relative and retains config and filename.
- No queue edge, scope, claim, CAP rule, public-download rule, dependency,
  subprocess, secret, egress, or CI behavior changed.

## Validation Evidence

- Real inline Jest proves one-token happy flow and fresh-token retry recovery.
- Direct rendering proves run-scoped URLs, states, actions, and fallback.
- The strengthened wrong-run test fails if the run/job association guard is
  removed despite a valid artifact.
- Focused rq-engine/worker tests pass.

## Residual Risk

Retry after an ambiguous submit transport failure can enqueue a second export
because submit has no idempotency key. This behavior predates SURF-16 and is not
broadened by the rejected-token recovery repair.

## Sign-off

- **Security reviewer**: `/root/surf16_review`, 2026-07-28
- **Package owner**: Codex, 2026-07-28
