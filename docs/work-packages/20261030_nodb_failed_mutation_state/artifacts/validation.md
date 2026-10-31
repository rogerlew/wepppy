# NFMS-01 validation evidence

Checkpoint ancestor: `2b998e08d`, committed on existing master after operator
explicit approval and before production/conformance-test edits. Implementation
was validated as a working-tree candidate; the operator subsequently authorized
its commit and push. No deployment or production jobs.

## Direct failed-state and generated-input boundary

- Independent matrix: **36 passed, zero skips**, 11.69 seconds; actual disposable
  Redis coordination. `validation_matrix.md` maps fault/state/race cases.
- Real consumer module: **6 passed**, 16.06 seconds. Valid Wepp parser/decorator
  input then replace failure and real Soils missing-SSURGO domain failure retain
  accepted values through an unrelated edit and actual `prep_soil`.
  `wepp/runs/p101.sol` is parsed with `WeppSoilUtil`: kslast **0.02**, saturation
  **0.2**, never rejected **0.9**. Option tests parse actual `phosphorus.txt` and
  `gwcoeff.txt` after a later raster failure and corrected retry; retry applies
  **9.0** to the changed map option while preserving the others.
- Resource case: twelve failed real-controller mutations preserve all logging
  handler/queue/listener identities, listener remains alive, descriptors stay
  within baseline+1, and process exits normally.
- Manual boundary batch: **58 passed**; additional migration admission two cases
  and recovery/cancellation two cases passed. Real source bytes and durable
  selected-source metadata agree; committed derived files and unknown-outcome
  recovery backups retained. Counts overlap narrower runs and are not additive.
- Grouped recovery: **11 passed**, including compensation success/failure, newer
  writer, postcommit mutation and secondary KeyboardInterrupt/SystemExit cleanup.
- Additional prelock/centroid + culvert success: **27 passed**; expanded prelock
  and nested-clean suite **10 passed** (overlapping coverage).
- Base boundary/unit/misc plus Climate multiple-build: **139 passed**; final
  shared state cases plus base unit: **25 passed** (overlapping coverage).

First-draft tests exposed real issues in quarantine, delayed hydration, abandoned
ownership, identity and cancellation handling. These were corrected and retained
as regressions; final matrix and independent reviewer rereads pass. The initial
existing base gate stopped on its first-create test reading a quarantined object's
filename; assertion now uses class metadata and explicitly tests blocked state.

## WAM-01, MRS-01 and compatibility

Plain canonical focused command initially reported **164 passed, 71 skipped**:
transport/route conformance passed, Redis-backed persistence skipped because the
container has no redis-server binary. A host-installed, port-disabled disposable
server was started at `.pytest_cache/nfms-validation/redis.sock`, with the fixture's
`batch-boundary-test-server=disposable` guard. No dependency/container installed.

Rerun via `wctl exec -e RQ212_TEST_REDIS_SOCKET=/workdir/wepppy/.pytest_cache/nfms-validation/redis.sock`
in the same dev runtime executed `test_wepp_admission_persistence.py` and
`test_malformed_input_persistence.py`: **71 passed**, six existing warnings,
29.07 seconds. Matrix coordination uses this same isolated server and unique IDs.
No production queue or unrelated lock/cache was touched. Cleanup is recorded below.

Wepp parser/preparation compatibility: **86 passed**. Existing grouped unit tests:
**23 passed**; WEPP/bootstrap route modules: **135 passed**. Valid false/default,
admission leases, no-prep artifacts, replay, stale-write/atomic behavior, explicit
low-level retries and legacy reads retain dedicated coverage. No queue wiring,
scientific/default, on-disk schema, authentication or permission change.

## Required broad and tooling gates

- `wctl run-stubtest wepppy.nodb.base`: pass, one module.
- `wctl check-test-stubs`: pass; existing SyntaxWarning only.
- Changed broad-exception enforcement: pass, unsuppressed net delta **-3**.
- Code quality observability: command passed; observe-only, radon unavailable.
  Added shared recovery/ownership code is deliberate to enforce held references,
  coherent commit recovery and cancellation. Current base SLOC is 2610; working
  diff adds 345/removes 69 lines. No threshold waiver used. Changed-file metric
  deltas are unavailable: the tool uses `base_ref...HEAD` and ignores uncommitted
  implementation. Smallest tooling follow-up: an explicit working-tree comparison
  mode; no tool or dependency change was made for this task.
- Scoped documentation lint and `git diff --check`: pass at review preparation;
  final closeout rerun also passes.
- Performance baseline/candidate/final observations: `performance.md`; measured
  overhead and limitations explicitly retained.

The first NoDb and full attempts were intentionally interrupted after final fixes
landed, so they cannot validate the final source imported by those processes.
Interrupted NoDb: 240 passed/20 skipped, exit 2. Interrupted full: 400 passed/27
skipped, exit 2. These are not full passes or split completion evidence.
Final broad coverage is partitioned to avoid repeating the 230-case treatment
soil matrix. The NoDb attempt stopped after **2302 passed, 23 skipped, one failure**
(1907.79 seconds) at the existing RAP unknown-commit error contract. All 147 NoDb
module files had completed: **2133 passed, 23 skipped** (retained progress markers
in `nodb-broad-attempt.log`). The queued duplicate full invocation never started.

