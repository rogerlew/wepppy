# MOFE Map Migration to wepppyo3 (Topaz Pre-Index + Rank Assignment)

**Status**: Closed (2026-04-23)
**Timezone**: UTC

## Overview
`WatershedOperationsMixin._build_mofe_map` is currently Python/Numpy-heavy and repeatedly scans full rasters per hillslope and per segment threshold. This package migrates MOFE map construction into `wepppyo3` (Rust/PyO3), with a pre-indexed by-`topaz_id` assignment path that labels MOFE ids from per-hillslope discharge rank in one pass while preserving current output semantics.

## Objectives
- Implement a production `wepppyo3` MOFE-map builder API that takes watershed rasters/segment boundaries and returns contiguous MOFE labels.
- Preserve parity with current `_build_mofe_map` behavior, including endpoint and fallback/repair semantics.
- Replace the Python hot-path in `_build_mofe_map` with the Rust implementation while keeping explicit failure contracts.
- Add parity and regression tests in WEPPpy + wepppyo3 for topaz-id indexing, rank-based assignment, and contiguous-id guarantees.
- Capture benchmark evidence showing runtime impact on representative watershed inputs.

## Scope
This package covers MOFE map construction only. It does not change hillslope abstraction or segmentation semantics already migrated in `20260422_segmented_multiple_ofe_wepppyo3_pool`.

### Included
- New wepppyo3 MOFE map construction routine and Python binding.
- WEPPpy call-site integration for `_build_mofe_map`.
- Optimized algorithm: pre-index cells by `topaz_id`, then assign labels by discharge-rank segment counts in one pass per hillslope.
- Test updates/additions for parity and regression safety.
- Benchmark artifacts and package documentation updates.

### Explicitly Out of Scope
- Changes to Peridot abstraction binaries or `post_abstract_watershed` contracts.
- Changes to MOFE segmentation `.mofe.slp` generation rules.
- Broader landuse/soils aggregation refactors outside MOFE map assignment.

## Stakeholders
- **Primary**: WEPPpy/WEPPcloud operators running MOFE workflows.
- **Reviewers**: NoDb watershed maintainers, wepppyo3 maintainers.
- **Security Reviewer**: Not required for planned scope.
- **Informed**: Disturbed workflow maintainers and runtime-performance triage contributors.

## Success Criteria
- [x] `wepppyo3` exposes a stable MOFE-map API used by WEPPpy production `_build_mofe_map`.
- [x] Output parity is demonstrated against existing Python behavior on targeted fixtures/runs.
- [x] `_build_mofe_map` no longer performs repeated full-raster `np.where` scans per hillslope/OFE.
- [x] Regression tests cover pre-indexed assignment, contiguous-id guarantees, and fallback semantics.
- [x] Benchmark artifact captures measured before/after runtime delta with mean/stddev and percent delta.

## Dependencies

### Prerequisites
- Existing segmented MOFE migration package closure: [20260422_segmented_multiple_ofe_wepppyo3_pool](../20260422_segmented_multiple_ofe_wepppyo3_pool/package.md).
- Access to `/home/workdir/wepppyo3` workspace for Rust/PyO3 implementation.

### Blocks
- Further MOFE runtime optimization packages should depend on this package for baseline map-builder performance.

## Related Packages
- **Depends on**: [20260422_segmented_multiple_ofe_wepppyo3_pool](../20260422_segmented_multiple_ofe_wepppyo3_pool/package.md)
- **Related**: [20260422_peridot_side_hillslope_length_capping](../20260422_peridot_side_hillslope_length_capping/package.md)
- **Follow-up**: Potential package for broader watershed map/vector aggregation acceleration.

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions.
- **Complexity**: High (cross-repo parity-sensitive refactor).
- **Risk level**: Medium-High (downstream model contract sensitivity).

## Security Impact and Review Gate
- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: Planned changes are internal computational refactors with no auth/session/secrets/public-route surface changes.
- **Security review artifact**: `N/A`

## References
- `wepppy/nodb/core/watershed_mixins.py` (`_build_mofe_map`, `_assign_mofe_ids_by_discharge_rank`)
- `tests/nodb/test_watershed_mofe_map.py`
- `wepppy/all_your_base/geo.py` (`read_raster`, `write_raster` call pattern)
- `/home/workdir/wepppyo3` (PyO3 module and Rust core)

## Deliverables
- wepppyo3 MOFE-map API and WEPPpy production integration.
- Updated tests in WEPPpy/wepppyo3 validating parity and failure contracts.
- Benchmark artifacts under `artifacts/` with raw and summarized metrics.
- Updated package tracker + ExecPlan + project tracker lifecycle entries.

## Closure Notes
- Implemented new module `wepppyo3.watershed_abstraction` with PyO3 API `assign_mofe_map(...)` (topaz pre-indexing + legacy-compatible fallback/repair semantics).
- WEPPpy production `_build_mofe_map` now delegates assignment to Rust via `wepppy/topo/watershed_abstraction/mofe_map.py` loader; no silent fallback path was introduced.
- Added WEPPpy tests:
  - `tests/nodb/test_watershed_mofe_map.py` (legacy parity helper + Rust delegation integration)
  - `tests/topo/test_watershed_abstraction_mofe_map.py` (loader contract/failure behavior)
- Added wepppyo3 tests:
  - `tests/watershed_abstraction/test_assign_mofe_map.py`
  - Rust unit tests in `watershed_abstraction/src/lib.rs`
- Captured artifacts:
  - `artifacts/parity_raw.json`, `artifacts/parity_notes.md`
  - `artifacts/benchmark_raw.json`, `artifacts/benchmark_summary.md`
- Validation highlights:
  - Targeted WEPPpy tests passed.
  - wepppyo3 Rust + Python tests passed.
  - Broad WEPPpy sweep (`wctl run-pytest tests --maxfail=1`) hit one unrelated existing failure in `tests/nodb/test_wepp_run_service.py::test_run_watershed_does_not_rewrite_wepp_50k_bin`.

## Follow-up Work
- Evaluate migrating other raster label-assignment hot paths from Python to wepppyo3.
- Consider adding dedicated performance regression gates for watershed abstraction phases.
