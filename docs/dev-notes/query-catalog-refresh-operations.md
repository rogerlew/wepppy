# Query catalog refresh operations

Status (2026-10-27): original code deployed to wepp1–3 with async disabled.
Streaming-inventory and HTTP-readiness remediation is validated locally and in
private production-equivalent probes, but not deployed. Complete discovery and
bounded timeout recovery pass; fleet capacity remains a rollout gate.
Authority: [refresh contract](../schemas/query-engine-catalog-refresh-contract.md).
Execution and evidence: [work package](../work-packages/20261023_query_catalog_async_refresh/package.md).

## Scope and rollout

This maintenance indexes project artifacts; it does not generate model/interchange
outputs. Existing synchronous APIs remain available for tools and freshness
barriers. The new producer notification path uses asynchronous durable requests
only for managed roots when `QUERY_CATALOG_REFRESH_ENABLED=true`. Disabled rollout
mode retains synchronous behavior. Enabled-mode queue/Redis failure retains
pending intent; it never invokes a synchronous scan as an outage fallback.

Before enabling, every eligible batch consumer must advertise matching protocol,
root/storage namespace and shared coordination settings. Deploy the paired native
scanner release, publication/lifecycle guards, reader barriers, polling classifier
and scheduler together. Keep existing identities, mounts and permissions; an
incompatible companion worker blocks maintenance admission. No new queue/service
is required. Follow the existing deployment entry point for the target platform;
this document does not authorize rollout or prescribe an alternate deployment. The implementation review inspected `scripts/deploy-production.sh` and the existing wepp1 deployment record; coordinated cutover must use that entry point and its installed preset, queue fencing and compatibility preflights.

## Configuration

Operational limits and rationale are in
[ADR-0104](../adrs/ADR-0104-query-catalog-refresh-operational-bounds.md). Default
rollout is disabled. Scheduler cadence, inventory/admission bounds, retry delays
and full-cycle target are configurable. Inventory discovery now uses an existing-batch
maintenance job with `inventory_protocol: 1` in worker capabilities. The inventory
limit is up to 100 entry records per worker checkpoint and up to 100 scope records
drained per scheduler tick; the separate admission limit remains 25. Checkpoints
survive worker restart, while Redis loss rebuilds discovery from configured roots.
A restarted directory stream may replay its prefix; no durable OS offset is assumed.
Measure actual oldest pending and
unreconciled scopes before claiming an attainable refresh target. The configured
cycle interval starts from previous completion; it is not a strict per-scope
freshness bound. Record traversal/reconciliation time separately from the delay
before the next cycle.

Enabled mode requires `QUERY_CATALOG_ROOTS_JSON`; missing configuration fails before admission. Use the same explicit configuration in producers, scheduler and every eligible batch consumer. The [queue catalog](../../wepppy/rq/job-dependencies-catalog.md) provides a three-namespace example, not a complete fleet configuration. October 26 production evidence confirms active owned projects under `/geodata/weppcloud_runs`; excluding that legacy namespace would break existing workflows. Verify its identity, coordination and participant access before enablement. Include all deployment-owned namespaces; a missing configured namespace is degraded storage evidence, not a completed cycle.

The existing development, production, worker-pool and dedicated wepp3 Compose definitions supply service settings through `${WEPPPY_ENV_FILE:-defaults.env}`. Stage these settings in that existing service env file; a shell variable used only for Compose interpolation is not sufficient. Verify the effective configuration in web producers, query services, scheduler and every eligible worker before enabling. All synchronous publishers also need the common guard release, even when they do not consume the batch queue. No extra Compose override or service is required.

`QUERY_CATALOG_ROOTS_JSON` explicitly maps managed root path, storage namespace,
external coordination directory and layout. Canonical mappings preserve equivalent
host/container namespace identity. Custom mappings must put guard files outside
replaceable run trees on the same shared storage. Do not map a managed project as
standalone to bypass a missing coordination mount. Nested project identities are
distinct while sharing their top-level owner's lifecycle guard.

## Inspecting progress and failures

Use existing authorized project browse/download paths:

- `_query_engine/catalog.json`: last published asset catalog.
- `_query_engine/refresh/status.json`: digest-bound current/pending/failed state.
- `_query_engine/refresh/requests/`: durable unacknowledged invalidations.
- `_query_engine/refresh/attempts/`: useful publication/failure/lifecycle evidence.

