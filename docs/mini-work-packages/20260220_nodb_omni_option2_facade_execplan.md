# ExecPlan: Option-2 Refactor of Omni into a Stable Facade + Internal Collaborators

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept current as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, the Omni controller keeps a stable public facade contract while internal logic is extracted into focused collaborators in the required Option-2 order. The user-visible outcome is lower regression risk for Omni scenario/contrast workflows across Flask routes, RQ jobs, and rq-engine API routes, while preserving current lock/mutation/persistence behavior.

Success is demonstrated by contract characterization tests added before extraction, milestone-specific regression tests for each extracted path, milestone review gates, and a final full-suite pre-handoff gate.

## Progress

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for every entry.

- [x] (2026-02-20 17:58Z) Read required guidance: `AGENTS.md`, `wepppy/nodb/AGENTS.md`, `tests/AGENTS.md`, `docs/prompt_templates/codex_exec_plans.md`, and `docs/standards/nodb-facade-collaborator-pattern.md`.
- [x] (2026-02-20 17:58Z) Characterized Omni source, public API surface, route/RQ callsites, and existing Omni-related tests.
- [x] (2026-02-20 17:58Z) Authored this ad hoc ExecPlan with milestone sequencing, explicit test-gap closures, review gates, and rollback strategy.
- [x] (2026-02-20 18:04Z) Executed Milestone 0 baseline characterization tests and established route/RQ/facade contract safety net.
- [x] (2026-02-20 18:08Z) Executed Milestone 1 extraction (`omni_input_parser.py`) with facade delegation and parser regression tests.
- [x] (2026-02-20 18:10Z) Executed Milestone 2 extraction (`omni_build_router.py`) with facade orchestration delegation tests.
- [x] (2026-02-20 18:12Z) Executed Milestone 3 extraction (`omni_mode_build_services.py`) with mode dispatch regression tests.
- [x] (2026-02-20 18:14Z) Executed Milestone 4 extraction (`omni_scaling_service.py`) with scaling/filter normalization regression tests.
- [x] (2026-02-20 18:16Z) Executed Milestone 5 extraction (`omni_artifact_export_service.py`) with report/export delegation tests.
- [x] (2026-02-20 18:23Z) Executed Milestone 6 extraction (`omni_station_catalog_service.py`) and extended RQ dependency metadata stability tests.
- [x] (2026-02-20 18:40Z) Executed Milestone 7 final facade cleanup (`omni.pyi` seam alignment), targeted validation gates, full test suite, and doc lint gate.
- [x] (2026-02-20 19:44Z) Integrated post-implementation review findings (SEV3 indirection debt in router/artifact/station collaborators) into this ExecPlan with explicit follow-up direction and residual-risk updates.

## Surprises & Discoveries

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for new entries.

- (2026-02-20 17:58Z) Observation: The objective references `wepppy/nodb/core/omni.py`, but the active Omni implementation is `wepppy/nodb/mods/omni/omni.py` and exports via `wepppy/nodb/mods/omni/__init__.py`.
  Evidence: `rg --files | rg '/omni.py$'`, `ls wepppy/nodb/mods/omni`.

- (2026-02-20 17:58Z) Observation: Omni facade usage includes both public and quasi-public methods; RQ orchestration currently depends on internal helpers (`_scenario_signature`, `_loss_pw0_path_for_scenario`, `_contrast_run_status`, etc.).
  Evidence: `wepppy/rq/omni_rq.py`, `wepppy/rq/path_ce_rq.py`, `wepppy/microservices/rq_engine/omni_routes.py`.

- (2026-02-20 17:58Z) Observation: Current Omni tests are strong for contrast mode builders and clone helpers, but thin for facade contracts used by routes/RQ (parse/delete/run-state/report/lock boundary behaviors).
  Evidence: `tests/nodb/mods/test_omni.py` (high `_build_contrasts` focus), `tests/rq/test_omni_rq.py` (2 tests), `tests/weppcloud/routes/test_omni_bp.py` (helper-only tests).

- (2026-02-20 18:03Z) Observation: Workspace started with unrelated dirty state (`AGENTS.md` modified, active ExecPlan untracked); work proceeded without reverting user-owned changes.
  Evidence: `git status --short`.

- (2026-02-20 18:06Z) Observation: Existing `delete_scenarios()` behavior duplicates missing scenario names when the same missing name is requested multiple times.
  Evidence: `tests/nodb/mods/test_omni_facade_contracts.py:189`.

- (2026-02-20 18:21Z) Observation: `omni_station_catalog_service.py` existed as a skeleton before Milestone 6 but Omni facade methods were not yet delegated to it.
  Evidence: `wepppy/nodb/mods/omni/omni_station_catalog_service.py`, `wepppy/nodb/mods/omni/omni.py`.

