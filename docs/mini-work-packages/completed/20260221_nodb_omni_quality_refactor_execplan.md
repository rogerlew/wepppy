# ExecPlan: Reduce `wepppy/nodb/mods/omni/omni.py` Hotspot Risk and Close Omni Test Gaps

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept current as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, Omni keeps the same route/RQ/facade behavior while reducing concentration risk in `wepppy/nodb/mods/omni/omni.py` and adding deterministic regression coverage for the highest-risk orchestration paths. The user-visible outcome is safer iteration on Omni scenarios/contrasts without reintroducing regressions in queue orchestration, report payloads, or run-state semantics.

Proof is observable via unchanged external contracts, targeted deterministic tests for newly extracted paths, and code-quality telemetry showing material reduction in `omni.py` hotspot metrics versus current baseline.

## Progress

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for every entry.

- [x] (2026-02-21 00:23Z) Read required guidance and templates: `AGENTS.md`, `wepppy/nodb/AGENTS.md`, `docs/prompt_templates/codex_exec_plans.md`, `docs/standards/nodb-facade-collaborator-pattern.md`.
- [x] (2026-02-21 00:23Z) Captured current Omni hotspot baseline and risk areas from code + observability + radon metrics.
- [x] (2026-02-21 00:23Z) Authored this ad hoc mini work-package for end-to-end execution.
- [x] (2026-02-21 00:27Z) Milestone 0 complete: refreshed baseline telemetry and revalidated route/RQ/facade contract characterization gates.
- [x] (2026-02-21 00:32Z) Milestone 1 complete: hardened exception contracts/logging in `omni.py` with deterministic regression coverage.
- [x] (2026-02-21 00:36Z) Milestone 2 complete: moved GeoJSON contrast build internals into `OmniArtifactExportService` helpers with facade seams preserved.
- [x] (2026-02-21 00:40Z) Milestone 3 complete: extracted shared contrast-mapping helper and de-duplicated selection-mode builders.
- [x] (2026-02-21 00:44Z) Milestone 4 complete: extracted scenario/contrast run orchestration into `OmniRunOrchestrationService` and preserved facade entrypoints.
- [x] (2026-02-21 00:45Z) Milestone 5 complete: deterministic regression gaps addressed and full Omni-focused gate suites passed.
- [x] (2026-02-21 00:51Z) Milestone 6 complete: captured final telemetry deltas, ran full-suite validation, and documented residual risks/deferred work.
- [x] (2026-02-21 01:26Z) Deferred follow-on extraction complete: moved `_build_contrasts_user_defined_areas` and `_build_contrasts_stream_order` out of `omni.py` into `OmniContrastBuildService`, preserved facade delegators/contracts, and re-ran targeted + full validation gates.

## Surprises & Discoveries

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for new entries.

- (2026-02-21 00:23Z) Observation: `omni.py` remains a top risk hotspot even after prior Option-2 extraction work.
  Evidence: `python3 tools/code_quality_observability.py --json-out /tmp/omni-quality.json --md-out /tmp/omni-quality.md` reported `python_file_sloc=3608`, `python_function_len=353`, `python_cc=104` for `wepppy/nodb/mods/omni/omni.py`.

- (2026-02-21 00:23Z) Observation: single largest complexity concentration is still `_build_contrast_ids_geojson_impl`.
  Evidence: `radon cc -s wepppy/nodb/mods/omni/omni.py` reports `Omni._build_contrast_ids_geojson_impl - F (104)`.

- (2026-02-21 00:23Z) Observation: long-method footprint is concentrated in a small subset of orchestration/build paths.
  Evidence: function length scan shows seven methods/functions over 150 lines: `_build_contrast_ids_geojson_impl`, `_build_contrasts_stream_order`, `_build_contrasts_user_defined_areas`, `_build_contrasts_user_defined_hillslope_groups`, `_build_contrasts`, `run_omni_scenarios`, `_run_contrast`.

- (2026-02-21 00:23Z) Observation: broad catch usage and generic exception contracts still exist in production flow.
  Evidence: `rg -n 'except Exception|except:|raise Exception\\(' wepppy/nodb/mods/omni/omni.py` includes active paths at `omni.py:889`, `omni.py:3315`, `omni.py:3598`, `omni.py:3756`, `omni.py:2107`, `omni.py:3824`.

- (2026-02-21 00:27Z) Observation: `code_quality_observability` changed-file analysis was unavailable against `origin/master`, so hotspot evidence must come from the current-tree section plus direct `radon` output.
  Evidence: `/tmp/omni-quality-baseline.md` reports "_No changed-file analysis available_" and still lists `wepppy/nodb/mods/omni/omni.py` at `python_file_sloc=3608`, `python_function_len=353`, `python_cc=104`.

