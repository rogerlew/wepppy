# Query Engine-Driven Reports

> **See also:** [AGENTS.md](../../../AGENTS.md) for report architecture, DuckDB query patterns, and telemetry expectations.

This guide captures the DuckDB-backed report pipelines that translate WEPP interchange parquet files into the summaries exposed through the Flask UI and API surfaces.

## Average Annuals by Landuse

- Reads directly from `wepp/output/interchange/loss_pw0.hill.parquet` joined with
  `watershed/hillslopes.parquet` (for WEPP ↔ Topaz mapping and precise areas) and
  `landuse/landuse.parquet` (for landuse id + description).
- Aggregation happens in DuckDB via the query-engine, returning per-landuse sums of
  runoff/subrunoff/baseflow volumes (m³·yr⁻¹), sediment terms (kg·yr⁻¹), and total
  contributing area (m²).
- Python post-processing converts volumes to depth using the total contributing
  area (`volume * 1000 / area_m²`) and assembles the report columns:
  `Avg Runoff/Lateral/Baseflow Depth (mm/yr)` plus the sediment annual totals.
- Results are cached to `wepp/reports/cache/average_annuals_by_landuse.parquet`.
  Selected source content and effective catalog aliases are checked on reuse;
  changes rebuild the report through DuckDB, even with restored timestamps.

## Water-balance and landuse cache freshness

Water-balance summaries use the required streaming native producer and also
verify the effective WEPP-to-Topaz mapping, including Roads segment targets.
Touching or hard-linking unchanged inputs does not rebuild either report. Actual
source or mapping changes rebuild before returning new rows. Scientific columns,
units, calculations and baseline/Roads scope are unchanged.

Retained reports remain available after required source files are archived or
removed, provided no remaining verified dependency is known to have changed.
These are historical reports, not a claim that current project inputs match.
Report objects expose `cache_status` (`current`, `built` or
`historical_unverified`); historical use is logged. Existing HTML and CSV do not
add a freshness badge or scientific column. Legacy caches without provenance
rebuild once when prerequisites exist; legacy water-balance reads retain their
native-unavailable compatibility rule. Failed rebuilds never silently replace a
known-stale result with historical rows.

New compact cache Parquet files contain their dependency provenance. Version-1
JSON sidecars remain readable by older releases. Inspect build observations,
status, native/query intermediates and failed candidates under
`wepp/reports/cache/<key>.attempts/<id>/` through normal project browse. These are
included in canonical archive/restore. An atomic Parquet replacement commits the
new cache; a later diagnostic-write failure is logged without rolling it back.
An interrupted attempt's embedded ID can be compared with the accepted Parquet
metadata. Do not delete the attempt to hide a failed build.

Land-use cache rebuilds require write access to an existing cache file as well as
its directory. Water-balance keeps its native atomic-writer permission behavior.
Version-sidecar repairs preserve their own access permissions and mode.
Denied publication retains the prior file and visible failed candidate.

Developers should use the [report cache contract](../../../docs/schemas/report-cache-freshness-contract.md)
for dependency selection, legacy behavior, publication/access preservation and
performance limits. Run `wctl run-pytest tests/wepp/reports` after changes. Source
hashing uses the bounded shared digest cache; native H.wat ID scanning and
DuckDB aggregation occur only on rebuild. Before/after source checks detect
observable drift but do not provide arbitrary-writer snapshot isolation.

## Loss Summary Reports

- **OutletSummary** reads `wepp/output/interchange/loss_pw0.out.parquet` via the
  query-engine, normalizes volumes to watershed-average depths (mm/yr), and exposes
  both absolute and per-area metrics for precipitation, discharge, soil loss, and
  phosphorus. Extraneous rows (irrigation volumes, explicit per-area totals) are
  kept available for the “show extraneous parameters” toggle.
- **HillSummary** joins `loss_pw0.hill.parquet` with `watershed/hillslopes.parquet`,
  `landuse/landuse.parquet`, and `soils/soils.parquet` (when present). It computes
  area-normalized depths/densities in DuckDB and renders a tidy table with landuse,
  soil descriptions, and phosphorus metrics when available—no `totalwatsed.py`
  dependency.
- **ChannelSummary** queries `loss_pw0.chn.parquet` and `watershed/channels.parquet`
  to derive per-channel discharge depths, sediment delivery, and erosion (plus
  optional phosphorus densities). All per-area conversions are handled in SQL with
  `CASE` guards for zero-area channels, yielding a clean DataFrame for the summary
  template.

## Sediment Characteristics

- `SedimentCharacteristics` orchestrates the channel and hillslope sediment views.
  It reads `loss_pw0.class_data.parquet` for particle definitions/fractions,
  `loss_pw0.out.parquet` for outlet totals (sediment discharge, specific surface
  metrics), `H.pass.parquet` for hillslope sediment class masses, and
  `loss_pw0.all_years.hill.parquet` to determine the simulation year span.
