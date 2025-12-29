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

## Notes
- Requires `CLIMATE_ENGINE_API_KEY`.
- Only observed climate modes are supported.
