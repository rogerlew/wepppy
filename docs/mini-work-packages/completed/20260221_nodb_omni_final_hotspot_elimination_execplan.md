# ExecPlan: Finish Omni Facade Decomposition and Enforce Hard Quality Gates in `omni.py`

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept current as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

This plan is a continuation and closure package for:

1. `docs/mini-work-packages/completed/20260221_nodb_omni_quality_refactor_execplan.md`
2. `docs/mini-work-packages/completed/20260221_nodb_omni_contrast_build_service_cc_refactor_execplan.md`

## Purpose / Big Picture

After this work, `wepppy/nodb/mods/omni/omni.py` should no longer be a high-risk concentration point for Omni behavior. The user-visible behavior must remain stable (same routes, same RQ behavior, same sidecar/report schemas), while the remaining heavy orchestration/build internals are moved behind collaborator seams with deterministic regression coverage.

This package is explicitly a closure package: do not stop at partial extraction. The package closes only when strict acceptance targets in this document are met and validated.

## Progress

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for every entry.

- [x] (2026-02-21 04:49Z) Reviewed governing guidance and baseline context (`AGENTS.md`, `wepppy/nodb/AGENTS.md`, `docs/prompt_templates/codex_exec_plans.md`), and drafted this closure ExecPlan.
- [x] (2026-02-21 04:49Z) Registered this plan as the current ad hoc active ExecPlan in `AGENTS.md`.
- [x] (2026-02-21 04:56Z) Milestone 0 complete: baseline telemetry and characterization gates captured before edits (`radon raw`: `SLOC 2329`; `radon cc` top: `_run_contrast E34`, `_omni_clone D29`, `_build_contrasts D26`, `_build_contrasts_user_defined_hillslope_groups D26`; baseline pytest groups passed: `69 passed` and `54 passed`).
- [x] (2026-02-21 04:59Z) Milestone 1 complete: `_build_contrasts_user_defined_hillslope_groups` internals moved to `OmniContrastBuildService.build_contrasts_user_defined_hillslope_groups`, and facade method reduced to delegator; milestone gate passed (`2 passed`, `57 deselected`).
- [x] (2026-02-21 05:00Z) Milestone 2 complete: `_build_contrasts` cumulative/default internals moved to `OmniContrastBuildService.build_contrasts_cumulative_default`, with facade method as delegator and milestone gate green (`15 passed`, `49 deselected`).
- [x] (2026-02-21 05:04Z) Milestone 3 attempt A failed and was rolled back: extracted `_run_contrast`/`_omni_clone` internals broke monkeypatch seam expectations (`test_omni_clone_copies_soils_from_archive_source`), so the milestone diff was reverted in full before reattempt.
- [x] (2026-02-21 05:07Z) Milestone 3 complete: `_run_contrast` and `_omni_clone` internals moved into `omni_clone_contrast_service.py`; `omni.py` wrappers remain compatibility shims and milestone gate passed (`57 passed`, `16 deselected`).
- [x] (2026-02-21 05:09Z) Milestone 4 complete: `run_omni_scenario` orchestration moved to `OmniRunOrchestrationService.run_omni_scenario`, with facade signature preserved and milestone gate green (`10 passed`, `91 deselected`).
- [x] (2026-02-21 05:11Z) Milestone 5 attempt A failed and was rolled back: new failure-boundary test monkeypatched `OmniScenario.parse` too broadly and triggered an `AttributeError` in `_scenario_name_from_scenario_definition`; milestone diff reverted before reattempt.
- [x] (2026-02-21 05:12Z) Milestone 5 complete: exception contracts tightened (`RuntimeError` for empty scenarios; explicit `TypeError` replacing runtime assert) and deterministic seam tests added; milestone gate passed (`80 passed`).
- [x] (2026-02-21 05:20Z) Milestone 6 complete: strict acceptance targets satisfied (`radon raw SLOC 1706`, `radon cc max C20`, no function >120 lines, Omni/cross-layer suites green, and full suite `1921 passed, 27 skipped` via `wctl run-pytest tests --maxfail=1`).

## Surprises & Discoveries

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for new entries.

