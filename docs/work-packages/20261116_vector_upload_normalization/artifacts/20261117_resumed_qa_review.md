# Resumed frozen-candidate QA review

Date: 2026-11-17
Reviewer: independent `qa_reviewer` (`frozen_qa`)
Source revision: `1bb088da5eb3aed6a2d591333ad7931644a21329`
Recovery-review ancestor: `ee26389f099e9e950b5920d53790f8661548a5e3`
Initial reviewed ancestor: `de15403aadbd7a659ef4717e77223ff4890b18c1`
Comparison revision: `0e861887e132b41b00a108292d7833d21750b146`
Exact local image: `wepppy/shape-converter:vector-upload-m2-final5`
Image ID: `sha256:4487dec16cdb1a0ed735e60f10672c646ecc3b26d0586dbfce93479b9eae98fa`

## Review boundary and current disposition

The reviewer did not author the implementation or tests under review. Source and
fixtures were read at the committed revision above; the initial worktree was
clean. The three-file recovery successor and the later Omni retention/test
fixture delta were then read independently. This is the secondary
quality/test-adequacy review of the six findings in
`20261117_final_qa_frozen_successor_review.md`. The scope is local implementation
acceptance, not publication, remote integration or production deployment.

**Overall M5 disposition: HOLD.** The six original QA findings are closed by
the committed remediation and the retained revision-bound runtime evidence in
`20261117_resumed_validation.json`. The remaining package blockers are
`VUN-CORRECTNESS-RESUME-01` (High fork privacy) and
`VUN-CORRECTNESS-RESUME-02` (Medium fork/Batch clone-reset accounting), recorded in
`20261117_resumed_correctness_review.md`, plus the unfinished full final sanity
and acceptance gates after their remediation. The operator's copy-retention
contract must resolve before dependent behavior is chosen.

Within the six original QA remediation areas, this review finds no additional
High or Medium quality defect. The receipt preserves each source revision,
individual runtime results and skips; earlier working-copy aggregates are not
used as replacements for those records. Publication, deployment and remote-host
acceptance remain separate from this local review.

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
without implying that the still-open fork/clone consumers are repaired.

## Residual non-blocking debt

- Run, Batch, private-delete and restore code repeat the same lease/obligation/
  reconcile/complete sequence. A later behavior-preserving extraction could reduce
  future ordering drift; the present explicit sequence remains reviewable.
- The three new real-Redis test modules duplicate connection and namespaced-ledger
  setup. A narrowly shared fixture could reduce maintenance cost while preserving
  each test's visible fault boundary. Random per-test namespace IDs would also
  make simultaneous independent runs of the same module easier to isolate.
- The two child-scope tests intentionally use the real ten-second acquisition
  deadline and are marked slow in the successor. Their result is based on
  ownership refusal and final state, not a timing assertion.

## Validation observed by this reviewer

- Verified exact source revision and clean initial worktree.
- Read the complete successor production/test diff and all six prior findings.
- Independently hashed all six retained equivalence fixtures; every size/hash
  matches `tests/data/vector_upload_final5/manifest.json`.
- Independently read back final5's running image ID through Docker.
- `git diff --check 0e861887e 1bb088da5` passed.
- Independently parsed the canonical JSON receipt, recomputed per-run result
  counts, and matched every earlier exact-receiver skip to its final passing
  node. No new runtime execution was needed for this evidence readback.
- Reviewed primary correctness's two remaining fork/clone findings; they hold
  package acceptance despite closure of the six original QA findings.
- Frontend evidence records lint, 126 Jest suites/1,091 tests and nine Node tests
  passed at unchanged frontend source. The broad sanity selection was interrupted
  after 475 actual tests passed and 28 skipped when scope reopened; it is
  explicitly incomplete and receives no complete-gate credit.
- Document lint and spelling-normalization preview pass for this review artifact.
