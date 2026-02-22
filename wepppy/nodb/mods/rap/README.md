# RAP NoDb Mods (Rangeland Analysis Platform)

> Retrieves and summarizes RAP fractional cover rasters for WEPPcloud scenarios, both as a single-year snapshot and as a multi-year time series.

> **See also:** [AGENTS.md](../../AGENTS.md) for NoDb locking/serialization/cache expectations.

## Overview

This directory contains two NoDb controllers that integrate the **Rangeland Analysis Platform (RAP) V3** fractional cover products into the WEPPpy/WEPPcloud run lifecycle:

- `RAP` (`rap.py`): downloads a single RAP year, summarizes each fractional cover band to TOPAZ hillslopes (and optionally to multi-OFE footprints), and exposes the result to downstream mods (for example, Landuse and Rangeland Cover).
- `RAP_TS` (`rap_ts.py`): orchestrates RAP downloads and summarization across a year range, persists a time-series dataset (optionally in Parquet), and can generate time-varying `.cov` cover files for WEPP runs (including revegetation transforms when enabled).

Both controllers rely on prior run setup:

- `Ron` provides the map extent (and cell size for time-series retrieval).
- `Watershed` provides abstraction rasters (for example, `subwta`, and optionally `mofe_map`) that define the aggregation keys used when summarizing RAP rasters.

## Workflow

### Single-year workflow (`RAP`)

1. **Acquire rasters**: `RAP.acquire_rasters(year)` uses the current `Ron` map extent to download RAP data into `<wd>/rap/` via `RangelandAnalysisPlatformV3.retrieve`.
2. **Analyze**: `RAP.analyze()` summarizes each RAP band to TOPAZ hillslopes using `Watershed.subwta` as the key raster.
   - If `multi_ofe` is enabled, it also summarizes by `(topaz_id, mofe_id)` using `Watershed.mofe_map`.
3. **Consume**:
   - `RAP.data` / `RAP.mofe_data` store per-band summaries.
   - `RAP.report` computes watershed-wide spatial statistics (per band) for UI dashboards.
   - Iteration yields `(topaz_id, RAPPointData)` rows for convenient per-hillslope access.

### Time-series workflow (`RAP_TS`)

1. **Choose the year range**: set `rap_start_year` and `rap_end_year` (often derived from observed climate years).
2. **Acquire rasters**: `RAP_TS.acquire_rasters(start_year=..., end_year=...)` downloads RAP datasets for each year in the range (threaded).
3. **Analyze**: `RAP_TS.analyze()` summarizes all `(year, band)` combinations to hillslopes (and optionally multi-OFE), producing `RAP_TS.data`.
   - If `pandas` and `pyarrow` are available, the analysis result is also written to `<wd>/rap/rap_ts.parquet` for faster load times and to avoid bloating `rap_ts.nodb`.
4. **Consume**:
   - `RAP_TS.get_cover(topaz_id, year)` returns a canopy-style cover metric (sum of selected vegetation bands) for a given hillslope/year.
   - Iteration yields `(topaz_id, RAPPointData)` for a single “reference year” when `multi_ofe` is **not** enabled (prefers `rap_end_year` when present).
   - `RAP_TS.prep_cover(runs_dir)` writes per-hillslope `.cov` files that WEPP consumes; when Disturbed + Revegetation metadata are present it applies burn-class/year transforms.

## Artifacts and persistence

All artifacts are stored under the scenario working directory (`<wd>`).

| Artifact | Location | Produced by | Purpose |
|---|---|---|---|
| NoDb state | `<wd>/rap.nodb` | `RAP` | Tracks the controller state and (for `RAP`) the summarized band data. |
| NoDb state | `<wd>/rap_ts.nodb` | `RAP_TS` | Tracks controller metadata (years, etc.). When Parquet exists, `data` is intentionally omitted from the serialized state. |
| RAP working directory | `<wd>/rap/` | both | Stores RAP rasters and derived artifacts. |
| Time-series parquet | `<wd>/rap/rap_ts.parquet` | `RAP_TS.analyze()` | Flat time-series table used for faster hydration and downstream analytics. |
| WEPP cover files | `<runs_dir>/p<wepp_id>.cov` | `RAP_TS.prep_cover()` | Time-varying cover inputs for WEPP runs (one file per hillslope). |
| Sentinels | `<runs_dir>/cancov.txt`, `<runs_dir>/simfire.txt` | `RAP_TS.prep_cover()` | Empty “presence” files used by downstream tooling; `simfire.txt` is written when transformed cover is used. |

Both controllers call `update_catalog_entry(...)` after acquiring rasters (and after writing Parquet) so the query engine/file catalog can surface RAP artifacts in the UI.

## Quick start / examples

These examples assume you already have a scenario working directory (`wd`) with `Ron` configured and the watershed abstracted (so `Watershed.subwta` exists).

### Single-year RAP summary

