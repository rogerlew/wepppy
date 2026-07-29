# Fork Destination Readiness Hardening

**Status**: Closed (2026-07-29)
**Timezone**: UTC
**Security impact**: `low`

## Overview

On 2026-07-29, production fork job
`a94e82fc-dcc3-4dcf-a648-90033ff9c5ad` reported authoritative RQ completion
before the destination page was loadable. The console exposed its success link,
but the first request to
`/weppcloud/runs/burned-out-harmonic/cfg/` returned HTTP 404 and a later request
loaded normally.

## Trigger and Failure Signature

- Environment: `wepp1`, WEPPcloud production.
- Source run: `enveloping-write-in`.
- Destination run: `burned-out-harmonic`.
- Job interval: 2026-07-29 20:51:09–20:51:28 UTC.
- Job result: `finished`, no `exc_info`.
- User-visible signature: the console displayed completion and its destination
  link, but that link initially returned HTTP 404.
- Filesystem result: the destination existed and later loaded without repair.

## Scope Boundary

Make fork success actionable only after WEPPcloud can resolve the destination,
without changing copy semantics, queue wiring, authorization, CAP behavior, or
the run page.

### Included

- A source-and-destination-authorized, read-only destination-readiness check
  bound to the exact finished fork job and run IDs.
- Bounded client readiness reconciliation after authoritative RQ completion.
- Exact route and client regressions for delayed readiness, recovery, terminal
  failure, and restored jobs.
- Forking documentation, work-package evidence, and local validation.

### Explicitly Out of Scope

- Deployment or production mutation.
- Changes to `fork_rq`, rsync, RQ dependencies, run data, or filesystem mounts.
- Generic retry middleware or changes to ordinary run-page 404 behavior.
- Parameter, threshold, formula, unit, or fallback changes.

## Hardening Hypothesis and Signals

**Hypothesis**: If the console separately confirms destination readiness after
RQ reports `finished`, then it will not expose a success link during a transient
post-fork 404 window.

**Primary health signal**: zero reports in the 14-day post-deployment
observation window where a fork console success link initially returns 404 and
later loads without repair.

**Guardrails**:

- authorization and CAP behavior remain unchanged;
- no extra fork jobs, mutations, or unbounded polling;
- readiness failures remain visible and retryable;
- normal ready destinations add no more than one readiness request after RQ
  completion.

**Danger signals**: success links still precede loadability, readiness polling
continues after terminal failure/navigation, authorization errors are hidden,
or completed forks are mislabeled failed.

## Precedent

- `docs/work-packages/20260729_pure_ui_fork_console_contract/` established
  poll-authoritative terminal state and safe destination links. This package
  retains those contracts but adds the missing loadability boundary.
- `docs/mini-work-packages/completed/trigger-refactor.md` established hybrid
  StatusStream/poll completion and idempotent terminal handlers. This package
  composes readiness after that terminal result rather than replacing it.
- `docs/standards/hardening-lifecycle-standard.md` supplies the incident,
  signal, regression, review, and closeout requirements.

Unlike generic status retry work, this package is confined to one confirmed
fork destination-readiness gap.

## Acceptance

After RQ reports `finished`, the console displays a finalizing state and checks
destination readiness. It exposes “Load project” only after the authorized
readiness route confirms the destination directory and required root NoDb state
are visible. A not-ready response is retried within a finite client budget;
authorization or transport exhaustion remains visible and retryable. Targeted
tests, frontend gates, repository pytest, documentation lint, code review, and
QA review must pass before closure.

## Compatibility and Rollback

The change adds a read-only route and client state; it does not change fork
payloads or run data. Rollback is removal of the route and readiness
reconciliation, restoring the prior RQ-finished-only link behavior. No
temporary feature flag or permanent fallback is introduced, so there is no
callus sunset date.

## Closure Constraint

Close after local automated validation and dual review. Deployment is
explicitly deferred. The operator will perform local integration testing after
closure and may reopen this package if that evidence contradicts acceptance.

## Outcome

Closed locally after the readiness route, bounded client reconciliation, exact
regressions, broad validation, and independent code and QA reviews passed.
Review findings were resolved or recorded as non-blocking coverage debt.
Nothing was deployed. Operator-led local integration testing remains the next
acceptance step and may reopen this package.
