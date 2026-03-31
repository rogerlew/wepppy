# Disturbed Test Consolidation and Hardening

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` are maintained as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md` and is intended to be executable by a novice contributor using only this file plus the repository checkout.

## Purpose / Big Picture

After this change, disturbed-controller tests are consolidated into one coherent test suite under `tests/nodb/mods/disturbed/`, with shared fixtures and clear concern-based modules. The suite directly covers disturbed orchestration and mutation behavior for landuse/soils paths (`modify_soil`, `modify_soils`, `modify_mofe_soils`, `remap_landuse`, `remap_mofe_landuse`, `pmetpara_prep`, and `on(...)` routing), plus regression cases for lookup safety, treatment suffix behavior, parent-soil fallback, and area/coverage recomputation.

Observable outcomes are:
- Disturbed controller tests are no longer scattered in root `tests/nodb/mods/`.
- Required disturbed behaviors are directly exercised in unit tests.
- Minimal production hardening is present only where fail-before/pass-after tests justify it.
- Required validation commands pass.

## Progress

- [x] (2026-03-31 03:13Z) Loaded required guidance: root `AGENTS.md`, `wepppy/nodb/AGENTS.md`, `tests/AGENTS.md`, and `docs/prompt_templates/codex_exec_plans.md`.
- [x] (2026-03-31 03:13Z) Ran pre-edit explorer subagent pass and captured gap map for disturbed test coverage and consolidation targets.
- [x] (2026-03-31 03:13Z) Created and initialized this living ExecPlan document.
- [x] (2026-03-31 03:24Z) Consolidated disturbed tests into `tests/nodb/mods/disturbed/` with shared `conftest.py` and concern-based modules; removed replaced root-level disturbed test files.
- [x] (2026-03-31 03:25Z) Added direct unit coverage for required disturbed functions and edge cases: `modify_soil`, `modify_soils`, `modify_mofe_soils`, `remap_landuse`, `remap_mofe_landuse`, `pmetpara_prep`, and `on(...)` routing.
- [x] (2026-03-31 03:25Z) Applied minimal production hardening in disturbed controller for parent soil fallback, MOFE lookup suffix parity, and replacement dict copy safety.
- [x] (2026-03-31 03:29Z) Ran required validation commands and confirmed all pass.
- [x] (2026-03-31 03:29Z) Completed post-implementation QA/reviewer pass and dispositioned findings (no blocking issues; residual risks recorded).

## Surprises & Discoveries

- Observation: Disturbed controller tests are fragmented across multiple root-level files in `tests/nodb/mods/`, which obscures ownership and leaves critical controller paths untested.
  Evidence: Explorer inventory + direct scan found only lookup/SBS tests for disturbed; no direct tests for `modify_soil`, `modify_soils`, `modify_mofe_soils`, `remap_landuse`, `remap_mofe_landuse`, `pmetpara_prep`, or `on(...)`.

- Observation: Parent-soil fallback hardening changed disturbed soil source expectations in tests that previously relied on non-existent local source files.
  Evidence: Initial post-change run failed in `test_modify_mofe_soils_uses_base_lookup_class_for_treatments` with `FileNotFoundError`; fixture setup was updated to materialize `src.sol` in run-scoped soils dirs.

## Decision Log

- Decision: Consolidate only disturbed controller tests into `tests/nodb/mods/disturbed/`, while keeping route tests in `tests/weppcloud/routes/` and matrix/regression tests in `tests/disturbed/`.
  Rationale: Matches requested scope and preserves subsystem boundaries.
  Date/Author: 2026-03-31 / Codex

- Decision: Prioritize minimal hardening in `wepppy/nodb/mods/disturbed/disturbed.py` only when directly justified by new tests (parent soil fallback, lookup class parity, replacements copy safety).
  Rationale: Required change-scope discipline and contract preservation.
  Date/Author: 2026-03-31 / Codex

- Decision: Keep `tests/nodb/test_disturbed_management_overrides.py`, route tests, and disturbed matrix tests in their existing locations while consolidating only disturbed controller tests.
  Rationale: Meets requested boundaries and avoids collapsing integration/route concerns into controller unit suites.
  Date/Author: 2026-03-31 / Codex

## Outcomes & Retrospective

Disturbed controller tests are now consolidated under `tests/nodb/mods/disturbed/` with a shared fixture module and concern-based test modules. Direct behavior coverage now exists for the required disturbed controller methods and routing logic. Minimal production hardening was applied only where test gaps demanded it: source soil fallback resolution, lookup class parity in MOFE, and defensive copying of replacement mappings.

Validation commands all pass. No blocking review findings remain. Residual risk is limited to environment-dependent integration behavior in the uniform SBS tests that rely on `/wc1/runs/le/legato-alkalinity`, which continues to skip when unavailable.

## Context and Orientation

Key implementation file:
- `wepppy/nodb/mods/disturbed/disturbed.py`

Related NoDb controllers in scope for compatibility:
- `wepppy/nodb/core/landuse.py`
- `wepppy/nodb/core/soils.py`