- (2026-02-20 19:44Z) Observation: Post-implementation review classified router/artifact/station collaborators as mostly pass-through seams because primary logic remains in `Omni` `_..._impl` methods.
  Evidence: `wepppy/nodb/mods/omni/omni_build_router.py:12`, `wepppy/nodb/mods/omni/omni_artifact_export_service.py:14`, `wepppy/nodb/mods/omni/omni_station_catalog_service.py:12`.

## Decision Log

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for new entries.

- Decision: Treat `wepppy/nodb/mods/omni/omni.py` as the implementation target while preserving all existing import paths and facade contracts.
  Rationale: Current production callsites import from `wepppy.nodb.mods.omni`; path relocation is out of scope for this risk-reduction refactor.
  Date/Author: 2026-02-20 17:58Z / Codex

- Decision: Use Option-2 collaborator extraction with the exact required sequence: input parser -> build router -> mode services -> scaling -> artifact export -> station/catalog resolution.
  Rationale: This keeps changes incremental and reversible while matching repository standard.
  Date/Author: 2026-02-20 17:58Z / Codex

- Decision: Add contract characterization tests before any production extraction.
  Rationale: Existing coverage gaps in facade contracts and RQ integration are a primary regression risk.
  Date/Author: 2026-02-20 17:58Z / Codex

- Decision: Preserve the observed `delete_scenarios()` duplicate-missing-name quirk during this refactor and capture it as characterization.
  Rationale: ExecPlan scope is Option-2 extraction with behavior stability; changing this quirk would be a behavior change outside scope.
  Date/Author: 2026-02-20 18:06Z / Codex

- Decision: For Milestone 6, keep helper names on the `Omni` facade and move logic into `_..._impl` bodies delegated through `OmniStationCatalogService`.
  Rationale: This preserves route/RQ monkeypatch seams and quasi-public helper contracts while reducing Omni class complexity.
  Date/Author: 2026-02-20 18:22Z / Codex

- Decision: Update `omni.pyi` to include new `_..._impl` station/catalog seam signatures in Milestone 7.
  Rationale: Keep typed Omni surface coherent with runtime collaborator extraction and prevent drift for future stub/type gates.
  Date/Author: 2026-02-20 18:26Z / Codex

- Decision: Accept reviewer SEV3 findings as non-blocking for this milestone set and preserve `GO`, while tracking deeper logic relocation as follow-up refactor debt.
  Rationale: Contracts, tests, and gates are green; findings concern decomposition completeness and maintainability rather than correctness/regression risk.
  Date/Author: 2026-02-20 19:44Z / Codex

## Outcomes & Retrospective

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for new entries.

- (2026-02-20 18:40Z) Outcome: Milestones 0-7 completed in required Option-2 order with facade behavior preserved across route, rq-engine, and RQ callsites.
- (2026-02-20 18:40Z) Outcome: Added targeted regressions for each extracted path, including new station/catalog service coverage and RQ dependency metadata derivation checks.
- (2026-02-20 18:40Z) Outcome: Validation gates are green: milestone-targeted commands, `wctl run-pytest tests --maxfail=1` (1863 passed, 27 skipped), and doc lint (2 files, 0 issues).
- (2026-02-20 18:40Z) Retrospective: Characterization-first sequencing materially reduced risk; wrapper+`_impl` seams preserved compatibility while making collaborator boundaries explicit.
- (2026-02-20 19:44Z) Outcome: External review re-validated `GO` and identified three SEV3 maintainability findings (router/artifact/station indirection without full logic relocation).
- (2026-02-20 19:44Z) Retrospective: Option-2 sequence is satisfied at the seam/delegation level; full collaborator ownership of logic remains an explicit next-step refactor.

## Context and Orientation

Primary module and contracts:

1. Implementation module: `wepppy/nodb/mods/omni/omni.py` (~5.2k LOC) with typed surface in `wepppy/nodb/mods/omni/omni.pyi`.
2. Export surface: `wepppy/nodb/mods/omni/__init__.py`.
3. NoDb contract constraints: preserve `with self.locked()`, `nodb_setter` behavior, mutation/persistence boundaries, and `dump_and_unlock` semantics where currently used by facade methods.

Current external Omni callsites that define behavior contracts:

1. Flask routes:
   `wepppy/weppcloud/routes/nodb_api/omni_bp.py` uses `scenarios`, `scenario_run_state`, `scenario_dependency_tree`, `scenario_run_markers()`, `delete_scenarios()`, `scenarios_report()`, `contrast_selection_mode`, `contrasts_report()`, `contrast_status_report()`.
2. Dashboard/run routes:
   `wepppy/weppcloud/routes/gl_dashboard.py` uses `contrast_names`; `wepppy/weppcloud/routes/run_0/run_0_bp.py` uses `has_ran_scenarios` and `has_ran_contrasts`.
