# ExecPlan: Omni Per-Scenario Cumulative Filters and Scenario Name Disambiguation

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept current as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

Status: Complete
Last Updated: 2026-05-13 23:14Z (UTC)
Primary Areas: `wepppy/weppcloud/templates/controls/omni_scenarios_pure.htm`, `wepppy/weppcloud/templates/controls/omni_contrasts_pure.htm`, `wepppy/weppcloud/controllers_js/omni.js`, `wepppy/nodb/mods/omni/omni.py`, `wepppy/nodb/mods/omni/omni_input_parser.py`, `wepppy/microservices/rq_engine/omni_routes.py`, `wepppy/nodb/mods/omni/omni_mode_build_services.py`, `tests/nodb/mods/test_omni_input_parser_service.py`, `tests/nodb/mods/test_omni_facade_contracts.py`, `tests/microservices/test_rq_engine_omni_routes.py`, `tests/nodb/mods/test_omni_mode_build_services.py`, `tests/nodb/mods/test_omni_scaling_service.py`, `wepppy/weppcloud/controllers_js/__tests__/omni.test.js`, `wepppy/nodb/mods/omni/README.md`.

## Purpose / Big Picture

Omni users need to define multiple scenarios that share the same treatment definition (for example, `mulch_60_sbs_map`) but differ by filters. After this package, only `prescribed_fire`, `mulch`, and `thinning` scenario items will render a collapsed-by-default **Filters** section. The filters section mirrors the current cumulative filters UI shape but includes only visible slope and burn-severity inputs. Scenario identity will include filter parameters when present so otherwise identical scenarios can coexist and appear as distinct selectable names in Omni Contrasts. These per-scenario filters will be used as treatment-application masks for `mulch`, `prescribed_fire`, and `thinning` scenarios.

## Progress

- [x] (2026-05-13 20:58Z) Mapped current Omni scenario UI, contrast UI, scenario serialization, and scenario-name generation in JS and Python.
- [x] (2026-05-13 21:08Z) Mapped NoDb parse/store behavior and rq-engine request parsing for `run-omni` and `run-omni-contrasts`.
- [x] (2026-05-13 21:20Z) Mapped downstream name consumers (scenario deletion, run markers, artifact paths, contrast selection options).
- [x] (2026-05-13 21:35Z) Authored this mini work-package ExecPlan including decision points and validation gates.
- [x] (2026-05-13 21:54Z) Incorporated operator decisions: keep global cumulative filters, per-scenario visible filters only (slope + burn severity), human-readable naming, integer slope constraints, and precedence `global then per-scenario`.
- [x] (2026-05-13 22:54Z) Resolved semantics decision: for `prescribed_fire`/`thinning`, burn-severity filters evaluate against base/project SBS burn classes when available; otherwise burn filtering is ignored while slope filtering remains active.
- [x] (2026-05-13 23:03Z) Implemented UI, serialization, naming, backend parsing, and contrast integration changes.
- [x] (2026-05-13 23:04Z) Added regression tests and updated Omni documentation.
- [x] (2026-05-13 23:12Z) Ran required validation set and recorded outcomes.
- [x] (2026-05-13 23:14Z) Completed independent code review and independent QA review; dispositioned all findings with evidence.

## Surprises & Discoveries

- Observation: scenario names are generated in two independent locations (`scenarioNameFromDefinition` in JS and `_scenario_name_from_scenario_definition` in Python).
  Evidence: `wepppy/weppcloud/controllers_js/omni.js` and `wepppy/nodb/mods/omni/omni.py` both build scenario names.

- Observation: `run-omni` parsing currently preserves only type-specific scenario fields; unknown per-scenario keys are dropped when persisting `_scenarios`.
  Evidence: `OmniInputParsingService.parse_scenarios` in `wepppy/nodb/mods/omni/omni_input_parser.py` appends only the current known keys for each scenario type.

