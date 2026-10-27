# Query-engine catalog refresh contract

Status: specified; implementation conformance pending. Contract phase initiated 2026-10-23. This contract governs the asset catalog at `_query_engine/catalog.json`, not the PostgreSQL Runs listing catalog.

## Authority, scope and rationale

Asynchronous refresh is the preferred path for artifact producers that do not consume catalog freshness before returning. Existing synchronous `update_catalog_entry`, `activate_query_engine` and run-context interfaces retain their return values and error semantics until explicitly migrated. A blanket replacement is prohibited.

The observed wepp1 failure is a missing catalog triggering a full native scan inside an HTTP submission. The native scan holds the GIL and can starve the serving process heartbeat. Artifact publication, catalog publication, and consumer readiness are distinct outcomes. A successful artifact write MUST NOT be advertised as a fresh catalog.

Use existing Redis/RQ, batch workers and scheduler infrastructure. No new queue, service, database, dependency or deployment topology is authorized. Existing model artifacts, filenames, column schemas, runtime identities, permissions and authorization remain unchanged. Canonical cross-cutting authorities include [NoDb persistence](nodb-persistence-concurrency-contract.md), [RQ responses](rq-response-contract.md), [report cache freshness](report-cache-freshness-contract.md), [artifact observability](../standards/artifact-observability-standard.md) and [generated artifact validation](../standards/generated-artifact-validation-standard.md).

The WMesque and Runs catalog queue implementations are precedents for transactional admission and concurrent invalidation handling, not a shared catalog data model. Mere duplicate suppression does not establish eventual consistency.

## Migration policy and interfaces

Introduce explicit `request_catalog_refresh(wd, asset_path=None)` for migrated producers. `asset_path=None` requests full reconciliation. The receipt describes durable intent and admission separately: scope, request identifier, `pending|queued|running|failed|current` state, optional canonical `job_id`, and safe error code. It MUST NOT claim an RQ job exists when enqueue has failed or coalesced without a known job.

Retain a synchronous refresh primitive for CLI/offline operation and consumer barriers. Its existing return shape remains actual catalog/entry data, never a queue receipt. No implicit Redis requirement is added to standalone synchronous tools. All catalog publishers participate in the same publication serialization protocol.

Migration classes:

| Class | Required behavior |
| --- | --- |
| Artifact producer; return discarded; downstream reads artifact directly | Prefer async after durable artifact publication; retain explicit downstream barriers where needed. |
| Producer followed by immediate catalog/schema/path-dependent consumption | Retain sync or install an explicit freshness barrier before consumption. |
| Query/report auto-repair; synchronous activation API | Retain existing synchronous contract initially; moving waiting work to another thread does not make GIL-holding native code safe. |
| Workflow finalizer/completion marker | Completion requiring discoverability waits for catalog publication; enqueue alone cannot satisfy it. |
| Offline migration/rebuild/admin CLI | Preserve synchronous operation and errors; async only by explicit new interface. |
| Unclassified/new caller | No migration until its dataflow and freshness obligations are recorded. |

The execution package's caller matrix records evidence and migration waves. Durable classification rules are this section; a historical matrix does not become perpetual authority. Every migrated route must preserve its primary domain job response and success semantics. Catalog jobs are maintenance work, not replacement WEPP job IDs.

## Identity and admission

A scope identifies deployment/storage namespace, canonical authorized project directory including nested `_pups`/scenario/batch subpaths, and project incarnation. `runid` or configuration name alone is insufficient. Recreated/restored/forked projects do not inherit executable coordination from prior incarnations. Existing legacy projects establish an incarnation through the serialized refresh initialization path; this does not mutate scientific state.

Resolve and validate scope using established run-path/access rules before durable intent or enqueue. Revalidate at worker execution and publication. Relative asset paths and allowed parent-project references retain existing containment policy; arbitrary host paths, traversal, symlink escapes and user-selected queue/function names are not admitted. Store the authorized source locator; never derive authority from a queue payload alone.

