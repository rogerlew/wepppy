# RQ Scoped Stale NoDb Cache Guard Follow-Ups

**Status**: Open (2026-04-28)
**Timezone**: UTC

## Overview

This package follows the completed `build_soils_rq` stale-cache guard package and broadens the same deterministic mitigation to other RQ mutation paths that hydrate a NoDb controller and then mutate/persist it. The goal is to prevent the same `NoDbStaleWriteError` class from recurring in adjacent worker jobs because a stale Redis-cached `.nodb` payload was reused immediately before a write.

## Objectives

- Add scoped `clear_nodb_file_cache(runid, pup_relpath="<controller>.nodb")` guards to confirmed RQ mutation paths before mutable controller hydration.
- Preserve existing lock-root, status, timestamp, enqueue, and archive-root rejection behavior.
- Add targeted regression coverage for guard ordering and scope on each grouped path.
- Keep the rollout evidence-driven and avoid a broad cache architecture rewrite.

## Candidate Call Sites

These candidates were identified from a scan of `wepppy/rq/*` on 2026-04-28 after closing `build_soils_rq` guard work.

### Priority 0: Top-level Project RQ Mutation Paths

These are direct project preparation or model-build paths with the same shape as the fixed soils path: hydrate a top-level NoDb controller from `getInstance(...)`, perform a mutable operation that is expected to persist state, and currently have no scoped cache guard.

| File | Function | Guard scope | Evidence |
|------|----------|-------------|----------|
| `wepppy/rq/project_rq.py` | `set_run_readonly_rq` | `ron.nodb` | `Ron.getInstance(wd)` followed by `ron.readonly = ...`. |
| `wepppy/rq/project_rq.py` | `fetch_dem_rq` | `ron.nodb` | `Ron.getInstance(wd)` followed by `set_map(...)` / `set_map_object(...)` and `fetch_dem()`. |
| `wepppy/rq/project_rq.py` | `fetch_dem_and_build_channels_rq` | `watershed.nodb` | `Watershed.getInstance(get_wd(runid))` followed by `set_extent_mode` and `map_bounds_text` updates before enqueue. |
| `wepppy/rq/project_rq.py` | `build_channels_rq` | `watershed.nodb` | `Watershed.getInstance(wd)` followed by WBT option mutations and `build_channels(...)` inside the watershed lock callback. |
| `wepppy/rq/project_rq.py` | `set_outlet_rq` | `watershed.nodb` | `Watershed.getInstance(wd).set_outlet(...)` inside the watershed lock callback. |
| `wepppy/rq/project_rq.py` | `build_subcatchments_rq` | `watershed.nodb` | `Watershed.getInstance(wd)` followed by optional settings mutations and `build_subcatchments()`. |
| `wepppy/rq/project_rq.py` | `abstract_watershed_rq` | `watershed.nodb` | `Watershed.getInstance(wd)` followed by `abstract_watershed()` and centroid repair checks. |
| `wepppy/rq/project_rq.py` | `build_landuse_rq` | `landuse.nodb` | `Landuse.getInstance(wd).build()` inside the landuse lock callback. |
| `wepppy/rq/project_rq.py` | `build_climate_rq` | `climate.nodb` | `Climate.getInstance(wd)` followed by payload replay and `build()` inside the climate lock callback. |
| `wepppy/rq/project_rq.py` | `upload_cli_rq` | `climate.nodb` | `Climate.getInstance(wd).set_user_defined_cli(...)` inside the climate lock callback. |

### Priority 1: Top-level Mod Build/Run Paths

These paths are similar but touch mod-specific NoDb controllers. They should be guarded after confirming each mutating method persists its own `.nodb` state and after choosing whether related prerequisite controllers are read-only inputs or mutation participants.

