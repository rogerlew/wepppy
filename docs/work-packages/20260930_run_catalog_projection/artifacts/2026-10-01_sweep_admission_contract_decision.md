# Sweep worker-availability admission checkpoint

Status: operator approved; implementation conformance pending. No deployment authorized.
Starting revision: `d11904f9f6334c219c835892729e884c5abdc675`.

## Authority and intended delta

The operator requests enqueueing catalog sweeps only when at least one batch
worker is available, because model work can back up the batch queue for days.
Existing admission already coalesces queued/started/deferred/scheduled sweeps;
thousands of redundant pending sweeps are not the current intended behavior.
This is an intended admission-policy change, not a deduplication defect fix.

Operator-confirmed interpretation: available means a
live **idle** worker subscribed to the destination batch queue, with catalog
protocol/database/write-mode metadata matching this deployment. Live means an
existing RQ worker hash with positive Redis TTL and no death marker; reuse RQ's
heartbeat expiry, not a new liveness timeout. Observe queue membership, state,
configuration, death marker and TTL from the same current registration in a
consistent Redis snapshot, not cached Worker attributes. Reject global RQ
suspension even if a worker still reports idle. Discovery must never heartbeat
a worker or prolong its registration. Busy, suspended, unknown-state, expired, absent,
wrong-queue and incompatible workers do not qualify. No qualifying worker means
return not-admitted without creating a job or changing the admission pointer.
Redis failures retain the existing scheduler error/retry boundary, not a false
claim that a worker is available.

Worker observation is not a worker reservation. It may race with ordinary model
dispatch or worker death. Preserve the existing atomic per-deployment admission
guard, including recovery after terminal/expired jobs; at most one sweep may
remain queued/running through a days-long backlog. Do not cancel existing jobs,
clear queues, change queue priority, add a service, or change other schedules.
SQL dirty state remains durable; the ordinary next tick rechecks availability.
Metadata may become stale during sustained saturation: retain explicit freshness
status and technical readiness failures, not a promise of the 60-second target.

## Contracts and scope

- Canonical: `docs/schemas/run-catalog-projection-contract.md`, section 6.4.
- Supporting operator/developer guide: `docs/dev-notes/run-catalog-operations.md`.
- Governance: `docs/standards/contract-first-change-standard.md`.
- Implementation boundary: `run_catalog_rq.enqueue_sweep` and its tests.
- Queue catalog/graph must describe the new admission condition without changing
  the batch queue, callable, dependencies, reserved IDs or redaction.

Compatibility: additive admission restriction; no project/schema/payload change,
no standalone PostgreSQL requirement. Security: no new credentials or privileges;
registration metadata remains a compatibility hint, not a replacement for the
deployment's connection-bound consumer proof. Existing SQL read hold remains.

## Regression evidence required

Real isolated Redis/RQ registrations: absent/empty pool; idle compatible worker;
busy-only pool; mixed idle/busy; expired/missing worker hash; another queue;
missing/malformed/wrong deployment metadata; unknown/suspended state; retained
death hashes; global suspension with idle state; non-expiring hashes; worker-name
reuse and stale queue membership; recovery when an idle consumer appears.
No-worker repeated ticks must create zero jobs and leave admission pointers unchanged.
Assert suspension/resumption behavior and that observation does not renew TTL or
update heartbeat; avoid RQ suspension helpers that heartbeat a supplied worker.
Concurrent schedulers with idle workers must still admit exactly one job; a
queued sweep across repeated ticks/restarts and worker loss must remain bounded.
Terminal recovery and the real file-to-SQL job/public-tree test must still pass.
Worker loss after observation must not weaken coalescing. Redis errors must be
observable. No live production queues are mutated to exercise these cases.

## Approval, reviews and commit gate

Operator confirmed live-idle semantics and the required contract-checkpoint
commit in response to the explicit clarification request on 2026-10-01.
Two independent read-only draft reviews passed after findings disposition below.
Canonical section 6.4 and the operator guide now carry the reviewed amendment.
Dirac and Ohm independently checked canonical promotion after operator approval;
both returned PASS for the documentation-only ancestor, with no blocking drift.
No runtime edits may precede an accepted, independently reviewed standalone
checkpoint ancestor commit. Runtime deployment is outside this request.

## Independent draft findings and disposition

- Dirac correctness review: no blocking coalescing-design defect; acceptance held
  for operator meaning, canonical promotion and authorized ancestor. Requested
  passive suspension checks and unchanged-heartbeat/TTL tests; added above.
  Dirac's narrow re-review closed these findings with technical draft PASS.
- Ohm security review SEC-21: positive TTL alone can include a retained death
  hash or globally suspended worker. Added consistent current-registration
  observation, death/global-suspension exclusions, no heartbeat extension and
  name-reuse/stale-membership/non-expiring-hash cases. Ohm's narrow re-review
  closed SEC-21 at draft-contract level with technical PASS, no new blockers.
- Both reviews retain all-consumer compatibility/origin proof separately from
  the admission hint; neither review grants operator or deployment authority.