For each scope, admit at most one queued/started/deferred/scheduled refresh job. Use Redis transaction/WATCH admission following the established pattern and job IDs of the form `query_catalog_refresh_<canonical-hyphenated-UUID>`, with suffix allocated by `new_rq_job_id()`. This narrowly reserved prefix enables safe classification before RQ payload deserialization; it is distinct from the Runs-catalog prefix. A WATCH conflict is contention, not proof of accepted work. Durable pending intent remains discoverable and recoverable. Terminal/missing jobs can be replaced after reconciliation; a stale admission record cannot permanently block refresh.

Do not require an idle worker to record invalidation. Capacity shortages leave explicit pending work. Bounded admission/retry must return promptly without invoking a catalog scan in the producer/request process. Multiple changes to one project coalesce; distinct projects remain independent.

All consumers eligible for the shared batch queue must advertise the refresh protocol version, configured storage namespace/root mapping and publication-coordination compatibility. Admission checks the queue's eligible consumers; incompatible consumers block new maintenance admission, while durable requests remain pending. Execution revalidates these properties before opening a project. Startup and deployment preflight must detect companion/off-host or mixed-version consumers lacking the protocol. This is not authority to change identities, privileges, mounts or queue topology. Absence of compatible consumers is visible pending/unavailable capacity, never permission for inline scan fallback.

## Durable invalidation and no lost updates

Artifact publication precedes invalidation. If publication succeeds but invalidation persistence fails, report the partial outcome explicitly and retain repair evidence; do not silently return fully successful catalog scheduling. Existing domain error envelopes and logs must distinguish committed artifacts from catalog maintenance failure. A Redis outage alone must not lose already-durable invalidations or trigger an inline full scan. Process death between artifact publication and receipt persistence is possible and cannot be repaired by receipt rediscovery alone. The recurring source reconciliation below MUST discover this gap without another user request. The request API guarantees durable acceptance only after receipt persistence; the project convergence guarantee additionally depends on completed recurring reconciliation.

Persist immutable unique invalidation receipts in `_query_engine/refresh/requests/`. Each records protocol version, scope/incarnation, request ID, relative asset path or full-scan flag, and UTC creation time. Write through a same-directory temporary file, flush, atomic replace and directory durability handling. Receipt IDs are opaque unique tokens, not reusable timestamps. Requests are durable project records; Redis holds derived admission/discovery state only.

A worker snapshots a finite set of receipt IDs and coalesces overlapping paths. Missing catalog requires a full scan. Existing catalogs allow asset/subtree updates, including deletion and removal of no-longer-existing subtree descendants. A partial refresh must not remove unrelated entries or alter parent/scenario path precedence.

Only the exact snapshot successfully incorporated into a published catalog can be acknowledged. Requests arriving during scanning remain pending even if a scan happened to observe their files. This set-based acknowledgment is equivalent to dirty/indexed generations without a fragile cross-store increment. Never clear a project-wide dirty flag or the entire receipt directory on completion.

After publication the worker records the acknowledged receipt IDs in visible attempt/status evidence before removing those requests. Crash before acknowledgment causes harmless replay; crash after acknowledgment but before cleanup is reconciled using the recorded publication. A failed attempt retains its pending receipts and last-good catalog. Bounded passes prevent a constantly changing project from monopolizing a worker; residual work gets one successor through atomic admission, not one job per asset.

## Publication and synchronous coexistence

Catalog publication MUST use a complete same-directory temporary file and atomic replacement. Preserve current schema/version and canonical path semantics. Readers observe either a complete old catalog or a complete new catalog. Refresh is metadata discovery, never WEPP interchange generation or scientific artifact regeneration.

All synchronous and asynchronous publishers MUST serialize final publication using one stable, process-held filesystem guard per top-level project owner. The configured coordination directory is outside replaceable/deletable project trees, on the same already-mounted shared storage: `/wc1/query-engine-coordination/locks/` in canonical container view (host `/geodata/wc1/query-engine-coordination/locks/`). Lock filenames hash configured storage namespace plus top-level project-relative identity; nested catalogs share their owner's lifecycle guard but retain independent admission/receipt scope. Different configured run roots require an explicit equivalent shared coordination path before deployment. This adds files on existing storage, not a mount or service.

