# Tenerife 2026 Data Ingestion

**Status**: Completed (2026-03-12)

## Overview
This work package integrates Jonay's 2026 Tenerife refresh into the active WEPPpy runtime. The implementation uses a dedicated Tenerife climate station catalog, the active Tenerife configs point at that catalog and explicitly default to WBT delineation, and the Tenerife soil runtime surface is reduced to the supported 25 m and 5 m maps with explicit documentation for the remaining `20.sol` and `21.sol` shims.

## Objectives
- Keep Tenerife 25 m and 5 m NoDb configs aligned with the 2026 runtime baseline, including explicit WBT delineation defaults.
- Install a Tenerife-specific CLIGEN station catalog for Jonay's 62 station `.par` files.
- Retire obsolete Tenerife soil legacy assets while keeping required runtime shims explicit.
- Add repeatable Tenerife-focused validation so future refreshes do not require rediscovery.

## Scope
This package covers Tenerife-specific NoDb config review, Tenerife climate station catalog creation, Tenerife soil asset cleanup, Tenerife validation, and package documentation updates.

### Included
- `wepppy/nodb/configs/tenerife-disturbed.cfg`
- `wepppy/nodb/configs/tenerife-5m-disturbed.cfg`
- Tenerife climate catalog assets under `wepppy/climates/cligen/`
- Tenerife soil runtime assets under `wepppy/locales/tenerife/soils/`
- Tenerife-focused tests and work-package docs

### Explicitly Out of Scope
- Managed ingestion of Tenerife observed `.cli` files
- Rehosting DEM rasters on `wepp1`
- Landuse or treatment changes unrelated to the Tenerife 2026 data refresh
- Preserving pre-2026 Tenerife soil or climate behavior

## Stakeholders
- **Primary**: Roger Lew
- **Reviewers**: Roger Lew, Jonay
- **Informed**: WEPPcloud operators maintaining `wepp1` / `wmesque2`

## Success Criteria
- [x] Tenerife 25 m and 5 m configs point at reviewed DEM keys and supported soil assets, explicitly default to WBT delineation, and their live WMesque dataset keys were smoke-tested.
- [x] Tenerife climate station selection resolves Jonay's 62 station `.par` files through a dedicated Tenerife catalog used by the active Tenerife configs.
- [x] Tenerife soil runtime behavior is explicit for the supported rasters, including the special `20` and `21` classes.
- [x] Obsolete Tenerife soil legacy assets are retired, while `tf_soil_10.tif` is kept only as inert 2026 source inventory.
- [x] Tenerife-focused validation exists for climate catalog contents, config wiring, soil raster coverage, and retired legacy inventory.

## Dependencies

### Prerequisites
- Jonay source bundle at `/workdir/tenerife-2026/`
- Existing DEM deployment and catalog entries on `wepp1` / `wmesque2`
- Active NoDb climate and soil runtime paths in `wepppy/nodb/core/`

### Blocks
- None remaining for this package.

## Related Packages
- **Depends on**: None
- **Related**: `docs/work-packages/20260205_ned1_vrt_alignment/package.md`
- **Follow-up**: Optional Tenerife launch-surface/UI work if the 5 m config should become user-discoverable

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions
- **Actual implementation state**: Complete in the first session
- **Risk level**: Medium

## References
- `/workdir/tenerife-2026/README.md`
- `/workdir/tenerife-2026/DEM/README.md`
- `/workdir/tenerife-2026/climate/README.md`
- `/workdir/tenerife-2026/soil/README.md`
- `wepppy/nodb/configs/tenerife-disturbed.cfg`
- `wepppy/nodb/configs/tenerife-5m-disturbed.cfg`
- `wepppy/climates/cligen/cligen.py`
- `wepppy/climates/cligen/_scripts/build_tenerife_station_db.py`
- `wepppy/locales/tenerife/soils/README.md`

## Deliverables
- Dedicated Tenerife climate catalog: `tenerife_stations.db`, `tenerife_stations.csv`, and `tenerife_par_files/`
- Active Tenerife configs switched to `cligen_db = "tenerife_stations.db"` and `delineation_backend = "wbt"`
- Tenerife soil legacy cleanup: removed legacy 250 m config/raster branch and template-generation artifacts
- Tenerife soil runtime note in `wepppy/locales/tenerife/soils/README.md`
- Tenerife-focused tests and custom validation evidence recorded in the tracker and ExecPlan

## Follow-up Work
- Decide later whether Tenerife needs a first-class 10 m config or UI surface.
