# Run catalog PostgreSQL projection specification

Status: forest read cutover completed, 2026-10-01 UTC; observation pending.
The operator authorized execution through gated cutover on **forest**, with later
**forest1 → wepp1** rollout. Independent contract reviews passed and accepted
checkpoint `db8e6be126fb231f16dd5e76f322d2b03089c10c` precedes runtime edits.
This document is not deployment evidence.

Execution: [work package](../work-packages/20260930_run_catalog_projection/package.md)
and [ExecPlan](../work-packages/20260930_run_catalog_projection/prompts/active/run_catalog_projection_execplan.md).
Rationale and initial operating limits:
[ADR-0078](../adrs/ADR-0078-run-catalog-projection.md).

## 1. Purpose and scope

The authenticated runs page must load without inspecting each project's
directory, Ron object, READONLY marker, or TTL file. The
[wepp1 investigation](../investigations/2026-09-30-user-runs-performance.md)
measured 169.56 seconds for 805 records: 0.85 seconds in PostgreSQL, 60.49
seconds resolving directories, and 108.20 seconds loading metadata. The
browser requests all Ron metadata, defeating the 200-run shortcut; that
shortcut still reads paths and TTL.

Scope includes `/runs/catalog`, `/runs/map-data`, and existing JSON variants of
`/runs`. Preserve the HTML shell and authentication. Cover web, rq-engine,
applicable RQ workers, maintenance, imports, forks, sync, relocation, READONLY,
and TTL producers. This is faithful extraction of current catalog values,
with the explicitly specified eventual-consistency and stale-state UI changes.

Non-goals: move scientific NoDb state into SQL; rewrite ownership/ACLs; change
TTL calculations or physical deletion authority; require PostgreSQL for
standalone WEPPpy; add a broker, service, database, PostGIS, filesystem watcher,
generic event bus, or durable outbox; repair NFS; change statistics-ledger work;
deploy to wepp2/wepp3 or Kubernetes.

## 2. Authority and portable projects

Project files remain authoritative for name, scenario, map, READONLY, and TTL.
PostgreSQL `run`, `user`, and `runs_users` remain authoritative for deployment
registration and access relationships. `run_catalog` is a rebuildable read
projection, not a second writable project model.

A project MUST remain usable outside a deployment with no PostgreSQL
installation, credentials, connection, or registration. Disabled integration
MUST NOT import Flask, SQLAlchemy, drivers, or WEPPcloud configuration. This
does not change unrelated existing Redis locking requirements. No deployment
connection, row ID, callback, or catalog state is serialized into a project.
No new project-side manifest is required.

Mutations continue through authorized file writers. SQL catalog edits MUST NOT
propagate back to files. Projected readonly/TTL values never authorize mutation
or physical deletion. Reconciliation considers registered rows only and cannot
infer ownership or registration from directory names or notifications.

Precedent: `NoDbBase.dump` already calls
`wepppy.weppcloud.db_api.update_last_modified` after file persistence. That
adapter imports the web app/model and creates an engine per session. Replace
this coupling through the interface below; do not expand it. The existing
[NoDb contract](nodb-persistence-concurrency-contract.md) already classifies
post-write mirrors as best-effort, without undoing a committed file save.

## 3. Database schema

Add exactly one table, `run_catalog`, one-to-one with `run.id`. Do not amend
`run` with catalog columns or duplicate run ID, config, owner/email, existing
timestamps, or access relationships. Join existing tables for those values.
A separate table isolates rebuildable file metadata from deployment-owned
registration and supports additive rollback. All new timestamps use UTC
`timestamptz`; current `run` timestamp types are unchanged.

### 3.1 Columns

| Column | PostgreSQL type / default | Meaning |
| --- | --- | --- |
| `run_id` | integer PRIMARY KEY REFERENCES `run(id)` ON DELETE CASCADE | Existing registration identity |
| `projection_id` | uuid NOT NULL, supplied on insert | New UUID per row incarnation; fences obsolete refresh |
| `name`, `scenario` | text NULL | Ron values; empty string is distinct from unknown |
| `readonly` | boolean NULL | Last successful marker observation; null means unknown |
| `map_lng`, `map_lat`, `map_zoom` | double precision NULL | Existing center `[longitude, latitude]` and zoom |
| `ron_state` | text NOT NULL DEFAULT 'pending' | `pending`, `ready`, `missing`, `invalid`, `unreadable` |
| `readonly_state` | text NOT NULL DEFAULT 'pending' | `pending`, `ready`, `unreadable` |
| `ttl_state` | text NOT NULL DEFAULT 'pending' | `pending`, `ready`, `missing`, `invalid`, `unreadable` |
| `ttl_policy` | text NULL | Normalized observed policy; unknown is not active |
| `ttl_deletion_at` | timestamptz NULL | Valid active expiration under catalog display rules |
| `source_locator` | text NULL | Internal canonical deployed location observed by refresh |
| `source_versions` | jsonb NOT NULL DEFAULT '{}' | Per-source coherent-read observations, not NoDb objects |
| `projection_version` | integer NOT NULL DEFAULT 1 | Extractor interpretation version |
| `dirty_revision` | bigint NOT NULL DEFAULT 1 | Invalidation generation |
| `indexed_revision` | bigint NOT NULL DEFAULT 0 | Last completely observed generation |
| `dirty_since` | timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP | Start of current dirty episode |
| `invalidated_at` | timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP | Latest notification |
| `last_attempt_at` | timestamptz NULL | Latest extraction attempt |
| `ron_observed_at`, `readonly_observed_at`, `ttl_observed_at` | timestamptz NULL | Successful per-source observations |
| `refreshed_at` | timestamptz NULL | Last complete publication without transient read failure |
| `reconciled_at` | timestamptz NULL | Last complete full-source observation |
| `next_attempt_at` | timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP | Dirty refresh eligibility / retry delay |
| `next_reconcile_at` | timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP | Full-source reconciliation eligibility |
| `last_error_code` | text NULL | Bounded internal classification, never raw traceback |