- (2026-02-21 04:49Z) Observation: `omni.py` remains large by SLOC even after prior extractions.
  Evidence: `radon raw wepppy/nodb/mods/omni/omni.py` currently reports `LOC 2880`, `SLOC 2329`.

- (2026-02-21 04:49Z) Observation: largest remaining Omni facade complexity is concentrated in a small set of methods/functions.
  Evidence: `radon cc -s wepppy/nodb/mods/omni/omni.py` currently reports `_run_contrast (E 34)`, `_omni_clone (D 29)`, `Omni._build_contrasts (D 26)`, and `Omni._build_contrasts_user_defined_hillslope_groups (D 26)`.

- (2026-02-21 04:49Z) Observation: `omni.py` is no longer in global top-20 `python_max_cc_top20` and `python_max_function_len_top20`, but local maintainability risk remains due to facade-local method size and branching.
  Evidence: `python3 tools/code_quality_observability.py --base-ref origin/master --json-out /tmp/omni-final-hotspot-baseline.json --md-out /tmp/omni-final-hotspot-baseline.md` and local `radon` output.

- (2026-02-21 04:56Z) Observation: baseline characterization suites were already stable before extraction, so regression checks can be milestone-local and deterministic.
  Evidence: `wctl run-pytest tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_contrast_build_service.py tests/nodb/mods/test_omni_facade_contracts.py --maxfail=1` => `69 passed`; `wctl run-pytest tests/rq/test_omni_rq.py tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/routes/test_omni_bp_routes.py --maxfail=1` => `54 passed`.

- (2026-02-21 04:59Z) Observation: Milestone 1 gate key-filter selected only `test_omni.py` cases (`2 selected`) and none from `test_omni_contrast_build_service.py`.
  Evidence: `wctl run-pytest tests/nodb/mods/test_omni_contrast_build_service.py tests/nodb/mods/test_omni.py -k "user_defined_hillslope_groups" --maxfail=1` => `collected 59 items / 57 deselected / 2 selected`.

- (2026-02-21 05:00Z) Observation: cumulative/default extraction preserved branch behavior and filter normalization without contract drift in focused tests.
  Evidence: `wctl run-pytest tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_mode_build_services.py -k "build_contrasts" --maxfail=1` => `15 passed`.

- (2026-02-21 05:04Z) Observation: first Milestone 3 extraction attempt broke test monkeypatch seams by bypassing `omni.py` module-level `nodir_resolve` patching during `_omni_clone`.
  Evidence: `wctl run-pytest tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_facade_contracts.py tests/rq/test_omni_rq.py -k "run_omni_contrast or run_omni_scenario or omni_clone or contrast" --maxfail=1` failed at `tests/nodb/mods/test_omni.py::test_omni_clone_copies_soils_from_archive_source` with `NoDirError: NODIR_INVALID_ARCHIVE`.

- (2026-02-21 05:07Z) Observation: rerouted collaborator dependencies through `omni.py` contract refs preserved monkeypatch seams while still moving heavy internals out of facade.
  Evidence: rerun of Milestone 3 gate command passed (`57 passed`, `16 deselected`) after wrappers delegated to `OmniCloneContrastService` and service resolved `nodir_resolve`/related collaborators from `omni.py`.

- (2026-02-21 05:09Z) Observation: moving scenario orchestration into run collaborator preserved timed boundary logs and cross-layer scenario execution behavior.
  Evidence: `wctl run-pytest tests/nodb/mods/test_omni.py tests/rq/test_omni_rq.py tests/microservices/test_rq_engine_omni_routes.py -k "run_omni_scenario or run_omni_scenarios" --maxfail=1` => `10 passed`.

- (2026-02-21 05:11Z) Observation: initial Milestone 5 failure-boundary test failed before target contract check because `_scenario_name_from_scenario_definition` also depends on `OmniScenario.parse`.
  Evidence: Milestone 5 gate failed at `tests/nodb/mods/test_omni_facade_contracts.py::test_run_omni_scenario_raises_type_error_when_parse_result_is_not_enum` with `AttributeError: 'str' object has no attribute 'value`, then milestone diff was reverted.

