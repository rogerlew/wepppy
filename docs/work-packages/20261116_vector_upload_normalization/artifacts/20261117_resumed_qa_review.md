# Resumed frozen-candidate QA review

Date: 2026-11-17
Reviewer: independent `qa_reviewer` (`frozen_qa`)
Source revision: `54ee356fd16845e7abf6da59d7df616f8b5fa6ce`
Sharing-policy revision: `bbb216c0bc48674f8b24f5e69f20ec58e57b795a`
Prior runtime-qualified selection: `1bb088da5eb3aed6a2d591333ad7931644a21329`
Recovery-review ancestor: `ee26389f099e9e950b5920d53790f8661548a5e3`
Initial reviewed ancestor: `de15403aadbd7a659ef4717e77223ff4890b18c1`
Comparison revision: `0e861887e132b41b00a108292d7833d21750b146`
Exact local image: `wepppy/shape-converter:vector-upload-m2-final5`
Image ID: `sha256:4487dec16cdb1a0ed735e60f10672c646ecc3b26d0586dbfce93479b9eae98fa`

## Review boundary and current disposition

The reviewer did not author the implementation or tests under review. Source and
fixtures were read independently across the committed successors. This review
covers the six findings in `20261117_final_qa_frozen_successor_review.md` and the
subsequent sharing/copy/reset implementation and its mapped consumers. The
latest committed source was initially clean; later uncommitted final fixes are
identified separately and are not silently included in that revision.

**QA source disposition at `54ee356fd`: no additional High or Medium finding.**
The six original findings remain closed by committed remediation and retained
runtime evidence. `VUN-CORRECTNESS-RESUME-01` is resolved by the explicit operator
sharing decision, not a privacy filtering change. The copy/reset accounting
implementation and its consumer regressions address the second correctness
finding in source; final runtime and independent primary-review closure remain
required.

**Overall M5 disposition: HOLD pending final acceptance.** The operations finding
on ancestor/stale-directory durability and final disk-reserve correction are
being integrated after `54ee356fd`, and the final focused/full gates have no
completed receipt yet. Reviewed uncommitted fixes and tests are suitable, but
receive no committed-source or runtime pass claim here. The receipt preserves
each source revision, result and skip rather than combining unrelated selections.
Publication, deployment and remote-host acceptance remain separate gates.

## Finding dispositions

### VUN-QA-FROZEN-01: downstream artifacts

Closed in source and retained runtime evidence. The 20 downstream cases cover four suffixes
at each of Roads, AgFields, Batch, Omni run and Omni dry-run. The actual Roads
converter consumes deterministic projected rasters; the test reads monotonic
segments and low points, compares the complete resulting feature properties and
geometry to a GeoJSON control, and reloads the controller. Batch invokes
`run_batch_hillslopes()` to clone/select/save/register its target watershed and
reads that generated input and detached Ron boundary state. Only unrelated
simulation stages and infrastructure are isolated. Omni calls both actual build
entry points, then reads `build_report.ndjson`, the contrast sidecar and overlay,
and compares a report from detached state. AgFields reads its generated rotation
Parquet and all retained feature properties. Every suffix verifies terminal
acceptance, retained original bytes, source SHA-256 and canonical SHA-256.

The tests' explicit fake retention ledger is appropriate for this artifact
boundary; separate new real-Redis request tests cover identity/accounting. These
cases establish upload-to-next-artifact behavior, not complete WEPP simulation
or a production browser/network rollout.

### VUN-QA-FROZEN-02: reproducible source/image evidence

Closed. The fixture and runtime binding changes are correct. Six retained input files
have a complete size/SHA-256 manifest, and independent rehashing reproduced every
entry. Both exact-image modules query readiness before inputs and assert the
GeoParquet binary hash, version, lock hash and Git-resolved source revision.
Independent Docker readback confirms the image ID printed above. The canonical
receipt retains that image, readiness/parser identities, runtime UID/GID, source
revisions and snapshot directories, exact commands, JUnit hashes, every test
result and skip reason, and all six fixture hashes. Its source readback records
95 changed production/test/tool files checked against the final container
snapshot with zero mismatches. Readiness alone is not treated as image proof.

The `de15403aa` selection passed 423 tests with four explicit exact-receiver
configuration skips; `ee26389f0` passed 452 with the same four skips. The final
`1bb088da5` selection passed all 206 tests, including each of those four exact
receiving nodes, actual workflow retention paths and post-build Omni receipt
readback. The intermediate fixture-setup failures at `860ba6760` are preserved
and correctly superseded by the two-line fixture-parent correction. These are
separate selections rather than one inflated aggregate pass count.