`dirty_since` matters only while revisions differ. A complete observation can
establish missing/invalid state; refreshed/reconciled timestamps do not imply
a healthy project. Transient unreadability does not advance affected source
observation times or aggregate refreshed/reconciled timestamps.

CHECK constraints enforce state vocabularies, nonnegative indexed revision,
`dirty_revision >= indexed_revision`, positive projection version, and JSONB
object shape. UUIDs come from Python's standard library; no extension is needed.
Longitude and latitude are both null or both finite; zoom is independently
null or finite. Preserve wrapped longitudes and existing zoom conventions;
do not introduce new coordinate cutoffs. Reconstruct the existing `map_center`
pair or null in JSON. Unsupported map data yields null map fields and an
operator diagnostic, not omission of an otherwise valid list row.

Enforce the null-safe constraint `ttl_deletion_at IS NULL OR
((ttl_policy = 'rolling_90d' AND ttl_state = 'ready') IS TRUE)`.
The `IS TRUE` is required: PostgreSQL CHECK accepts SQL NULL, which must not
permit a non-null expiration with a null policy. TTL `ready` means a readable mapping normalized
successfully, not necessarily an active expiration. Disabled, excluded,
unknown-policy, or invalid-expiration states have null expiration.

Constraint validation must cover null expiration with every admitted state/
policy (accepted), non-null expiration with ready/rolling policy (accepted),
and non-null expiration with null/unknown/non-rolling policy or any non-ready
state (rejected). On transient TTL failure clear the stored expiration; it is
explicitly exempt from last-good value retention. Preserve its prior successful
observation time and retain policy only as diagnostic history until reread.

### 3.2 Indexes, migration, and rebuild

Create a partial index on `(next_attempt_at, dirty_since, run_id)` where
`dirty_revision > indexed_revision`, and an index on
`(next_reconcile_at, run_id)`. The primary key handles joins. Add no speculative
search/spatial/sort indexes. Preserve existing response sort semantics,
including Python casefold where database collation would differ.

The Alembic migration is additive and schema-only: no NFS reads/backfill in
the migration. Supply a development downgrade, but never drop the table for
operational rollback. Existing `owner_id` representation is unchanged.

Backfill inserts missing rows by database pagination, not directory discovery.
Existing rows are not reset. Rebuild invalidates rows/version in bounded
batches without deleting registrations. If a projection row is replaced,
its UUID changes; refresh publication compares that UUID so old work cannot
overwrite the new incarnation.

## 4. Portable notification interface

Add `wepppy/nodb/persistence_events.py` with a frozen primitive-only
`ProjectCommit` record, observer registration, and
`notify_project_commit(event)`. Record fields: `runid`, `wd`, source kind
(`nodb`, `readonly`, `ttl`, `lifecycle`), optional `controller_filename`, and
UTC `committed_at`. Paths are provenance, not arbitrary access authority.
Records and observers are ephemeral and never jsonpickle-persisted.

No observer means no imports or I/O. The explicitly installed deployment
observer performs bounded SQL only: no project reads, NoDb hydration, or job
enqueue per notification. Reuse a process-local, fork-safe engine/pool;
initialize after worker fork or dispose inherited connections. Do not create
an engine per save. This is one integration boundary, not an event framework.

Replace the direct database import in `NoDbBase.dump` through this interface.
All committed NoDb dumps retain the last-modified mirror; only Ron dumps dirty
the catalog. READONLY/TTL events dirty the catalog without adding new
last-modified semantics. Preserve the Redis last-modified mirror. SQL uses the
maximum committed timestamp, not delivery time, so delayed notifications cannot
regress time. Existing timestamp representation is not migrated. Catalog
reconciliation does not crawl unrelated NoDb files or claim to repair every
historically missed modification timestamp.

Emit only after authoritative commit, including correct classification of
ancillary failures after `os.replace`. Test that committed bytes still trigger
the mirror attempt, and failed replacements never do. Enabled but invalid
configuration/missing adapter is a startup/preflight failure. Transient database
outage after startup is an observable mirror failure, never rollback of a
successful file save. The deliberate boundary logs context and increments
failure telemetry; no silent broad catch or retries while holding NoDb locks.

Explicitly initialize the adapter in Flask, rq-engine, worker process startup,
scheduler jobs, and deployed maintenance entry points. Maintenance exposes
deployment/standalone mode without importing the web app. Flask-only coverage
does not constitute wired completion.

## 5. Producer and lifecycle matrix

| Boundary | Obligation |
| --- | --- |
| Ron persistence: name/scenario/map | Notify after committed dump; no SQL in setters |
| Other NoDb dumps | Last-modified mirror only |
| `NoDbBase.readonly` and direct marker writers | Notify after marker create/remove; audit bypass writers |
| `run_ttl._write_payload` and removal/replacement paths | Notify once after committed replacement/removal |
| `WeppCloudUserDatastore.create_run` and equivalent registrations | Pending catalog row in registration transaction; preserve ACL workflow |
| Anonymous/unregistered projects | No implicit registration; attachment supplies initial metadata |
| Creation/fork/archive/restore finalizers | Invalidate after completed intended file publication |
| `run_sync_rq` / migration completion | Invalidate after successful transfer/normalization; provenance is not ACL registration |
| Relocation/root migration | Invalidate; discard old locator hint and re-resolve |
| Sharing/owner/user changes | Current authoritative joins, no ACL/email copy |
| Registration deletion / TTL GC | Cascade; preserve existing file-deletion order |
| Offline edits / older binaries / manual copies | Reconciliation, not claimed notification coverage |