- (2026-02-21 05:12Z) Observation: corrected failure-boundary test seam (parse returns non-enum object) exercises the explicit `TypeError` contract without colliding with enum string-comparison internals.
  Evidence: Milestone 5 command rerun passed (`80 passed`) with new tests in `test_omni_facade_contracts.py` and updated runtime-error expectation in `test_omni.py`.

- (2026-02-21 05:20Z) Observation: first Milestone 6 telemetry pass missed hard target #1 by a narrow margin (`Omni.delete_scenarios` at `D (21)`), requiring one additional micro-refactor before final gates.
  Evidence: `radon cc -s wepppy/nodb/mods/omni/omni.py` initially reported `Omni.delete_scenarios - D (21)`; after extracting `_remove_scenario_artifacts`, rerun reported `Omni.delete_scenarios - C (17)` and max method `C (20)`.

- (2026-02-21 05:20Z) Observation: final strict closeout gates are green across telemetry and full-suite execution.
  Evidence: `radon raw` => `SLOC 1706`; `radon cc` => max `C (20)`; function-length scan => `max_function_length=82` with `violations=[]`; full suite => `1921 passed, 27 skipped`.

## Decision Log

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for new entries.

- Decision: treat this package as closure-only with hard acceptance gates instead of another exploratory extraction pass.
  Rationale: prior packages reduced hotspots but left recurring residual complexity; this package must end the loop with objective stop criteria.
  Date/Author: 2026-02-21 04:49Z / Codex

- Decision: preserve all facade entrypoint signatures and quasi-public helper names while moving internals to collaborators.
  Rationale: route/RQ/tests depend on existing call surface; contract churn is riskier than internal extraction.
  Date/Author: 2026-02-21 04:49Z / Codex

- Decision: only declare completion after full-suite gates pass and strict telemetry thresholds are met.
  Rationale: prevents another partial “done-but-not-done” outcome.
  Date/Author: 2026-02-21 04:49Z / Codex

- Decision: keep milestone execution strict and sequential with immediate per-milestone plan updates, even when gates are already green.
  Rationale: user requested end-to-end execution with no skipped bookkeeping, and milestone evidence must be attributable to the exact change window.
  Date/Author: 2026-02-21 04:56Z / Codex

- Decision: preserve user-defined hillslope-groups behavior by extracting to collaborator with helper-level parity and leaving the facade signature/body as a single delegator.
  Rationale: this removes one facade hotspot while preserving monkeypatch/import compatibility and report schema stability.
  Date/Author: 2026-02-21 04:59Z / Codex

- Decision: keep the existing `build_contrast_mapping(..., contrast_id=topaz_id)` invocation unchanged during `_build_contrasts` extraction, despite non-intuitive ID argument usage.
  Rationale: this call shape is existing behavior and changing it would be a contract risk during hotspot elimination.
  Date/Author: 2026-02-21 05:00Z / Codex

- Decision: reattempt Milestone 3 extraction only with collaborator methods that resolve runtime dependencies through `omni.py` module contract refs so monkeypatch seams remain intact.
  Rationale: Omni tests patch module-level symbols (`nodir_resolve`, projection helpers, run wrappers) and expect wrappers to honor those seams.
  Date/Author: 2026-02-21 05:04Z / Codex

- Decision: keep `_run_contrast` and `_omni_clone` as module-level wrappers that delegate into a new `OmniCloneContrastService`, rather than importing helpers directly inside the service module.
  Rationale: wrapper compatibility plus module-level ref resolution preserves existing patch points while eliminating facade hotspots.
  Date/Author: 2026-02-21 05:07Z / Codex

- Decision: keep `run_omni_scenario` facade method as a single delegator and place all orchestration/timing blocks in `OmniRunOrchestrationService.run_omni_scenario`.
  Rationale: this removes another large facade hotspot while preserving the `(omni_dir, scenario_name)` return contract and existing service centralization.
  Date/Author: 2026-02-21 05:09Z / Codex

- Decision: reattempt Milestone 5 using a narrower failure-boundary test seam (patch scenario-name helper separately) so the explicit exception contract is exercised directly.
  Rationale: the first test patch unintentionally altered upstream helper behavior and did not isolate the intended contract boundary.
  Date/Author: 2026-02-21 05:11Z / Codex

