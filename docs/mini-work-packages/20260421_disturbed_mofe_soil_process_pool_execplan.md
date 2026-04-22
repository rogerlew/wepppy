# Mini Work Package: Canonical `createProcessPoolExecutor` for MOFE Soil Building
Status: Completed
Last Updated: 2026-04-22
Primary Areas: `wepppy/nodb/mods/disturbed/disturbed.py`, `tests/nodb/mods/disturbed/test_modify_soils_mofe.py`, `tests/nodb/mods/disturbed/test_modify_soils_single_ofe.py`, `wepppy/nodb/base.py`, `wepppy/nodb/core/wepp.py`, `wepppy/nodb/core/wepp_prep_service.py`

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

`Disturbed.modify_mofe_soils()` currently builds disturbed MOFE soils serially under a single lock. On larger watersheds, this becomes a wall-clock hotspot because each OFE soil conversion (`WeppSoilUtil.to_7778disturbed` / `to_over9000`) and file write executes one-at-a-time.

After this change, MOFE soil-building will adopt the same canonical process-pool execution pattern already used in NoDb WEPP prep services: use `createProcessPoolExecutor`, prefer spawn first, retry fork context on `BrokenProcessPool`, then fall back to sequential only when the pool itself is broken. Non-boundary worker errors remain explicit failures.

## Scope and Non-Goals

In scope:
- Introduce canonical `createProcessPoolExecutor` execution path for disturbed MOFE soil building.
- Preserve current disturbed soil semantics (including 9002 lookup-hit/miss behavior and class-aware keying).
- Add focused regression coverage for pool success path and fallback/error behavior.

Out of scope:
- Changing disturbed lookup contracts.
- Refactoring unrelated soil-build paths (`build_isric`, WEPP prep pipelines, climate pools).
- Introducing silent error masking or broad fallback wrappers.

## Review of Existing Implementations (Scoping Evidence)

Canonical helper and behavior source:
- `wepppy/nodb/base.py::createProcessPoolExecutor`
  - Requires `max_workers`.
  - Prefers spawn context when requested.
  - Falls back to default context when spawn unavailable/fails.

Canonical orchestration patterns:
- `wepppy/nodb/core/wepp.py::_prep_multi_ofe`
- `wepppy/nodb/core/wepp_prep_service.py::prep_soils`

Shared traits to preserve:
1. `run_concurrent` gating by worker count and task count.
2. Dedicated `_run_*_pool(prefer_spawn: bool)` wrapper returning `(success, exc)`.
3. Progress loop using `wait(..., return_when=FIRST_COMPLETED)` and periodic waiting logs.
4. Pending-future cancellation on task failure.
5. Retry with `prefer_spawn=False` on `BrokenProcessPool`.
6. Sequential fallback only when pool is broken.
7. Re-raise non-pool task exceptions.

MOFE target seam:
- `wepppy/nodb/mods/disturbed/disturbed.py::modify_mofe_soils`
  - Currently serial loop over hillslopes and OFEs.
  - Must retain existing data contract and output files.

## Key Risks and Mitigations

Risk: Mutating NoDb state concurrently can corrupt in-memory maps.
- Mitigation: two-phase design.
  - Phase A (parallel): worker computes/writes unique disturbed MOFE soil artifacts from a deterministic build plan.
  - Phase B (unlocked synthesis + locked apply): build `hill_<topaz>.mofe.sol` stacks from generated artifacts, then update `soils.domsoil_d`, `soils.soils`, and coverage stats under lock.

Risk: Worker pickling/import constraints under spawn.
- Mitigation: keep worker callable as module-level function with plain-serializable task args.

Risk: Silent behavior drift in disturbed outputs.
- Mitigation: preserve current lookup/replacement/keying logic in worker unit and assert parity via targeted tests.

## Plan of Work

### Milestone 1: Isolate MOFE disturbed soil build unit

- Extract the disturbed-soil conversion logic into a top-level worker helper in `disturbed.py` that:
  - accepts fully-resolved task args,
  - builds/writes one disturbed MOFE `.sol` artifact,
  - returns stable metadata for progress logging and deterministic apply.
- Keep behavior identical to current logic:
  - lookup normalization,
  - 7778/900x converter routing,
  - 9002 lookup-miss fallback replacements + class-aware keying,
  - descriptive metadata strings.

### Milestone 2: Adopt canonical pool orchestration in `modify_mofe_soils`

- Add canonical execution flow modeled after `wepp.py::_prep_multi_ofe`:
  - `_run_mofe_soil_pool(prefer_spawn)` boundary,
  - `_run_mofe_soil_sequential()` boundary,
  - progress wait loop,
  - `BrokenProcessPool` retry/fallback semantics.
- Apply results under `soils.locked()` after concurrent generation stage.
- Keep non-pool task exceptions explicit (no silent fallback for logic/data errors).

### Milestone 3: Regression tests and docs

- Extend `tests/nodb/mods/disturbed/test_modify_soils_mofe.py` with coverage for:
  - concurrent path invoked when tasks/workers justify it,
  - spawn-failure (`BrokenProcessPool`) retry path,
  - sequential fallback when pool remains broken,
  - non-`BrokenProcessPool` task error propagation,
  - unchanged lookup-hit/miss semantic outputs.
- Update disturbed developer notes to state MOFE soil building now uses canonical process-pool pattern and documented fallback contract.

## Concrete File-Level Changes

- `wepppy/nodb/mods/disturbed/disturbed.py`
  - add worker helper(s) and canonical pool orchestration.
  - import/use `createProcessPoolExecutor` and `BrokenProcessPool`.