Maintain an exact writer/process/test/live-evidence inventory in the package.
Search direct writes, not just setters. Grouped and legacy identity resolution
must preserve the current mapping; a child notification cannot register or
invalidate an unrelated parent. Catalog readiness means availability of the
required metadata, not successful completion of a fork/create/model job.
Finalizer notifications accelerate another observation but are never the
authority for readiness. Missing projections for existing
registrations may be seeded; missing registrations are never synthesized.

Registration before enqueue starts with pending/unobserved metadata. If the
first extraction finds missing Ron, classify it missing/unavailable as the
existing reader would; if readable Ron and a known READONLY state appear during
publication, the row can become visible before job completion. No row promises
that the model/job succeeded. Successful finalization requests a fresh snapshot.
If that notification is lost, reconciliation reaches the same result from
current files. Failed/abandoned creation can remain missing/unavailable or have
visible usable metadata, independently of the job's failed status. Restart and
backfill use these same rules, with no hidden finalizer latch or completion
marker. Preserve existing job-status/error surfaces for lifecycle progress.
Test registration-before-enqueue, absent/partial sources, successful and failed
publication, lost final notification, abandonment, and restart/backfill.

## 6. Synchronization protocol

### 6.1 Invalidation

In a short transaction, resolve the validated event identity to an existing
registered run; upsert a missing projection only for that registration.
Atomically increment dirty revision, preserve `dirty_since` during an already
dirty episode, set it on clean-to-dirty transition, and make refresh immediately
eligible. Duplicate notifications may cause extra work but cannot apply stale
values. FK/registration deletion fences resurrection.

Initially one dirty generation covers all three source families. Refresh the
whole small snapshot; do not add per-source queues without measured capacity
evidence that this bounded approach misses acceptance.

### 6.2 Refresh serialization and publication

Every scheduled, manual, and backfill refresh takes a nonblocking PostgreSQL
transaction-scoped advisory lock using the two-integer namespace `1381322307`
(`RUNC`) and `run.id`. Busy work is skipped. Notification writers never acquire
this lock. Existing OSM locks use PostgreSQL's separate single-bigint key space;
audit other lock users when implementing.

Use READ COMMITTED isolation. After locking, capture projection UUID and dirty
revision without a row lock. Resolve current source location using deployed
path rules; stored location is only a hint. Read sources without NoDb write
locks. No row lock is held during NFS reads, so notifications/deletion proceed.

Verify detected source versions and resolver identity before updating the same
`(run_id, projection_id)` in that SQL transaction. Publish the snapshot and
acknowledge at most the captured dirty revision. Never overwrite the current
dirty revision. A concurrent invalidation leaves the row dirty and immediately
eligible. Deleted registration or replaced UUID discards the result. A failed
database transaction discards the snapshot; never reconnect and publish old
work without starting the protocol again.

The advisory transaction holds one connection across NFS reads. Use a small
refresh pool separate from request capacity and report transaction/job age.
Bounded concurrency avoids a new lease table/service. Hard NFS waits are not
bounded by Python timeouts; operational job/transaction limits are not a promise
of hard cancellation. Once the transaction is aborted it cannot publish.
The two-reader physical bound assumes intact coordination; lost coordinator
connections cannot cancel kernel-blocked reads. Check coordination again after
final source verification and discard work on detected loss without reconnecting
to publish it. This check is not atomic with a separate per-run commit; the
per-run advisory transaction, revision, incarnation and source-version fences
remain authoritative. Do not claim an additional atomic coordinator-loss fence.

### 6.3 Non-mutating extraction

Implement a dedicated extractor, not `Ron.load_detached`, `ensure_version`,
Redis caches, controller constructors, property setters, or TTL initialization.
Read coherent Ron/TTL descriptor snapshots and READONLY presence without
modifying files. Reuse existing coherent-read helpers where compatible.

Parse JSON as data without executing jsonpickle reconstruction hooks. Support
explicit current and legacy Ron field/map encodings, including tuple wrappers.
Preserve supported Ron missing-field defaults. Unknown encodings are reported,
not guessed. Real current/legacy sample parity is a cutover gate. TTL must use
the same pure normalization and expiration checks as the catalog, including
missing-policy normalization in `read_ttl_state`; do not accidentally validate
a different raw schema. Do not recompute expiration or modify policy.

`source_versions` has objects for `ron`, `readonly`, and `ttl`: state, SHA-256
of bytes actually read, device/inode, size, nanosecond mtime, and observation
timestamp as applicable. Absence is explicit. Do not store raw payloads or
secrets; absolute location belongs only in `source_locator`. These tokens are
observations, not globally ordered project revisions. Never skip due
reconciliation merely because mtime/size match.

Detected replacement/drift discards the affected observation and schedules
retry. Preserve existing atomic-producer/coherent-read assumptions; arbitrary
in-place change-and-restore cannot be made atomic by a reader. Independent
Ron/TTL/marker files are eventually consistent, not one cross-file transaction.

### 6.4 Scheduling and durable progress

Add one bounded sweep job using the existing scheduler and batch queue, not a
job per save. Initial cadence is 15 seconds; a dispatch attempts at most 50
rows, at most two concurrent refreshes, and stops submitting new work after
45 seconds. Only one dispatcher submits a sweep at a time per deployment;
source-reading commands share a global nonblocking sweep key `(1381322308, 0)`
in a separate namespace from per-run keys. Manual single-run refresh participates
in the global concurrency limit. Hold the sweep coordination transaction on
a dedicated connection, and use separate per-run connections for extraction.
Database-only status/seed/preflight operations do not take the sweep lock.