- Decision: use `TypeError("Invalid omni scenario type: ...")` for the former assert boundary and retain the exact `"No scenarios to run"` message under `RuntimeError`.
  Rationale: explicit exception types satisfy contract clarity while preserving message compatibility for existing assertions.
  Date/Author: 2026-02-21 05:12Z / Codex

- Decision: reduce `delete_scenarios` complexity with a helper extraction (`_remove_scenario_artifacts`) instead of behavior changes.
  Rationale: hard target required `<= C (20)` and this was the smallest safe refactor preserving existing missing/removed list semantics.
  Date/Author: 2026-02-21 05:20Z / Codex

## Outcomes & Retrospective

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for new entries.

- (2026-02-21 04:49Z) Outcome: authored closure-focused ExecPlan with strict acceptance thresholds and installed it as active ad hoc plan.
- (2026-02-21 04:49Z) Retrospective: prior packages proved the collaborator pattern works; remaining work is consolidation and hard-threshold closeout, not design discovery.
- (2026-02-21 04:56Z) Outcome: Milestone 0 baseline freeze completed with full telemetry and characterization evidence recorded in-plan; no pre-existing gate failures blocked extraction work.
- (2026-02-21 04:59Z) Outcome: Milestone 1 extraction landed with contract-preserving facade delegation and green milestone-local tests.
- (2026-02-21 05:00Z) Outcome: Milestone 2 extraction landed with focused `build_contrasts` regression suite green, keeping cumulative/default contracts intact.
- (2026-02-21 05:04Z) Outcome: Milestone 3 attempt A was safely rolled back after a deterministic seam regression, preserving pre-milestone behavior before retry.
- (2026-02-21 05:07Z) Outcome: Milestone 3 finalized with collaborator extraction plus preserved wrapper seams; targeted scenario/contrast/clone tests are green.
- (2026-02-21 05:09Z) Outcome: Milestone 4 completed with run-scenario orchestration moved to collaborator and scenario-oriented regression gate passing.
- (2026-02-21 05:11Z) Outcome: Milestone 5 attempt A was rolled back cleanly after test-boundary design error; repository remained at post-Milestone-4 behavior before retry.
- (2026-02-21 05:12Z) Outcome: Milestone 5 finalized with explicit exception contracts and deterministic delegation/failure-boundary regression coverage.
- (2026-02-21 05:20Z) Outcome: Milestone 6 hard acceptance targets all satisfied; closure criteria met with full test-suite confirmation.

## Context and Orientation

Primary Omni files in scope:

1. `wepppy/nodb/mods/omni/omni.py` (facade + residual heavy methods/functions).
2. `wepppy/nodb/mods/omni/omni_contrast_build_service.py` (current contrast mode collaborator).
3. `wepppy/nodb/mods/omni/omni_run_orchestration_service.py` (scenario/contrast run orchestration collaborator).
4. `wepppy/nodb/mods/omni/omni_build_router.py` (build input routing).
5. `wepppy/nodb/mods/omni/omni_mode_build_services.py` (mode behavior and shared mapping).
6. `wepppy/nodb/mods/omni/omni_artifact_export_service.py` (report/export seams).
7. `wepppy/nodb/mods/omni/omni_station_catalog_service.py` (scenario/landuse/dependency helpers).
8. `wepppy/nodb/mods/omni/omni.pyi` (public typed surface).

Cross-layer contracts that must remain stable:

1. `wepppy/rq/omni_rq.py`
2. `wepppy/rq/path_ce_rq.py`
3. `wepppy/microservices/rq_engine/omni_routes.py`
4. `wepppy/weppcloud/routes/nodb_api/omni_bp.py`
5. `wepppy/weppcloud/routes/gl_dashboard.py`

Minimum deterministic suites for behavioral parity:

1. `tests/nodb/mods/test_omni.py`
2. `tests/nodb/mods/test_omni_contrast_build_service.py`
3. `tests/nodb/mods/test_omni_facade_contracts.py`
4. `tests/nodb/mods/test_omni_*_service.py` suites touched by extraction.
5. `tests/rq/test_omni_rq.py`
6. `tests/microservices/test_rq_engine_omni_routes.py`
7. `tests/weppcloud/routes/test_omni_bp.py`
8. `tests/weppcloud/routes/test_omni_bp_routes.py`

