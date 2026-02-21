# ExecPlan: Option-2 Omni Facade/Collaborator Refactor with Regression Controls

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept current as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Refactor Omni to an Option-2 shape (stable facade + internal collaborators) without changing route/RQ/test-facing contracts, while closing the highest-risk regression gaps before and during extraction. The outcome should be maintainable Omni internals that still behave exactly the same for all public and quasi-public callers.

This plan is milestone-driven, requires targeted deterministic tests per extracted path, and uses severity-based go/no-go review gates with explicit rollback strategy.

## Progress

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for every entry.

- [x] (2026-02-20 20:32Z) Read required guidance and standards: `AGENTS.md`, `wepppy/nodb/AGENTS.md`, `tests/AGENTS.md`, `docs/prompt_templates/codex_exec_plans.md`, `docs/standards/nodb-facade-collaborator-pattern.md`.
- [x] (2026-02-20 20:32Z) Read cross-plan context: `docs/mini-work-packages/20260220_nodb_climate_option2_facade_execplan.md`.
- [x] (2026-02-20 20:32Z) Mapped Omni facade entrypoints, route/RQ callsites, and existing Omni tests.
- [x] (2026-02-20 20:32Z) Authored this planning-only ExecPlan with required milestone sequencing, gates, and risk controls.
- [x] (2026-02-20 20:41Z) Milestone 0 complete: baseline characterization suites passed; existing deterministic coverage already satisfied planned facade/RQ/route safety-net targets.
- [x] (2026-02-20 20:44Z) Milestone 1 complete: added parser coercion/invalid-bool regressions and rq-engine malformed-scenarios 400 regressions; milestone gate passed after a single expectation correction retry.
- [x] (2026-02-20 20:50Z) Milestone 2 complete: moved contrast router/dry-run/status orchestration into `OmniBuildRouter`, preserved facade seam compatibility, and added deterministic selection-mode status matrix tests.
- [x] (2026-02-20 20:53Z) Milestone 3 complete: expanded mode-service scenario branch regressions (mulch/thinning/undisturbed `_base`) and added deterministic stream-order stale-vs-fresh rebuild decision coverage.
- [x] (2026-02-20 20:54Z) Milestone 4 complete: added scaling regressions for malformed numeric inputs, unknown burn classes, and stream-order order-reduction mismatch rerun status semantics.
- [x] (2026-02-20 20:59Z) Milestone 5 complete: moved scenarios/contrasts/hillslope/channel report compilation logic into `OmniArtifactExportService`, retained geojson seam compatibility, and replaced delegation-only artifact tests with deterministic behavior coverage.
- [x] (2026-02-20 21:06Z) Milestone 6 complete: moved station/catalog helper `_..._impl` bodies to collaborator ownership via service delegation and added deterministic station + RQ helper-output regressions.
- [x] (2026-02-20 21:14Z) Milestone 7 complete: finalized facade wiring, resolved one milestone-local router expectation mismatch, and passed all Omni + cross-layer + full-suite gates.
- [x] (2026-02-20 21:14Z) Program continuity follow-up complete: climate legacy-retirement status verified and continuity handoff captured against `docs/mini-work-packages/20260220_nodb_climate_option2_facade_execplan.md`.
- [x] (2026-02-20 22:03Z) Post-review remediation complete: restored scaling singleton seam usage in router collaborator and replaced broad silent station parquet catch with narrow logged handling plus deterministic regressions.

## Surprises & Discoveries

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for new entries.

- (2026-02-20 20:32Z) Observation: `wepppy/nodb/core/omni.py` does not exist in this tree; active Omni implementation is `wepppy/nodb/mods/omni/omni.py` with collaborators in `wepppy/nodb/mods/omni/*.py`.
  Evidence: `rg --files | rg '/omni\.py$'`.

- (2026-02-20 20:32Z) Observation: Option-2 collaborator modules exist, but major orchestration logic still resides in `omni.py` `_..._impl` methods for router/artifact/station concerns.
  Evidence: `wepppy/nodb/mods/omni/omni_build_router.py`, `wepppy/nodb/mods/omni/omni_artifact_export_service.py`, `wepppy/nodb/mods/omni/omni_station_catalog_service.py`.

- (2026-02-20 20:32Z) Observation: Service tests for router/artifact/station are mostly delegation seams; high-risk behavior coverage remains concentrated in `tests/nodb/mods/test_omni.py` and leaves orchestration branches weakly characterized at collaborator boundaries.
  Evidence: `tests/nodb/mods/test_omni_build_router_service.py`, `tests/nodb/mods/test_omni_artifact_export_service.py`, `tests/nodb/mods/test_omni_station_catalog_service.py`.

- (2026-02-20 20:32Z) Observation: RQ workers depend on Omni quasi-public helpers (`_scenario_signature`, `_loss_pw0_path_for_scenario`, `_contrast_run_status`, `_contrast_landuse_skip_reason`) that must be treated as contract surfaces.
  Evidence: `wepppy/rq/omni_rq.py`, `wepppy/rq/path_ce_rq.py`.

- (2026-02-20 20:32Z) Observation: `wepppy/nodb/core/climate.py` still contains substantial legacy mode/orchestration branches despite collaborator seams, creating cross-controller consistency risk if Omni refactor completes while climate remains partially legacy.
  Evidence: `wepppy/nodb/core/climate.py`, `wepppy/nodb/core/climate_mode_build_services.py`, `wepppy/nodb/core/climate_build_router.py`.

- (2026-02-20 20:41Z) Observation: Milestone 0 characterization expectations were already present in current tests (`delete_scenarios`, `scenario_run_markers`, output-option normalization, RQ dependency/trigger checks, route scenario-state payload shape); baseline gate required no new code.
  Evidence: `tests/nodb/mods/test_omni_facade_contracts.py`, `tests/rq/test_omni_rq.py`, `tests/weppcloud/routes/test_omni_bp_routes.py`.

- (2026-02-20 20:44Z) Observation: rq-engine malformed-scenarios JSON path currently returns `"Scenarios data must be valid JSON"` (not `"Scenario 0 must be an object"`), so Milestone 1 route regression had to align with existing contract after first gate attempt.
  Evidence: `tests/microservices/test_rq_engine_omni_routes.py::test_run_omni_rejects_non_object_scenarios_entry`, `wctl run-pytest ... -k "run_omni and scenarios"` failure transcript.

