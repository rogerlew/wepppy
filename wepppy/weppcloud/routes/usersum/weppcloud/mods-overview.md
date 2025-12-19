# Mods Overview
> Quick reference for the optional mods toggled from the header dropdown.

## RAP Time Series (`rap_ts`)
- Purpose: Download RAP fractional cover rasters across years, summarize them to TOPAZ hillslopes (and optional OFEs).
- Use when: You need multi-year cover trends to drive WEPP runs or the GL-Dashboard. Revegetation requires the RAP TS database
- Outputs: `rap/rap_ts.parquet`

## Ash Transport (`ash`)
- Purpose: Model post-fire ash and contaminant transport using burn severity, ash load/type maps, and hydrology/climate inputs.
- Use when: Evaluating post-fire water quality or ash delivery; depends on Landuse/BAER/Disturbed layers and optional ash rasters.
- Outputs: Per-hillslope daily ash parquet files plus AshPost watershed summaries and status updates. Daily aggregated ash measures are added to the `totalwatsed3.parquet`

## Treatments (`treatments`; Experimental)
- Purpose: Apply spatial treatments (mulch, seeding, road upgrades) after Disturbed adjustments, using a treatment map or manual selections.
- Use when: Experimental, but required by `Omni`
- Outputs: Normalized treatment map, treatment lookups per hillslope, and prep timestamps for downstream controllers.

## Observed Data (`observed`)
- Purpose: Ingest observed flow/sediment CSVs and calculate fit statistics against simulated hillslope/channel outputs.
- Use when: Calibrating or validating runs against measured data; expects dated observations with matching measures.
- Outputs: Parsed `observed.csv`, fit metrics, and cached results for reporting.

## Debris Flow (`debris_flow`)
- Purpose: Estimate debris-flow probability and volume using USGS equations fed by burn severity, soils, slope, and precipitation frequency curves.
- Use when: Screening post-fire debris-flow hazards. Relies on BAER/Disturbed severity, soils, and NOAA or Holden WRF Atlas precip data.
- Outputs: Probability/volume matrices keyed by datasource plus status timestamps for UI panels.

## DSS Export (`dss_export`)
- Purpose: Package WEPP watershed outputs into HEC-DSS files (totalwatsed time series and channel peak flows) and bundle them for download.
- Use when: Delivering hydrographs to HEC-HMS/RAS or other DSS consumers after WEPP completes; optional filters control channel selection and date ranges.
- Outputs: `export/dss/*.dss`, boundary GeoJSON/GML artifacts, and `dss.zip` with a README.

## Omni (`omni`)
- Purpose: Orchestrate scenario clones (uniform burns, thinning, mulch, SBS map, etc.), re-run WEPP per scenario, and produce contrast analytics.
- Use when: Comparing mitigation scenarios side-by-side under `_pups/omni`; consumes existing climate/soils/landuse/disturbed inputs.
- Outputs: Scenario run directories, DuckDB/Parquet reports (`scenarios.out.parquet`, contrast logs), and refreshed catalog entries.

## Path Cost-Effective (`path_ce`)
- Purpose: Run the PATH cost-effective optimizer to rank mitigation treatments by sediment reduction per dollar using linear programming.
- Use when: You have Parquet summaries from baseline/reference scenarios (e.g., Omni) and need a prioritized treatment package.
- Outputs: Solver inputs/outputs under `path/`, optimized treatment tables, and interchange artifacts for UI consumption.