Current measurable baseline:

1. `radon raw wepppy/nodb/mods/omni/omni.py`: `LOC 2880`, `SLOC 2329`.
2. `radon cc -s wepppy/nodb/mods/omni/omni.py` top methods include `_run_contrast (E 34)`, `_omni_clone (D 29)`, `_build_contrasts (D 26)`, `_build_contrasts_user_defined_hillslope_groups (D 26)`.

## Invariants

1. No route/RQ/facade contract drift unless explicitly approved and documented.
2. Preserve NoDb lock and persistence boundaries (`with self.locked()`, `nodb_setter`, dependency-tree/status writers).
3. Preserve contrast sidecar schema and `build_report.ndjson` field contracts.
4. Preserve module-level compatibility seams used by tests/monkeypatching where already relied upon.
5. No silent broad exception swallowing in production flow.
6. Do not mark the package complete until all strict acceptance targets are met.

## Milestone Plan

### Milestone 0: Baseline Freeze and Characterization Gates

Scope:
Record immutable before-state telemetry and verify cross-layer characterization tests are green before extraction.

Target files:

1. `wepppy/nodb/mods/omni/omni.py` (read-only this milestone).
2. Omni collaborator modules (read-only this milestone).
3. Characterization tests listed in Context section.

Validation commands:

    python3 tools/code_quality_observability.py --base-ref origin/master --json-out /tmp/omni-final-hotspot-baseline.json --md-out /tmp/omni-final-hotspot-baseline.md
    radon raw wepppy/nodb/mods/omni/omni.py
    radon cc -s wepppy/nodb/mods/omni/omni.py
    wctl run-pytest tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_contrast_build_service.py tests/nodb/mods/test_omni_facade_contracts.py --maxfail=1
    wctl run-pytest tests/rq/test_omni_rq.py tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/routes/test_omni_bp_routes.py --maxfail=1

Go/No-Go:

1. `NO-GO` if baseline tests fail before edits.
2. `NO-GO` if baseline metrics are not captured in this plan.

### Milestone 1: Extract User-Defined-Hillslope-Groups Builder Out of Facade

Scope:
Move all internals of `Omni._build_contrasts_user_defined_hillslope_groups` into `OmniContrastBuildService`, keeping a facade delegator only.

Target files:

1. `wepppy/nodb/mods/omni/omni.py`
2. `wepppy/nodb/mods/omni/omni_contrast_build_service.py`
3. `wepppy/nodb/mods/omni/omni.pyi` (if typed surface changes are needed)
4. `tests/nodb/mods/test_omni_contrast_build_service.py`
5. `tests/nodb/mods/test_omni.py`

Required work:

1. Preserve error messages and report entry schema.
2. Preserve signature-map/id assignment behavior and contrast label behavior.
3. Keep facade method name/signature unchanged.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni_contrast_build_service.py tests/nodb/mods/test_omni.py -k "user_defined_hillslope_groups" --maxfail=1

Go/No-Go:

1. `NO-GO` if contrast IDs, names, labels, or report schema drift.

### Milestone 2: Extract Cumulative/Default Builder Out of Facade

Scope:
Move `Omni._build_contrasts` orchestration internals into collaborator methods; keep facade method as delegator.

Target files:

1. `wepppy/nodb/mods/omni/omni.py`
2. `wepppy/nodb/mods/omni/omni_contrast_build_service.py` and/or `wepppy/nodb/mods/omni/omni_mode_build_services.py`
3. `tests/nodb/mods/test_omni.py`
4. `tests/nodb/mods/test_omni_mode_build_services.py`

Required work:

1. Preserve selection-mode branching semantics.
2. Preserve hill-limit and advanced-filter normalization behavior.
3. Preserve sidecar/report generation and cumulative threshold stop behavior.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_mode_build_services.py -k "build_contrasts" --maxfail=1

Go/No-Go:

1. `NO-GO` if cumulative selection behavior or filter contracts regress.

### Milestone 3: Extract Clone/Contrast Execution Internals from `omni.py`

