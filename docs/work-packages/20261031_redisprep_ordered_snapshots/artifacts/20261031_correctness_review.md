# Correctness review — RedisPrep snapshots

Reviewer: independent `implementation_review`, with preliminary `protocol_review`.
Date: 2026-10-31 UTC. Context: master, checkpoint ancestors 88b5c174f and ea95e1298,
implementation working tree. Canonical authority: RedisPrep snapshot contract,
including RPS-01A and participating setter serialization. Related reviews:
`20261031_security_review.md`, `20261031_qa_review.md`.

## User outcome and failure class

Complete ordered recovery metadata, coherent readiness and preserved receipts
without duplicate admission. `consumer-matrix.md` records the bounded inventory.
File replacement is the visibility point, serialized HGETALL establishes newer
capture, and conditional Redis EXEC exposes restoration atomically. A successful
Redis update and a failed snapshot remain distinct outcomes, never automatic
rollback. Lost RQ jobs are not reconstructed. No production incident asserted.

## Valid states and actual evidence

All named tests are in `tests/nodb/test_redis_prep_snapshots.py` unless specified.

| State | Behavior / evidence |
| --- | --- |
| Fresh file/hash absent | Concurrent constructors initialize coherently; `test_concurrent_fresh_constructors_retry_after_contention` |
| Empty JSON object | Valid empty recovery, loaded atomically; `test_empty_legacy_snapshot` |
| Populated live hash/file missing | Preserve metadata and capture; `test_missing_file_preserves_live_hash_and_missing_directory_is_not_created` |
| Only NoDb mirrors live | Restore cold metadata preserving lock/last_modified; `test_cold_restore_preserves_independent_live_fields` |
| Legacy saved true loaded marker | Kill before EXEC exposes no partial marker; `test_two_cold_loaders_and_kill_before_atomic_restore` |
| Ambiguous unloaded partial hash | Explicit error without mutation; `test_ambiguous_partial_unloaded_state_is_not_blessed` |
| Corrupt/nonobject/nonscalar/nonfinite file | Original bytes retained; `test_corrupt_recovery_preserves_evidence` |
| Healthy loaded read under 0555 | No mkdir/write requirement; `test_loaded_reader_requires_no_write_permission` |
| Deleted/recreated/in-place restored path | Old wrapper cannot seed new state; lifecycle, namespace and killed-restore tests |
| Copied/profile/nested archive | Destination reset isolated; only root has live activation authority; nested-collision test |
| Parallel actual setters and batch leaves | Real kernel contention, no caller retries or model execution; multi-process tests |

## User-reachable errors

Corruption and ambiguous recovery are exceptional, requiring retained-evidence
reconciliation. Genuine lifecycle contention is retryable before mutation; normal
setters serialize. Stale incarnation/namespace requires a fresh wrapper. Redis
EXEC response uncertainty, pre-replacement failure and committed/uncertain file
publication identify the affected store/stage. Existing endpoint translation is
retained. Accepted historical already-loaded partial state remains indistinguishable
from legitimate later deletion; this is not claimed repaired automatically.

## Artifact evidence chain

| Stage | Direct evidence | Result |
| --- | --- | --- |
| Intended setters/deletes | Real flags, task times, rq/archive IDs and multi-field resets | Pass |
| File publication | Large concurrent readers, actual kernel contention, write/fsync/replace failures and writer kill | Pass |
| Normal reader | Cold RedisPrep restoration and atomic/conditional EXEC races | Pass |
| Receipt consumer | Real RQ job retained, `prepare_redisprep_job_id` rejects duplicate accepted work | Pass |
| Report/cleanup consumer | Actual Omni contrast reader and WEPPcloudR tracked-receipt removal | Pass |
| Archive | Canonical archive/restore, incoming-mode staging, late failure and killed restore | Pass |
| Model output | No scientific preparation/execution formula changed | N/A |
| Service access | Existing web/worker/archive/browser identities inspect shared NFS artifact; see access.jsonl | Local evidence |
| Cross-host rollout | Production host and NFS/server pairing not exercised | Hold |

## Findings and disposition

| Finding | Severity | Resolution |
| --- | --- | --- |
| First catalog initialization looked like replacement | High | Reviewed RPS-01A provenance bit; one-time adoption regression |
| Failed archive cleanup rewrote incoming bytes from old live hash | High | Skip unreconciled cleanup; real late-failure test |
| Missing old wrapper mutated live Redis | High | Reject stale setters after deletion; no-op late dump retained |
| Constructor observed transient profile namespace | High | Revalidate namespace inside mutation guard |
| Nested snapshots activated arbitrary basename hashes | High | Activate only proven archive root; preserve nested file artifacts |
| Batch-owner nonblocking initialization rejected parallel leaves | High | Same serializer discipline; actual two-leaf initializer test |
| Root-symlink guard side effects | Medium | Validate/open fork root before resolving guard |
| Private archive mode applied after publication | Medium | Stage required mode before replacement |
| Guard release leaked fd / mislabeled committed operation | Medium | Nested close and committed-state classification tests |
| Ordinary parallel setters failed on self-contention | Medium | Short serializer then nonblocking lifecycle ownership; four-process regression |

Final independent verdict: all reviewed findings resolved; zero remaining medium/
high code findings. Approved for reviewed local implementation scope. Existing
basename collisions, accepted historic partial-state ambiguity and production
mount/identity parity remain explicit boundaries; not a class-wide deployment or
incident-resolution claim. Broad-suite provenance is recorded separately.

## Final archive correction

Independent reviewer rechecked restoration of post-extraction catalog invalidation
after the consumer test exposed copied nested identities surviving restore.
Approved: pre-destructive root fencing remains intact; copied requests/nested
identities retire before fresh RedisPrep binding. Final consumer run: 183 passed;
final NFS snapshot run: 52 passed. No new correctness findings.
