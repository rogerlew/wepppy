# Tenerife Locale Integration

> Runtime reference for the active Tenerife WEPPcloud interfaces and data wiring.

## Overview

Tenerife is currently served by two active configs:

- `tenerife-disturbed` (25 m)
- `tenerife-5m-disturbed` (5 m)

Both interfaces use:

- WhiteboxTools delineation (`delineation_backend = "wbt"`)
- DEM retrieval through `wmesque` version 2
- Dedicated Tenerife climate station catalog (`tenerife_stations.db`)
- Tenerife-specific soils rasters and `.sol` profile database

Source configs:

- `wepppy/nodb/configs/tenerife-disturbed.cfg`
- `wepppy/nodb/configs/tenerife-5m-disturbed.cfg`

## DEM Integration (`wmesque2`)

DEM rasters are requested from mapserver datasets via config `dem_db` keys:

- `tenerife-disturbed`: `tenerife/136_MDT25_TF`
- `tenerife-5m-disturbed`: `tenerife/MDT05_Tenerife`

Both configs explicitly set:

- `[wmesque] version=2`

Operationally, this means Tenerife DEM support depends on those dataset keys
being installed and reachable in the `wmesque2` service backing WEPPcloud.

## Climate Integration (Dedicated Tenerife Catalog)

Active Tenerife configs use:

- `[climate] cligen_db = "tenerife_stations.db"`

Catalog assets live in:

- `wepppy/climates/cligen/tenerife_stations.db`
- `wepppy/climates/cligen/tenerife_stations.csv`
- `wepppy/climates/cligen/tenerife_par_files/`

Refresh builder:

- `wepppy/climates/cligen/_scripts/build_tenerife_station_db.py`

Example rebuild command:

```bash
python wepppy/climates/cligen/_scripts/build_tenerife_station_db.py \
  --source-climate-dir /workdir/tenerife-2026/climate \
  --output-dir /workdir/wepppy/wepppy/climates/cligen
```

### Tenerife catalog runtime constraints

When `cligen_db` resolves to `tenerife_stations.db`, runtime enforces:

- climate mode: `Vanilla` only
- climate spatial mode: `Single` only
- station mode: `FindClosestAtRuntime` (auto) and `Closest` (distance ranking) only

These constraints are enforced in `wepppy/nodb/core/climate.py`.

## Soils Integration

Active Tenerife soil rasters:

- `wepppy/locales/tenerife/soils/tf_soil_25.tif` (`tenerife-disturbed`)
- `wepppy/locales/tenerife/soils/tf_soil_5.tif` (`tenerife-5m-disturbed`)

Reference-only raster (not currently wired by active configs):

- `wepppy/locales/tenerife/soils/tf_soil_10.tif`

Soil profile database:

- `wepppy/locales/tenerife/soils/db/*.sol`

Runtime still requires `20.sol` and `21.sol` shims for rock/urban class codes in
active rasters. See:

- `wepppy/locales/tenerife/soils/README.md`

### Template token handling in WEPP prep

Tenerife `.sol` files from legacy/template pipelines can include symbolic WEPP
tokens (`sat`, `ki`, `kr`, `tauc`, `ke`). During WEPP soil prep, runtime now
applies the legacy materialization path (`compute_erodibilities=True`,
`compute_conductivity=True`) when symbolic parameters are detected.

Implementation path:

- `wepppy/nodb/core/wepp.py`

## What Is Not Auto-Integrated

- Observed Tenerife `.cli` climate files are not auto-integrated in this locale
  package; they can still be used as user-defined climates.
- Retired Tenerife branches/artifacts (for example legacy 250 m wiring) are not
  part of the active runtime contract.

## Validation Checklist

1. Confirm config wiring:
   - `cligen_db = "tenerife_stations.db"`
   - `delineation_backend = "wbt"`
   - `soils_map` points to `tf_soil_25.tif` or `tf_soil_5.tif`
2. Confirm climate assets exist:
   - `tenerife_stations.db`
   - `tenerife_par_files/*.par`
3. Confirm soils runtime assets exist:
   - active `tf_soil_*.tif`
   - required `db/*.sol` (including `20.sol`, `21.sol`)
4. Run Tenerife tests and a run-level smoke test (`build-soils` then `run-wepp`).