Scope:
Move heavy module-level internals of `_run_contrast` and `_omni_clone` into dedicated collaborator modules/services. Keep module-level wrapper names in `omni.py` for compatibility.

Target files:

1. `wepppy/nodb/mods/omni/omni.py`
2. New collaborator(s) under `wepppy/nodb/mods/omni/` (for clone and contrast execution internals)
3. `tests/nodb/mods/test_omni.py`
4. `tests/nodb/mods/test_omni_facade_contracts.py`
5. `tests/rq/test_omni_rq.py`

Required work:

1. Keep `_run_contrast(...)` and `_omni_clone(...)` callable from existing import sites.
2. Preserve side effects for clone paths, nodb rewrite behavior, and output trigger behavior.
3. Preserve compatibility with existing run orchestration service imports.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_facade_contracts.py tests/rq/test_omni_rq.py -k "run_omni_contrast or run_omni_scenario or omni_clone or contrast" --maxfail=1

Go/No-Go:

1. `NO-GO` if scenario clone directory/output contracts or contrast run behavior drift.

### Milestone 4: Extract `run_omni_scenario` Body to Run Collaborator

Scope:
Reduce `Omni.run_omni_scenario` to facade delegation while preserving signature and behavior.

Target files:

1. `wepppy/nodb/mods/omni/omni.py`
2. `wepppy/nodb/mods/omni/omni_run_orchestration_service.py`
3. `tests/nodb/mods/test_omni.py`
4. `tests/rq/test_omni_rq.py`
5. `tests/microservices/test_rq_engine_omni_routes.py`

Required work:

1. Preserve scenario-specific routing logic (including base-scenario/sibling clone semantics).
2. Preserve timed logging boundaries and post-run hooks.
3. Preserve return tuple `(omni_dir, scenario_name)` contract.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni.py tests/rq/test_omni_rq.py tests/microservices/test_rq_engine_omni_routes.py -k "run_omni_scenario or run_omni_scenarios" --maxfail=1

Go/No-Go:

1. `NO-GO` if orchestration dependency semantics or return contract changes.

### Milestone 5: Exception Contract Tightening + Deterministic Gap Closure

Scope:
Close remaining explicit contract issues and broaden deterministic coverage for new seams.

Target files:

1. `wepppy/nodb/mods/omni/omni.py`
2. `wepppy/nodb/mods/omni/omni_run_orchestration_service.py`
3. Affected deterministic Omni tests.

Required work:

1. Replace generic `raise Exception("No scenarios to run")` with `RuntimeError` and preserve message contract if asserted.
2. Replace runtime `assert` usage in production path with explicit exception contract.
3. Add tests for new seam delegation argument passthrough and failure boundaries.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_facade_contracts.py tests/nodb/mods/test_omni_contrast_build_service.py tests/rq/test_omni_rq.py --maxfail=1

Go/No-Go:

1. `NO-GO` if exception semantics become less explicit or regress existing tests.

### Milestone 6: Strict Closeout Gates (Hard Acceptance)

Scope:
Finalize metrics and gates; package is incomplete unless every target below is met.

Validation commands:

    python3 tools/code_quality_observability.py --base-ref origin/master --json-out /tmp/omni-final-hotspot-after.json --md-out /tmp/omni-final-hotspot-after.md
    radon raw wepppy/nodb/mods/omni/omni.py
    radon cc -s wepppy/nodb/mods/omni/omni.py
    wctl run-pytest tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_contrast_build_service.py tests/nodb/mods/test_omni_mode_build_services.py tests/nodb/mods/test_omni_artifact_export_service.py tests/nodb/mods/test_omni_station_catalog_service.py tests/nodb/mods/test_omni_facade_contracts.py --maxfail=1
    wctl run-pytest tests/rq/test_omni_rq.py tests/rq/test_path_ce_rq.py tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/routes/test_omni_bp_routes.py tests/weppcloud/routes/test_gl_dashboard_route.py --maxfail=1
    wctl run-pytest tests --maxfail=1

Hard acceptance targets (all required):

1. `radon cc -s wepppy/nodb/mods/omni/omni.py` has no function/method above `C (20)`.
2. `radon raw wepppy/nodb/mods/omni/omni.py` reports `SLOC <= 1900`.
3. `omni.py` contains no function/method longer than `120` lines.
4. All listed Omni-focused and cross-layer suites pass.
5. `wctl run-pytest tests --maxfail=1` passes.