Use the scheduler's existing per-task overrides: `initial_delay_seconds: 0`
and `jitter_seconds: 0` for this task only. Preserve every other task's behavior.
The current scheduler loop also sleeps 30 seconds; zero startup delay/jitter
alone cannot achieve a 15-second cadence. While this task is enabled, bound
sleep by its next due time as well as the configured ordinary sleep interval.
Do not change other tasks' intervals, initial delays, jitter, or failure-retry
semantics. Test real dispatch timestamps and disable/re-enable behavior, not
only configuration parsing, before claiming the cadence target.
`wepppy/tools/scheduler.py` currently enqueues each due invocation; a fixed job
ID alone is not proof of deduplication. Add opt-in coalescing for this task:
atomically admit at most one queued/started sweep per deployment identity using
existing Redis/RQ primitives, permit the next sweep after terminal completion,
and recover failed/abandoned jobs through actual RQ state. Admission failure
leaves SQL dirty state intact. Test simultaneous scheduler processes, restart,
enqueue failure, and abandoned recovery; never accumulate one redundant queued
job every 15 seconds while a model occupies the worker. Database sweep locks
still guard manual and multi-scheduler execution. Queue wait counts toward the
60-second objective; capacity failure blocks promotion, not a silent new queue.

Reserve at least one quarter of attempts for due reconciliation; unused slots
can serve the other class. Dirty rows use next-attempt and oldest-dirty order.
Deduplicate row IDs between the two candidate lists within a dispatch. A full
dirty-row extraction also satisfies reconciliation for that row.
Transient failures retain work and retry no sooner than 60 seconds unless a
new commit invalidates the source. There is no inline retry loop.

Reconciliation orders registered rows by `next_reconcile_at`, then run ID.
Complete observations set `reconciled_at` and next due time 12 hours later;
transient failure reschedules after 60 seconds without claiming success.
Per-row timestamps are durable progress, so no cursor table is required.
Seed missing projection rows in bounded ascending-ID anti-join batches; restart
does not depend on an in-memory cursor. Record failures so repeatedly unreadable
rows cannot silently starve the rest of the sweep.

Reconciliation includes apparently clean rows and repairs lost notifications,
database downtime, offline edits, and older producers. Creation/attachment
requests immediate first refresh; completed fork/sync invalidates independently
of intermediate writes. Shared-host producers are not assumed upgraded.

There is an unavoidable crash gap between file commit and invalidation. This
is neither an atomic NFS/PostgreSQL transaction nor a transactional outbox.
Reconciliation supplies bounded repair under healthy storage/database operation.
If measured capacity fails acceptance, block promotion and document evidence
before adding infrastructure or durable project-side notification state.

### 6.5 Source identity, containment, and pure resolution

Bind every observation to an existing registration, its validated canonical
run identifier, and a location derived from trusted deployment root/group
configuration. Neither `ProjectCommit.wd`, Redis path-cache values, stored
`source_locator`, nor a path embedded in Ron can change that binding. The
notification adapter performs only lexical identifier/location consistency
checks using those configured mappings; it does no filesystem resolution on
the save path. Inconsistent event pairs are rejected as catalog hints with a
bounded diagnostic. Existing parent-run last-modified mirroring for grouped
controllers is a separate explicitly mapped action; it cannot redirect a child
catalog observation into its parent or synthesize child registration.

Extraction and pre-publication identity checks require a **side-effect-free
resolver**, separate from repair behavior in `helpers.get_wd`. Preserve primary,
legacy, grouped, and operator-configured root mappings, but do not invoke
`_ensure_omni_shared_inputs`, create/delete/repair links, stamp files, or use
request context overrides. Existing ordinary workflow repair remains unchanged.
Resolve/check the expected project boundary before opening fixed source names
`ron.nodb`, `READONLY`, and `TTL`. A source JSON field never supplies filenames.

Operator-configured storage-root aliases may resolve to their configured
canonical target. Below that boundary, project-controlled links cannot redirect
the registered project root, its ancestors, or a catalog source into another
project or outside its approved source boundary. A source link wholly inside
the same verified project boundary is allowed, with the current absent-marker
semantics preserved for genuinely missing targets. Established explicit grouped
mapping, not an arbitrary symlink, defines a child's boundary. Shared-input
links such as climate/watershed/DEM remain valid and untouched; they are not
catalog sources. A previously supported deployment alias requiring a different
source binding must be represented in trusted configuration and covered by
legacy parity tests before cutover, not silently rejected or trusted on sight.

Containment must be bound to the actual opened descriptor/directory chain;
`realpath`/`exists` followed by an unchecked `open` is insufficient. Use a
descriptor-relative constrained traversal/open, or equivalent verified-open
primitive, and verify descriptor identity through publication checks. Changed
ancestors, cross-project redirects, and mismatched source bindings discard the
observation with an explicit internal `source_scope_mismatch`/drift diagnostic.
They never publish another project's metadata and never repair its files.
Existing coherent-read helpers may be reused only behind that containment seam;
their current ordinary `open` is not itself a containment guarantee.

Real-file tests must cover cross-project leaf and ancestor links, event/path
mismatch, path replacement races, valid legacy/grouped roots, within-project
links, and standalone operation. Compare the entire directory/link inventory
before and after extraction and `compare`, including missing/dangling shared
links; checking only the three source file hashes cannot prove a read is pure.

## 7. Public reads and compatibility

### 7.1 Query contract

In `postgres` mode all three list/map JSON surfaces use explicit database
columns and current access/owner joins. Never call `Run.wd`, `get_wd`, Ron,
TTL readers, project filesystem probes, or request-time repair/enqueue. This
includes admin aliases/all-runs scopes; loading templates is not project I/O.

Preserve authentication, Admin/Root alias behavior, sharing/ownership filtering,
CSRF, sort aliases/direction, null placement, JSON keys, dates, and URLs.
`include_ron_meta` remains accepted but cannot select filesystem access. Actual
names/scenarios are returned at all scope sizes; the old threshold substitution
is not used in database mode. Batched owner lookup remains batched.

Retain current JSON pagination accounting: DB-sort variants paginate registered
rows before omissions; metadata-sort variants paginate visible sorted metadata.
The catalog remains full-scope with browser filtering/pagination. Server-side
search/pagination redesign is out of scope. Map-data preserves its fields and
last-modified/id ordering; absent optional map data never removes a list row.

### 7.2 State matrix

