# Ash Transport Module

This module provides the post-fire ash transport workflow used by `wepppy`. It manages
model setup, executes one of the supported ash transport simulators for every
hillslope in a watershed, and aggregates results into curated parquet products that
drive downstream summaries and reports.

## Components At A Glance

| Component | Role |
| --- | --- |
| `Ash` | Per-project manager responsible for configuration, model execution, and coordination with other NoDB modules. |
| `AshModel` / `AshModelAlex` | Core simulators that compute day-by-day ash depletion and transport for a single hillslope. Each wraps one published model calibration. |
| `AshPost` | Post-processor that consumes raw hillslope outputs and produces watershed-level datasets, return-period statistics, and documentation. |

## Execution Workflow

1. **Configuration**  
   `Ash.__init__` reads the project configuration and loads required inputs such as burn severity, ash load, and ash type rasters. It prepares model parameter sets for both supported calibrations.

2. **Cleanup / Versioning**  
   Each run of `Ash.run_ash` clears prior artifacts in `ash_dir`, including stale ashpost outputs and manifests. This guarantees that a fresh run only exposes version-compatible results.

3. **Per-Hillslope Simulation**  
   `Ash.run_ash` iterates through every TOPAZ hillslope:
   - Builds metadata (area, slope, burn class, ash depth) and selects the requested model (`multi` or `alex`).
   - Loads climate (`cli_df`) and water balance (`hill_wat_df`) data frames.
   - Calls `AshModel.run_model`, which locates each fire anniversary within the multi-year time series, dispatches `_run_ash_model_until_gone`, and collects the day-by-day records for that fire year.
   - The concatenated dataframe (`pd.concat(dfs)`) is written to `ash/H{wepp_id}_ash.parquet`; the same run produces PNG plots for diagnostics.

