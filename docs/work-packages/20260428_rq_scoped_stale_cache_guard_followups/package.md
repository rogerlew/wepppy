# RQ Scoped Stale NoDb Cache Guard Follow-Ups

**Status**: Complete (2026-04-28)
**Timezone**: UTC

## Overview

This package follows the completed `build_soils_rq` stale-cache guard package and broadens the same deterministic pattern to other RQ mutation paths that hydrate a NoDb controller and then mutate/persist it. The goal is to prevent stale signature reuse in adjacent worker jobs when a stale Redis-cached `.nodb` payload would otherwise be reused immediately before write.

## Objectives

- Conform qualifying RQ mutation paths to the canonical scoped-cache guard contract.
- Add scoped `clear_nodb_file_cache(runid, pup_relpath="<controller>.nodb")` guards to confirmed RQ mutation paths before mutable controller hydration.
- Preserve existing lock-root, status, timestamp, enqueue, and archive-root rejection behavior.
- Add targeted regression coverage for guard ordering and scope on each grouped path.
- Keep the rollout evidence-driven and avoid a broad cache architecture rewrite.

## Canonical Contract Reference

This package implements the repository standard:

- `docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md`

Classification for this package: contract conformance rollout, not incident hardening.

## Candidate Call Sites

These candidates were identified from a scan of `wepppy/rq/*` on 2026-04-28 after closing `build_soils_rq` guard work.

### Priority 0: Top-level Project RQ Mutation Paths

These are direct project preparation or model-build paths with the same shape as the fixed soils path: hydrate a top-level NoDb controller from `getInstance(...)`, perform a mutable operation that is expected to persist state, and currently have no scoped cache guard.

| File | Function | Guard scope | Evidence |
|------|----------|-------------|----------|
| `wepppy/rq/project_rq.py` | `init_sbs_map_rq` | conditional `disturbed.nodb` / `baer.nodb` | `Ron.getInstance(wd)` calls `ron.init_sbs_map(...)`, which triggers locked SBS validation in mod controllers. |
| `wepppy/rq/project_rq.py` | `fetch_dem_rq` | `ron.nodb` | `Ron.getInstance(wd)` followed by `set_map(...)` / `set_map_object(...)` and `fetch_dem()`. |
| `wepppy/rq/project_rq.py` | `fetch_dem_and_build_channels_rq` | `watershed.nodb` | `Watershed.getInstance(get_wd(runid))` followed by `set_extent_mode` and `map_bounds_text` updates before enqueue. |
| `wepppy/rq/project_rq.py` | `build_channels_rq` | `watershed.nodb` (conditional `topaz.nodb`) | `Watershed.getInstance(wd)` followed by WBT option mutations and `build_channels(...)` inside the watershed lock callback; TOPAZ-backed paths may persist `topaz.nodb` through mixins. |
| `wepppy/rq/project_rq.py` | `set_outlet_rq` | `watershed.nodb` (conditional `topaz.nodb`) | `Watershed.getInstance(wd).set_outlet(...)` inside the watershed lock callback; TOPAZ-backed paths may persist `topaz.nodb` through mixins. |
| `wepppy/rq/project_rq.py` | `build_subcatchments_rq` | `watershed.nodb` (conditional `topaz.nodb`) | `Watershed.getInstance(wd)` followed by optional settings mutations and `build_subcatchments()`; TOPAZ-backed paths may persist `topaz.nodb` through mixins. |
| `wepppy/rq/project_rq.py` | `abstract_watershed_rq` | `watershed.nodb` | `Watershed.getInstance(wd)` followed by `abstract_watershed()` and centroid repair checks. |
| `wepppy/rq/project_rq.py` | `build_landuse_rq` | `landuse.nodb` | `Landuse.getInstance(wd).build()` inside the landuse lock callback. |
| `wepppy/rq/project_rq.py` | `build_climate_rq` | `climate.nodb` | `Climate.getInstance(wd)` followed by payload replay and `build()` inside the climate lock callback. |
| `wepppy/rq/project_rq.py` | `upload_cli_rq` | `climate.nodb` | `Climate.getInstance(wd).set_user_defined_cli(...)` inside the climate lock callback. |

### Priority 1: Top-level Mod Build/Run Paths

These paths are similar but touch mod-specific NoDb controllers. They should be guarded after confirming each mutating method persists its own `.nodb` state and after choosing whether related prerequisite controllers are read-only inputs or mutation participants.