3. rq-engine API routes:
   `wepppy/microservices/rq_engine/omni_routes.py` uses `parse_scenarios()`, `parse_inputs()`, `build_contrasts()`, `build_contrasts_dry_run_report()`.
4. RQ workers:
   `wepppy/rq/omni_rq.py` and `wepppy/rq/path_ce_rq.py` use both facade and quasi-public helpers (`run_omni_scenarios()`, `run_omni_contrast()`, `clear_contrasts()`, `scenario_dependency_tree`, `contrast_dependency_tree`, `_scenario_signature()`, `_loss_pw0_path_for_scenario()`, `_contrast_run_status()`, `_contrast_sidecar_path()`, `_clean_stale_contrast_runs()`, etc.).

## Test-Gap Analysis

### Current Coverage Map

1. `tests/nodb/mods/test_omni.py`: strong coverage for contrast sidecars, user-defined area/group/stream-order contrast construction, clone helpers, and selected contrast-run status paths.
2. `tests/microservices/test_rq_engine_omni_routes.py`: strong request payload and enqueue behavior coverage using `DummyOmni` stubs.
3. `tests/rq/test_omni_rq.py`: currently only preflight smoke checks for `run_omni_scenarios_rq`.
4. `tests/rq/test_path_ce_rq.py`: preflight + orchestration smoke with Omni stubs.
5. `tests/weppcloud/routes/test_omni_bp.py`: only report summarization helper behavior, not route-facade integration.

### Uncovered / High-Risk Behaviors

1. Facade parsing contracts are largely uncharacterized (`parse_inputs`, `parse_scenarios`, `_normalize_contrast_pairs`, boolean normalization defaults, scenario coercion).
2. Facade mutation/persistence boundaries are uncharacterized for `delete_scenarios`, `scenario_run_state`, and dependency tree updates.
3. `run_omni_scenarios` dependency/skip/year-set behavior has limited direct regression protection.
4. Reporting and artifact surface (`scenarios_report`, `compile_hillslope_summaries`, `compile_channel_summaries`, `_build_contrast_ids_geojson`) is weakly covered as a facade contract.
5. RQ orchestration flows in `wepppy/rq/omni_rq.py` (scenario/contrast run orchestration, lock retries, dependency metadata updates) are under-tested.
6. Route-level Omni facade contract tests are thin for Flask `omni_bp` endpoints and dashboard contrast retrieval behaviors.

### Exact Tests to Add (Path + Intent)

1. `tests/nodb/mods/test_omni_facade_contracts.py`
   Intent: characterization tests for facade entrypoints used by routes/RQ (`parse_inputs`, `parse_scenarios`, `delete_scenarios`, `scenario_run_markers`, `has_ran_scenarios`, `has_ran_contrasts`, `contrast_batch_size`, `contrast_output_options`).
2. `tests/nodb/mods/test_omni_input_parser_service.py`
   Intent: parser service unit tests for payload coercion/validation, pair normalization, scenario coercion, and lock-boundary behavior.
3. `tests/nodb/mods/test_omni_build_router_service.py`
   Intent: orchestrator dispatch tests for `build_contrasts`, dry-run route, run-status assembly, and trigger/report sequencing without mode internals.
4. `tests/nodb/mods/test_omni_mode_build_services.py`
   Intent: mode-specific scenario and contrast builder dispatch tests (`cumulative`, `user_defined_areas`, `user_defined_hillslope_groups`, `stream_order`; scenario types `uniform_*`, `sbs_map`, `undisturbed`, `mulch`, `thinning`, `prescribed_fire`).
5. `tests/nodb/mods/test_omni_scaling_service.py`
   Intent: objective-threshold accumulation, hillslope limit clamping, slope/burn/topaz filter normalization, and order-reduction pass normalization.
6. `tests/nodb/mods/test_omni_artifact_export_service.py`
   Intent: deterministic non-skipped tests for `scenarios_report`, `contrasts_report`, `compile_hillslope_summaries`, `compile_channel_summaries`, and `contrast_ids` geojson generation using stubs (no optional dependency skips).
7. `tests/nodb/mods/test_omni_station_catalog_service.py`
   Intent: scenario/contrast path and catalog resolution checks (`_loss_pw0_path_for_scenario`, `_scenario_dependency_target`, `_contrast_scenario_keys`, `_contrast_landuse_skip_reason`, translator/topaz mapping).
8. `tests/rq/test_omni_rq.py`
   Intent: add lock-retry, dependency-entry mutation, enqueue sequencing, and finalization timestamp tests for `run_omni_scenario_rq`, `run_omni_contrast_rq`, `run_omni_contrasts_rq`, `_finalize_omni_*`.
9. `tests/weppcloud/routes/test_omni_bp_routes.py`
   Intent: route-level Omni facade integration tests for `get_scenarios`, `get_scenario_run_state`, `delete_scenarios`, and report endpoints with `Omni` stubs asserting expected facade calls/response contracts.
