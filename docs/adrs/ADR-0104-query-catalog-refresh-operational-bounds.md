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

## October 27 inventory execution clarification

The original scheduler-side eager directory expansion failed measured production
acceptance: legacy enumeration exceeded both the 60-second lease and a bounded
full-stream probe. Raising the lease or replacing listdir with scandir alone is
not evidenced remediation. Move streaming discovery into one existing-batch
maintenance job per inventory cycle, with fenced Redis progress batches drained
by the scheduler. No new queue, service, datastore or dependency.

Reuse the existing 3600-second maintenance job timeout and 86400-second retention
as candidate bounds; require complete legacy enumeration and kill/restart
acceptance before rollout. The inventory limit of 100 becomes the maximum
streaming checkpoint batch (up to 100 discovered entry records) and scheduler
discovery-drain budget (up to 100 scope records per tick, not 100 batches), rather than
permission for one node to enumerate unlimited children within a scheduler
lease. The admission limit, retry values and cycle target remain unchanged.
Checkpointed directory replay preserves emitted work without relying on opaque
filesystem cookies. One occupied batch worker and Redis frontier/batch storage
are the explicit operational costs; measure their capacity before enablement.
This clarifies implementation intent; production conformance remains pending.

## October 27 bounded pilot decision

Decision venue: operator execution conversation, 2026-10-27 UTC (October 26
America/Los_Angeles). Participants: requesting operator and Codex implementation,
correctness and security reviewers. Decision owner: operator, “execute the bounded
pilot.” Implementers: Codex agents. Implementation conformance remains pending.

Add a queue-wide cap of seven outstanding maintenance jobs, further bounded by
compatible live consumers, plus pause on ordinary ready backlog. The first
owned-scope pilot has retry-inclusive budgets of 25 refresh and two inventory
job IDs, a fixed 1,800-second admission window and a 300-second ordinary-wait
failure trigger. These are operational limits, not scientific parameters or
unconditional latency/freshness guarantees. Original cadence, consideration,
checkpoint, timeout and cycle-spacing settings remain unchanged.

Measured discovery/classification found 18,514 writable scopes. The scheduler
requires at least 49,405 considerations (about 16.47 hours at nominal cadence).
Actual 25-candidate scratch ticks fit the cadence, but real-source component
measurements include a 277.591-second collection/verification and an unresolved
verification after a 256.494-second collection. Per-tick limits alone do not bound
distinct-project queue accumulation. More component-only measurements cannot
supply that bound. Seven leaves one consumer outside catalog work when the
observed eight-consumer fleet is healthy; it is not a universal reservation.

Use authentic deployed capability and a manifest-bound disabled-mode exception
for owned fixtures so ordinary producers stay synchronous and unrelated scopes
cannot be released. Reject unbounded general enablement, a new queue/worker pool,
registration spoofing, arbitrary source bootstrap and weakening freshness checks.
See the canonical bounded-pilot section and the package's capacity assessment.

Pause only catalog admission on stop, retain receipts/checkpoints and let admitted
work drain. Explicit operator recovery/resume preserves original budgets and
failure evidence; it does not silently reset or extend a pilot. General async
remains disabled. Scope/capability/identity failures block acceptance; pilot
success is not whole-fleet capacity acceptance.

Pilot observation runs every 10 seconds with a 60-second owned observation lease,
reusing the existing lease-duration precedent and leaving multiple observations
before the 300-second wait-failure trigger. Renewal follows successful observation,
not an independent blind heartbeat. Controller loss pauses new admission without
stopping ordinary work or already-admitted jobs; gaps remain acceptance evidence.
These timings do not promise instantaneous reaction or automatic recovery.

The pilot's necessary participant cutover adds only an opt-in targeted batch
mode to the canonical deploy entry point, governed by
[the scoped deployment contract](../schemas/query-catalog-pilot-deployment-contract.md).
Source staging is a manifest-reviewed task-only patch on each existing production
baseline followed by canonical `--skip-pull`; unrelated local history is excluded.
If deployment source requires backporting the opt-in target to that baseline,
retain and validate the exact production candidate separately from local HEAD.
Default deployment modes and unrelated services remain unchanged.

Correctness review verified that production batch containers do not bind-mount
repository source. A host patch followed by `--skip-build` would run old code.
The scoped target therefore builds its image from the production baseline plus
the task-only patch, with verified existing native/dependency inputs and an
owned old-image rollback reference. Candidate image imports/source hashes must
pass before batch cutover. This corrects activation mechanics; it does not
authorize unrelated code, dependency or scientific changes.

Baseline provenance additionally shows mutable vendor branch/base references and
uncached installers in the ordinary image build. The pilot uses a source-only
derivative of each exact running local batch image inside the canonical targeted
mode, replacing only manifest-approved Python files and stale derived bytecode.
No network/installer/vendor/native step is permitted. This preserves the measured
nine native modules and 307-distribution runtime fingerprint instead of assuming
a mutable rebuild is equivalent. General build/deploy defaults remain unchanged.