These records remain in normal archives; they are excluded from query dataset
indexing. Restored request history is not authority to execute an old job. A model
job finishing and a catalog job finishing do not prove required dataset freshness;
consumer barriers validate actual entries/schema/source selection.

Maintenance IDs use `query_catalog_refresh_<UUID>`. Open polling deliberately
returns generic sanitized job information, not scope paths, request data or raw
tracebacks. Successful jobstatus keeps its existing response shape. Detailed
failure evidence requires existing project authorization/operator diagnostics.
Existing maintenance cancellation authority remains Admin/Root.

An inventory node limit is not a wall-clock limit: enumerating one large NFS
directory may exceed the scheduler lease before a cursor can be committed.
Repeated `lease_lost` results or an unchanged cursor do not establish progress.
October 26 rollout checks found this risk on the active legacy root; both eager
and full streaming directory listings exceeded bounded probe deadlines. Keep
enablement gated on actual full-directory and complete-cycle measurements;
first-page timings and nominal admissions per day are insufficient. Streaming
discovery removes this listing from the scheduler lease; worker checkpoints are
fenced by cycle/job identity and failed attempts retain their frontier. Scheduler
acknowledgment and pending-scope publication are atomic. Retry/timeout and full
cycle capacity still require measured acceptance.

HTTP/MCP handlers await blocking catalog, readiness and query operations in
Starlette’s existing worker pool. Responses still wait for freshness and preserve
authorization/error contracts; other event-loop requests can progress during
guard waits. This does not shorten NFS lock waits or guarantee request latency
under worker-pool saturation. The constant `/health` response runs directly on
the event loop, so queued blocking work cannot consume the worker token needed
to answer health checks.

Full production discovery on October 27 found 30,891 scopes across all four
roots, with empty frontiers and no errors. Discovery counts include READONLY
projects and do not establish refresh demand or completed reconciliation. Legacy
discovery retained progress across attempts; a bounded actual RQ timeout/retry
canary also completed without duplicate scopes. See the package's
[full inventory evidence](../work-packages/20261023_query_catalog_async_refresh/artifacts/20261027_full_inventory.md).

The existing wepp3 fork/archive role can read legacy projects and acquire the
external catalog guard, but its project-config guard fails on the read-only
legacy mount. Archive/restore also need writes there. This preexisting placement
issue is outside this catalog release per the operator’s October 27 disposition.
It is retained as a preexisting workflow limitation, not a catalog-rollout
blocker. No routing or mount changes are part of this remediation; legacy catalog
scopes remain included.

## Recovery and rollback

Preserve receipt and attempt evidence when a worker fails. Scheduler reconciliation
repairs missing/terminal admission pointers and discovers pending work after Redis
loss. Recurring source reconciliation also covers process death after artifact
publication but before invalidation. No later user request should be necessary.

Never remove a shared lifecycle lock inode to clear apparent contention. Confirm
the actual process/host ownership and lifecycle state; stale queue timestamps
alone do not prove a worker is dead. Generic workers cannot bypass READONLY.
Explicit combined-viewer offline preparation retains its separate reviewed
manifest-owned exception.

Rollback must coordinate producer mode and admission, drain/reconcile active
maintenance, and retain pending records. Old/new publishers cannot mix without
the common lifecycle guard. Keep maintenance-ID sanitization installed through
job retention even after worker rollback. Production project repair requires a
separate recorded action and actual final consumer readback.

## Bounded pilot operator CLI

