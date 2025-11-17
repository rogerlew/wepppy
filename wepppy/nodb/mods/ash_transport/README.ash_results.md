# Ash Transport Outputs
> Quick guide to the per-hillslope ash simulations and the post-processed watershed products. See `AGENTS.md` for conventions and the totalwatsed3 spec for hydrology context.

## Where to look
- `ash/` — per-hillslope simulation outputs (`H{wepp_id}_ash.parquet`) plus plots/diagnostics.
- `ash/post/` — aggregated, versioned parquet products and manifest docs produced by `AshPost.run_post()`.
- `wepp/output/interchange/totalwatsed3.parquet` — watershed hydrology + ash merge used for ash-aware streamflow and solids loads.

## Key inputs used in calculations
- `wepp/output/interchange/H.wat.parquet`: per-OFE water balance; runoff volumes are summed back to hillslopes.
- `wepp/output/interchange/totalwatsed3.parquet`: daily watershed hydrology (Runoff, Lateral Flow, Baseflow, Streamflow) and sediment deposition (`seddep_1..5`).
- `Ash.nodb`: `meta` dictionary flags hillslopes with/without ash (`ash_type`), burn class, and area. Non-ash hillslopes supply uncorrected runoff.

## Per-hillslope outputs (`ash/H{wepp_id}_ash.parquet`)
- Scope: one TOPAZ/WEPP hillslope, simulated for each fire-year; ash is reloaded at the ignition date each year until transportable ash is depleted.
- Core columns (names include units):
  - `ash_runoff (mm|m^3)`: ash-laden runoff depth/volume for that hillslope/day.
  - `ash_transport (tonne/ha)`, `water_transport (tonne/ha)`, `wind_transport (tonne/ha)`: daily transported ash mass.
  - `transportable_ash (tonne/ha)`: ash still available to move.
  - `ash_depth (mm|m^3)`: ash layer depth/volume.
  - `days_from_fire (days)`, `year0`, `year`, `julian`, `mo`, `da`: time keys; `year0` is the ignition year for that run.

## Post-processed parquet files (`ash/post/`)
- Common traits: units live in column names; per-area columns are recomputed from aggregated totals.
- `hillslope_annuals.parquet`: mean annual per-hillslope transport (`wind_transport (tonne/ha)`, `water_transport (tonne/ha)`, `ash_transport (tonne/ha)`).
- `watershed_annuals.parquet`: watershed-summed annual masses/volumes across all ash hillslopes; per-area columns normalized by ash hillslope area.
- `watershed_daily.parquet`: watershed daily aggregates with hydrology-aware extras:
  - Ash totals: `wind_transport (tonne)`, `water_transport (tonne)`, `ash_transport (tonne)`, `transportable_ash (tonne)` plus per-ha variants (ash hillslope area).
  - Ash runoff replacement: `Streamflow_orig (mm)` from totalwatsed3 vs `Streamflow_ash_corr (mm)` where ash-runoff volume replaces WEPP runoff on ash hillslopes. Non-ash runoff comes from `H.wat`; `Lateral Flow` and `Baseflow` come from totalwatsed3.
  - Solids: `tot_seddep+ash (tonne)` = `(seddep_1..5 sum)/1000 + ash_transport`; `tot_seddep+ash (tonne/ha)` uses total watershed area.
  - Also carries ash volumes (`ash_runoff (m^3)`, `ash_depth (m^3)`) and per-area depths when present.
- `watershed_daily_by_burn_class.parquet`: same daily aggregation split by `burn_class`.
- `watershed_cumulatives.parquet`: one row per fire year (`year0`) with cumulative transport (`cum_*` columns) and return-period stats.
- `documentation.md` and `version_manifest.json`: generated schemas/metadata tied to `ASHPOST_VERSION`.

## Calculation references
- Ash runoff replacement: `Streamflow_ash_corr (mm)` = (`non_ash_runoff_m3` from `H.wat` + `ash_runoff_m3` from ash hillslopes + `lateral_flow_m3` + `baseflow_m3`) ÷ total watershed area × 1000. `Streamflow_orig` is untouched totalwatsed3 streamflow.
- Solids load: `tot_seddep+ash (tonne)` uses deposition (`seddep_1..5`) from totalwatsed3 (kg → tonne) plus ash transport (tonne); per-ha uses watershed area.
- Area rules: hydrology depths (`Runoff`, `Streamflow`) use total hillslope area. Ash per-ha metrics use the summed area of ash-modeled hillslopes only.

## Operational notes
- Column names in `totalwatsed3` are unitless; units are in Arrow metadata. Legacy ash columns with unit suffixes are auto-renamed during merge.
- If `totalwatsed3.parquet` or `H.wat.parquet` are missing, ash products still write but hydrology-aware columns zero-fill.
- Return-periods are computed on first-year daily aggregates (`days_from_fire <= 365`); cumulative products also retain extended multi-year runs.