The derived helper had changed ordinary unknown-commit errors to their original
OSError plus note. Restore the existing _CommitOutcomeUnknown(RuntimeError),
chained from that OSError, while preserving direct cancellation propagation and
recovery artifacts. An initial missing class definition was caught by review and
focused failure (six passed, one failed), restored, and rerun successfully:
**51 passed** in `derived-followup.log`. Independent reviews reconfirm approval.
This is a bounded compatibility correction; shared base and scientific paths are
unchanged from the completed module prefix.

`wctl run-pytest tests --ignore=tests/nodb --maxfail=1`: **8669 passed, 343 skipped**,
647 warnings, 1445.44 seconds. This includes one collection skip (9011 executable
items collected); see `repository-complement.log`.
`wctl run-pytest tests/nodb --ignore=tests/nodb/mods --maxfail=1` ran after
the compatibility correction; its completed prefix and subsequent tail cover
all 1736 core NoDb items (see final partition accounting below).
This is split broad coverage, not an uninterrupted full-suite pass.

A two-case diagnostic with native thread limits passed (228 deselected), about
3.7 seconds per call; it did not establish a useful speedup. Final partitions use
the normal environment, not that diagnostic override. No production threading,
scientific parameter or test expectation was changed to accelerate validation.

## Reviews, scope and cleanup

Independent security and QA approve local code scope; correctness approves with code findings
resolved. Reviews are not substitutes for broad gates.
Consumer disposition is in `consumer_matrix.md` and `remaining_boundary_audit.md`.
Independent non-NoDbBase RunStatistics remains an unresolved separate boundary;
RedisPrep is not covered by NoDbBase recovery. No arbitrary external nested-alias,
full distributed rollback, process-crash or production recovery claim.

Disposable Redis guard rechecked as `disposable`; shutdown nosave exited zero,
socket removed by server, dedicated directory removed. No production Redis or
unrelated cache/lock cleanup. Final broad outcomes are recorded below; local validation is complete.

## TTL fixture clarification

The first core rerun stopped at 846 passed, two skipped, one failure: an old TTL
test used the same cached singleton to simulate a separate process. Use a distinct
detached controller and assert completion after persistence and the accepted
second writer in both memory and disk. Correctness and QA approved this test-only
clarification; no production change. The full race module passed 17 tests
(`ttl-compatibility.log`). The subsequent core attempt and completed tail are recorded below.

Prepared-input retention rerun: six passed, two warnings, 16.12 seconds
(`prepared-consumer.log`). `prepared_input_readback.json` retains fixture names,
exact relative paths, SHA-256 and independently parsed accepted values for three
regenerated soil inputs. All three hashes match; kslast=0.02, saturation=0.2.

## Filesystem fixture clarification

Second core attempt: 1301 passed, five skipped, one failure, 279.95 seconds
(`nodb-core-second-attempt.log`). Its completed prefix before the root-directory
module is 1299 passed/five skipped. That module used incomplete __new__ controllers
with islocked=True to bypass persistence; five filesystem-only doubles now use
the existing locked=nullcontext pattern. Real ownership tests remain unchanged.
Independent QA approves; focused filesystem/ownership modules: 17 passed.
The remaining partition starts with test_root_dir_materialization.py and includes
all lexically following core test modules. No production change after the prefix.

## Final partition accounting

| Non-overlapping partition | Passed | Skipped | Evidence |
| --- | ---: | ---: | --- |
| NoDb mods, 147 completed files | 2133 | 23 | nodb-broad-attempt.log prefix |
| Core NoDb before root-directory module | 1299 | 5 | nodb-core-second-attempt.log prefix |
| Core NoDb from root-directory module onward | 432 | 0 | nodb-core-tail.log, exit 0, 76.57 seconds |
| Repository excluding NoDb | 8669 | 343 | repository-complement.log, exit 0 |
| Total distinct coverage | 12533 | 371 | Split runs; includes one collection skip |

No uninterrupted full-suite pass is claimed. The failed root-directory attempt's
first two passes are excluded from prefix accounting because the entire seven-test
module reran in the tail. Focused retries and actual-Redis runs are supplemental,
not added to these totals. Existing skips remain; required 36-case mutation matrix
and 71 WAM/MRS actual-Redis cases separately passed without skips. Only reviewed
compatibility fixes followed the completed partitions; affected paths reran.

Independent correctness, security and QA approve the local scope. Source hashes
match candidate_manifest.json. Final API/stub, exception, docs and whitespace
gates pass; code-quality metric limitations remain as described above. Commit and push were authorized after validation. No deployment or production
recovery has been performed.

Retained pytest logs have trailing whitespace normalized for repository checks;
test results and diagnostics are unchanged.