Refresh initialization/publication, synchronous updates, fork destination publication, archive snapshot, restore, deletion and recreate MUST acquire that same guard. Lock files MUST NOT be removed/replaced during normal cleanup or project deletion; retaining the inode prevents old-holder/new-lock splits. Acquire this guard before existing project-config lifecycle guards, then existing Roads lifecycle guards when needed; multiple owner guards use sorted namespace/identity order. Never acquire the catalog guard while holding a downstream lifecycle guard in the opposite order, except for a short catalog freshness barrier under an ordinary Roads shared read. Roads readers MUST retain concurrent shared admission and MUST NOT hold the exclusive catalog guard for their entire read. This narrow exception is safe because archive uses compatible Roads shared admission, while restore and writers MUST acquire Roads exclusive admission nonblockingly and release catalog ownership on conflict. Blocking Roads exclusive acquisition and shared-to-exclusive upgrades are forbidden; catalog publication remains exclusively guarded. Publisher code does not acquire NoDb locks while holding it. The implementation inventory must audit all legacy publisher/lifecycle entry points before enabling async admission.

Within the stable guard, validate the opened project directory identity, current incarnation and readonly state immediately before publication. Restore/recreate changes incarnation while holding the guard; old scan results are discarded even if paths or files look identical. Scan collection is outside the guard; archive holds it for the catalog snapshot, and destructive lifecycle work holds it through tree replacement and new-incarnation publication. No Redis lease can authorize bypassing the guard. Offline synchronous callers use the same filesystem guard without needing Redis.

Standalone synchronous compatibility is a distinct supported mode: a directory outside all configured/known managed run roots, with no managed incarnation/admission identity, may use a process-held local guard at `_query_engine/refresh/publication.lock` and requires neither Redis nor `/wc1` access. Normal standalone refresh must not unlink/replace that guard; concurrent deletion/restoration/replacement of a standalone directory is outside this local mode and must first adopt managed lifecycle coordination. The caller must not use local mode to operate on an actively managed project. Resolve physical root/aliases before classification; known canonical managed roots and recorded managed identity cannot fall back to local mode when shared coordination configuration is missing or unavailable. Reject that misconfiguration explicitly. Ordinary temporary-directory synchronous APIs retain return/error behavior and need no additional mount permissions. Test both an unconfigured temporary directory and a managed-root attempt to select local mode.

Deployment acceptance must prove coherent exclusion across actual hosts/containers/NFS and identities, including old-holder/new-lock and restore/delete races. Unsupported locking blocks rollout, not a silent unlocked fallback. Coordination locks are empty non-project records excluded from project archives because they reside outside the run tree; all project diagnostics remain visible and archived.
A scan may run outside the stable guard, but publication MUST compare its starting catalog revision/incarnation against the current publication while holding the stable guard. If another writer published meanwhile, rebuild or rebase from the current catalog; never overwrite newer entries with an old full scan. Sync updates also advance revision metadata. A process holding a stale queue lease cannot bypass filesystem ownership or lifecycle checks.

Atomic catalog and sidecar writes are not a multi-file transaction. Status/publication metadata MUST bind the catalog by content digest and incarnation. On crash or digest mismatch, classify freshness as unknown/pending and reconcile; do not infer current status from a job result or orphaned sidecar. The lock is not held while waiting for RQ dependencies or Redis availability.

Source artifacts can change during scanning. For the new async acknowledgment and freshness-barrier paths, an unreadable/corrupt required asset fails readiness and retains pending intent instead of silently certifying it current. Required assets are the requested datasets and any source needed to resolve their schema/path dependencies; full-scan completeness remains unknown if required metadata was skipped. Full reconciliation exposes skipped/unreadable paths. The retained synchronous compatibility API may continue its existing best-effort schema/skip behavior and return/error shape, but such a return cannot satisfy the new strict acknowledgment or freshness barrier without explicit required-entry validation. This bounded distinction preserves offline behavior while preventing a false async current claim. Publication claims cover the acknowledged requests, not an atomic snapshot of all scientific files. Consumers requiring a stable scientific snapshot retain their stronger source-version checks.