| Source state | Public behavior | Refresh behavior |
| --- | --- | --- |
| New/pending, never indexed | Omit unfinished row; scoped updating count | Immediate extraction |
| Valid empty strings | Include empty strings | Normal acknowledgment |
| Supported current/legacy populated Ron | Equivalent fields | Non-mutating extraction |
| Confirmed missing/invalid Ron | Omit as before; scoped unavailable count | Reconcile later |
| READONLY absent, successful observation | `readonly=false` | Ready observation |
| READONLY never known | Omit unfinished row; never guess false | Retry |
| Transient Ron/marker error with usable prior snapshot | Last-good row with stale indicator | Retain values, retry |
| Transient error without usable snapshot | Omit; unavailable summary | Retry |
| TTL missing/invalid/unreadable/disabled/excluded | Include run with null deletion date | Retry unreadable; reconcile other states |
| Dirty, previously usable snapshot | Last-good row with stale indicator | Read current source |
| Required observation older than 24 hours | Stale; suppress TTL date | Reconcile and report breach |
| Registration deleted | Absent | Cascade; discard obsolete refresh |

Confirmed Ron absence/invalidity must not be overridden by retained old fields.
An I/O error is not proof of deletion. Successful READONLY absence is distinct
from failed stat/permission checks. On partial failure, publish successful
source observations and failed source states, retain last-good failed-source
values **except clear `ttl_deletion_at` on TTL failure**, but do not acknowledge
the dirty revision. Keep last completed `source_versions` observations for
failed sources; failure state/error metadata records the unsuccessful attempt.
For Ron, a retained usable snapshot requires a last completed source token in
`ready` state. Confirmed missing/invalid observations replace that token and
clear the obsolete display values, so a later I/O error cannot revive a row
already confirmed absent/invalid. Required Ron and READONLY observations, not
aggregate `indexed_revision > 0`, determine initial visibility: an initial
successful Ron/READONLY read with unreadable optional TTL is a visible stale
row with null expiration, not an indefinitely hidden new project.

For ready(active TTL) → unreadable → ready, publish any simultaneous successful
Ron change, clear expiry during failure, keep the TTL observation timestamp
unchanged, leave the row dirty, then restore only the newly read expiry/time
after recovery. Require this transition as a real SQL constraint/state test.
A clean reconciliation that
finds transient failure makes the row dirty before returning. Invalid/missing
sources are terminal observations and can acknowledge the generation; they
remain eligible for future reconciliation.

Add per-row `catalog_state` (`current` or `stale`) and `catalog_updated_at`
(UTC string or null). Add top-level `catalog_status` with authorized-scope
integer counts `pending`, `stale`, `unavailable`, and `mode`. Use disjoint
count precedence: never-attempted/pending; confirmed invalid/missing or no
usable failed snapshot/unavailable; visible last-good/stale; otherwise current.
Counts in paginated JSON cover its whole authorized scope, not just its page.
Expose no locators, error details, hashes, or new identities. Existing payload
fields are retained; older consumers can ignore these additive fields.

UI adds an accessible updating/stale summary and stale-row indicator. Healthy
empty catalogs remain ordinary empty results. TTL dates are emitted only when
the row is clean, TTL is ready, and its observation is <=24 hours old; otherwise
use the existing Last Modified presentation. The UI explains metadata may be
updating, without implying expiry or readonly values authorize actions.
Missed notifications can remain invisible until reconciliation, so immediate
read-after-write is not promised. Refreshing a page does not enqueue repair.

In `postgres` mode database failure returns the canonical explicit catalog
error; there is no automatic NFS fallback. `legacy` mode is an operator-selected
rollback, not a hidden request-time recovery branch.

## 8. Configuration and measurable limits

Separate persistence integration, projection maintenance, and read selection:

- `WEPPPY_PROJECT_COMMIT_MODE=disabled|postgres`; library default `disabled`.
  Deployed producers explicitly choose `postgres`.
- `WEPPCLOUD_RUN_CATALOG_WRITE_MODE=timestamp_only|catalog`; deployment staging
  default `timestamp_only`. The adapter preserves the existing modification
  mirror before the additive schema exists; `catalog` requires the migration.
- `WEPPCLOUD_RUN_CATALOG_READ_MODE=legacy|postgres`; staging default `legacy`.
- Explicit scheduler task enablement; a read flag never silently starts work.

Separate static startup validation from live promotion readiness. Startup
rejects unknown modes, missing required adapter/secret configuration, and
incompatible selections such as database reads with timestamp-only writes.
Do not require a currently running sweep, recent successful reconciliation,
or a successful live database connection to construct/start a correctly
configured process: canonical deployment recreates workers and scheduler, and
outage recovery must be able to restart them. Missing schema or database
unavailability is an explicit readiness failure and database-mode request error,
not permission to run a legacy reader or lose post-commit failure telemetry.

The operator preflight rejects read promotion until migration, catalog writes,
producer initialization, a healthy sweep, and coverage/freshness checks pass.
The CLI reports `technical_ready` for its automated SQL/RQ observations, never
unqualified promotion readiness. It always reports
`gate_status=operator_evidence_required` and the remaining operator witnesses.
A zero CLI exit is not activation, cutover, or promotion authorization: the
completed, retained stage-specific run sheet in section 11.1 is mandatory.
This separates machine observations from operator evidence without adding an
evidence-ingestion protocol or weakening any release obligation.
After cutover, loss of those dynamic signals marks readiness unhealthy and
reports the specified stale/error states; it does not introduce a startup loop
or silently change read mode. Test full-stack restart with the scheduler absent
initially, database outage at restart, and recovery without editing modes.
Shadow operation means catalog writes/sweeps plus legacy reads and explicit
operator comparisons, not double-scanning every request.

