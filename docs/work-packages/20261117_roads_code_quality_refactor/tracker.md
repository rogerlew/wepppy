# Roads code quality refactor tracker

**Status**: Open; implementation complete, broad acceptance unresolved
**Updated**: 2026-11-18 UTC

## Task Board

- [x] Inspect controller, existing helpers, contracts, and test entry points.
- [x] Record measured baseline and bounded extraction map.
- [x] Create package and active ExecPlan on isolated task branch.
- [x] M1: Characterize facade, persistence, failure, and artifact behavior.
- [x] M2: Extract input parsing and preparation orchestration.
- [x] M3: Extract native writers and design-specific execution stages.
- [x] M4: Extract PASS routing, accounting/publication, and queries.
- [ ] M5: Complete parity evidence, reviews, documentation, and quality assessment.

## Decisions

2026-11-17 22:37 UTC: Prepare the work package in response to the request; implementation remains pending. Preserve behavior through faithful extraction, keeping the `Roads` facade and current lock/persistence placement. Use current measured 5,907 SLOC rather than the earlier 5,834 figure. Reuse existing Roads collaborators.

2026-11-17 22:37 UTC: Quality bands guide decomposition and remain observe-only under root AGENTS. Runtime/artifact parity and review findings are hard acceptance gates. Record residual quality debt explicitly; do not disguise relocation as decomposition.

## Risks and open evidence

Native/project parity and source reviews are complete: all 516 native profiles and five project controls match baseline, including a second 6,192-file comparison from the final-source v3 run. RUPC-02 wording is reconciled with operator approval; measured complexity and residual hotspots are in artifacts/quality_metrics.md. V5 completed with failures. Replacement qualification passes all 391 tests across 17 modules. Exact reconciliation accounts for all 15,104 unique nodes: 14,582 passed, 505 runtime skipped, nine failed and eight setup errors, plus one separate collection skip. M5 remains open because broad acceptance has not passed. Baseline missing generated bundles, incomplete Jinja fixture globals, missing browser dependencies and PostgreSQL schema mismatch, plus load-sensitive catalog latency, prevent a broad-green claim. Broad evidence is composite across processes and partly different environments; it is not an uninterrupted canonical-suite pass. Work remains isolated at `/home/workdir/wepppy-roads-code-quality` on `codex/roads-code-quality-package`.

## Verification

Planning measurements are in [baseline.md](artifacts/baseline.md). All four package Markdown files plus root AGENTS and PROJECT_TRACKER passed `wctl doc-lint` using individual absolute file paths (six files, zero errors/warnings). Spelling previews and `git diff --check` were clean; root AGENTS size gate passed at 160 lines. Relative directory lint inspected zero files; absolute directory lint reported file-resolution errors, so neither directory invocation counted as validation. Individual absolute paths avoided that wrapper/path issue. This paragraph records the original planning gate; runtime results follow below.

## Next action

The integrator leaves M5 open: the broad regression gate is unsuccessful. See `artifacts/broad_final_reconciliation.json` for exact outcomes and retained limitations. Resolve the recorded baseline runtime/fixture/schema prerequisites in their owning scope, then qualify all affected modules with source and environment receipts; investigate the latency failure under representative load. A future acceptance decision must preserve the mixed-process, mixed-environment and original source-drift qualifications. No unrelated production fixes or shared database/schema changes are included here. Continue from the [active plan](prompts/active/roads_code_quality_refactor_execplan.md).

## Completion states

Package scaffold: prepared. Refactor local acceptance: pending. Remote integration: not attempted. Publication/deployment: not included.

## M1 / M2 checkpoint - 2026-11-17 UTC

The dated checkpoint sections preserve the state at each earlier stage; current
open work is stated above and in the latest acceptance update below.

Contract reconciliation checkpoint: `efc0f642b`. Two independent reviews accepted
RUPC-02 as existing authority before source edits. Baseline matrix: 527 tests
passed, including 516 native profiles. Focused immutable baseline: 407 passed,
one skipped, two existing fixture admission failures. The stale consumer fixture
now creates missing prepared GeoJSON as a valid empty FeatureCollection; populated
files remain untouched. M2 input extraction with repaired fixture: 305 passed,
one skipped. Preparation extraction: 31 passed (61 unrelated tests deselected). Immutable
full-project baseline controls remain in progress. Complexity remains unavailable in both host
and existing container; no dependency installed.

M3 writers/spatial checkpoint: 251 focused tests passed. AST body comparison
against the original commit confirms identical bodies for 55 extracted methods
(including M2 input helpers); runtime parity remains the acceptance authority.
Execution decomposition is being prepared separately for integration.

M4 checkpoint: queries, retained parameterization support, PASS/workspace staging,
native runner and report/accounting helpers extracted. Expanded controller, RQ,
route and lifecycle selection: 390 passed, one skipped. Native/project parity
and final reviews remain mandatory after execution decomposition.

M3 execution checkpoint: the integrated execution decomposition passes 390 focused
tests, one skipped. The facade method is 269 lines versus 2,069. Independent
correctness source review accepts with no medium/high findings. QA identified
missing mixed-design accumulator coverage; a focused regression is in progress.
Security requested direct evidence for the new bounded sanitized warning on the
legacy diagnostic-list continuation path; tests are prepared. Both remain open
until their candidate test receipts pass.

## Final acceptance progress - 2026-11-17 UTC