## Recovery and liveness

An existing scheduler task reconciles pending receipt scopes against admission/job state. A Redis dirty-scope index accelerates normal operation but is not the only discovery mechanism. Startup/Redis-loss reconciliation uses a resumable, bounded traversal of configured authorized run roots, including supported nested scopes, to rediscover durable receipts. This runs outside web requests and must expose traversal progress/failures. Never scan arbitrary filesystem roots.

The same background reconciler also revisits every registered/configured supported project scope on a resumable recurring source-reconciliation cycle, including scopes with no receipt. It compares source metadata/catalog dependencies and requests or performs a full index-only refresh when freshness cannot be established. It MUST discover changes after a producer dies between artifact rename and receipt persistence, without a later user action. Root/child enumeration must cover supported nested projects and durable registry gaps; progress cursors and failures cannot silently skip scopes. Use bounded per-tick admission and per-scope work to preserve fairness. Configure and report the target complete-cycle interval and actual oldest unreconciled scope; capacity evidence must show that this target is attainable before rollout. No unconditional time bound is promised during storage/worker outage. This recurring inventory cost is explicit and must be measured against the incident workload; it cannot run in HTTP handlers.

Inventory execution clarification (2026-10-27; conformance pending): large-directory
discovery runs as at most one active maintenance job per configured inventory
cycle on the existing batch queue. Scheduler ticks admit/recover that job and
drain checkpointed discovery batches; they do not enumerate entire directories.
Inventory jobs use the existing `query_catalog_refresh_` maintenance-ID privacy
classification, matching worker capabilities, and existing maintenance timeout
and retention bounds. Worker capability advertisements distinguish support for
this inventory protocol; mixed consumers block admission. Filesystem receipt and
catalog protocols remain unchanged.

Discovery streams directory entries and checkpoints its directory frontier,
current directory identity, emitted-child deduplication and sequenced scope
batches in Redis. These checkpoints survive worker restart, not Redis loss;
filesystem roots/receipts remain authoritative and reconstruct discovery. A
restarted stream may replay a directory prefix: no portable durable filesystem
offset is claimed. A child is marked seen atomically with its frontier/scope
publication. Directory exhaustion is committed only after all prior discoveries.
Every worker checkpoint is fenced by the current admitted job identity and cycle;
a stale worker may not publish progress or completion after replacement. Slow
filesystem I/O holds no scheduler inventory lease.

Scheduler consumption acknowledges a discovery batch only in the same fenced
transaction that incorporates it into its pending scope cursor; trimming occurs
after that commit. Discovery completion requires exhausting the full frontier
with no unresolved required-root/directory traversal failures; retain and retry
failed frontier items and block completion while they remain unresolved. Full-cycle
completion additionally requires all
discovered scopes to reconcile. Timeout/error retains incomplete progress and
retries with existing bounds. Directory replacement triggers revalidation/replay;
ordinary mutation does not continuously reset a busy root. Inventory is eventual,
not a scientific snapshot: later cycles cover additions missed by an active
stream. Nofollow/containment and scope identity are revalidated before traversal,
admission and publication. Actual legacy full-listing and worker-kill/restart
acceptance are mandatory before enablement; a first-page benchmark is insufficient.

Retry failed/stopped/canceled/abandoned maintenance with bounded backoff and retained diagnostics; distinguish deliberate operator suspension from recoverable failure. There is no unconditional freshness deadline when workers/storage are unavailable. Expose pending age, last success, last error, queue delay and reconciliation health. Recovery must prove convergence after worker death, enqueue failure, Redis restart and temporary storage outage. Exact scheduling/backoff limits require measured acceptance and documented configuration before implementation rollout; no new hard-coded scientific thresholds are introduced here.