- `SedimentClassInfoReport` exposes the particle class table rendered in the report.
- `ChannelSedimentDistribution` supplies both the class-wise discharge table and
  the particle-type distribution (fractions + tonne·yr⁻¹) derived from outlet totals.
- `HillslopeSedimentDistribution` aggregates the pass file to average-annual class
  masses, providing hillslope totals, class distributions, and particle-type splits.

## Return Periods (Refactor Specification)

- **Objective**: replace the legacy `ReturnPeriods` class with a query-engine
  pipeline that narrows the event set to just the ranked observations needed for
  common recurrence intervals, while allowing the template to request arbitrary
  return periods at runtime.
- **Inputs**:
  - `wepp/output/interchange/ebe_pw0.parquet` – event-by-event channel metrics 
    (runoff volume, peak discharge, sediment yield, pollutants, element id, etc.).
  - `wepp/output/interchange/loss_pw0.all_years.chn.parquet` / `loss_pw0.all_years.hill.parquet`
    – per-year summaries to track simulation years and filter excluded years.
  - `wepp/output/interchange/totalwatsed3.parquet` – hillslope aggregates to attach
    hill sediment delivery/streamflow to each event.
  - `H.pass.parquet` – hillslope event sediment mass by class (when detailed hillslope
    metrics are needed for the return-period rows).
  - `climate/*.parquet` – climate intensities and storm durations (10/15/30 minute
    peaks). Query these via DuckDB joins rather than pandas merges.
- **Staging procedure**:
  1. Use DuckDB to join the event table `ebe_pw0.parquet` with the climate parquet
     and any hillslope/channels tables needed for the metrics shown in the report.
  2. Persist the full staged event set plus year/month event counts. Year and
     month exclusions are applied later by `ReturnPeriodDataset.create_report()`
     so one staged parquet pair can serve multiple report filter combinations.
  3. For each metric (runoff, peak discharge, sediment yield, phosphorus, hill
     sediment delivery, hill streamflow, etc.), compute a descending rank (dense)
     and keep only the top *N* rows, where *N* ≥ max recurrence interval + buffer
     (e.g., 50). Store the ranks along with the event metadata in a staged parquet
     file such as `return_period_events.parquet`.
  4. Persist a second mapping table `return_period_event_ranks.parquet` containing
     `(measure, rank, event_id)` for fast lookups. Include per-measure metadata
     (units, labels) in the parquet schema metadata so the report class can render
     nicely formatted headers.
- **Reporting API**:
  - Implement a `ReturnPeriodDataset` class that loads the staged parquet files,
    computes Weibull positions for the requested recurrence intervals, resolves the
    appropriate events by rank, and returns the same structure the template expects
    today (measure → period → values + units, Weibull rank/T, etc.).
  - For CTA reports with excluded months, compute the effective days per year from
    the filtered event-count table and use that basis for both CTA recurrence-rank
    selection and displayed Weibull T. Interpret these results as recurrence within
    the included seasonal window, not the full calendar year.
  - Always render the core report measures (precipitation depth, runoff, peak
    discharge, sediment yield). If no ranked rows for a core measure survive the
    selected filters, the report should show an explicit no-events state rather
    than omit the measure.
  - Provide a helper (e.g., `refresh_return_period_events(wd)`) that regenerates the
    staged parquet files when a run is updated.
- **Runtime and cache split**:
  - The RQ postprocess task `_analyze_return_periods_rq` builds or refreshes the
    staged parquet assets and TSV exports during the WEPP pipeline.
  - The Flask `weppcloud` report route calls `Wepp.report_return_periods()`
    synchronously when a user opens the report. That call reads/writes meoized
    JSON caches under `wepp/output/return_periods*.json`.
  - To force UI report regeneration without rerunning WEPP, remove only the
    matching `wepp/output/return_periods*.json` cache files and leave
    `wepp/output/interchange/return_period_events.parquet` and
    `return_period_event_ranks.parquet` intact.
- **Reboot prompt for implementation phase**:
  > “Rebuild `ReturnPeriods` using the staged query-engine approach: generate
  > `return_period_events.parquet` and `return_period_event_ranks.parquet` from
  > `ebe_pw0.parquet`, climate intensities, and `totalwatsed3.parquet`, then expose
  > a `ReturnPeriodDataset` that supplies the template without relying on the old
  > pandas-based code.”

## Hillslope Water Balance

`HillslopeWatbalReport` requires the paired native hillslope-watbal API when a
cache must be rebuilt. Rust streams projected H.wat batches and writes the
compact Topaz/year summary; Python loads only that summary for report iterators.
Existing baseline/Roads mappings, cache version, source freshness, legacy reads,
headers, units, and average divisors remain unchanged. Large-run processing no
longer creates a source-sized pandas dataframe. Missing native support fails
explicitly; update the paired release and startup pin together.

See the [summary cache contract](../../../docs/schemas/output-scope-contract.md#hillslope-water-balance-summary-cache)
for exact fields, null behavior, and publication expectations.