Adapter limits start at connection timeout 1 second, pool wait 250 ms, SQL lock
timeout 250 ms, statement timeout 1 second, and zero inline retries. Validate
combined latency: statement timeout does not bound connection establishment.
Dispose failed sessions. Refresh uses a separate pool sized for its two readers
and coordinator. Schema-install mode avoids startup deadlock before migration.

Promotion targets under healthy infrastructure:

- Notified commits appear within 60 seconds; no immediate read-after-write
  guarantee. Measure actual producer→browser delays.
- Every registration is revisited within 24 hours, even under sustained dirty
  traffic. Twelve-hour due scheduling leaves headroom, not a guarantee against
  unreadable storage. Missed updates repair within 24 hours after restoration.
- Catalog and map-data for the representative 805-run scope: p95 <=1 second,
  p99 <=2.5 seconds over >=100 sequential authenticated requests, plus a recorded
  concurrent-reader check. Record browser readiness, server/TTFB, payload size,
  and process-cache conditions separately.
  Forest uses its actual single-account project scope with controlled requests;
  absence of 805 projects does not block forest cutover or promotion. Retain
  isolated scale evidence separately and validate representative host scale on
  the first stage with that dataset, on wepp1 in shadow before read cutover if
  unavailable earlier. Do not assume forest1 has the production dataset.
- Zero project filesystem calls on database read paths; zero unauthorized data
  exposure and zero project changes by extraction.
- Healthy notification overhead: added p95 <=50 ms on interactive mutations;
  retain baseline and unavailable-database worst-case measurements.

Use producer-specific, matched performance baselines. NoDb saves already pay
for a synchronous timestamp-mirror commit; compare timestamp-only versus catalog
mode and also characterize the legacy helper versus its replacement. TTL and
READONLY previously had no SQL mirror: their baseline must not invent one.
Measure complete mutations and observer time, counterbalance/interleave mode
order, retain raw samples, and label paired-delta p95 separately from differences
between mode p95s. Include commit/locking cost; no durability relaxation or
threshold waiver follows from sharing the existing NoDb transaction.

These are acceptance limits, not achieved claims. Cadence, concurrency, stale
window, and retry choices are recorded in ADR-0078. Adjustments require capacity
evidence and ADR/spec updates before promotion, not silent changes.

## 9. Operator interface and observability

Implement `python -m wepppy.weppcloud.run_catalog` in the deployed container:
`status`, `seed`, `refresh`, `reconcile`, `compare`, and `preflight`. This is a
future interface, not an existing command. All support `--json`; mutations
default to dry-run and require `--apply`, with `--limit` and existing database
`--run-id` where applicable. Reject arbitrary roots/paths. Scheduled work calls
the same bounded implementation explicitly in apply mode.

`status` reports registered/projected/ready/pending/dirty/unavailable counts,
oldest dirty/reconciliation age, attempts/failures, and source/SQL latency.
`preflight` checks modes/schema, producer initialization, sweep health and age,
coverage, and unresolved transient failures. It fails readiness for breached
limits; RQ SUCCESS alone does not prove reconciliation. `compare` performs
bounded authorized-scope semantic comparison against the non-mutating extractor.
Legacy reader characterization runs on controlled fixtures/copies because
the old reader can stamp version files.

Record notification failure counters/logs by deployment, process, run, source,
time, and bounded code, never raw credentials or full source JSON. Distinguish
expected missing/invalid source from I/O/permission failures. Internal metrics
can expose aggregate deployment counts; public counts are authorization-scoped.
Use existing operator tooling, not new public maintenance endpoints.

Catalog rows are deployment artifacts rebuilt on import, not project archive
members. Run inputs/outputs retain existing browse/download/archive observability.
Retain redacted source→SQL→JSON comparison evidence in the work package. Secrets
follow current file conventions; a companion worker must use its job-origin
database, not a database chosen from its physical hostname.

### 9.1 Public RQ disclosure boundary

Catalog sweeps use a trusted fixed callable and server-minted opaque job IDs
of exact form `run_catalog_sweep_<canonical-hyphenated-UUID>`, using
`wepppy.rq.job_id.new_rq_job_id()` for the suffix. This is the catalog-only
exception to the shared RQ identifier generation rule. Enqueue, coalescing,
persistence, lookup, polling, and cancellation preserve the complete exact
string; unrelated identifiers are unchanged. IDs, job arguments, descriptions,
and public metadata contain no account/run identifiers, database DSNs, host
names, source paths, projection snapshots, or deployment-wide counts. Coalescing
may use a private deployment key; it must not embed that private identity into
the public job description or result.

Both single and batch job-info serializers, including recursive nodes and
fetch/import/abandonment failure paths for that reserved job namespace, expose
only normal job identity/status/timestamps, the constant description
`Run catalog maintenance`, `result=null`, and `exc_info=null`. Failures expose
only `error.code=run_catalog_maintenance_failed`, message `Run catalog maintenance
failed; consult operator diagnostics.`, and an opaque `error_id`. Do not depend
only on a cooperative task catch: import failure, worker death, and generic RQ
tracebacks also require this narrowly scoped serializer rule. The scheduler
sets the identifying metadata before enqueue; the reserved opaque ID enables
safe classification even when job deserialization fails.

Detailed per-run outcomes, SQL/source errors, and aggregate counts remain in
authenticated operator CLI/log evidence, correlated by job/error IDs. Public
jobstatus retains its existing successful status schema, but reserved-ID errors
in status fetch/deserialization/aggregation and outer polling handlers must use
the same bounded maintenance error without traceback or private details.
Classify the reserved ID before deserialization, not only inside job-info.
This bounded exception is
cross-linked in the RQ response contract; it changes no unrelated job's polling
authorization or traceback behavior. Verify success, expected/unexpected SQL
and filesystem failure, import failure, and abandonment through single/batch
job-info and jobstatus (including outer error responses) as an anonymous or
unrelated caller. Test exact-string generation/enqueue/fetch/cancellation and
classification before deserialization. Job success still means an
attempt completed, not that every projection is current.