- Observation: cumulative filters are currently only top-level contrast inputs, not per-scenario inputs.
  Evidence: `_prepare_omni_contrasts` in `wepppy/microservices/rq_engine/omni_routes.py` parses `omni_contrast_hill_min_slope`, `omni_contrast_hill_max_slope`, `omni_contrast_select_burn_severities`, and `omni_contrast_select_topaz_ids`; `_prepare_omni_scenarios` does not.

- Observation: scenario names are used as filesystem directory keys under `_pups/omni/scenarios/<scenario_name>` and as contrast option values.
  Evidence: `_omni_clone` pathing (`wepppy/nodb/mods/omni/omni_clone_contrast_service.py`) and contrast option builder (`buildContrastScenarioOptions` in `wepppy/weppcloud/controllers_js/omni.js`).

- Observation: treatment application for `mulch`, `prescribed_fire`, and `thinning` already constructs a `treatments_domlc_d` per-topaz map in one place that can host the new per-scenario mask.
  Evidence: `OmniModeBuildServices.apply_scenario_mode` branches in `wepppy/nodb/mods/omni/omni_mode_build_services.py` build `treatments_domlc_d` loops for all three modes.

- Observation: `wctl doc-lint` panics when passed absolute paths in this environment.
  Evidence: panic output `path is expected to be under the root` for required absolute-path invocations; relative-path invocations pass.

- Observation: `wctl run-npm lint` currently fails due pre-existing non-Omni Jest lint errors.
  Evidence: `wepppy/weppcloud/controllers_js/__tests__/disturbed.test.js` and `wepppy/weppcloud/controllers_js/__tests__/landuse_map_inline.test.js` (`jest/no-conditional-expect`).

## Decision Log

- Decision: scope this as a scenario-contract extension, not a one-off UI patch.
  Rationale: the request requires persistence, naming, and contrast-selection behavior consistency across frontend and backend.
  Date/Author: 2026-05-13 / Codex

- Decision: keep backward compatibility by preserving existing scenario names when no per-scenario filters are set.
  Rationale: existing run artifacts, scenario deletion, and contrast references depend on current naming for unfiltered scenarios.
  Date/Author: 2026-05-13 / Codex

- Decision: include explicit operator decisions before implementation where behavior could diverge.
  Rationale: per-scenario filters can be interpreted as metadata-only, naming-only, or executable contrast-selection parameters.
  Date/Author: 2026-05-13 / Codex

- Decision: keep global cumulative filters in Omni Contrasts with current behavior.
  Rationale: explicit operator request; cumulative contrast workflow remains unchanged.
  Date/Author: 2026-05-13 / Operator+Codex

- Decision: per-scenario Filters UI includes only visible slope and burn-severity fields (no Topaz IDs input).
  Rationale: explicit operator request.
  Date/Author: 2026-05-13 / Operator+Codex

- Decision: constrain slope min/max to integer percent values in both scenario filters and cumulative contrast filters.
  Rationale: explicit operator request to simplify human-readable scenario names.
  Date/Author: 2026-05-13 / Operator+Codex

- Decision: precedence is `global then per-scenario`.
  Rationale: explicit operator request.
  Date/Author: 2026-05-13 / Operator+Codex

- Decision: only `prescribed_fire`, `mulch`, and `thinning` scenario rows render the Filters collapsible.
  Rationale: explicit operator request to avoid exposing irrelevant filter controls on non-treatment scenario types.
  Date/Author: 2026-05-13 / Operator+Codex

- Decision: require explicit code-review and QA-review disposition prior to handoff.
  Rationale: explicit operator request for review integration and disposition traceability.
  Date/Author: 2026-05-13 / Operator+Codex

- Decision: for `prescribed_fire` and `thinning`, per-scenario burn-severity filtering reads burn classes from base/project SBS context when available; if unavailable, burn filtering is ignored (no hard failure) while slope filtering remains active.
  Rationale: explicit operator semantics decision balancing treatment-mask fidelity with backward-compatible execution in undisturbed clone contexts.
  Date/Author: 2026-05-13 / Operator+Codex

