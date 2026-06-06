# Execution Evidence

**Evidence mode**: Static local artifact inspection + targeted test execution
**Captured**: 2026-06-06 21:03 UTC
**Package**: `20260606_indispensable_presenter_daymet_radiation_bounds`

## Mechanism and Ownership

Ownership is WEPPpy producer-boundary normalization for observed-Daymet climate
publication.

The source chain is:

1. `wepppy.climates.daymet.retrieve_historical_timeseries(...)` returns
   Daymet-derived `srad(l/day)`.
2. `wepppy/nodb/core/climate_build_helpers.py::build_observed_daymet` writes
   the source dataframe to `daymet_<start>-<end>.parquet`.
3. CLIGEN generates a base observed CLI.
4. WEPPpy replaces CLI `rad` with Daymet `srad(l/day)`.
5. openWEPP rejects rows where generated `rad` exceeds baseline `sunmap.r3`.

The unit conversion itself is not the defect for the single-location path:
Daymet `srad(W/m^2)` is daylight-average flux and WEPPpy computes daily
Langleys as `srad * dayl / 41840`. The defect is that genuine Daymet source
values can exceed the baseline daily top-of-atmosphere horizontal potential used
by downstream WEPP/openWEPP radiation physics.

## Baseline Bound

The implemented bound is baseline `sunmap.r3` horizontal daily potential in
Langleys/day:

- solar constant: `1.94 Ly min^-1`
- inputs: day-of-year and CLI latitude
- provenance: openWEPP `SC-CLIMATE-001#INV-CLIMATE-013` and baseline
  `sunmap` lineage

For the downstream WBVAL03 blocker:

- date: `1990-02-18`
- CLI latitude: `43.73`
- original Daymet-derived source value: `486.398513 Ly/day`
- generated rounded CLI `rad`: `486 Ly/day`
- baseline `sunmap.r3` bound: `453.068716 Ly/day`
- normalized publication-safe value before CLI publication: `453 Ly/day`
- generated rounded CLI `rad` after normalization: `453 Ly/day`

Post-close rebuild verification on `2026-06-06` showed that exact fractional
`sunmap.r3` normalization was not sufficient for every row because
`ClimateFile.replace_var()` serializes CLI `rad` as an integer. The corrected
publication rule preserves exact `sunmap.r3` in `srad_toa_bound(l/day)` and
publishes `srad_toa_publication_bound(l/day)`, the largest integer L/day value
that remains below the exact bound.

Current rebuilt-run verification:

- artifact timestamp: `2026-06-06 14:19` local filesystem time
- current `daymet_1990-1995.parquet` normalized rows: `53`
- current `wepp.cli` / `wepp_cli.parquet` rows above exact `sunmap.r3` after
  integer publication: `22`
- maximum current published excess: `0.437451 Ly/day`
- repaired-helper simulation against the same source artifact: `0` published
  exceedances, maximum simulated excess `-0.000292877 Ly/day`
- conclusion: the current rebuilt run is not yet openWEPP-clean; rebuild the
  climate once more after the publication-safe producer fix.

## Real-Run Validation

Command:

    .venv/bin/python - <<'PY'
    from pathlib import Path
    import pandas as pd
    from wepppy.climates.cligen import ClimateFile
    from wepppy.nodb.core.climate_build_helpers import _normalize_daymet_radiation_to_toa_bound
    root = Path('/wc1/runs/in/indispensable-presenter/climate')
    df = pd.read_parquet(root / 'daymet_1990-1995.parquet')
    cli = ClimateFile(str(root / 'wepp.cli'))
    result = _normalize_daymet_radiation_to_toa_bound(
        df,
        latitude_deg=cli.lat,
        cli_dir='/tmp',
        artifact_label='indispensable_presenter',
    )
    post_excess = (result.normalized_values - df['srad_toa_bound(l/day)']).max()
    print('cli_lat', cli.lat)
    print('affected_count', result.affected_count)
    print('artifact_path', result.artifact_path)
    print('original_max', df['srad_source(l/day)'].max())
    print('normalized_max', result.normalized_values.max())
    print('post_excess_max', post_excess)
    print(pd.read_csv(result.artifact_path).head(10).to_string(index=False))
    PY

Result summary:

- `cli_lat`: `43.73`
- `affected_count`: `53`
- `artifact_path`:
  `/tmp/daymet_radiation_toa_normalization_indispensable_presenter.csv`
- `original_max`: `989.1975619287764`
- `normalized_max`: `957.5862694359464`
- `post_excess_max`: `0.0`

The command emitted host Redis authentication warnings while importing WEPPpy
NoDb modules, then completed successfully and wrote the temp provenance CSV.

First affected rows:

| date | year | julian | original_srad_l_day | toa_bound_l_day | normalized_srad_l_day | excess_l_day |
|---|---:|---:|---:|---:|---:|---:|
| 1990-02-18 | 1990 | 49 | 486.398513 | 453.068716 | 453.068716 | 33.329797 |
| 1990-02-19 | 1990 | 50 | 502.729494 | 458.706289 | 458.706289 | 44.023205 |
| 1990-02-20 | 1990 | 51 | 508.236181 | 464.403132 | 464.403132 | 43.833050 |
| 1990-02-24 | 1990 | 55 | 499.076201 | 487.742694 | 487.742694 | 11.333507 |
| 1990-02-25 | 1990 | 56 | 506.258626 | 493.705219 | 493.705219 | 12.553407 |

## Implementation

Production changes:

- `wepppy/nodb/core/climate_build_helpers.py`
  - added baseline `sunmap.r3` bound helper,
  - added observed-Daymet radiation normalization helper,
  - applied normalization in `build_observed_daymet`,
  - applied normalization in `build_observed_daymet_interpolated`.

ADR:

- `docs/adrs/ADR-0006-observed-daymet-radiation-toa-normalization.md`

Regression tests:

- `tests/nodb/test_climate_build_helpers.py`
  - validates the `1990-02-18` bound,
  - validates over-TOA row normalization and provenance CSV,
  - validates fractional-bound CLI publication does not round above
    `sunmap.r3`,
  - validates `build_observed_daymet()` publishes bounded CLI `rad`,
  - validates `build_observed_daymet_interpolated()` publishes bounded CLI
    `rad` and persists parquet provenance.

## Validation Commands

Focused helper suite:

    wctl run-pytest tests/nodb/test_climate_build_helpers.py --maxfail=1

Result:

- `20 passed`

Additional focused climate suites:

    wctl run-pytest tests/nodb/test_climate_artifact_export_service.py tests/climate/test_cligen_peak_intensity_contract.py tests/nodb/test_climate_build_router_services.py tests/nodb/test_user_defined_cli_parquet.py --maxfail=1

Result:

- `29 passed`

Documentation validation:

    wctl doc-lint --path docs/work-packages/20260606_indispensable_presenter_daymet_radiation_bounds --path docs/adrs/ADR-0006-observed-daymet-radiation-toa-normalization.md --path docs/adrs/README.md --path PROJECT_TRACKER.md

Result:

- `8 files validated, 0 errors, 0 warnings`