- (2026-02-21 00:27Z) Observation: baseline cross-layer characterization gates are currently green before refactor edits.
  Evidence: `wctl run-pytest tests/nodb/mods/test_omni_facade_contracts.py tests/rq/test_omni_rq.py --maxfail=1` passed `18/18`; `wctl run-pytest tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_omni_bp_routes.py --maxfail=1` passed `42/42`.

- (2026-02-21 00:32Z) Observation: narrowing `_scenario_name_from_scenario_definition` must still absorb `KeyError` from `OmniScenario.parse` to preserve existing fallback naming behavior for non-enum scenario values used by clone tests.
  Evidence: targeted test initially failed with `KeyError: Invalid scenario: dummy`; expanded catch to `(TypeError, ValueError, KeyError)` restored compatibility.

- (2026-02-21 00:32Z) Observation: file-removal cleanup in `delete_scenarios` and `clear_contrasts` can be narrowed to `OSError` without breaking current contract tests.
  Evidence: new deterministic tests `test_delete_scenarios_propagates_non_oserror_cleanup_failures` and `test_clear_contrasts_propagates_non_oserror_from_report_cleanup` both passed.

- (2026-02-21 00:36Z) Observation: direct relocation of `_build_contrast_ids_geojson_impl` risks recursion unless the service owns the implementation and both facade methods delegate outward.
  Evidence: extraction finalized with `Omni._build_contrast_ids_geojson()` and `Omni._build_contrast_ids_geojson_impl()` both delegating to `OmniArtifactExportService.build_contrast_ids_geojson`.

- (2026-02-21 00:36Z) Observation: empty-feature fallbacks for `stream_order` and `user_defined_areas` can remain dependency-free after extraction.
  Evidence: deterministic service tests for both modes pass without GIS imports by exercising report-driven empty-selection paths.

- (2026-02-21 00:40Z) Observation: stream-order contrast naming uses normalized pair keys (`control_key`/`contrast_key`) while user-defined/cumulative builders can emit `None` control names for base-scenario control.
  Evidence: new shared mapping helper required explicit optional label override inputs to keep per-mode contrast name contracts stable.

- (2026-02-21 00:40Z) Observation: de-duplicating only path-mapping assembly removes repeated branch logic without changing report-entry schema.
  Evidence: cumulative/stream-order/user-defined builders now call one helper for sidecar path mapping; existing report-entry payload fields remained unchanged and tests stayed green.

- (2026-02-21 00:44Z) Observation: run orchestration extraction can be done with facade-level delegation while preserving lock boundaries because locking/state writes live on the `Omni` instance methods invoked by the collaborator.
  Evidence: new `OmniRunOrchestrationService` methods call existing `omni.locked()`, status writers, dependency-tree writers, and `_post_omni_run` hooks directly.

- (2026-02-21 00:44Z) Observation: delegation seams are regression-prone unless explicitly tested for argument passthrough.
  Evidence: added deterministic tests for `run_omni_scenarios`, `run_omni_contrasts`, and `run_omni_contrast` delegation to `_OMNI_RUN_ORCHESTRATION_SERVICE`.

- (2026-02-21 00:45Z) Observation: existing Omni-focused suites provided broad deterministic coverage once new collaborator-delegation tests were added; no additional environment-gated-only assertions were needed for changed paths.
  Evidence: combined NoDb Omni suites (`113` tests) and cross-layer RQ/routes suites (`72` tests) passed with all new collaborator extractions enabled.

- (2026-02-21 00:51Z) Observation: `omni.py` is no longer the global max CC hotspot after extraction milestones.
  Evidence: final observability (`/tmp/omni-quality-after.md`) reports `python_cc=55` for `omni.py`; `python_max_cc_top20` no longer lists `omni.py` in top-10, while baseline was `python_cc=104`.

- (2026-02-21 00:51Z) Observation: facade hotspot reduction is material but user-defined/stream-order builders still dominate remaining `omni.py` complexity.
  Evidence: final `radon cc` top methods are `_build_contrasts_user_defined_areas (F 55)` and `_build_contrasts_stream_order (F 50)`.

- (2026-02-21 01:11Z) Observation: stream-order rebuild tests depend on monkeypatching the module-level `_prune_stream_order` seam on `omni.py`.
  Evidence: `tests/nodb/mods/test_omni.py::test_build_contrasts_stream_order_stale_rebuild_decisions` initially failed after extraction with `AttributeError` when `_prune_stream_order` was imported directly in the collaborator.

