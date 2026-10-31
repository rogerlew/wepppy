# RedisPrep atomic ordered snapshots (RPS-01)

Status: operator-authorized bounded repair; contract checkpoint accepted 2026-10-31;
implementation conformance pending. This contract applies to RedisPrep, which
is not a NoDbBase singleton. The NoDb disk-authority and failed-memory-recovery
rules do not make RedisPrep's live hash a disposable cache.

## Authority and compatibility

During healthy operation, Redis DB 0's resolved run hash is authoritative live
metadata. `redisprep.dump` is its recovery snapshot, not an RQ job database.
After metadata loss, the last valid published snapshot supplies recovery data;
missing RQ jobs still require existing submission reconciliation. No synthetic
completion, enqueue, or cross-store transaction is implied.

Keep the legacy flat JSON object, field meanings, basename-derived namespaces
and validated `.redisprep-run-id` profile namespace. Do not silently change
batch, pup or scenario identity to NoDbBase's different runid scheme. Physical
aliases to one project must share coordination. Distinct copied destinations
are separate lifecycles; fork marker stripping is intentional, not stale source
publication. Namespace collisions must be identified and resolved explicitly
before claiming isolation for that variant, not hidden by a new key scheme.

The persisted record remains `redisprep.dump`, visible through normal project
inspection and included in archive, restore and skeleton retention. Profile
namespace identity must survive supported retention workflows. Temporary files
and empty coordination locks are not substitute project records.

## Atomic and ordered publication

A participating publication MUST acquire cross-process coordination before
capturing the live hash and retain it through replacement. Newer means a later
capture in that serialized critical section, not mtime, invocation order or
an independently allocated Redis counter. Once a newer capture is published,
an older capture MUST NOT replace it. No expiring-lease token check followed by
an unprotected rename satisfies this rule.

Serialize a complete object, create a uniquely owned same-directory temporary
file exclusively, handle short writes, flush and fsync it, then atomically
replace the destination. Replacement is the file visibility linearization point.
Readers observe a complete prior or next snapshot. On pre-replacement failure,
retain the previous bytes and remove only the caller's own temporary file.
A killed writer's orphan temporary file is never a recovery authority.

Attempt parent-directory fsync after replacement. A later fsync, cleanup or
release failure MUST identify that publication committed or is uncertain;
it MUST NOT restore old bytes or report an ordinary precommit rejection.
No full power-loss durability claim is permitted without filesystem evidence.

Preserve first-create umask-derived accessibility and existing effective reader
access on replacement, including ownership, mode and applicable ACLs. Preserve
existing fork no-symlink/regular-file protections. Do not add privileges or
silently tighten working paths. Unsupported metadata preservation must be
observable and tested under actual web/worker/archive identities before rollout.

## Mutation and lifecycle boundaries

Successful participating mutation return means the mutation reached live Redis
and a complete snapshot was published containing that state or a subsequently
serialized state. A later legitimate mutation may supersede it. If Redis changed
but persistence failed, report that split outcome; do not roll Redis back from
an older snapshot. Process death between stores can lose unsnapshotted changes.

Direct hash mutation followed by dump participates in snapshot ordering only
when dump captures under the publication guard. This alone does not make a
multi-command mutation atomic or serialize it against restoration. Confirmed
receipt/timestamp reset and restore-sensitive writers MUST use an atomic Redis
operation and the necessary shared coordination/conditional publication. Unrelated
NoDb lock mirrors and `last_modified` writers are not advertised as participants.

Coordinate destructive lifecycle transitions with capture/publication and
restoration. An old wrapper or paused writer MUST NOT mutate or publish into a
new incarnation at the same pathname. Account for in-place archive restoration,
not just directory inode replacement. Reuse proven existing managed-owner
lifecycle coordination where possible; retain lock order with submission,
project-config, Roads and NoDb guards. No locks across model execution.

Managed coordination must work across supported NFS clients and local server
access. Existing catalog coordination uses POSIX record locks plus thread
exclusion; `flock` is not evidence of parity for NFS/local ZFS. Lock inodes must
remain stable across deletion/recreation. Lost coordination fails explicitly;
an old owner must never publish or release another owner's coordination.
Standalone compatibility and managed-root configuration must remain explicit;
no silent unlocked fallback. Unsupported cross-host semantics block rollout.

