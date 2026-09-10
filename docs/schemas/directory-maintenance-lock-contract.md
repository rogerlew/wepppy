# Directory maintenance lock contract

## RQ cancellation ownership

Implementation validated locally (RQ-CANCEL-LOCKS-01); production rollout pending.

New RQ-owned directory maintenance locks MUST identify the server-created job
execution that acquired them, distinguishing retries of the same job. Ownership
metadata is additive; existing lock keys, scopes, tokens, and expiry behavior
remain compatible. Non-RQ callers retain ordinary context-managed release.

Cancellation cleanup MUST run only after the owning execution's workhorse and
descendant writers, including detached or reparented writers, have terminated.
If termination cannot be verified (including permission-denied inspection),
cleanup MUST retain the locks and record an inspectable pending/error reason.
PID identity alone or death of the original process group is insufficient proof.
It MUST atomically verify execution ownership
and current lock token before deleting each lock. It MUST NOT delete another
execution's lock, a replacement lock, or unrelated NoDb controller locks.
Repeated cleanup and absent locks are valid no-ops. Queued cancellation MUST NOT
clear active jobs' locks. Missing legacy execution identity is not authority to
clear a lock; existing explicit operator recovery remains available.

Malformed ownership MUST NOT broaden cleanup. Redis/cleanup failures MUST be
logged with job/root context and remain inspectable, without suppressing RQ stop
handling or claiming cleanup success. Stop acknowledgment alone does not prove
writer termination. Whole-container crash reconciliation is outside this change.

Rationale: forced cancellation bypasses Python context-manager release. Cleanup
in the surviving supervisor can remove abandoned locks safely only when exact
ownership and writer termination are established. Run-wide clearing is unsafe.

See [RQ cancellation](rq-engine-agent-api-contract.md#cancellation-directory-lock-cleanup)
and [NoDb persistence](nodb-persistence-concurrency-contract.md) for the separate
controller-lock ownership requirements. Historical NoDir thaw/freeze documents
remain retired; this contract covers current directory maintenance locks.
