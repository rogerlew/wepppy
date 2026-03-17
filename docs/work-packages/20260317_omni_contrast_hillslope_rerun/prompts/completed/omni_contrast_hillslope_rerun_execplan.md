# Omni Contrasts: Hillslope Source Recovery for `delete_after_interchange`

## Outcome Summary (Completed 2026-03-17)

Implemented in `wepppy/rq/omni_rq.py`: before enqueuing contrast child jobs, `run_omni_contrasts_rq` now reruns hillslopes (no prep, no interchange) for deduped scenario working directories referenced by the finalized contrast `run_ids`, gated by `delete_after_interchange`. Regression tests were added in `tests/rq/test_omni_rq.py` for delete-flag on/off behavior, and targeted + full-suite validation passed.

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Users can run Omni scenarios with `delete_after_interchange=true`, but Omni contrasts then fail because contrast watershed stubs require `{wepp_id_path}.pass.dat` files that were deleted after interchange cleanup. This change restores reliable contrast execution by adding a preflight step in `run_omni_contrasts_rq` that reruns hillslopes only (no prep, no interchange) for the scenarios used by queued contrasts.

After this change, a run configured with `delete_after_interchange=true` can execute Omni contrasts end-to-end without manual scenario rebuilds.

## Progress

- [x] (2026-03-17 16:55Z) Reviewed root/package planning guidance and traced Omni contrast execution path.
- [x] (2026-03-17 16:55Z) Verified contrast watershed stubs depend on hillslope PASS sources and cleanup deletes them in delete-after mode.
- [x] (2026-03-17 16:55Z) Authored work-package docs and initial active ExecPlan.
- [x] (2026-03-17 17:20Z) Implemented rerun preflight helpers in `wepppy/rq/omni_rq.py`.
- [x] (2026-03-17 17:24Z) Wired rerun preflight into `run_omni_contrasts_rq` before enqueue fan-out.
- [x] (2026-03-17 17:34Z) Added regression tests in `tests/rq/test_omni_rq.py` for delete-flag on/off and dedupe behavior.
- [x] (2026-03-17 18:38Z) Corrected scenario rerun invocation to pass base-run `cli/slp` relpaths for pre-existing Omni scenario workspaces.
- [x] (2026-03-17 19:05Z) Extracted shared helper `_hillslope_input_relpath_to_base_runs` and reused it in scenario orchestration + contrast rerun preflight.
- [x] (2026-03-17 19:05Z) Added explicit rerun input preflight diagnostics (`missing_hillslope_inputs`) and regression tests for input-contract edge cases.
- [x] (2026-03-17 17:39Z) Ran `wctl run-pytest tests/rq/test_omni_rq.py --maxfail=1` successfully (`12 passed`).
- [x] (2026-03-17 17:44Z) Ran changed-file broad-exception guard successfully after allowlist line-anchor sync.
- [x] (2026-03-17 18:11Z) Ran full suite `wctl run-pytest tests --maxfail=1` successfully (`2323 passed, 34 skipped`).
- [x] (2026-03-17 18:20Z) Closed package docs and moved this ExecPlan to `prompts/completed`.

## Surprises & Discoveries

- Observation: Contrast watershed stubs consume raw hillslope PASS files, not interchange parquet.
  Evidence: `wepp_runner/wepp_runner.py::make_watershed_omni_contrasts_run` writes hillstub entries as `{wepp_id_path}.pass.dat`.

- Observation: Interchange cleanup intentionally removes hillslope source outputs needed by contrasts.
  Evidence: `wepppy/wepp/interchange/hill_interchange.py::cleanup_hillslope_sources_for_completed_interchange` unlinks `H*.pass.dat` and related files.

- Observation: Broad-exception allowlist line anchors for `wepppy/rq/omni_rq.py` drifted after inserting new helper code.
  Evidence: `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` initially flagged unsuppressed catches until allowlist line numbers were synchronized.

- Observation: Existing Omni scenario directories may intentionally omit local `p*.slp` and rely on relpaths back to base runs.
  Evidence: `omni_run_orchestration_service.py` scenario execution sets `cli_relpath/slp_relpath` from base runs; default `run_hillslopes()` in preflight caused `wepp_runner.py` assert on missing local scenario `p*.slp`.

## Decision Log

- Decision: Place recovery logic in `run_omni_contrasts_rq` orchestration before contrast child jobs are enqueued.
  Rationale: This is where the final queued contrast set is known and where one deduped preflight pass can be guaranteed.
  Date/Author: 2026-03-17 / Codex.

- Decision: Gate rerun preflight on `delete_after_interchange`.
  Rationale: The failure mode exists only when cleanup removes hillslope source outputs.
  Date/Author: 2026-03-17 / Codex.

- Decision: Recovery path runs `Wepp.getInstance(...).run_hillslopes()` only and does not invoke prep/interchange.
  Rationale: User explicitly required no prep and no interchange regeneration.
  Date/Author: 2026-03-17 / Codex.

- Decision: Select rerun targets from finalized `run_ids` and dedupe scenario keys.
  Rationale: Preserves current skip semantics and avoids redundant reruns for shared scenarios.
  Date/Author: 2026-03-17 / Codex.