### VUN-QA-FROZEN-03: destructive recovery fault coverage

The prior mock-only evidence gap is closed in source and retained runtime evidence. The new deletion and archive
modules call real marker helpers, Redis Lua accounting and renewable scope leases
under isolated key prefixes. Faults cover missing configuration/containment,
partial removal, file/directory fsync failures, deliberate loss of lease keys,
rebuild failure, symlink substitution, absent-target retry and Redis-marker loss.
They prove that pending dual obligations survive failed destructive operations,
retry converges, unrelated retained bytes survive, and global/principal totals
remain exact while active reservations are preserved. Deterministic lease-key
loss exercises ownership failure without relying on expiry timing or a sleeping
background renewer. Run deletion rejects invalid configuration before catalog
or TTL mutation; private restore rejects live and incoming sensitive evidence
before RedisPrep mutation.

### VUN-QA-FROZEN-04: signed-session provenance

The new five-boundary request suite closes the missing receiving evidence. It
uses signed Flask sessions and actual cookie-to-JWT decoding for rq-engine,
then real receiving actor extraction, retention receipts and Redis accounting.
It checks accepted/rejected original bytes and hashes, the numeric human actor,
exact global/principal retained-byte totals, zero residual reservation charges,
and minimized rejection events. Anonymous and non-owner/nonmember requests fail
before staging. Account lookup, controller work and queue execution are explicit
seams; this is not a claim that those subsystems are independently tested here.

The former finding's requirement to omit filenames from every durable surface
was too broad: the canonical contract requires sanitized submitted filenames in
private receipts. The new test correctly preserves that metadata and excludes
filenames from security events. Cookies, raw identity claims, email and client
IP remain excluded from both receipt and event surfaces.

### VUN-QA-FROZEN-05: concurrency false-green

Closed. The worker coordinates attempted/blocked/retry/completed events and sends
all exceptions back to the main thread. The callback cannot proceed without
proof that the first lock attempt was rejected; the worker must then commit a
unique sentinel after rollback. The final assertions require that it observed
only restored bytes, completed without errors, terminated, and survived detached
reload. There is no scheduling sleep or uncaught-thread-warning success path.

### VUN-QA-FROZEN-06: whole-Batch deletion

The missing lifecycle consumer is now covered. Batch deletion validates retained
evidence and root configuration, acquires global maintenance before its Batch
and child-run scopes, records a deterministic rebuild obligation, removes and
flushes durably, reconciles and verifies ownership, then clears markers in order.
Absent retry resolves the same target without requiring a surviving controller.
Real-Redis tests cover normal and failed removal, absent retry, fsync/rebuild and
ownership failures, missing configuration and exact deleted/unrelated/reserved
principal accounting. Two tests additionally hold `_base` and generated child-run
upload scopes and prove deletion cannot reach content/cache mutation until those
scopes are released.

## Additional primary-review finding

The primary code reviewer found that an unrelated parent deletion could remove
an archive workspace still needed by an earlier pending repair. The successor
`ee26389f0` rejects new destructive identities while either filesystem or Redis
contains another pending obligation. Six tests cover run/Batch parent deletion
against both, filesystem-only and Redis-only authorities; the original exact
operation/target can still recreate both markers and resume. The QA review finds
the test shape appropriate and the scope aligned with existing fail-closed
accounting. Its six frozen runtime cases passed in the `ee26389f0` receipt.

## Omni retention successor

The `860ba6760..1bb088da5` follow-up places exact downstream attempts under their
real workflow roots and checks the Omni receipt after build. Production contrast
clear/rebuild/stale cleanup now preserves `vector_upload_attempts` alongside
`_uploads`. Four direct cleanup cases check retained bytes while obsolete contrast
workspaces are still removed; all eight format/run-or-dry-run Omni downstream
cases read the retained receipt after the actual build. The final 206-test
selection passes with no skips. This closes the discovered cleanup consumer
without substituting for the later fork/clone lifecycle coverage below.

## Sharing, copy and reset successor

The policy at `bbb216c0b` explicitly permits an admitted public/team copier to
inherit originals, rejected attempts, receipts and private archives. Direct
sensitive-download restrictions remain unchanged. This review applies the
canonical contract's "Sharing, copies, and existing workspace resets" section;
inheritance is not reported again as an unauthorized disclosure.

