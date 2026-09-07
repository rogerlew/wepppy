# ADR-0049: Bound transient reads during WEPP preparation

**Status**: Accepted design; implementation pending
**Decision venue**: User/Codex incident-remediation session, 2026-09-07 UTC
**Participants**: Requesting WEPPcloud operator and Codex
**Decision owner**: Requesting operator (scope); Codex (implementation defaults)
**Implementer**: Codex

## Context

Fork preparation jobs failed initial NoDb reads during small-file-heavy fork
activity. The exact NAS mechanism is unproven. See the
[incident](../infrastructure/ui-rcds-nfs-vs-dev-nfs.md#production-incident-fork-preparation-file-visibility-failures-2026-09-06)
and [work package](../work-packages/20260906_fork_read_retry_hardening/package.md).

## Decision

Change initial WEPP preparation controller loading from one attempt to an
opt-in 5-second shared retry deadline for ENOENT and ESTALE. Start delays at
0.1 seconds, double to a 1-second cap, and never schedule another attempt after
the deadline. The first attempt has no delay. The budget bounds application
retry scheduling, not blocking hard-NFS syscalls. Non-opted-in reads retain
zero retry delay. Optional missing files return None immediately.

Preserve original OSError errno/path and log attempts, elapsed time, worker,
run and job. Only stat/open/read operations may retry. Parsing, mutation,
permission errors, EIO, Redis errors and whole jobs are excluded.

## Rationale and Alternatives

Five seconds gives brief visibility failures time to clear while limiting
worker occupation and diagnostic noise; it is a conservative starting budget,
not a measured NAS recovery guarantee. Capped backoff reduces metadata pressure
compared with tight polling. Global delays would penalize ordinary web loads;
whole-job retries could repeat side effects. Host-specific routing and NFS
mount changes do not follow from the evidence and are excluded.

## Risk, Observation and Rollback

Record recovery/exhaustion frequency and added latency. On recurrence reassess
the errno evidence and burst hypothesis before increasing budgets. Remove or
revise the retry scope if it hides persistent failures or adds undue latency.
Rollback requires code only; no model parameter or persisted schema changes.
