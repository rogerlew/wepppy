# Roads code quality refactor tracker

**Status**: Open; implementation complete, final acceptance in progress
**Updated**: 2026-11-17 UTC

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

Native source fixtures and isolated container identities are verified. RUPC-02 validation wording is reconciled with operator approval. Candidate native/project comparisons and the broad suite remain open. Complexity is measured using the existing /usr/bin/python interpreter with Radon; see artifacts/quality_metrics.md. Shared checkout has unrelated WIP; work is isolated at `/home/workdir/wepppy-roads-code-quality` on `codex/roads-code-quality-package`.

## Verification

Planning measurements are in [baseline.md](artifacts/baseline.md). All four package Markdown files plus root AGENTS and PROJECT_TRACKER passed `wctl doc-lint` using individual absolute file paths (six files, zero errors/warnings). Spelling previews and `git diff --check` were clean; root AGENTS size gate passed at 160 lines. Relative directory lint inspected zero files; absolute directory lint reported file-resolution errors, so neither directory invocation counted as validation. Individual absolute paths avoided that wrapper/path issue. This paragraph records the original planning gate; runtime results follow below.

## Next action

Complete M5 in the [active plan](prompts/active/roads_code_quality_refactor_execplan.md). Recheck source drift and relevant instructions first. Use one writer per source file and one integrator. Keep this tracker and the plan current at each milestone.

## Completion states

Package scaffold: prepared. Refactor local acceptance: pending. Remote integration: not attempted. Publication/deployment: not included.

## M1 / M2 checkpoint - 2026-11-17 UTC

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
