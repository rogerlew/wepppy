# Default-worker routing decision, 2026-10-28

Starting revision: `2fff37a75`. Classification: intended queue-routing change.
Operator approval: “we need to make the catalog update jobs run on default
workers. the batch workers can get backed up for days”. Scope is implementation
and local validation; production deployment/general enablement are not requested.

## Contract delta and rationale

Amend the query-engine catalog refresh contract (October 28 amendment), the
query-catalog pilot deployment contract (routing boundary) and ADR-0104. Move
both refresh and inventory, retries and new pilots to default. Preserve seven-job
cap, ordinary-backlog deferral and all existing budgets. Bind queue in capabilities
to reject old worker code. Pilot checks twelve existing default consumers, matching
the two six-worker production pools; no worker-count configuration changes.
Batch backlog lasting days is the operator's evidence for this bounded change.
No new queue/pool, priority, fallback or other catalog routing is introduced.

## Compatibility and security

Keep legacy ledger/pause keys and receipts; count legacy outstanding/uncertain
jobs rather than silently releasing permits. Missing-ledger bootstrap checks
both queues. Old pilot manifests stay readable but fail new-work authorization
against current queue/configuration. Never modify historical manifests/budgets.
Deployment requires old maintenance pause/drain and full participant deployment;
the old targeted-batch option cannot activate default workers. Preserve identities,
mounts, permissions, disclosure, scope guards and general-disabled mode.
No persisted project schema or scientific output parameter changes.

## State matrix and regression evidence

- Absent ledger: initialize only when both queues lack retained maintenance.
- Empty/default idle: actual Redis enqueue, worker execution and catalog readback.
- Populated batch backlog: default refresh/inventory progress independently.
- Populated default backlog: expected pending result; no priority bypass.
- Changed configuration identity: new inventory rediscovers old durable receipts; old Redis cursor/dirty state is not deleted.
- Legacy outstanding/uncertain ledger: preserve accounting and cap.
- Legacy batch pilot: inspect history; reject default execution/resume authority.
- Missing/old/malformed default capability: expected pending/unavailable response.
- Disabled mode and absent optional projects: preserve existing behavior.
- Malformed scope/receipt/manifest: retain existing explicit fail-closed contracts.

Run real-Redis catalog RQ/inventory/pilot and operator tests, live local job-tree
readback, graph gate, focused disclosure tests and broad pytest. Retain artifact
checks from actual workers; local evidence cannot assert production cutover.

## Checkpoint reviews

Independent read-only reviews completed before runtime edits:

- `queue_contract_correctness` (reviewer): PASS, no blocking findings. Low-priority stale M2 batch instruction corrected; added explicit changed-configuration receipt rediscovery coverage.
- `queue_contract_security` (security_reviewer): PASS, no blocking findings. Verify old/malformed capability rejection, legacy pilot read-only compatibility, both-queue bootstrap and preserved uncertain accounting in implementation.

Both reviews identify default contention and live fleet parity as remaining
production gates; neither claims runtime validation. This checkpoint must be
committed before runtime edits. Active plan's existing commit authority covers
reviewed checkpoints; no production operation is authorized here.