| File | Function | Guard scope | Evidence |
|------|----------|-------------|----------|
| `wepppy/rq/project_rq.py` | `build_rangeland_cover_rq` | `rangeland_cover.nodb` | `RangelandCover.getInstance(wd)` followed by `build(...)`. |
| `wepppy/rq/project_rq.py` | `build_treatments_rq` | `landuse.nodb` + `soils.nodb` | `build_treatments()` mutates landuse/soils state through those controller lock/write paths under landuse/soils root locks. |
| `wepppy/rq/project_rq.py` | `run_ash_rq` | `ash.nodb` | `Ash.getInstance(wd)` followed by `run_ash(...)`. |
| `wepppy/rq/project_rq.py` | `run_debris_flow_rq` | `debris_flow.nodb` | `DebrisFlow.getInstance(wd)` followed by `run_debris_flow(...)`. |
| `wepppy/rq/project_rq.py` | `fetch_and_analyze_rap_ts_rq` | `rap_ts.nodb` | `RAP_TS.getInstance(wd)` followed by `acquire_rasters(...)` and `analyze()`. |
| `wepppy/rq/project_rq.py` | `fetch_and_analyze_openet_ts_rq` | `openet_ts.nodb` | `OpenET_TS.getInstance(wd)` followed by `acquire_timeseries(...)` and `analyze()`. |
| `wepppy/rq/project_rq.py` | `fetch_and_align_polaris_rq` | `polaris.nodb` | `Polaris.getInstance(wd)` followed by `acquire_and_align(...)`. |
| `wepppy/rq/project_rq.py` | `build_rusle_rq` | `rusle.nodb` | `Rusle.getInstance(wd)` followed by `build(...)`. |

### Priority 2: Cross-module and Orchestration Paths

These should be audited and guarded where the mutation boundary is clear. They may need separate tests or a split package if the implementation gets large.

| File | Function | Initial guard scope | Reason to investigate |
|------|----------|---------------------|-----------------------|
| `wepppy/rq/wepp_rq.py` | `bootstrap_enable_rq`, `run_wepp_rq`, `run_wepp_watershed_rq`, `prep_wepp_watershed_rq` | `wepp.nodb` | Orchestrator paths call mutating `Wepp` methods such as `init_bootstrap()`, `ensure_bootstrap_main()`, `clean()`, and `_check_and_set_*` before enqueueing stage jobs. |
| `wepppy/rq/swat_rq.py` | `_build_swat_inputs_rq`, `_run_swat_rq`, `run_swat_interchange_rq` | `swat.nodb` | SWAT worker paths hydrate `Swat` and call build/run/interchange methods that can persist SWAT NoDb state under lock. |
| `wepppy/rq/omni_rq.py` | `run_omni_scenario_rq`, `run_omni_contrast_rq`, `run_omni_scenarios_rq`, `run_omni_contrasts_rq`, `delete_omni_contrasts_rq` | `omni.nodb` plus PUP scopes where applicable | Omni already has cache/lock helpers for clone paths; execution/deletion paths should be audited before adding duplicate guards. |
| `wepppy/rq/path_ce_rq.py` | `run_path_cost_effective_rq` | `path_ce.nodb` and `omni.nodb` | The workflow mutates PATH status and provisions/runs Omni scenarios. |
| `wepppy/rq/roads_rq.py` | `run_roads_prepare_rq`, `run_roads_rq` | `roads.nodb` | Roads worker paths sync enabled state and run mutable prepare/run methods behind a runtime lock. |
| `wepppy/rq/geneva_rq.py` | `run_geneva_prepare_hrus_rq`, `run_geneva_build_frequency_panel_rq`, `run_geneva_run_batch_rq` | `geneva.nodb` | Geneva worker paths mark job start/finish and run mutable module methods. |
| `wepppy/rq/project_rq_fork.py` | `prepare_fork_run(..., undisturbify=True)` | new-run `ron.nodb`, `disturbed.nodb`, `landuse.nodb`, `soils.nodb` | Forked `.nodb` files are copied and rewritten before undisturbify mutates them; implementation needs a `clear_nodb_file_cache` injection that can target `new_runid`. |

### Not Primary Candidates

- `land_and_soil_rq.py` builds a fresh job-id workspace under `/wc1/land_and_soil_rq` and does not operate on a normal runid-backed cache key. It should be left out unless evidence shows reused job workspaces.
- Full-cache clear operations in delete/archive/restore and batch clone flows already clear broad cache as part of moving or deleting run trees. This package should not replace those with scoped guards.
- Read-only stage/post-processing jobs that hydrate controllers only to read paths or settings should not receive guards unless method-level inspection proves they persist NoDb state.

