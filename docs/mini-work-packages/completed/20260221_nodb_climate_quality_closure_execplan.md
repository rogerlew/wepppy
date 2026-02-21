# ExecPlan: Closure Refactor for `wepppy/nodb/core/climate.py` Quality Gates

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept current as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, `wepppy/nodb/core/climate.py` keeps the same public facade behavior while no longer containing unresolved quality hotspots. Specifically, no method/function in that file exceeds `C (20)` complexity, no method/function exceeds 120 lines, and deterministic regression tests cover the new delegation seams introduced by refactoring.

This is a closure package. It is complete only when every hard acceptance target and every required command gate in this document is green with recorded evidence.

## Progress

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format.

- [x] (2026-02-21 05:53Z) Reviewed governing instructions (`AGENTS.md`, `wepppy/nodb/AGENTS.md`, `tests/AGENTS.md`, `docs/prompt_templates/codex_exec_plans.md`) and inspected `climate.py` hotspot baseline.
- [x] (2026-02-21 05:53Z) Authored this mini ExecPlan and registered it as the active ad hoc plan in `AGENTS.md`.
- [x] (2026-02-21 05:53Z) Milestone 0 complete: captured baseline telemetry and hotspot evidence (`radon raw`, `radon cc`, `code_quality_observability`).
- [x] (2026-02-21 05:55Z) Milestone 1 complete: extracted user-defined station-meta parsing/writing to `climate_user_defined_station_meta_service.py` and switched `set_user_defined_cli` to delegator usage; focused regression gate passed (`6 passed`).
- [x] (2026-02-21 05:58Z) Milestone 2 complete: extracted `_build_climate_observed_gridmet_multiple` internals into `climate_gridmet_multiple_build_service.py`, leaving a locked facade delegator; focused gate passed (`13 passed` across build-router/facade/user-defined tests).
- [x] (2026-02-21 05:59Z) Milestone 3 complete: added deterministic seam regressions for gridmet-multiple delegator and user-defined station-meta delegator; focused regression gate passed (`8 passed`).
- [x] (2026-02-21 06:06Z) Milestone 4 complete: ran all required hard-gate commands and AST length scan; all gates green (`radon raw SLOC 1728`, `radon cc max C19`, targeted gate `50 passed, 11 skipped`, full suite `1923 passed, 27 skipped`).
- [x] (2026-02-21 07:00Z) Milestone 5 complete: verified `AGENTS.md` ad hoc active ExecPlan remains `none`, moved this plan to `docs/mini-work-packages/completed/`, and performed closure commit/push workflow.
- [x] (2026-02-21 06:51Z) Post-review findings remediation complete: added executor-shutdown boundary handling in GridMET multiple build service and direct collaborator unit coverage for GridMET future-wait paths plus user-defined station-meta parsing/stub semantics; focused climate gate passed (`59 passed, 11 skipped`).
- [x] (2026-02-21 06:58Z) Post-review full-suite verification complete: `wctl run-pytest tests --maxfail=1` passed (`1929 passed, 27 skipped`) after adding six collaborator-level tests.

## Surprises & Discoveries

- (2026-02-21 05:53Z) Observation: `climate.py` contains two hard blockers for closure criteria.
  Evidence: `radon cc -s wepppy/nodb/core/climate.py` reports `_build_climate_observed_gridmet_multiple - E (31)` and `_build_user_defined_station_meta_from_cli - D (27)`.

- (2026-02-21 05:53Z) Observation: only one function violates the 120-line limit.
  Evidence: AST length scan reports `Climate._build_climate_observed_gridmet_multiple` length `239`; no other function exceeds 120.

- (2026-02-21 05:53Z) Observation: baseline SLOC must not increase.
  Evidence: `radon raw wepppy/nodb/core/climate.py` baseline is `SLOC: 2031`.

- (2026-02-21 05:55Z) Observation: user-defined station-meta extraction preserved current behavior without touching lock/post-build flow.
  Evidence: `wctl run-pytest tests/nodb/test_user_defined_cli_parquet.py tests/nodb/test_climate_facade_collaborators.py --maxfail=1` passed (`6 passed`).

