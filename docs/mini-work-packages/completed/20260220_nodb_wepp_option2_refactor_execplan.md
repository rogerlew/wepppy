# ExecPlan: Stabilize and Refactor `wepppy/nodb/core/wepp.py` with a Facade + Collaborators

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept current as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, the WEPP NoDb controller keeps its current public behavior while becoming substantially easier to change safely. The user-visible gain is stability during future feature work: defects are fixed first, test coverage for high-risk paths is expanded, and the current monolith is split into focused collaborator modules behind a stable `Wepp` facade.

Proof will be observable in two ways. First, defect regression tests that fail before fixes will pass after fixes. Second, the WEPP NoDb and WEPP test suites will pass with unchanged workflow behavior, while complexity hotspots in `wepppy/nodb/core/wepp.py` are reduced through extraction.

## Progress

- [x] (2026-02-20 04:36Z) Reviewed root and NoDb `AGENTS.md` guidance, plus `docs/prompt_templates/codex_exec_plans.md`.
- [x] (2026-02-20 04:36Z) Assessed `wepppy/nodb/core/wepp.py` complexity and risk hotspots using current tree metrics and function-level scans.
- [x] (2026-02-20 04:36Z) Identified open defect candidates and current test-coverage gaps for `parse_inputs`, prep/run wrappers, and defect-prone file contracts.
- [x] (2026-02-20 04:36Z) Authored this ExecPlan at `docs/mini-work-packages/20260220_nodb_wepp_option2_refactor_execplan.md`.
- [x] (2026-02-20 04:44Z) Phase 0 complete: captured baseline metrics (`SLOC 3127`, max CC `67`) and baseline characterization suites (`14 passed`, `9 passed`).
- [x] (2026-02-20 04:58Z) Phase 1 complete: defect regressions added and fixed (`baseflow_opts` typo, PMET remove contract, broad bare-catch removals) with targeted tests green.
- [x] (2026-02-20 05:04Z) Phase 2 complete: extracted `WeppInputParser` into `wepppy/nodb/core/wepp_input_parser.py`; `Wepp.parse_inputs` now lock-scoped facade delegation.
- [x] (2026-02-20 05:09Z) Phase 3 complete: extracted prep/run/postprocess/bootstrap collaborators and rewired `Wepp` facade wrappers; added collaborator delegation tests.
- [x] (2026-02-20 05:14Z) Phase 4 complete: quality packet captured (after metrics, focused gates, broad WEPP gates, full `tests` gate, CAO report, doc-lint).
- [x] (2026-02-20 05:15Z) Phase 5 complete: closeout updates complete; plan moved to `docs/mini-work-packages/completed/`.

## Surprises & Discoveries

- Observation: The requested file path (`wepppy/nodb/wepp.py`) does not exist in this checkout; the operational controller is `wepppy/nodb/core/wepp.py`.
  Evidence: file discovery and path scan in repository tree.

- Observation: The target file remains a severe complexity hotspot (`SLOC 3127`, max method CC `67`, max method length `247` in quality report).
  Evidence: `code-quality-report.json`, `code-quality-summary.md`, and `radon cc` on `wepppy/nodb/core/wepp.py`.

- Observation: There are probable high-value defects that should be stabilized before structural refactor:
  - `baseflows_opts` likely typo (`wepppy/nodb/core/wepp.py:642`);
  - PMET removal filename mismatch (`pmetpara.txt` vs `pmet.txt`, `wepppy/nodb/core/wepp.py:1830` and `wepppy/nodb/core/wepp.py:1834`);
  - broad catches and bare `except` in production paths (`wepppy/nodb/core/wepp.py:120`, `wepppy/nodb/core/wepp.py:2249`).
  Evidence: direct line-level inspection of `wepppy/nodb/core/wepp.py`.

- Observation: Coverage is already strong for some prep paths (`tests/nodb/test_wepp_nodir_read_paths.py`, `tests/wepp/test_wepp_prep_managements_rap_ts.py`, `tests/wepp/test_wepp_run_watershed_interchange_options.py`), but direct coverage of `Wepp.parse_inputs` and several wrapper contracts is thin.
  Evidence: targeted test query against `tests/nodb` and `tests/wepp`.

