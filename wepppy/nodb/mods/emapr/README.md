# OSU eMapR Time Series (`emapr_ts`) NoDb Mod

> Downloads Oregon State eMapR raster products for a run extent and aggregates them into a per-subcatchment time series persisted in NoDb.

> **See also:** [AGENTS.md](../../AGENTS.md) for NoDb locking/persistence conventions and debugging hooks.

## Overview

This module implements the optional NoDb controller `OSUeMapR_TS` (`wepppy.nodb.mods.OSUeMapR_TS`). When enabled, it:

- Clips OSU eMapR GeoTIFF layers (biomass, canopy, landcover vote, plus uncertainty layers) to the run’s map extent.
- Aggregates each raster by TOPAZ subcatchment ID (from the watershed `subwta` raster).
- Persists the resulting time series into `<run>/emapr_ts.nodb` for later consumption.

This mod is currently wired to run during WEPP preparation (see **Integration points**); it is not a web route/controller by itself.

## Workflow

`OSUeMapR_TS` is a two-phase pipeline:

1. **Acquire rasters** (`acquire_rasters(start_year, end_year)`)
   - Reads the run bounding box from `Ron.getInstance(wd).map.extent`.
   - Uses `wepppy.landcover.emapr.OSUeMapR` to download/crop rasters into `<run>/emapr/` via `gdalwarp` (GDAL `/vsicurl`).
2. **Analyze / aggregate** (`analyze()`)
   - Loads the watershed subcatchment raster from `Watershed.getInstance(wd).subwta`.
   - For each `year` and each `(measure, statistic)` layer, computes a masked **median** value over pixels inside each subcatchment ID.
   - Writes the nested results to `self.data` and persists to `<run>/emapr_ts.nodb`.

### Prerequisites

Before running `acquire_rasters()` / `analyze()` the run directory must already have:

- A `Ron` controller with a populated `map.extent` bounding box (expected order: `[min_lon, min_lat, max_lon, max_lat]`).
- A `Watershed` controller with a materialized `subwta` raster on disk.

## Outputs / Artifacts

### Persisted NoDb state

- `<run>/emapr_ts.nodb`
  - `emapr_start_year` / `emapr_end_year`: inclusive year range.
  - `data`: nested mapping described below.

### Downloaded rasters

- `<run>/emapr/`
  - One GeoTIFF per `(year, measure, statistic)` named:
    - `_emapr_v1_<measure>_<statistic>_<year>.tif`

The number of rasters scales with the year span: `num_years * len(OSUeMapR_Measures)`.

## Data shape

After `analyze()`, `OSUeMapR_TS.data` has this structure:

```text
data[topaz_id: str][year: int][(measure: str, statistic: str)] -> float | None
```

Notes:

- `topaz_id` keys are strings (they come from the `subwta` raster IDs).
- Values are medians of raster pixels within the subcatchment mask; missing/fully-masked areas yield `None`.
- `(measure, statistic)` is one of `wepppy.landcover.emapr.OSUeMapR_Measures`, for example:
  - `("biomass", "median")`, `("canopy", "mean")`, `("landcover", "vote")`.

## Quick start / Examples

### Manual run (Python)

```python
from wepppy.nodb.mods import OSUeMapR_TS

wd = "/wc1/runs/<runid>"  # run working directory

emapr_ts = OSUeMapR_TS.getInstance(wd)
emapr_ts.acquire_rasters(start_year=2001, end_year=2010)
emapr_ts.analyze()

# Example: read a single value
topaz_id = "1"
year = 2010
value = emapr_ts.data[topaz_id][year][("canopy", "mean")]
print(value)
```

### Enable in a config (typical pipeline path)

`NoDbBase.mods` is loaded from the config’s `[nodb]` section. To run this mod as part of WEPP prep, include `emapr_ts` in `mods`, for example:

```ini
[nodb]
mods = ["emapr_ts"]
```

When enabled, `wepppy.nodb.core.wepp_prep_service.WeppPrepService` calls `acquire_rasters()` and `analyze()` using the run’s observed climate year range.

## Integration points

- **Invoked by**: `wepppy/nodb/core/wepp_prep_service.py` when `"emapr_ts" in wepp.mods`.
- **Depends on**:
  - `wepppy.landcover.emapr.OSUeMapR` (download + crop orchestration)
  - `Ron` (`map.extent`) and `Watershed` (`subwta`) NoDb controllers
  - GDAL Python bindings (`osgeo.gdal`) and the `gdalwarp` CLI available on `PATH`
- **Remote source**: eMapR VRTs fetched via GDAL `/vsicurl` from `https://wepp.cloud/geodata/emapr/...` (network required).

## Developer notes

- Locking/persistence: `OSUeMapR_TS.acquire_rasters()` and `OSUeMapR_TS.analyze()` both run inside `with self.locked():` and therefore persist on success (see `NoDbBase.locked()` in `wepppy/nodb/base.py`).
- `OSUeMapR_TS.__init__` creates `<run>/emapr/` with `os.mkdir()` (no `exist_ok=True`); re-initializing against an existing run directory may raise if the folder already exists.
- `OSUeMapR_TS.on(...)` is currently a no-op; this mod is activated via explicit calls rather than `TriggerEvents`.
- Failure modes to keep in mind:
  - `analyze()` asserts `Watershed.subwta` exists and that raster shapes match the downloaded rasters.
  - `gdalwarp` execution is time-limited (see `OSUeMapR.retrieve()`); slow networks can fail downloads.

## Further reading

- Dataset acquisition helpers: `wepppy/landcover/emapr/oregonstate_emapr.py`
- Invocation site: `wepppy/nodb/core/wepp_prep_service.py`
- NoDb base contracts: `wepppy/nodb/base.py` and [AGENTS.md](../../AGENTS.md)