- (2026-02-21 05:58Z) Observation: moving GridMET-multiple internals out of facade immediately clears both hard quality hotspots in `climate.py`.
  Evidence: `radon cc -s wepppy/nodb/core/climate.py` now reports max `C (19)` and `_build_climate_observed_gridmet_multiple - A (1)` after extraction.

- (2026-02-21 05:59Z) Observation: post-extraction function-length gate is now green before final full-suite run.
  Evidence: AST scan reports `max (111, 833, 'Climate.__init__')` with `violations []`.

- (2026-02-21 06:06Z) Observation: strict hard-gate command list is fully green after refactor.
  Evidence: required commands completed successfully, including `wctl run-pytest tests --maxfail=1` => `1923 passed, 27 skipped`.

- (2026-02-21 06:07Z) Observation: no milestone rollback was required; every milestone completed green on first attempt.
  Evidence: all listed milestone gates passed without revert entries.

- (2026-02-21 06:51Z) Observation: post-review quality findings were resolved without regressing closure hard targets.
  Evidence: focused climate gate rerun passed (`59 passed, 11 skipped`) and `radon cc/raw` remained at `max C (19)` / `SLOC 1728` for `climate.py`.

- (2026-02-21 06:58Z) Observation: full-suite pass count increased versus Milestone 4 baseline due new collaborator tests.
  Evidence: full suite moved from `1923 passed` to `1929 passed` while skipped count remained `27`.

- (2026-02-21 07:00Z) Observation: closure workflow is now reflected in repository state.
  Evidence: this plan lives under `docs/mini-work-packages/completed/` and `AGENTS.md` lists current ad hoc active ExecPlan as `none`.

## Decision Log

- Decision: execute this package as a facade-preserving extraction refactor, not a behavior rewrite.
  Rationale: user requirement mandates preserving existing public contracts (facade/API/routes/RQ behavior) unless explicitly documented and tested.
  Date/Author: 2026-02-21 05:53Z / Codex

- Decision: treat baseline telemetry captured at package start as immutable acceptance reference.
  Rationale: closure criteria require no SLOC regression and objective complexity thresholds against pre-change values.
  Date/Author: 2026-02-21 05:53Z / Codex

- Decision: extract user-defined station-meta logic into a dedicated collaborator service instead of helper splitting inside `climate.py`.
  Rationale: this removes one `D`-grade hotspot from `climate.py` entirely while preserving facade contracts and lowering file-local complexity/SLOC risk.
  Date/Author: 2026-02-21 05:55Z / Codex

- Decision: extract GridMET-multiple orchestration into `ClimateGridmetMultipleBuildService` and keep facade lock boundary in `Climate`.
  Rationale: this preserves lifecycle/locking behavior while removing the single largest complexity and line-length hotspot from `climate.py`.
  Date/Author: 2026-02-21 05:58Z / Codex

- Decision: add seam tests at facade call points rather than integration tests of heavy GridMET workflows.
  Rationale: closure requirement asked for deterministic regression coverage; seam tests validate contract-preserving delegation without introducing flaky network/data dependencies.
  Date/Author: 2026-02-21 05:59Z / Codex

- Decision: treat warning-only output in pytest gates as non-blocking while keeping exact command list and pass/fail totals captured in-plan.
  Rationale: closure criteria are command pass state and behavioral/test parity; warnings were pre-existing deprecations outside the scope of this refactor.
  Date/Author: 2026-02-21 06:06Z / Codex

- Decision: close the package immediately after hard gates with no additional opportunistic refactors.
  Rationale: user requested closure-only execution with strict acceptance targets and no partial/extra scope.
  Date/Author: 2026-02-21 06:07Z / Codex

