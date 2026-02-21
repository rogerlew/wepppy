# ExecPlan: Refactor `wepppy/nodb/core/climate.py` with a Stable `Climate` Facade + Collaborators (Option 2)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept current as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, `wepppy/nodb/core/climate.py` keeps the current public `Climate` facade behavior while moving internals into focused collaborator services. The user-visible goal is regression-safe maintainability: queue routes, Flask routes, and downstream WEPP tasks should continue to interact with `Climate` exactly as they do now, while implementation complexity and change risk are reduced.

Proof will be observable through characterization tests, targeted collaborator regression tests, and full-suite pre-handoff validation. The plan is intentionally incremental so each extraction step is independently verifiable and reversible.

## Progress

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for every entry.

- [x] (2026-02-20 06:06Z) Read required guidance: `AGENTS.md`, `wepppy/nodb/AGENTS.md`, `tests/AGENTS.md`, and `docs/prompt_templates/codex_exec_plans.md`.
- [x] (2026-02-20 06:06Z) Characterized `wepppy/nodb/core/climate.py` hotspots and contracts from code + tests + route call sites.
- [x] (2026-02-20 06:06Z) Authored this new ad hoc ExecPlan and initially set root `AGENTS.md` active-plan pointer (later reset at closeout).
- [x] (2026-02-20 06:20Z) Milestone 0 complete: captured baseline metrics and seeded characterization evidence with passing targeted suites (`7 passed`, `13 passed`).
- [x] (2026-02-20 06:30Z) Milestone 1 complete: extracted `ClimateInputParsingService`, rewired `Climate.parse_inputs`, and added parser regression coverage (catalog/spatial/year/deprecation guard).
- [x] (2026-02-20 06:33Z) Milestone 2 complete: extracted `ClimateBuildRouter`, rewired `Climate.build`, and added router orchestration/trigger/timestamp regression coverage.
- [x] (2026-02-20 06:35Z) Milestone 3 complete: extracted `ClimateModeBuildServices` mode-routing collaborator with dispatch-matrix regressions.
- [x] (2026-02-20 06:37Z) Milestone 4 complete: extracted `ClimateScalingService`, rewired scaling facade methods, and added scalar/monthly/spatial validation + behavior regressions.
- [x] (2026-02-20 06:39Z) Milestone 5 complete: extracted `ClimateArtifactExportService`, rewired parquet/PDS/Atlas14 facade methods, and added artifact regression coverage.
- [x] (2026-02-20 06:41Z) Milestone 6 complete: extracted `ClimateStationCatalogService`, rewired catalog/station facade methods, and added station/catalog regression coverage.
- [x] (2026-02-20 06:58Z) Milestone 7 complete: finalized facade wiring, reran final-state pre-handoff gate (`1814 passed`, `27 skipped`), and completed closeout updates.
- [x] (2026-02-20 06:58Z) Closeout housekeeping complete: reset root `AGENTS.md` ad hoc active ExecPlan pointer to `none designated`.
- [x] (2026-02-20 16:19Z) Review remediation complete: replaced skipped-only Milestone 4/5 evidence with deterministic non-skipped annual-monthly scaling and Atlas14 branch test transcripts; tightened router cleanup exception handling.

## Surprises & Discoveries

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for new entries.

- (2026-02-20 06:06Z) Observation: `wepppy/nodb/core/climate.py` is a major hotspot (`LOC 3578`, `SLOC 2708`, max CC `63`, max function length `248`).
  Evidence: `radon raw wepppy/nodb/core/climate.py`, `radon cc -s wepppy/nodb/core/climate.py`, and `code-quality-summary.md`.

- (2026-02-20 06:06Z) Observation: The main complexity concentration is inside orchestration and mode-specific branches, not enum/property boilerplate.
  Evidence: `Climate.build` (CC 63), `_build_climate_observed_gridmet_multiple` (CC 31), `parse_inputs` (CC 29), `_export_cli_precip_frequency_csv` (CC 28).

