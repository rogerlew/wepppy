# Resumed frozen-candidate QA review

Date: 2026-11-17
Reviewer: independent `qa_reviewer` (`frozen_qa`)
Final source revision: `4da014fee8a3c80643fc542165d6c529a85532ad`
Production source revision: `f964831084159eb4cf68cb533dc48235cb580989`
Archive-cleanup ancestor: `467e9db1b752ebd8448b569b58eede661f6e64a5`
Bounded-ZIP/exact-workflow ancestor: `111dd982cadb499333bc6b5eba2c07f9d4923d7c`
Complete affected-suite ancestor: `13feaac9276bd95f2341102d2683aca5a43cd3a5`
Broad-sanity baseline: `224184ecd778dd58844036084f272897b79f7cd7`
Copy/reset review ancestor: `54ee356fd16845e7abf6da59d7df616f8b5fa6ce`
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
production/test source was clean at the revisions reviewed. The complete
`54ee356fd..224184ecd`, `224184ecd..13feaac92` and
`13feaac92..111dd982c`, `111dd982c..467e9db1b` and
`467e9db1b..f96483108` production/test deltas were
then reviewed independently; concurrent review-document edits are separate.

**QA source disposition at `4da014fee`: PASS; no additional High or Medium finding.**
The six original findings remain closed by committed remediation and retained
runtime evidence. `VUN-CORRECTNESS-RESUME-01` is resolved by the explicit operator
sharing decision, not a privacy filtering change. The copy/reset accounting
implementation and its consumer regressions address the second correctness
finding in source and retained runtime evidence.

**QA M5 disposition: PASS for local implementation acceptance at `4da014fee`.**
The canonical `20261117_final_validation.json` is accepted. Independent readback
verified all nine log/JUnit pairs and all 113 changed source files against both
the committed revision and final container snapshot, with zero mismatches.
The complete ordered coverage contains 14,973 collected nodes: 14,497 passed and
476 skipped, with none unaccounted for. The repeated collection-only SBS skip
and 15 passing subtests are retained separately. All four earlier failing nodes
passed at the final source after the reviewed Roads staleness repair or verified
test-environment corrections.

This is source-qualified coverage across the recorded baseline, bounded
successors and ordered continuations, not one uninterrupted final-source suite
invocation. Exact source/image identities, commands, failures, skips, environment
corrections and ordering proofs remain visible in the receipt and below.
No High or Medium QA finding remains. Publication, deployment and remote-host
acceptance remain separate gates.

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

The final fixture uses actual authenticated Redis admission, renewable
scopes, maintenance and accounting, with only the connection injected. Teardown
compares every physical receipt directory with global/principal committed bytes,
requires zero reservations/inflight and no pending markers, and the Omni path
borrows the prepared lease through its real workflow transaction. Separate
signed-session tests cover receiving identity. These cases establish
upload-to-next-artifact behavior, not complete WEPP simulation or a production
browser/network rollout. Their final source-qualified runtime receipt passes.

### VUN-QA-FROZEN-02: reproducible source/image evidence

Closed. The fixture and runtime binding changes are correct. Six retained input files
have a complete size/SHA-256 manifest, and independent rehashing reproduced every
entry. Both exact-image modules query readiness before inputs and assert the
GeoParquet binary hash, version, lock hash and Git-resolved source revision.
Independent Docker readback confirms the image ID printed above. The canonical
receipt retains that image, readiness/parser identities, runtime UID/GID, source
revisions and snapshot directories, exact commands, JUnit hashes, every test
result and skip reason, and all six fixture hashes. The historical `1bb088da5`
source readback records 95 changed production/test/tool files checked against
that container snapshot with zero mismatches. The accepted final receipt binds
113 changed source files to `4da014fee`; independent Git/container rehashing
found zero mismatches. Readiness alone is not treated as image proof.

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

The committed `224184ecd` correction adds all outstanding reservations to the
disk-free admission requirement, syncs intervening evidence ancestors and newly
retained stale trees, and adds direct pre-mutation/real-consumer assertions. It
also upgrades the exact downstream fixture to real Redis as described above.