Completion rule:

1. If any hard acceptance target fails, this work-package remains active and is not moved to `completed/`.

## Concrete Steps

Run all commands from `/workdir/wepppy`.

1. Execute Milestone 0 commands and record outputs in `Progress`, `Surprises & Discoveries`, and `Outcomes & Retrospective`.
2. Execute Milestones 1 through 5 sequentially with milestone-local test gates after each milestone.
3. Execute Milestone 6 closeout commands and compare against hard acceptance targets.
4. Only after all hard targets pass, mark this plan complete and move it to `docs/mini-work-packages/completed/`.

## Validation and Acceptance

Global acceptance requires every Hard acceptance target in Milestone 6 plus:

1. No route/RQ/facade contract drift.
2. No schema drift for contrast sidecars and build reports.
3. No new broad exception swallow behavior in production paths without explicit boundary comments.

## Risk and Rollback

1. Risk: extracting clone/run internals changes subtle filesystem side effects.
   Mitigation: preserve wrappers and run scenario/contrast regression tests per milestone.
   Rollback: revert only latest milestone and re-run milestone-local gates.

2. Risk: collaborator extraction causes import-cycle or seam regressions.
   Mitigation: keep wrappers in `omni.py` and import collaborators lazily where needed.
   Rollback: restore prior wrapper body and retain added tests as characterization.

3. Risk: hard threshold misses by small deltas late in package.
   Mitigation: reserve final mini-pass in Milestone 6 to move residual low-value boilerplate/delegators out of `omni.py`.
   Rollback: keep package active until thresholds pass; do not archive as complete.

## Idempotence and Recovery

This plan is milestone-idempotent. If a milestone fails:

1. Revert only that milestone’s diff.
2. Re-run the milestone’s validation commands.
3. Update living sections with failure evidence and revised approach.

Do not proceed to the next milestone until current milestone gates are green.

## Out of Scope

1. Frontend/UI redesign.
2. RQ dependency-graph rewiring unrelated to Omni contract preservation.
3. New Omni features or schema expansions.

## Artifacts and Notes

Record as work proceeds:

1. Before/after `radon raw` and `radon cc` snippets for `omni.py`.
2. Pass/fail summaries for each milestone gate command.
3. Explicit notes for any preserved boundary broad-catch blocks.

Revision Note (2026-02-21 04:49Z, Codex): Authored closure-focused mini work-package with hard quality thresholds to finish Omni facade decomposition and prevent another partial completion cycle.
Revision Note (2026-02-21 04:56Z, Codex): Recorded Milestone 0 command evidence, marked baseline gate completion, and updated living sections before Milestone 1 edits.
Revision Note (2026-02-21 04:59Z, Codex): Completed Milestone 1 collaborator extraction for user-defined hillslope groups and captured milestone-local validation evidence.
Revision Note (2026-02-21 05:00Z, Codex): Completed Milestone 2 cumulative/default builder extraction and recorded focused validation evidence.
Revision Note (2026-02-21 05:04Z, Codex): Logged Milestone 3 attempt-A failure evidence, reverted the failed milestone diff, and recorded the compatibility-focused reattempt decision.
Revision Note (2026-02-21 05:07Z, Codex): Completed Milestone 3 with compatibility-safe collaborator extraction for `_run_contrast` and `_omni_clone`, then captured green gate evidence.
Revision Note (2026-02-21 05:09Z, Codex): Completed Milestone 4 by extracting `run_omni_scenario` into run orchestration service and recorded focused scenario-run validation evidence.
Revision Note (2026-02-21 05:11Z, Codex): Logged Milestone 5 attempt-A failure evidence, reverted milestone-local changes, and recorded the corrected reattempt plan.
Revision Note (2026-02-21 05:12Z, Codex): Completed Milestone 5 exception-contract tightening and deterministic seam regression coverage with green validation.
Revision Note (2026-02-21 05:20Z, Codex): Completed Milestone 6 strict closeout gates, including full-suite validation and final hotspot micro-refactor for `delete_scenarios`.