- (2026-02-20 06:06Z) Observation: Public behavior depends on multiple external entrypoints beyond direct NoDb calls.
  Evidence: `wepppy/microservices/rq_engine/climate_routes.py` depends on `Climate.parse_inputs`; `wepppy/rq/project_rq.py` depends on `Climate.build` and `Climate.set_user_defined_cli`; `wepppy/weppcloud/routes/nodb_api/climate_bp.py` depends on station/mode/catalog properties and methods.

- (2026-02-20 06:06Z) Observation: Existing tests protect catalog parsing, lock-race scenarios, upload-side effects, and route payload contracts, but direct coverage of `Climate.build` route-to-builder dispatch and artifact export internals is thin.
  Evidence: `tests/nodb/test_climate_catalog.py`, `tests/nodb/test_build_climate_race_conditions.py`, `tests/nodb/test_user_defined_cli_parquet.py`, `tests/microservices/test_rq_engine_climate_routes.py`, and `tests/weppcloud/routes/test_climate_bp.py`.

- (2026-02-20 06:28Z) Observation: Single-storm inputs are currently blocked by `_assert_supported_climate_mode` before mode-specific parser steps run.
  Evidence: first Milestone 1 parser regression failed with `ValueError: Single-storm climate modes are deprecated and unsupported...`; adjusted regression to assert deprecation guard behavior explicitly.

- (2026-02-20 06:39Z) Observation: Milestone 4/5 validation suites include environment-gated tests that are expected to skip locally.
  Evidence: `tests/climate/test_climate_scaling.py` reported `7 skipped`; `tests/climates/noaa/test_atlas14_download.py` reported `4 skipped` due fixture/env gating.

- (2026-02-20 16:19Z) Observation: Milestone acceptance evidence needs non-skipped deterministic coverage even when environment-gated integration suites skip.
  Evidence: added deterministic regressions in `tests/nodb/test_climate_scaling_service.py` (`annual_monthlies` path, 4 passed) and `tests/nodb/test_climate_artifact_export_service.py` (`atlas14` success/no-coverage/failure, 3 passed).

## Decision Log

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for new entries.

- Decision: Use Option 2 (stable facade + collaborator extraction) and keep `Climate` as the only public controller entrypoint.
  Rationale: This achieves maintainability gains without forcing API or queue contract churn.
  Date/Author: 2026-02-20 06:06Z / Codex

- Decision: Sequence extractions as requested: parsing service, router/orchestrator, mode builders, scaling, artifact export, then station/catalog resolution.
  Rationale: This order isolates highest-coupling logic early and keeps each phase behavior-focused.
  Date/Author: 2026-02-20 06:06Z / Codex

- Decision: Preserve NoDb lock semantics as a hard contract during refactor.
  Rationale: Race/TTL behavior is a known risk area; lock-boundary drift can create regressions that are hard to detect late.
  Date/Author: 2026-02-20 06:06Z / Codex

- Decision: Add targeted regression tests per extraction path before broad gate runs.
  Rationale: Smaller verification loops reduce ambiguity when failures occur and make rollback scoped.
  Date/Author: 2026-02-20 06:06Z / Codex

- Decision: Do not change public API contracts unless explicitly called out and approved.
  Rationale: Route handlers, RQ tasks, and downstream report flows depend on existing `Climate` method/property behavior.
  Date/Author: 2026-02-20 06:06Z / Codex

- Decision: Keep large mode-specific builder implementations on the `Climate` facade for this pass while extracting dispatch/orchestration into collaborator services.
  Rationale: This preserves stable private side-effects while still removing the highest-risk routing complexity from `Climate.build`.
  Date/Author: 2026-02-20 06:33Z / Codex

- Decision: Keep artifact post-build orchestration calling facade methods (`_export_cli_parquet`, `_export_cli_precip_frequency_csv`, `_download_noaa_atlas14_intensity`) from the new collaborator.
  Rationale: This preserves monkeypatch/test hooks and existing call contracts used by upload/build regression tests.
  Date/Author: 2026-02-20 06:39Z / Codex

- Decision: For Milestone 4/5 acceptance, retain environment-gated integration checks but add deterministic non-skipped unit regressions as required evidence.
  Rationale: Integration suites can skip by design in local environments; deterministic tests prove branch behavior and satisfy milestone acceptance expectations.
  Date/Author: 2026-02-20 16:19Z / Codex

