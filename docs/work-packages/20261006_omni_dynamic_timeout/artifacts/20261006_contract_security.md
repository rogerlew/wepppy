# WRT-02 independent contract security review

Reviewer: independent Codex operations/security control agent. Date: 2026-10-06.
Scope: preimplementation WRT-02 contract checkpoint. No implementation files
were reviewed or edited.

## Initial verdict

Hold with three medium findings and one deployment control reminder.

1. Contrast timeout validation could occur after expensive hillslope rerun.
2. Aggregate batch-worker occupancy from finite per-leaf allowances across Omni
   fan-out was not durably assessed.
3. Captured enqueue arguments did not prove actual RQ serialization.
4. Deployment/retry needs independent drain, exact-revision, rollback and
   post-retry queue review; WRT-02 does not repair timeout subprocess cleanup.

## Disposition

Admission is now required before contrast rerun and every affected RQ child-id,
metadata, Redis and enqueue mutation. The package records unchanged
authorization, tracked-job conflicts, scenario/contrast selection, batching,
dependency serialization and concurrency, plus the increased aggregate occupancy
risk and explicit absence of a new quota. Real disposable Redis serialization,
`job_info` inspection and verified cleanup are mandatory. Deployment and retry
remain a separate hold with queue drain, revision/container, rollback and
post-retry observation requirements; timeout subprocess cleanup remains an open
known risk.

## Final verdict

Approved for standalone checkpoint commit and implementation. No blocking
preimplementation security/governance findings remain. Final implementation
evidence must directly assert that malformed contrast workload never calls
`_rerun_hillslopes_for_contrast_scenarios`; this is an acceptance obligation,
not a checkpoint blocker.