## Scope

### Included

- Guard implementation for Priority 0 call sites.
- Method-level audit and, where confirmed, guarded implementation for Priority 1 call sites.
- A written disposition for Priority 2 call sites: guarded in this package, split into a follow-up package, or explicitly deferred with rationale.
- Targeted tests for guard ordering and scoped `pup_relpath` usage.
- Package lifecycle docs and `PROJECT_TRACKER.md` updates.

### Explicitly Out of Scope

- Reworking NoDb cache internals in `wepppy/nodb/base.py`.
- Replacing existing broad cache clears for delete/archive/restore or batch clone flows.
- Adding silent fallback wrappers around missing Redis cache dependencies.
- Changing queue topology, dependency edges, status messages, or timestamp semantics except where tests prove an existing behavior must be preserved.

## Stakeholders

- **Primary**: RQ operators, NoDb maintainers, project-prep maintainers.
- **Reviewers**: RQ/NoDb maintainers.
- **Security Reviewer**: Not required by default; no new endpoint, auth, or privilege surface expected.
- **Informed**: Incident responders tracking stale NoDb write recurrence.

## Success Criteria

- [x] Priority 0 call sites have scoped cache guards before mutable controller hydration.
- [x] Priority 1 call sites have implementation or explicit defer/split disposition backed by method-level audit.
- [x] Existing lock-root, archive-root rejection, status, timestamp, and enqueue behavior remains unchanged.
- [x] Targeted regression tests pass for guarded paths.
- [x] Package docs and `PROJECT_TRACKER.md` are synchronized and lint-clean.

## Closure Summary

Closed on 2026-04-28 with scoped cache guards implemented in `wepppy/rq/project_rq.py` for all Priority 0 paths and the simple, testable Priority 1 `project_rq.py` mod paths. Guards use exact per-file `pup_relpath` values and remain inside existing directory-root lock callbacks where those callbacks already enforced archive/root preconditions.

Targeted regression coverage in `tests/rq/test_project_rq_mutation_guards.py` now asserts exact scopes, guard-before-hydration ordering, archive-root rejection before cache clearing, and unchanged representative enqueue/status/timestamp behavior. Non-`project_rq.py` Priority 2 module families were audited enough to confirm they are real candidates but split/deferred because each needs module-specific fixtures for queue topology, single-flight locks, clone/deletion semantics, or new-runid cache keys.

Validation evidence at closure:

- `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py --maxfail=1` -> `44 passed, 15 warnings`.
- Additional non-`project_rq.py` pytest commands: not required; no non-`project_rq.py` implementation files were touched.
- `wctl doc-lint --path docs/work-packages/20260428_rq_scoped_stale_cache_guard_followups --path PROJECT_TRACKER.md` -> passed.
- `git diff --check` -> passed.

## Implementation and Disposition Matrix