## Outcomes & Retrospective

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for new entries.

- (2026-02-20 06:06Z) Outcome: Planning is complete and ready for phased implementation; no production code changes were made in this planning pass.
- (2026-02-20 06:06Z) Retrospective: The risk profile supports an incremental extraction strategy with strict contract and lock-semantics checks at every milestone.
- (2026-02-20 06:20Z) Outcome: Milestone 0 baseline evidence is now embedded in this plan with concrete command results and passing characterization suites.
- (2026-02-20 06:30Z) Outcome: Milestone 1 delivered `ClimateInputParsingService` extraction with parser regressions and no route contract changes.
- (2026-02-20 06:33Z) Outcome: Milestone 2/3 moved build orchestration and mode routing out of `Climate.build` into dedicated collaborators with passing dispatch regressions.
- (2026-02-20 06:39Z) Outcome: Milestone 4/5 moved scaling and artifact exports into collaborators while preserving filenames, trigger/timestamp behavior, and upload-path side effects.
- (2026-02-20 06:41Z) Outcome: Milestone 6 moved station/catalog resolution into a collaborator and preserved route-facing station/catalog responses.
- (2026-02-20 06:58Z) Retrospective: Milestones 1–7 completed with full validation green (`1814 passed`, `27 skipped`) and stable facade contracts; remaining risk is mostly internal collaborator growth rather than cross-module API churn.
- (2026-02-20 16:19Z) Outcome: Post-review hardening added deterministic non-skipped annual-monthly scaling and Atlas14 branch tests and replaced silent cleanup swallow with logged `OSError` handling in the build router.

## Context and Orientation

`wepppy/nodb/core/climate.py` currently mixes six concerns in one controller: input parsing/validation, mode routing, mode-specific data generation, precipitation scaling, climate artifact exports, and station/catalog resolution. It is imported broadly via `wepppy.nodb.core.climate` and directly used by RQ handlers and Flask/FastAPI routes.

Public behavior that must remain stable includes:

1. Facade entrypoints and properties used outside the module:
   `Climate.parse_inputs`, `Climate.build`, `Climate.set_user_defined_cli`, `Climate.find_closest_stations`, `Climate.find_heuristic_stations`, `Climate.catalog_datasets_payload`, `Climate._resolve_catalog_dataset`, and properties like `climate_mode`, `climate_spatialmode`, `catalog_id`, `cli_fn`, `par_fn`, `sub_cli_fns`, and `sub_par_fns`.
2. NoDb mutation and persistence contracts:
   `with self.locked()` usage patterns, `nodb_setter` behavior, `dump_and_unlock` lifecycle, and run-scoped mutation boundaries used by `mutate_root(...)`.
3. Artifact and side-effect contracts:
   generation of `climate.wepp_cli.parquet`, `wepp_cli_pds_mean_metric.csv`, optional NOAA Atlas14 output, timestamp updates via `RedisPrep`, and `TriggerEvents.CLIMATE_BUILD_COMPLETE`.

Current characterization baseline:

1. Hotspot metrics:
   `Climate.build` (~248 lines, CC 63), `_build_climate_observed_gridmet_multiple` (~239 lines, CC 31), `parse_inputs` (~102 lines, CC 29), `_export_cli_precip_frequency_csv` (~199 lines, CC 28).
2. Existing protective tests:
   `tests/nodb/test_climate_catalog.py`, `tests/nodb/test_user_defined_cli_parquet.py`, `tests/nodb/test_build_climate_race_conditions.py`, `tests/nodb/test_lock_race_conditions.py`, `tests/microservices/test_rq_engine_climate_routes.py`, `tests/microservices/test_rq_engine_upload_climate_routes.py`, `tests/weppcloud/routes/test_climate_bp.py`.
3. Known gaps to close during this plan:
   direct build-router dispatch assertions, explicit tests for annual-monthly scaling branch decisions, artifact-export failure contracts, and station resolution behavior under catalog/user-defined variants.

## Plan of Work

