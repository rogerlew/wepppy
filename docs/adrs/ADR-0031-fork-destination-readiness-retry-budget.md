# ADR-0031: Fork Destination Readiness Retry Budget

**Status**: Accepted
**Date**: 2026-07-29

## Context

A production fork reported authoritative RQ completion before WEPPcloud could
load the destination. The first destination request returned HTTP 404 and a
later request loaded without repair. The console therefore needs a short,
finite reconciliation window between worker completion and exposing its load
link.

## Decision

After authoritative RQ success, the fork console checks destination readiness
immediately. A not-ready result is retried once per second for at most 30 total
attempts. Success exposes the destination link. Exhaustion stops automatic
requests, retains the tracked destination, and presents a user-operated
readiness retry.

## Decision Provenance

- **Decision venue**: WEPPcloud operator/Codex incident conversation,
  2026-07-29 21:16 UTC.
- **Participants present**: WEPPcloud operator and Codex.
- **Decision owner**: Codex for the bounded technical retry policy, under the
  operator-requested hardening scope.
- **Implementer**: Codex.
- **Change summary**: old behavior exposed the link immediately at RQ
  `finished`; new behavior requires readiness, with 30 attempts at one-second
  intervals before manual retry.

## Rationale

Thirty seconds is long enough to absorb a short shared-filesystem visibility
delay without treating a persistent readiness failure as success. A
one-second interval limits request volume to one lightweight, read-only check
per second and gives a normally ready fork only one additional request.

## Alternatives Considered

- Expose the link at RQ completion: rejected because production disproved that
  this guarantees loadability.
- Retry without a limit: rejected because a persistent failure would cause
  unbounded background traffic.
- Require only manual retry: rejected because it preserves avoidable operator
  toil for a transient condition.
- Delay for a fixed time without checking: rejected because it is slower for
  healthy forks and still cannot prove readiness.

## Evidence

- Work package:
  `docs/work-packages/20260729_fork_destination_readiness_hardening/`.
- Production job: `a94e82fc-dcc3-4dcf-a648-90033ff9c5ad`.
- Regression coverage:
  `wepppy/weppcloud/controllers_js/__tests__/console_smoke.test.js`.

## Risks and Rollback

The readiness route adds up to 30 lightweight GET requests for an unavailable
destination. Authorization or transport errors stop automatic polling.
Rollback removes the readiness loop and route, restoring the previous
RQ-finished-only behavior without data migration.

Review the budget if post-deployment evidence shows readiness commonly exceeds
30 seconds, the route adds measurable load, or false readiness persists. The
WEPPcloud operator owns the 14-day post-deployment observation.