## Outcomes & Retrospective

Outcome achieved:
- `run_omni_contrasts_rq` now regenerates hillslope source files required by contrast watershed stubs when `delete_after_interchange` is enabled, before queue fan-out.
- Scenario reruns now align with Omni scenario execution semantics by passing base-run relpaths for `cli/slp` inputs.
- Implementation remains minimal and non-invasive: no new queue topology, no prep calls, no interchange calls.
- Regression coverage validates deduped reruns, ordering before enqueue, and disabled-path no-op behavior.

Validation outcome:
- Targeted tests pass: `wctl run-pytest tests/rq/test_omni_rq.py --maxfail=1` -> `12 passed, 4 warnings`.
- Targeted tests pass after review follow-ups: `wctl run-pytest tests/rq/test_omni_rq.py --maxfail=1` -> `14 passed, 4 warnings`.
- Scenario orchestration tests pass after shared-helper refactor: `wctl run-pytest tests/nodb/mods/test_omni_run_orchestration_service.py --maxfail=1` -> `7 passed, 2 warnings`.
- Broad-exception guard pass (after allowlist line-anchor sync).
- Full suite pass: `wctl run-pytest tests --maxfail=1` -> `2323 passed, 34 skipped, 175 warnings`.

Remaining gaps:
- None for scoped package requirements.
- Optional future enhancement remains: reuse rerun helper in non-RQ direct Omni contrast execution paths.

## Context and Orientation

The implementation touches:

- `wepppy/rq/omni_rq.py`
  - `run_omni_contrasts_rq` now invokes a new preflight helper before enqueue.
  - New helpers:
    - `_collect_contrast_scenario_keys_for_run_ids`
    - `_contrast_scenario_run_wd`
    - `_rerun_hillslopes_for_contrast_scenarios`

- `tests/rq/test_omni_rq.py`
  - Added tests for delete-flag-enabled deduped reruns and delete-flag-disabled no-rerun behavior.

- `docs/standards/broad-exception-boundary-allowlist.md`
  - Updated existing `omni_rq.py` line anchors to match shifted file positions.

Scenario key/path rules in this implementation:
- Base scenario key -> run root working directory (`omni.wd`).
- Non-base key -> `_pups/omni/scenarios/<scenario_key>` under `omni.wd`.
- Missing scenario directory raises `FileNotFoundError` (explicit failure; no silent fallback).

## Plan of Work

Milestone 1 (completed): Add internal rerun helpers in `wepppy/rq/omni_rq.py` to collect deduped scenario keys from `run_ids`, resolve scenario WDs, and rerun hillslopes only.

Milestone 2 (completed): Invoke rerun preflight in `run_omni_contrasts_rq` after `run_ids` selection and before contrast child enqueue.

Milestone 3 (completed): Add regression tests in `tests/rq/test_omni_rq.py` for delete-flag gate and dedup/ordering behavior.

Milestone 4 (completed): Execute validation gates and close package docs/tracker.

## Concrete Steps

Run from `/workdir/wepppy`.

1. Implemented helper + orchestration edits.

    edit wepppy/rq/omni_rq.py

2. Added tests.

    edit tests/rq/test_omni_rq.py

3. Ran validation.

    wctl run-pytest tests/rq/test_omni_rq.py --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    wctl run-pytest tests --maxfail=1

4. Closed package docs.

    edit docs/work-packages/20260317_omni_contrast_hillslope_rerun/package.md
    edit docs/work-packages/20260317_omni_contrast_hillslope_rerun/tracker.md
    mv prompts/active/omni_contrast_hillslope_rerun_execplan.md -> prompts/completed/omni_contrast_hillslope_rerun_execplan.md
    edit AGENTS.md
    edit PROJECT_TRACKER.md

## Validation and Acceptance

Acceptance criteria met:
- Delete-flag-enabled path reruns hillslopes for deduped scenario targets used by queued contrasts.
- Rerun preflight does not invoke prep or interchange generation.
- Contrast queue fan-out and finalize wiring remained unchanged.
- New targeted tests pass.
- Full repository pytest sweep passed in this change set.

## Idempotence and Recovery

- Preflight rerun is deterministic by user assumption and safe to repeat.
- Failures in scenario path resolution or WEPP hillslope execution fail explicitly and preserve normal RQ exception behavior.
- No destructive git/worktree commands were used.

## Artifacts and Notes

Key evidence snippets:

    wctl run-pytest tests/rq/test_omni_rq.py --maxfail=1
    -> 12 passed, 4 warnings

    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    -> PASS

    wctl run-pytest tests --maxfail=1
    -> 2323 passed, 34 skipped, 175 warnings in 346.29s

## Interfaces and Dependencies

No external API contract changes were introduced.

Internal dependencies used by implementation:
- `wepppy.nodb.mods.omni.Omni`
- `wepppy.nodb.core.Wepp`
- `omni._contrast_scenario_keys(...)`
- `omni._normalize_scenario_key(...)`

Queue topology remained unchanged (no new enqueue edges).

---
Revision Note (2026-03-17, Codex): Updated ExecPlan from active draft to completed state with implementation details, validation outcomes, and closure evidence after full end-to-end execution.
