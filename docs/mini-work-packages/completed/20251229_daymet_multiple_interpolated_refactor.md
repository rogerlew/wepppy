# Daymet Multiple Interpolated Climate Build (Current Flow)
> Investigation notes for refactor away from local Daymet v4 rasters.
> Status: completed

## Context
Observed Daymet with `ClimateSpatialMode.MultipleInterpolated` is the current path for generating per-hillslope observed climate files. The local Daymet NetCDF dependency has been removed, so the build now relies only on the Daymet single-pixel API. This document captures the current flow and its dependencies.

## Entry Points
- `wepppy/nodb/core/climate.py` -> `Climate.build_climate()`
- Path: `climate_mode == ObservedPRISM (9)` and `climate_spatialmode == MultipleInterpolated (2)`
- Builder: `Climate._build_climate_observed_daymet_multiple()`

## Data Sources and Dependencies
- Daymet single-pixel API: `https://daymet.ornl.gov/single-pixel/api/data`
- Optional GridMET wind: `wepppy.climates.gridmet.retrieve_historical_wind` (ws centroid only)
- Rust interpolation kernel: `wepppyo3.climate.interpolate_geospatial`

## Current Control Flow
1. Build `hillslope_locations` from watershed centroid plus each hillslope centroid.
2. Call `daymet_singlelocation_client.interpolate_daily_timeseries(...)`:
   - Projects hillslopes to Daymet LCC and derives a bounding grid with padding.
   - Uses grid constants `a=-4560750`, `b=1000`, `d=4984500`, `f=-1000` to build pixel coordinates.
   - For each grid pixel, downloads Daymet daily time series via ORNL API.
   - Builds per-measure 3D cubes `(ncols, nrows, ndays)` for:
     - `prcp(mm/day)`, `tmax(degc)`, `tmin(degc)`, `tdew(degc)`, `srad(l/day)`
   - Interpolates each cube onto hillslope centroids via `interpolate_geospatial`.
   - Writes per-hillslope `.parquet` and `.prn` files in `cli_dir`.
4. If `use_gridmet_wind_when_applicable` is true:
   - Fetches wind for watershed centroid only.
   - Reuses the same wind series for every hillslope build.
5. For each hillslope and the watershed `ws`:
   - `build_observed_daymet_interpolated(...)` reads the parquet and runs `Cligen.run_observed` on the `.prn`.
   - Rewrites `rad`, `tdew`, and optional `w-vl`/`w-dir` in the `.cli`.
6. Climate state updates:
   - `self.cli_fn = "wepp.cli"`, `self.sub_cli_fns`, `self.sub_par_fns`, `self.monthlies`, `self.par_fn`.

## Artifacts
- `daymet_observed_<topaz_id>_<start>-<end>.parquet`
- `daymet_observed_<topaz_id>_<start>-<end>.prn`
- `daymet_observed_<topaz_id>_<start>-<end>.cli`
- `wepp.cli` (watershed aggregate)
- Debug output (always on): `daymet_observed_<col>,<row>_<start>-<end>.parquet`

## Observations
- API call count scales with the derived grid size, not just hillslope count.

## Closeout
- Removed the `identify_pixel_coords` dependency from `_build_climate_observed_daymet_multiple`.
- Updated `wepppy/climates/README.md` to reference `daymet_singlelocation_client` in the observed Daymet workflow.

## Follow-ups
- Evaluate caching or tiling to reduce ORNL per-pixel API calls for large watersheds.
