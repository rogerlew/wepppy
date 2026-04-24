# Landuse Multi-OFE Build Optimization (Lookup Reuse, Pass De-dup, IO Guarding, Logging)

**Status**: Complete (2026-04-23)
**Timezone**: UTC

## Overview
Multi-OFE landuse build still has avoidable overhead in `wepppy/nodb/core/landuse.py`: repeated management summary lookup in SBS burn remap, duplicate heavy `build_managements()` passes in `build()`, and high-volume info logging in large watersheds. This package optimizes these hotspots while preserving output parity, event semantics, and explicit failure contracts.

## Objectives
- Reuse cached management summaries in the SBS burn-remap path instead of repeated `get_management_summary(...)` calls.
- Remove or safely collapse duplicate heavy `build_managements()` passes in `Landuse.build()` for multi-OFE flows.
- Guarantee no unnecessary MOFE raster/pair-count work occurs in the first pass before MOFE assignments exist.
- Reduce high-volume logging overhead (large dict dumps and per-hillslope info spam) without reducing diagnosability.
- Add regression/parity tests and benchmark evidence (per-run timings, mean/stddev, percent delta).

## Scope
This package is limited to WEPPpy landuse multi-OFE build-path performance and contract-preserving refactors.

### Included
- `wepppy/nodb/core/landuse.py` optimization edits for the four identified hotspots.
- Targeted tests in `tests/nodb/` for parity, event/trigger behavior, and contract preservation.
- Benchmark/parity artifact capture under this package `artifacts/`.
- Package lifecycle docs (`tracker.md`, ExecPlan updates, `PROJECT_TRACKER.md`).

### Explicitly Out of Scope
- New wepppyo3/Rust APIs.
- MOFE map assignment algorithm changes.
- Disturbed soils process-pool changes.
- Unrelated Geneva/RQ/doc-index dirty worktree cleanup.

## Stakeholders
- **Primary**: NoDb landuse maintainers and disturbed workflow operators.
- **Reviewers**: NoDb core maintainers, disturbed maintainers, QA maintainers.
- **Security Reviewer**: Not required for planned scope.
- **Informed**: Runtime performance triage contributors.

## Success Criteria
- [x] SBS remap path no longer performs repeated `get_management_summary(...)` per `(topaz_id, mofe_id)` pair when equivalent summary is already available.
- [x] Duplicate heavy `build_managements()` pass in `Landuse.build()` is removed or merged with explicit parity and trigger-event contract tests.
- [x] Multi-OFE first pass does not do MOFE raster/pair-count work before `domlc_mofe_d` is available.
- [x] High-volume logging in hot loops is reduced (debug-gated/summarized) without losing failure diagnostics.
- [x] Targeted tests pass, and benchmark/parity artifacts contain per-run timings, mean/stddev, and percent delta.

## Dependencies

### Prerequisites
- [20260423_mofe_map_wepppyo3](../20260423_mofe_map_wepppyo3/package.md)
- [20260423_mofe_landuse_pair_counts_wepppyo3](../20260423_mofe_landuse_pair_counts_wepppyo3/package.md)
- [20260423_mofe_man_synthesis_process_pool](../20260423_mofe_man_synthesis_process_pool/package.md)

### Blocks
- Follow-on package(s) for broader per-hillslope planning offload if this optimization pass does not deliver target runtime gains.

## Related Packages
- **Depends on**: [20260423_mofe_man_synthesis_process_pool](../20260423_mofe_man_synthesis_process_pool/package.md)
- **Related**: [20260423_mofe_landuse_pair_counts_wepppyo3](../20260423_mofe_landuse_pair_counts_wepppyo3/package.md)
- **Follow-up**: deeper multi-OFE planning/object materialization offload if needed.

## Timeline Estimate
- **Expected duration**: 2-5 focused sessions.
- **Complexity**: Medium-High.
- **Risk level**: Medium (duplicate-pass collapse may alter side-effect timing if not explicitly guarded).