The `bbb216c0b..54ee356fd` production delta and all new regression modules were
read independently against `20261117_vector_retention_copy_reset_inventory.md`.
The shared lifecycle helper uses existing Redis maintenance/project leases and
dual repair obligations. It preserves original upload provenance, adds bounded
copy provenance and a separate retention actor, verifies copied payload hashes,
admits full incoming physical bytes without speculative deletion credit, and
rebuilds exact totals while preserving active reservations. Source ownership and
recipient charges are tested separately. The helper makes the newly mapped
ordering visible without introducing another store or queue.

| Consumer group | QA evidence boundary |
| --- | --- |
| Ordinary forks and target replacement | Actual rsync, copied original/private-archive bytes, unchanged source receipt, verified actor forwarding, recipient quota rejection, stable tombstone and both/single-authority absent-target retries. |
| Batch leaf/base/Omni subtree | Actual copy/reset entry points, all five retained roots, detached copied state, no-reset rerun, interrupted copy forcing retry, failed cleanup preventing another copy, and exact principal/global readback. Unrelated model execution is stopped after the boundary. |
| Omni cleanup/reset | Actual bulk/stale/single-child cleanup, preservation of owning attempts, pending repair after failure, absent-child retry, deferred stale evidence accounting, and borrowing a live upload scope without losing its reservation. |
| Profile promotion/playback/export | Actual assembler/session/service copy paths, preserved offline bytes/modes, managed reentry charges, split-root compatibility, missing-config refusal, deterministic reset, interrupted retry and private-archive export readback. Network/model setup is explicitly isolated. |
| Shared copy helper | Accepted/rejected/reconciled-incomplete states, repeated-copy provenance, bounded receipts, quota rejection before mutation, linked evidence and missing-receipt refusal, reservation preservation, and release attempts after a release failure. |

The fixtures use real Redis under per-test namespaces and compare complete
physical bytes and exact charges rather than accepting callback success alone.
The tests preserve existing model symlinks and profile merge/config-seed
semantics. The inventory explicitly excludes culvert/D-Tale and fixture-only
test-support deletion; this review makes no retention-safety claim for those
paths or production public-fork canaries.

The subsequent uncommitted correction adds all outstanding reservations to the
disk-free admission requirement, syncs intervening evidence ancestors and newly
retained stale trees, and adds direct pre-mutation/real-consumer assertions. The
exact downstream fixture is also being upgraded from a fake ledger to real
authenticated Redis with post-workflow receipt/totals/reservation/marker checks.
Those changes were read and introduce no additional QA concern, but must be
bound to the final source and completed runtime receipt before acceptance.

## Residual non-blocking debt

- Run, Batch, private-delete and restore code repeat the same lease/obligation/
  reconcile/complete sequence. A later behavior-preserving extraction could reduce
  future ordering drift; the present explicit sequence remains reviewable.
- The real-Redis test modules duplicate connection and namespaced-ledger
  setup. A narrowly shared fixture could reduce maintenance cost while preserving
  each test's visible fault boundary. Random per-test namespace IDs would also
  make simultaneous independent runs of the same module easier to isolate.
- The two child-scope tests intentionally use the real ten-second acquisition
  deadline and are marked slow in the successor. Their result is based on
  ownership refusal and final state, not a timing assertion.

## Validation observed by this reviewer

- Verified each reviewed source revision and clean initial worktrees.
- Read the complete successor production/test diffs, all six prior findings,
  ratified sharing policy and complete copy/reset consumer inventory.
- Independently hashed all six retained equivalence fixtures; every size/hash
  matches `tests/data/vector_upload_final5/manifest.json`.
- Independently read back final5's running image ID through Docker.
- `git diff --check 0e861887e 1bb088da5` and
  `git diff --check bbb216c0b 54ee356fd` passed.
- Independently parsed the canonical JSON receipt, recomputed per-run result
  counts, and matched every earlier exact-receiver skip to its final passing
  node. No new runtime execution was needed for this evidence readback.
- Reviewed primary correctness's fork/clone findings and the explicit policy
  decision and lifecycle remediation that address them. Final accounting and
  operations closure must come from their independent reviews and frozen gates.
- Frontend evidence records lint, 126 Jest suites/1,091 tests and nine Node tests
  passed at unchanged frontend source. The broad sanity selection was interrupted
  after 475 actual tests passed and 28 skipped when scope reopened; it is
  explicitly incomplete and receives no complete-gate credit.
- The new full gate in `/tmp/vun-final-acceptance` was still running when read;
  `/tmp/vun-final-full.log` has no completion result. A final source-bound focused
  and full receipt is required. Historical selections cannot replace it.
- Document lint and spelling-normalization preview pass for this review artifact.