- Decision: add direct collaborator unit tests for the new extracted services and harden GridMET future-wait exception boundary cleanup.
  Rationale: review findings identified that seam-only tests and reduced executor shutdown semantics left avoidable regression risk in failure paths and collaborator behavior contracts.
  Date/Author: 2026-02-21 06:51Z / Codex

## Outcomes & Retrospective

- (2026-02-21 05:53Z) Outcome: closure package is initialized with active-plan registration and baseline evidence captured.
- (2026-02-21 05:53Z) Retrospective: hotspot shape is narrow and tractable; a focused extraction on two code regions should satisfy hard quality gates without contract churn.
- (2026-02-21 05:55Z) Outcome: Milestone 1 extraction completed and validated with focused tests; no behavioral regression observed in user-defined CLI flow.
- (2026-02-21 05:58Z) Outcome: Milestone 2 extraction completed and facade hotspot removed while preserving mode-routing contracts.
- (2026-02-21 05:59Z) Outcome: Milestone 3 deterministic seam coverage added and verified green on focused test gates.
- (2026-02-21 06:06Z) Outcome: Milestone 4 hard quality/test gates all passed with evidence captured for every required command.
- (2026-02-21 07:00Z) Outcome: closure workflow is complete; plan archived under `docs/mini-work-packages/completed/` with `AGENTS.md` active ad hoc plan set to `none`.
- (2026-02-21 06:51Z) Outcome: post-review remediation added collaborator-level regression coverage and restored explicit executor shutdown semantics at the GridMET worker boundary while keeping all climate hard gates green.
- (2026-02-21 06:58Z) Outcome: full regression sweep remained green after remediation, confirming no cross-subsystem regressions from the follow-up changes.

## Context and Orientation

Primary files in scope:

1. `wepppy/nodb/core/climate.py` (facade plus current hotspot implementations).
2. `wepppy/nodb/core/climate_build_router.py` (build orchestration entrypoint that depends on facade methods).
3. `wepppy/nodb/core/climate_mode_build_services.py` (mode-routing collaborator that currently calls `Climate._build_climate_observed_gridmet_multiple`).
4. `tests/nodb/test_climate_facade_collaborators.py` (facade delegation seam coverage).
5. `tests/nodb/test_user_defined_cli_parquet.py` and/or targeted climate tests for deterministic regression coverage on user-defined CLI metadata behavior.

Required hard acceptance targets:

1. `radon cc -s wepppy/nodb/core/climate.py` reports no method/function above `C (20)`.
2. `wepppy/nodb/core/climate.py` has no method/function longer than `120` lines.
3. `radon raw wepppy/nodb/core/climate.py` SLOC is not greater than baseline `2031`.
4. Regression gaps introduced by refactor are covered by deterministic tests.
5. The full required gate command list runs and passes.

## Milestone Plan

### Milestone 0: Baseline Freeze (Completed)

Capture baseline metrics and current hotspot profile before edits, then proceed only with objective thresholds documented.

Commands already executed:

    python3 tools/code_quality_observability.py --base-ref origin/master --json-out /tmp/climate-quality-baseline.json --md-out /tmp/climate-quality-baseline.md
    radon raw wepppy/nodb/core/climate.py
    radon cc -s wepppy/nodb/core/climate.py
    python3 - <<'PY'
    import ast, pathlib
    src = pathlib.Path("wepppy/nodb/core/climate.py").read_text()
    mod = ast.parse(src)
    class V(ast.NodeVisitor):
        def __init__(self):
            self.stack = []
            self.out = []
        def visit_ClassDef(self, node):
            self.stack.append(node.name); self.generic_visit(node); self.stack.pop()
        def visit_FunctionDef(self, node):
            end = getattr(node, "end_lineno", node.lineno)
            self.out.append((end - node.lineno + 1, node.lineno, ".".join(self.stack + [node.name])))
            self.stack.append(node.name); self.generic_visit(node); self.stack.pop()
        visit_AsyncFunctionDef = visit_FunctionDef
    v = V(); v.visit(mod)
    print(max(v.out))
    print([x for x in sorted(v.out, reverse=True) if x[0] > 120])
    PY