Admission release and successor admission must check ownership atomically. A finishing old job cannot clear a newer job's reservation. Producers arriving at the final worker check must either join the active job's pending work or leave durable discoverable work for a successor. False job completion cannot acknowledge pending requests.

## Reader freshness and caches

No query consumer may interpret absent/not-yet-indexed metadata as proof that a required artifact does not exist. No stale catalog may silently select an old `fs_path`, identifier alias, schema or scenario source. Preserve the current fresh-selection verification in report cache publication.

Before any producer migrates, upgrade its affected internal readers to a targeted freshness barrier: snapshot the required receipt IDs for the same incarnation, incorporate/verify them, read back the requested entry/schema/physical selection against the actual source, and reload held catalog objects. Existing `resolve_run_context` catalog reuse and `ReportQueryContext.ensure_datasets` missing-entry checks are NOT sufficient for an already-cataloged asset whose schema, alias or fs_path changed. Presence alone is not a barrier. Source validation also detects changes in the artifact-to-receipt crash gap; current metadata cannot be inferred solely from an empty request directory.

Source-selection clarification (implementation review, 2026-10-23): without a matching producer receipt, a permitted explicit `fs_path` remains the selected authority, including a parent source when a child copy also exists. Revalidate that selected source's actual schema and identity; do not silently discard report-catalog redirection. A captured asset/subtree receipt identifies newly published canonical artifacts in that scope and may replace inherited fallback selection. Full recurring reconciliation uses normal full-activation precedence to recover receipt-free publication. Merely finding a child file does not prove it supersedes an explicitly selected parent. This preserves the report cache contract while allowing producer intent and recurring reconciliation to advance selection.

Keep externally synchronous behavior in report auto-repair, run-context auto-activation, Geneva queries, explicit activation endpoints and workflow finalizers while implementing these internal barriers. A barrier acknowledges only its captured receipt set after publication and actual dependency validation, not whatever requests arrive later. Revalidate relevant source identity before executing/publishing freshness-sensitive results as required by the report/domain contract. Concurrent mutation can yield explicit superseded/retry behavior, never silently mixed selection. Do not route these barriers back through async admission and then wait on the same saturated queue. Later externally asynchronous reader conversion requires explicit domain/API contract amendments and bounded ready/pending/failed behavior; existing successful synchronous responses cannot become empty data or generic 404s.

Report/query contexts and in-memory catalogs created before publication must revalidate against publication/source identity before freshness-sensitive reuse. Last-good catalogs may be used only where their required source dependencies are still valid. Published freshness metadata is not authorization. Flow-duration sessions retain their existing stale/mismatch refusal and reload semantics; background maintenance must not imply a new valid session snapshot. Metadata publication may invalidate a held session snapshot; the session must reload rather than silently adopt new provenance. This bounded clarification is cross-linked from its domain contract.

Retained web-serving synchronous native scan paths must release the GIL during native I/O/traversal before rollout, or execute out of process while preserving the synchronous response. In-process thread offload alone is insufficient for a GIL-holding scanner. The initial implementation must choose and validate native GIL release; no new service is authorized. This prerequisite prevents reader auto-activation from reproducing the incident after producer conversion.

## Lifecycle and visibility

Visible records: `_query_engine/catalog.json`, `_query_engine/refresh/status.json`, immutable requests, and attempt diagnostics under `_query_engine/refresh/attempts/`. Retain useful failed/partial evidence through normal project browse/download/archive/restore. Never hide required diagnostics behind a fixed download-only endpoint. No secrets or unrestricted absolute host paths in user-visible receipts/job payloads.

The exact subtree `_query_engine/refresh/**` is excluded from full and subtree query-dataset scans, including explicit requests targeting it; diagnostics/receipts must not recursively become query datasets or leave deleted receipt entries in the catalog. This is an indexing exclusion only: browse/download/archive visibility remains required. Existing catalog/cache indexing behavior outside this exact subtree is unchanged.