- (2026-02-21 01:26Z) Observation: after extracting the two remaining heavy contrast builders, `omni.py` dropped out of the global max-function-length and max-CC hotspot lists.
  Evidence: `/tmp/omni-quality-followup.md` no longer lists `wepppy/nodb/mods/omni/omni.py` under `python_max_function_len_top20` or `python_max_cc_top20`; `radon cc -s wepppy/nodb/mods/omni/omni.py` now tops at `_run_contrast - E (34)`.

## Decision Log

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for new entries.

- Decision: Keep the existing Option-2 contract-first approach and continue slimming `omni.py` by moving cohesive internals to current Omni collaborators.
  Rationale: This aligns with `docs/standards/nodb-facade-collaborator-pattern.md` and avoids route/RQ contract churn.
  Date/Author: 2026-02-21 00:23Z / Codex

- Decision: Prioritize extraction by risk and metric impact: GeoJSON builder and contrast/run orchestration before lower-impact helpers.
  Rationale: These paths dominate current max CC and max function-length telemetry.
  Date/Author: 2026-02-21 00:23Z / Codex

- Decision: Treat quasi-public Omni helper methods used by RQ as fixed contracts unless explicitly approved.
  Rationale: `wepppy/rq/omni_rq.py` and `wepppy/rq/path_ce_rq.py` consume helper outputs for dependency metadata and rerun semantics.
  Date/Author: 2026-02-21 00:23Z / Codex

- Decision: Add deterministic collaborator and cross-layer tests before/with each extraction milestone.
  Rationale: Environment-gated integrations can skip; deterministic tests are required to prove behavioral parity.
  Date/Author: 2026-02-21 00:23Z / Codex

- Decision: Treat Milestone 0 baselines (`radon raw/cc` and observability) as immutable comparison anchors for Milestone 6 closeout deltas.
  Rationale: Stable before/after metric comparability is required to prove hotspot reduction and avoid optimistic drift claims.
  Date/Author: 2026-02-21 00:27Z / Codex

- Decision: Preserve scenario-name fallback behavior for unknown scenario strings while still narrowing parse exception handling.
  Rationale: `_omni_clone` tests and internal helper usage rely on non-enum scenario labels resolving to string names instead of propagating parser errors.
  Date/Author: 2026-02-21 00:32Z / Codex

- Decision: Keep `_build_contrast_ids_geojson_impl` as a compatibility shim that delegates to the artifact service.
  Rationale: preserves quasi-public facade API shape for any callers while removing hotspot complexity from `omni.py`.
  Date/Author: 2026-02-21 00:36Z / Codex

- Decision: Implement one shared `build_contrast_mapping` helper in `OmniModeBuildServices` and reuse it from cumulative, stream-order, user-defined-areas, and user-defined-hillslope-group builders.
  Rationale: meets de-duplication target with minimal contract risk by extracting only repeated mapping/path assembly logic.
  Date/Author: 2026-02-21 00:40Z / Codex

- Decision: Introduce a dedicated `OmniRunOrchestrationService` collaborator for `run_omni_scenarios`, `run_omni_contrasts`, and `run_omni_contrast`, with facade methods reduced to delegators.
  Rationale: lowers facade orchestration volume while keeping public Omni method signatures and side effects stable.
  Date/Author: 2026-02-21 00:44Z / Codex

- Decision: Treat Milestone 5 as validation-and-gap-closure only (no additional contract-expanding behavior changes) after deterministic delegation and mapping tests were in place.
  Rationale: broadening behavior in Milestone 5 would increase risk immediately before final telemetry and full-suite gates.
  Date/Author: 2026-02-21 00:45Z / Codex

- Decision: Defer further decomposition of selection-mode builders (`user_defined_areas`, `stream_order`) to a follow-on package rather than expand scope during closeout.
  Rationale: current contract-safe extraction already met hotspot reduction goals and all validation gates; additional deep surgery would add late-stage regression risk.
  Date/Author: 2026-02-21 00:51Z / Codex

- Decision: Execute deferred extraction by introducing `OmniContrastBuildService` and reducing `Omni._build_contrasts_stream_order` / `Omni._build_contrasts_user_defined_areas` to facade delegators.
  Rationale: isolates remaining high-complexity contrast builders while keeping facade signatures, lock/persistence ownership, and monkeypatch seams stable.
  Date/Author: 2026-02-21 01:05Z / Codex

- Decision: Preserve module-level `_prune_stream_order` compatibility seam during collaborator extraction.
  Rationale: existing deterministic regression tests patch this symbol on `omni.py`; preserving it avoids behavioral drift in stale-rebuild paths.
  Date/Author: 2026-02-21 01:11Z / Codex

