# OpenET Climate Engine Mod
> Monthly OpenET evapotranspiration time series for WEPPcloud hillslopes.
> **See also:** `wepppy/nodb/mods/openet/spec-and-plan.md`

## Overview
This module queries Climate Engine's `OPENET_CONUS` dataset to retrieve
monthly ET for each hillslope polygon. Results are cached per hillslope and
assembled into a single parquet for analytics and dashboards.

## Usage
```python
from wepppy.nodb.mods.openet import OpenET_TS

openet_ts = OpenET_TS.getInstance(wd)
openet_ts.acquire_timeseries()
openet_ts.analyze()
```

## Outputs
- `openet/individual/<dataset_key>/<topaz_id>.parquet` (per-hillslope cache)
- `openet/openet_ts.parquet` (combined monthly time series)

## Layers
OpenET drives a gl-dashboard map overlay when `openet/openet_ts.parquet` is present.

- The Layers control shows an OpenET section only when the parquet exists.
- Each `dataset_key` becomes a radio option (for example, `ensemble`, `eemetric`).
- OpenET uses the monthly time slider; the yearly slider is hidden while an OpenET layer is active.

## openet/openet_ts.parquet Specification
Combined monthly OpenET time series aggregated at the hillslope level.
Per-hillslope cache files use the same schema.

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| `topaz_id` | string | - | Hillslope identifier (TopazID) as a string. |
| `year` | int | - | Calendar year of the monthly observation. |
| `month` | int | - | Calendar month (1-12) of the observation. |
| `dataset_key` | string | - | Logical dataset key (currently `ensemble`, `eemetric`). |
| `dataset_id` | string | - | Climate Engine dataset id (`OPENET_CONUS`). |
| `value` | float | `mm` | Monthly evapotranspiration depth. Values are rounded to 4 decimals. |
| `units` | string | - | Unit label reported by Climate Engine (defaults to `mm`). |
| `source` | string | - | Source label (`climateengine`). |

## Notes
- Requires `CLIMATE_ENGINE_API_KEY`.
- Only observed climate modes are supported.
