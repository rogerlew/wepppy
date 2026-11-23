# Dedicated query catalog queue on wepp3

Deployed and closed 2026-11-23 UTC. The operator authorized a dedicated maintenance queue and one consumer alongside the serial fork/archive service on wepp3. The incumbent deployment uses shared default workers on wepp1 and wepp2. A long-running refresh occupies one of their RQ execution slots even while it waits on Rocket NFS.

## Outcome

Route refresh, inventory and reconciliation consistently. Preserve durable receipts, stale-job fencing, selection of the newest publication, ordinary backlog deferral and the Rocket batch-owner cap. Leave the fork/archive worker exclusively on its FIFO queue. Use existing worker registration, job records and filesystem evidence for monitoring. The operator requested no changes to rq/info-details.

## Acceptance

Prove default workers no longer take catalog jobs. Confirm precisely one compatible catalog worker on wepp3 and one independent fork/archive worker. Read back a catalog produced by a real receipt, verify a controlled test-project fork/archive during catalog activity, and record queue wait, oldest outstanding receipt and Rocket latency. One execution slot bounds concurrent catalog work. This rollout establishes neither a higher NFS capacity nor long-term freshness by itself.

Security impact is high because this changes worker routing, writable project access and the deployment fence. [Contract](../../schemas/query-engine-catalog-refresh-contract.md) · [ExecPlan](prompts/completed/implementation.md) · [Tracker](tracker.md)