## 10. Implementation sequence

### M0 — Contract checkpoint and fixtures

Record base revision, approved architecture, detailed changes, NoDb/TTL/RQ/auth
contracts, ADR, and compatibility matrix. Obtain two independent read-only
contract reviews and disposition findings, including correctness and security
artifacts. Commit the contract set as a standalone ancestor before runtime
edits, only when committing is authorized. Architecture endorsement is not
evidence of completed detailed review. Collect absent/empty/current/legacy/
malformed/grouped/TTL/READONLY fixtures and inventory direct writers.

### M1 — Additive schema and extractor

Implement migration, separate mapping/repository, non-mutating extractor,
seed/status/compare CLI, and real SQL/file tests. Prove constraints, cascade/
UUID fencing, repeatable seeding, legacy value parity, and unchanged source
bytes/version/markers. Do not change request reads or save behavior yet.

### M2 — Portable observer and producers

Replace the old timestamp dependency with the explicit adapter; wire every
producer and process initialization. Prove standalone usage with web/database
modules unavailable, outages after file commit, bounded failures, fork-safe
pools, and no implicit registration. Complete the writer coverage inventory.

### M3 — Refresh and reconciliation

Implement concurrency protocol, durable per-row progress, bounded existing-queue
scheduling, metrics, and preflight. Test reversed/duplicate/lost notifications,
concurrent commits, partial reads, deletion/rebuild races, source drift, and
sustained reconciliation. Update the RQ graph/catalog and inspect live job
trees. Measure capacity before increasing concurrency or infrastructure.

### M4 — SQL readers and freshness UI

Wire all three read surfaces behind explicit mode selection, plus scoped
freshness UI. Preserve authorization, sorting, pagination, map and TTL/date
formatting. Make filesystem helpers fail in database-mode tests. Exercise real
HTTP/browser behavior and real SQL/file boundaries, not mock-only substitutes.

### M5 — Rollout and retirement

Execute section 11 in order. Legacy reads remain during rollout for explicit
rollback. After wepp1 acceptance and seven further healthy days, retire legacy
request-time metadata/threshold code in a separately reviewed cleanup with
rollback implications recorded. Package closure requires that disposition;
retaining it longer needs an explicit owner/date, not an indefinite fallback.
Notifications, reconciliation, and diagnostics are permanent mechanisms.

## 11. Rollout: forest → forest1 → wepp1

### 11.1 Common procedure and promotion gate

Record target hostname, git/image revision, installed `wctl` preset, effective
Compose topology, database identity without secrets, writers, run roots,
UID/GID/groups/umask, and shared storage/queue boundaries. Host-order rollout
does not authorize changes to unrelated companion stacks.

Deploy additive code with legacy reads and timestamp-only writes. Run schema
migration using the existing Flask-Migrate entry point inside the candidate
app container (`wctl exec -T weppcloud flask db upgrade` through its preset),
then enable catalog writes/sweeps. Verify the container actually contains the
migration and record its Alembic head. If the target requires a different
candidate staging boundary, record the canonical command in its run sheet;
do not invent a parallel image/registry workflow. Startup must support this
schema-install phase without attempting catalog SQL prematurely.

Before enqueueing any new sweep callable, inventory **every worker eligible to
consume its existing queue**, including remote/companion workers. Each must
support that callable and its reserved-job disclosure contract, have the correct
job-origin database modes/secrets, and see the approved source mounts. An old
writer can be tolerated through reconciliation only if it cannot consume these
new jobs. An incompatible consumer blocks sweep activation and promotion;
resolve producer/consumer rollout scope explicitly. Do not silently deploy
additional hosts, remove their queue subscriptions, or introduce a new queue.
Retain mixed-version and wrong-database preflight rejection evidence.

URI hostname/port/database hashes are configuration hints and admission
namespaces, not database identity or compatibility proof. Before admission,
prove job-origin database access using fresh random signed-bigint advisory
nonces: hold an exclusive transaction-scoped lock on one nonce in the origin
database; each eligible consumer uses its actual adapter, credentials and
effective configuration on a separate connection to probe that nonce and a
fresh unheld control nonce with `pg_try_advisory_xact_lock(bigint)`. Require
held nonce → false and control nonce → true while the coordinator demonstrably
retains its lock. Errors, timeouts, lost coordinator, or unexpected results mean
HOLD. End all probe transactions explicitly; never leave session locks in pools.
Identically named databases in separate Compose networks must fail this test.
Record the consumer revision, effective configuration, runtime identity, mounts,
probe results, and mutation/readback witnesses. Restart, candidate/configuration/
mount changes, or eligible-consumer membership changes invalidate affected
witnesses; revalidate before resuming admission with existing drain/deploy tools.
Configuration agreement cannot waive this connection-bound proof; operator
evidence cannot waive a failed probe or other failed automated check.

Keep gates in order: consumer proof before sweep activation; producer witnesses,
coverage, semantic comparisons and omission disposition before read cutover;
latency, full reconciliation and at least 48 healthy hours before host promotion.
The final observation window is not a prerequisite for initial shadow activation.

Seed/backfill while reads remain legacy. Classify every registration; unresolved
transient read failures block cutover. Missing/invalid Ron needs an explained
omission manifest, not invented values. The observed 805 registered / 615
returned on wepp1 is an audit starting point, not a hard-coded count.

Compare source snapshots, SQL, actual authorized JSON, and browser list/map.
Require zero unexplained semantic/authorization differences and record permitted
freshness differences. Simulate faults only in isolated test runs; do not break
shared production DB/storage. Verify restart/resume and rollback/re-enable.

Switch only reads after readiness. Apply environment changes through the host's
canonical recreate/deployment mechanism; a restart alone need not update env.
Then prove zero project I/O, latency, every writer identity, and a full
reconciliation cycle. Retain >=48 healthy hours and a completed full cycle
at each stage before promotion. Restart the healthy observation window after
a source outage or freshness breach is repaired.

