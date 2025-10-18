# Report Catalog

Quick lookup for report classes under `wepppy.wepp.reports`.

| Report | Purpose | Key datasets | Cache | Exposed via |
| --- | --- | --- | --- | --- |
| `AverageAnnualsByLanduseReport` | Hydrologic + sediment averages per landuse | `loss_pw0.hill.parquet`, `watershed/hillslopes.parquet`, `landuse/landuse.parquet` | `wepp/reports/cache/average_annuals_by_landuse.parquet` | `/wepp` landuse summary download |
| `ChannelWatbalReport` | Channel water balance aggregates by Topaz ID and water year | `chnwb.parquet` | none (computed on demand) | `/wepp` channel balance views |
| `FrqFloodReport` | Flood frequency table derived from event maxima | `ebe_pw0.parquet`, `totalwatsed3.parquet` | none | `/wepp` return-period widgets |
| `HillslopeWatbalReport` | Hillslope-level water balance and watershed totals | `H.wat.parquet` | `wepp/reports/cache/hillslope_watbal_summary.parquet` | `/wepp` hillslope balance views |
| `HillSummaryReport` | Hillslope sediment & hydrology summary plus metadata | `loss_pw0.hill.parquet`, `watershed/hillslopes.parquet`, `landuse/landuse.parquet`, optional `soils/soils.parquet` | none | CSV exports & batch scripts |
| `ChannelSummaryReport` | Channel sediment + flow summary for each reach | `loss_pw0.chn.parquet`, `watershed/channels.parquet` | none | CSV exports & batch scripts |
| `OutletSummaryReport` | Outlet-level delivery metrics and ratios | `loss_pw0.out.parquet` | none | CSV exports & batch scripts |
| `TotalWatbalReport` | Watershed water balance statistics and ratios | `totalwatsed3.parquet` | none | `/wepp` total balance download |
| `ReturnPeriods` | Return-period datasets & refresh utilities | `ebe_pw0.parquet`, `totalwatsed3.parquet`, `return_period_events.parquet` | `return_period_events.parquet` (managed via catalog) | Return-period API + UI |
| `SedimentCharacteristics` | Aggregated sediment class distributions & outlet metrics | class/outlet/hill/pass parquet assets | none | `/wepp` sediment characteristics view |

_Notes_

- All caches now live under `wepp/reports/cache/` and are versioned through
  `ReportCacheManager`.
- Scripts under `_scripts/` use the renamed `*Report` classes via
  `wepppy.wepp.reports`.
- Add new reports by subclassing `ReportBase`, wiring `ReportQueryContext`
  as needed, and documenting them here.