## Outcomes & Retrospective

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for new entries.

- (2026-02-21 00:23Z) Outcome: Planning-only pass completed; no production Omni code changed in this authoring step.
- (2026-02-21 00:23Z) Retrospective: Prior Option-2 extraction created strong collaborator seams, but major residual complexity still sits in facade `_..._impl` orchestration paths and needs one focused follow-up package.
- (2026-02-21 00:27Z) Outcome: Milestone 0 completed with no contract regressions detected pre-refactor.
  Evidence: `python3 tools/code_quality_observability.py --base-ref origin/master --json-out /tmp/omni-quality-baseline.json --md-out /tmp/omni-quality-baseline.md` (observe-only success), `radon raw` (`LOC 4190`, `SLOC 3500`), and `radon cc` (`_build_contrast_ids_geojson_impl - F (104)`).
- (2026-02-21 00:27Z) Outcome: Milestone 0 validation command summary.
  Evidence: `wctl run-pytest tests/nodb/mods/test_omni_facade_contracts.py tests/rq/test_omni_rq.py --maxfail=1` -> PASS (`18 passed`); `wctl run-pytest tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_omni_bp_routes.py --maxfail=1` -> PASS (`42 passed`).
- (2026-02-21 00:32Z) Outcome: Milestone 1 delivered typed exception contracts (`ValueError`/`RuntimeError`) and logger-backed clone failure reporting while preserving message contracts.
  Evidence: `omni.py` now uses logger warnings instead of `print(...)` in `_omni_clone`; generic raises changed to `ValueError('No soil erosion data found!')` and `RuntimeError('No scenarios to run')`; file-cleanup catch blocks narrowed to `OSError`.
- (2026-02-21 00:32Z) Outcome: Milestone 1 validation command summary.
  Evidence: `wctl run-pytest tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_facade_contracts.py -k "delete_scenarios or clear_contrasts or run_omni_scenarios or run_omni_contrast" --maxfail=1` -> PASS (`9 passed`); additional deterministic regression checks `wctl run-pytest tests/nodb/mods/test_omni.py -k "omni_clone_logs_directory_copy_permission_errors or build_contrasts_raises_value_error_when_no_soil_data" --maxfail=1` -> PASS (`2 passed`).
- (2026-02-21 00:36Z) Outcome: Milestone 2 removed GeoJSON overlay build internals from facade and centralized mode-specific generation in artifact collaborator helpers.
  Evidence: `wepppy/nodb/mods/omni/omni.py` now keeps only delegator seams for `_build_contrast_ids_geojson*`; `wepppy/nodb/mods/omni/omni_artifact_export_service.py` now owns selection normalization, source collection, and stream/user-defined/default GeoJSON emit paths.
- (2026-02-21 00:36Z) Outcome: Milestone 2 validation command summary.
  Evidence: `wctl run-pytest tests/nodb/mods/test_omni_artifact_export_service.py tests/nodb/mods/test_omni.py -k "contrast_ids_geojson or user_defined_areas or stream_order" --maxfail=1` -> PASS (`12 passed`).
- (2026-02-21 00:40Z) Outcome: Milestone 3 removed duplicated sidecar path-assembly loops from four contrast builders while preserving naming/sidecar schemas.
  Evidence: `OmniModeBuildServices.build_contrast_mapping(...)` now drives mapping assembly in `_build_contrasts`, `_build_contrasts_stream_order`, `_build_contrasts_user_defined_hillslope_groups`, and `_build_contrasts_user_defined_areas`.
- (2026-02-21 00:40Z) Outcome: Milestone 3 validation command summary.
  Evidence: `wctl run-pytest tests/nodb/mods/test_omni_mode_build_services.py tests/nodb/mods/test_omni.py -k "build_contrasts and (stream_order or user_defined_hillslope_groups or user_defined_areas or cumulative)" --maxfail=1` -> PASS (`6 passed`); `wctl run-pytest tests/rq/test_omni_rq.py -k "contrast" --maxfail=1` -> PASS (`3 passed`).
- (2026-02-21 00:44Z) Outcome: Milestone 4 extracted orchestration logic into new collaborator file `wepppy/nodb/mods/omni/omni_run_orchestration_service.py` and kept Omni facade method signatures unchanged.
  Evidence: `Omni.run_omni_scenarios`, `Omni.run_omni_contrasts`, and `Omni.run_omni_contrast` now delegate to `_OMNI_RUN_ORCHESTRATION_SERVICE`.
