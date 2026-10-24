# ADR-0104: Query catalog refresh operational bounds

Status: Accepted for implementation; production capacity acceptance pending
Date: 2026-10-23

## Context and decision

Use the existing batch queue and scheduler for the async-preferred query catalog
refresh contract. Bound enumeration/admission and retry to avoid replacing one
request-time scan problem with unbounded background backlog. These are workflow
operational settings; no model parameterization or scientific output changes.

## Decision provenance

Decision Venue: Codex execution conversation, 2026-10-23, America/Los_Angeles.
Participants Present: requesting operator and Codex orchestration/queue agents.
Decision Owner: operator selected the reviewed async-preferred contract and
instructed execution; Codex selected configurable implementation bounds within
its explicit measured-capacity gate. Implementers: Codex agents.

## Change summary

Previously no query-catalog background refresh schedule existed. Proposed
initial configurable values:

| Setting | Initial value | Purpose |
| --- | --- | --- |
| QUERY_CATALOG_ROOTS_JSON | Required when enabled | Explicit active namespaces and external coordination roots; no filesystem guessing. |
| QUERY_CATALOG_REFRESH_ENABLED | false | Rollout gate; preserve synchronous producer behavior until paired workers and recovery are configured. |
| QUERY_CATALOG_REFRESH_INTERVAL_SECONDS | 30 | Existing scheduler cadence for bounded maintenance admission. |
| QUERY_CATALOG_INVENTORY_LIMIT | 100 | Directory nodes processed per reconciliation tick. |
| QUERY_CATALOG_ADMISSION_LIMIT | 25 | Scope candidates admitted per tick. |
| QUERY_CATALOG_RETRY_SECONDS | 30 | Initial failure retry delay. |
| QUERY_CATALOG_RETRY_MAX_SECONDS | 3600 | Maximum failure retry delay. |
| QUERY_CATALOG_CYCLE_SECONDS | 86400 | Target recurring source reconciliation cycle, not an unconditional freshness guarantee. |
| Scheduler inventory lease | 60 seconds | Prevent concurrent cursor writers; verify ownership before cursor publication. |
| RQ job timeout / result TTL | 3600 / 86400 seconds | Existing maintenance precedent; explicit failed/expired handling. |

Disabled rollout mode is distinct from enabled-mode Redis/worker failure.
Enabled mode retains durable pending intent and never falls back to an inline
scan because admission is unavailable. All participating producers, worker
registrations and scheduler must agree on protocol/storage/rollout settings.
Enabled mode requires explicit root configuration and fails preflight when it is
missing. Historical default roots include legacy namespaces that are not served
on every host; retaining them implicitly can cause endless degraded cycles.
Automatically filtering defaults by current path existence would hide mount
outages. Explicit deployment configuration avoids both failure modes. See the
[canonical root example](../../wepppy/rq/job-dependencies-catalog.md#query-engine-asset-catalog-maintenance).

## Rationale and alternatives

Use bounded resumable inventory and per-project coalescing on owned infrastructure.
Per-asset jobs multiply backlog; a new queue/service is outside the reviewed
complexity budget. A Redis-only dirty set misses process-death and Redis-loss
windows; recurring source reconciliation is necessary even for scopes without
receipts. Native GIL release alone does not remove request latency.

The 60-second inventory lease bounds abandoned scheduler ownership without
blocking later ticks indefinitely. A slow tick may perform duplicate admissions,
which scope coalescing makes harmless; it cannot publish a cursor after losing
its lease. Missing redundant aliases are tolerated only when another configured
root for the same namespace is accessible. An unavailable namespace produces
degraded health and retries on the next tick, without the full-cycle delay.

The initial values are conservative implementation bounds, not a measured
production service-level objective. Before enabling rollout, record project
count, complete-cycle duration, oldest unreconciled scope, shared worker
capacity and queue delay; adjust configuration if the target is unattainable.
Do not claim a 24-hour guarantee when workers or storage are unavailable.

## Evidence and risks

[Contract](../schemas/query-engine-catalog-refresh-contract.md) and
[execution evidence](../work-packages/20261023_query_catalog_async_refresh/artifacts/execution_evidence.md)
retain the acceptance gates. Original incident: 8.56-second NFS scan with
5.70-second Python heartbeat starvation; writing the small soil Parquet itself
was fast. Existing WMesque/Run-catalog maintenance provides queue precedent.

Risks: distinct-project backlog, slow NFS enumeration, incompatibly configured
companion workers, and delayed recovery under outages. Expose actual progress
and pending age, retain diagnostics and never certify catalog currentness from
RQ success alone.

## Rollback

Disable new admission only after coordinating producer mode, drain/reconcile
active work, preserve durable requests and use the common publication guard.
Retain maintenance-ID disclosure classification for job retention lifetime.
Do not remove guard inodes or discard unacknowledged requests.
