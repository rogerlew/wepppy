# Multi-OFE Landuse Pair-Count Optimization via wepppyo3 Raster Characteristics

**Status**: Closed (2026-04-23)
**Timezone**: UTC

## Overview
`Landuse.build_managements()` still performs repeated full-raster scans when computing per-`(topaz_id, mofe_id)` area coverage for multi-OFE runs. This package adds a dedicated Rust/PyO3 counting API in `wepppyo3.raster_characteristics` and rewires the WEPPpy call site to use one-pass pair counting with explicit contracts and parity checks.

## Objectives
- Add a production `wepppyo3.raster_characteristics` API to count intersecting raster key pairs (`key`, `key2`) in one pass.
- Replace the hot Python multi-OFE area loop in `Landuse.build_managements()` with the Rust count path.
- Preserve current behavior contracts for area/pct coverage outputs and explicit failure handling.
- Add regression/parity tests in both repos for new API and WEPPpy integration.
- Capture benchmark evidence on the specified local run set with per-run timings, mean/stddev, and percent delta.

## Scope
This package is limited to optimization lane #1: replacing multi-OFE pair-area counting with a Rust API under `raster_characteristics` and integrating that API in WEPPpy landuse build paths.

### Included
- New `wepppyo3.raster_characteristics` pair-count API and release export.
- WEPPpy integration in `wepppy/nodb/core/landuse.py` multi-OFE area calculation path.
- Targeted parity/regression tests in WEPPpy and wepppyo3.
- Benchmark and parity artifacts under package `artifacts/`.
- Package lifecycle docs updates (`tracker.md`, active/completed ExecPlan notes, `PROJECT_TRACKER.md`).

### Explicitly Out of Scope
- Broader multi-OFE `.man` synthesis parallelization work.
- Disturbed/RAP semantic changes beyond preserving current output behavior.
- Additional optimization lanes not directly required for pair-count replacement.

## Stakeholders
- **Primary**: WEPPpy/WEPPcloud operators running disturbed multi-OFE workflows.
- **Reviewers**: NoDb landuse maintainers, wepppyo3 maintainers.
- **Security Reviewer**: Not required for planned scope.
- **Informed**: Disturbed mod maintainers and runtime performance triage contributors.

## Success Criteria
- [x] New Rust API exists in `wepppyo3.raster_characteristics` and is shipped in release package exports.
- [x] WEPPpy multi-OFE area coverage path no longer uses repeated `np.where` full-raster scans per pair.
- [x] Area and pct coverage parity demonstrated versus current behavior on fixed benchmark/parity inputs.
- [x] Targeted tests pass in both repos.
- [x] Benchmark artifact reports per-run timings, mean/stddev, and percent delta on the five specified runs.

## Dependencies

### Prerequisites
- Closed MOFE map migration package: [20260423_mofe_map_wepppyo3](../20260423_mofe_map_wepppyo3/package.md).
- Access to both workspaces: `/home/workdir/wepppy` and `/home/workdir/wepppyo3`.

### Blocks
- Follow-on multi-OFE landuse optimization packages (parallel `.man` synthesis, duplicate build pass elimination) should depend on this package baseline.

## Related Packages
- **Depends on**: [20260423_mofe_map_wepppyo3](../20260423_mofe_map_wepppyo3/package.md)
- **Related**: [20260422_segmented_multiple_ofe_wepppyo3_pool](../20260422_segmented_multiple_ofe_wepppyo3_pool/package.md)
- **Follow-up**: package(s) for multi-OFE synthesis parallelization and trigger/build-pass reduction.

## Timeline Estimate
- **Expected duration**: 1-3 focused sessions.
- **Complexity**: Medium-High (cross-repo parity + performance contract).
- **Risk level**: Medium (landuse report/runtime contract sensitivity).

## Security Impact and Review Gate
- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: Internal computational optimization only; no auth/session/secrets/public route surface changes.
- **Security review artifact**: `N/A`

## Benchmark Dataset Targets
Benchmark/parity dataset anchors for this package:
- `https://wc.bearhive.duckdns.org/weppcloud/runs/moth-eaten-blackhead/disturbed9002-wbt-mofe/`
- `https://wc.bearhive.duckdns.org/weppcloud/runs/objectionable-sublimate/disturbed9002_wbt/`
- `https://wc.bearhive.duckdns.org/weppcloud/runs/cochlear-beriberi/disturbed9002-mofe/`
- `https://wc.bearhive.duckdns.org/weppcloud/runs/ordained-incentive/disturbed9002-wbt-mofe/`
- `https://wc.bearhive.duckdns.org/weppcloud/runs/uninsured-deformation/disturbed9002-wbt-mofe/`

Expected local roots:
- `/wc1/runs/mo/moth-eaten-blackhead`
- `/wc1/runs/ob/objectionable-sublimate`
- `/wc1/runs/co/cochlear-beriberi`
- `/wc1/runs/or/ordained-incentive`
- `/wc1/runs/un/uninsured-deformation`

## References
- `wepppy/nodb/core/landuse.py` (`_build_multiple_ofe`, `build_managements`)
- `/home/workdir/wepppyo3/raster_characteristics/src/lib.rs`
- `wepppy/wepp/management/utils/multi_ofe.py`
- `tests/nodb/test_landuse_coverage_area_source.py`

## Deliverables
- New Rust pair-count API + Python export in wepppyo3.
- WEPPpy integration patch for multi-OFE area counting.
- Added/updated tests in both repos.
- Raw + summary benchmark/parity artifacts under `artifacts/`.
- Updated package docs and `PROJECT_TRACKER.md` lifecycle entry.

## Closure Notes (2026-04-23 17:22 UTC)
- Implemented and exported `count_intersecting_raster_key_pairs` in `wepppyo3.raster_characteristics` with explicit read/shape failure contracts.
- Integrated WEPPpy `Landuse.build_managements()` multi-OFE area path to consume Rust pair counts with unchanged area/pct semantics.
- Added regression coverage in both repos and rebuilt canonical release binary (`release/linux/py312/wepppyo3/raster_characteristics/raster_characteristics_rust.so`).
- Produced required artifacts:
  - `artifacts/benchmark_raw.json`
  - `artifacts/benchmark_summary.md`
  - `artifacts/parity_raw.json`
  - `artifacts/parity_notes.md`
- Required run matrix executed using isolated temp copies. For `/wc1/runs/ob/objectionable-sublimate` (no MOFE map, no `domlc_mofe_d`), benchmark harness used an isolated synthetic single-segment MOFE map and derived pair map from `domlc_d`; this adaptation is flagged in raw artifacts.

## Follow-up Work
- Parallelize multi-OFE `.mofe.man` synthesis per hillslope.
- Remove/reduce duplicate `build_managements()` passes in landuse build flow.
- Optional cache/materialization of management summaries for burn-remap loops.