The plan is milestone-driven and contract-first. `Climate` remains the public facade at all times; collaborator services are internal implementation details.

1. Milestone 0: Baseline and characterization lock-in.
   Capture baseline complexity and route contract inventory; add missing characterization tests for currently unprotected behavior that must remain stable.
   Acceptance criteria: baseline metrics and coverage matrix are recorded in this ExecPlan, and initial characterization tests pass.
   Validation commands:
       radon raw wepppy/nodb/core/climate.py
       radon cc -s wepppy/nodb/core/climate.py
       wctl run-pytest tests/nodb/test_climate_catalog.py tests/nodb/test_user_defined_cli_parquet.py --maxfail=1
       wctl run-pytest tests/microservices/test_rq_engine_climate_routes.py tests/microservices/test_rq_engine_upload_climate_routes.py tests/weppcloud/routes/test_climate_bp.py --maxfail=1

2. Milestone 1: Extract input parsing/validation service.
   Move parsing and validation internals from `Climate.parse_inputs` to a collaborator (for example `wepppy/nodb/core/climate_input_parser.py`) while keeping `Climate.parse_inputs` as the lock-scoped facade entrypoint.
   Targeted regression tests: catalog-id mode selection, spatial mode validation, year bounds validation, and single-storm deprecation/guard paths.
   Acceptance criteria: `Climate.parse_inputs` signature/behavior remains stable and all parse-related route tests pass.
   Validation commands:
       wctl run-pytest tests/nodb/test_climate_catalog.py --maxfail=1
       wctl run-pytest tests/nodb -k "climate and parse_inputs" --maxfail=1
       wctl run-pytest tests/microservices/test_rq_engine_climate_routes.py --maxfail=1

3. Milestone 2: Extract build router/orchestrator.
   Move mode and spatial routing branches out of `Climate.build` into a dedicated router/orchestrator collaborator (for example `wepppy/nodb/core/climate_build_router.py`). Keep `Climate.build` as the externally called facade method.
   Targeted regression tests: mode dispatch matrix, unsupported-mode failures, spatial-mode compatibility checks, and unchanged timestamp/trigger behavior.
   Acceptance criteria: router dispatch outcomes match pre-refactor behavior for every supported mode/spatial combination.
   Validation commands:
       wctl run-pytest tests/nodb -k "climate and build and not slow" --maxfail=1
       wctl run-pytest tests/microservices/test_rq_engine_climate_routes.py --maxfail=1

4. Milestone 3: Extract mode-specific build services.
   Move mode builders into focused collaborators (for example vanilla/prism/observed/future/depnexrad/mod/user-defined builders). Keep facade call points and output field updates (`cli_fn`, `par_fn`, `monthlies`, sub-file maps) stable.
   Targeted regression tests: one focused test path per mode family, including `Multiple` and `MultipleInterpolated` branches where applicable.
   Acceptance criteria: each mode-specific builder preserves current side effects and output file naming conventions.
   Validation commands:
       wctl run-pytest tests/nodb -k "climate and (vanilla or prism or observed or future or user_defined)" --maxfail=1
       wctl run-pytest tests/weppcloud/routes/test_climate_bp.py --maxfail=1

5. Milestone 4: Extract scaling service.
   Move `_scale_precip`, `_scale_precip_monthlies`, `_spatial_scale_precip`, and annual-monthlies scaling logic into a scaling collaborator while retaining facade APIs and validation behavior.
   Targeted regression tests: scalar scaling, monthly scaling list-length/typing validation, spatial map factor bounds behavior, annual-monthlies reference selection (`prism`, `daymet`, `gridmet`).
   Acceptance criteria: scaled CLI naming and monthlies behavior remain unchanged for both watershed and subcatchment files.
   Validation commands:
       wctl run-pytest tests/climate/test_climate_scaling.py --maxfail=1
       wctl run-pytest tests/nodb -k "climate and scale" --maxfail=1