- Decision: align JS scenario-name filter normalization with Python legacy fractional slope handling (`0.1` -> `10`) to keep naming parity in edge-case historic payloads while continuing to emit integer-percentage suffixes.
  Rationale: avoids JS/Python scenario-name drift for legacy values and preserves deterministic naming.
  Date/Author: 2026-05-13 / Codex

## Outcomes & Retrospective

- (2026-05-13 21:59Z) Outcome: discovery and planning complete; major decisions captured. One semantics decision remained for burn-severity filtering in undisturbed treatment contexts.
- (2026-05-13 22:54Z) Outcome: semantics decision is now resolved; implementation phase started.
- (2026-05-13 23:14Z) Outcome: implementation, validation, documentation, and review-disposition workflow complete. Required behavior constraints are implemented, tested, and documented.

## Context and Orientation

Current Omni behavior spans three layers.

Frontend scenario authoring is in `wepppy/weppcloud/controllers_js/omni.js`, with static shell markup in `wepppy/weppcloud/templates/controls/omni_scenarios_pure.htm`. Scenario rows are rendered dynamically in JS via `addScenario()` and `updateScenarioControls()`. Scenario definitions are serialized by `serializeScenarios()` and posted to `/rq-engine/api/runs/<runid>/<config>/run-omni`.

Frontend contrast selection is in `wepppy/weppcloud/templates/controls/omni_contrasts_pure.htm` and `wepppy/weppcloud/controllers_js/omni.js`. The existing “Cumulative filters” card lives under “Advanced options” and is currently global to the contrast request.

Backend scenario persistence and naming flow through `wepppy/microservices/rq_engine/omni_routes.py` (`_prepare_omni_scenarios`), `wepppy/nodb/mods/omni/omni_input_parser.py` (`parse_scenarios`), and `wepppy/nodb/mods/omni/omni.py` (`_scenario_name_from_scenario_definition`). Treatment application for `mulch`, `prescribed_fire`, and `thinning` is in `wepppy/nodb/mods/omni/omni_mode_build_services.py`, where per-topaz treatment maps are created before `Treatments.build_treatments()`.

## Open Questions / Decision Points

None remaining. Prior open question resolved: `prescribed_fire`/`thinning` burn-severity filtering uses project/base SBS burn classes when available, and is ignored (without hard failure) when unavailable.

## Compatibility and Regression Strategy

This package mutates the Omni scenario-definition contract (NoDb payload) and scenario naming contract (directory keys and contrast option values). Compatibility plan:

- Additive schema evolution: new per-scenario filter keys are optional and absent in legacy scenarios.
- Name stability for legacy rows: unfiltered scenario names must remain byte-for-byte identical to current behavior.
- Deterministic naming: filtered-name generation must be canonical and identical in JS and Python.
- Regression safety: existing artifacts under current unfiltered names must continue resolving via `_normalize_scenario_key`, run-marker lookup, and contrast status paths.

Regression evidence will include targeted tests for parsing, naming, contrast selection options, and route payload coercion.

## Plan of Work

### Milestone 1: Define per-scenario filter contract and canonical naming

Add a canonical per-scenario filter contract with explicit optional keys stored inside each scenario definition payload. Define a deterministic human-readable suffix appended to scenario names only when at least one filter is set. Slope fields are integer percentages. Implement the naming algorithm in both JS and Python with matching normalization rules.

Target edits:

- `wepppy/weppcloud/controllers_js/omni.js` (`scenarioNameFromDefinition` and helper normalization).
- `wepppy/nodb/mods/omni/omni.py` (`_scenario_name_from_scenario_definition` plus helper).
- `wepppy/nodb/mods/omni/omni_scaling_service.py` for shared integer-percent normalization utilities.

### Milestone 2: Add conditional per-scenario Filters collapsible UI and serialization/hydration

