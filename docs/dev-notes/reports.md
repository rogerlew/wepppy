# Reports Refactor Notes

> **See also:** [AGENTS.md](../../AGENTS.md) for WEPP model file management and validation sections.

This document summarizes the reporting stack that now lives in
`wepppy.wepp.reports`: the `ReportBase` contract, shared helper classes,
the recommended pattern for authoring new reports, and a catalog of the
current report implementations with their data dependencies and cache
behavior.

---

## ReportBase contract

All tabular reports inherit from `wepppy.wepp.reports.report_base.ReportBase`.
Implementations are expected to:

* Populate `self.header` with display column labels.
* Implement `__iter__` to yield `RowData` instances (`row_data.RowData`)
  that expose `(value, units)` pairs.
* Optionally populate `self.units_d` (a mapping of label → units) when
  derived units are not handled automatically.
* Use the base helpers `write()` and `to_dataframe()` for export /
  serialization; both rely on the iterator contract.

`RowData` provides convenience iteration and lookup and still supports
legacy column-name parsing (e.g. extracting units from `"Column (mm)"`)
until parquet metadata is ubiquitous.

---

## Shared helpers

The helpers live in `wepppy.wepp.reports.helpers`.

### ReportQueryContext

```python
context = ReportQueryContext(run_directory, run_interchange=False)
context.ensure_datasets("wepp/output/interchange/file.parquet", ...)
result = context.query(payload)  # payload is a QueryRequest
```

This class wraps the query-engine bootstrap (`activate_query_engine` +
`resolve_run_context`), memoises the DuckDB context, and exposes a simple
catalog interface for presence checks. Tests can monkeypatch the class
with light-weight stubs.

### ReportCacheManager

```python
cache = ReportCacheManager(run_directory)
frame = cache.read_parquet("key", version="1")
cache.write_parquet("key", dataframe, version="1", index=False)
```

Caches are standardized under `<run>/wepp/reports/cache/`. When a version
is supplied, a `key.meta.json` sidecar stores the version string; cache
misses occur automatically when the version differs.

### extract_units_from_schema

Utility for deriving display units from parquet metadata:

```python
units = extract_units_from_schema(schema, {"Precipitation (mm)": "P (mm)"})
```

Pass a mapping of display labels → column name(s); the helper reads the
`b"units"` metadata for each field and falls back to a default.

### ReportHarness

`ReportHarness` (in `wepppy.wepp.reports.harness`) is a simple registry
for collecting report factory callables. The current unit test exercises
it as a smoke harness and it provides a foundation for future integration
tests.

---

## Authoring a new report

1. **Design** – Determine the parquet assets required from the run
   directory and the shape of the resulting table (headers, units).
2. **Bootstrap** – Instantiate `ReportQueryContext` to ensure datasets
   and execute `QueryRequest` instances. If the report does not rely on
   the DuckDB catalog, skip the helper.
3. **Fetch / Build** – Read source data (pandas / pyarrow), perform
   aggregation or transformations, and construct a `pandas.DataFrame`.
   Keep column names presentation-ready so they can be used directly in
   templates.
4. **Cache (optional)** – If the computation is expensive or requires
   substantial aggregation, store results via `ReportCacheManager`.
   Embed a `CACHE_VERSION` to control invalidation when the schema
   changes.
5. **Expose rows** – Set `self.header`, populate other context fields
   (`self.units_d`, `self.areas`, `self.years`, etc.), and yield rows by
   wrapping dictionaries in `RowData`.
6. **Register** – Export the class in `wepppy.wepp.reports.__init__`
   (both the `Report` name and compatibility alias if needed) and update
   call sites.
7. **Tests** – Add a unit test under `tests/wepp/reports/`, mocking
   parquet assets with temporary files or patched contexts. Prefer to
   stub `ReportQueryContext` rather than patching low-level
   query-engine functions.

---

## Report catalog