- (2026-02-21 00:44Z) Outcome: Milestone 4 validation command summary.
  Evidence: `wctl run-pytest tests/nodb/mods/test_omni.py tests/rq/test_omni_rq.py -k "run_omni_scenarios or run_omni_scenario or run_omni_contrasts or run_omni_contrast" --maxfail=1` -> PASS (`19 passed`); `wctl run-pytest tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/routes/test_omni_bp_routes.py --maxfail=1` -> PASS (`45 passed`).
- (2026-02-21 00:45Z) Outcome: Milestone 5 Omni-focused gate sweep passed end-to-end with deterministic regression additions included.
  Evidence: `wctl run-pytest tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_facade_contracts.py tests/nodb/mods/test_omni_input_parser_service.py tests/nodb/mods/test_omni_build_router_service.py tests/nodb/mods/test_omni_mode_build_services.py tests/nodb/mods/test_omni_scaling_service.py tests/nodb/mods/test_omni_artifact_export_service.py tests/nodb/mods/test_omni_station_catalog_service.py --maxfail=1` -> PASS (`113 passed`).
- (2026-02-21 00:45Z) Outcome: Milestone 5 cross-layer gate summary.
  Evidence: `wctl run-pytest tests/rq/test_omni_rq.py tests/rq/test_path_ce_rq.py tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/routes/test_omni_bp_routes.py tests/weppcloud/routes/test_gl_dashboard_route.py --maxfail=1` -> PASS (`72 passed`).
- (2026-02-21 00:51Z) Outcome: Milestone 6 telemetry delta summary for `omni.py`.
  Evidence: observability hotspot metrics moved from `python_file_sloc=3608` -> `2887` (`-721`), `python_function_len=353` -> `284` (`-69`), and `python_cc=104` -> `55` (`-49`); `radon raw` moved from `LOC 4190/SLOC 3500` -> `LOC 3400/SLOC 2787`; top prior hotspot `_build_contrast_ids_geojson_impl (F 104)` is now delegator-level (`A 1`).
- (2026-02-21 00:51Z) Outcome: Milestone 6 validation command summary.
  Evidence: `python3 tools/code_quality_observability.py --base-ref origin/master --json-out /tmp/omni-quality-after.json --md-out /tmp/omni-quality-after.md` -> PASS; `radon raw wepppy/nodb/mods/omni/omni.py` -> PASS; `radon cc -s wepppy/nodb/mods/omni/omni.py` -> PASS; `wctl run-pytest tests --maxfail=1` -> PASS (`1907 passed`, `27 skipped`).
- (2026-02-21 00:51Z) Retrospective: residual risks and deferred work.
  Evidence: Remaining high-complexity builders (`_build_contrasts_user_defined_areas`, `_build_contrasts_stream_order`) should be split into collaborator methods in a follow-on package; deprecation-warning cleanup and optional GIS dependency-path hardening were intentionally deferred because they are orthogonal to Omni facade contract preservation.

- (2026-02-21 01:12Z) Outcome: deferred collaborator extraction delivered with contract-preserving facade seams.
  Evidence: `wepppy/nodb/mods/omni/omni_contrast_build_service.py` now owns `build_contrasts_stream_order` and `build_contrasts_user_defined_areas`; `wepppy/nodb/mods/omni/omni.py` methods delegate via `_OMNI_CONTRAST_BUILD_SERVICE`.

- (2026-02-21 01:26Z) Outcome: deferred extraction validation command summary.
  Evidence: `wctl run-pytest tests/nodb/mods/test_omni_contrast_build_service.py tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_mode_build_services.py tests/nodb/mods/test_omni_artifact_export_service.py --maxfail=1` -> PASS (`74 passed`); `wctl run-pytest tests/nodb/mods/test_omni_facade_contracts.py tests/rq/test_omni_rq.py tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/routes/test_omni_bp_routes.py --maxfail=1` -> PASS (`64 passed`); `wctl run-pytest tests --maxfail=1` -> PASS (`1916 passed`, `27 skipped`).

- (2026-02-21 01:26Z) Outcome: post-extraction `omni.py` telemetry delta versus Milestone 6 closeout baseline.
  Evidence: `python3 tools/code_quality_observability.py --base-ref origin/master --json-out /tmp/omni-quality-followup.json --md-out /tmp/omni-quality-followup.md` and `radon` show `python_file_sloc` hotspot value improved `2887 -> 2429` (`-458`), `radon raw` improved `LOC/SLOC 3400/2787 -> 2880/2329` (`-520/-458`), and max method CC in `omni.py` improved from `55 -> 34`.

