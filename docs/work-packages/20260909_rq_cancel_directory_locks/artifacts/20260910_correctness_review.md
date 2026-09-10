# Correctness and user-experience review

## Metadata

Reviewer: /root/cancel_impl_correctness, 2026-09-10 UTC.
Scope: WepppyRqWorker cancellation, rq/directory_locks.py, directory maintenance
ownership, and cancellation probes. Checkpoint ancestor: 3903cb778.
Authority: docs/schemas/rq-engine-agent-api-contract.md, Cancellation directory-lock
cleanup; docs/schemas/directory-maintenance-lock-contract.md, RQ cancellation
ownership. Related: 20260910_security_review.md and 20260910_qa_review.md.

## User outcome and error policy

Cancellation stops writers before releasing that execution's locks, allowing
the next build to acquire its root. Stop acknowledgment remains asynchronous.
Unverifiable process ownership/termination or lock-Redis failure retains locks
with pending diagnostics. Diagnostic-Redis errors log their receipt without
preventing local writer termination. Whole-container crashes and legacy locks
retain existing explicit recovery.

## Valid-state matrix

| State | Required behavior | Evidence |
| --- | --- | --- |
| No locks / repeated cleanup | No-op | ownership and queued probes |
| Owned populated locks | Stop writers, release, reacquire | cancel probe with thread/fork/detached writer |
| Another execution / same-job retry | Preserve current owner | ownership probe |
| Replacement during deletion | Atomic payload check preserves replacement | real Redis Lua race injection |
| Legacy lock | Preserve | unrelated landuse lock in cancellation probe |
| Missing/malformed token | Retain, explicit error | ownership probe |
| Missing/denied process inspection | Retain | missing-live-task and permission guards |
| Scheduler live/dead | Preserve live scheduler; retain locks when uncertain | actual cancellation + scheduler-death guard |
| Metadata Redis failure | Stop writers despite diagnostics failure | cancel_watch and cancel_redis probes |
| Lock Redis release failure | Retain affected locks, no complete receipt | ownership fault + pending-state unit guard |
| Previous crashed execution | Retire ambiguous supervisor; preserve old writer during later cancel | crash_then_cancel probe |

Queued, running, stopped/repeated cancellation, retry identity, and crash/worker
replacement are exercised separately from stored lock state. No exhaustive claim
is made for arbitrary third-party worker subclasses or non-Linux deployments.

## Findings and disposition

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| COR-01 | High | Scheduler child disabled production cleanup | Resolved: live RQ scheduler pidfd protection; real scheduler-enabled worker probe |
| COR-02 | High | Diagnostic write failure prevented termination | Resolved: diagnostic Redis boundary logs independently; real fault scenarios |
| COR-03 | Medium | Prior failed-job children poisoned subsequent execution ownership | Resolved: reap exited children and retire supervisor with residual/unknown ownership |

Independent rereview confirmed all three findings closed and no new major
correctness findings. Its residual lock-Redis/scheduler-death coverage requests
were subsequently added.

## Verdict

Correctness review passed. Focused and real worker evidence is recorded in
20260910_validation.md. Full-suite gate completed: 8202 passed, 83 skipped; final focused suite 17 passed.