| File | Function | Guard scope | Evidence |
|------|----------|-------------|----------|
| `wepppy/rq/project_rq.py` | `build_rangeland_cover_rq` | `rangeland_cover.nodb` | `RangelandCover.getInstance(wd)` followed by `build(...)`. |
| `wepppy/rq/project_rq.py` | `build_treatments_rq` | `treatments.nodb` | `Treatments.getInstance(wd).build_treatments()` under landuse/soils root locks. |
| `wepppy/rq/project_rq.py` | `run_ash_rq` | `ash.nodb` | `Ash.getInstance(wd)` followed by `run_ash(...)`. |
| `wepppy/rq/project_rq.py` | `run_debris_flow_rq` | `debris_flow.nodb` | `DebrisFlow.getInstance(wd)` followed by `run_debris_flow(...)`. |
| `wepppy/rq/project_rq.py` | `run_rhem_rq` | `rhem.nodb` | `Rhem.getInstance(wd)` followed by clean/prep/run methods. |
| `wepppy/rq/project_rq.py` | `fetch_and_analyze_rap_ts_rq` | `rap_ts.nodb` | `RAP_TS.getInstance(wd)` followed by `acquire_rasters(...)` and `analyze()`. |
| `wepppy/rq/project_rq.py` | `fetch_and_analyze_openet_ts_rq` | `openet_ts.nodb` | `OpenET_TS.getInstance(wd)` followed by `acquire_timeseries(...)` and `analyze()`. |
| `wepppy/rq/project_rq.py` | `fetch_and_align_polaris_rq` | `polaris.nodb` | `Polaris.getInstance(wd)` followed by `acquire_and_align(...)`. |
| `wepppy/rq/project_rq.py` | `build_rusle_rq` | `rusle.nodb` | `Rusle.getInstance(wd)` followed by `build(...)`. |

### Priority 2: Cross-module and Orchestration Paths

These should be audited and guarded where the mutation boundary is clear. They may need separate tests or a split package if the implementation gets large.

| File | Function | Initial guard scope | Reason to investigate |
|------|----------|---------------------|-----------------------|
| `wepppy/rq/wepp_rq.py` | `bootstrap_enable_rq`, `run_wepp_rq`, `run_wepp_watershed_rq`, `prep_wepp_watershed_rq` | `wepp.nodb` | Orchestrator paths call mutating `Wepp` methods such as `init_bootstrap()`, `ensure_bootstrap_main()`, `clean()`, and `_check_and_set_*` before enqueueing stage jobs. |
| `wepppy/rq/swat_rq.py` | `_build_swat_inputs_rq` | `swat.nodb` | `Swat.getInstance(wd).build_inputs()` is a mod-specific mutable build path. |
| `wepppy/rq/omni_rq.py` | `run_omni_scenario_rq`, `run_omni_contrast_rq`, `run_omni_scenarios_rq`, `run_omni_contrasts_rq`, `delete_omni_contrasts_rq` | `omni.nodb` plus PUP scopes where applicable | Omni already has cache/lock helpers for clone paths; execution/deletion paths should be audited before adding duplicate guards. |
| `wepppy/rq/path_ce_rq.py` | `run_path_cost_effective_rq` | `path_cost_effective.nodb` and `omni.nodb` | The workflow mutates PATH status and provisions/runs Omni scenarios. |
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

- [ ] Priority 0 call sites have scoped cache guards before mutable controller hydration.
- [ ] Priority 1 call sites have implementation or explicit defer/split disposition backed by method-level audit.
- [ ] Existing lock-root, archive-root rejection, status, timestamp, and enqueue behavior remains unchanged.
- [ ] Targeted regression tests pass for guarded paths.
- [ ] Package docs and `PROJECT_TRACKER.md` are synchronized and lint-clean.

## Dependencies

### Prerequisites

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

## Hardening and Callus Softening

- **Failure signature(s)**:
  - Prior confirmed `NoDbStaleWriteError` in `build_soils_rq` for `soils.nodb`.
  - This package targets adjacent equivalent shapes before they produce the same signature.
- **Health signals**:
  - No stale-write recurrence in guarded RQ paths.
  - Regression tests fail if guards are removed or broadened incorrectly.
- **Danger signals**:
  - Guards added before archive-root rejection, masking existing contract behavior.
  - Broad cache clears replacing scoped guards and disrupting unrelated in-flight work.
- **Temporary calluses introduced**: none planned.
- **Callus softening hypothesis**: not applicable; scoped deterministic guards should become stable contract behavior.

## Deliverables

- Guard implementation for prioritized RQ mutation paths.
- Regression coverage for guard ordering and scope.
- Priority 2 disposition note if not fully implemented in this package.
- Updated package lifecycle docs and tracker evidence.

## Follow-up Work

- Split Priority 2 module families into dedicated packages if the audit shows behavior-specific testing is too large for this package.

## Kickoff Prompt

- Execution prompt: `docs/work-packages/20260428_rq_scoped_stale_cache_guard_followups/prompts/active/execute_rq_scoped_stale_cache_guard_followups_prompt.md`
- Active ExecPlan: `docs/work-packages/20260428_rq_scoped_stale_cache_guard_followups/prompts/active/rq_scoped_stale_cache_guard_followups_execplan.md`