10. `tests/weppcloud/routes/test_gl_dashboard_route.py`
    Intent: add `_get_omni_contrasts` contract tests to ensure contrast-name + README gating behavior is preserved when Omni returns mixed entries.

## Milestone Plan

### Milestone 0: Baseline, Contract Characterization, and Safety Net

Scope: lock current Omni external behavior before extraction.

File targets:

1. `tests/nodb/mods/test_omni_facade_contracts.py` (new).
2. `tests/rq/test_omni_rq.py` (expand existing).
3. `tests/weppcloud/routes/test_omni_bp_routes.py` (new).
4. `tests/weppcloud/routes/test_gl_dashboard_route.py` (extend existing).

Behavior invariants:

1. No production behavior changes.
2. Characterization tests reflect current behavior, including quirks, unless a behavior is clearly invalid and explicitly recorded.
3. New characterization tests must be deterministic and non-skipped.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_facade_contracts.py --maxfail=1
    wctl run-pytest tests/rq/test_omni_rq.py tests/rq/test_path_ce_rq.py --maxfail=1
    wctl run-pytest tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/routes/test_omni_bp_routes.py tests/weppcloud/routes/test_gl_dashboard_route.py --maxfail=1

Review checkpoint:

1. Record findings in severity format:
   `- [SEVx] <title> | <path:line> | <impact> | <required fix>`.
2. Go/No-Go gate:
   `GO` only if characterization tests are green and no SEV0/SEV1 regressions are introduced.

Rollback plan:

1. Revert only Milestone 0 test additions that incorrectly codify unintended behavior.
2. Re-run the same Milestone 0 commands until characterization baseline is trusted.

### Milestone 1: Extract Input Parsing/Validation Service

Required sequence step: `1. input parsing/validation service`.

File targets:

1. `wepppy/nodb/mods/omni/omni_input_parser.py` (new).
2. `wepppy/nodb/mods/omni/omni.py` (facade delegation via module singleton, no contract changes).
3. `tests/nodb/mods/test_omni_input_parser_service.py` (new).
4. `tests/nodb/mods/test_omni_facade_contracts.py` (extend delegation assertions).

Behavior invariants:

1. Preserve signatures and side effects of `parse_inputs` and `parse_scenarios`.
2. Preserve lock/mutation semantics around parser writes.
3. No silent exception swallowing; keep explicit `ValueError` paths.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni_input_parser_service.py tests/nodb/mods/test_omni_facade_contracts.py --maxfail=1
    wctl run-pytest tests/microservices/test_rq_engine_omni_routes.py --maxfail=1

Review checkpoint:

1. Apply severity format and classify any parser contract drift.
2. Go/No-Go gate:
   `GO` only if parser service tests and rq-engine Omni route tests pass with unchanged route contracts.

Rollback plan:

1. Revert parser service wiring in `wepppy/nodb/mods/omni/omni.py`.
2. Keep characterization tests; adjust parser extraction until green.

### Milestone 2: Extract Build Router/Orchestrator

Required sequence step: `2. build router/orchestrator`.

File targets:

1. `wepppy/nodb/mods/omni/omni_build_router.py` (new).
2. `wepppy/nodb/mods/omni/omni.py` (delegate `build_contrasts`, `build_contrasts_dry_run_report`, `contrast_status_report` orchestration shell).
3. `tests/nodb/mods/test_omni_build_router_service.py` (new).

Behavior invariants:

1. Preserve selection-mode normalization aliases and branch routing.
2. Preserve lock boundaries for persisted contrast metadata.
3. Preserve sidecar/report generation boundaries and existing error contracts.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni_build_router_service.py tests/nodb/mods/test_omni.py -k "build_contrasts or contrast_status_report or dry_run" --maxfail=1
    wctl run-pytest tests/microservices/test_rq_engine_omni_routes.py --maxfail=1

Review checkpoint:

1. Review for orchestration-only extraction; mode logic must remain behavior-identical.
2. Go/No-Go gate:
   `GO` only if no SEV0/SEV1 findings on contrast-building contracts.

Rollback plan:

1. Re-point facade methods to pre-router in-class orchestration.
2. Keep new router tests as guardrail.

### Milestone 3: Extract Mode-Specific Build Services

Required sequence step: `3. mode-specific build services`.

File targets:

1. `wepppy/nodb/mods/omni/omni_mode_build_services.py` (new).
2. `wepppy/nodb/mods/omni/omni.py` (delegate mode-specific scenario and contrast build branches).
3. `tests/nodb/mods/test_omni_mode_build_services.py` (new).
4. `tests/nodb/mods/test_omni.py` (targeted updates to existing mode tests if seams move).

Behavior invariants:

1. Preserve all scenario mode effects (`uniform_*`, `sbs_map`, `undisturbed`, `mulch`, `thinning`, `prescribed_fire`).
2. Preserve contrast mode effects (`cumulative`, `user_defined_areas`, `user_defined_hillslope_groups`, `stream_order`).
3. Preserve existing monkeypatch seams currently relied on by tests (`_omni_clone`, `_run_contrast`, `_post_watershed_run_cleanup`, etc.).

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni_mode_build_services.py tests/nodb/mods/test_omni.py --maxfail=1
    wctl run-pytest tests/rq/test_omni_rq.py tests/rq/test_path_ce_rq.py --maxfail=1

Review checkpoint:

1. Explicitly verify mode dispatch map and branch outputs did not drift.
2. Go/No-Go gate:
   `GO` only if all mode service tests are deterministic and no branch contracts regress.

Rollback plan:

1. Revert mode service delegation while leaving router extraction intact.
2. Re-run Milestone 3 validation until mode parity is restored.

### Milestone 4: Extract Scaling Service

Required sequence step: `4. scaling service`.

File targets:

1. `wepppy/nodb/mods/omni/omni_scaling_service.py` (new).
2. `wepppy/nodb/mods/omni/omni.py` (delegate objective scaling/filter/threshold/order-reduction logic).
3. `tests/nodb/mods/test_omni_scaling_service.py` (new).

Behavior invariants:

1. Preserve cumulative objective threshold and hillslope limit behavior.
2. Preserve slope normalization and filter semantics.
3. Preserve `order_reduction_passes` normalization and stream-order guard behavior.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni_scaling_service.py tests/nodb/mods/test_omni.py -k "contrast_limit or filters or stream_order" --maxfail=1
    wctl run-pytest tests/microservices/test_rq_engine_omni_routes.py -k "stream_order or limit_error" --maxfail=1

Review checkpoint:

1. Verify no numerical selection drift in ranking/filter outputs.
2. Go/No-Go gate:
   `GO` only if scaling tests pass and no SEV1 findings on contrast selection results.

Rollback plan:

1. Revert scaling delegation only.
2. Retain tests and re-implement extraction with narrower boundaries.

### Milestone 5: Extract Artifact Export Service

Required sequence step: `5. artifact export service`.

File targets:

1. `wepppy/nodb/mods/omni/omni_artifact_export_service.py` (new).
2. `wepppy/nodb/mods/omni/omni.py` (delegate reports/parquet/geojson exports and catalog refresh triggers).
3. `tests/nodb/mods/test_omni_artifact_export_service.py` (new).

Behavior invariants:

1. Preserve report output paths and expected columns (`v`/`value`, scenario/contrast labels).
2. Preserve deterministic geojson artifact behavior for contrast IDs.
3. Preserve explicit failures for missing required artifacts; no silent fallbacks.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni_artifact_export_service.py tests/nodb/mods/test_omni.py -k "scenarios_report or contrasts_report or contrast_ids_geojson or compile_" --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/test_omni_report_templates.py --maxfail=1

Review checkpoint:

1. Ensure new artifact tests are non-skipped and deterministic even without optional GIS binaries.
2. Go/No-Go gate:
   `GO` only if artifact contracts hold and no SEV0/SEV1 findings remain.

Rollback plan:

1. Revert artifact service delegation while keeping prior milestones intact.
2. Re-run artifact-focused test commands before reattempt.

### Milestone 6: Extract Station/Catalog Resolution Service

Required sequence step: `6. station/catalog resolution service`.

Omni adaptation: this service encapsulates scenario/catalog/path resolution and translator-driven lookup behavior used by contrast dependency logic.

File targets:

1. `wepppy/nodb/mods/omni/omni_station_catalog_service.py` (new).
2. `wepppy/nodb/mods/omni/omni.py` (delegate scenario/path/dependency/landuse resolution helpers).
3. `tests/nodb/mods/test_omni_station_catalog_service.py` (new).
4. `tests/rq/test_omni_rq.py` (extend for dependency-path and signature stability).

Behavior invariants:

1. Preserve scenario key normalization and dependency target resolution.
2. Preserve contrast skip reasons based on landuse map equivalence.
3. Preserve RQ-dependent helper behavior currently consumed by `wepppy/rq/omni_rq.py`.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni_station_catalog_service.py tests/nodb/mods/test_omni.py --maxfail=1
    wctl run-pytest tests/rq/test_omni_rq.py tests/rq/test_path_ce_rq.py --maxfail=1

Review checkpoint:

1. Explicitly review all helper methods imported/used by `wepppy/rq/omni_rq.py` for compatibility.
2. Go/No-Go gate:
   `GO` only if dependency metadata and path-resolution tests remain stable.

Rollback plan:

1. Revert station/catalog service delegation only.
2. Keep helper characterization tests to enforce parity on re-implementation.