- (2026-02-20 20:50Z) Observation: Dry-run orchestration must continue to invoke `omni.build_contrasts(...)` (facade seam), not router-internal `build_contrasts(...)`, because existing tests and monkeypatch hooks rely on the facade call point.
  Evidence: initial Milestone 2 gate failure in `tests/nodb/mods/test_omni.py::test_build_contrasts_dry_run_report_cumulative_statuses`.

- (2026-02-20 20:53Z) Observation: `_build_contrasts_stream_order` rebuild behavior can be tested deterministically by controlling `RedisPrep[TaskEnum.build_subcatchments]` timestamps plus stubbed `whitebox_tools` and prune outputs; no external binaries are required.
  Evidence: `tests/nodb/mods/test_omni.py::test_build_contrasts_stream_order_stale_rebuild_decisions`.

- (2026-02-20 20:54Z) Observation: stream-order rerun semantics are correctly coupled to `order_reduction_passes`; changing passes from prior dependency metadata deterministically forces `needs_run` even when sidecar/hash snapshots are unchanged.
  Evidence: `tests/nodb/mods/test_omni.py::test_contrast_run_status_needs_run_when_order_reduction_passes_change`.

- (2026-02-20 20:59Z) Observation: `build_contrast_ids_geojson` can safely return an empty FeatureCollection for stream-order reports with only skipped/no-hillslope groups without importing optional GIS dependencies.
  Evidence: `tests/nodb/mods/test_omni_artifact_export_service.py::test_build_contrast_ids_geojson_stream_order_empty_fallback_without_gis_deps`.

- (2026-02-20 21:06Z) Observation: Milestone 6 `-k "scenario_key or dependency or landuse_skip"` characterization currently executes only service-focused station tests (3 selected), so RQ helper-output contracts required dedicated explicit tests in `tests/rq/test_omni_rq.py`.
  Evidence: Milestone 6 validation output (`3 passed, 51 deselected`) plus new tests `test_run_omni_scenarios_rq_concurrency_uses_helper_outputs_for_dependency_metadata` and `test_run_omni_contrasts_rq_landuse_skip_prunes_dependency_entries`.

- (2026-02-20 21:14Z) Observation: Milestone 7 full-gate pass required a milestone-local correction to a router test expectation to match canonical scenario-name normalization (`mulch` -> `mulch_None_None`) for sparse mulch definitions.
  Evidence: initial Milestone 7 failure in `tests/nodb/mods/test_omni_build_router_service.py::test_build_router_sets_contrast_inputs_inside_lock_scope`, followed by helper-aligned assertion update and successful rerun (`100 passed`).

- (2026-02-20 22:03Z) Observation: Router seam fidelity regression was valid; collaborator directly instantiated `OmniScalingService`, bypassing facade singleton monkeypatch seams used in contract tests.
  Evidence: `wepppy/nodb/mods/omni/omni_build_router.py` pre-remediation import/instantiation (`from ...omni_scaling_service import OmniScalingService`, `scaling_service = OmniScalingService()`), replaced with `_OMNI_SCALING_SERVICE` seam and covered by `test_build_router_uses_scaling_singleton_seam`.

- (2026-02-20 22:03Z) Observation: Station landuse parquet fallback previously swallowed non-schema exceptions silently, reducing failure-path observability for landuse-equality skip decisions.
  Evidence: prior `except Exception: continue` in `wepppy/nodb/mods/omni/omni_station_catalog_service.py`, now narrowed to schema fallback + logged non-schema failure with `test_load_landuse_key_map_logs_and_returns_none_on_read_failure`.

## Decision Log

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for new entries.

- Decision: Execute Option-2 refactor against the active Omni module path (`wepppy/nodb/mods/omni/omni.py`) while preserving all existing import/usage contracts.
  Rationale: No `wepppy/nodb/core/omni.py` implementation exists in this branch; contract-preserving refactor must target the live module.
  Date/Author: 2026-02-20 20:32Z / Codex

- Decision: Preserve all route/RQ/test-facing Omni behavior, including quasi-public helper semantics consumed by worker code.
  Rationale: Dependency metadata, skip logic, and run-state behavior are externally observable in RQ and UI flows.
  Date/Author: 2026-02-20 20:32Z / Codex

- Decision: Use strict Option-2 extraction order and require targeted deterministic regressions before/at each milestone gate.
  Rationale: Incremental isolation minimizes rollback scope and makes regressions attributable.
  Date/Author: 2026-02-20 20:32Z / Codex

- Decision: Treat all six required Option-2 stages as applicable to Omni; no stage is marked N/A.
  Rationale: Omni contains all six concern areas (parse, orchestration, mode build, scaling/filtering, artifact export, station/catalog/dependency resolution).
  Date/Author: 2026-02-20 20:32Z / Codex

- Decision: Add explicit program continuity follow-up for climate legacy branch retirement after Omni milestone completion.
  Rationale: Mixed facade maturity across controllers increases long-term regression and reviewer burden.
  Date/Author: 2026-02-20 20:32Z / Codex

- Decision: Mark Milestone 0 as complete without test edits because all required characterization checks were already deterministic and passing.
  Rationale: Existing suites already enforce the requested baseline behavior contracts; additional duplicate tests would be redundant and add maintenance noise.
  Date/Author: 2026-02-20 20:41Z / Codex

- Decision: Preserve the existing malformed-scenarios error contract (`"Scenarios data must be valid JSON"`) in rq-engine route tests.
  Rationale: Milestone 1 is contract-hardening, not behavior change; route regression tests must encode the current public 400 payload.
  Date/Author: 2026-02-20 20:44Z / Codex

- Decision: In `OmniBuildRouter.build_contrasts_dry_run_report`, call `omni.build_contrasts(...)` to preserve facade monkeypatch seams before producing status payloads.
  Rationale: This keeps dry-run orchestration contract-compatible with existing tests and downstream expectations while still moving orchestration ownership to router collaborator methods.
  Date/Author: 2026-02-20 20:50Z / Codex

- Decision: Keep undisturbed `_base` no-SBS bypass as a contract and add direct collaborator-level regression coverage for it.
  Rationale: `_base` projects are a known special-case execution context; preserving this branch avoids false-positive failures during base-context scenario orchestration.
  Date/Author: 2026-02-20 20:53Z / Codex

