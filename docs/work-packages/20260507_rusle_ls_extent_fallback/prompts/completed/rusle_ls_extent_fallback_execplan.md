# RUSLE LS Extent Reversion and Conservative No-Flow Fallback

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, `wepppy` will run `RusleLsFactor` across the full map extent by default (no implicit outside-watershed LS blocking mask), and `RusleLsFactor` will tolerate small interior no-flow defects using a conservative single-cell correction fallback while still failing fast for larger DEM quality issues.

## Progress

- [x] (2026-05-07 17:02Z) Created work package and active ExecPlan.
- [x] Removed watershed-boundary LS blocking-mask generation/wiring in `wepppy` `Rusle` controller.
- [x] Updated `wepppy` controller tests for full-extent LS behavior.
- [x] Implemented bounded conservative fallback in `RusleLsFactor` for small interior no-flow defects.
- [x] Added fallback metadata fields in `RusleLsFactor` outputs.
- [x] Updated RUSLE LS specification and package tracker with final contract details.
- [x] Ran and recorded QA checks in `wepppy` and `weppcloud-wbt`.
- [x] Finalized package closeout sections and archived ExecPlan to `prompts/completed/`.

## Surprises & Discoveries

- Observation: The watershed confinement behavior was entirely in `wepppy` orchestration (`_resolve_ls_blocking_mask_path`) rather than the Rust `RusleLsFactor` core.
  Evidence: `wepppy/nodb/mods/rusle/rusle.py` helper and call-site wiring.

## Decision Log

- Decision: Keep fallback automatic only when defects are small relative to eligible interior cells and hard-capped by count.
  Rationale: Satisfies robustness request while preserving conservative behavior and explicit failure for likely unconditioned DEMs.
  Date/Author: 2026-05-07 / Codex

- Decision: Use `BreachSingleCellPits` as fallback method.
  Rationale: It minimally edits local terrain to open flow paths without broad depression filling.
  Date/Author: 2026-05-07 / Codex

## Outcomes & Retrospective

- Removed implicit outside-watershed LS blocking in `wepppy`; LS now defaults to full DEM/map extent unless callers provide explicit masks.
- Added conservative small-defect fallback in `RusleLsFactor` for DInf-derived SCA using `BreachSingleCellPits`, with strict fail-fast retained for larger/unresolved defects.
- Added metadata fields documenting no-flow guard/fallback state and thresholds.
- Updated specification and package docs so orchestration behavior and core-tool behavior remain aligned.
- Validation outcome:
  - `wctl run-pytest tests/nodb/mods/test_rusle_controller.py tests/nodb/mods/test_rusle_ls_integration.py --maxfail=1` -> `10 passed`
  - `cargo check -p whitebox_tools` -> passed
  - `cargo test -p whitebox_tools rusle_ls_factor -- --nocapture` -> `7 passed`
  - `python -m py_compile whitebox_tools.py WBT/whitebox_tools.py` -> passed
  - `wctl doc-lint` on updated docs -> `5 files validated, 0 errors, 0 warnings`

## Context and Orientation

Primary change locations:

- `wepppy/nodb/mods/rusle/rusle.py`: remove implicit outside-watershed LS blocking mask.
- `tests/nodb/mods/test_rusle_controller.py`: update controller expectations for no implicit blocking mask.
- `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/terrain_analysis/rusle_ls_factor.rs`: add small-defect fallback + metadata.
- `/workdir/weppcloud-wbt/whitebox_tools.py` and `/workdir/weppcloud-wbt/WBT/whitebox_tools.py`: wrapper docs.
- `wepppy/nodb/mods/rusle/specification.md`: document full-extent LS and fallback contract.

## Plan of Work

Implement the `wepppy` extent revert first to restore expected LS domain semantics. Then add a conservative fallback gate in `RusleLsFactor` that inspects interior no-flow counts for DInf-derived SCA; apply `BreachSingleCellPits` only when defect counts are within a bounded threshold, rerun no-flow validation, and continue only if cleared. Record fallback outcome in metadata for auditability.

## Concrete Steps

1. Edit `wepppy` controller and tests.
2. Edit `RusleLsFactor` Rust tool and wrapper docs.
3. Update RUSLE spec and package docs.
4. Run targeted QA:
   - `/workdir/wepppy`: `wctl run-pytest tests/nodb/mods/test_rusle_controller.py tests/nodb/mods/test_rusle_ls_integration.py --maxfail=1`
   - `/workdir/weppcloud-wbt`: `cargo check -p whitebox_tools`
   - `/workdir/weppcloud-wbt`: `cargo test -p whitebox_tools rusle_ls_factor -- --nocapture`
   - `/workdir/weppcloud-wbt`: `python -m py_compile whitebox_tools.py WBT/whitebox_tools.py`

## Validation and Acceptance

Acceptance criteria:

- `wepppy` no longer auto-generates an outside-watershed LS blocking mask.
- Rust tool still fails fast for large interior no-flow defect patterns.
- Rust tool succeeds for small-defect patterns when conservative fallback resolves no-flow cells.
- Metadata explicitly reports fallback/guard state.
- All targeted test/check commands pass.

## Idempotence and Recovery

All edits are additive and safe to rerun. If validation fails, fix forward and rerun targeted commands. No destructive git reset/checkouts are used.

## Artifacts and Notes

QA transcript summary will be recorded in:
- `docs/work-packages/20260507_rusle_ls_extent_fallback/artifacts/20260507_qa_review.md`

## Interfaces and Dependencies

- No new external dependencies.
- Reuse existing WBT hydrology tool `BreachSingleCellPits` for fallback.

Plan revision note (2026-05-07 17:09 UTC): Updated to completion state after implementation, validation, QA artifact capture, and package closeout.
