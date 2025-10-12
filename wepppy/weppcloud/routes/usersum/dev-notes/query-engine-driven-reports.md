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
- Results are cached to `wepp/output/interchange/average_annuals_by_landuse.parquet`
  so large watersheds do not re-query on every request. The cache is invalidated
  automatically if the stored column layout no longer matches the current schema.

## Loss Summary Reports

- **OutletSummary** reads `wepp/output/interchange/loss_pw0.out.parquet` via the
  query-engine, normalises volumes to watershed-average depths (mm/yr), and exposes
  both absolute and per-area metrics for precipitation, discharge, soil loss, and
  phosphorus. Extraneous rows (irrigation volumes, explicit per-area totals) are
  kept available for the “show extraneous parameters” toggle.
- **HillSummary** joins `loss_pw0.hill.parquet` with `watershed/hillslopes.parquet`,
  `landuse/landuse.parquet`, and `soils/soils.parquet` (when present). It computes
  area-normalised depths/densities in DuckDB and renders a tidy table with landuse,
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
  2. Apply year/month exclusions in SQL to trim the candidate event set.
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
  - Provide a helper (e.g., `refresh_return_period_events(wd)`) that regenerates the
    staged parquet files when a run is updated.
- **Reboot prompt for implementation phase**:
  > “Rebuild `ReturnPeriods` using the staged query-engine approach: generate
  > `return_period_events.parquet` and `return_period_event_ranks.parquet` from
  > `ebe_pw0.parquet`, climate intensities, and `totalwatsed3.parquet`, then expose
  > a `ReturnPeriodDataset` that supplies the template without relying on the old
  > pandas-based code.”
