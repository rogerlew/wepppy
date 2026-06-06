# Initial Radiation Evidence

**Evidence mode**: Static local artifact inspection
**Captured**: 2026-06-06 20:01 UTC
**Run root**: `/wc1/runs/in/indispensable-presenter`

## Observed Downstream Failure

openWEPP WBVAL03 package execution reported a climate-source blocker before the
snowmelt/water-balance validation surfaces:

- `CLIM-RUNTIME-E-017: runtime context symbol radly=486 is out of domain`
- The openWEPP guard described the accepted domain as:
  `0 <= radly <= baseline sunmap horizontal daily potential (rpoth/r3)`

The corresponding openWEPP package is:

- `/workdir/openWEPP/docs/work-packages/20260606-wbval03-snowmelt-wb-closure-defect-closure-001/`

## WEPPpy Run Configuration

Static inspection of `/wc1/runs/in/indispensable-presenter/climate.nodb`
identified:

- Config: `disturbed9002_wbt.cfg`
- Climate mode: `observed_daymet`
- Climate mode enum value: `9`
- Station: `id102676`
- Station description: `DRIGGS ID`
- Observed years: `1990` through `1995`
- CLI file: `wepp.cli`
- CLIGEN database: `2015_stations.db`

`/wc1/runs/in/indispensable-presenter/climate.log` records:

- `climate.catalog_id -> observed_daymet`
- `running _build_climate_observed_daymet`
- `building wepp.cli`
- `Climate Build Successful.`

## Producer Chain

The observed-Daymet producer path is:

1. `wepppy/nodb/core/climate.py::_build_climate_observed_daymet`
2. `wepppy/nodb/core/climate_build_helpers.py::build_observed_daymet`
3. `wepppy.climates.daymet.retrieve_historical_timeseries(...)`
4. `ClimateFile.replace_var("rad", dates, df["srad(l/day)"])`
5. `climate.write(cli_path)`

Current source excerpt:

    df = daymet_retrieve_historical_timeseries(lng, lat, start_year, end_year, gridmet_wind=gridmet_wind)
    df.to_parquet(_join(cli_dir, f"daymet_{start_year}-{end_year}.parquet"))
    df_to_prn(df, _join(cli_dir, prn_fn), "prcp(mm/day)", "tmax(degc)", "tmin(degc)")
    ...
    climate = ClimateFile(cli_path)
    climate.replace_var("rad", dates, df["srad(l/day)"])
    climate.replace_var("tdew", dates, df["tdew(degc)"])
    ...
    climate.write(cli_path)

## Source and CLI Radiation Statistics

Static parquet inspection of
`/wc1/runs/in/indispensable-presenter/climate/daymet_1990-1995.parquet`
showed:

- `srad(l/day)` min: `21.429958336520073`
- `srad(l/day)` max: `989.1975619287764`
- `srad(l/day)` mean: `419.96463589751727`
- `srad(W/m^2)` min: `27.72`
- `srad(W/m^2)` max: `812.36`
- `srad(W/m^2)` mean: `386.40238703788225`
- `dayl(s)` min: `31477.75`
- `dayl(s)` max: `54922.24`
- `dayl(s)` mean: `43194.88601551802`

Static parquet inspection of
`/wc1/runs/in/indispensable-presenter/climate/wepp_cli.parquet` showed:

- `rad` min: `21.0`
- `rad` max: `989.0`
- `rad` mean: `419.96074851665907`

The top source rows were:

| year | yday | dayl(s) | srad(W/m^2) | srad(l/day) |
|------|------|---------|-------------|-------------|
| 1991 | 139 | 52784.79 | 784.09 | 989.1975619287764 |
| 1993 | 130 | 51603.21 | 793.79 | 979.0179751422332 |
| 1991 | 121 | 50252.01 | 812.36 | 975.6864921892939 |
| 1991 | 136 | 52412.71 | 772.50 | 967.7059856642928 |
| 1990 | 154 | 54246.54 | 738.58 | 957.5862691405354 |

The top generated CLI rows were:

| day | month | year | julian | rad |
|-----|-------|------|--------|-----|
| 19 | 5 | 1991 | 139 | 989.0 |
| 10 | 5 | 1993 | 130 | 979.0 |
| 1 | 5 | 1991 | 121 | 976.0 |
| 16 | 5 | 1991 | 136 | 968.0 |
| 3 | 6 | 1990 | 154 | 958.0 |

## Initial Interpretation

The generated CLI `rad` values match the Daymet-derived `srad(l/day)` values
after integer publication rounding. That makes the first investigation target
the Daymet radiation conversion and applicable physical/domain bound, not
CLIGEN stochastic generation.

This artifact does not prove whether the defect is in WEPPpy conversion,
upstream Daymet source values, or openWEPP's bound. The package must establish
that ownership before implementing a fix.
