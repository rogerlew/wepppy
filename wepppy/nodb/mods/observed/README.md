# Observed Controller
> Observed NoDb controller for model-fit statistics between observed CSV time series and WEPP outputs.
> **See also:** `../../../../AGENTS.md` and `../../../../wepppy/weppcloud/controllers_js/README.md#observed-controller-reference-2025-helper-migration`

## Overview
- Parses observed CSV text (`Date` + measures) into a normalized `observed.csv` with year/month/day/julian fields.
- Loads WEPP interchange outputs to compute daily/yearly model-fit statistics for hillslopes and channels.
- Persists results in `observed.nodb`, writes comparison CSVs under `<run>/observed/`, and exposes report/plot routes.

## Data Flow
1. `parse_textdata(textdata)` reads CSV, parses dates, and writes `<run>/observed/observed.csv`.
2. `calc_model_fit()` loads hillslope + channel simulations and runs metrics:
   - Hillslopes: `wepp/output/interchange/totalwatsed3.parquet` (reused if present).
   - Channels: `wepp/output/ebe_pw0.txt` + `wepp/output/chanwb.out`.
3. Outputs are written to `<run>/observed/` and summarized in `observed.nodb`.

## Outputs
- `observed/observed.csv` (normalized input with `Year`, `Month`, `Day`, `Julian`).
- `observed/Hillslopes-<Measure>-Daily.csv`, `observed/Channels-<Measure>-Yearly.csv`, etc.
- `observed.log` (timing logs, status stream).
- `observed.nodb` (results payload).

## UI Wiring
- Control template: `wepppy/weppcloud/templates/controls/observed_pure.htm`.
- Controller: `wepppy/weppcloud/controllers_js/observed.js`.
  - On page load, the summary pane shows “View Model Fit Results” when `observed.hasResults` is true.
  - Status stream uses channel `observed` (`controlBase.attach_status_stream`).
- Report: `/runs/<runid>/<config>/report/observed/` (Pure report template).
- Plot: `/runs/<runid>/<config>/plot/observed/<selected>/` (legacy D3 v3 graph).

## Endpoints
| Route | Method | Purpose |
| --- | --- | --- |
| `/runs/<runid>/<config>/tasks/run_model_fit` | POST | Parse CSV + run model fit (sync) |
| `/runs/<runid>/<config>/report/observed/` | GET | Render observed summary report |
| `/runs/<runid>/<config>/plot/observed/<selected>/` | GET | Render comparison graph |
| `/runs/<runid>/<config>/resources/observed/<file>` | GET | Download CSV artifacts |

## Profiling Notes (Dec 2025)
Measured on test run `/wc1/runs/un/unpresidential-shabbiness` with `tests/data/observed/CedarRv_WA.csv`:
- Before refactor (rebuilding interchange): `parse_textdata ~5s`, `calc_model_fit ~75s` (hillslope load ~72s).
- After reuse of `totalwatsed3.parquet` + parallel stats: `parse_textdata ~5s`, `calc_model_fit ~2.2s`.
Times depend on cache state and machine I/O; use `observed.log` for per-step timings.

## Test Data & Reference Run
- Observed CSV fixture: `tests/data/observed/CedarRv_WA.csv`.
- Reference run: `https://wc.bearhive.duckdns.org/weppcloud/runs/unpresidential-shabbiness/disturbed9002/`
  - Run directory: `/wc1/runs/un/unpresidential-shabbiness`
  - Config: `disturbed9002`
- Note: running the observed regression test overwrites `<run>/observed/` outputs and updates `observed.nodb`.

## Tests
```bash
wctl run-pytest tests/nodb/mods/test_observed_processing.py
wctl run-pytest tests/weppcloud/routes/test_observed_bp.py
wctl run-npm test -- observed
```

## Implementation Notes
- `parse_textdata` uses pandas with the `pyarrow` CSV engine and in-reader date parsing.
- `calc_model_fit` runs hillslope stats in parallel with channel load + stats.
- The observed model fit remains synchronous (not RQ); large runs can still block the request thread.