Missing run directories remain a late-dump no-op and MUST NOT be recreated.
This no-op is not proof of persistence. A stale incarnation is rejected rather
than becoming a fresh wrapper for replacement data.

## Coherent initialization and restoration

Validate the complete snapshot before changing live metadata: it must be a flat
object of Redis-compatible scalar values, with no malformed JSON, non-object
root, null/container values, or non-finite numbers. Retain corrupt bytes and
surface failure; never replace corruption with usable empty defaults.

Restore the allowed fields and `attrs:loaded=true` in one atomic Redis visibility
operation, conditional on the state still being eligible for recovery. The
snapshot's own loaded marker MUST NOT become visible before the remaining
fields. A competing initializer or live writer must invalidate a stale restore
attempt; a delayed loader MUST NOT overwrite new values or resurrect deletions.
Do not delete the whole shared hash. RedisPrep owns `attrs:*`, `timestamps:*`,
`rq:*` and `archive:job_id`; postfire projection owns `postfire_debris_flow:*`.
NoDb independently owns `locked:*` mirrors and `last_modified`. A hash containing
only those NoDb fields remains eligible for cold metadata recovery; preserve
existing live values, including newer `last_modified`, rather than replaying
older snapshot values over them. Other extensions require explicit ownership
inventory before defining their recovery eligibility. Preserve unrelated live
fields and active coordination. Exclude `locked:*` on publication and restore. Tokens, leases and
other active ownership are not restorable records; any further field exclusion
requires a named compatibility decision and test in this contract.

| State | Required behavior |
| --- | --- |
| No file and no metadata | Initialize fresh loaded state coherently; snapshot only if the run directory exists. |
| No file and populated live metadata | Preserve live data; initialize readiness and capture without clearing fields. |
| Valid empty object and cold hash | Restore empty metadata plus readiness atomically; empty is valid. |
| Only unrelated `locked:*`/`last_modified` fields, no readiness | Eligible cold metadata recovery; atomically restore allowed missing metadata while preserving live unrelated values. |
| Valid legacy object and cold hash | Restore allowed legacy scalar fields atomically; retain reader compatibility. |
| Live loaded hash | Live authority wins; loading must not replay old disk values. |
| Missing/false loaded marker with nonempty metadata | Establish whether it is cold recovery, live mutation, or interrupted legacy restore; do not merge blindly or bless a partial hash. If ambiguous, fail explicitly without changing either store and require reconciled recovery. |
| Malformed/non-object/unreadable snapshot needed for recovery | Observable error with original bytes retained; no defaults or overwrite. |
| Concurrent constructors/loaders/writer | Exactly one coherent initialization outcome; losing attempts refresh/reject without clobbering live state. |
| Fork/restore lifecycle replacement | Incoming project state and intentional destination marker stripping govern under lifecycle exclusion; unrelated ownership is preserved. |

A legacy process may already have exposed `attrs:loaded=true` from snapshot data
before completing its per-field restore. That hash is indistinguishable from
legitimate later field deletion using only the existing marker and values.
Do not claim automatic detection or safe reconstruction of such historic damage.
Operator-accepted disposition (2026-10-31): known/suspected
partial legacy restores require operator reconciliation of live jobs/metadata
and snapshot before explicit recovery. The operator explicitly accepted this limit of the original acceptance request;
automatic detection is not claimed.
Tests MUST construct that state and demonstrate the limitation. Separately, the
required interrupted-restore test MUST load a legacy snapshot containing
`attrs:loaded=true` through the new normal reader and prove that interruption
cannot expose readiness before all restored fields. That test is not waived. A new completeness/version marker or migration policy requires an
explicit amendment before implementation; do not quietly invalidate healthy
legacy hashes or fabricate missing fields.

## Diagnostics and operator recovery

Report run identity, operation stage and committed/uncertain status without
payloads or lease secrets. Distinguish corrupt input, contention, stale
incarnation, Redis transaction uncertainty and pre/post-replacement failure.
After uncertain Redis publication, inspect the live state before retrying;
never assume an error means the transaction did not execute. On corrupt recovery
input, retain the file and inspect a verified archive or healthy live hash under
quiescence; no automatic salvage or backup retention system is authorized.
Do not flush shared Redis, clear unrelated locks or delete RQ data to recover
RedisPrep. Restore receipts only as identity hints, then reconcile real jobs.