Redis reservations and external empty lifecycle locks are coordination, not scientific provenance. Archive/restore preserves catalog and diagnostics; restored request history is evidence, not authority to execute an old job. Fork/restore establishes a new scope incarnation, invalidates copied freshness, and schedules reconciliation only after lifecycle completion. No queued job may recreate a deleted run. Archive/delete/restore/fork transitions and publication must share a proven exclusion/identity protocol; root existence checks alone are insufficient against replacement races.

Generic refresh of readonly projects remains readable according to current contracts and never writes new receipts/status/catalogs. The existing [combined-viewer offline preparation exception](../ui-docs/contracts/combined-watershed-viewer-contract.md) remains valid: operator-invoked staged preparation and manifest-owned rollback may publish their authorized artifacts/catalog under the shared stable guard, retaining exclusive `os.link`, refusal to overwrite unknown outputs and manifest hash ownership. Generic async workers never inherit that exception. Missing/stale readonly catalog uses existing explicit failure behavior; no worker bypasses readonly flags. Temporary/replay workspaces and parent-backed scenarios retain their existing owner/path rules. Deletion must invalidate executable coordination without losing records that the canonical archive lifecycle requires retaining.

Existing authenticated project inspection is the detailed status surface. Open job polling classifies `query_catalog_refresh_` IDs before deserializing job payloads. Job-info exposes only a fixed sanitized maintenance shape: exact job_id, status, generic description "Query catalog maintenance", started_at/ended_at, runid=null, result=null, exc_info=null, auth_actor=null, children={}. Failure uses canonical error envelope with code `query_catalog_refresh_failed`, generic message "Query catalog maintenance failed; consult project diagnostics", and opaque error_id. No paths, scope identity, asset requests or raw traceback are public.

Successful jobstatus retains its existing status-only response shape; its error paths use the same sanitization. Apply the classification to single-job, batch and recursive polling, unknown/expired IDs, deserialization/import failure, abandoned jobs and IDs retained after rollback. Missing/expired prefix IDs retain the existing not-found HTTP behavior with generic details; malformed/unreadable retained jobs expose only sanitized failure. Public RQ state does not assert catalog currentness. Prefix recognition remains installed through the retention lifetime of these jobs, including rollback. Detailed state is available through existing run-authorized project records/operator diagnostics, not an auth-policy change or new endpoint. The RQ response contract owns this specialization.

## Valid-state and input matrix

| State/input | Required outcome |
| --- | --- |
| Never indexed, valid project | Durable full-scan request; producer responsive; freshness-sensitive consumer uses barrier. |
| Present-empty valid catalog | Valid empty state; add requested assets without treating empty as corruption. |
| Populated catalog, changed/deleted asset/subtree | Coalesced update/removal; unrelated entries preserved. |
| Legacy catalog without refresh metadata | Read under current schema; initialize coordination safely; no invented historical freshness. |
| New receipt while queued/running/finalizing | No duplicate active admission; no lost request; bounded successor if needed. |
| Duplicate/replayed receipt | Idempotent publication/acknowledgment. |
| Malformed catalog or required asset unreadable | Explicit failed/unknown freshness; retain last-good readable artifact/evidence; no silent current claim. |
| Redis/worker/storage unavailable | Durable pending when possible; explicit partial failure if receipt cannot persist; no inline scan fallback. |
| Worker crash at any publication step | Atomic readable catalog, digest-checked status, replayable pending intent. |
| Readonly, deleted, recreated, restored or forked scope | Preserve lifecycle authority; old job cannot mutate new/absent scope. |
| Traversal, symlink escape, wrong deployment/incarnation | Reject before publication without affecting valid authorized paths. |
| Stale reader cache/session | Revalidate required sources or preserve domain-defined reload/refusal behavior. |

## Implementation and acceptance gates

Before production code edits, complete two independent contract reviews and their disposition and commit the accepted checkpoint as a standalone ancestor per the contract-first standard. This document does not claim that gate has occurred.

Required implementation evidence:

- Real Redis/RQ races: producer kill after artifact publication but before receipt creation with no further user action; duplicate admission, final-check race, request during scan, stale worker, crash/retry and Redis-loss rediscovery; tests cannot mock away the admission/publication boundary.
- Real filesystem/NFS: multi-publisher lock exclusion, source changes, atomic readback, missing and corrupt catalogs, deletion and lifecycle replacement. Compare final entries/schema/path mapping against a synchronous reference.
- All migrated caller families: preserve domain job response, prepared model artifacts and direct consumers; barriers prove immediate report/query/finalizer readiness. Re-run old stale-cache/identifier/fs_path cases.
- Normal authorized browser/download/archive/restore under production-equivalent identities, mounts, groups and umask; verify visible attempt evidence and restored incarnation separation.
- Original incident acceptance: isolated copy of affected Mill Creek project with missing catalog; submission returns without full scan on serving process, job executes, final artifact/catalog readback matches intended data, heartbeat remains responsive.
- Queue wiring catalog, `wctl check-rq-graph`, live job-tree inspection, focused tests and substantive broad gates. Paired native GIL release for retained serving scans is a required compatible prerequisite, not a substitute for async/readiness evidence.

Rollback stops new async admission, reconciles/drains active maintenance and preserves receipts/diagnostics before restoring synchronous producers. Mixed-version publishers must not run without common publication/lifecycle coordination. Existing catalogs remain schema-compatible; rollback cannot silently discard unacknowledged changes.

## Bounded admission and disabled-mode pilot (October 27)

Status: implemented; bounded production pilot conformance passed October 27.
See [acceptance](../work-packages/20261023_query_catalog_async_refresh/artifacts/20261027_shared_pilot_acceptance.md) for scope and evidence limits.
The operator authorized execution of the bounded pilot on October 27, 2026.
This section does not authorize general async enablement.

### Shared batch admission

All inventory and refresh admission paths, including producers, reconciliation
and retries, MUST share one atomic queue-wide admission decision. At most seven
catalog-maintenance jobs may be outstanding; admission also respects the current
compatible live consumer count. Count queued, started, deferred, scheduled and
reserved work across configurations/pilots, not only one project or current
configuration. Worker disappearance does not release a permit. Existing
nonterminal or unresolved records remain counted until their disposition can be
proved. Per-scope coalescing does not consume a second permit or cumulative job
budget. Permit/budget reservation and RQ enqueue commit together; contention,
Redis failures and missing/corrupt accounting fail closed with intent retained.

RQ cancellation alone is not execution-exit proof: the installed `Job.cancel()`
can mark a running job canceled without stopping its workhorse. A claimed,
canceled job remains outstanding and uncertain until its worker records exit
after all scope/inventory work. Admission and drain observations use the same
classification. Unclaimed canceled work may retire because the atomic execution
claim watches job status. Genuine RQ finished/failed/stopped work retains normal
workhorse-completion/death recovery, including timeout and killed-worker retries;
missing exit proof for a claimed cancellation requires explicit recovery.

Ordinary ready jobs waiting on the batch queue prevent new catalog admission.
Inspect raw job identifiers, states and timestamps without executing task payloads
or invoking registry cleanup; unknown/corrupt classification is conservative.
Do not suspend ordinary queues, preempt scientific work, discard receipts, or
invoke inline refresh as an enabled-mode admission fallback. Already-admitted
maintenance may drain; a job-count cap is not an elapsed-delay guarantee.

Trusted operator APIs may pause/resume catalog admission independently of
ordinary RQ execution. No new public endpoint or authentication authority is
introduced. A pilot pause is latched until an explicit operator resume; resume
cannot extend its original admission deadline, reset consumed budgets or erase
failure evidence. Missing accounting never implicitly creates a fresh budget.
Reconstruction requires explicit operator recovery against retained job evidence.

### Disabled-mode pilot authority and isolation

General `QUERY_CATALOG_REFRESH_ENABLED=false` retains existing synchronous
producer behavior. Only explicitly pilot-tagged admission and recorded pilot
jobs may use a bounded exception. They MUST present an existing operator-created
pilot manifest; a caller-provided pilot ID alone is not authority.