```python
from wepppy.nodb.mods.rap import RAP
from wepppy.landcover.rap import RAP_Band

wd = "/path/to/scenario"

rap = RAP.getInstance(wd)
rap.acquire_rasters(year=2019)
rap.analyze()

# Per-hillslope access
tree_by_topaz = rap.data[RAP_Band.TREE]
print("tree cover for TOPAZ 101:", tree_by_topaz["101"])

# Convenience iterator and normalized values
for topaz_id, point in rap:
    if point.isvalid:
        print(topaz_id, point.tree, point.tree_normalized)
```

### Time-series RAP summary and `.cov` export

```python
from wepppy.nodb.mods.rap import RAP_TS

wd = "/path/to/scenario"
runs_dir = f"{wd}/runs"  # or `WEPP.runs_dir` for the scenario

rap_ts = RAP_TS.getInstance(wd)
rap_ts.rap_start_year = 2001
rap_ts.rap_end_year = 2020

rap_ts.acquire_rasters()  # uses rap_start_year/rap_end_year already set
rap_ts.analyze()

# Write WEPP cover inputs (uses revegetation transforms when configured)
rap_ts.prep_cover(runs_dir)
```

### Dashboard-style spatial stats (`RAP.report`)

```python
from wepppy.nodb.mods.rap import RAP

wd = "/path/to/scenario"
rap = RAP.getInstance(wd)

# Dict keyed by band display name, each value is a stats dict.
stats = rap.report
print(stats)
```

## Key concepts and data model

### RAP bands

RAP data is represented with the `RAP_Band` enum (from `wepppy.landcover.rap`). The controllers summarize the following bands:

- `ANNUAL_FORB_AND_GRASS`
- `BARE_GROUND`
- `LITTER`
- `PERENNIAL_FORB_AND_GRASS`
- `SHRUB`
- `TREE`

### Summaries (`data` / `mofe_data`)

`RAP` stores per-band summaries as:

- `data[band][topaz_id] -> value`
- when `multi_ofe` is enabled: `mofe_data[band][topaz_id][mofe_id] -> value`

`RAP_TS` stores time-series summaries as:

- `data[band][year][topaz_id] -> value`
- when `multi_ofe` is enabled: `data[band][year][topaz_id][mofe_id] -> value`

`RAPPointData` is a convenience wrapper for a single hillslope’s band values. It exposes:

- Raw band attributes (for example, `tree`, `shrub`, `bare_ground`).
- `total_cover` and per-band `*_normalized` properties (percent of total cover).
- `isvalid` to indicate all bands are present.

## Integration points

- **Depends on**:
  - `wepppy.nodb.core.Ron` for `map.extent` (and `map.cellsize` for `RAP_TS` retrieval setup).
  - `wepppy.nodb.core.Watershed` for `subwta`, optional `mofe_map`, `bound`, and the hillslope translator used by `.cov` generation.
- **Used by**:
  - `wepppy.nodb.core.landuse.Landuse.build()` when `'rap'` is enabled in the mods list (single-year RAP is used to derive canopy cover defaults).
  - `wepppy.nodb.mods.rangeland_cover` (gridded RAP mode, and dashboards via `rap_report`).
  - `wepppy.nodb.core.wepp.WEPP._prep_revegetation()` which calls `RAP_TS.prep_cover(...)` during revegetation preparation.
  - RQ jobs (for example, `wepppy.rq.project_rq.fetch_and_analyze_rap_ts_rq`) to fetch/analyze RAP time series in the background.
- **Task timestamps**:
  - `RAP_TS.analyze()` attempts `RedisPrep.timestamp(TaskEnum.fetch_rap_ts)` (it no-ops when Redis prep state is unavailable).

## Developer notes

- **Serialization compatibility**:
  - `RAP._post_instance_loaded()` remaps serialized `data`/`mofe_data` keys back onto `RAP_Band` so callers can use enum keys consistently.
  - `RAP_TS._post_instance_loaded()` supports three cases: hydrate from Parquet (preferred), map older `.nodb` layouts, or leave `data` unset.
- **Parquet dependency behavior**:
  - If `<wd>/rap/rap_ts.parquet` exists and `pandas`/`pyarrow` are unavailable, `RAP_TS` raises an `ImportError` during load to avoid silently returning partial data.
- **Concurrency**:
  - `RAP_TS.acquire_rasters()` and `RAP_TS.analyze()` use a `ThreadPoolExecutor` and cancel remaining work on first failure; errors propagate to the caller.

## Further reading

- `wepppy/landcover/rap.py` (RAP dataset manager, bands, and dataset I/O)
- `wepppy/nodb/core/landuse.py` (how RAP drives cover defaults during landuse build)
- `wepppy/nodb/mods/rangeland_cover/rangeland_cover.py` (how RAPPointData is used to derive cover components)
- `wepppy/rq/project_rq.py` (background job orchestration for RAP time series)