The descendant fix discovers active reservation scopes under global maintenance
using both composite project identities and bound attempt paths. Parent deletion,
restore, copy and reset therefore fence already-reserved children, including the
interval before an attempt directory exists. Eight regression cases use actual
prepared uploads or real unbound reservations: run/Batch deletion, parent restore,
Omni cleanup and the shared helper. They verify original bytes, unchanged totals,
live child ownership and absence of a destructive marker before allowing the
parent retry after upload completion. Additional missing-identity cases preserve
nested originals without metadata mutation.

The fork retry regression executes actual rsync, injects failure after copying,
then invokes the authorized API replacement helper and retries the worker copy.
It verifies exact destination repair, unchanged source and new recipient charge.
The production exception consumes only the matching destination `fork_copy`
identity; unrelated repairs remain barred by the common obligation helper. These
changes introduce no additional QA concern. Their final runtime qualification is
retained in the accepted canonical receipt.

## Final durability and archive-classification delta

The `224184ecd..13feaac92` production delta changes only the shared evidence
sync routine and archive creation. Sync now resolves the target path and flushes
every linking ancestor through the configured filesystem root, including newly
created shard directories. The regression uses two absent parents and both
relative and absolute targets, records real directory fsync calls, and asserts
child-to-parent ordering.

Archive creation now detects nested private archive bundles during classification
and checks each directory/file member before writing a public temporary ZIP.
The race regression injects an actual prepared child upload immediately after
the initial public classification, observes actual ZIP writes, and requires an
error before any retained member is written. It verifies unchanged source bytes
and receipt, live upload ownership and removal of the incomplete public archive.
After completion of the upload, retry produces a private archive containing the
original and its sensitivity sidecar. A second real archive case covers nested
private bundles without an upload-attempt directory. This protects direct archive
visibility while preserving the approved public/team copy contract.

The final `13feaac92..111dd982c` production delta changes only archive creation.
Its bounded private ZIP stream rejects a write whose ending file offset would
exceed the already admitted ZIP allowance, while permitting header rewrites
within that extent. The existing receipt allowance and quota defaults remain
unchanged. Three direct tests verify exact-final-size header rewriting, rejection
before central-directory growth and seek/overwrite extent semantics. The fourth
uses actual archive creation and real Redis, introduces incompressible child
growth after size estimation, and checks every resulting physical extent against
the bound. Source bytes survive; the partial ZIP is removed and committed,
reserved and inflight totals remain correct. The test scales only test headroom
to reproduce the retained overcommit without a large fixture.

The `111dd982c..467e9db1b` production delta also changes only the archive module.
Failed temporary-file unlink or containing-directory sync now retains the
reservation and writes an incomplete receipt under the verified archive actor.
Receipt persistence failure is logged while preserving the reservation. The
expanded real-Redis regression combines the size-cap rejection with unlink,
directory-sync or receipt-write failure. It verifies the original sources,
bounded residual physical bytes, remaining reservation/inflight charge and the
failure log. When a receipt is available, actual reconciliation converts the
reservation into exact remaining-byte charges under the archive actor, leaving
source-principal charges unchanged. The receipt-write-failure case preserves the
charge and deliberately leaves existing corrupt-receipt recovery for later.

The final `467e9db1b..f96483108` helper delta rejects copying a source receipt
whose accounting is pending, or whose referenced Redis reservation remains
uncommitted despite a committed-looking receipt. Both real-Redis regressions
require rejection before destination creation or copier charge, then invoke
actual reconciliation and prove successful copy with exact source/copier/global
totals. The recorded helper selection passed all 19 tests. Missing accounting
metadata retains the existing legacy compatibility default; known pending
accounting is not treated as reconciled evidence.