### Milestone 7: Final Facade Cleanup and Full Gates

Scope: finalize facade wiring, preserve contracts, and complete pre-handoff validation.

File targets:

1. `wepppy/nodb/mods/omni/omni.py` (facade-only cleanup, collaborator singleton wiring, comments for boundary catches where required).
2. `wepppy/nodb/mods/omni/omni.pyi` (update signatures if needed without public contract drift).
3. `tests/nodb/mods/test_omni*.py`, `tests/rq/test_omni_rq.py`, and route tests (final alignment).
4. `docs/mini-work-packages/20260220_nodb_omni_option2_facade_execplan.md` (living updates + evidence).

Behavior invariants:

1. Public Omni facade contracts unchanged for all route/RQ/test consumers.
2. Lock/mutation/persistence semantics unchanged.
3. No new broad exception swallows in production paths unless explicit boundary with rationale + logging.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_facade_contracts.py tests/nodb/mods/test_omni_input_parser_service.py tests/nodb/mods/test_omni_build_router_service.py tests/nodb/mods/test_omni_mode_build_services.py tests/nodb/mods/test_omni_scaling_service.py tests/nodb/mods/test_omni_artifact_export_service.py tests/nodb/mods/test_omni_station_catalog_service.py --maxfail=1
    wctl run-pytest tests/rq/test_omni_rq.py tests/rq/test_path_ce_rq.py tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/routes/test_omni_bp_routes.py tests/weppcloud/routes/test_gl_dashboard_route.py --maxfail=1
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path AGENTS.md --path docs/mini-work-packages/20260220_nodb_omni_option2_facade_execplan.md

Review checkpoint:

1. Run full severity-based review, resolve all SEV0/SEV1 before handoff.
2. Go/No-Go gate:
   `GO` only when all milestone gates and the final full-suite gate pass.

Rollback plan:

1. Revert only the latest milestone commit(s) that introduced regression.
2. Re-run Milestone 7 and full-suite gates before handoff.

## Regression-Risk Controls

1. Characterization-first: add/green contract tests before extraction milestones.
2. Lock/race boundary checks: explicit tests for `with self.locked()` mutation sites and RQ lock-retry paths.
3. Persistence boundary checks: ensure in-memory updates that must persist still use `nodb_setter`/lock semantics and route/RQ mutation boundaries remain unchanged.
4. Deterministic acceptance tests: for branches that often rely on optional GIS/tooling, use deterministic stubs/fixtures in service tests so acceptance does not rely on env-gated skips.
5. Incremental rollback: each milestone is isolated and reversible without discarding prior validated milestones.

## Review Process and Severity Format

Findings format for every milestone review:

- `[SEV0]` Blocker: data corruption, lock/persistence boundary break, or public facade contract break.
- `[SEV1]` High: user-visible behavior regression in route/RQ/test contracts.
- `[SEV2]` Medium: missing regression coverage in changed path, non-deterministic tests, or maintainability risk likely to regress.
- `[SEV3]` Low: clarity/refactor debt without immediate behavioral risk.

Required review artifact entry format:

- `[SEVx] <title> | <path:line> | <observed impact> | <required fix>`.

Milestone go/no-go rule:

1. `NO-GO` if any unresolved SEV0/SEV1 findings.
2. `NO-GO` if milestone validation commands fail.
3. `NO-GO` if newly added milestone tests are env-skipped for acceptance paths that can be deterministic.
4. `GO` only when all above are satisfied.

## Concrete Steps

Run all commands from `/workdir/wepppy`.

1. Execute Milestone 0 characterization additions and validations.
2. Implement Milestones 1-6 strictly in required Option-2 order.
3. At each milestone stop, update `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective`.
4. Execute Milestone 7 final gates, including full test suite and doc lint.

## Validation and Acceptance

Overall acceptance requires all of the following:

1. Public Omni facade behavior remains stable across route, rq-engine, and RQ worker callsites.
2. NoDb lock/mutation/persistence semantics remain unchanged.
3. Each extracted/fixed path has targeted regression tests.
4. Milestone go/no-go gates pass with no unresolved SEV0/SEV1 findings.
5. Final pre-handoff gate passes:

       wctl run-pytest tests --maxfail=1

6. Changed docs lint gate is green:

       wctl doc-lint --path AGENTS.md --path docs/mini-work-packages/20260220_nodb_omni_option2_facade_execplan.md

## Idempotence and Recovery

1. Milestones are intentionally incremental and independently repeatable.
2. If a milestone fails, rollback only that milestone’s changes, keep characterization tests, and retry.
3. Avoid multi-milestone merges without passing each milestone gate first.

## Evidence / Transcript Scaffold

Populate this section during execution with concise command transcripts.

### Milestone 0 Evidence