6. Milestone 5: Extract artifact export service.
   Move `_export_cli_parquet`, `_export_cli_precip_frequency_csv`, and `_download_noaa_atlas14_intensity` into an artifact export collaborator. Keep artifact filenames, failure handling, and optional behavior stable.
   Targeted regression tests: parquet export schema essentials, PDS CSV generation with recurrence bounds, and Atlas14 success/no-coverage/failure handling.
   Acceptance criteria: report-facing artifact contracts remain stable and existing upload regression tests still pass.
   Validation commands:
       wctl run-pytest tests/nodb/test_user_defined_cli_parquet.py --maxfail=1
       wctl run-pytest tests/climates/noaa/test_atlas14_download.py --maxfail=1
       wctl run-pytest tests/nodb -k "climate and parquet" --maxfail=1

7. Milestone 6: Extract station/catalog resolution service.
   Move catalog and station resolution logic (`available_catalog_datasets`, `_resolve_catalog_dataset`, `climatestation_meta`, closest/heuristic station selection) into a collaborator and keep facade properties/methods stable.
   Targeted regression tests: catalog visibility filters, catalog-id resolution, station selection modes, and `climatestation_meta` behavior for user-defined uploads.
   Acceptance criteria: route payloads and UI-facing station/catalog behaviors remain unchanged.
   Validation commands:
       wctl run-pytest tests/nodb/test_climate_catalog.py --maxfail=1
       wctl run-pytest tests/weppcloud/routes/test_climate_bp.py --maxfail=1

8. Milestone 7: Final facade cleanup and closeout.
   Reduce `climate.py` to a maintainable facade plus enums/contracts; ensure collaborators are wired, documented, and covered by targeted tests; complete full validation gates.
   Acceptance criteria: all milestone validations pass and full pre-handoff test gate passes.
   Validation commands:
       wctl run-pytest tests/nodb --maxfail=1
       wctl run-pytest tests/microservices/test_rq_engine_climate_routes.py tests/microservices/test_rq_engine_upload_climate_routes.py --maxfail=1
       wctl run-pytest tests/weppcloud/routes/test_climate_bp.py --maxfail=1
       wctl run-pytest tests --maxfail=1

## Concrete Steps

Run all commands from `/workdir/wepppy`.

1. Establish baseline metrics and execute characterization tests from Milestone 0.
2. Implement Milestones 1 through 6 in order, running each milestone’s targeted validation commands before proceeding.
3. Keep this living plan updated after each milestone with UTC timestamped updates in `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective`.
4. Execute Milestone 7 full validation gates, then summarize deltas, residual risks, and completion status in this ExecPlan.

## Validation and Acceptance

Overall acceptance requires all conditions below.

1. Public `Climate` facade behavior remains stable for external call sites in routes, RQ jobs, and tests.
2. NoDb contracts remain intact: lock semantics, mutation boundaries, and persistence lifecycle do not regress.
3. Each extraction milestone includes targeted regression coverage for the exact path moved or fixed.
4. Required validation gates pass, including the pre-handoff command:
       wctl run-pytest tests --maxfail=1
5. Complexity in `wepppy/nodb/core/climate.py` improves materially relative to baseline without introducing speculative abstractions.

## Risk and Rollback

Highest-risk behavior areas and containment strategy:

1. Locking/concurrency risk (`parse_inputs`, build flows, race-sensitive routes).
   Containment: keep lock acquisition boundaries at existing facade entrypoints; add/retain race-focused tests before and after each extraction.
   Rollback: revert only the last extraction milestone commit and rerun the same focused lock tests.
2. Mode routing risk (`Climate.build` dispatch matrix).
   Containment: characterize current dispatch behavior before extraction; add matrix-style routing regression tests.
   Rollback: restore prior router mapping and builder delegation in one commit; keep collaborator modules unused until corrected.
3. Artifact generation risk (parquet, PDS CSV, Atlas14 download paths).
   Containment: extract artifact logic as a separate milestone with deterministic fixture tests and explicit error-path assertions.
   Rollback: temporarily rewire facade methods to legacy in-class artifact implementations while collaborator defects are fixed.
4. Scaling behavior risk (scalar/monthly/spatial/annual-monthly transformations).
   Containment: keep transformation function signatures and output filenames stable; run climate scaling tests at every related edit.
   Rollback: revert scaling collaborator wiring independently of mode-builder and parser milestones.