Acceptance evidence:

    radon raw: SLOC 2031
    radon cc: max E (31) on Climate._build_climate_observed_gridmet_multiple; D (27) on _build_user_defined_station_meta_from_cli
    function length: max 239 lines (Climate._build_climate_observed_gridmet_multiple)

### Milestone 1: Extract User-Defined Station Meta Helpers

Move user-defined station metadata parsing and `.par` stub creation helpers out of `climate.py` into a collaborator module, and keep `Climate.set_user_defined_cli` behavior unchanged.

Files:

1. `wepppy/nodb/core/climate.py`
2. `wepppy/nodb/core/<new collaborator module for user-defined station meta>`
3. relevant tests under `tests/nodb/`

Go/No-Go:

1. `NO-GO` if `set_user_defined_cli` behavior or expected metadata/par outputs drift.
2. `NO-GO` if climate facade public contracts change.

### Milestone 2: Extract GridMET Multiple Build Internals

Move `_build_climate_observed_gridmet_multiple` internals into a collaborator module and leave `Climate` facade method as orchestration-safe delegator.

Files:

1. `wepppy/nodb/core/climate.py`
2. `wepppy/nodb/core/<new collaborator module for GridMET multiple build>`
3. relevant tests under `tests/nodb/`

Go/No-Go:

1. `NO-GO` if mode-routing contracts in `ClimateModeBuildServices` change.
2. `NO-GO` if lock/timestamp/artifact boundaries move in ways that alter behavior.

### Milestone 3: Add Deterministic Regression Coverage

Add tests for new delegation seams and user-defined metadata extraction edge cases introduced by the refactor.

Required traits:

1. Deterministic and hermetic (no external network calls).
2. Focused on refactor seams and behavior compatibility.

### Milestone 4: Run Hard Validation Gates

Run and record every required gate command with evidence:

    python3 tools/code_quality_observability.py --base-ref origin/master --json-out /tmp/climate-quality-baseline.json --md-out /tmp/climate-quality-baseline.md
    radon raw wepppy/nodb/core/climate.py
    radon cc -s wepppy/nodb/core/climate.py
    wctl run-pytest tests/nodb/test_climate_artifact_export_service.py tests/nodb/test_climate_build_router_services.py tests/nodb/test_climate_catalog.py tests/nodb/test_climate_facade_collaborators.py tests/nodb/test_climate_input_parser_service.py tests/nodb/test_climate_scaling_service.py tests/nodb/test_climate_station_catalog_service.py tests/nodb/test_climate_type_hints.py tests/climate/test_climate_scaling.py tests/climates --maxfail=1
    wctl run-pytest tests --maxfail=1

Also re-run AST length scan to verify no function in `climate.py` exceeds 120 lines.

### Milestone 5: Closure Workflow

Only after all hard targets are green:

1. Mark this ExecPlan complete.
2. Move this file to `docs/mini-work-packages/completed/`.
3. Set `AGENTS.md` current ad hoc active ExecPlan back to `none`.
4. Commit and push all package changes.

## Concrete Steps

Working directory for all commands: repository root (`/workdir/wepppy`).

Implementation sequence:

1. Complete Milestone 1 extraction and run focused tests.
2. Complete Milestone 2 extraction and run focused tests.
3. Complete Milestone 3 tests and confirm deterministic seam coverage.
4. Execute Milestone 4 hard gates; if a gate fails, fix and rerun until green.
5. Execute Milestone 5 closure workflow exactly in order.

Failure handling rule:

1. If a milestone attempt fails, revert only that milestone diff, log evidence in this plan, and continue with the next successful attempt.

## Validation and Acceptance

Closure acceptance is satisfied only when all below are true:

1. `radon cc -s wepppy/nodb/core/climate.py` max grade is `C (20)` or lower.
2. AST length scan confirms no method/function in `climate.py` exceeds 120 lines.
3. `radon raw wepppy/nodb/core/climate.py` SLOC is `<= 2031`.
4. Required targeted test gate passes.
5. Full test suite gate (`wctl run-pytest tests --maxfail=1`) passes.
6. Plan completion workflow performed (move to `completed`, `AGENTS.md` reset, commit, push).