- Observation: Broad WEPP and full-suite gates surfaced a pre-existing import-cycle hazard when NoDir modules imported `wepppy.nodb.base` at module import time (`query_engine.activate` -> `nodir` -> `nodb` package init recursion).
  Evidence: repeated collection failure in `tests/wepp/interchange/test_calendar_utils.py` during `wctl run-pytest tests/wepp tests/nodb -k "wepp and not slow" --maxfail=1`.

- Observation: Resolving the lock-backend imports lazily in `wepppy/nodir/materialize.py`, `wepppy/nodir/projections.py`, and `wepppy/nodir/thaw_freeze.py` removed the cycle and preserved NoDir test monkeypatch contracts by keeping module-level `redis_lock_client` attributes.
  Evidence: `wctl run-pytest tests/nodir/test_materialize.py tests/nodir/test_projections.py tests/nodir/test_thaw_freeze.py tests/nodir/test_mutations.py tests/nodir/test_wepp_inputs.py --maxfail=1` -> `75 passed`.

- Observation: Facade extraction materially reduced `wepp.py` size and hotspot severity (`SLOC 3127 -> 1966`, max method CC `67 -> 13`).
  Evidence: before/after `radon raw wepppy/nodb/core/wepp.py` and `radon cc -s wepppy/nodb/core/wepp.py`.

## Decision Log

- Decision: Use option 2 (stable facade + internal collaborators) rather than a full state-machine rewrite.
  Rationale: It provides large maintainability gains with lower regression risk than a full orchestration model replacement.
  Date/Author: 2026-02-20 / Codex

- Decision: Sequence work as “defects + characterization tests first, structural extraction second.”
  Rationale: This gives a stable baseline before moving logic across modules and reduces false positives during refactor.
  Date/Author: 2026-02-20 / Codex

- Decision: Keep `wepppy/nodb/core/wepp.py` as the public facade during this plan; extracted modules remain internal implementation detail.
  Rationale: Existing imports and runtime assumptions in RQ/routes/tests should not break during the migration.
  Date/Author: 2026-02-20 / Codex

- Decision: Treat quality review as a first-class phase with explicit acceptance artifacts (test pass set + complexity deltas + review checklist outcomes).
  Rationale: The stated goal is maintainability with controlled regression risk, so implementation without review evidence is insufficient.
  Date/Author: 2026-02-20 / Codex

- Decision: Keep existing test monkeypatch seams stable by routing collaborator dependency lookups through `wepppy.nodb.core.wepp` symbols where legacy tests already patch behavior.
  Rationale: This preserved facade behavior and avoided brittle test churn during extraction.
  Date/Author: 2026-02-20 / Codex

- Decision: Fix NoDir lock-backend import cycles by using lazy lock-backend resolvers with module-level `redis_lock_client` override compatibility.
  Rationale: Full-suite gate failures were collection-time import cycles; lazy resolution fixed runtime ordering while preserving NoDir test contracts.
  Date/Author: 2026-02-20 / Codex

## Outcomes & Retrospective

- (2026-02-20 04:36Z) Outcome: Planning is complete; implementation has not started yet.
- (2026-02-20 04:36Z) Retrospective: The plan intentionally prioritizes contract-preserving extraction over aggressive redesign to keep risk bounded while still reducing long-term maintenance cost.
- (2026-02-20 05:14Z) Outcome: Phases 0-4 are complete. Defect fixes are locked by regressions, collaborators are extracted behind stable `Wepp` facade methods, and required validation gates are passing.
- (2026-02-20 05:14Z) Outcome: Validation evidence includes focused WEPP/NoDb suites, broad WEPP filters, and full pre-handoff gate `wctl run-pytest tests --maxfail=1` (`1779 passed`, `27 skipped`).
- (2026-02-20 05:14Z) Retrospective: The highest-risk follow-on issue was import-order coupling in NoDir lock dependencies; fixing it during quality hardening reduced gate fragility and improved reproducibility.
- (2026-02-20 05:15Z) Outcome: ExecPlan implementation and closeout are complete end-to-end for the requested scope.

## Context and Orientation

`wepppy/nodb/core/wepp.py` currently combines multiple concerns in one class: option parsing and validation, hillslope/channel input prep, run orchestration, interchange/post-processing, and bootstrap git management. This makes local changes expensive to review and hard to test in isolation.

