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

## GL Dashboard Query Payloads
OpenET overlays and graphs in the gl-dashboard issue Query Engine payloads
against `openet/openet_ts.parquet`. The UI always uses the base scenario
query engine for OpenET.

### Monthly overlay summary (map colors)
Returns a single month of ET values per hillslope for the selected dataset.
Source: `wepppy/weppcloud/static/js/gl-dashboard/data/openet-data.js`.

```json
{
  "datasets": [{ "path": "openet/openet_ts.parquet", "alias": "openet" }],
  "columns": ["openet.topaz_id AS topaz_id", "openet.value AS value"],
  "filters": [
    { "column": "openet.dataset_key", "op": "=", "value": "<dataset_key>" },
    { "column": "openet.year", "op": "=", "value": "<year>" },
    { "column": "openet.month", "op": "=", "value": "<month>" }
  ]
}
```

### Overlay detection (dataset keys)
Discovers which OpenET dataset keys are present in the parquet.
Source: `wepppy/weppcloud/static/js/gl-dashboard/layers/detector.js`.

```json
{
  "datasets": [{ "path": "openet/openet_ts.parquet", "alias": "openet" }],
  "columns": ["DISTINCT openet.dataset_key AS dataset_key"],
  "order_by": ["dataset_key"]
}
```

### Overlay detection (month list)
Discovers available month/year combinations for the month slider.
Source: `wepppy/weppcloud/static/js/gl-dashboard/layers/detector.js`.

```json
{
  "datasets": [{ "path": "openet/openet_ts.parquet", "alias": "openet" }],
  "columns": ["DISTINCT openet.year AS year", "openet.month AS month"],
  "order_by": ["year", "month"]
}
```

### Monthly timeseries graph (per hillslope)
Loads full monthly series per hillslope for the selected dataset.
Source: `wepppy/weppcloud/static/js/gl-dashboard/graphs/graph-loaders.js`.

```json
{
  "datasets": [{ "path": "openet/openet_ts.parquet", "alias": "openet" }],
  "columns": [
    "openet.topaz_id AS topaz_id",
    "openet.year AS year",
    "openet.month AS month",
    "openet.value AS value"
  ],
  "filters": [{ "column": "openet.dataset_key", "op": "=", "value": "<dataset_key>" }],
  "order_by": ["year", "month"]
}
```

### Yearly graph (area-weighted)
Aggregates ET using hillslope area to build water-year or calendar-year curves.
Source: `wepppy/weppcloud/static/js/gl-dashboard/graphs/graph-loaders.js`.

```json
{
  "datasets": [
    { "path": "openet/openet_ts.parquet", "alias": "openet" },
    { "path": "watershed/hillslopes.parquet", "alias": "hill" }
  ],
  "joins": [{ "left": "openet", "right": "hill", "on": "topaz_id", "type": "inner" }],
  "columns": ["openet.year AS year", "openet.month AS month"],
  "aggregations": [{ "expression": "SUM(openet.value * hill.area)", "alias": "area_weighted" }],
  "filters": [{ "column": "openet.dataset_key", "op": "=", "value": "<dataset_key>" }],
  "group_by": ["openet.year", "openet.month"],
  "order_by": ["year", "month"]
}
```

## Notes
- Requires `CLIMATE_ENGINE_API_KEY`.
- Only observed climate modes are supported.