- Decision: Encode unknown burn classes and malformed numeric filter inputs as explicit `ValueError` contracts in scaling collaborator tests.
  Rationale: These are high-signal operator errors; explicit failures prevent silent contrast-selection drift.
  Date/Author: 2026-02-20 20:54Z / Codex

- Decision: Keep `build_contrast_ids_geojson` routed through the artifact collaborator seam while preserving the existing facade implementation body for now.
  Rationale: This maintains current optional-dependency behavior and minimizes migration risk while still relocating the high-volume report compilation logic to the collaborator.
  Date/Author: 2026-02-20 20:59Z / Codex

- Decision: Repoint all station/catalog facade `_..._impl` methods to delegate directly to `OmniStationCatalogService` methods while preserving existing method names/signatures.
  Rationale: This completes Option-2 station collaborator ownership without contract drift and avoids duplicate logic maintenance in facade internals.
  Date/Author: 2026-02-20 21:06Z / Codex

- Decision: Add explicit RQ helper-output regression coverage for concurrent scenario orchestration and landuse-skip contrast orchestration paths.
  Rationale: These worker paths consume station/catalog helper outputs and are quasi-public behavior surfaces for dependency metadata and skip semantics.
  Date/Author: 2026-02-20 21:06Z / Codex

- Decision: Align router-service lock-scope test expectations with `_scenario_name_from_scenario_definition(...)` instead of hardcoded short labels.
  Rationale: Mulch scenario naming depends on payload shape; helper-aligned assertions preserve contract intent while avoiding false-negative test drift.
  Date/Author: 2026-02-20 21:14Z / Codex

- Decision: Route router selection-mode normalization through `_OMNI_SCALING_SERVICE` seam instead of directly instantiating `OmniScalingService`.
  Rationale: Preserves Option-2 singleton seam compatibility for monkeypatch/injection tests and avoids collaborator seam drift.
  Date/Author: 2026-02-20 22:03Z / Codex

- Decision: Replace broad catch in station landuse loader with explicit schema-fallback (`KeyError`/`ValueError`) and logged non-schema boundary handling (`ImportError`/`OSError`).
  Rationale: Enforces exception policy (no silent broad catches) while preserving existing column-fallback behavior.
  Date/Author: 2026-02-20 22:03Z / Codex

## Outcomes & Retrospective

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for new entries.

- (2026-02-20 20:32Z) Outcome: Planning-only pass complete; no Omni/climate production code changed in this turn.
- (2026-02-20 20:32Z) Outcome: Milestone map, regression controls, test-gap closures, and rollback strategy are fully defined.
- (2026-02-20 20:32Z) Retrospective: Highest risk is not missing collaborator files; it is remaining legacy orchestration inside facade `_..._impl` branches and under-tested worker/route contract edges.
- (2026-02-20 20:41Z) Outcome: Milestone 0 gate completed with all baseline suites green (`9 passed`, `9 passed`, `56 passed`).
- (2026-02-20 20:41Z) Retrospective: Baseline is stable; primary remaining work is deeper collaborator ownership (router/artifact/station) plus targeted deterministic regressions in later milestones.
- (2026-02-20 20:44Z) Outcome: Milestone 1 parser hardening completed with added deterministic parser and route regressions (`15 passed`, `4 passed` for milestone commands).
- (2026-02-20 20:44Z) Retrospective: Milestone-local gate retry validated the expected rollback discipline; contract-aligned expectation fix restored `GO` without production behavior drift.
- (2026-02-20 20:50Z) Outcome: Milestone 2 router/orchestrator extraction hardening completed; router now owns build, dry-run, and status payload assembly paths with passing mode-matrix regressions.
- (2026-02-20 20:50Z) Retrospective: collaborator ownership improved while preserving facade seam contracts required by legacy tests; one milestone-local retry was needed to restore dry-run seam parity.
- (2026-02-20 20:53Z) Outcome: Milestone 3 mode-service hardening completed with targeted treatment-mapping and stream-order rebuild path regressions (`20 passed`, `7 passed` for milestone commands).
- (2026-02-20 20:53Z) Retrospective: mode-service contracts are now explicitly characterized at collaborator level; stream-order stale/fresh branch behavior is deterministic under test stubs.
- (2026-02-20 20:54Z) Outcome: Milestone 4 scaling hardening completed with deterministic edge/failure coverage (`8 passed`, `4 passed` for milestone commands).
- (2026-02-20 20:54Z) Retrospective: scaling/rerun invariants are now explicitly guarded; stream-order dependency metadata changes are regression-tested without integration dependencies.
- (2026-02-20 20:59Z) Outcome: Milestone 5 artifact hardening completed with collaborator-owned report/summary compilation and deterministic artifact behavior tests (`13 passed`, `6 passed` for milestone commands).
- (2026-02-20 20:59Z) Retrospective: largest artifact logic now lives in collaborator service; geojson generation remains a seam-preserved facade implementation and is covered by explicit empty-fallback regression.
- (2026-02-20 21:06Z) Outcome: Milestone 6 station/catalog hardening completed with collaborator-owned helper implementations and deterministic station/RQ regressions (`3 passed`, `11 passed` for milestone commands).
- (2026-02-20 21:06Z) Retrospective: facade still exposes compatibility helpers, but logic ownership is now centralized in collaborator service; RQ orchestration helper contracts are directly characterized for both scenario and contrast pipelines.
- (2026-02-20 21:14Z) Outcome: Milestone 7 finalization completed with all milestone and pre-handoff gates green (`100 passed`, `72 passed`, `1894 passed, 27 skipped`) plus doc-lint gate success.
- (2026-02-20 21:14Z) Retrospective: milestone-local rollback discipline held at closeout (single failing expectation corrected and rerun), and full contract-preservation confidence now comes from deterministic collaborator + RQ + route characterization.
- (2026-02-20 22:03Z) Outcome: Post-review SEV2 follow-ups completed with seam restoration + logged exception handling and focused regression gates green (`21 passed`; milestone-targeted `16 passed` and `3 passed` characterization reruns).
- (2026-02-20 22:03Z) Retrospective: review-driven fixes were isolated to collaborator seam/failure observability and did not require route/RQ contract changes.

