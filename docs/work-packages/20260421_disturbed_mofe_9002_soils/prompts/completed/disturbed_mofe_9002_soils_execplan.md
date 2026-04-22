# Outcome (2026-04-22)

- Completed end-to-end: locked MOFE 9002 parity decisions, implemented class-aware lookup-miss keying, and documented intentional MOFE-specific fallback behavior.

- Added MOFE 9002 regression coverage (hit/miss/suffix/class-keying/area-pct) and passed required pytest gates (17 + 30 + 49).

- Executed config-level check for `disturbed9002-10-mofe` confirming `disturbed.sol_ver=9002.0` and `wepp.multi_ofe=true`.

---

# Disturbed MOFE 9002 Soil Support Parity Execution Plan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` are updated as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md` and is the active execution plan for `docs/work-packages/20260421_disturbed_mofe_9002_soils/`.

## Purpose / Big Picture

After this change, disturbed multi-OFE (MOFE) runs using `sol_ver=9002` will have explicit, regression-tested behavior for both lookup-hit and lookup-miss classes. The behavior is anchored to the existing single-OFE disturbed contract, with MOFE-only differences documented where the multi-OFE soil synthesizer requires same-version (`9002`) inputs across OFEs.

The observable outcome is that `Disturbed.modify_mofe_soils()` produces deterministic class-aware disturbed soil artifacts for `9002` runs, avoids unintended lookup-miss class collapsing, and continues to recompute area and percent coverage correctly.

## Progress

- [x] (2026-04-22 00:38 UTC) Loaded required context files and confirmed current single-OFE vs MOFE behavior gaps.
- [x] (2026-04-22 00:38 UTC) Locked parity decisions for MOFE `9002` lookup-hit and lookup-miss behavior with rationale (see Decision Log).
- [x] (2026-04-22 00:43 UTC) Implemented minimal `modify_mofe_soils` contract changes in `wepppy/nodb/mods/disturbed/disturbed.py`.
- [x] (2026-04-22 00:45 UTC) Added MOFE `9002` regression tests in `tests/nodb/mods/disturbed/test_modify_soils_mofe.py` for lookup-hit, lookup-miss, treatment normalization, class keying, and area/pct recomputation.
- [x] (2026-04-22 01:06 UTC) Updated disturbed/package/tracker documentation to reflect finalized contract and intentional MOFE-specific differences.
- [x] (2026-04-22 00:58 UTC) Ran required validation gates and recorded command outcomes.
- [x] (2026-04-22 01:05 UTC) Ran one config-level MOFE check (`disturbed9002-10-mofe`) and recorded evidence.
- [x] (2026-04-22 01:08 UTC) Updated `PROJECT_TRACKER.md` to reflect completion status and evidence summary.

## Surprises & Discoveries

- Observation: Current MOFE lookup-miss logic for `sol_ver=9002` injects an undocumented fallback replacement map and keys soils as `mukey-texid`, which can merge distinct disturbed classes into one generated soil key.
  Evidence: `wepppy/nodb/mods/disturbed/disturbed.py` in `modify_mofe_soils()` lookup-miss branch.

- Observation: Single-OFE lookup misses intentionally short-circuit to base `mukey`; MOFE cannot always do this directly for `9002` when a hillslope stack must be synthesized from same-version soils.
  Evidence: Single-OFE `modify_soil()` returns `mukey` on miss; `SoilMultipleOfeSynth.write()` asserts one soil version in stack.

- Observation: A config-level `Disturbed(...)` bootstrap check inside `wctl run-python` emits security-log directory permission warnings in this environment, but the disturbed controller still initializes and reports `sol_ver=9002.0`.
  Evidence: `wctl run-python` output includes `Security log file handler setup skipped due to errors` followed by successful printed config checks.

## Decision Log

- Decision: Lock lookup-hit parity to single-OFE behavior for MOFE `9002`.
  Rationale: Single-OFE is the reference contract. MOFE lookup hits will continue to normalize treatment suffixes for lookup keying (`lookup_disturbed_class`) while preserving full disturbed class in generated soil key names.
  Date/Author: 2026-04-22 / Codex

- Decision: For MOFE `9002` lookup misses, generate a class-specific migrated `9002` soil without lookup-table erodibility overrides, using explicit neutral metadata replacements (`luse`, `stext`, `ksatfac=0.0`, `ksatrec=0.0`) to keep migration deterministic and MOFE-stack-compatible.
  Rationale: Pure single-OFE miss semantics (return base `mukey`) can violate MOFE same-version synthesis requirements when other OFEs are converted to `9002`. This is an intentional MOFE-specific deviation required by `SoilMultipleOfeSynth` version-homogeneity constraints.
  Date/Author: 2026-04-22 / Codex

- Decision: Prevent lookup-miss class collapsing for MOFE `9002` by keying generated soils with the full disturbed class (`mukey-texid-disturbed_class`) rather than `mukey-texid`.
  Rationale: Distinct disturbed classes should not silently share one fallback artifact unless explicitly intended and documented.
  Date/Author: 2026-04-22 / Codex

## Outcomes & Retrospective