## Idempotence and Recovery

This plan is intentionally incremental and replayable. Each milestone is independently testable and can be retried without requiring full rollback.

If a milestone fails validation:

1. Revert only that milestone’s extraction diff.
2. Re-run the milestone’s focused validation commands.
3. Update this plan’s living sections with the failure cause and revised decision.

Avoid multi-milestone refactor bursts without passing the current milestone tests first.

## Out of Scope

1. Public API contract changes for `Climate` facade methods/properties unless explicitly called out and approved.
2. Speculative abstractions for unsupported climate modes or hypothetical data providers.
3. Queue wiring changes outside climate behavior preservation scope.
4. Unrelated refactors in other NoDb controllers.

## Artifacts and Notes

Baseline artifacts to keep updated as work progresses:

1. Complexity snapshots before/after extraction:
       radon raw wepppy/nodb/core/climate.py
       radon cc -s wepppy/nodb/core/climate.py
2. Validation transcripts for each milestone command set.
3. Updated contract notes when behavior is intentionally changed (if any), including exact file/route impact.

Initial baseline captured during planning:

1. `wepppy/nodb/core/climate.py` raw metrics: `LOC 3578`, `SLOC 2708`, `LLOC 2285`.
2. Highest-risk methods by CC: `Climate.build (63)`, `_build_climate_observed_gridmet_multiple (31)`, `Climate.parse_inputs (29)`, `_export_cli_precip_frequency_csv (28)`.

Milestone 0 evidence capture (2026-02-20 06:20Z):

1. Baseline complexity snapshots:
       $ radon raw wepppy/nodb/core/climate.py
       wepppy/nodb/core/climate.py
           LOC: 3578
           LLOC: 2285
           SLOC: 2708

       $ radon cc -s wepppy/nodb/core/climate.py
       Climate.build - F (63)
       Climate._build_climate_observed_gridmet_multiple - E (31)
       Climate.parse_inputs - D (29)
       Climate._export_cli_precip_frequency_csv - D (28)

2. Characterization suite 1:
       $ wctl run-pytest tests/nodb/test_climate_catalog.py tests/nodb/test_user_defined_cli_parquet.py --maxfail=1
       collected 7 items
       tests/nodb/test_climate_catalog.py .....                                 [ 71%]
       tests/nodb/test_user_defined_cli_parquet.py ..                           [100%]
       7 passed

3. Characterization suite 2:
       $ wctl run-pytest tests/microservices/test_rq_engine_climate_routes.py tests/microservices/test_rq_engine_upload_climate_routes.py tests/weppcloud/routes/test_climate_bp.py --maxfail=1
       collected 13 items
       tests/microservices/test_rq_engine_climate_routes.py ...                 [ 23%]
       tests/microservices/test_rq_engine_upload_climate_routes.py ..           [ 38%]
       tests/weppcloud/routes/test_climate_bp.py ........                       [100%]
       13 passed

4. Post-refactor complexity snapshot (Milestone 7):
       $ radon raw wepppy/nodb/core/climate.py
       LOC: 2745
       LLOC: 1694
       SLOC: 2031

       $ radon cc -s wepppy/nodb/core/climate.py
       Climate._build_climate_observed_gridmet_multiple - E (31)
       _build_user_defined_station_meta_from_cli - D (27)
       Climate.set_single_storm_pars - C (19)

Milestones 1-7 evidence capture (2026-02-20 06:58Z):

1. Milestone 1 validation:
       $ wctl run-pytest tests/nodb/test_climate_catalog.py --maxfail=1
       5 passed
       $ wctl run-pytest tests/nodb -k "climate and parse_inputs" --maxfail=1
       9 passed
       $ wctl run-pytest tests/microservices/test_rq_engine_climate_routes.py --maxfail=1
       3 passed

2. Milestone 2 validation:
       $ wctl run-pytest tests/nodb -k "climate and build and not slow" --maxfail=1
       11 passed
       $ wctl run-pytest tests/microservices/test_rq_engine_climate_routes.py --maxfail=1
       3 passed

