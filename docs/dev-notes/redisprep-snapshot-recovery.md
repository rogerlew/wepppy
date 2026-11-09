# RedisPrep snapshot operation and recovery

[Canonical guarantees](../schemas/redisprep-snapshot-contract.md) distinguish
healthy live Redis metadata from `redisprep.dump` recovery data. The implementation
is validated locally; deployment and cross-host acceptance are separate gates.

## Normal use

Use RedisPrep setters or `update_metadata(values, remove=(...))` for a bounded
multi-field operation. They atomically update live Redis and then publish a
complete flat JSON snapshot under short serializer/lifecycle coordination.
`dump()` captures under that coordination, including direct legacy mutations,
but direct Redis writes are not themselves part of the restore protocol.
Use `persist=False` only for established live-only projections, such as postfire
revision notifications. It does not claim snapshot persistence.

Ordinary parallel setters serialize without caller retries. Contention with
archive, fork or other lifecycle operations fails before mutation; retry after
that operation completes using a fresh wrapper. A replaced directory, incarnation
or profile namespace rejects old wrappers. No guard is held across model work.
Loaded reads need no new filesystem write permissions. Missing-directory dump
remains a no-op; a formerly bound wrapper cannot seed deleted/recreated live state.

Ordinary catalog metadata operations participate in the same short serializer,
including identity initialization, clone rotation, receipts and publication.
Batch siblings share lifecycle ownership because deleting or restoring a batch
replaces every child. They wait for ordinary metadata work, while genuine
lifecycle contention remains an explicit pre-mutation failure for RedisPrep.
Catalog callers retain their historical waiting behavior: only acquisition is
retried, with the serializer released between attempts. Caller bodies execute
once, and deleted directories are refused. Candidate collection and model execution stay outside these critical sections;
final inventory/schema revalidation remains inside publication ownership.

## Failure interpretation

- **Pre-replacement file failure:** prior snapshot remains authoritative on disk;
  a setter may already have changed Redis. Inspect live state before retrying.
- **Replace response lost:** `published=None` means publication is uncertain;
  read the destination and compare relevant fields before retrying.
- **Post-replacement directory fsync/cleanup/release error:** published bytes are
  not rolled back. Durability or cleanup is uncertain; preserve the artifact.
- **Redis EXEC response lost:** `live_committed=None` means the transaction may
  have committed. Inspect the hash and real RQ job before retrying admission.
- **Corrupt recovery file:** retain original bytes and use a verified archive or
  healthy live state under operator-controlled quiescence. Do not replace it with
  `{}` or infer completion from saved job IDs.
- **Ambiguous partial unloaded hash:** reconcile it explicitly. Lock mirrors and
  `last_modified` alone are valid cold recovery and are preserved.

An already-partial historical hash with a true loaded marker is indistinguishable
from valid subsequent deletion. Automatic diagnosis is not claimed. Quiesce the
specific project, retain its snapshot/live metadata, reconcile actual RQ jobs,
and select verified recovery state before explicit restoration. Never flush a
shared database, delete RQ jobs, or clear unrelated ownership to restore metadata.

`restore_snapshot()` is an explicit lifecycle replacement operation for approved
fork/archive recovery, not a generic retry after a failed setter. It preserves
unrelated live metadata and removes obsolete owned receipts. Failed archive
extraction retains any incoming snapshot already published; receipt cleanup does
not overwrite it with the unreconciled old hash. Inspect the failed restore before
resuming use. Nested archived snapshots are retained files, not permission to
activate another Redis namespace.

## Files and rollout checks

`redisprep.dump` remains a normal project artifact included in archive/restore.
Owned `.redisprep.dump.*.tmp` staging files are never restoration authority;
process-death orphans may be removed only after verifying no writer owns them.
Keep stable lifecycle/serializer lock inodes: managed `<owner-hash>.lock` and
`<owner-hash>.redisprep.lock` live in configured coordination storage; standalone
`_query_engine/refresh/publication.lock` and `redisprep.lock` are preserved during
in-place restore with `incarnation.json`. Do not unlink them to clear contention.
Process-held locks release on exit; repair a stuck process through normal ops.

The `initialization_only` bit in existing catalog incarnation JSON distinguishes
normal first initialization from destructive replacement. Restore persists its
replacement fence before destruction and never accepts archived coordination
markers as live ownership. Older missing bits remain conservative.

Before rollout, prove cross-host exclusion on the actual NFS/local-server pairing
and effective web/worker/archive UID, GID, mode and ACL access. POSIX record locks
are required; `flock` is not a substitute for the supported NFS/local-ZFS pairing.
Do not mix old truncate writers with the new publication protocol. No deployment
is authorized by this repair package. Existing basename collisions across distinct
projects remain a separately governed identity-migration boundary.

Regression entry point: `wctl run-pytest tests/nodb/test_redis_prep_snapshots.py`.
The suite uses a disposable local redis-server or an explicitly marked disposable
`RQ212_TEST_REDIS_SOCKET`; it never flushes shared Redis. Retain skipped service
checks as skipped, not passed.
