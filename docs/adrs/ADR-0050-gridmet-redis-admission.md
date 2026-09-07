# ADR-0050: Opt-in shared GridMET Redis admission

Status: Accepted for implementation; Forest acceptance pending  
Date: 2026-09-07

## Context

The multiple-interpolated downloader has a four-process pool per build. Point
requests have no shared admission. Independent workers therefore multiply
GridMET traffic, and the existing three attempts with 5/10-second backoffs do
not coordinate that traffic. A shared opt-in boundary must preserve direct
library use and existing climate output contracts.

## Decision

Use one Redis FIFO admission pool for point and gridded attempts, in the
existing `RedisDB.LOCK`, with explicit immutable configuration propagation.
Ratify the package's initial Forest values for implementation and live testing:

| Parameter | Previous behavior | Enabled initial value |
| --- | --- | --- |
| Shared limit | No shared cap | 4 live permits |
| Admission deadline | No admission wait | 900 seconds across all retries |
| Lease duration | No distributed lease | 300 seconds with background renewal |
| Waiting-ticket TTL | No queue | 60 seconds since waiting heartbeat |
| Polling | No queue polling | 0.25 seconds with 0.5–1.5 jitter multiplier |
| Operational namespace | None | `wepppy:gridmet:admission:v1` |
| Development Compose default | No admission | Disabled |

Redis connect/socket timeouts are two seconds each with automatic retries off.
Renewal runs every `min(lease / 3, 5)` seconds. Configuration requires
`lease > 3 * (renewal_interval + 2)` and
`queue_ttl > 3 * (1.5 * poll_interval + 2)`. Enabled HTTP clients also require
`lease > max(connect_timeout, read_timeout) + renewal_interval + 2`.
The durable [contract](../schemas/gridmet-redis-admission-contract.md) defines
state, public `None` semantics, policy agreement, and safety limits.

## Decision Provenance

Decision Venue: Roger Lew/Codex task session, 2026-09-07 UTC; exact request time
was not captured.  
Participants Present: Roger Lew and Codex.  
Decision Owner(s): Roger Lew authorized execution of the GridMET Redis admission
plan and selected Redis/explicit opt-in; Codex ratifies these implementation
values within that scope. Roger Lew/WEPPcloud operators own subsequent tuning.  
Implementer(s): Codex agents executing the work package.

## Change Summary

When explicitly enabled by orchestration, all runtime GridMET HTTP attempts
share four live permits rather than separate uncoordinated process limits.
The existing local pool of four, point `(10, 60)` and grid `(10, 120)` connect/
read timeouts, three HTTP attempts, payload limits, and result contracts remain.
Admission adds bounded queue scheduling, lease renewal, and explicit failures.
Public client `admission=None` and absent/false enable values retain zero Redis
construction and I/O. Environment resolution occurs only at orchestration.

## Rationale

Four preserves the earlier per-build ceiling while making that starting policy
aggregate. It is a conservative operational starting value, not a measured
upstream capacity or optimal throughput claim. A 900-second shared deadline
allows queued climate work to progress without multiplying that budget by three
attempts; retries and their backoff consume the same deadline.

A 300-second lease exceeds both 60/120-second read inactivity timeouts and
allows frequent five-second renewal, including while a request blocks waiting
for a chunk. Sixty-second ticket TTL removes dead waiters substantially sooner
than a holder lease, while quarter-second polling makes admission responsive.
The timing inequalities reject configurations unable to tolerate multiple
bounded Redis refresh opportunities. The HTTP inequality is conservative about
individual blocking calls and is not a total transfer-time bound.

## Alternatives Considered

1. Retain only the local pool: does not limit point requests or aggregate workers.
2. Shared counter/unexpiring ownership: lacks FIFO/position and leaks capacity
   after process death.
3. Enable Redis implicitly inside public functions: breaks literal `None` and
   adds a deployment dependency for direct library consumers.
4. Renew only after each response chunk: expires healthy holders during a
   blocked read, so use background renewal plus validity checks.
5. Claim expired leases fence upstream requests: GridMET does not honor tokens;
   document the limitation instead of asserting an unsupported socket ceiling.
6. Add a transport daemon or dependency: unnecessary to establish the bounded
   cooperative admission contract in this package.

## Consequences

FIFO improves fairness between attempts, but slow streams still occupy capacity
while live. Redis availability becomes required only for enabled calls.
Conflicting policy values in a live shared namespace fail explicitly rather
than silently permitting inconsistent limits. Independent namespaces and
configuration left disabled bypass the aggregate pool by design; deployments
must propagate one policy to every participating worker.

Redis guarantees the count of live leases, not hard upstream fencing after
process pauses, DNS stalls, or partition. Detected lease loss stops subsequent
HTTP work and fails the result; closing an already blocked response can wait
for control to return. Read inactivity bounds do not bound total trickle-stream
wall time. This limitation must remain visible in operational evidence.

## Evidence

- [Work package and initial values](../work-packages/20260907_gridmet_redis_admission/package.md)
- [Execution and Forest acceptance plan](../work-packages/20260907_gridmet_redis_admission/prompts/active/gridmet_redis_admission_execplan.md)
- [Earlier HTTP retry/concurrency decision](ADR-0028-gridmet-download-retry-concurrency.md)
- Existing timeouts and retry constants: `wepppy/climates/gridmet/acquisition.py`.
- Runtime tests, independent review, and Forest evidence remain required before
  deployment/closeout; this ADR does not assert they have already passed.

## Risk and Rollback Notes

Observe queue depth, wait exhaustion, active occupancy, Redis failures, lease
loss, upstream timeout/retry rates, and completed-request throughput before
changing parameters. Operators own tuning; revise this ADR and the contract,
configuration/runbook docs, tests, and package values before deploying changed
policy. Drain/recreate all participating clients together for policy changes.

Rollback sets `GRIDMET_REDIS_ADMISSION_ENABLED=false`, recreates the same Forest
workers, and verifies new processes resolve `None`. This restores prior
uncoordinated acquisition and removes Redis availability from that path. Never
flush Redis or delete a namespace with live owners. Revert code if required.

## Implementation Notes

Configuration is immutable and pickle-safe, Redis connections are process-local,
and atomic scripts use server time and one cluster hash slot. Each attempt
owns a unique ticket/token, releases before validation/backoff, and retries at
the FIFO tail. Independent review of this contract checkpoint precedes runtime
edits. Forest tests use isolated namespaces and never run a batch; subsequent
registry build, openwepp.org deployment, and batch validation are separate.
