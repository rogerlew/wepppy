# ADR-0094: WMesque priority retrieval and scheduled master sync

Status: accepted for implementation, 2026-10-14; rollout pending.

## Decision and Rationale

Preserve remote-only wepp.cloud retrieval by default. Explicit deployment lists
enable ordered failover with one attempt per endpoint and a 300-second total
network budget, divided over remaining candidates. This retains the existing
single-server timeout ceiling while avoiding multiplying it by list length.
Retry only availability/network/raster-integrity failures specified in the
[contract](../schemas/wmesque-catalog-contract.md), not bad requests or local IO.

Reuse existing interval-based RQ scheduling: sync is opt-in, initially daily,
with a one-hour job timeout. Operators may configure the interval for their data
volume and update cadence. Do not enable local routing or synchronization merely
because a local server exists. Keep scientific datasets identified by immutable
manifest revision, independently of API version.

## Alternatives

Unbounded retries or 300 seconds per server increase outage latency. Automatic
local discovery changes working behavior without configuration. Multi-master
conflict management adds unnecessary ownership state. A new scheduler or public
bulk API duplicates existing private-network and queue mechanisms.

## Provenance and Evidence

Venue: this repository's operator/Codex conversation, 2026-10-14 UTC.
Participants: Roger Lew and Codex. Decision owner: Roger Lew for master authority,
default routing, shared-tailnet scope, and M1–M5 execution. Implementer: Codex;
bounded timeout/schedule values are implementation choices under that scope.
Evidence: [static assessment](../infrastructure/wmesque-implementation-assessment.md)
and [work package](../work-packages/20261014_wmesque_catalog_sync/package.md).

## Risk and Rollback

Slow servers may exhaust their divided attempt allowance; actual elapsed time
and failure tests must be retained. Socket read deadlines cover header/body
trickling; OS name resolution and connection/TLS establishment are not a universal
wall-clock guarantee. Unpinned replicas may lag; record revisions
and do not imply reproducible rebuilds. Disable sync and restore wepp.cloud-only
routing to roll back. Preserve releases and local extensions; no automatic deletion.