Source-qualified acceptance combines the completed broad prefix at
`224184ecd` with the repaired publication gate and ordered remainder at
`4da014fee`, plus the complete affected-suite run at `13feaac92` and the
archive-delta/exact-workflow/helper/session selection at `111dd982c`, followed by
the two complete archive modules at `467e9db1b` and the final helper tests at
`f96483108`. The final frozen `f96483108` helper/exact-workflow/session selection
also passed 130 tests without skips. Production
changes after the broad baseline remain bounded to the lifecycle helper and
archive module. The
selections include their actual consumer regressions and the prior vector
workflow cases. The receipt must retain every exact revision, command, result,
skip reason and final source/image readback, and map final fixes to passing nodes.
This does not claim that the full suite ran at `4da014fee`. The baseline failure
requires the provenance repair and ordered remainder below; prefix progress
alone cannot substitute for completed broad coverage.

## Roads publication provenance disposition

The broad `224184ecd` invocation stopped after 7,966 passed, 205 skipped and one
failure at
`tests/roads/test_roads_publication.py::test_published_results_and_sources_are_current_or_explicitly_stale`.
This is legitimate task-induced source drift, not an unrelated environment or
baseline failure. Independent comparison of all 100 Roads source fingerprints
found exactly two entries not covered by the historical staleness descriptor:

- `wepppy/nodb/mods/roads/roads.py`: the upload transaction stages replacement
  bytes and restores canonical/controller/retained-output state on failed receipt
  commit, while retaining successfully committed publication after a later log
  failure. The current source was finalized at `0e861887e`.
- `wepppy/wepp/interchange/_roads_lifecycle.py`: `restore_retained()` restores
  that failed mutation's prior outputs/runs/segments/cache under the existing
  Roads writer guard. This additive helper entered at `4654150c9`.

At the task's `05e3450fa` merge base, both hashes exactly match their previously
reviewed entries. Both current files are byte-identical at `0e861887e`,
`224184ecd` and `f96483108`. The complete source delta contains no numerical
formula, parameterization, native binary, scientific fixture or simulation-builder
change. The original report is already explicitly stale for full-project routing;
the new upload transaction does not refresh that historical evidence.

Following `docs/schemas/roads-validation-suite-contract.md`'s rerun/review or
explicit-staleness rule, the integrator authorized this reviewer to update only
`tests/roads/analysis_staleness_current.json`: two current hashes and two explicit
`subsequent_source_reviews`, with previous/current identities, actual source-change
commits and this rationale. The stale status/notice, recorded source hashes,
provenance, matrix results, report and vendored report remain unchanged. This is
a reviewed staleness disclosure, not a hash-only bypass or scientific rerun.

Independent readback of the retained `/tmp/vun-224-full.xml` confirms that Roads
upload staging, receipt-commit rollback with detached state, and post-commit
interruption tests passed before the publication check. The earlier exact-image
Roads cases additionally validate real monotonic conversion against GeoJSON
controls. Their scope supports the transaction review without certifying the
stale published full-project results as current.

An exact-node continuation is appropriate after the metadata-only repair:
collect the complete final suite in its normal order, require a unique matching
failed node, retain ordered excluded-prefix/selected-suffix manifests, and run
from that node inclusively through the end. Retain the original failed invocation
and the repaired publication rerun. The final receipt must show the complete
coverage union and source-delta tests separately; it must not call this one
uninterrupted full-suite pass. No repeated 52-minute prefix or changed historical
result hashes are needed to resolve this specific publication gate.

## Native test environment and coverage continuation

The first ordered suffix at unchanged source `4da014fee` passed 1,719 tests and
skipped 259 before failing at the first shape-converter abuse-control test. Its
startup correctly rejected `parser_binary_or_provenance_missing`: a Git checkout
does not include the native build outputs. This is an isolated-test environment
prerequisite failure, not evidence that the already-qualified final5 service
accepted a malformed request or bypassed its provenance gate.

