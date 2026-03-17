# Omni Contrast Hillslope Re-run Recovery (`delete_after_interchange`)

**Status**: Closed (2026-03-17)

## Overview
Omni contrasts build watershed runs from hillslope `*.pass.dat` paths listed in contrast sidecars. When `delete_after_interchange` is enabled, those source hillslope files are intentionally removed after interchange completes, so `run_omni_contrasts_rq` cannot build contrast watershed runs from base/scenario outputs.

This package adds a targeted pre-contrast recovery step: rerun hillslopes (without prep and without interchange) for the exact scenarios referenced by contrasts that are about to run.

## Objectives
- Ensure `run_omni_contrasts_rq` can execute reliably when `delete_after_interchange=true`.
- Regenerate required hillslope source files by rerunning hillslopes only (`wepp.run_hillslopes()`), with no hillslope prep and no interchange regeneration.
- Limit reruns to scenarios used by the contrasts selected for execution in this invocation.
- Preserve current Omni contrast queue semantics, status messaging, and dependency-tree behavior.
- Add regression coverage for the failure mode and new recovery path.

## Scope

### Included
- `wepppy/rq/omni_rq.py` changes to:
  - identify scenario keys used by queued contrasts,
  - resolve scenario working directories,
  - rerun hillslopes in those directories before queuing contrast child jobs.
- Focused unit tests in `tests/rq/test_omni_rq.py` for scenario selection and rerun behavior.
- Work-package planning + tracker + ExecPlan docs for implementation handoff.

### Explicitly Out of Scope
- Rebuilding contrasts via hillslope prep (`prep_hillslopes`) for this fix.
- Regenerating any WEPP interchange artifacts during contrast preflight.
- Changing Omni contrast API routes, request payload contracts, or UI forms.
- Modifying contrast watershed execution internals (`_run_contrast`) beyond consuming regenerated hillslope outputs.

## Stakeholders
- **Primary**: Omni/WEPP RQ maintainers.
- **Reviewers**: NoDb Omni maintainers and rq-engine maintainers.
- **Informed**: Omni UI/report consumers who rely on contrast reruns after scenario execution.

## Success Criteria
- [x] `run_omni_contrasts_rq` reruns hillslopes only for scenarios referenced by queued contrast runs when `delete_after_interchange` is enabled.
- [x] The pre-contrast rerun path does not call hillslope prep or any interchange writers.
- [x] Existing skip paths remain intact (`up_to_date`, `in_progress`, missing sidecar, landuse-unchanged).
- [x] New/updated unit tests cover scenario resolution, deduped rerun targets, and the delete-flag gate.
- [x] Targeted tests pass and docs/tracker stay synchronized.

## Dependencies

### Prerequisites
- Existing Omni contrast queue orchestration in `wepppy/rq/omni_rq.py`.
- Existing scenario key parsing in `wepppy/nodb/mods/omni/omni_station_catalog_service.py`.
- Existing WEPP hillslope run entrypoint `Wepp.run_hillslopes()`.

### Blocks
- Robust contrast rerun behavior for runs configured with `delete_after_interchange=true`.

## Related Packages
- **Most recent related package context**: [20260312_tenerife_2026_data_ingestion](../20260312_tenerife_2026_data_ingestion/package.md) (ExecPlan workflow and package process baseline).
- **Follow-up**: none identified yet.

## Timeline Estimate
- **Expected duration**: 1 focused implementation session + validation pass.
- **Complexity**: Medium.
- **Risk level**: Medium (execution-order and path-resolution correctness).

## Closure Summary (2026-03-17)
- Implemented contrast preflight in `wepppy/rq/omni_rq.py` that:
  - collects deduped scenario keys from queued contrast IDs,
  - resolves scenario working directories (base scenario root + `_pups/omni/scenarios/<scenario>`),
  - reruns hillslopes only via `Wepp.getInstance(<scenario_wd>).run_hillslopes()` when `delete_after_interchange` is enabled,
  - for non-base scenarios, uses relpaths back to base `wepp/runs` for `cli/slp` inputs (matching Omni scenario execution semantics).
- Refactored relpath computation into shared helper `_hillslope_input_relpath_to_base_runs` in `wepppy/nodb/mods/omni/omni.py` and reused it in both Omni scenario orchestration and contrast preflight reruns.
- Added explicit rerun input validation + status diagnostics in `wepppy/rq/omni_rq.py` for missing hillslope inputs (including local scenario `man/sol` assumptions).
- Added regression coverage in `tests/rq/test_omni_rq.py` for:
  - delete-flag-enabled rerun behavior with scenario deduplication and enqueue ordering,
  - delete-flag-disabled behavior with no rerun preflight.
- Added focused validation coverage for rerun input contracts where scenario-local `slp/cli` are absent but base-run relpaths are valid.
- Synced boundary allowlist line anchors in `docs/standards/broad-exception-boundary-allowlist.md` after `omni_rq.py` line shifts.
- Validation completed:
  - `wctl run-pytest tests/rq/test_omni_rq.py --maxfail=1` -> pass
  - `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` -> pass
  - `wctl run-pytest tests --maxfail=1` -> `2323 passed, 34 skipped`

## References
- `wepppy/rq/omni_rq.py` - contrast queue orchestration (`run_omni_contrasts_rq`).
- `wepppy/nodb/mods/omni/omni_run_orchestration_service.py` - contrast/scenario orchestration patterns and hillslope run usage.
- `wepppy/nodb/mods/omni/omni_station_catalog_service.py` - contrast scenario key derivation.
- `wepppy/nodb/mods/omni/omni_clone_contrast_service.py` - contrast clone uses `*.pass.dat` paths for watershed run stubs.
- `wepp_runner/wepp_runner.py` - `make_watershed_omni_contrasts_run` consumes `{wepp_id_path}.pass.dat`.
- `wepppy/wepp/interchange/hill_interchange.py` - `cleanup_hillslope_sources_for_completed_interchange` deletion behavior.
- `tests/rq/test_omni_rq.py` - existing `run_omni_contrasts_rq` test surface.

## Deliverables
- Updated `run_omni_contrasts_rq` logic with hillslope rerun preflight for contrast scenarios.
- Targeted regression tests for delete-after-interchange recovery behavior.
- Synchronized package docs (`package.md`, `tracker.md`, ExecPlan moved to `prompts/completed`).

## Follow-up Work
- Evaluate whether the same recovery helper should be reused in direct (non-RQ) `Omni.run_omni_contrasts()` execution paths.
- Optional observability follow-up: add explicit status events for each scenario hillslope rerun in Omni contrast channel.