- Command: `wctl run-pytest tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_facade_contracts.py --maxfail=1`; `wctl run-pytest tests/rq/test_omni_rq.py tests/rq/test_path_ce_rq.py --maxfail=1`; `wctl run-pytest tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/routes/test_omni_bp_routes.py tests/weppcloud/routes/test_gl_dashboard_route.py --maxfail=1`.
- Output summary: All commands green; characterization coverage added for facade routes/RQ/dashboard contracts.
- Review decision (`GO`/`NO-GO`): `GO` (2026-02-20 18:04Z).
- Findings: `[SEV2] delete_scenarios duplicate missing-name behavior preserved as characterization | tests/nodb/mods/test_omni_facade_contracts.py:189 | Existing quirk remains and could surprise callers if deduping is expected | Track separate behavior-change ticket if product wants dedupe semantics.`
- Rollback action: Revert Milestone 0 characterization additions only if they codify unintended behavior.

### Milestone 1 Evidence

- Command: `wctl run-pytest tests/nodb/mods/test_omni_input_parser_service.py tests/nodb/mods/test_omni_facade_contracts.py --maxfail=1`; `wctl run-pytest tests/microservices/test_rq_engine_omni_routes.py --maxfail=1`.
- Output summary: Commands green; `parse_inputs`, `parse_scenarios`, and `_normalize_contrast_pairs` now delegate via `OmniInputParsingService` without route contract drift.
- Review decision (`GO`/`NO-GO`): `GO` (2026-02-20 18:08Z).
- Findings: No SEV0-SEV3 regression findings.
- Rollback action: Revert parser delegation in `wepppy/nodb/mods/omni/omni.py` and rerun Milestone 1 validations.

### Milestone 2 Evidence

- Command: `wctl run-pytest tests/nodb/mods/test_omni_build_router_service.py tests/nodb/mods/test_omni.py -k "build_contrasts or contrast_status_report or dry_run" --maxfail=1`; `wctl run-pytest tests/microservices/test_rq_engine_omni_routes.py --maxfail=1`.
- Output summary: Commands green; facade orchestration methods delegate through `OmniBuildRouter` with unchanged build/dry-run/status contracts.
- Review decision (`GO`/`NO-GO`): `GO` (2026-02-20 18:10Z).
- Findings: No SEV0-SEV3 regression findings.
- Rollback action: Re-point facade methods to in-class orchestration and keep new router tests as guardrails.

### Milestone 3 Evidence

- Command: `wctl run-pytest tests/nodb/mods/test_omni_mode_build_services.py tests/nodb/mods/test_omni.py --maxfail=1`; `wctl run-pytest tests/rq/test_omni_rq.py tests/rq/test_path_ce_rq.py --maxfail=1`.
- Output summary: Commands green; mode-specific contrast and scenario branches moved into `OmniModeBuildServices` with parity retained.
- Review decision (`GO`/`NO-GO`): `GO` (2026-02-20 18:12Z).
- Findings: No SEV0-SEV3 regression findings.
- Rollback action: Revert mode-service delegation while preserving Milestones 0-2.

### Milestone 4 Evidence

- Command: `wctl run-pytest tests/nodb/mods/test_omni_scaling_service.py tests/nodb/mods/test_omni.py -k "contrast_limit or filters or stream_order" --maxfail=1`; `wctl run-pytest tests/microservices/test_rq_engine_omni_routes.py -k "stream_order or limit_error" --maxfail=1`.
- Output summary: Commands green; scaling/normalization logic delegates through `OmniScalingService` with stream-order and filter semantics intact.
- Review decision (`GO`/`NO-GO`): `GO` (2026-02-20 18:14Z).
- Findings: No SEV0-SEV3 regression findings.
- Rollback action: Revert scaling delegation only and rerun milestone filters/stream-order tests.

### Milestone 5 Evidence

- Command: `wctl run-pytest tests/nodb/mods/test_omni_artifact_export_service.py tests/nodb/mods/test_omni.py -k "scenarios_report or contrasts_report or contrast_ids_geojson or compile_" --maxfail=1`; `wctl run-pytest tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/test_omni_report_templates.py --maxfail=1`.
- Output summary: Commands green; report/export methods now route through `OmniArtifactExportService` with unchanged artifact contracts.
- Review decision (`GO`/`NO-GO`): `GO` (2026-02-20 18:16Z).
- Findings: No SEV0-SEV3 regression findings.
- Rollback action: Revert artifact delegation and keep prior milestones/tests in place.

### Milestone 6 Evidence

