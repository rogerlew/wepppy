# GridMET queue recovery

Status: Closed 2026-09-09 (PDT; 2026-09-10 UTC). Scope: fix confirmed queue deadline and transient Redis aborts without changing HTTP validation or admission capacity.

User-visible incident: eleven release/poll transport TimeoutError failures in six Marta runs, including downright-houri job d4ccb55e-9619-49ba-8bce-8918ba1d52de at 2026-09-09T22:51:34Z on wepp2. Valid populated admission state and successful HTTP receipt can reach this failure; corruption is not established.

Hypothesis: removing queue-age expiry and reconciling transient command outcomes will allow live requests and completed downloads to finish while preserving FIFO and the four-permit bound. Health/danger signals and recurrence-triggered observation are in the [ExecPlan](prompts/completed/gridmet_queue_recovery_execplan.md). No temporary callus or sunset date; these are permanent queue semantics. Security impact: high, shared cooperative ownership boundary; preserve token validation and fail closed on corruption. Independent correctness, QA and dedicated security review required.

Precedents: [original admission](../20260907_gridmet_redis_admission/package.md), [download hardening](../20260831_gridmet_download_hardening/package.md), [contention](../20260906_batch_climate_rap_contention/package.md). Reuse Lua ownership and existing HTTP validation; replace the arbitrary wait cutoff and terminal transient-transport policy.


## Delivered and validated

Live queue waiting has no elapsed deadline. Redis transport failures recover
with same-token replay; FIFO, capacity and lease authority remain enforced.
Exceptional cleanup preserves cancellation, release revokes local authority
before I/O, and manual/background renewal is serialized. The durable decision
is [ADR-0061](../../adrs/ADR-0061-gridmet-persistent-queue-recovery.md) and the
[admission contract](../../schemas/gridmet-redis-admission-contract.md).

Validation: **8,192 broad tests passed**, 77 skipped; **145 focused tests passed**;
**14 real Redis scenarios passed** with final targeted rechecks; public GridMET
returned **366 records**, independently observed across two worker containers,
with zero final queued/active state. API/stub/doc/exception checks and independent
correctness and QA/security reviews passed with no unresolved findings.
See [evidence](artifacts/incident-and-validation.md),
[correctness review](artifacts/correctness-review.md), and
[QA/security review](artifacts/20260909_security_review.md).

All local implementation and validation milestones are complete. Commit/push
follow closure as requested. Production deployment remains held pending
clarification; no production jobs were interrupted. Deployment is a separate
operational action through the canonical runbook. A future recurrence uses a
new incident record and the durable signals in the operator documentation;
this closed package is immutable history.
