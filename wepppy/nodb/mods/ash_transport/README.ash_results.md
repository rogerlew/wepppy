# Post-Fire Ash Transport Model Outputs
> Guide to understanding ash transport simulation results for watershed-scale post-wildfire response assessment.

## Overview

This ash transport model simulates the movement of wildfire-generated ash from burned hillslopes into stream channels. The model tracks both **water-driven transport** (ash carried by surface runoff) and **wind-driven transport** (ash eroded by wind during dry periods) over multiple years following a fire. Model outputs are designed to help assess post-fire water quality risks, sediment loads to downstream reservoirs, and the timing of ash delivery to streams.

**Key physical processes modeled:**
- Initial ash layer depth and bulk density based on burn severity
- Daily ash depletion through water runoff events
- Wind erosion of loose ash between storms
- Natural ash decomposition over time
- Multi-year ash availability decline as material is transported or stabilized

## File Organization

Results are stored in two main locations within your project directory:

- **`ash/`** — Individual hillslope simulation outputs plus diagnostic plots
  - `H{hillslope_id}_ash.parquet` — daily time series for each burned hillslope
  
- **`ash/post/`** — Watershed-scale aggregated summaries
  - `watershed_daily.parquet` — daily watershed totals with hydrology corrections
  - `watershed_annuals.parquet` — annual summaries by year
  - `watershed_cumulatives.parquet` — cumulative transport by fire year
  - `hillslope_annuals.parquet` — average annual transport by hillslope
  - `watershed_daily_by_burn_class.parquet` — daily totals stratified by burn severity
  - `documentation.md` and `version_manifest.json` — metadata and schema documentation

## Understanding Hillslope Results

Each burned hillslope has a detailed daily output file (`H{hillslope_id}_ash.parquet`) covering the entire simulation period. The model simulates multiple fire years, reloading ash at each ignition date until the transportable ash pool is depleted.

**Key variables to examine:**

| Column Name | Units | Description |
|------------|-------|-------------|
| `year0` | - | Fire ignition year for this simulation run |
| `year`, `julian`, `mo`, `da` | - | Date identifiers for the record |
| `days_from_fire` | days | Time elapsed since fire ignition (useful for plotting recovery timelines) |
| `ash_transport` | tonne/ha | **Total daily ash loss** from the hillslope (water + wind combined) |
| `water_transport` | tonne/ha | Ash transported by surface runoff |
| `wind_transport` | tonne/ha | Ash eroded by wind (when runoff is minimal) |
| `transportable_ash` | tonne/ha | Remaining ash available for mobilization |
| `ash_runoff` | mm or m³ | Runoff depth modified by ash layer hydrology |
| `ash_depth` | mm or m³ | Current ash layer thickness

**Interpretation tips:**
- Most ash transport occurs during the first few large storms after the fire
- Watch `days_from_fire` to see how quickly the ash load depletes
- Compare `water_transport` vs `wind_transport` to understand dominant transport mechanisms
- `transportable_ash` approaching zero indicates end of simulation for `year0` year

## Watershed-Scale Summaries

The `ash/post/` directory contains aggregated results suitable for watershed-scale assessment and reporting.

### Daily Watershed Totals (`watershed_daily.parquet`)

Provides daily time series summed across all burned hillslopes. This is the primary file for understanding watershed-scale ash mobilization patterns.

**Critical columns for analysis:**

| Column | Units | What It Represents |
|--------|-------|-------------------|
| `ash_transport` | tonne | **Total daily ash exported** from all burned hillslopes |
| `water_transport` | tonne | Portion transported by runoff |
| `wind_transport` | tonne | Portion eroded by wind |
| `Streamflow_ash_corr` | mm | **Corrected streamflow** accounting for ash-layer effects on runoff generation |
| `Streamflow_orig` | mm | Original WEPP streamflow (without ash corrections) |
| `tot_seddep+ash` | tonne | Combined WEPP sediment + ash delivered from the hillslopes |

**Understanding the hydrology corrections:**

The ash layer affects hillslope hydrology by changing infiltration and water retention. The model replaces WEPP's original runoff estimates for burned hillslopes with ash-modified runoff:

- **Streamflow_orig** = baseline WEPP watershed streamflow (as if no ash layer existed)
- **Streamflow_ash_corr** = corrected streamflow incorporating ash layer hydrology effects
- The difference between these values shows how the ash layer influences total water yield

Streamflow corrections account for:
- Ash layer water storage capacity
- Changed infiltration rates through the ash layer
- Surface sealing effects from ash
- Integration with subsurface flow (lateral flow and baseflow unchanged)

### Annual Summaries

**Hillslope Annuals** (`hillslope_annuals.parquet`)

Average annual transport rates for each burned hillslope. Useful for identifying hotspot areas with persistently high ash export.

**Watershed Annuals** (`watershed_annuals.parquet`)

Annual totals for the entire watershed. Key for year-to-year comparisons and understanding multi-year ash export patterns.

Both files include:
- `wind_transport` (tonne/ha or tonne) — average or total wind erosion when wind transport is enabled
- `water_transport` (tonne/ha or tonne) — average or total water transport
- `ash_transport` (tonne/ha or tonne) — combined total ash loss
- `transportable_ash` (tonne/ha or tonne) — remaining ash pool

### Cumulative Transport (`watershed_cumulatives.parquet`)

One row per simulated fire year showing cumulative totals:
- `cum_ash_transport` — total ash exported over the entire simulation
- `cum_water_transport` — cumulative water-driven transport
- `cum_wind_transport` — cumulative wind-driven transport
- `days_from_fire` — simulation duration

**This file includes return period statistics** for design storm analysis (2-year, 10-year, 100-year events). These statistics help assess risks of extreme ash transport events.

### Burn Severity Stratification (`watershed_daily_by_burn_class.parquet`)

Same daily structure as `watershed_daily.parquet`, but stratified by burn severity class (1=unburned, 2=low, 3=moderate, 4=high). Use this to:
- Compare transport rates between severity classes
- Assess whether high-severity areas dominate ash export
- Prioritize treatment areas based on transport potential

## Technical Details

### Model Inputs (automatically handled by the system)

The ash transport model integrates:
- WEPP hillslope hydrology (runoff, infiltration, soil moisture)
- CLIGEN synthetic climate (precipitation, wind speed)
- Burn severity maps (soil burn severity classes)
- Hillslope geometry (area, slope, aspect)
- Ash properties (initial depth/load, bulk density, decomposition rate)

### Calculation Methods

**Streamflow correction methodology:**

Corrected streamflow combines:
- Runoff from unburned hillslopes (from WEPP H.wat.parquet)
- Ash-modified runoff from burned hillslopes (from ash model)
- Lateral flow and baseflow (from WEPP totalwatsed3.parquet, unchanged)

Formula: `Streamflow_ash_corr = (non_ash_runoff + ash_runoff + lateral_flow + baseflow) / watershed_area`

**Total solids calculation:**

Combines sediment deposition with ash transport:
`tot_seddep+ash = WEPP_sediment_deposition + ash_transport`

This represents total particulate matter delivered to the watershed outlet.

**Area normalization:**
- Per-area ash metrics (tonne/ha, mm) use only the burned hillslope area
- Watershed-scale hydrology metrics (mm) use the total watershed area
- This distinction is important when comparing burned vs unburned responses

### Data Quality Notes

- Model results are deterministic given the input climate sequence
- Actual outcomes depend on the specific timing and magnitude of post-fire storms
- Results represent median conditions for the simulated hillslope characteristics
- Spatial variability within hillslopes is not captured (lumped model)
- Channel routing and deposition processes are not explicitly modeled

### File Format Details

All output files use Apache Parquet format with:
- Units embedded in column names (e.g., `ash_transport (tonne)`)
- Schema metadata including field descriptions
- Snappy compression for efficient storage
- Compatible with Python (pandas/duckdb), R (arrow), and most data science tools

## Further Documentation

- **`README.md`** in `ash/post/` — complete schema documentation with field descriptions
- **WEPP interchange files** (`wepp/output/interchange/`) — source hydrology data for advanced analysis