3. Milestone 3 validation:
       $ wctl run-pytest tests/nodb -k "climate and (vanilla or prism or observed or future or user_defined)" --maxfail=1
       3 passed
       $ wctl run-pytest tests/weppcloud/routes/test_climate_bp.py --maxfail=1
       8 passed

4. Milestone 4 validation:
       $ wctl run-pytest tests/climate/test_climate_scaling.py --maxfail=1
       7 skipped
       $ wctl run-pytest tests/nodb -k "climate and scale" --maxfail=1
       2 passed
       $ wctl run-pytest tests/nodb/test_climate_scaling_service.py -k "annual_monthlies" --maxfail=1
       4 passed

5. Milestone 5 validation:
       $ wctl run-pytest tests/nodb/test_user_defined_cli_parquet.py --maxfail=1
       2 passed
       $ wctl run-pytest tests/climates/noaa/test_atlas14_download.py --maxfail=1
       4 skipped
       $ wctl run-pytest tests/nodb -k "climate and parquet" --maxfail=1
       1 passed
       $ wctl run-pytest tests/nodb/test_climate_artifact_export_service.py -k "atlas14_intensity and (success or no_coverage or download_failure)" --maxfail=1
       3 passed

6. Milestone 6 validation:
       $ wctl run-pytest tests/nodb/test_climate_catalog.py --maxfail=1
       5 passed
       $ wctl run-pytest tests/weppcloud/routes/test_climate_bp.py --maxfail=1
       8 passed

7. Milestone 7 validation:
       $ wctl run-pytest tests/nodb --maxfail=1
       315 passed, 3 skipped
       $ wctl run-pytest tests/microservices/test_rq_engine_climate_routes.py tests/microservices/test_rq_engine_upload_climate_routes.py --maxfail=1
       5 passed
       $ wctl run-pytest tests/weppcloud/routes/test_climate_bp.py --maxfail=1
       8 passed
       $ wctl run-pytest tests --maxfail=1
       1814 passed, 27 skipped

## Interfaces and Dependencies

The `Climate` facade in `wepppy/nodb/core/climate.py` remains authoritative. Collaborators are internal modules under `wepppy/nodb/core/` and should be explicitly typed and testable in isolation.

Target collaborator interfaces at end state:

1. `wepppy/nodb/core/climate_input_parser.py`
   `class ClimateInputParsingService:`
   `def parse_inputs(self, climate: "Climate", kwds: dict[str, object]) -> None`
2. `wepppy/nodb/core/climate_build_router.py`
   `class ClimateBuildRouter:`
   `def build(self, climate: "Climate", *, verbose: bool = False, attrs: dict[str, object] | None = None) -> None`
3. `wepppy/nodb/core/climate_mode_build_services.py`
   `class ClimateModeBuildServices:`
   mode-specific builder methods currently on facade.
4. `wepppy/nodb/core/climate_scaling_service.py`
   `class ClimateScalingService:`
   scalar/monthly/spatial/annual-monthly scaling entrypoints.
5. `wepppy/nodb/core/climate_artifact_export_service.py`
   `class ClimateArtifactExportService:`
   parquet/PDS CSV/Atlas14 export methods.
6. `wepppy/nodb/core/climate_station_catalog_service.py`
   `class ClimateStationCatalogService:`
   station search and catalog resolution methods.

No silent fallback wrappers should be introduced. Failures should remain explicit and contract-compliant.

Revision Note (2026-02-20 06:06Z, Codex): Created this ad hoc ExecPlan for Option-2 `Climate` facade refactor, including baseline characterization, extraction milestones, validation gates, risk/rollback strategy, and out-of-scope constraints.
Revision Note (2026-02-20 06:20Z, Codex): Seeded Milestone 0 evidence with concrete baseline command transcripts and marked Milestone 0 complete in `Progress`.
Revision Note (2026-02-20 06:58Z, Codex): Completed Milestones 1-7 with collaborator extraction, targeted regression coverage, full validation transcripts, and final closeout updates.
Revision Note (2026-02-20 16:19Z, Codex): Addressed review findings by adding deterministic non-skipped Milestone 4/5 evidence and tightening router cleanup exception handling.