| Report class | Purpose & aggregation | Input assets | Cache |
| --- | --- | --- | --- |
| `AverageAnnualsByLanduseReport` | Summarizes runoff / flow / sediment metrics per landuse by joining loss, hillslope, and landuse tables; converts volumes to depths (mm) via area normalization. | `wepp/output/interchange/loss_pw0.hill.parquet`, `watershed/hillslopes.parquet`, `landuse/landuse.parquet` | `wepp/reports/cache/average_annuals_by_landuse.parquet` (version `1`) |
| `ChannelWatbalReport` | Aggregates channel water balance metrics (precipitation, streamflow, evapotranspiration, etc.) by `wepp_id` / water year and computes watershed averages weighted by channel area. | `wepp/output/interchange/chnwb.parquet` | None |
| `HillslopeWatbalReport` | Builds per-hillslope water balance (precipitation, percolation, runoff, etc.) using `H.wat.parquet`; aggregates per `TopazID` and computes watershed-wide yearly means weighted by area. | `wepp/output/interchange/H.wat.parquet` | `wepp/reports/cache/hillslope_watbal_summary.parquet` (version `1`) |
| `TotalWatbalReport` | Summarizes watershed-level water balance totals and derived ratios across water years, including means, standard deviations, and percentage-of-precipitation ratios. | `wepp/output/interchange/totalwatsed3.parquet` | None |
| `FrqFloodReport` | Performs flood-frequency analysis of event maxima, computing mean / standard deviation and frequency factors for selected recurrence intervals; converts runoff volumes to depths using watershed area. | `wepp/output/interchange/ebe_pw0.parquet`, `wepp/output/interchange/totalwatsed3.parquet` | None |
| `HillSummaryReport` | Produces per-hillslope sediment and hydrologic summaries enriched with landuse (and soils when available); converts volumes to depths and mass to densities per hectare. | `wepp/output/interchange/loss_pw0.hill.parquet`, `watershed/hillslopes.parquet`, `landuse/landuse.parquet`, optional `soils/soils.parquet` | None |
| `ChannelSummaryReport` | Generates per-channel sediment / hydrologic summaries using loss output joined with channel metadata; derives discharge depths and per-area densities. | `wepp/output/interchange/loss_pw0.chn.parquet`, `watershed/channels.parquet` | None |
| `OutletSummaryReport` | Summarizes outlet delivery metrics, adds per-area conversions (mm or kg/ha), and exposes both primary and extended rows. | `wepp/output/interchange/loss_pw0.out.parquet` | None |
| `SedimentClassInfoReport` | Provides static class metadata (particle class characteristics and fractions). | `wepp/output/interchange/loss_pw0.class_data.parquet` (queried through `SedimentCharacteristics`) | None |
| `ChannelClassFractionReport` / `ChannelParticleDistributionReport` | Derived sub-reports conveying outlet sediment discharge fractions by class and particle type. Built by `SedimentCharacteristics`. | `loss_pw0.class_data.parquet`, `loss_pw0.out.parquet` | None |
| `HillslopeClassFractionReport` / `HillslopeParticleDistributionReport` | Mirrors the channel distributions but for hillslope delivery (based on pass file mass totals and class fractions). | `loss_pw0.class_data.parquet`, `H.pass.parquet`, `loss_pw0.all_years.hill.parquet` | None |

**Notes**

* `SedimentCharacteristics` is not itself a `ReportBase` subclass; it
  composes `SedimentClassInfoReport`, `ChannelClassFractionReport`,
  `ChannelParticleDistributionReport`, `HillslopeClassFractionReport`,
  and `HillslopeParticleDistributionReport`.
* Compatibility aliases (e.g. `ChannelWatbal`) remain for legacy imports
  via `wepppy.wepp.reports.__init__` and the shim package
  `wepppy.wepp.stats`.

---

## Checklist for new reports

1. Decide whether results should be cached. If yes, define a cache key
   and version and rely on `ReportCacheManager`.
2. Use `ReportQueryContext.ensure_datasets()` early to bubble up missing
   assets with useful error messages.
3. Provide unit coverage under `tests/wepp/reports`. For complex DuckDB
   interactions, patch `ReportQueryContext` with a stub that returns the
   desired dataset records.
4. Export the class (and optional legacy alias) from
   `wepppy.wepp.reports.__init__`.
5. Update command-line scripts, Flask routes, and notebooks to import the
   renamed `*Report` class.