“Facade” in this plan means the existing `Wepp` class remains the entrypoint and keeps method names/signatures. “Collaborators” means new internal modules/classes that own cohesive behavior areas and are called by facade wrappers. The migration is incremental: behavior first, structure second.

Primary code surface in scope:

- `wepppy/nodb/core/wepp.py` (facade wrappers and transitional delegations)
- New internal collaborator modules under `wepppy/nodb/core/` (defined below)
- Optional typing stubs for new modules, if needed by current stub policy

Primary tests in scope:

- `tests/nodb/test_wepp_nodir_read_paths.py`
- `tests/wepp/test_wepp_frost_opts.py`
- `tests/wepp/test_wepp_prep_managements_rap_ts.py`
- `tests/wepp/test_wepp_run_watershed_interchange_options.py`
- New targeted regression suites for defects and wrapper contracts

## Plan of Work

Phase 0 establishes a measurable baseline and characterization harness. Capture current complexity and current behavior so refactor changes can be evaluated against known outcomes, not assumptions. Add missing harness helpers for `Wepp.__new__`-style isolated tests where needed.

Phase 1 addresses open defects with targeted regression tests first, then minimal code fixes. This includes config-key consistency, PMET file lifecycle correctness, and replacing non-boundary broad catches where practical with narrower exception handling and explicit logging.

Phase 2 extracts input parsing and bounds-guard logic from `Wepp.parse_inputs` into a dedicated collaborator (`wepppy/nodb/core/wepp_input_parser.py`) while preserving facade behavior. `Wepp.parse_inputs` becomes a wrapper that delegates through a stable context object and remains lock-scoped exactly as before.

Phase 3 extracts additional cohesive collaborators:

- `wepppy/nodb/core/wepp_prep_service.py` for `_prep_*` methods and related helpers.
- `wepppy/nodb/core/wepp_run_service.py` for `run_hillslopes`, `run_watershed`, and flowpath orchestration.
- `wepppy/nodb/core/wepp_postprocess_service.py` for return periods, loss query helpers, and grid/export post-run logic.
- `wepppy/nodb/core/wepp_bootstrap_service.py` for bootstrap git operations.

Each extraction step is done behind facade wrappers and followed immediately by tests so contract drift is caught at the smallest diff.

Phase 4 runs quality review and hardening. This includes required test gates, code-quality observability delta checks, and a structured review of exception boundaries, lock semantics, and path/file contract handling.

Phase 5 performs closeout and documentation housekeeping: finalize this plan’s living sections, move it to `docs/mini-work-packages/completed/`, and provide a concise retrospective with remaining risks.

## Concrete Steps

Run all commands from `/workdir/wepppy`.

1. Capture baseline before edits:

       radon cc -s wepppy/nodb/core/wepp.py
       radon raw wepppy/nodb/core/wepp.py
       wctl run-pytest tests/nodb/test_wepp_nodir_read_paths.py
       wctl run-pytest tests/wepp/test_wepp_frost_opts.py tests/wepp/test_wepp_prep_managements_rap_ts.py tests/wepp/test_wepp_run_watershed_interchange_options.py

2. Add/adjust characterization tests and defect regressions:

       wctl run-pytest tests/wepp/test_wepp_frost_opts.py
       wctl run-pytest tests/nodb/test_wepp_nodir_read_paths.py -k "prep_managements or prep_soils or prep_climates"

3. Implement Phase 1 defect fixes and rerun targeted tests until green:

       wctl run-pytest tests/wepp tests/nodb -k "wepp and not slow" --maxfail=1

4. Execute phased collaborator extraction with narrow test loops:

       wctl run-pytest tests/wepp tests/nodb -k "wepp" --maxfail=1

5. Run full pre-handoff validation:

       wctl run-pytest tests --maxfail=1
       python3 tools/code_quality_observability.py --base-ref origin/master
       wctl doc-lint --path docs/mini-work-packages/20260220_nodb_wepp_option2_refactor_execplan.md

Expected outcomes:

- No regression in WEPP NoDb behavior tests.
- Defect regression tests pass and lock in fixes.
- Complexity and hotspot signals improve materially in touched code paths.