Extend scenario-row rendering so only `prescribed_fire`, `mulch`, and `thinning` scenario items include a **Filters** collapsible section collapsed by default, with fields matching cumulative filters shape but only: minimum slope (%), maximum slope (%), burn severities. All other scenario types must render with no Filters collapsible. Ensure scenario serialization writes filter keys into each scenario definition and backend hydration (`load_scenarios_from_backend`) repopulates these fields.

Target edits:

- `wepppy/weppcloud/templates/controls/omni_scenarios_pure.htm` (shell/template hooks if needed).
- `wepppy/weppcloud/controllers_js/omni.js` (row rendering, control generation, serialization, hydration, run-state updates).
- `wepppy/weppcloud/static/css/ui-foundation.css` only if row layout adjustments are needed for responsive behavior.

### Milestone 3: Persist per-scenario filter fields in NoDb scenario state

Expand `run-omni` parsing and NoDb scenario parsing to preserve per-scenario filter values in `_scenarios` while keeping current validation for scenario type-specific required fields.

Target edits:

- `wepppy/microservices/rq_engine/omni_routes.py` (`_prepare_omni_scenarios` coercion/validation of scenario-local filter values).
- `wepppy/nodb/mods/omni/omni_input_parser.py` (`parse_scenarios` to include new optional fields in persisted scenario dictionaries).

### Milestone 4: Apply per-scenario filter masks during treatment scenario execution

Apply per-scenario filters only to treatment-scenario application maps for `mulch`, `prescribed_fire`, and `thinning`. The mask determines whether a candidate hillslope receives treatment assignment in `treatments_domlc_d`. Keep all global cumulative contrast filters working exactly as they do today, with slope fields constrained to integers and precedence `global then per-scenario` where both contribute to effective filtering behavior.

Target edits:

- `wepppy/nodb/mods/omni/omni_mode_build_services.py` (filter helper and per-scenario mask application).
- `wepppy/nodb/mods/omni/omni_scaling_service.py` (reuse/extend burn-class and integer slope normalization logic as shared utility).
- `wepppy/microservices/rq_engine/omni_routes.py` and `wepppy/weppcloud/templates/controls/omni_contrasts_pure.htm` (global cumulative slope field integer constraints).

### Milestone 5: Regression tests, docs, and bundle rebuild

Add/adjust tests for scenario naming parity, per-scenario filter persistence, treatment-mask behavior for `mulch`/`prescribed_fire`/`thinning`, and contrast option uniqueness. Update Omni docs to describe new scenario filters, naming behavior, and precedence rules.

Target edits:

- `wepppy/weppcloud/controllers_js/__tests__/omni.test.js`
- `tests/nodb/mods/test_omni_input_parser_service.py`
- `tests/nodb/mods/test_omni_facade_contracts.py`
- `tests/nodb/mods/test_omni_mode_build_services.py`
- `tests/nodb/mods/test_omni_scaling_service.py`
- `tests/microservices/test_rq_engine_omni_routes.py`
- `wepppy/nodb/mods/omni/README.md`

### Milestone 6: Code Review + QA Review Disposition

Run an independent correctness/risk code review and an independent QA-oriented review after implementation and initial test pass. Capture every finding with disposition in this ExecPlan before handoff.

Required disposition categories:

- `fixed`: issue confirmed and corrected in this change set.
- `accepted-risk`: issue confirmed but intentionally deferred with rationale.
- `not-repro`: issue could not be reproduced with evidence.
- `not-applicable`: reviewer concern does not apply to final implementation.

For each finding, record:

- finding summary
- affected file/function
- severity
- disposition category
- evidence (test name, command output summary, or code pointer)

## Concrete Steps

Run from `/workdir/wepppy`.

1. Resolve remaining semantics decision in “Open Questions / Decision Points”.
2. Implement Milestone 1 naming contract in JS + Python.
3. Implement Milestone 2 UI/serialization/hydration changes.
4. Implement Milestone 3 backend scenario parsing/persistence changes.
5. Implement Milestone 4 treatment-mask behavior in scenario execution and integer constraint updates for global cumulative slope fields.
6. Add/adjust tests in Milestone 5.
7. Rebuild controllers bundle.
8. Run validations and capture results in this plan.
9. Run Milestone 6 reviews and disposition all findings in this plan.
10. Update Omni documentation.

