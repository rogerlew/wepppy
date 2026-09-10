# RQ cancellation directory-lock cleanup

Status: Contract checkpoint preparation; implementation pending.

## Scope and incident

Implement the operator's instruction: "canceling rq-jobs needs to clear directory locks."
On wepp1, job 2964a4f7-6b07-4d3b-a70d-d78dabcb8c67 failed at
2026-09-10 03:56:20 UTC with NODIR_LOCKED for asteroid-hindrance/climate.
The lock named a removed container and expired at 04:38:32 UTC.
Cancellation as the cause of that owner's disappearance is not proven.

Scope: release directory maintenance locks owned by canceled RQ executions after
their writers stop. Preserve unrelated locks, authorization, queue wiring, and
NoDb controller locks. GridMET retrieval/scaling defects and whole-host crash
recovery are excluded. This is an intended behavior amendment, not restoration
of an existing cancellation-cleanup guarantee.

## Security and compatibility

Security impact: high, because early or overbroad release permits concurrent
writers. Dedicated security review is required before implementation acceptance.
Keep existing cancellation responses and asynchronous stop behavior.
Add execution ownership to new lock payloads; preserve existing keys, TTLs and
token-checked release. Legacy locks without provable execution identity require
existing explicit operator recovery, never a run-wide automatic clear.

## Validation and signals

Prove real Redis lock acquisition, real worker cancellation, descendant writer
termination, cleanup, and immediate reacquisition under the development Compose
worker identity/mounts. Prove another job's lock and a replacement token survive.
Include detached/reparented CLIGEN-style writers and unknown/permission-denied
termination evidence; retain locks with an inspectable reason without proof.
Test queued, active, stopped, repeated cancellation, missing/empty legacy
metadata, malformed ownership, and Redis cleanup failure.
Run focused tests and wctl run-pytest tests --maxfail=1. No deployment until
production-equivalent process-boundary evidence and reviews pass.

Hypothesis: canceled executions no longer leave owned directory locks that block
the next build. Health signal: stopped-job cleanup and successful immediate
rebuild. Danger signals: release before writer termination, unrelated lock
deletion, unreported cleanup failure. Use recurrence-triggered observation with
pre/post rollout evidence; recurrence opens a new incident. No temporary retry
or TTL mitigation is proposed.

## Precedent

Reuse token compare-and-delete in runtime_paths/thaw_freeze.py and the surviving
worker supervisor pattern in rq_worker.py. Consult
../20260906_fork_read_retry_hardening/package.md for abrupt-death reporting,
../20260803_fork_archive_serial_queue/package.md for cancellation authorization,
and ../20260909_gridmet_queue_recovery/package.md for the separate GridMET issue.
Unlike admission retry work, this changes execution-owned resource cleanup.