## Validation and Acceptance

Acceptance requires all of the following:

1. Open defect set is resolved with direct regression tests.
2. `Wepp` public behavior remains stable for existing entrypoints (`parse_inputs`, `prep_hillslopes`, `run_hillslopes`, `prep_watershed`, `run_watershed`, report/query methods).
3. New collaborators exist and are used by `Wepp` facade wrappers without contract drift.
4. Test gates pass:
   - Focused WEPP/NoDb suites during iteration.
   - `wctl run-pytest tests --maxfail=1` before closeout.
5. Quality review packet is complete:
   - before/after complexity evidence,
   - exception-boundary review findings,
   - unresolved risk list and rationale.

## Idempotence and Recovery

The plan is designed to be replayable. Each phase is additive and can be rerun from a clean branch. Tests are run after each phase to prevent deep rollback.

If a collaborator extraction introduces drift, revert that extraction step only (not the whole phase), keep facade wrappers in place, and re-run the same focused test set before proceeding.

Generated or report artifacts should be regenerated using repository tooling rather than manual edits. For docs, use `wctl doc-lint` to confirm clean state after updates.

## Artifacts and Notes

Expected implementation artifacts include:

- New collaborator modules under `wepppy/nodb/core/` for parser/prep/run/postprocess/bootstrap responsibilities.
- New or expanded tests in `tests/wepp/` and `tests/nodb/` that explicitly cover defect regressions and facade-wrapper contracts.
- A final review note in this ExecPlan summarizing complexity deltas and remaining risks.

Quality review checklist to complete during Phase 4:

- No new broad `except Exception` handlers in production flow unless explicitly justified as a boundary.
- Locking semantics (`with self.locked()`) are unchanged for mutating facade entrypoints.
- File contracts for prep/remove pairs are symmetric and tested.
- Logging remains actionable for failure paths without swallowing root causes.

## Interfaces and Dependencies

The `Wepp` facade in `wepppy/nodb/core/wepp.py` must remain the primary interface. Collaborators are internal and should expose explicit, typed functions/classes that accept dependencies as parameters where practical to support isolated tests.

Target collaborator interfaces at end state:

- In `wepppy/nodb/core/wepp_input_parser.py`:
  - `class WeppInputParser:`
    - `def parse(self, wepp: "Wepp", kwds: dict[str, object]) -> None`

- In `wepppy/nodb/core/wepp_prep_service.py`:
  - `class WeppPrepService:`
    - `def prep_hillslopes(self, wepp: "Wepp", ...) -> None`
    - `def prep_watershed(self, wepp: "Wepp", ...) -> None`

- In `wepppy/nodb/core/wepp_run_service.py`:
  - `class WeppRunService:`
    - `def run_hillslopes(self, wepp: "Wepp", ...) -> None`
    - `def run_watershed(self, wepp: "Wepp") -> None`

- In `wepppy/nodb/core/wepp_postprocess_service.py`:
  - `class WeppPostprocessService:`
    - `def report_return_periods(self, wepp: "Wepp", ...) -> ReturnPeriods`
    - `def query_sub_val(self, wepp: "Wepp", measure: str) -> dict | None`
    - `def query_chn_val(self, wepp: "Wepp", measure: str) -> dict | None`

- In `wepppy/nodb/core/wepp_bootstrap_service.py`:
  - `class WeppBootstrapService:`
    - bootstrap/git helper methods currently on `Wepp`, migrated without changing facade behavior.

No RQ queue wiring changes are expected in this plan. If such changes become necessary, update `wepppy/rq/job-dependencies-catalog.md` and run `wctl check-rq-graph` per repository contract.

Revision Note (2026-02-20 04:36Z, Codex): Created this multi-phase ExecPlan in response to the request for an option-2 collaborator refactor plan that explicitly includes defect remediation, test-gap closure, and quality-review gates.
Revision Note (2026-02-20 05:14Z, Codex): Updated living sections with implementation progress through Phase 4, including collaborator extraction outcomes, import-cycle discoveries/fixes, and validation evidence.
Revision Note (2026-02-20 05:15Z, Codex): Completed Phase 5 closeout, moved this ExecPlan to `docs/mini-work-packages/completed/`, and finalized completion outcomes.