The integrator copied both parser executables and their sidecars from final5 to
`/tmp/vun-final-parser-bin` and selected them through the existing
`SHAPE_CONVERTER_PARSER_CLI` and `SHAPE_CONVERTER_GEOPARQUET_PARSER_CLI` settings.
This reviewer independently hashed all four files in both containers: they match
byte-for-byte, and the final5 image ID remains the one above. The shape binary is
`1b9b719b9b6633684addd117be01dd7754b648f0a45ab27eea644185a30b70b3`;
the GeoParquet binary is
`160854839d237acb4c369bc15f97d5e51ae3841aaaca37777ba2353cfdd79c47`.
No executable source, test expectation or startup/provenance validation is
changed. The actual four-test abuse-control smoke passed before continuation.

The external selection-only plugins require a unique exact start node and
preserve collection order. Independent manifest/JUnit comparison found:

- All 8,173 nodes excluded before the repaired Roads node are covered by the
  baseline and final delta runs. Four final nodes differ from the baseline:
  the two fsync parameter cases and two source-reservation cases; all four passed
  in the final 130-test selection. Seventeen other apparent node differences are
  solely the explicit checkout directory in parameter IDs.
- The first suffix selected 6,800 nodes. The native-enabled selection is exactly
  its last 4,823 nodes, starting inclusively at the parser startup failure. Every
  one of the preceding 1,977 selected nodes has a nonfailed JUnit result.
- The collection-only SBS fixture skip appears in multiple processes and is
  separate from selected test nodes. The baseline's three subtests are also
  distinct from its 8,172 JUnit testcase elements. Do not inflate coverage by
  counting those as additional unique final nodes.

The original failed runs, their environment/source dispositions, both ordered
manifests, native binary/sidecar identities and the final remainder result must
remain in the canonical receipt. This reviewed environment correction supports
continued execution without repeating the completed prefix. It does not turn
either stopped invocation into an uninterrupted full-suite pass.

The parser-enabled continuation then passed 2,422 tests, skipped 15 and passed
12 subtests before the first bundle-read test failed because ignored
`controllers-gl.js` was absent. The integrator ran the committed
`wepppy/weppcloud/controllers_js/build_controllers_js.py` in the same checkout.
Independent readback confirms a clean tracked worktree at `4da014fee`; only
normal generated outputs were added. The generated main bundle is 2,239,250
bytes, SHA-256 `6eb9ddac8514d7b8e11f7c22ea54b120282b31ff2d83c9f04741176d468523ed`.
The builder log and generated-output identities belong in the final receipt.

The final bundle continuation is exactly the last 2,387 of the previous 4,823
nodes. Every one of the preceding 2,436 selected nodes has a nonfailed result;
the only extra JUnit row is the repeated collection-only SBS skip. Together the
ordered partitions are 8,173 + 1,977 + 2,436 + 2,387 = 14,973 collected nodes,
with the last partition subsequently split at the browser prerequisite below.
The accepted receipt retains the native partial invocation and proves that every
previously failed node passed at the final source, rather than accepting a pass
only from an older revision.

The bundle continuation passed another 1,533 tests and then stopped at the first
Chromium run-table test because the isolated checkout also lacked ignored
`static-src/node_modules/@playwright/test`. No browser assertion ran. Supplying
the established Node/browser dependencies is the appropriate environment
correction. Independent readback confirms that the installed-dependency source
and frozen checkout have identical package locks
(`2ddc0117c0bf2c559d2509bded8964801092fe68e4046ec3c8fa3df9c6877a92`).
The snapshot uses a local dependency symlink and existing Playwright browser
cache; the standard npm build supplies ignored static vendor assets. Tracked
source remains clean. Both actual owner/non-owner Chromium smoke cases pass.
The original bundle partial result and the final exact-node inclusive browser
selection must remain in the receipt; no test is changed or skipped to bypass
the prerequisite failures.

The final browser continuation passed all 854 selected tests. Independent receipt
readback accounts for every collected node across all ordered partitions and
confirms final-source passes for the Roads publication, parser startup, bundle
read and Chromium failures. The collector preserves each failed invocation,
all skip details and subtest suite attributes, and asserts exact source revision,
zero source mismatches, no uncovered suffix node and final-source failure closure.

## Residual non-blocking debt

- Run, Batch, private-delete and restore code repeat the same lease/obligation/
  reconcile/complete sequence. A later behavior-preserving extraction could reduce
  future ordering drift; the present explicit sequence remains reviewable.
