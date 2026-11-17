# Roads code quality refactor tracker

**Status**: Open; execution started; M1 baseline in progress
**Updated**: 2026-11-17 22:37 UTC

## Task Board

- [x] Inspect controller, existing helpers, contracts, and test entry points.
- [x] Record measured baseline and bounded extraction map.
- [x] Create package and active ExecPlan on isolated task branch.
- [ ] M1: Characterize facade, persistence, failure, and artifact behavior.
- [ ] M2: Extract input parsing and preparation orchestration.
- [ ] M3: Extract native writers and design-specific execution stages.
- [ ] M4: Extract PASS routing, accounting/publication, and queries.
- [ ] M5: Complete parity evidence, reviews, documentation, and quality assessment.

## Decisions

2026-11-17 22:37 UTC: Prepare the work package in response to the request; implementation remains pending. Preserve behavior through faithful extraction, keeping the `Roads` facade and current lock/persistence placement. Use current measured 5,907 SLOC rather than the earlier 5,834 figure. Reuse existing Roads collaborators.

2026-11-17 22:37 UTC: Quality bands guide decomposition and remain observe-only under root AGENTS. Runtime/artifact parity and review findings are hard acceptance gates. Record residual quality debt explicitly; do not disguise relocation as decomposition.

## Risks and open evidence

Native-project source availability and the candidate container identity are not yet verified. Host complexity measurement is unavailable. Existing native-suite documentation has stale unrutted negative-case wording; characterize the current source before choosing positive/negative fixtures. Shared checkout has unrelated WIP; work is isolated at `/home/workdir/wepppy-roads-code-quality` on `codex/roads-code-quality-package`.

## Verification

Planning measurements are in [baseline.md](artifacts/baseline.md). All four package Markdown files plus root AGENTS and PROJECT_TRACKER passed `wctl doc-lint` using individual absolute file paths (six files, zero errors/warnings). Spelling previews and `git diff --check` were clean; root AGENTS size gate passed at 160 lines. Relative directory lint inspected zero files; absolute directory lint reported file-resolution errors, so neither directory invocation counted as validation. Individual absolute paths avoided that wrapper/path issue. No runtime implementation or runtime test result is claimed.

## Next action

Execute M1 in the [active plan](prompts/active/roads_code_quality_refactor_execplan.md). Recheck source drift and relevant instructions first. Use one writer per source file and one integrator. Keep this tracker and the plan current at each milestone.

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