Current disturbed tests to migrate/consolidate:
- `tests/nodb/mods/test_lookup_disturbed_class.py`
- `tests/nodb/mods/test_disturbed_lookup_persistence.py`
- `tests/nodb/mods/test_disturbed_extended_lookup_temp_path.py`
- `tests/nodb/mods/test_disturbed_validate_sbs_4class.py`
- `tests/nodb/mods/test_disturbed_uniform_sbs.py`

Tests to keep in place:
- Route tests under `tests/weppcloud/routes/` (for example `test_disturbed_bp.py`)
- Matrix/regression integration tests under `tests/disturbed/` (for example `test_disturbed_matrix.py`)
- `tests/nodb/test_disturbed_management_overrides.py` (management override utility coverage)

## Plan of Work

First, create `tests/nodb/mods/disturbed/` and add a shared fixture module (`conftest.py`) with detached Disturbed stubs and no-op context helpers so controller methods can be unit tested without full run initialization.

Then migrate existing lookup/SBS tests into concern-based modules:
- `test_lookup_contract.py`
- `test_sbs_validation.py`

Next, author new direct behavior tests:
- `test_landuse_remap.py`
- `test_modify_soils_single_ofe.py`
- `test_modify_soils_mofe.py`
- `test_pmetpara_prep.py`
- `test_trigger_routing.py`

After tests expose gaps, apply minimal hardening in disturbed controller code:
- resolve source soil path with parent fallback
- normalize MOFE lookup key behavior for treatment suffixes
- pass copied replacements mappings into soil conversion calls

Finally, run required validation commands and a reviewer/QA subagent pass, then record findings/dispositions and results here.

## Concrete Steps

From repository root `/workdir/wepppy`:

1. Create test package directory and shared fixtures.
2. Migrate and split disturbed tests into concern-based modules.
3. Remove replaced/duplicate old disturbed test files from `tests/nodb/mods/`.
4. Add minimal disturbed controller hardening required by tests.
5. Run:
   - `wctl run-pytest tests/nodb/mods/disturbed --maxfail=1`
   - `wctl run-pytest tests/nodb/mods/test_treatments_build.py --maxfail=1`
   - `wctl run-pytest tests/nodb/test_disturbed_management_overrides.py --maxfail=1`
   - `wctl run-pytest tests/wepp/soils/utils/test_wepp_soil_util.py --maxfail=1`
   - `wctl doc-lint --path docs/mini-work-packages/20260331_disturbed_test_consolidation_and_hardening_execplan.md`

## Validation and Acceptance

Acceptance is satisfied when:
- Disturbed controller tests are consolidated under `tests/nodb/mods/disturbed/` with shared fixtures and concern-separated modules.
- Required disturbed controller behaviors are directly covered by tests.
- Any production changes are demonstrably test-backed (fail-before/pass-after rationale documented).
- All required validation commands pass.

## Idempotence and Recovery

All test-file moves and code edits are idempotent with git tracking. If a test migration introduces issues, rerun focused disturbed tests first, then restore expected behavior via small isolated patches before running the broader validation commands.

No branch switching is used. Unrelated dirty files in the working tree are preserved untouched.

## Artifacts and Notes

Pre-edit explorer gap map summary:
- No direct disturbed-controller coverage for `modify_soil`, `modify_soils`, `modify_mofe_soils`, `remap_landuse`, `remap_mofe_landuse`, `pmetpara_prep`, or `on(...)`.
- Existing disturbed tests are scattered in root `tests/nodb/mods/`.
- Candidate hardening areas: parent soil fallback, treatment suffix parity in MOFE lookup, replacement dict copy safety.

Validation evidence:
- `wctl run-pytest tests/nodb/mods/disturbed --maxfail=1` -> 62 passed.
- `wctl run-pytest tests/nodb/mods/test_treatments_build.py --maxfail=1` -> 3 passed.
- `wctl run-pytest tests/nodb/test_disturbed_management_overrides.py --maxfail=1` -> 2 passed.
- `wctl run-pytest tests/wepp/soils/utils/test_wepp_soil_util.py --maxfail=1` -> 41 passed.
- `wctl doc-lint --path docs/mini-work-packages/20260331_disturbed_test_consolidation_and_hardening_execplan.md` -> 1 validated, 0 errors, 0 warnings.

Post-implementation QA/review disposition:
- No blocking findings in changed disturbed controller/test paths after full required validation pass.
- Residual risks: integration test dependence on external run directory for `test_sbs_validation.py`.

## Interfaces and Dependencies

Primary interfaces under test:
- `Disturbed.modify_soil(...)`
- `Disturbed.modify_soils()`
- `Disturbed.modify_mofe_soils()`
- `Disturbed.remap_landuse()`
- `Disturbed.remap_mofe_landuse()`
- `Disturbed.pmetpara_prep()`
- `Disturbed.on(evt: TriggerEvents)`

No new third-party dependencies are introduced.

---

Revision note (2026-03-31, Codex): Initialized the active mini work-package ExecPlan after required guidance review and pre-edit explorer gap mapping so implementation can proceed milestone-by-milestone with auditable progress.
Revision note (2026-03-31, Codex): Updated plan to reflect completed consolidation/hardening implementation, validation outcomes, and post-implementation QA/review disposition.
