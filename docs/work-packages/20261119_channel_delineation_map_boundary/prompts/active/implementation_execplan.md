# Enforce configured map boundaries for channel delineation

Keep Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective current as specified in `docs/prompt_templates/codex_exec_plans.md`.

## Purpose

A user who selects an extent that fails the configured policy should get immediate feedback and be able to submit a new extent. The project selects intersection, full inclusion, or no check. Users of configurations with the boundary unset continue through ordinary channel admission without a boundary check.

## Progress

- [x] 2026-11-19 16:01 UTC. Scaffolded the package and traced the main admission and execution paths.
- [ ] Audit supported boundary assets and channel entry points and complete the canonical contract checkpoint.
- [ ] Implement focused validation and test all affected paths.
- [ ] Read back real artifacts and complete correctness, security and regression reviews.

## Surprises & Discoveries

`Ron.boundary` is initialized from `config_get_path('map', 'boundary')` in `wepppy/nodb/core/ron.py`. The run-page bootstrap treats it as a map overlay URL. Tracked Tahoe, Coeur d'Alene, Portland and Seattle boundaries are polygon feature collections. Shipped settings use both `static/...` and `/static/...`. Coeur d'Alene declares EPSG:4269 and the other tracked polygon assets declare CRS84. Audit coordinate reference systems before choosing normalization.

`wepppy/nodb/core/map_object.py` stores `Map.extent` in longitude/latitude decimal degrees ordered west, south, east, north. The older RQ docstring that describes projected coordinates should be checked against the actual data flow.

## Decision Log

The operator requested intersection with the effective config boundary and unrestricted geographic admission when the setting is unset. The operator then requested an opt-in full-inclusion policy as well. Use `intersects` by default for a configured boundary, `covers` for full inclusion, and `none` to bypass the test. Intersection uses inclusive edge and corner contact. Coverage allows the extent's own edge on the polygon edge. Accepted extents are used as submitted. The operator confirmed that `salvage_logging` is deprecated. The package focuses its asset audit on supported presets.

## Outcomes & Retrospective

The package and tracker are ready. Source discovery identified the candidate admission path, channel consumers and the initial asset audit. Contract review and runtime evidence remain implementation milestones.

## Context and orientation

In `wepppy/microservices/rq_engine/watershed_routes.py`, `_parse_map_change` decodes the request and `fetch_dem_and_build_channels` authorizes the run, checks config identity and preflights mutation. Modes 0 and 1 use `map_bounds`, mode 2 uses `Map.from_payload(...).extent`, and mode 3 uses a previously uploaded DEM and its persisted `Ron.map` for actual channel work. The route saves parameters for batch/base projects or sends work to `fetch_dem_and_build_channels_rq` in `wepppy/rq/project_rq.py`. That job normally queues DEM fetch before channel build. In Upload DEM mode it queues channel build directly.

`wepppy/nodb/core/watershed_mixins.py::WatershedOperationsMixin.build_channels` is the channel build method used by the normal worker. `wepppy/nodb/batch_runner.py` and the task chain in `wepppy/rq/project_rq.py` also build channels directly. Trace their effective configs and map extents, including any per-run batch extent established after base-project settings are saved.

## Milestone 1. Define the contract

Read the applicable subsystem guides. Audit configured references, deployment asset locations, preset support and legacy run hydration. Confirm which runtime config reader and map extent correspond to the actual build. Define the supported path forms and geometry types, coordinate normalization, intersection semantics, retry behavior, the actionable spatial error and a separate configuration error. Cover absent, empty, populated, legacy and malformed states independently of extent modes. Record the rule and rationale in the relevant canonical schema and controller/user guidance. Complete the checkpoint in `docs/standards/contract-first-change-standard.md` before runtime edits.

## Milestone 2. Implement the check

Use the effective project config with the existing unset normalization. Resolve configured assets within supported server-owned locations using the existing geospatial stack. Evaluate the configured intersection or coverage predicate on compatible coordinates, including holes and multiple polygon features. Reuse a small shared check where needed for actual channel-build paths. In the ordinary request, return an actionable disjoint-extent error after decoding and establishing the effective extent and before saving parameters, invalidating readiness or enqueueing work. Validate before mutation on any confirmed direct path that can otherwise bypass admission. Use existing response and status handling.

## Milestone 3. Verify the workflow

From the implementation worktree, run `wctl run-pytest tests/microservices/test_rq_engine_watershed_routes.py` plus focused worker and NoDb tests, then `wctl run-pytest tests --maxfail=1`. Run frontend lint and tests if frontend code changes. Validate in disposable representative projects with overlapping, fully covered, disjoint, explicit opt-out and unset-boundary cases. Confirm Upload DEM uses the validated footprint even with misleading request bounds. Read the channel artifact and map/report outcome for accepted runs and verify prior state and artifacts survive a rejected resubmission. Retain the exact revision, runtime identity, config, extent, job tree and artifact readbacks under the package. Complete independent reviews using the correctness and security templates.

## Idempotence and recovery

Repeat acceptance with disposable runs and fresh job identities. A rejected request must permit immediate resubmission with a valid extent. If a supported boundary asset is unavailable, report the affected configuration and restore the expected asset through its owning deployment process.

## Interfaces and dependencies

The existing build-channels request and the effective run config carry the inputs. Reuse existing map extent types, server-side geometry tooling and the RQ error envelope. Keep the shared check usable from admission and any direct build consumer that needs it. Record the final interface and concrete test commands as the implementation proceeds.