The October 27 pilot uses installed `tools/query_catalog_pilot.py` and the
canonical explicit-pilot APIs. Deployment and authority prerequisites are in
[the pilot deployment contract](../schemas/query-catalog-pilot-deployment-contract.md)
and [catalog pilot contract](../schemas/query-engine-catalog-refresh-contract.md#bounded-admission-and-disabled-mode-pilot-october-27).
Do not run these commands before the approved candidate deployment and participant
readbacks. General asynchronous refresh stays false; the tool refuses general
enablement, alternative queue/root inputs, and identities other than UID1002/GID130.
No source overlay, extra worker or fake worker registration is used.

Run inside an existing batch container, as UID1002/GID130, against its installed
checkout. Choose a unique lowercase pilot ID (8–64 characters) and an absolute
private evidence directory. The directory must belong to that operator and have
no group/other permissions. Exact IDs, owned paths and raw observations are
operator-private; redact ordinary identifiers before copying summaries elsewhere.

```bash
python /workdir/wepppy/tools/query_catalog_pilot.py prepare --pilot-id qcat-20261027-example --evidence /tmp/qcat-20261027-example
python /workdir/wepppy/tools/query_catalog_pilot.py register --pilot-id qcat-20261027-example --evidence /tmp/qcat-20261027-example
python /workdir/wepppy/tools/query_catalog_pilot.py run --pilot-id qcat-20261027-example --evidence /tmp/qcat-20261027-example
```

`prepare` exclusively creates eight canonical `/wc1/runs/qc/qcat-pilot-*` fixtures
and one excluded sentinel from the retained owned 79-Parquet fixture; it copies
no real project or credentials. It initializes only these new scopes. The canonical `qc` shard is created if absent (production preflight found no
existing shard); its existing root, permissions and namespace are unchanged. Existing
fixture paths, symlink redirection or source count/size drift fail closed. Partial setup
is retained for inspection, never automatically overwritten or deleted. The
sentinel holds an intentional pending receipt that admission and inventory must
leave untouched. Preparation alone does not grant queue authority.

`register` freezes the exact initialized scope identities and begins the original
30-minute admission window. Start `run` promptly. It acquires observation ownership,
observes, and explicitly resumes the newly registered paused pilot. It observes
at 10-second intervals while ticking reconciliation every 30 seconds; slow artifact
readback does not substitute a blind lease heartbeat. Raw observations precede
60-second lease renewal. Existing ordinary disabled producers remain synchronous.
The receipt wave uses the reviewed receipt primitive plus explicit pilot admission.

The run first verifies receipt-free scoped inventory and its publications, then
records an owned receipt wave and verifies its acknowledgments. Every claimed
wave needs actual recorded finished jobs for all eight scopes; catalog existence
alone cannot satisfy it. Scientific source hashes, Parquet schemas, DuckDB counts,
actual query-engine consumers and sentinel invariance are checked. Raw pending,
publication identity/digest or schema failure blocks consumer calls; consumer
publication changes cannot be credited as repair. The known catalog-self entry
may appear on later scans; the scientific path set remains exact.

`status` inspects durable state. `pause` stops admission without suspending ordinary
RQ work. `resume` is an explicit operator decision using fresh observer ownership;
it preserves the original window, counters and failures. It cannot turn retained
acceptance failure into a pass. An interrupted receipt-creation wave requires
manual reconciliation of its retained phase/receipt evidence before resuming;
the tool never blindly replays it. It does not steal an existing observer lease.

`drain` acquires fresh observation ownership without resuming admissions. It can
monitor an already paused/failed pilot even when fixture setup/readback is invalid;
it never treats that drain as completed acceptance. It does not steal a live
controller lease.

`verify` performs standalone artifact readback; it grants no admissions and is
not a substitute for uninterrupted pilot observation. Keep the active controller
monitoring through readback and drain. The automated controller admits for at most
the original window and observes for a bounded 5,400 seconds per invocation. A
monitor bound, ordinary backlog, mismatch or artifact failure stops new work;
already-admitted jobs drain and unfinished receipts survive. Unresolved work is
reported as incomplete drain, not cleaned up by deleting jobs, queue keys or guards.

Exit 0 means the requested operator command succeeded; for `run`/`resume` it
requires completed acceptance. Exit 2 denotes a stopped/incomplete/failed run
result. Unexpected exceptions exit nonzero with retained evidence; they are not
success. `result.json` contains final counters, exact job bindings and sanitized
public job trees. `observations.jsonl`, phase readbacks, setup and registration
records retain the evidence needed to distinguish completed acceptance, safe stop,
monitor gaps and unresolved drain. No general fleet enablement follows.

A claimed job marked canceled can still be executing: RQ cancellation does not
stop its workhorse. The catalog ledger keeps that permit occupied and uncertain
until the worker records execution exit after all scoped work. Keep observing;
do not delete the job or ledger to manufacture a drain. A missing exit marker
requires explicit operator reconciliation. Normal RQ finished/failed/stopped
workhorse completion and timeout/death retry behavior remains unchanged.