## Context and Orientation

Primary Omni implementation and collaborators:

1. `wepppy/nodb/mods/omni/omni.py` (facade + substantial `_..._impl` logic).
2. `wepppy/nodb/mods/omni/omni_input_parser.py`.
3. `wepppy/nodb/mods/omni/omni_build_router.py`.
4. `wepppy/nodb/mods/omni/omni_mode_build_services.py`.
5. `wepppy/nodb/mods/omni/omni_scaling_service.py`.
6. `wepppy/nodb/mods/omni/omni_artifact_export_service.py`.
7. `wepppy/nodb/mods/omni/omni_station_catalog_service.py`.
8. Typed surface: `wepppy/nodb/mods/omni/omni.pyi`.

External callsites that define contracts:

1. rq-engine API: `wepppy/microservices/rq_engine/omni_routes.py`.
2. Flask routes: `wepppy/weppcloud/routes/nodb_api/omni_bp.py`, `wepppy/weppcloud/routes/gl_dashboard.py`.
3. RQ workers: `wepppy/rq/omni_rq.py`, `wepppy/rq/path_ce_rq.py`.

Invariants that must remain true throughout the plan:

1. Preserve public Omni facade contracts and quasi-public helper behavior used by routes/RQ/tests.
2. Preserve NoDb lock/mutation/persistence boundaries (`with self.locked()`, `nodb_setter`, `dump_and_unlock`, boundary ownership).
3. No silent exception swallowing; boundary catches must log with context.
4. No speculative abstractions or unsupported behavior expansions.

## Option-2 Sequence Mapping for Omni

1. Input parsing/validation service: `OmniInputParsingService` (`parse_inputs`, `parse_scenarios`, contrast pair normalization).
2. Build router/orchestrator: `OmniBuildRouter` (`build_contrasts`, dry-run report, status report orchestration).
3. Mode-specific build services: `OmniModeBuildServices` (selection-mode and scenario-mode build branches).
4. Scaling service: `OmniScalingService` (selection-mode aliases, limits, slope/burn/topaz filters, order-reduction normalization).
5. Artifact export service: `OmniArtifactExportService` (reports/summaries/geojson export seams).
6. Station/catalog resolution service: `OmniStationCatalogService` (scenario key/path/dependency resolution and landuse skip helpers).

All six stages are applicable; no N/A stage is required.

## Milestone Plan

### Milestone 0: Baseline Characterization and Safety Net

Scope: freeze current behavior for facade, route, and RQ contracts before deeper extraction.

Files/modules touched:

1. `tests/nodb/mods/test_omni_facade_contracts.py`.
2. `tests/rq/test_omni_rq.py`.
3. `tests/weppcloud/routes/test_omni_bp_routes.py`.
4. `tests/weppcloud/routes/test_gl_dashboard_route.py`.

Invariants to preserve:

1. No production code changes in this milestone.
2. Characterization tests must encode existing behavior (including known quirks) unless explicitly approved to change.

Tests to add/update:

1. Add deterministic checks for `delete_scenarios`, `scenario_run_markers`, and output-option normalization.
2. Expand RQ tests for dependency-state mutation and trigger emissions.
3. Expand route contract checks for scenario state payload structure.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni_facade_contracts.py --maxfail=1
    wctl run-pytest tests/rq/test_omni_rq.py tests/rq/test_path_ce_rq.py --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_omni_bp_routes.py tests/weppcloud/routes/test_gl_dashboard_route.py tests/microservices/test_rq_engine_omni_routes.py --maxfail=1

Go/No-Go review gate:

1. Severity review required (`SEV0`..`SEV3`) with findings format:
   `[SEVx] <title> | <path:line> | <impact> | <required fix>`.
2. `NO-GO` if unresolved `SEV0`/`SEV1` or any baseline command fails.

Rollback strategy:

1. Revert only newly added characterization tests that are proven incorrect.
2. Re-run Milestone 0 commands until baseline is trusted.

### Milestone 1: Input Parsing/Validation Service Hardening

Scope: keep facade thin and ensure parser service owns input normalization/validation behavior.

Files/modules touched:

1. `wepppy/nodb/mods/omni/omni.py`.
2. `wepppy/nodb/mods/omni/omni_input_parser.py`.
3. `tests/nodb/mods/test_omni_input_parser_service.py`.
4. `tests/nodb/mods/test_omni_facade_contracts.py`.

Invariants to preserve:

1. `parse_inputs` and `parse_scenarios` signatures and side effects remain stable.
2. Mutations remain lock-scoped and contract-compatible.
3. No broad catches that hide malformed payload errors.

Tests to add/update:

1. Add parser tests for scenario coercion edge cases and invalid boolean tokens.
2. Add lock-scope assertions for parser mutation boundaries.
3. Add rq-engine route regression for parser-related 400 responses.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni_input_parser_service.py tests/nodb/mods/test_omni_facade_contracts.py --maxfail=1
    wctl run-pytest tests/microservices/test_rq_engine_omni_routes.py -k "run_omni and scenarios" --maxfail=1

Go/No-Go review gate:

1. `NO-GO` if parser contract drift is detected in route payload handling.
2. `NO-GO` if unresolved `SEV0`/`SEV1` findings.

Rollback strategy:

1. Re-point facade calls to previous parser wiring if needed.
2. Keep parser tests; fix implementation until green.

### Milestone 2: Build Router/Orchestrator Hardening

Scope: move and stabilize orchestration logic now living in facade `_build_contrasts_router_impl`/dry-run/status branches.

Files/modules touched:

1. `wepppy/nodb/mods/omni/omni.py`.
2. `wepppy/nodb/mods/omni/omni_build_router.py`.
3. `tests/nodb/mods/test_omni_build_router_service.py`.
4. `tests/nodb/mods/test_omni.py` (targeted status/build report cases).

Invariants to preserve:

1. Selection-mode routing and validation behavior must remain identical.
2. Lock/persistence boundaries for stored contrast inputs remain unchanged.
3. Dry-run report and status payload schemas remain route-compatible.

Tests to add/update:

1. Add deterministic router tests for cumulative vs user-defined vs stream-order status outputs.
2. Add dry-run regression for report item schema and selection-mode normalization aliases.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni_build_router_service.py tests/nodb/mods/test_omni.py -k "dry_run or contrast_status_report or build_contrasts" --maxfail=1
    wctl run-pytest tests/microservices/test_rq_engine_omni_routes.py -k "run_omni_contrasts" --maxfail=1

Go/No-Go review gate:

1. `NO-GO` if status/dry-run payload contracts regress.
2. `NO-GO` if unresolved `SEV0`/`SEV1` findings.

Rollback strategy:

1. Revert router-orchestration extraction only.
2. Retain new tests to guard parity on reattempt.

### Milestone 3: Mode-Specific Build Services Hardening

Scope: isolate selection-mode and scenario-mode build branches behind `OmniModeBuildServices`.

Files/modules touched:

1. `wepppy/nodb/mods/omni/omni.py`.
2. `wepppy/nodb/mods/omni/omni_mode_build_services.py`.
3. `tests/nodb/mods/test_omni_mode_build_services.py`.
4. `tests/nodb/mods/test_omni.py`.

Invariants to preserve:

1. Scenario mode behavior (`uniform_*`, `undisturbed`, `sbs_map`, `mulch`, `prescribed_fire`, `thinning`) remains unchanged.
2. Contrast mode behavior (`cumulative`, `user_defined_areas`, `user_defined_hillslope_groups`, `stream_order`) remains unchanged.
3. Existing monkeypatch seams used by tests/workers remain valid.

Tests to add/update:

1. Expand mode-service tests for mulch/thinning treatment mapping and `_base` undisturbed exceptions.
2. Add deterministic stream-order branch tests with WBT stubs for stale/rebuild decision paths.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni_mode_build_services.py tests/nodb/mods/test_omni.py -k "scenario_mode or stream_order or user_defined" --maxfail=1
    wctl run-pytest tests/rq/test_omni_rq.py --maxfail=1

Go/No-Go review gate:

1. `NO-GO` if mode dispatch map or output naming contracts change.
2. `NO-GO` if unresolved `SEV0`/`SEV1` findings.

Rollback strategy:

1. Revert mode-service extraction independently.
2. Keep mode regressions to enforce parity.

### Milestone 4: Scaling Service Hardening

Scope: consolidate limit/filter/order-reduction normalization and advanced candidate filtering in scaling collaborator.

Files/modules touched:

1. `wepppy/nodb/mods/omni/omni.py`.
2. `wepppy/nodb/mods/omni/omni_scaling_service.py`.
3. `tests/nodb/mods/test_omni_scaling_service.py`.
4. `tests/nodb/mods/test_omni.py`.

Invariants to preserve:

1. Hillslope limit clamp/default behavior remains stable.
2. Slope/topaz/burn filters preserve semantics and error contracts.
3. Stream-order pass normalization remains compatible with RQ dependency checks.

Tests to add/update:

1. Add edge tests for invalid burn classes and malformed numeric inputs.
2. Add deterministic tests for order-reduction mismatch forcing rerun status.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni_scaling_service.py tests/nodb/mods/test_omni.py -k "hillslope_limit or filters or order_reduction" --maxfail=1
    wctl run-pytest tests/rq/test_omni_rq.py -k "dependency or contrast" --maxfail=1

Go/No-Go review gate:

1. `NO-GO` if contrast candidate selection drifts unexpectedly.
2. `NO-GO` if unresolved `SEV0`/`SEV1` findings.

Rollback strategy:

1. Revert scaling extraction only.
2. Keep added scaling tests to verify reimplementation.

### Milestone 5: Artifact Export Service Hardening

Scope: shift report/export logic from facade `_..._impl` methods into artifact collaborator with deterministic coverage.

Files/modules touched:

1. `wepppy/nodb/mods/omni/omni.py`.
2. `wepppy/nodb/mods/omni/omni_artifact_export_service.py`.
3. `tests/nodb/mods/test_omni_artifact_export_service.py`.
4. `tests/weppcloud/routes/test_omni_bp.py`.
5. `tests/weppcloud/test_omni_report_templates.py`.

Invariants to preserve:

1. Output schema expectations (`v`/`value`, scenario/contrast labels, contrast ids) stay stable.
2. Artifact path naming and catalog refresh behavior remain stable.
3. Missing-artifact failures remain explicit and observable.

Tests to add/update:

1. Replace delegation-only artifact service tests with deterministic behavior tests for scenarios/contrasts/hillslope/channel summaries.
2. Add deterministic non-skipped tests for `_build_contrast_ids_geojson` fallbacks when optional GIS deps are absent (stub-based fallback assertions).

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni_artifact_export_service.py tests/nodb/mods/test_omni.py -k "report or compile or contrast_ids_geojson" --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/test_omni_report_templates.py --maxfail=1

Go/No-Go review gate:

1. `NO-GO` if report templates/routes observe schema drift.
2. `NO-GO` if unresolved `SEV0`/`SEV1` findings.

Rollback strategy:

1. Revert artifact extraction only.
2. Keep deterministic artifact tests as acceptance guardrails.

### Milestone 6: Station/Catalog Resolution Service Hardening

Scope: move path/dependency/landuse-resolution helpers out of facade `_..._impl` methods into station/catalog collaborator.

Files/modules touched:

1. `wepppy/nodb/mods/omni/omni.py`.
2. `wepppy/nodb/mods/omni/omni_station_catalog_service.py`.
3. `tests/nodb/mods/test_omni_station_catalog_service.py`.
4. `tests/rq/test_omni_rq.py`.

Invariants to preserve:

1. Scenario key normalization and dependency target/path/signature behavior remain stable.
2. Landuse equivalence skip behavior for contrasts remains stable.
3. RQ helper compatibility remains stable for dependency metadata and rerun logic.

Tests to add/update:

1. Expand station service tests beyond delegation to real behavior fixtures (temporary parquet/path fixtures).
2. Add RQ regressions covering helper outputs consumed by `run_omni_scenarios_rq` and `run_omni_contrasts_rq`.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni_station_catalog_service.py tests/nodb/mods/test_omni.py -k "scenario_key or dependency or landuse_skip" --maxfail=1
    wctl run-pytest tests/rq/test_omni_rq.py tests/rq/test_path_ce_rq.py --maxfail=1

Go/No-Go review gate:

1. `NO-GO` if helper output changes break RQ dependency metadata semantics.
2. `NO-GO` if unresolved `SEV0`/`SEV1` findings.

Rollback strategy:

1. Revert station/catalog extraction only.
2. Retain helper regressions for parity verification.

### Milestone 7: Facade Finalization and Full Gates

Scope: complete facade slimming, ensure collaborator ownership is coherent, and pass full validation gates.

Files/modules touched:

1. `wepppy/nodb/mods/omni/omni.py`.
2. `wepppy/nodb/mods/omni/omni.pyi`.
3. Omni-related tests under `tests/nodb/mods/`, `tests/rq/`, `tests/microservices/`, and `tests/weppcloud/routes/`.
4. `docs/mini-work-packages/completed/20260220_nodb_omni_option2_facade_execplan.md` (living updates).

Invariants to preserve:

1. All public/quasi-public contracts unchanged unless explicitly approved.
2. Lock/mutation/persistence semantics unchanged.
3. No silent exception swallowing introduced.

Tests to add/update:

1. Final alignment updates for all touched Omni tests.
2. Any missing deterministic tests discovered during review.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_facade_contracts.py tests/nodb/mods/test_omni_input_parser_service.py tests/nodb/mods/test_omni_build_router_service.py tests/nodb/mods/test_omni_mode_build_services.py tests/nodb/mods/test_omni_scaling_service.py tests/nodb/mods/test_omni_artifact_export_service.py tests/nodb/mods/test_omni_station_catalog_service.py --maxfail=1
    wctl run-pytest tests/rq/test_omni_rq.py tests/rq/test_path_ce_rq.py tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/routes/test_omni_bp_routes.py tests/weppcloud/routes/test_gl_dashboard_route.py --maxfail=1
    wctl run-pytest tests --maxfail=1

Go/No-Go review gate:

1. `NO-GO` if any unresolved `SEV0`/`SEV1` finding remains.
2. `NO-GO` if any milestone validation or full-suite command fails.

Rollback strategy:

1. Revert only the latest failing milestone diff.
2. Re-run Milestone 7 gates after correction.

## Test-Gap Analysis

### Current Coverage Map

1. `tests/nodb/mods/test_omni.py` provides broad behavior coverage for many contrast/scenario paths.
2. `tests/nodb/mods/test_omni_facade_contracts.py` covers key facade contract surfaces.
3. `tests/nodb/mods/test_omni_input_parser_service.py` and `tests/nodb/mods/test_omni_scaling_service.py` exercise service-level logic.
4. `tests/nodb/mods/test_omni_build_router_service.py`, `tests/nodb/mods/test_omni_artifact_export_service.py`, and `tests/nodb/mods/test_omni_station_catalog_service.py` now include deterministic collaborator behavior checks (not only facade delegation seams).
5. `tests/rq/test_omni_rq.py` now includes deterministic helper-output coverage for concurrent scenario dependency orchestration and landuse-skip contrast pruning.
6. `tests/microservices/test_rq_engine_omni_routes.py` covers request validation/enqueue contracts extensively.
7. `tests/weppcloud/routes/test_omni_bp_routes.py` and `tests/weppcloud/routes/test_gl_dashboard_route.py` cover route facade interactions for selected endpoints.

### Uncovered High-Risk Behaviors

1. Router/artifact/station collaborator ownership is weakly tested where `_..._impl` logic remains in facade.
2. `run_omni_scenarios` two-pass dependency/year-set rerun behavior is under-characterized in direct RQ tests.
3. `run_omni_contrasts_rq` queue batching/dependency updates/skip-reasons need richer deterministic assertions.
4. Stream-order branches rely on filesystem/WBT state and need deterministic tests that do not depend on external binaries.
5. Report/artifact schema guarantees (`v` vs `value`, labels, IDs) across all selection modes need stronger service-level assertions.
6. Landuse-based contrast skip and dependency helper semantics need more fixture-based coverage.

### Deterministic Tests to Add (Exact Targets + Intent)

1. `tests/nodb/mods/test_omni_build_router_service.py`:
   Add status payload matrix tests across `cumulative`, `user_defined_areas`, `user_defined_hillslope_groups`, and `stream_order`.
2. `tests/nodb/mods/test_omni_artifact_export_service.py`:
   Replace delegation-only checks with deterministic fixture tests for scenarios/contrasts reports, summary compile outputs, and contrast-ids geojson fallback behavior.
3. `tests/nodb/mods/test_omni_station_catalog_service.py`:
   Add fixture-backed tests for scenario-key normalization, dependency-target/path/signature generation, and landuse-skip reasoning.
4. `tests/nodb/mods/test_omni_mode_build_services.py`:
   Add stream-order stale/rebuild branch tests and mulch/thinning/prescribed-fire edge contracts.
5. `tests/rq/test_omni_rq.py`:
   Add deterministic tests for contrast queue batching, dependency-tree updates/removals, lock retry paths, and finalization job sequencing.
6. `tests/weppcloud/routes/test_omni_bp_routes.py`:
   Add route tests for report endpoints to validate facade call contracts and response schema assumptions.
7. `tests/weppcloud/routes/test_gl_dashboard_route.py`:
   Add contrast-name edge-case tests (gaps/missing directories/readme gating).

## Regression-Risk Controls

1. Characterization-first: expand baseline coverage before refactor movement; never move logic without path-specific regression tests.
2. Lock/race protections: verify all moved mutating paths retain original `with self.locked()` and `nodb_setter` boundaries; add lock retry tests where RQ writes dependency state.
3. Persistence boundary protections: ensure any changes keep persistence ownership at current facade boundaries and do not move `dump_and_unlock` responsibilities across route/RQ layers.
4. Env-gated skip mitigation: for paths typically gated by optional GIS/binary availability, add deterministic stub-backed non-skipped tests to prove behavior even when integration suites skip.
5. Rollback discipline: each milestone remains independently reversible; revert only the failing milestone and rerun its gate before proceeding.

## Program Continuity: Climate Legacy Orchestration Retirement

Concrete follow-up after Omni milestones complete:

1. Retire remaining legacy orchestration branches still in `wepppy/nodb/core/climate.py` by moving mode/orchestration behavior from facade `_build_climate_*` and related `_..._impl` methods into existing collaborators:
   `climate_build_router.py`, `climate_mode_build_services.py`, `climate_scaling_service.py`, `climate_artifact_export_service.py`, `climate_station_catalog_service.py`.