## Acceptance and limits

Use deterministic barriers, real files and real Redis in two processes for
ordering/restore claims. Cover readers during large writes, older capture pause,
receipt/timestamp deletion, cold recovery after NoDb recreates unrelated fields,
direct writers, multi-field reset, concurrent fresh
constructors, writer kill, all write/replace/fsync stages, release failure,
lifecycle replacement, mode/umask/access, legacy corruption, profile and nested
namespaces, actual archive/restore and normal inspection. Parse the published
artifact, reload through RedisPrep, and inspect receipts/timestamps through an
existing submission/preflight consumer. Metadata-loss tests retain RQ job data.

Preserve WAM-01 admission/leases, MRS-01 early rejection, NFMS-01 reusable-memory
recovery, fork resets and callback replay. Measure setter/dump/startup cost;
no unbounded retry, global key scan, new dependency, datastore or service.
Mixed old truncate writers and new publishers do not satisfy this protocol.
Independent correctness/security reviews and representative identity/mount
validation gate rollout; unit tests alone do not prove environment parity.

Rationale: serialized capture through replacement closes the stale-publication
race that atomic rename alone leaves open. Atomic conditional Redis recovery
closes partial visibility and delayed-loader overwrites. Explicit cross-store
limits preserve honest failure/retry behavior without a distributed transaction
framework or guessed legacy repair.

## Initial catalog identity distinction (RPS-01A)

Implementation conformance pending. Normal first catalog initialization is not
project replacement and MUST NOT reject a previously bound RedisPrep wrapper.
Healthy loaded reads MUST NOT require new write access to the run directory or
coordination storage. The existing catalog incarnation marker may add
`initialization_only: true` only when creating the first identity without
replacement; destructive invalidation omits this field (equivalent to false).
Absent/false remains conservative replacement, including historical markers.
A wrapper bound before the first marker may adopt that first explicitly initial
incarnation while holding the guard, with unchanged directory identity. Once
bound to a nonempty incarnation, every incarnation change remains a conflict.
This does not add Redis fields or alter `redisprep.dump`'s flat schema.

Rationale: review reproduced normal catalog creation rejecting healthy completion
setters and a loaded reader in a mode-0555 directory failing at mkdir. Directory
identity alone cannot distinguish in-place restore, and the old marker's absence
cannot distinguish ordinary initialization from replacement. The one additive
provenance bit avoids forcing write access onto healthy readers. Missing historic
provenance is never guessed from file timestamps or status metadata.

Destructive in-place replacement MUST durably rotate the existing incarnation
with initial provenance absent/false before removing any project contents.
Restoration MUST preserve that fence and its held coordination inode through
cleanup, archive extraction, failure and process death; copied archive markers
cannot replace it. If pre-replacement fencing fails, do not start destruction.
An absent marker after interrupted replacement is not evidence of initialization.
Test kill/failure after destructive work begins followed by normal catalog
initialization and an old markerless wrapper's attempted mutation.

## Participating setter serialization

RedisPrep operations first take a short process-held serializer using the existing
catalog filesystem-guard implementation, then attempt lifecycle ownership
nonblockingly. Ordinary competing setters wait for the serializer and do not
need caller retries. A serializer holder never waits for lifecycle ownership;
therefore a lifecycle holder can safely invoke RedisPrep without an opposing
wait cycle. No serializer is held across model execution. Genuine lifecycle
contention is an explicit retryable conflict before mutation.

Managed serializer files are `<owner-hash>.redisprep.lock` beside existing
lifecycle locks. Standalone files are `_query_engine/refresh/redisprep.lock`.
These empty coordination inodes are retained across in-place replacement with
the existing publication lock. They contain no model record. Reuse was extended
because tests/review showed immediate rejection of parallel successful setters
would otherwise turn completion into workflow failure. No new lock service,
lease protocol, datastore or runtime dependency is introduced.

Effective profile namespace is revalidated under the mutation guard. A wrapper
created during transient archive extraction cannot later write a different hash.
Archive restoration activates only the root's proven run namespace. Nested
snapshots remain byte artifacts unless an independently governed workflow proves
their live namespace; repeated scenario leaves and provenance directories do not
authorize whole-system Redis mutation.