## Validation and Acceptance

Primary acceptance criteria:

1. Only `prescribed_fire`, `mulch`, and `thinning` scenario items render a collapsed-by-default Filters section.
2. Non-treatment scenario items (`uniform_*`, `sbs_map`, `undisturbed`) render with no Filters collapsible.
3. Two otherwise identical scenario definitions can coexist when their filter values differ.
4. Filtered scenarios appear as distinct names in Omni Contrasts options.
5. Unfiltered scenario names are unchanged from current behavior.
6. Persisted scenarios round-trip (`run-omni` save, `get_scenarios` load) with filter fields intact.
7. Treatment application for `mulch`, `prescribed_fire`, and `thinning` respects the configured filter mask.
8. Global cumulative slope filter fields accept only integer percentages and retain current functionality.
9. Code review and QA review findings are dispositioned and recorded in this plan.

Validation commands:

- `wctl run-npm lint`
- `wctl run-npm test -- omni`
- `python wepppy/weppcloud/controllers_js/build_controllers_js.py`
- `wctl run-pytest tests/nodb/mods/test_omni_input_parser_service.py tests/nodb/mods/test_omni_facade_contracts.py tests/nodb/mods/test_omni_mode_build_services.py tests/nodb/mods/test_omni_scaling_service.py tests/microservices/test_rq_engine_omni_routes.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods/test_omni_contrast_build_service.py tests/nodb/mods/test_omni_run_orchestration_service.py tests/nodb/mods/test_omni_build_router_service.py --maxfail=1`
- `wctl doc-lint --path docs/mini-work-packages/20260513_omni_per_scenario_cumulative_filters_execplan.md`
- `wctl doc-lint --path wepppy/nodb/mods/omni/README.md`

### Validation Results (2026-05-13)

- `wctl run-npm lint`
  - Result: `fail` (pre-existing unrelated lint errors)
  - Evidence: `jest/no-conditional-expect` in:
    - `wepppy/weppcloud/controllers_js/__tests__/disturbed.test.js:185`
    - `wepppy/weppcloud/controllers_js/__tests__/landuse_map_inline.test.js:99,100,101,103`
- `wctl run-npm test -- omni`
  - Result: `pass`
  - Evidence: `2 passed, 0 failed` suites; `15 passed` tests.
- `python wepppy/weppcloud/controllers_js/build_controllers_js.py`
  - Result: `pass`
- `wctl run-pytest tests/nodb/mods/test_omni_input_parser_service.py tests/nodb/mods/test_omni_facade_contracts.py tests/nodb/mods/test_omni_mode_build_services.py tests/nodb/mods/test_omni_scaling_service.py tests/microservices/test_rq_engine_omni_routes.py --maxfail=1`
  - Result: `pass`
  - Evidence: `96 passed, 0 failed` (`8 warnings`).
- `wctl run-pytest tests/nodb/mods/test_omni_contrast_build_service.py tests/nodb/mods/test_omni_run_orchestration_service.py tests/nodb/mods/test_omni_build_router_service.py --maxfail=1`
  - Result: `pass`
  - Evidence: `37 passed, 0 failed` (`2 warnings`).
- `wctl doc-lint --path /workdir/wepppy/docs/mini-work-packages/20260513_omni_per_scenario_cumulative_filters_execplan.md`
  - Result: `tooling-fail` (panic in `wctl doc-lint` with absolute paths in this environment)
  - Evidence: panic `path is expected to be under the root`.
- `wctl doc-lint --path /workdir/wepppy/wepppy/nodb/mods/omni/README.md`
  - Result: `tooling-fail` (same absolute-path panic)
  - Evidence: panic `path is expected to be under the root`.