Production source checkpoint: `5ef264810`. Mixed execution and direct sanitized
diagnostic tests pass (4/4), closing the two review coverage gaps. All 143 facade
signatures/decorators remain unchanged. Source reviews have no medium/high
findings. The ordinary archive test fixture required isolation from inherited
vector-retention settings: the broad run's RecordingRedis.eval failure reproduced
on the original 96555f2f9 baseline; the bounded fixture correction passes 73 tests.
No production archive/retention behavior changed. The broad suite is rerunning
with read-only shared Git metadata mounted for worktree-aware repository checks.
Candidate native validation passed 527 tests (516 profiles); all 6,192 native
files are byte-identical and all 516 parsed scientific summaries match. All five
project controls match across 4,577 artifact comparisons, with 92 parquet
field-metadata schema checks. Historical publication checks pass (3 tests),
retaining original report/results/provenance and explicit stale status. Broad
validation remains pending.

Second broad run: 1,769 passed, 41 skipped, one inherited fork-route fixture
failure (`DummyRedis.sismember`), reproduced on immutable baseline. The analogous
test-only environment isolation correction passes all 65 route tests and is
independently reviewed, committed as `43cb4e78f`. Third broad run in progress.
Final focused Roads selection passes 413 tests, one skipped. All 37 frozen
Roads source hashes match the tested snapshot and committed `d6ecf9a2a`.

Third broad run: 3,341 passed, 155 skipped (including one collection skip), three
subtests passed, and one Geneva archive-fixture failure in 1,768.48 seconds.
The immutable baseline reproduces the same inherited retention configuration
failure. All three direct ArchiveRuntime test consumers are being checked as a
failure class. After bounded test-only corrections, the remaining broad inventory
will run from the first Geneva-module item under an independently reviewed,
source-qualified continuation. This is composite coverage, not a claim of one
uninterrupted green suite; the plan records the cross-process limitation.

## Canonical environment qualification - 2026-11-18 UTC

The global `/tmp` retention-root override was itself responsible for an Omni
fake-Redis failure; baseline and candidate both pass with canonical `dev-wc1,/wc1`.
Roads and four prefix upload fixtures now explicitly declare local filesystem
scope. Canonical Roads focused validation passes 413 tests, one skipped; all 537
environment-sensitive prefix items are retained individually (508 passed,
29 skipped), with unchanged source hashes and complete phase outcomes. These
replace their earlier v3 results. Independent QA accepts the bounded fixture
changes and exact union: 2,947 unchanged v3-prefix items + 537 canonical-prefix
items + 11,620 canonical-suffix items = 15,104. Subsequent observer and fixture
qualification split that suffix into the completed segments and active diagnostic
below; the total inventory is unchanged.


## Current acceptance update - 2026-11-18 UTC

The v2 observer encountered a test's temporary `Path.open` patch. Ordinary pytest
passed the full eight-test derived-signature module; a fresh guarded process
verified all 2,836 source fingerprints unchanged at checkpoint `5a6e45c4`.
QA accepts 2,521 complete v2 items before that module (2,518 passed, three skipped).
The buffered v3 observer then passed all eight module cases with complete phase
receipts. See [continuation review](artifacts/broad_continuation_review.md) and
[post-exit qualification](artifacts/observer_v2_postexit_qualification.json).

The v3 run regenerated all 516 native cases from final Roads source. The
[final-source comparison](artifacts/final_source_matrix_comparison.json) confirms
all 6,192 native input/output files are byte-identical to baseline. Its reusable
segment contains 2,246 complete items (2,170 passed, 76 runtime skipped); the
shared-batch-queue failure is excluded. Read-only inspection found four active
workers, and the original test matched baseline bytes. The reviewed private-queue
fixture passes both recovery tests while preserving real Redis operations;
its logical-name alias limitation is explicit. The next ordinary batch-deletion
fixture failure reproduced on baseline; its local environment reset passes all
five module cases. No production changes or worker stops occurred. Details are in
[queue isolation](artifacts/batch_queue_fixture_isolation.md) and
[batch-deletion isolation](artifacts/batch_delete_fixture_isolation.md).

V5 completed the 6,853-item suffix with `--maxfail=0`: pytest reported 6,365
passed, 208 failed, 273 skipped and eight errors in 967.84 seconds. These summary
counts do not replace the observer's exact item/phase accounting. Partial v4
outcomes remain excluded. The original inventory remains 2,947 original-prefix +
537 canonical-prefix + 2,521 v2 + 2,246 v3 + 6,853 v5 items = 15,104 unique nodes.

Baseline probes reproduced missing shape-parser artifacts and 13 of the 14
non-shape failures, plus the representative PostgreSQL setup error. The isolated
baseline latency case passed, leaving its full-suite behavior inconclusive. Two
ordinary deletion fixture corrections at `5812caa02` pass all 50 module tests;
dedicated retention cases remain unchanged. The import sweep's sole source drift,
an added null management JSON field, was preserved, reproduced on copied input,
and restored to exact HEAD/baseline bytes. See
[non-shape assessment](artifacts/nonshape_failure_class_assessment.md),
[source-drift receipt](artifacts/management_sidecar_drift_receipt.json), and
[parser diagnostic](artifacts/shape_parser_environment_diagnostic.md).

The reviewed replacement passed all 391 tests across 17 modules in 55.79 seconds,
with all 1,173 phase records, no runtime skips and one separate collection skip.
Before/after source is identical; source, runtime and environment checks are clean.
QA is packaging final source/node substitutions; 17 failure/error nodes remain: one
generated-bundle failure, four Jinja fixture failures, three browser-dependency
failures, one latency failure and eight PostgreSQL setup errors. All 194 shape
failures, including the five GeoParquet cases, resolve in this replay using both
existing provenance-matched parser pairs mounted read-only. Missing generated JavaScript, Jinja
fixture globals, browser dependencies and PostgreSQL columns are confirmed
baseline limitations; load-sensitive catalog latency remains unresolved. M5 is
open, and neither baseline attribution nor the passing replacement establishes broad
acceptance.
