# Checkpoint Operations and Security Review

**Reviewer**: Independent operations/security control agent
**Date**: 2026-08-07 UTC
**Mode**: Read-only pre-implementation review

## Initial Verdict

Held pending disposition. Math, operation-scoped locking, token-owned release,
and lack of route/auth/secret/queue expansion were confirmed safe. High findings
were mixed-version RQ compatibility, missing durable timing evidence, and
undefined partial-Git recovery. Medium findings were non-measurable queue
guardrails, insufficient behavioral coverage, and the absent security artifact.

## Required Disposition

- Roll out consumer compatibility to all default workers before activating the
  longer producer timeout; reverse that order only after longer-timeout leaves
  drain. Avoid a new serialized keyword when possible.
- Persist host, run, command/script, timestamps, output, commit, and lock release.
- Treat 300 seconds as a bounded margin, not proof. Inspect surviving processes,
  HEAD, index/worktree, and `.git/index.lock`; never blindly requeue or delete a
  suspected stale lock.
- Define measurable queue/finalizer guardrails and collection cadence.
- Test old-job compatibility, derivation/scoping, token-owned release, exception
  behavior, unchanged sibling paths, and representative production acceptance.

Live corroboration found 12 global default workers (11 idle, one busy), an empty
default queue, the historical failure, recovery commit, and released lock.

## Post-Fix Confirmation

Consumer-first compatibility, producer-first rollback/drain, durable evidence,
partial-Git recovery, measurable guardrails, relative sunset window, and canary
acceptance resolved every high and medium finding. Operations/security verdict:
PASS; residual NFS-stall and worker-occupancy risks are bounded, monitored, and
covered by containment rules.