The implementation now explicitly locks MOFE `9002` lookup-hit and lookup-miss behavior while preserving non-`9002` paths. Lookup misses for `9002` now remain class-aware (`mukey-texid-disturbed_class`) and keep the explicit fallback replacement contract required to maintain same-version MOFE soil stacks.

Regression coverage was expanded to include all required `9002` MOFE contract dimensions (hit, miss, treatment suffix normalization, class keying, area/pct recomputation). Required test gates passed, and a config-level check against `disturbed9002-10-mofe.cfg` confirmed `sol_ver=9002` and `wepp.multi_ofe=true` at config text level with successful disturbed controller bootstrap.

## Context and Orientation

Relevant code path:

- `wepppy/nodb/mods/disturbed/disturbed.py`
  - `modify_soil()` is the single-OFE reference contract.
  - `modify_mofe_soils()` is the MOFE implementation under change.
- `wepppy/wepp/soils/utils/multi_ofe.py`
  - `SoilMultipleOfeSynth.write()` enforces one consistent soil version across stacked OFE inputs.
- `wepppy/wepp/soils/utils/wepp_soil_util.py`
  - `to_over9000(version=9002)` performs migration and replacement application.

Relevant tests:

- `tests/nodb/mods/disturbed/test_modify_soils_single_ofe.py` (reference behavior)
- `tests/nodb/mods/disturbed/test_modify_soils_mofe.py` (targeted MOFE regression coverage)
- `tests/nodb/mods/disturbed/test_lookup_contract.py`
- `tests/wepp/soils/utils/test_wepp_soil_util.py`

Work-package artifacts to keep current:

- `docs/work-packages/20260421_disturbed_mofe_9002_soils/package.md`
- `docs/work-packages/20260421_disturbed_mofe_9002_soils/tracker.md`
- `PROJECT_TRACKER.md`

## Plan of Work

Implement the smallest behavior change inside `Disturbed.modify_mofe_soils()` needed to codify the locked `9002` contract. Preserve existing behavior for non-`9002` versions unless needed for correctness.

Add focused unit tests in `test_modify_soils_mofe.py` that pin each required contract dimension:

- lookup-hit path in `9002`
- lookup-miss path in `9002`
- treatment suffix normalization for lookup keying
- class-aware keying on miss to avoid unintended collapse
- area/pct_coverage recomputation

Then update package/tracker and disturbed docs to document the intentional MOFE-only lookup-miss deviation, run the required validation gates, and capture command outcomes.

## Concrete Steps

From repository root (`/workdir/wepppy`):

1. Edit implementation and tests.
2. Run required gates:
   - `wctl run-pytest tests/nodb/mods/disturbed/test_modify_soils_single_ofe.py tests/nodb/mods/disturbed/test_modify_soils_mofe.py --maxfail=1`
   - `wctl run-pytest tests/nodb/mods/disturbed/test_lookup_contract.py --maxfail=1`
   - `wctl run-pytest tests/wepp/soils/utils/test_wepp_soil_util.py --maxfail=1`
3. Run one config-level MOFE check and record result.
4. Update docs/tracker/project tracker with final evidence.

## Validation and Acceptance

Acceptance requires all of the following:

- MOFE `9002` lookup-hit and lookup-miss behavior is explicit in code and verified in tests.
- MOFE `9002` lookup-miss does not unintentionally collapse distinct disturbed classes into one key.
- MOFE area and percent coverage recomputation remains correct.
- Required pytest gates pass.
- A config-level MOFE check (`disturbed9002-10-mofe` or `disturbed9002-wbt-mofe`) is executed and recorded.
- Package/tracker/PROJECT_TRACKER entries reflect final state with evidence.

## Idempotence and Recovery

The planned edits are additive and localized. Re-running tests is safe and expected. If a validation gate fails, iterate on the failing path and re-run only affected gate(s) first, then re-run the full required gate list.

## Artifacts and Notes

- `wctl run-pytest tests/nodb/mods/disturbed/test_modify_soils_single_ofe.py tests/nodb/mods/disturbed/test_modify_soils_mofe.py --maxfail=1`
  - Result: `17 passed`.
- `wctl run-pytest tests/nodb/mods/disturbed/test_lookup_contract.py --maxfail=1`
  - Result: `30 passed`.
- `wctl run-pytest tests/wepp/soils/utils/test_wepp_soil_util.py --maxfail=1`
  - Result: `49 passed`.
- `wctl run-python -- - <<'PY' ... Disturbed(temp_wd, disturbed9002-10-mofe.cfg) ... PY`
  - Result: printed `disturbed.sol_ver=9002.0` and `config.wepp.multi_ofe=true (text-level check)`.

## Interfaces and Dependencies

No new external dependencies. Existing interfaces and modules are preserved:

- `Disturbed.modify_mofe_soils()` contract in `wepppy/nodb/mods/disturbed/disturbed.py`
- `lookup_disturbed_class()` lookup normalization
- `WeppSoilUtil.to_over9000(..., version=9002)` migration behavior
- `SoilMultipleOfeSynth` same-version stack synthesis requirement

---

Revision note (2026-04-22 00:38 UTC): Created active ExecPlan and locked `9002` parity decisions prior to implementation.
Revision note (2026-04-22 01:08 UTC): Marked implementation/test/doc milestones complete and recorded validation/config-check evidence.
