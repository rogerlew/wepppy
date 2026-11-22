# Refactor Roads controller tests by responsibility

This ExecPlan is a living document maintained under
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose

Give Roads maintainers a single test target with focused modules for upload,
preparation, execution, inspection, and parameterization. Preserve the coverage
of the original controller module while making the orchestration scenarios easier
to review.

## Progress

- [x] (2026-11-22 05:08 UTC) Created branch `refactor/roads-controller-tests`
  from `782552bde21186e2327caa3540a16ce943f8cb27` and scoped the package.
- [x] Capture baseline metrics and focused results. All 92 cases passed.
  Measured 3,543 source lines, 285 lines in the longest function, and a
  maximum cyclomatic complexity of 41 with Radon 6.0.1.
- [x] Organize cases and shorten orchestration setup. All replacement modules
  are below the quality tool's red thresholds.
- [x] Verify parity, review, and close the package locally on 2026-11-22 UTC.

## Surprises & Discoveries

The original module mixes direct NoDb state tests with orchestration scenarios
that simulate native WEPP and write artifacts for downstream assertions. The
longest scenarios repeat file setup and monkeypatches. One channel scenario
replaced its first PASS combiner callback before entering the controller.
The extraction removed that dormant callback and preserved the effective one.

## Decision Log

On 2026-11-22 UTC, Codex chose a dedicated directory so a single pytest path
continues to select the whole set after the split. Keep scenario-specific
behavior and the assertions in the tests. Extract common setup where it has
the same contract across cases. Use a Python package initializer and relative
support imports so the refactored configuration cases collect alongside
`tests/weppcloud/test_configuration.py`.

## Outcomes & Retrospective

All 92 cases passed with matching JUnit outcomes and parameterized names.
Mixed-directory collection passed. The replacement modules total 3,050 source
lines. Their maxima are 553 source lines per file, 146 lines per function, and
29 cyclomatic complexity. Independent source review accepted the extraction.

## Plan of Work

From the task worktree, run the original module through `wctl` and measure its
source with `tools/code_quality_observability.py`. Move related test cases
from `tests/nodb/mods/test_roads_controller.py` into
`tests/nodb/mods/roads_controller/`. Keep test names, markers, parameter values
and IDs, artifact assertions, and stub behavior. Reduce the longest setup
sections using named shared or scenario-local helpers. Preserve per-test
temporary directories and monkeypatch scoping.

## Concrete Steps

Use these repository-relative commands from the corresponding worktree state.

    wctl run-pytest --profile python -- tests/nodb/mods/test_roads_controller.py -q
    wctl run-pytest --profile python -- tests/nodb/mods/roads_controller -q
    wctl run-pytest --profile python -- tests/nodb/mods/roads_controller tests/weppcloud/test_configuration.py --collect-only -q

Compare collected test identifiers by function and parameter suffix to allow
the expected file path change. Review all moved and extracted assertions,
measure each candidate file, and update `wepppy/nodb/mods/roads/README.md`
with the new selector. Lint the changed Markdown with `wctl doc-lint`.

## Validation and Acceptance

The original and replacement selectors must cover the same cases with matching
outcomes. Review the extraction for unchanged test inputs, fake native behavior,
and exact artifact readback. Use the quality tool's red thresholds of 1,200 source
lines, 150 lines per function, and cyclomatic complexity of 30 to evaluate the
decomposition. The user scoped regression execution to the affected tests.

## Recovery and evidence

The base commit retains the original test suite. Repeat focused validation on the
task worktree after any review fix. Record commands and outcomes in the tracker
and [validation record](../../artifacts/validation.md).

On 2026-11-22 UTC, this plan moved to `prompts/completed/` after the
focused gates passed and independent review accepted the source.