## Idempotence and Recovery

The refactor and test commands are safe to rerun. If a milestone attempt introduces regressions, rollback is milestone-scoped only and must be recorded in this plan with command evidence.

## Artifacts and Notes

Baseline artifacts:

1. `/tmp/climate-quality-baseline.json`
2. `/tmp/climate-quality-baseline.md`

Baseline command excerpts:

    radon raw wepppy/nodb/core/climate.py
        SLOC: 2031

    radon cc -s wepppy/nodb/core/climate.py
        Climate._build_climate_observed_gridmet_multiple - E (31)
        _build_user_defined_station_meta_from_cli - D (27)

Milestone 4 gate evidence:

    python3 tools/code_quality_observability.py --base-ref origin/master --json-out /tmp/climate-quality-baseline.json --md-out /tmp/climate-quality-baseline.md
        Wrote JSON report to /tmp/climate-quality-baseline.json
        Wrote Markdown summary to /tmp/climate-quality-baseline.md
        Observe-only mode: no threshold-based failure.

    radon raw wepppy/nodb/core/climate.py
        LOC: 2377
        SLOC: 1728

    radon cc -s wepppy/nodb/core/climate.py
        max hotspot: Climate.set_single_storm_pars - C (19)
        Climate._build_climate_observed_gridmet_multiple - A (1)

    wctl run-pytest tests/nodb/test_climate_artifact_export_service.py tests/nodb/test_climate_build_router_services.py tests/nodb/test_climate_catalog.py tests/nodb/test_climate_facade_collaborators.py tests/nodb/test_climate_input_parser_service.py tests/nodb/test_climate_scaling_service.py tests/nodb/test_climate_station_catalog_service.py tests/nodb/test_climate_type_hints.py tests/climate/test_climate_scaling.py tests/climates --maxfail=1
        50 passed, 11 skipped

    wctl run-pytest tests --maxfail=1
        1923 passed, 27 skipped

    python3 - <<'PY'  # AST length verification
        ...
        max (111, 833, 'Climate.__init__')
        violations []

## Interfaces and Dependencies

Contract constraints for this package:

1. Keep `Climate` facade method signatures unchanged.
2. Keep `ClimateModeBuildServices` mode routing semantics unchanged.
3. Keep route/RQ-facing behavior unchanged through existing facade interactions.
4. Keep deterministic test harness behavior (no live network dependencies in new tests).

Plan revision notes:

1. 2026-02-21 05:53Z — Initial plan authored with baseline evidence and closure milestones. Reason: execute requested climate closure package end-to-end under an active mini ExecPlan.
2. 2026-02-21 05:55Z — Updated plan for Milestone 1 completion with focused test evidence and decision rationale. Reason: keep living sections current after each milestone.
3. 2026-02-21 05:59Z — Updated plan for Milestones 2-3 completion with extraction/test evidence and decisions. Reason: maintain milestone-by-milestone closure traceability.
4. 2026-02-21 06:06Z — Updated plan for Milestone 4 completion with required gate command evidence. Reason: satisfy hard acceptance proof requirements before closure workflow.
5. 2026-02-21 06:07Z — Updated plan to mark Milestone 5 as pending in this working tree. Reason: closure workflow evidence (move/commit/push) is not yet present.
6. 2026-02-21 06:51Z — Updated plan with post-review remediation status and evidence. Reason: keep living sections accurate after resolving review findings on completion claim, exception boundary handling, and collaborator test coverage.
7. 2026-02-21 06:58Z — Added post-review full-suite evidence with updated pass totals. Reason: record end-to-end regression confirmation after adding collaborator-level tests.
8. 2026-02-21 07:00Z — Finalized Milestone 5 closure workflow state and archived this plan under `completed/`. Reason: complete requested work-package closeout steps.
