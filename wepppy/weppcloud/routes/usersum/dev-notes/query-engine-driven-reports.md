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