4. **Post-Processing**  
   `AshPost.run_post` orchestrates the post-processing pass:
   - Removes incompatible parquet outputs based on the AshPost version manifest.
   - Reads every `H{wepp_id}_ash.parquet`, enriches it with hillslope metadata, and converts per-area metrics to absolute tonnes and cubic metres.
   - Generates parquet artifacts (see [Produced Artifacts](#produced-artifacts)) with embedded schema metadata and writes `ash/post/ashpost_version.json`.
   - Creates a markdown README summarising the schema and sample values.

5. **Catalog Update**  
   After successful post-processing, `update_catalog_entry` registers the ash products for query-engine discovery.

## Supported Models

Two calibrated models are bundled. Both inherit from `AshModelAlex` or `AshModel` and share the same high-level algorithm:

### Srivastava 2023 (`AshModel`)

*Key idea:* Exponential decay of ash transport capacity tied to evolving ash bulk density and runoff depth.

**Parameters**

| Attribute | Description |
| --- | --- |
| `ini_bulk_den` / `fin_bulk_den` | Initial and final ash bulk densities (gm/cm³); density transitions via exponential decay driven by cumulative infiltration. |
| `bulk_den_fac` | Controls the time constant for the bulk-density transition. |
| `par_den` | Particle density (gm/cm³). |
| `decomp_fac` | Ash decomposition coefficient (per day). |
| `ini_erod` / `fin_erod` | Initial and asymptotic transport capacities (t/ha); blended as density increases. |
| `roughness_limit` | Minimum ash depth retained on the surface (mm). |
| `run_wind_transport` | Enables optional wind-driven removal based on peak daily wind speed. |

### Watanabe 2025 (`AshModelAlex`)

*Key idea:* Dynamic transport capacity involving organic matter, slope, and fitted coefficients (β₀–β₃) with depletion driven by cumulative ash runoff.

**Additional Parameters**

| Attribute | Description |
| --- | --- |
| `org_mat` | Fraction of surface organic matter (unitless). |
| `beta0` – `beta3` | Calibrated coefficients for the dynamic transport-capacity equation. |
| `transport_mode` | Currently `dynamic`; allows future toggles. |
| `initranscap` (`A`) | Initial transport capacity (t ha⁻¹ mm⁻¹). |
| `depletcoeff` (`B`) | Depletion coefficient applied to cumulative ash runoff (mm⁻¹). |

Both models compute the following for each daily timestep until transportable ash is exhausted:

- Water-driven transport when runoff exceeds ash storage.
- Wind-driven transport when enabled and wind thresholds are exceeded.
- Ash decomposition proportional to infiltration.
- Cumulative tallies (`cum_*` columns) enforcing mass balance checks.

## AshPost Data Pipeline

`AshPost` consumes the raw hillslope parquet files and produces higher-level tables:

1. **Hillslope Daily Aggregation**  
   `read_hillslope_out_fn` ingests each `H{wepp_id}_ash.parquet`, attaches metadata (`topaz_id`, `area`, `burn_class`), and converts per-area measures to totals. When `cumulative=True`, rows are filtered to the final day of each fire-year run.

2. **Statistics & Grouping**  
   - `calculate_hillslope_statistics` computes first-year averages per hillslope (tonne/ha).
   - `calculate_watershed_statisics` aggregates daily and annual watershed totals, builds burn-class drilldowns, and calculates Weibull-based return periods.
   - `calculate_cumulative_transport` captures cumulative metrics at the point ash is depleted for each fire year.

3. **Return Periods**  
   `calculate_return_periods` ranks events for specified recurrence intervals (default: 1000–2 years) and packages probability, rank, and return interval metadata for both watershed-wide and burn-class-specific perspectives.

4. **Versioned Output**  
   `_write_parquet` casts every table to a schema augmented with units, descriptions, and dataset version metadata (major/minor). `write_version_manifest` records the schema version in `ash/post/ashpost_version.json`.

5. **Documentation**  
   `generate_ashpost_documentation` reads each parquet file, renders a markdown section with schema and preview rows, and writes `ash/post/README.md`. The header lists the manifest version so consumers can detect mismatches.

## Produced Artifacts

All outputs reside under `ash_dir` (per project):

| Path | Description |
| --- | --- |
| `H{wepp_id}_ash.parquet` | Per-hillslope daily ash transport, remaining mass, and hydrology for all simulated fire years. |
| `H{wepp_id}_ash.png` / `_ash_scatter.png` | Diagnostic plots (cumulative transport vs. time, scatter vs. runoff). |
| `post/hillslope_annuals.parquet` | First-year average transport per hillslope (tonne/ha). |
| `post/watershed_daily.parquet` | Daily watershed totals (tonne and tonne/ha) for ash transport and remaining ash. |
| `post/watershed_daily_by_burn_class.parquet` | Daily totals segmented by burn class. |
| `post/watershed_annuals.parquet` | Annual watershed totals and per-area metrics. |
| `post/watershed_cumulatives.parquet` | One row per fire-year capturing cumulative metrics at ash exhaustion. |
| `post/ashpost_version.json` | Semantic version manifest (major/minor). |
| `post/README.md` | Auto-generated documentation with schemas and sample rows. |

All parquet schemas embed units (`units` metadata) and column descriptions (`description` metadata), making them self-describing for analytics tools that understand Arrow metadata.

## Operational Notes

- **Multiprocessing:** `Ash.run_ash` can parallelise hillslope simulations via the process-pool utilities in `NoDbBase` (subject to project configuration).
- **Wind Transport:** Controlled by `ash.config` via `run_wind_transport`. When disabled, wind pathways are skipped entirely.
- **Return Periods:** Default recurrence intervals mirror other WEPP outputs but can be overridden when calling `AshPost.run_post`.
- **Version Bumping:** Increase `ASHPOST_VERSION` when schema-breaking changes occur; the next `run_post` automatically purges incompatible parquet outputs and regenerates everything.

This README is intended as a maintenance guide: it captures the end-to-end flow so future updates can be scoped confidently even though ash transport is rarely touched.