2. Keep `Climate` facade public contracts stable for routes/RQ/tests exactly as done for Omni.
3. Require deterministic collaborator behavior tests, not only delegation tests, for climate router/artifact/station modules.

Risk if deferred:

1. Omni and Climate drift into inconsistent facade patterns.
2. Legacy climate branch complexity continues to hide regressions and increases change-review risk.
3. Cross-controller maintenance remains asymmetric, slowing future NoDb controller refactors.

Validation expectations for that cleanup:

    wctl run-pytest tests/nodb/test_climate_input_parser_service.py tests/nodb/test_climate_build_router_services.py tests/nodb/test_climate_scaling_service.py tests/nodb/test_climate_artifact_export_service.py tests/nodb/test_climate_station_catalog_service.py --maxfail=1
    wctl run-pytest tests/microservices/test_rq_engine_climate_routes.py tests/microservices/test_rq_engine_upload_climate_routes.py tests/weppcloud/routes/test_climate_bp.py --maxfail=1
    wctl run-pytest tests --maxfail=1

Follow-up completed in this Omni plan (2026-02-20 21:14Z):

1. Verified that climate continuity target work is already completed in `docs/mini-work-packages/20260220_nodb_climate_option2_facade_execplan.md` (Milestones 0-7 complete plus post-review deterministic hardening at `2026-02-20 16:19Z`).
2. Verified that the climate plan records deterministic non-skipped collaborator evidence and full-suite validation transcripts.
3. Recorded this Omni closeout linkage so future controller refactors can treat both Omni and Climate as Option-2-pattern-aligned baselines.

## Review Process and Severity Gates

Severity rubric:

1. `SEV0`: data corruption, lock/persistence boundary break, or incompatible facade contract break.
2. `SEV1`: route/RQ user-visible regression or broken dependency orchestration semantics.
3. `SEV2`: missing regression tests in changed path, flaky/non-deterministic behavior, maintainability risk likely to regress.
4. `SEV3`: non-blocking clarity/decomposition debt.

Gate rule for each milestone:

1. `NO-GO` on any unresolved `SEV0` or `SEV1`.
2. `NO-GO` on failed milestone validation command.
3. `NO-GO` when acceptance relies only on env-skipped tests for behaviors that can be deterministic.
4. `GO` only when all above conditions pass.

## Validation and Acceptance

Overall acceptance requires all of the following:

1. Public and quasi-public Omni contracts remain stable for route/RQ/test callsites.
2. NoDb lock/mutation/persistence semantics remain unchanged.
3. Every extracted path has targeted deterministic regression tests.
4. Milestone severity gates pass with no unresolved `SEV0`/`SEV1` findings.
5. Final suite gate passes:

    wctl run-pytest tests --maxfail=1

6. Doc lint gate passes:

    wctl doc-lint --path AGENTS.md --path docs/mini-work-packages/completed/20260220_nodb_omni_option2_facade_execplan.md

## Idempotence and Recovery

1. Milestones are intentionally incremental and independently retryable.
2. If a milestone fails, revert only that milestone’s changes, keep characterization tests, and rerun the same gate.
3. Do not batch multiple milestone refactors without passing each gate.

## Milestone Evidence

### Milestone 0 (2026-02-20 20:41Z)

Validation:

    wctl run-pytest tests/nodb/mods/test_omni_facade_contracts.py --maxfail=1
    -> 9 passed

    wctl run-pytest tests/rq/test_omni_rq.py tests/rq/test_path_ce_rq.py --maxfail=1
    -> 9 passed

    wctl run-pytest tests/weppcloud/routes/test_omni_bp_routes.py tests/weppcloud/routes/test_gl_dashboard_route.py tests/microservices/test_rq_engine_omni_routes.py --maxfail=1
    -> 56 passed

Severity gate findings:

1. None (`SEV0`: none, `SEV1`: none, `SEV2`: none, `SEV3`: none).

Gate decision:

1. `GO` (all baseline commands passed; no unresolved `SEV0`/`SEV1`).

### Milestone 1 (2026-02-20 20:44Z)

Validation:

    wctl run-pytest tests/nodb/mods/test_omni_input_parser_service.py tests/nodb/mods/test_omni_facade_contracts.py --maxfail=1
    -> 15 passed

    wctl run-pytest tests/microservices/test_rq_engine_omni_routes.py -k "run_omni and scenarios" --maxfail=1
    -> initial run failed (contract expectation mismatch in new malformed-scenarios test)
    -> rerun after milestone-local test expectation rollback/fix: 4 passed

Severity gate findings:

1. None (`SEV0`: none, `SEV1`: none, `SEV2`: none, `SEV3`: none).

Gate decision:

1. `GO` (all milestone commands passing after milestone-local correction; no unresolved `SEV0`/`SEV1`).

### Milestone 2 (2026-02-20 20:50Z)

Validation:

    wctl run-pytest tests/nodb/mods/test_omni_build_router_service.py tests/nodb/mods/test_omni.py -k "dry_run or contrast_status_report or build_contrasts" --maxfail=1
    -> initial run failed (dry-run seam regression bypassed facade monkeypatch hook)
    -> rerun after milestone-local router fix: 14 passed

    wctl run-pytest tests/microservices/test_rq_engine_omni_routes.py -k "run_omni_contrasts" --maxfail=1
    -> 25 passed

Severity gate findings:

1. None (`SEV0`: none, `SEV1`: none, `SEV2`: none, `SEV3`: none).

Gate decision:

1. `GO` (all milestone commands passing after seam-compatibility correction; no unresolved `SEV0`/`SEV1`).

### Milestone 3 (2026-02-20 20:53Z)

Validation:

    wctl run-pytest tests/nodb/mods/test_omni_mode_build_services.py tests/nodb/mods/test_omni.py -k "scenario_mode or stream_order or user_defined" --maxfail=1
    -> 20 passed

    wctl run-pytest tests/rq/test_omni_rq.py --maxfail=1
    -> 7 passed

Severity gate findings:

1. None (`SEV0`: none, `SEV1`: none, `SEV2`: none, `SEV3`: none).

Gate decision:

