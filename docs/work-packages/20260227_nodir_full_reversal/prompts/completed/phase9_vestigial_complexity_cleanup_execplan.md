# Phase 9 ExecPlan: Vestigial Complexity Cleanup

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current while execution proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Phase 8 completed runtime migration and work-package closeout, but several compatibility-era surfaces still add cognitive load. This Phase 9 pass reduces that vestigial complexity without changing runtime behavior: legacy fallback logic is centralized, compatibility no-op flags are consolidated, and runtime-path module docs stop advertising retired NoDir compatibility as active design intent.

After this change, operators and maintainers can still open legacy runs and omni child paths as before, but the implementation is easier to reason about and future retirement points are explicit.

## Progress

- [x] (2026-02-28 05:52Z) Identified Phase 9 scope and validated that key legacy behaviors are still covered by unit tests (`tests/weppcloud/utils/test_helpers_paths.py`, `tests/runtime_paths/test_wepp_inputs_compat.py`).
- [x] (2026-02-28 05:52Z) Implemented behavior-preserving `get_wd` cleanup in `wepppy/weppcloud/utils/helpers.py` by extracting primary/legacy root and omni-child resolution helpers.
- [x] (2026-02-28 05:52Z) Consolidated no-op compatibility flag handling in `wepppy/runtime_paths/wepp_inputs.py`.
- [x] (2026-02-28 05:52Z) Updated runtime-path module docstrings to directory-only wording (`wepppy/runtime_paths/__init__.py`, `fs.py`, `projections.py`, `mutations.py`).
- [x] (2026-02-28 06:13Z) Ran validation gates and confirmed pass: targeted pytest, full pytest, broad-exception enforcement, code-quality observability, and package doc lint.
- [x] (2026-02-28 06:14Z) Ran cleanup review loop (`reviewer`, `test_guardian`) and resolved findings to unresolved high/medium = 0.
- [x] (2026-02-28 06:15Z) Published Phase 9 artifacts and updated tracker/package status.

## Surprises & Discoveries

- Observation: legacy run-root fallback and omni legacy candidate logic are explicitly covered by current helper-path tests, so we can refactor internals without changing behavior.
  Evidence: `tests/weppcloud/utils/test_helpers_paths.py` includes assertions for primary preference and legacy fallback paths.

- Observation: subagent review identified a medium test gap in omni-path “path exists” branches after refactor.
  Evidence: `test_guardian` flagged unresolved medium = 1 until new primary-hit and legacy-hit omni tests were added.

## Decision Log

- Decision: perform behavior-preserving refactor only, not compatibility removal.
  Rationale: current tests and prior manual validation indicate legacy run-opening remains operationally important; Phase 9 should reduce complexity without introducing migration risk.
  Date/Author: 2026-02-28 / Codex

- Decision: add explicit branch tests for refactored omni child path resolution before closing Phase 9.
  Rationale: required to clear subagent medium severity and to lock regression protection for both primary-hit and legacy-hit branches.
  Date/Author: 2026-02-28 / Codex

## Outcomes & Retrospective

- Phase 9 reduced vestigial complexity without changing runtime contracts by centralizing legacy path resolution, consolidating no-op compatibility flag handling, and tightening runtime-path module framing.
- Validation and subagent closure gates passed with unresolved high/medium = 0.
- Residual complexity intentionally retained: legacy run root fallback and legacy omni archive linking remain in place for operational compatibility.

## Context and Orientation

The main vestigial surfaces targeted by this phase are:
- `wepppy/weppcloud/utils/helpers.py`: run root resolution and omni child path fallback logic.
- `wepppy/runtime_paths/wepp_inputs.py`: compatibility-era optional parameters that are still accepted but no longer affect behavior.
- `wepppy/runtime_paths/{__init__,fs,projections,mutations}.py`: module framing text still emphasizing compatibility wrappers.

This phase does not remove legacy support paths outright; it focuses on code and docs maintainability while preserving existing contracts.

## Plan of Work

Phase 9 executes in three waves:

1. Refactor `helpers.get_wd` internals to centralize primary-vs-legacy and omni child path resolution into helper functions, preserving output behavior.
2. Refactor `wepp_inputs.py` no-op compatibility argument handling so unused flags are consumed through explicit helper functions rather than repeated inline tuple assignments.
3. Update work-package docs and publish a Phase 9 cleanup report with retained-vs-removed complexity inventory and validation evidence.

## Concrete Steps

Run from `/workdir/wepppy`:

1. `wctl run-pytest tests/weppcloud/utils/test_helpers_paths.py tests/runtime_paths/test_wepp_inputs_compat.py --maxfail=1`
2. `wctl run-pytest tests --maxfail=1`
3. `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
4. `python3 tools/code_quality_observability.py --base-ref origin/master`
5. `wctl doc-lint --path docs/work-packages/20260227_nodir_full_reversal`

Subagent loop:
1. `reviewer`
2. `test_guardian`
3. resolve findings until unresolved high/medium = 0

## Validation and Acceptance

Acceptance criteria:
- `get_wd` still prefers `/wc1/runs/<prefix>/<runid>` and falls back to `/geodata/weppcloud_runs/<runid>` when needed.
- Omni scenario/contrast grouped runids still resolve and continue to trigger shared-input symlink checks.
- Runtime-path compatibility signatures remain accepted, but compatibility no-op handling is explicit and centralized.
- Validation commands listed above pass.
- Subagent review loop reports unresolved high/medium = 0.

## Idempotence and Recovery

All edits are non-destructive refactors. If validation finds regressions, rollback is a standard `git revert` of Phase 9 commit(s). The test/doc commands are safe to rerun.

## Interfaces and Dependencies

No interface removals are allowed in this phase. Existing call signatures and route behavior remain unchanged. This phase depends on the current helper path tests and runtime-path compatibility tests as regression guardrails.
