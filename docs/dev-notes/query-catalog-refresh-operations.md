# Query catalog refresh operations

Status: implementation validation in progress; production rollout not performed.
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
and full-cycle target are configurable; measure actual oldest pending and
unreconciled scopes before claiming an attainable refresh target.

Enabled mode requires `QUERY_CATALOG_ROOTS_JSON`; missing configuration fails before admission. Use the same explicit configuration in producers, scheduler and every eligible batch consumer. The [queue catalog](../../wepppy/rq/job-dependencies-catalog.md) provides the canonical three-namespace example. Include only deployment-owned namespaces; a missing configured namespace is degraded storage evidence, not a completed cycle.

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
