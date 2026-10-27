# Inventory contract correctness review

Reviewer: independent `roads_contract_review` agent. Date: 2026-10-27 UTC.
Disposition: **PASS** after independent readback of the C1/C2 corrections below.
No unresolved contract findings. This is a contract review, not implementation
or rollout approval.

## Reviewed scope and authority

Reviewed [decision](20261027_inventory_contract_decision.md),
[canonical recovery and liveness](../../../schemas/query-engine-catalog-refresh-contract.md#recovery-and-liveness),
and [ADR-0104 clarification](../../../adrs/ADR-0104-query-catalog-refresh-operational-bounds.md#october-27-inventory-execution-clarification).
Compared them with the existing scheduler lease, cursor publication and RQ
admission implementation, and the retained production inventory evidence.

The operator-approved remediation covers streaming discovery on the existing
batch queue, preserving four namespaces and established access/readonly roles.
It does not authorize deployment, permission changes, a new queue/service, or
scientific artifact changes. The recorded contract promotes durable rules out
of the work package and correctly marks conformance pending. The HTTP work is
separate from this inventory checkpoint.

## Findings and verified disposition

- **C1 — Completion after traversal failure: resolved.** The original phrase
  “without unreported failures” could permit premature completion after a
  reported error. Canonical recovery/liveness now expressly blocks completion
  while required-root/directory traversal failures remain unresolved and
  requires retaining/retrying failed frontier items. Implementation must test a
  child permission/I/O failure after successful batches, followed by recovery.
- **C2 — Checkpoint/drain budget units: resolved.** ADR-0104 now specifies up to
  100 discovered entry records per checkpoint and up to 100 scope records per
  scheduler tick, explicitly not 100 batches. The admission limit remains 25.
  Implementation must test multiple full batches against this per-tick bound.

## Correctness and valid states

The proposed atomic seen/publication checkpoint prevents a crash from recording
a child as processed before making its work durable. Fencing by current job and
cycle prevents a replaced worker from publishing stale progress. Atomic batch
acknowledgment with pending-cursor incorporation prevents loss on scheduler
restart. Redis loss correctly restarts discovery from authoritative roots rather
than treating missing coordination as completed work.

The state matrix includes empty valid roots, previously unindexed projects,
nested projects, readonly projects, active legacy projects, unavailable roots,
replacement, mutation, malformed cursors, symlinks, stale workers and mixed
consumer capabilities. Preserve valid empty completion while distinguishing
missing/error roots. Directory-prefix replay is disclosed honestly; the contract
does not promise portable filesystem offsets or uninterrupted progress during
storage outage. Completed directories and published scopes survive worker
restart; acceptance must prove eventual completion after an interrupted stream.

The 3600-second timeout remains a candidate bound. Full legacy enumeration,
restart/replay, actual Redis races, production-equivalent identity/mount checks,
and fleet capacity evidence remain rollout gates. A successful first page or
unit test cannot replace them. No implementation, configuration, production
state, permissions or canonical documents were changed by this review.