| Priority | Candidate | Disposition | Guard scope / rationale |
|----------|-----------|-------------|-------------------------|
| 0 | `project_rq.py::init_sbs_map_rq` | Implemented | Clears conditional `disturbed.nodb` or `baer.nodb` before SBS mod hydration through `ron.disturbed`. |
| 0 | `project_rq.py::fetch_dem_rq` | Implemented | Clears `ron.nodb` before `Ron.getInstance(wd)` and DEM/map mutation. |
| 0 | `project_rq.py::fetch_dem_and_build_channels_rq` | Implemented | Clears `watershed.nodb` before extent metadata hydration/mutation and preserves dependent enqueue metadata. |
| 0 | `project_rq.py::build_channels_rq`, `set_outlet_rq`, `build_subcatchments_rq` | Implemented | Clears `watershed.nodb` inside the watershed root lock; clears conditional `topaz.nodb` after current watershed hydration and before TOPAZ-backed mutable calls. |
| 0 | `project_rq.py::abstract_watershed_rq` | Implemented | Clears `watershed.nodb` inside the watershed root lock before abstraction hydration. |
| 0 | `project_rq.py::build_landuse_rq` | Implemented | Clears `landuse.nodb` inside the landuse root lock before landuse hydration/build. |
| 0 | `project_rq.py::build_climate_rq`, `upload_cli_rq` | Implemented | Clears `climate.nodb` inside the climate root lock before climate hydration/build or CLI mutation. |
| 1 | `build_rangeland_cover_rq`, `run_ash_rq`, `run_debris_flow_rq`, `fetch_and_analyze_rap_ts_rq`, `fetch_and_analyze_openet_ts_rq`, `fetch_and_align_polaris_rq`, `build_rusle_rq` | Implemented | Clears exact mod `.nodb` file before the mutable mod controller hydration. Root-checked ash/debris guards run after supporting root checks. |
| 1 | `build_treatments_rq` | Implemented | Clears `landuse.nodb` and `soils.nodb` as separate scoped calls inside the landuse/soils roots lock before treatment build hydrates and mutates those controllers. |
| 2 | `wepp_rq.py` WEPP orchestration paths | Split/deferred | Real `wepp.nodb` mutation candidates, but queue pipeline, bootstrap, mixed-NoDir recovery, and enqueue metadata need a dedicated package and tests. |
| 2 | `swat_rq.py` SWAT paths | Split/deferred | Real `swat.nodb` mutation candidates, but build/run/interchange and bootstrap autocommit side effects need module-specific tests. |
| 2 | `omni_rq.py` Omni scenario/contrast paths | Split/deferred | Real `omni.nodb` mutation candidates, but existing clone cache helpers, concurrency branches, and deletion semantics need dedicated coverage. |
| 2 | `path_ce_rq.py` PATH/Omni workflow | Split/deferred | Mutates PATH and Omni state together; needs combined PATH/Omni fixtures and status/progress assertions. |
| 2 | `roads_rq.py` Roads prepare/run paths | Split/deferred | Real `roads.nodb` candidates, but single-flight runtime locks and enabled-state sync need roads-specific tests. |
| 2 | `geneva_rq.py` Geneva paths | Split/deferred | Real `geneva.nodb` candidates, but config-specific controller creation and best-effort state-lock retries need Geneva-specific tests. |
| 2 | `project_rq_fork.py::prepare_fork_run(..., undisturbify=True)` | Split/deferred | New-runid cache clearing must target `new_runid`/`new_wd`; implement with a helper injection and fork-specific tests in a follow-up. |

## Dependencies

### Prerequisites

- Canonical contract: `docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md`.
- Completed package: [20260428_build_soils_rq_stale_cache_guard](../20260428_build_soils_rq_stale_cache_guard/package.md).
- Existing scoped `clear_nodb_file_cache` support in `wepppy/nodb/base.py`.
- Existing mutation guard tests in `tests/rq/test_project_rq_mutation_guards.py`.

### Blocks

- None currently identified.

## Related Packages

- **Depends on:** [20260428_build_soils_rq_stale_cache_guard](../20260428_build_soils_rq_stale_cache_guard/package.md)
- **Related:** [20260424_rq_worker_nodb_cache_hardening](../20260424_rq_worker_nodb_cache_hardening/package.md)
- **Related:** [20260425_nodb_atomicity_observability_followups_a](../20260425_nodb_atomicity_observability_followups_a/package.md)

## Timeline Estimate

- **Expected duration**: 1-3 focused sessions depending on Priority 1/2 disposition.
- **Complexity**: Medium.
- **Risk level**: Medium (touches multiple production RQ mutation paths).

## Security Impact and Review Gate

- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: internal worker reliability hardening in existing authenticated/queued paths with no new public API surface.
- **Security review artifact**: `N/A`

## Contract Signals

- **Baseline risk signature**:
  - Prior confirmed stale-write mismatch on `build_soils_rq` (`NoDbStaleWriteError`).
- **Conformance signals**:
  - Qualifying mutation paths use scoped guard placement defined by `docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md`.
  - Regression tests fail when guard scope or ordering drifts.
- **Drift signals**:
  - Guard is added before archive/root precondition checks.
  - Run-wide cache clear appears where scoped guard is required.
  - Read-only paths receive unnecessary guard churn.

## Deliverables

- Guard implementation for prioritized RQ mutation paths.
- Regression coverage for guard ordering and scope.
- Priority 2 disposition note if not fully implemented in this package.
- Updated package lifecycle docs and tracker evidence.

## Follow-up Work

- Split Priority 2 module families into dedicated packages if the audit shows behavior-specific testing is too large for this package.

## Kickoff Prompt

- Execution prompt: `docs/work-packages/20260428_rq_scoped_stale_cache_guard_followups/prompts/active/execute_rq_scoped_stale_cache_guard_followups_prompt.md`
- Completed ExecPlan: `docs/work-packages/20260428_rq_scoped_stale_cache_guard_followups/prompts/completed/rq_scoped_stale_cache_guard_followups_execplan.md`