1. `GO` (all milestone commands passed; no unresolved `SEV0`/`SEV1`).

### Milestone 4 (2026-02-20 20:54Z)

Validation:

    wctl run-pytest tests/nodb/mods/test_omni_scaling_service.py tests/nodb/mods/test_omni.py -k "hillslope_limit or filters or order_reduction" --maxfail=1
    -> 8 passed

    wctl run-pytest tests/rq/test_omni_rq.py -k "dependency or contrast" --maxfail=1
    -> 4 passed

Severity gate findings:

1. None (`SEV0`: none, `SEV1`: none, `SEV2`: none, `SEV3`: none).

Gate decision:

1. `GO` (all milestone commands passed; no unresolved `SEV0`/`SEV1`).

### Milestone 5 (2026-02-20 20:59Z)

Validation:

    wctl run-pytest tests/nodb/mods/test_omni_artifact_export_service.py tests/nodb/mods/test_omni.py -k "report or compile or contrast_ids_geojson" --maxfail=1
    -> 13 passed

    wctl run-pytest tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/test_omni_report_templates.py --maxfail=1
    -> 6 passed

Severity gate findings:

1. None (`SEV0`: none, `SEV1`: none, `SEV2`: none, `SEV3`: none).

Gate decision:

1. `GO` (all milestone commands passed; no unresolved `SEV0`/`SEV1`).

### Milestone 6 (2026-02-20 21:06Z)

Validation:

    wctl run-pytest tests/nodb/mods/test_omni_station_catalog_service.py tests/nodb/mods/test_omni.py -k "scenario_key or dependency or landuse_skip" --maxfail=1
    -> 3 passed, 51 deselected

    wctl run-pytest tests/rq/test_omni_rq.py tests/rq/test_path_ce_rq.py --maxfail=1
    -> 11 passed

Severity gate findings:

1. None (`SEV0`: none, `SEV1`: none, `SEV2`: none, `SEV3`: none).

Gate decision:

1. `GO` (all milestone commands passed; no unresolved `SEV0`/`SEV1`).

### Milestone 7 (2026-02-20 21:14Z)

Validation:

    wctl run-pytest tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_facade_contracts.py tests/nodb/mods/test_omni_input_parser_service.py tests/nodb/mods/test_omni_build_router_service.py tests/nodb/mods/test_omni_mode_build_services.py tests/nodb/mods/test_omni_scaling_service.py tests/nodb/mods/test_omni_artifact_export_service.py tests/nodb/mods/test_omni_station_catalog_service.py --maxfail=1
    -> initial run failed (`test_build_router_sets_contrast_inputs_inside_lock_scope` expectation mismatch)
    -> rerun after milestone-local test correction: 100 passed

    wctl run-pytest tests/rq/test_omni_rq.py tests/rq/test_path_ce_rq.py tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/routes/test_omni_bp_routes.py tests/weppcloud/routes/test_gl_dashboard_route.py --maxfail=1
    -> 72 passed

    wctl run-pytest tests --maxfail=1
    -> 1894 passed, 27 skipped

    wctl doc-lint --path AGENTS.md --path docs/mini-work-packages/completed/20260220_nodb_omni_option2_facade_execplan.md
    -> 2 files validated, 0 errors, 0 warnings

Severity gate findings:

1. None (`SEV0`: none, `SEV1`: none, `SEV2`: none, `SEV3`: none).

Gate decision:

1. `GO` (all milestone and pre-handoff validation commands passed after milestone-local correction; no unresolved `SEV0`/`SEV1`).

### Post-Review Remediation (2026-02-20 22:03Z)

Validation:

    wctl run-pytest tests/nodb/mods/test_omni_build_router_service.py tests/nodb/mods/test_omni.py -k "dry_run or contrast_status_report or build_contrasts" --maxfail=1
    -> 16 passed, 40 deselected

    wctl run-pytest tests/nodb/mods/test_omni_station_catalog_service.py tests/nodb/mods/test_omni.py -k "scenario_key or dependency or landuse_skip" --maxfail=1
    -> 3 passed, 52 deselected

    wctl run-pytest tests/nodb/mods/test_omni_build_router_service.py tests/nodb/mods/test_omni_station_catalog_service.py --maxfail=1
    -> 21 passed

Severity gate findings:

1. No remaining review SEV2 findings in targeted paths (`SEV0`: none, `SEV1`: none, `SEV2`: none, `SEV3`: none).

Gate decision:

1. `GO` (all remediation validation commands passed; seam and exception-observability regressions closed).

Revision Note (2026-02-20 20:32Z, Codex): Replaced prior completed-state Omni plan with a fresh planning-only ExecPlan per request, including required Option-2 milestone mapping, test-gap closure plan, severity gates, rollback strategy, and climate continuity follow-up guidance.
Revision Note (2026-02-20 20:41Z, Codex): Completed Milestone 0 baseline execution, recorded gate evidence/GO decision, and updated living sections to reflect current execution state.
Revision Note (2026-02-20 20:44Z, Codex): Completed Milestone 1 parser regression hardening, including milestone-local gate retry and final GO evidence.
Revision Note (2026-02-20 20:50Z, Codex): Completed Milestone 2 router/orchestrator hardening with collaborator-owned status matrix coverage and seam-preserving dry-run behavior.
Revision Note (2026-02-20 20:53Z, Codex): Completed Milestone 3 mode-service hardening with deterministic treatment-mapping and stream-order rebuild-path tests.
Revision Note (2026-02-20 20:54Z, Codex): Completed Milestone 4 scaling hardening with explicit malformed-input and order-reduction rerun regressions.
Revision Note (2026-02-20 20:59Z, Codex): Completed Milestone 5 artifact hardening with collaborator-owned report compilation logic and deterministic artifact regression coverage.
Revision Note (2026-02-20 21:06Z, Codex): Completed Milestone 6 station/catalog extraction hardening with collaborator-owned helper implementations plus targeted RQ helper-output regressions.
Revision Note (2026-02-20 21:14Z, Codex): Completed Milestone 7 final gates, recorded milestone-local correction evidence, and completed climate continuity follow-up linkage.
Revision Note (2026-02-20 22:03Z, Codex): Applied review follow-ups for singleton seam fidelity and station loader exception observability, with deterministic regression coverage and passing targeted gates.
