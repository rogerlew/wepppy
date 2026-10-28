# ADR-0109: Bound RQ webhook tracking and delivery

Status: Accepted 2026-10-28 19:56 UTC; implementation under acceptance
Date: 2026-10-28

## Context

Per-submission callbacks must not consume computation capacity or retain unlimited
receiver-controlled data. These are accepted initial operational ceilings, not
measured capacity claims. Existing behavior has no application webhook service.

## Decision

| Policy | Accepted value | Rationale |
| --- | --- | --- |
| Total attempt deadline | 10 seconds, including DNS/connect/TLS/headers | Operator's suggested short deadline; killable isolated attempt process |
| Attempts | 3 total, including interrupted attempts | Limits duplicates and receiver amplification |
| Retry delays | 30 seconds after attempt 1, 120 after attempt 2 | Brief outage tolerance without tight loops |
| Retry-After cap | 300 seconds; use max(normal delay, bounded Retry-After) | Respect receiver pressure within bounded delivery age |
| Delivery age | 1 hour after event commit | Bound backlog; no fresh attempt at/after expiry |
| Attempt claim lease | 30 seconds; no renewal while HTTP runs | Longer than deadline, bounded crash recovery; fenced owner token |
| Tracking window | 30 days from admission | Accommodate long workflows; expiry means outcome_unavailable |
| Sanitized audit and dedup tombstones | 30 days after terminal tracking/delivery state | Incident investigation and request replay protection |
| Raw destination removal | Immediately on terminal delivery/unavailable state | Minimize capability retention; backups follow existing restricted policy |
| URL / event / response headers | 2048 UTF-8 bytes / 4096 bytes / 16 KiB | Bound untrusted input and payload; response body never read |
| Pending roots | 100 per verified principal, 10000 global | Prevent one principal monopolizing tracking |
| Tracking storage | 64 MiB per principal, 512 MiB global logical serialized bytes | Includes intent/member/event/audit records; count before allocation |
| Members / edges per root | 100000 / 500000 | Bounded graph work; over-limit tracking becomes unavailable, computation continues |
| Attempt audit | At most 3 rows per event | Match attempt cap |
| Dispatcher concurrency | 4 attempts global, 1 per principal | Fair round-robin due-root selection, computation worker isolation |
| Evaluator page | 256 members/edges, 100 ms scheduling slice | Yield across roots; traversal is not run in workers |
| Reconciliation interval | 30 seconds for subscribed due roots | Recover missed signals with bounded indexed reads |
| Computation hook budget | 50 ms total incremental bookkeeping per lifecycle call, no internal retries | Failure suppresses closure, not computation |
| Admission pressure Retry-After | 60 seconds | Avoid tight retry loops |
| Idempotency key | 16–128 ASCII token characters | Bound receipt indexing; avoids new receipt lookup API |
| Noninterference acceptance | p95 completion/next-job latency increase <=5% and <=50 ms per transition | Both limits required, at least 1000 transitions against disabled baseline |

All storage counts include terminal retained records, not just active roots. Reserve
space for the bounded terminal summary at admission. When capacity cannot retain new
member evidence, stop recording growth for that root, set incomplete tracking when
possible, and never stop computation. Missing producer closure prevents false events
if even that marker fails. Global logical bytes are not RSS: actual Redis memory and
latency must be measured before activation, with admission disabled if these bounds
cannot preserve tasking. Do not evict RQ keys to free notification capacity.

Retain only minimal membership while evaluation remains active. On tracking closure,
delete member/edge receipts and raw intent, retaining bounded sanitized outcome,
event/attempt summary and allowlisted credential-free idempotency receipt. Never
retain browse tokens or their expiry as a replay response; freshly authorized
retries use the existing mint helper as specified in the contract. Quotas still
count retained bytes.
Do not delete the destination before pending delivery has ended. Admission-pending
records share the 30-day tracking window; unavailable tombstones prevent same-key
reenqueue. No new attempt may extend beyond the one-hour age: shorten its deadline
to remaining age. Dispatch pause does not reset time or attempt counts.

## Decision Provenance

Decision Venue: user-directed kickoff execution, 2026-10-28, UTC.  
Participants Present: requesting operator and Codex (asynchronous conversation).  
Decision Owner(s): requesting operator; exact matrix approved 2026-10-28 19:56 UTC.  
Implementer(s): Codex; runtime implementation follows the approved checkpoint.

Accepted direction: short independent delivery, limited retries, and suggested
10-second budget. The operator explicitly approved all exact values with the RQ-WH-01 matrix. No model parameterization changes.

## Rationale and alternatives

Unlimited retention/retries would convert receiver outages into shared-resource
pressure. A single attempt would make transient faults unnecessarily lossy. Longer
tracking increases Redis residency; shorter tracking can miss large batches. Start
with explicit bounds and measure representative graphs before activation. A separate
durable database would add a transaction/recovery boundary; existing Redis is the
smallest candidate and explicitly does not promise durable delivery after Redis loss.

## Evidence

[Source and probe evidence](../work-packages/20261027_rq_webhooks/artifacts/20261028_source_and_probe_evidence.md)
shows current publication gaps and actual RQ dependency behavior. Numeric performance,
HTTP deadline, quota fairness and production-equivalent tests remain unexecuted.
The [contract](../schemas/rq-webhook-contract.md) and acceptance matrix define the
required tests; values must be revised through this ADR if measured bounds fail.

## Risk and rollback notes

Limits can deny new callbacks or leave long/large workflows without notifications;
computation behavior is preserved. Disable admission first, drain accepted tracking,
retain sanitized audit, and keep worker instrumentation through producer drain.
Dispatch pause is an emergency control, not retention extension. Local implementation/integration is authorized by the checkpoint approval;
production rollout remains excluded.

### Implementation budget allocation (2026-10-28)

The total 50 ms hook limit is unchanged. Receipt construction has at most half
that budget and streams JSON with deadline checks rather than recursively copying
large dependency tuples. Notification connections use 5 ms connect/read timeouts
and no retry. Exhaustion suppresses closure without changing computation.

Actual model acceptance found a short-lived adopted multiprocessing helper after
workhorse exit. A subscribed supervisor may spend at most 25 ms of the same total
budget waiting on pidfds, followed by positive child/protected-scheduler checks.
It never kills helpers or treats elapsed time as exit. Closure carries one absolute
deadline into receipt construction and reserves the remaining half for persistence;
worker retirement behavior is preserved. This bounded observation avoids a new
reaper service; longer-lived or uncertain producers remain unclosed.

### Evaluator scheduling allocation

The existing 100 ms scheduler budget is shared across active evaluators rather
than multiplied by the number of roots. Rotate after each bounded generator step.
This avoids consecutive per-root bursts observed while investigating failed
backlog measurements, preserves fairness and adds no new numeric policy. A running
step may complete after the cooperative deadline; workers never traverse the graph.