The immutable manifest binds the pilot generation, queue/configuration,
capability version, owned fixture paths, scope IDs, namespace, incarnation and
directory identity, original deadline and cumulative budgets. Fixtures MUST be
new owned validation projects in existing canonical namespaces; an ownership
marker and exclusive creation are required. An unrelated valid project is not
implicitly authorized by sharing a root, prefix, owner or parent. Reject symlink
redirection, changed identities and unlisted descendants before initialization,
receipt creation or publication. Initialization of only the approved fixture
metadata is an explicit operator preparation step, not a public disabled-mode
bypass.

Each admitted job ID is recorded atomically with its pilot generation, kind and
scope/identity binding. Workers validate this binding, authentic compatible
parent registration and current filesystem identity before scope/receipt access.
Job arguments or metadata cannot enlarge the manifest. Retired job IDs cannot be
revived without a new budgeted admission. Admission pause/deadline expiry permits
already-recorded jobs to execute/drain; it does not permit replacement jobs or
retries. Missing/malformed manifests or uncertain authority fail closed.

Pilot inventory seeds only approved canonical-root locators. It MUST NOT traverse
all production roots, expand an approved parent into unlisted scopes, or consume
ordinary dirty indexes. Its checkpoint/stream state is isolated by pilot
identity. The ordinary scheduler continues returning disabled; only explicit
pilot reconciliation uses the exception. Worker capability advertisement comes
from installed candidate code; do not spoof registration or bootstrap arbitrary
source into a normal worker to bypass compatibility checks.

### Pilot limits and acceptance

The first pilot admits at most 25 new refresh job IDs and two inventory job IDs,
including retries in each cumulative budget, within a fixed 1,800-second
admission window. The window is not a completion deadline: drain and artifact
readback may finish later. Controller restart, cancellation, failure and retry do
not reset these counters. Keep the existing 25-candidate/100-record budgets,
30-second cadence, 3,600-second job timeout and 86,400-second cycle spacing.

Stop new pilot admission on ordinary backlog, configuration mismatch, artifact
failure, uncertain accounting or unexpected outstanding-job growth. An ordinary
job waiting 300 seconds is a retained pilot failure, not a promise that running
maintenance can finish in that interval. A cleared queue does not automatically
resume a paused pilot. End-of-window or exhausted-budget state retains unfinished
receipts and discovery checkpoints. Never label a stopped partial cycle complete.

Acceptance uses actual existing batch workers and queue, actual production
identity/mounts, sanitized live job trees and direct generated-artifact readback.
Verify expected schemas, source lineage and query results, remaining receipts,
held-out-project noninterference, capacity counters, pause/drain/restart recovery,
ordinary waiting time and owned-resource cleanup. A private-queue canary alone
cannot satisfy this shared-queue pilot. Success does not certify whole-fleet
capacity or authorize general enablement.

Pilot participant deployment follows the
[scoped batch deployment contract](query-catalog-pilot-deployment-contract.md).
Its opt-in canonical target and candidate-only source closure do not authorize
unrelated rollout or changes to default deployment behavior.

### Pilot observation and controller loss

The operator controller observes raw ordinary-job waiting state and pilot job,
budget and artifact outcomes throughout admission, pause and drain, until every
admitted job is terminal and readback is complete. Its observation interval is
10 seconds, with a 60-second owned observation lease. Renew only after a
successful observation; a separate blind heartbeat is insufficient. Admission
requires a current observation and matching owner token/generation. Expired or
lost ownership cannot be revived by the stale controller. Loss latches pilot
admission paused on the next attempted admission; admitted work still drains.
An unavailable observer is not proof of healthy queue delay or successful pilot
completion. Recovery obtains fresh explicit operator ownership, reconciles prior
jobs/counters, and retains observation gaps and failures. Original window and
budgets remain fixed; no automatic restart/resume or deadline extension.

A recorded ordinary-wait, artifact, scope or accounting failure cannot become a
passed pilot merely because observation resumes or the queue later clears.
Explicit operator resume is a trusted control operation, not an automatic loop;
it may resume an otherwise valid pause within the original window but cannot
resurrect terminal/retired job IDs or reset failure evidence.