- Fallback validation for the two doc-lint checks (same files, repo-relative paths):
  - `wctl doc-lint --path docs/mini-work-packages/20260513_omni_per_scenario_cumulative_filters_execplan.md` -> `pass`
  - `wctl doc-lint --path wepppy/nodb/mods/omni/README.md` -> `pass`

### Independent Code Review (Correctness/Risk)

Reviewer mode: correctness/regression focused review of changed diffs plus targeted re-validation.

Findings:

1. Finding `CR-1`
   - Summary: JS scenario-name suffix normalization initially diverged from Python for legacy fractional slope values.
   - Affected file/function: `wepppy/weppcloud/controllers_js/omni.js` / `parseOptionalIntegerPercent`.
   - Severity: medium
   - Disposition: `fixed`
   - Evidence:
     - Code: `parseOptionalIntegerPercent` now promotes legacy fractional values (`<=1` with decimal/number input) to integer percentages before suffix generation.
     - Test: `wepppy/weppcloud/controllers_js/__tests__/omni.test.js` (`filtered scenarios produce distinct contrast options`) now includes `filter_hill_min_slope_pct: 0.1` and expects `__filters_smin10`.
     - Command: `wctl run-npm test -- omni` passed after fix.

### Independent QA Review (Validation/Workflow)

Reviewer mode: test/validation pipeline and operator workflow compliance.

Findings:

1. Finding `QA-1`
   - Summary: Required lint command fails due unrelated pre-existing test lint violations.
   - Affected file/function: unrelated test files (`disturbed.test.js`, `landuse_map_inline.test.js`).
   - Severity: low
   - Disposition: `accepted-risk`
   - Evidence:
     - Command: `wctl run-npm lint` fails with `jest/no-conditional-expect` in unrelated files.
     - Scope check: Omni-targeted test suites still pass (`wctl run-npm test -- omni`).

2. Finding `QA-2`
   - Summary: Required absolute-path doc-lint invocations panic in current toolchain.
   - Affected file/function: `wctl doc-lint` path handling (tooling issue, not Omni code).
   - Severity: low
   - Disposition: `accepted-risk`
   - Evidence:
     - Commands: both required absolute-path doc-lint invocations panic with `path is expected to be under the root`.
     - Mitigation evidence: equivalent repo-relative path invocations pass for the same two files.

Optional broad gate before merge:

- `wctl run-pytest tests --maxfail=1`

## Idempotence and Recovery

The change is additive when filters are omitted. Re-running scenario save/load should be safe because missing filter keys imply legacy behavior. If implementation creates regressions, rollback can be performed by removing per-scenario filter fields from serialization/parsing and restoring current name generation logic while leaving existing unfiltered scenarios intact.

## Interfaces and Dependencies

No new external dependencies are required.

Expected internal interface evolution:

- Scenario definition payload gains optional per-scenario filter keys for slope/burn filters.
- Scenario-name generation includes deterministic human-readable optional filter suffix.
- Treatment-scenario map building (`mulch`, `prescribed_fire`, `thinning`) consumes optional per-scenario filter masks.
- Global cumulative slope fields normalize as integer percentages while preserving current contrast flow.

Any decision-dependent contract details must be documented in `wepppy/nodb/mods/omni/README.md` in the same change set as implementation.

Change note: created on 2026-05-13 after repository discovery to scope per-scenario cumulative filter support and capture unresolved contract decisions before implementation.
Change note: updated on 2026-05-13 after operator decisions clarifying that filters apply to treatment assignment for `mulch`/`prescribed_fire`/`thinning`, global cumulative filters remain, visible per-scenario filters are slope+burn only, slopes are integer percentages, precedence is `global then per-scenario`, Filters collapsible appears only on treatment scenarios, and review disposition is required before handoff.
Change note: updated on 2026-05-13 during implementation kickoff to resolve the final semantics decision for `prescribed_fire`/`thinning` burn-severity filtering and mark the plan status as in progress.