- (2026-02-21 01:26Z) Retrospective: residual complexity risk shifted from contrast builders to clone/build orchestration internals.
  Evidence: current `radon cc` leaders in `omni.py` are `_run_contrast (E 34)`, `_omni_clone (D 29)`, `_build_contrasts (D 26)`, and `_build_contrasts_user_defined_hillslope_groups (D 26)`; further extraction remains optional follow-on work.

- (2026-02-21 01:26Z) Retrospective: extracted builders still need internal decomposition, but risk is now isolated to the collaborator boundary instead of the Omni facade.
  Evidence: `radon cc -s wepppy/nodb/mods/omni/omni_contrast_build_service.py` reports `build_contrasts_user_defined_areas (F 55)` and `build_contrasts_stream_order (F 50)` in the new service.

## Context and Orientation

Primary facade and collaborators:

1. `wepppy/nodb/mods/omni/omni.py` (facade + residual heavy internals).
2. `wepppy/nodb/mods/omni/omni_build_router.py`.
3. `wepppy/nodb/mods/omni/omni_mode_build_services.py`.
4. `wepppy/nodb/mods/omni/omni_scaling_service.py`.
5. `wepppy/nodb/mods/omni/omni_artifact_export_service.py`.
6. `wepppy/nodb/mods/omni/omni_station_catalog_service.py`.
7. `wepppy/nodb/mods/omni/omni_input_parser.py`.
8. Typed surface: `wepppy/nodb/mods/omni/omni.pyi`.

External contract surfaces that must remain stable:

1. RQ flows: `wepppy/rq/omni_rq.py`, `wepppy/rq/path_ce_rq.py`.
2. API/route flows: `wepppy/microservices/rq_engine/omni_routes.py`, `wepppy/weppcloud/routes/nodb_api/omni_bp.py`, `wepppy/weppcloud/routes/gl_dashboard.py`.
3. Existing coverage suites:
   `tests/nodb/mods/test_omni.py`,
   `tests/nodb/mods/test_omni_*_service.py`,
   `tests/nodb/mods/test_omni_facade_contracts.py`,
   `tests/rq/test_omni_rq.py`,
   `tests/microservices/test_rq_engine_omni_routes.py`,
   `tests/weppcloud/routes/test_omni_bp.py`,
   `tests/weppcloud/routes/test_omni_bp_routes.py`,
   `tests/weppcloud/routes/test_gl_dashboard_route.py`.

Current quality baseline (to be re-measured in Milestone 0):

1. `omni.py` raw size: `LOC 4190`, `SLOC 3500` (`radon raw`).
2. Hotspot telemetry: `python_file_sloc=3608`, `python_function_len=353`, `python_cc=104` (`tools/code_quality_observability.py`).
3. Highest complexity methods:
   `_build_contrast_ids_geojson_impl (F 104)`,
   `_build_contrasts_user_defined_areas (F 60)`,
   `_build_contrasts_stream_order (F 54)`,
   `_run_contrast (E 34)`,
   `_build_contrasts (E 31)`,
   `_build_contrasts_user_defined_hillslope_groups (E 31)`.

## Invariants

1. Preserve route/RQ/facade observable behavior unless a contract change is explicitly approved.
2. Preserve NoDb lock and persistence boundaries (`with self.locked()`, `nodb_setter`, `dump_and_unlock` ownership).
3. No broad silent exception swallows in production flow; log context and preserve explicit contracts.
4. Keep module-level collaborator singleton seams intact where tests monkeypatch them.
5. Keep extraction sequence incremental and milestone-reversible.

## Milestone Plan

### Milestone 0: Baseline Refresh and Contract Characterization

Scope:
Refresh quality telemetry and reconfirm current contract behavior before new extraction.

Target files:

1. `wepppy/nodb/mods/omni/omni.py` (read-only in this milestone).
2. `tests/nodb/mods/test_omni_facade_contracts.py`.
3. `tests/rq/test_omni_rq.py`.
4. `tests/microservices/test_rq_engine_omni_routes.py`.
5. `tests/weppcloud/routes/test_omni_bp_routes.py`.

Validation commands:

    python3 tools/code_quality_observability.py --base-ref origin/master --json-out /tmp/omni-quality-baseline.json --md-out /tmp/omni-quality-baseline.md
    radon raw wepppy/nodb/mods/omni/omni.py
    radon cc -s wepppy/nodb/mods/omni/omni.py
    wctl run-pytest tests/nodb/mods/test_omni_facade_contracts.py tests/rq/test_omni_rq.py --maxfail=1
    wctl run-pytest tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_omni_bp_routes.py --maxfail=1

Go/No-Go:

1. `NO-GO` if baseline contract tests fail before refactor edits.
2. `NO-GO` if baseline metrics are not recorded in this plan.

