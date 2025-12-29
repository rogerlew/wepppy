# OpenET Climate Engine NoDb Mod - Spec + Plan

## Goals
- Acquire monthly OpenET ET time series for each TOPAZ hillslope polygon using Climate Engine.
- Mirror RAP_TS style: cache per-hillslope results, then write a combined parquet for analytics.
- Key sources: `OPENET_CONUS` measures `et_ensemble_mad` and `et_eemetric` (monthly).

## Non-Goals
- No UI work yet (new controllers, reports).
- No OpenET openet-api.org integration (use Climate Engine only).
- No stochastic climate support (observed only).

## Inputs / Dependencies
- ClimateEngine API key: `CLIMATE_ENGINE_API_KEY` (already in `docker/.env`).
- Climate date range: `Climate.observed_start_year` / `Climate.observed_end_year`.
  - Fail fast if climate mode is stochastic or missing observed years.
- Geometry source: `Watershed.subwta_shp` (WGS GeoJSON from Topaz/WBT/TauDEM).
  - Use `TopazID` (or `topaz_id`) property to label hillslopes.
  - Skip channel IDs (suffix `4`) to match other hillslope-only mods.

## Data Sources
Climate Engine timeseries endpoint (see `climate-engine-timeseries-doc.md`):
- `https://api.climateengine.org/timeseries/native/coordinates`
- Required params: `dataset`, `variable`, `start_date`, `end_date`, `coordinates`, `area_reducer`.
- Payload format mirrors `oce-et-downloader/ag_fields_timeseries_api.py`:
  - `dataset` = OpenET dataset id.
  - `variable` = ET variable (per dataset).
  - `coordinates` = JSON-encoded GeoJSON polygon coordinates.
  - `area_reducer` = `median` (match example client).

## Target Dataset + Measures
Primary Climate Engine dataset:

- Dataset ID: `OPENET_CONUS` (Climate Engine identifier)
- Primary measures (core):
  - `et_ensemble_mad` (mm) - Ensemble median after MAD outlier filtering
  - `et_eemetric` (mm) - eeMETRIC model
- Additional measures (optional):
  - `et_ssebop`, `et_sims`, `et_geesebal`, `et_ptjpl`, `et_disalexi`
  - `et_ensemble_mad_min`, `et_ensemble_mad_max`
- Units: mm/month
- Temporal resolution: Monthly (pre-aggregated)

**Data Availability:** October 1999 - December 2024
**Spatial Resolution:** 30-meter pixels
**Coverage:** CONUS (Continental United States)

## Expected Response Shape (from Climate Engine API)
`payload["Data"][0]["Data"]` -> list of rows:
```
{"Date": "YYYY-MM-DD", "et_ensemble_mad (mm)": <float>, ...}  # ensemble
{"Date": "YYYY-MM-DD", "et_eemetric (mm)": <float>, ...}      # eeMETRIC
```
Notes:
- Some dates may return `-9999` (no-data sentinel value).
- Response contains monthly values (one row per month in date range).
- Response keys include units (e.g., `et_ensemble_mad (mm)`), so parsing should match by prefix.
- For Ensemble: use `et_ensemble_mad` variable (primary).
- For eeMETRIC: use `et_eemetric` variable (primary).

## Storage Layout (implemented)
- Working dir: `<wd>/openet/`
  - `openet_ts.nodb` (NoDb state)
  - `individual/<dataset_key>/<topaz_id>.parquet` (per-hillslope cache)
  - `openet_ts.parquet` (combined monthly time series)

## Combined Parquet Schema (proposed)
- `topaz_id` (string)
- `year` (int)
- `month` (int)
- `dataset_key` (string; `ensemble`, `eemetric`)
- `dataset_id` (string; Climate Engine dataset id)
- `value` (float; ET)
- `units` (string; if provided by API, else `mm`)
- `source` (string; `climateengine`)

## Aggregation Rules
Since both datasets are **already monthly** (pre-aggregated):
- Parse `Date` field (format: `YYYY-MM-DD`) to extract `year` and `month`.
- Keep ET values as-is (no temporal aggregation needed).
- Filter out no-data values (`-9999` or similar sentinels).
- Round to 4 decimals for stability and consistency with other mods.
- Store with dataset metadata (dataset_key, dataset_id, units).

## Error Handling + Retry
- Requests with retry/backoff for transient errors.
- Parallel fetches with `ThreadPoolExecutor`.
- Log failures per hillslope; continue run; emit summary of failures.
- Fail fast for missing `CLIMATE_ENGINE_API_KEY`, missing geometry, or unsupported climate mode.
- Do not silently ignore missing dependencies (raise ImportError if pandas/pyarrow missing).

## NoDb Integration
- New module path: `wepppy/nodb/mods/openet/openet_ts.py`.
- `__all__` must include public class + exception.
- Register mod in `wepppy/nodb/mods/openet/__init__.py` and ensure lazy import works.
- Add `openet_ts.pyi` stub and sync with implementation.
- Add new `TaskEnum` entry (e.g., `fetch_openet_ts`) and wire into `RedisPrep` + `batch_runner`.
- Update `wepppy/nodb/core/wepp.py` only if OpenET is needed for WEPP runs.

## Implementation Plan (Checklist)
- [x] **Phase 0 smoke test** (`smoke_climate_engine_openet.py`)
  - Validate API key, dataset availability, and polygon retrieval.
  - Confirm response shape, units suffix, and no-data handling.
- [x] **Constants + mappings**
  - Dataset id: `OPENET_CONUS`
  - Variables: `et_ensemble_mad`, `et_eemetric`
- [x] **Scaffold mod**
  - `openet_ts.py`, `__init__.py`, `README.md`, `openet_ts.pyi`
- [x] **Geometry loader**
  - Parse `Watershed.subwta_shp`, drop channels, normalize TOPAZ ids.
- [x] **Climate guardrails**
  - Observed-only modes; years must be set and consistent.
- [x] **Acquisition pipeline**
  - Parallel requests with retry/backoff.
  - Per-hillslope parquet cache, skip cached hillslopes when years unchanged.
- [x] **Parquet assembly**
  - Normalize date, filter `-9999`, round to 4 decimals.
  - Write `openet/openet_ts.parquet` and update catalog entry.
- [x] **Redis + Task enum**
  - `fetch_openet_ts` added to `TaskEnum` + labels/icons.
- [x] **Tests**
  - Unit tests for parsing, no-data filtering, and channel skipping.
- [ ] **Batch runner integration**
  - Wire into `batch_runner` (pending).
- [ ] **Preflight integration**
  - Hook into preflight/task readiness UX (pending).

## Verification Checklist
- Climate observed start/end years line up with output.
- Combined parquet covers all hillslopes and both datasets.
- Missing data is handled (`-9999` -> NA) without crashing.
- Retry behavior logs failures and continues.
- Phase 0 smoke test returns valid time series rows for both datasets.