- `tests/nodb/mods/disturbed/test_modify_soils_mofe.py`
  - add pool/fallback/error-path tests.
  - keep existing behavior tests green.

- `wepppy/nodb/mods/disturbed/README.md`
  - update developer notes for concurrency model and fallback behavior.

## Validation Gates

Required:
- `wctl run-pytest tests/nodb/mods/disturbed/test_modify_soils_mofe.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods/disturbed/test_modify_soils_single_ofe.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods/disturbed/test_lookup_contract.py --maxfail=1`

Recommended confidence checks:
- `wctl run-pytest tests/wepp/soils/utils/test_wepp_soil_util.py --maxfail=1`
- `wctl run-pytest tests --maxfail=1` (if package execution scope/time allows)

## Acceptance Criteria

1. `modify_mofe_soils` uses canonical `createProcessPoolExecutor` orchestration with spawn->fork retry and sequential fallback on broken pools.
2. Existing disturbed MOFE output semantics are preserved (lookup and keying behavior unchanged).
3. Non-boundary task failures still fail explicitly (no silent masking).
4. New regression tests cover success, retry, fallback, and error propagation paths.
5. Targeted disturbed test gates pass.

## Progress

- [x] (2026-04-21) Reviewed canonical helper in `base.py`.
- [x] (2026-04-21) Reviewed reference pool implementations in `wepp.py::_prep_multi_ofe` and `wepp_prep_service.py::prep_soils`.
- [x] (2026-04-21) Reviewed target MOFE seam in `disturbed.py::modify_mofe_soils`.
- [x] (2026-04-21) Authored mini work-package scope/spec with implementation milestones and validation gates.
- [x] (2026-04-22) Implemented canonical MOFE disturbed soil pool orchestration in `Disturbed.modify_mofe_soils` with spawn-first, fork-retry, and sequential fallback on `BrokenProcessPool`.
- [x] (2026-04-22) Refactored MOFE flow into two phases: unlocked generation/synthesis, then locked serial apply of `soils.domsoil_d` / `soils.soils` and area/coverage recompute.
- [x] (2026-04-22) Extended `tests/nodb/mods/disturbed/test_modify_soils_mofe.py` with concurrent-path, spawn-retry, broken-pool fallback, and non-broken task failure propagation coverage.
- [x] (2026-04-22) Updated `wepppy/nodb/mods/disturbed/README.md` developer notes for pool retry/fallback and error propagation semantics.
- [x] (2026-04-22) Ran required and recommended validation gates; all targeted suites passed.

## Surprises & Discoveries

- `modify_mofe_soils` currently performs all conversion/synthesis serially while holding lock scope, unlike canonical prep paths.
- Canonical NoDb pool implementations consistently distinguish `BrokenProcessPool` from task logic errors and only use sequential fallback for the former.
- Existing MOFE unit tests monkeypatch local converter classes; default spawn pools would bypass those monkeypatches. A default inline executor fixture in the MOFE test module keeps tests hermetic while dedicated tests still validate spawn/fork/sequential control-flow behavior.
- `wctl run-pytest` initially failed because `weppcloud` was not running; bringing up `docker/docker-compose.dev.yml` service `weppcloud` restored the canonical test path.

## Decision Log

- Decision: Scope this package to disturbed MOFE soil-building only.
  - Rationale: user request targets MOFE soil building; avoiding broader refactors keeps risk bounded.
  - Date/Author: 2026-04-21 / Codex

- Decision: Reuse the established NoDb pool error-handling contract instead of inventing a new pattern.
  - Rationale: lowers operational risk and improves consistency across prep/build services.
  - Date/Author: 2026-04-21 / Codex

- Decision: Use a deterministic unique disturbed-soil generation stage plus serial MOFE apply instead of mutating `soils` maps inside workers.
  - Rationale: preserves existing keying/lookup contracts while avoiding concurrent mutation of NoDb state and duplicate/racy writes for shared disturbed keys.
  - Date/Author: 2026-04-22 / Codex

- Decision: Keep non-`BrokenProcessPool` errors as hard failures with no sequential fallback.
  - Rationale: matches canonical NoDb behavior and prevents silent masking of logic/data regressions.
  - Date/Author: 2026-04-22 / Codex

## Outcomes & Retrospective

- Completed. `Disturbed.modify_mofe_soils` now uses canonical pool orchestration for disturbed MOFE soil generation (`prefer_spawn=True` first, retry with `prefer_spawn=False` on `BrokenProcessPool`, sequential fallback only when both pools are broken).
- Completed. Disturbed MOFE behavior contracts remained intact: lookup-hit keying, lookup-miss 9002 class-specific fallback replacements (`luse`/`stext`/`ksatfac`/`ksatrec`), and output naming/metadata patterns were preserved.
- Completed. Regression coverage now explicitly exercises concurrent path, spawn failure retry, broken-pool sequential fallback, and non-broken task failure propagation.
- Validation evidence:
  - `wctl run-pytest tests/nodb/mods/disturbed/test_modify_soils_mofe.py --maxfail=1` -> `14 passed`
  - `wctl run-pytest tests/nodb/mods/disturbed/test_modify_soils_single_ofe.py --maxfail=1` -> `7 passed`
  - `wctl run-pytest tests/nodb/mods/disturbed/test_lookup_contract.py --maxfail=1` -> `30 passed`
  - `wctl run-pytest tests/wepp/soils/utils/test_wepp_soil_util.py --maxfail=1` -> `51 passed`

Plan revision note (2026-04-22): Updated living sections to reflect implementation completion, final design decisions, and executed validation evidence.