## Security Impact and Review Gate
- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: internal compute/logging optimization in existing NoDb controller path; no auth/session/secrets/public-route changes.
- **Security review artifact**: `N/A`

## Benchmark Dataset Targets
Use isolated temp copies of these local run roots (do not modify source run data):
- `/wc1/runs/mo/moth-eaten-blackhead`
- `/wc1/runs/ob/objectionable-sublimate`
- `/wc1/runs/co/cochlear-beriberi`
- `/wc1/runs/or/ordained-incentive`
- `/wc1/runs/un/uninsured-deformation`

Reference URLs:
- `https://wc.bearhive.duckdns.org/weppcloud/runs/moth-eaten-blackhead/disturbed9002-wbt-mofe/`
- `https://wc.bearhive.duckdns.org/weppcloud/runs/objectionable-sublimate/disturbed9002_wbt/`
- `https://wc.bearhive.duckdns.org/weppcloud/runs/cochlear-beriberi/disturbed9002-mofe/`
- `https://wc.bearhive.duckdns.org/weppcloud/runs/ordained-incentive/disturbed9002-wbt-mofe/`
- `https://wc.bearhive.duckdns.org/weppcloud/runs/uninsured-deformation/disturbed9002-wbt-mofe/`

## References
- `wepppy/nodb/core/landuse.py` (`build`, `_build_multiple_ofe`, `build_managements`)
- `wepppy/wepp/management/managements.py::get_management_summary`
- `tests/nodb/test_landuse_mofe_process_pool.py`
- `tests/nodb/test_landuse_mofe_disturbed_scalar_lookup.py`
- `tests/nodb/test_landuse_coverage_area_source.py`

## Deliverables
- Updated WEPPpy landuse implementation for four hotspot lanes.
- Added/updated targeted regression tests.
- Benchmark/parity artifacts:
  - `artifacts/benchmark_raw.json`
  - `artifacts/benchmark_summary.md`
  - `artifacts/parity_raw.json`
  - `artifacts/parity_notes.md`
- Package lifecycle updates and archived ExecPlan/outcome note.

## Closure Notes (2026-04-23)

- Completed implementation in `wepppy/nodb/core/landuse.py`:
  - Reused cached management summaries in SBS remap loop (`_build_multiple_ofe`).
  - Collapsed multi-OFE duplicate `build_managements()` pass in `Landuse.build()` while preserving final post-DOMLC rebuild flow.
  - Cleared stale `domlc_mofe_d` before multi-OFE build path and guarded MOFE pair-count work when assignment map is missing/empty.
  - Moved heavy/high-volume informational logging to compact summaries/debug-level logs.
- Added/updated regression coverage:
  - `tests/nodb/test_landuse_mofe_disturbed_scalar_lookup.py`
  - `tests/nodb/test_landuse_coverage_area_source.py`
  - `tests/nodb/test_landuse_build_event_contracts.py`
  - `tests/nodb/test_landuse_mofe_process_pool.py`
- Validation:
  - `wctl run-pytest tests/nodb/test_landuse_mofe_process_pool.py tests/nodb/test_landuse_mofe_disturbed_scalar_lookup.py tests/nodb/test_landuse_coverage_area_source.py tests/nodb/test_landuse_build_event_contracts.py --maxfail=1 -q` -> `14 passed`.
- Benchmark/parity artifacts regenerated from isolated temp-run copies for all required benchmark runs:
  - `artifacts/benchmark_raw.json`
  - `artifacts/benchmark_summary.md`
  - `artifacts/parity_raw.json`
  - `artifacts/parity_notes.md`
- Benchmark deltas (optimized vs legacy emulation): `+0.21%`, `-1.00%`, `-3.19%`, `-7.28%`, `-0.98%` (single-iteration sampling).
- Contract parity status: `match` for all five runs (MOFE files, management area/pct values, and `domlc_mofe_d`).

## Follow-up Work
- If benchmark deltas remain weak/negative, scope a follow-up package that offloads broader per-hillslope plan construction, not just final synthesis/write phases.