### 11.2 Forest — development integration

Use the installed development `wctl` preset and `docker/docker-compose.dev.yml`
per `docker/README.md`. Exercise NFS-backed projects, standalone mode, all
producer entry points, fault injection, and both browser views. Inventory the
forest1 companion worker if it consumes forest's queue: it writes for forest's
database. This is distinct from forest1 test-production acceptance.

Prove the complete writer→files→notification→SQL→JSON→browser chain, 24-hour
missed-update recovery, and no unacceptable model-job starvation. Hold legacy
reads if any adapter is uninitialized or source compatibility is unexplained.

### 11.3 Forest1 — production-compose rehearsal

Target the test-production web stack at `wc-prod.bearhive.duckdns.org`, not the
`forest1-batch` companion project. Use the installed production `wctl` preset
and `/workdir/wepppy/scripts/deploy-production.sh`. `docker/README.md` requires
the exact no-argument deploy twice for forest1 release evidence, with existing
CAPTCHA/login/session and real RQ/DEVAL artifact checks between runs. Preserve
those alongside catalog checks. Inspect `--print-plan` first; targeted web
deployment is not a substitute for this all-producer release.

Rehearse fresh schema, populated upgrade, interrupted backfill, rollback,
stale-state UI, and multiple writer processes on production image/mount/secret
configuration. Keep the same candidate revision's forest/forest1 evidence and
48-hour healthy window before wepp1 promotion.

### 11.4 Wepp1 — production activation

Use `/workdir/wepppy/scripts/deploy-production.sh` with installed preset and
existing active-job/deployment-fence gates. Record `wctl rq-info --detailed`
and `--print-plan`; do not bypass shared-worker gates. Reconfirm all writers
for the actual database, including other hosts. No automatic wepp2/wepp3
deployment is implied by this plan.

Enable shadow writes/sweeps, backfill, compare, then cut over after preflight.
Benchmark the operator-designated large account (user ID 11 during profiling),
empty/small/shared/admin scopes, and map-data. Preserve privacy in artifacts.
If old remote writers share the DB but cannot consume catalog sweeps, explicitly
measure their reconciliation-only recovery. Eligible sweep consumers must all
pass the compatibility gate in section 11.1. Do not claim 60-second notification coverage for old writers; if real
workflows require it, block promotion until producer rollout scope is resolved.

Mark deployed, environment-validated, and incident-resolved separately. The
original large-account browser workflow must meet latency and correctness
targets before the incident is resolved.

### 11.5 Rollback and stop conditions

Pause promotion for authorization mismatch, unexplained omission/value drift,
project changes by extraction, lost saves, freshness breaches, excessive NFS/
queue load, or failed existing deployment gates.

For reader defects switch explicitly to legacy reads through canonical
activation, retaining additive tables and healthy notifications. Expect the
original latency to return. For refresh overload stop sweeps and switch reads
to legacy, retaining dirty state. For adapter defects deploy the previous
known-good application revision through the canonical workflow; do not simply
disable the existing timestamp mirror on a deployed stack.

Never drop tables, replay SQL into NoDb, delete project files, or clear unrelated
Redis queues for rollback. Recovered candidates must reconcile, compare, and
preflight before re-enabling reads. Database restores use existing tooling;
restored projections are revalidated against current files/registrations.

Before rolling any eligible consumer back to code without the sweep callable,
disable catalog enqueue admission and drain started catalog sweeps under existing
active-job gates. Remove/cancel only queued catalog sweep jobs through supported
RQ operations, reconcile their private coalescing records, and retain dirty SQL
state. Verify no queued/started catalog jobs can reach the old consumer before
its rollback; preserve all unrelated jobs. Do not count a read-mode switch alone
as worker rollback safety. Re-enable sweep admission only after every eligible
consumer again satisfies the compatibility gate. Test queued and started cases.

Public polling serializers have a separate rollback gate: redaction-compatible
code must remain deployed for the entire retained lifetime of catalog job
records, including failed/finished records, recursive references, and stored
results. A previous revision without this protection is not a valid public
polling rollback while those records remain. Use a known-good rollback candidate
that retains this narrow protection; do not silently downgrade it or assume
queue draining deletes terminal evidence. This contract does not authorize
bulk Redis cleanup or introduce a new sanitization tool. Test anonymous single/
batch job-info and jobstatus after rollback with retained failed terminal jobs
containing private diagnostic canaries; no raw details may escape.

## 12. Acceptance and documentation

Cover independent dimensions: absent/empty/populated/current/legacy/malformed
source; standalone/enabled; healthy/unavailable DB; warm/cold process;
grouped/legacy location; normal/admin/shared/unauthorized scope; changes during
refresh. Do not claim exhaustive testing without the input/state matrix.

Real PostgreSQL tests cover constraints, acknowledgment races, advisory
contention, cascade/UUID fencing, and connection loss. Real filesystem tests
cover coherent Ron/TTL reads, unchanged bytes/version/markers, offline
same-size/restored-mtime edits, and notification failure after commit. Prove
import independence with database/web modules unavailable. Exercise producers,
not just adapter functions. Preserve model inputs/outputs through representative
save/run/archive/restore workflows.

Run focused NoDb/catalog/TTL/migration/worker/scheduler/UI tests, then repository
gates, RQ graph, changed-surface stub checks, frontend lint/test, changed-code
exception enforcement, and docs lint. Verify live job trees and actual browser
performance under production-equivalent identities, groups, mounts, umask,
configuration, and orchestration. Unit tests alone cannot approve this boundary.

Update NoDb developer guidance, NoDb and TTL contracts, operator/container/
worker docs, catalog user help, and RQ dependency documentation with runtime
changes. Shared-contract amendments in this set remain implementation-pending.
Closure requires independent correctness/security sign-off, all host evidence,
rollback proof, and explicit legacy-reader retirement disposition.