- Command: `wctl run-pytest tests/nodb/mods/test_omni_station_catalog_service.py tests/nodb/mods/test_omni.py --maxfail=1`; `wctl run-pytest tests/rq/test_omni_rq.py tests/rq/test_path_ce_rq.py --maxfail=1`.
- Output summary: Commands green; station/catalog helper delegation completed in `Omni` with new service tests and RQ dependency metadata derivation regression (`tests/rq/test_omni_rq.py:171`).
- Review decision (`GO`/`NO-GO`): `GO` (2026-02-20 18:23Z).
- Findings: No SEV0-SEV3 regression findings.
- Rollback action: Revert station/catalog delegation seams only (`omni_station_catalog_service.py` + `omni.py` helper wrappers) and rerun Milestone 6 validations.

### Milestone 7 Evidence

- Command: `wctl run-pytest tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_facade_contracts.py tests/nodb/mods/test_omni_input_parser_service.py tests/nodb/mods/test_omni_build_router_service.py tests/nodb/mods/test_omni_mode_build_services.py tests/nodb/mods/test_omni_scaling_service.py tests/nodb/mods/test_omni_artifact_export_service.py tests/nodb/mods/test_omni_station_catalog_service.py --maxfail=1`; `wctl run-pytest tests/rq/test_omni_rq.py tests/rq/test_path_ce_rq.py tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/routes/test_omni_bp_routes.py tests/weppcloud/routes/test_gl_dashboard_route.py --maxfail=1`.
- Output summary: Both targeted final-gate command groups passed (`73 passed`, `68 passed`); final seam alignment included `wepppy/nodb/mods/omni/omni.pyi` updates for `_..._impl` helpers.
- Review decision (`GO`/`NO-GO`): `GO` (2026-02-20 18:30Z).
- Findings: `[SEV3] Build-router extraction is mostly indirection, not logic relocation | wepppy/nodb/mods/omni/omni_build_router.py:12 | Orchestration logic remains in Omni `_..._impl` methods, limiting maintainability gains | Follow-up: move orchestration bodies into `OmniBuildRouter` (or remove wrapper layer).`; `[SEV3] Artifact-export collaborator is a pass-through seam | wepppy/nodb/mods/omni/omni_artifact_export_service.py:14 | Export/report logic remains in Omni `_..._impl` methods | Follow-up: relocate export/report implementations into `OmniArtifactExportService`.`; `[SEV3] Station/catalog collaborator is a pass-through seam | wepppy/nodb/mods/omni/omni_station_catalog_service.py:12 | Scenario/path/dependency logic remains in Omni `_..._impl` methods | Follow-up: relocate station/catalog resolution implementations into `OmniStationCatalogService`.`
- Rollback action: Revert Milestone 7-only cleanup (`omni.pyi` seam additions) if any downstream type/stub tool reports drift.

### Final Handoff Evidence

- Full suite command: `wctl run-pytest tests --maxfail=1`.
- Full suite output summary: `1863 passed, 27 skipped, 62 warnings in 328.79s (0:05:28)`.
- Doc lint output summary: `wctl doc-lint --path AGENTS.md --path docs/mini-work-packages/20260220_nodb_omni_option2_facade_execplan.md` -> `✅ 2 files validated, 0 errors, 0 warnings`.
- Residual risks: Existing broad exception boundaries and deprecated-datetime warnings remain in untouched modules; no new SEV0/SEV1 issues introduced by this Omni Option-2 extraction. Additional SEV3 design debt remains: collaborator router/artifact/station modules are delegation seams rather than full logic owners.

## Interfaces and Dependencies

Planned collaborator modules (internal only) under `wepppy/nodb/mods/omni/`:

1. `omni_input_parser.py` -> `OmniInputParsingService`.
2. `omni_build_router.py` -> `OmniBuildRouter`.
3. `omni_mode_build_services.py` -> `OmniModeBuildServices`.
4. `omni_scaling_service.py` -> `OmniScalingService`.
5. `omni_artifact_export_service.py` -> `OmniArtifactExportService`.
6. `omni_station_catalog_service.py` -> `OmniStationCatalogService`.

Facade wiring convention in `wepppy/nodb/mods/omni/omni.py`:

1. Keep `Omni` class as public entrypoint.
2. Add module-level collaborator singletons (mirroring the climate Option-2 pattern) to preserve monkeypatch seams and avoid API churn.
3. Keep failures explicit and logged; avoid silent fallback wrappers.

Revision Note (2026-02-20 17:58Z, Codex): Created ad hoc ExecPlan for the Omni Option-2 facade refactor with required extraction sequence, test-gap closure plan, per-milestone review/rollback gates, final full-suite gate, doc-lint gate, and evidence scaffold.
Revision Note (2026-02-20 18:40Z, Codex): Executed Milestones 0-7 end-to-end; updated living sections (`Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`) and populated evidence, severity gates, go/no-go outcomes, and rollback actions for each milestone.
Revision Note (2026-02-20 19:44Z, Codex): Integrated external review findings and assumptions; preserved `GO` with explicit SEV3 collaborator-decomposition follow-up notes in Milestone 7 and residual risk tracking.