- The real-Redis test modules duplicate connection and namespaced-ledger
  setup. A narrowly shared fixture could reduce maintenance cost while preserving
  each test's visible fault boundary. The final deletion/archive fixtures now
  use random per-test namespace IDs, avoiding collisions between independent runs.
- Child-scope refusal tests intentionally use the real ten-second acquisition
  deadline; the final successor adds the required `slow` metadata to the new
  cases. Their results depend on ownership refusal/final state, not timing
  assertions. The earlier marker follow-up is closed.
- A frozen-checkout test preflight should check native parser/provenance files,
  generated controller assets and Node/browser dependencies before the broad
  gate. Missing ignored prerequisites caused avoidable sequential stops in this
  run; a small prerequisite check would prevent that repeated setup work.

## Validation observed by this reviewer

- Verified each reviewed source revision and clean initial worktrees.
- Read the complete successor production/test diffs, all six prior findings,
  ratified sharing policy and complete copy/reset consumer inventory.
- Independently hashed all six retained equivalence fixtures; every size/hash
  matches `tests/data/vector_upload_final5/manifest.json`.
- Independently read back final5's running image ID through Docker.
- `git diff --check 0e861887e 1bb088da5` and
  `git diff --check bbb216c0b 54ee356fd` and
  `git diff --check 54ee356fd 224184ecd` passed. Final
  `224184ecd..13feaac92`, `13feaac92..111dd982c` and
  `111dd982c..467e9db1b` diff checks also passed. The final helper production/test
  delta and its two source-reconciliation cases were independently reviewed.
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
- The broad full gate used `/tmp/vun-224184ecd` and `/tmp/vun-224-full.log`;
  its failed publication disposition and completed continuations are above. The intermediate `/tmp/vun-cfd-focused.log`
  reports 718 passed with no skips. `/tmp/vun-13feaac92` and
  `/tmp/vun-13f-focused.log` report 721 passed with no skips.
  `/tmp/vun-111dd982c` and `/tmp/vun-111-delta.log` report 142 passed with no skips.
  `/tmp/vun-467e9db1b` and `/tmp/vun-467-delta.log` report 98 passed with no skips.
  `/tmp/vun-f964-delta.log` reports 130 passed with no skips. The ordered suffix
  ran from the repaired publication gate at `4da014fee`, using
  `/tmp/vun-final-suffix2.log`, and stopped with the environment failure described
  above. `/tmp/vun-native-env-smoke.log` records four passes after supplying
  the exact parsers. `/tmp/vun-final-native.log` records 2,422 passed, 15 skipped,
  12 passing subtests and the missing-generated-bundle failure described above.
  `/tmp/vun-final-bundle-build.log` retains the standard build command;
  `/tmp/vun-final-bundle.log` records 1,533 passed, one collection skip and the
  missing Node dependency failure described above. `/tmp/vun-final-browser.log`
  records 854 passed and the repeated collection-only skip. The accepted final
  receipt retains every invocation separately and proves the ordered coverage
  union without describing partial commands as complete passes.
- `/tmp/vun-copy-pending-green2.log` records 19 passed for the final helper,
  including pending-receipt and inconsistent-reservation copy refusal/reconcile.
- Independently verified the Roads descriptor changes only its two current
  source hashes and appends two explicit reviews; its SHA-256 is
  `4c72276eb683317fd248f379d379f7d0be97cae0671130a2c880a5a1fd61e44d`.
  All historical report/results/provenance files and prior review entries are
  byte- or structurally unchanged. The exact reviewed-delta mapping now matches
  all 100 source fingerprints.
- Independently rehashed all nine final-receipt logs and JUnit files, recomputed
  every per-run outcome count, matched all 113 source hashes to committed Git
  contents and container files, and recomputed complete node coverage with only
  explicit checkout prefixes normalized in parameter IDs. No node is missing;
  every earlier failure has a passing result at the final source.
- Document lint and spelling-normalization preview pass for this review artifact.