### Milestone 1: Exception and Error-Contract Hardening

Scope:
Remove broad/non-observable failure handling in `omni.py` where safe to narrow, and replace generic raises with explicit contract errors.

Target files:

1. `wepppy/nodb/mods/omni/omni.py`.
2. `tests/nodb/mods/test_omni.py`.
3. `tests/nodb/mods/test_omni_facade_contracts.py`.

Required work:

1. Replace `print(...)` exception paths in clone helpers with logger-backed handling.
2. Narrow broad catches where expected exception classes are known.
3. Convert generic `raise Exception(...)` to explicit exceptions (`ValueError` or `RuntimeError`) with stable messages where externally observed.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_facade_contracts.py -k "delete_scenarios or clear_contrasts or run_omni_scenarios or run_omni_contrast" --maxfail=1

Go/No-Go:

1. `NO-GO` if any route/RQ-facing error message contract changes without explicit documentation and test updates.

### Milestone 2: Extract GeoJSON Contrast Build Internals

Scope:
Move `_build_contrast_ids_geojson_impl` internals out of facade into `OmniArtifactExportService` mode-specific helpers while preserving facade method names.

Target files:

1. `wepppy/nodb/mods/omni/omni.py`.
2. `wepppy/nodb/mods/omni/omni_artifact_export_service.py`.
3. `wepppy/nodb/mods/omni/omni.pyi`.
4. `tests/nodb/mods/test_omni_artifact_export_service.py`.
5. `tests/nodb/mods/test_omni.py`.

Required work:

1. Keep `Omni._build_contrast_ids_geojson()` as facade seam.
2. Move heavy implementation branches (`stream_order`, `user_defined_areas`, cumulative/default overlays) into collaborator methods.
3. Preserve optional-dependency behavior and empty-feature fallbacks exactly.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni_artifact_export_service.py tests/nodb/mods/test_omni.py -k "contrast_ids_geojson or user_defined_areas or stream_order" --maxfail=1

Go/No-Go:

1. `NO-GO` if contrast overlay payload structure changes (`FeatureCollection`, `properties`, labels/IDs) without explicit approval.

### Milestone 3: De-duplicate Contrast Selection Builders

Scope:
Factor shared contrast assembly/report-entry logic out of `_build_contrasts`, `_build_contrasts_stream_order`, `_build_contrasts_user_defined_hillslope_groups`, and `_build_contrasts_user_defined_areas`.

Target files:

1. `wepppy/nodb/mods/omni/omni.py` and/or `wepppy/nodb/mods/omni/omni_mode_build_services.py`.
2. `tests/nodb/mods/test_omni_mode_build_services.py`.
3. `tests/nodb/mods/test_omni.py`.

Required work:

1. Extract a single reusable helper for contrast mapping generation (`top2wepp` + selected topaz set + control/contrast scenario resolution).
2. Preserve contrast sidecar format and run report field schema.
3. Keep selection-mode-specific behavior (skips, labels, signatures) unchanged.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni_mode_build_services.py tests/nodb/mods/test_omni.py -k "build_contrasts and (stream_order or user_defined_hillslope_groups or user_defined_areas or cumulative)" --maxfail=1
    wctl run-pytest tests/rq/test_omni_rq.py -k "contrast" --maxfail=1

Go/No-Go:

1. `NO-GO` if sidecar schema or contrast naming contracts drift.

### Milestone 4: Extract Scenario/Contrast Run Orchestration

Scope:
Reduce facade orchestration volume by moving cohesive run/clone orchestration internals to dedicated collaborators while preserving facade entrypoints.

Target files:

1. `wepppy/nodb/mods/omni/omni.py`.
2. `wepppy/nodb/mods/omni/omni_build_router.py` and/or a new collaborator module under `wepppy/nodb/mods/omni/`.
3. `wepppy/nodb/mods/omni/omni.pyi`.
4. `tests/nodb/mods/test_omni.py`.
5. `tests/rq/test_omni_rq.py`.
6. `tests/microservices/test_rq_engine_omni_routes.py`.

Required work:

1. Keep `run_omni_scenarios`, `run_omni_scenario`, `run_omni_contrasts`, `run_omni_contrast` facade signatures stable.
2. Preserve two-pass scenario dependency semantics and contrast dependency-tree update semantics.
3. Preserve NoDb lock boundaries and run-status side effects.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni.py tests/rq/test_omni_rq.py -k "run_omni_scenarios or run_omni_scenario or run_omni_contrasts or run_omni_contrast" --maxfail=1
    wctl run-pytest tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/routes/test_omni_bp_routes.py --maxfail=1

Go/No-Go:

1. `NO-GO` if dependency metadata, rerun decisions, or queue-trigger expectations change.

### Milestone 5: Fill Deterministic Test Gaps + Full Omni Gates

Scope:
Close remaining under-characterized branches and run full Omni-related validation gates.

Target tests to add/expand:

1. Deterministic failure-path tests for narrowed exception boundaries.
2. Scenario/contrast orchestration branch matrix tests (skip, in-progress, up-to-date, rerun).
3. GeoJSON mode parity tests for unchanged payload schemas.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_facade_contracts.py tests/nodb/mods/test_omni_input_parser_service.py tests/nodb/mods/test_omni_build_router_service.py tests/nodb/mods/test_omni_mode_build_services.py tests/nodb/mods/test_omni_scaling_service.py tests/nodb/mods/test_omni_artifact_export_service.py tests/nodb/mods/test_omni_station_catalog_service.py --maxfail=1
    wctl run-pytest tests/rq/test_omni_rq.py tests/rq/test_path_ce_rq.py tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/routes/test_omni_bp_routes.py tests/weppcloud/routes/test_gl_dashboard_route.py --maxfail=1

Go/No-Go:

1. `NO-GO` if any unresolved `SEV0`/`SEV1` finding remains or any Omni gate fails.

### Milestone 6: Final Telemetry Comparison and Closeout

Scope:
Measure quality deltas and capture residual debt with explicit follow-up notes.

Validation commands:

    python3 tools/code_quality_observability.py --base-ref origin/master --json-out /tmp/omni-quality-after.json --md-out /tmp/omni-quality-after.md
    radon raw wepppy/nodb/mods/omni/omni.py
    radon cc -s wepppy/nodb/mods/omni/omni.py
    wctl run-pytest tests --maxfail=1

Acceptance targets:

1. `wepppy/nodb/mods/omni/omni.py` metrics improve materially from Milestone 0 baseline.
2. At least top-1 complexity hotspot (`_build_contrast_ids_geojson_impl`) is removed from facade or reduced below red band equivalent.
3. Full-suite gate passes or any blocker is documented with exact failing tests and cause.

## Concrete Steps

Run all commands from `/workdir/wepppy`.

1. Execute Milestone 0 commands and record baseline metrics + contract test transcript snippets in this plan.
2. Implement Milestones 1-4 in order; after each milestone, run the listed validation commands and update all living-document sections.
3. Complete Milestone 5 gap-filling tests and run Omni-focused gate commands.
4. Complete Milestone 6 telemetry + full-suite validation and write final `Outcomes & Retrospective` entries.

## Validation and Acceptance

Global acceptance requires all of the following:

1. Facade and cross-layer contracts remain stable for routes/RQ/tests unless explicitly approved and documented.
2. Lock/persistence semantics are preserved at existing boundaries.
3. No new broad exception swallow patterns in production flow.
4. Added tests cover exact extracted/fixed paths with deterministic assertions.
5. Code-quality telemetry for `omni.py` trends materially better than baseline and is captured in this plan.

## Risk and Rollback

1. Risk: contract drift while extracting heavy orchestration.
   Mitigation: characterization-first tests and milestone-local gates.
   Rollback: revert only latest milestone diff and re-run that milestone’s gate.

2. Risk: optional GIS dependency branches regress in GeoJSON outputs.
   Mitigation: deterministic fallback and import-error tests per selection mode.
   Rollback: rewire facade to prior implementation and keep new tests to guide fix.

3. Risk: RQ dependency metadata semantics drift.
   Mitigation: dedicated RQ helper-output regressions for both scenario and contrast paths.
   Rollback: restore previous helper wiring while preserving test additions.

## Idempotence and Recovery

This plan is incremental and idempotent by milestone. If a milestone fails:

1. Revert only that milestone’s changes.
2. Re-run the milestone-specific validation commands.
3. Update `Progress`, `Surprises & Discoveries`, and `Decision Log` with failure evidence and revised approach.

Do not proceed to the next milestone until the current one is green.

## Out of Scope

1. Frontend redesign or large Omni UI controller rewrites.
2. Queue dependency graph rewiring not required by Omni contract preservation.
3. Broad refactors outside Omni collaborators and directly related tests.

## Artifacts and Notes

Record concise evidence as work proceeds:

1. Before/after telemetry snippets for `omni.py`.
2. Milestone command results (short pass/fail summaries).
3. Any contract-change justification with explicit route/RQ/test impact.

Revision Note (2026-02-21 00:23Z, Codex): Created this ad hoc mini work-package to execute a contract-safe Omni hotspot reduction and deterministic test-gap closure program after prior Option-2 extraction work.
