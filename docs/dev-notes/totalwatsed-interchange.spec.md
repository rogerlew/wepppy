# Daily combined output over hillslope interchange outputs (`H.wat`, `H.pass`, optional `H.soil` and `H.element`)

> **See also:** [AGENTS.md](../../AGENTS.md) for WEPP model integration and [wepp_interchange.spec.md](wepp_interchange.spec.md) for overall interchange architecture.

At after `run_wepp_hillslope_interchange` create `interchange/totalwatsed3.parquet`

Kitchen sink of daily (`sim_day_index` is the 1-indexed simulation day) measures for watershed.

`def run_totalwatsed3(interchange_dir, baseflow_opts: BaseflowOpts, wepp_ids = None | List[int])`

if `wepp_ids` is None aggregate all the wepp_ids, otherwise filter to only include wepp_ids

## Specification
- H.wat.parquet -> wat (optional columns: `SoilWaterTotal`, `ProfileDepth`, `ProfilePorosityCap`, `ProfileFCStore`, `ProfileWPStore`, `Interception`, `InterceptionStorage`)
- H.pass.parquet -> pass
- H.soil.parquet -> soil (optional `TSMF` full-profile moisture fraction)
- H.element.parquet -> element (optional runoff partition columns `QRain` and `QSnow`)
- ash/H{wepp_id}_ash.parquet -> first-year ash transport metrics (optional)

### Optional H.wat storage/capacity contract (authoritative from WEPP when present)
- `SoilWaterTotal (mm)` = `watcon + frozwt`
- `ProfileDepth (mm)` = `solthk(nsl)`
- `ProfilePorosityCap (mm)` = `sum(por * dg)`
- `ProfileFCStore (mm)` = `sum(thetfc * dg)`
- `ProfileWPStore (mm)` = `sum(thetdr * dg)`

These terms are producer-authoritative values emitted by WEPP into `H.wat`
when available. `wepppy` should parse/pass through these columns and avoid
re-deriving them if present.

### Legacy executable compatibility
- Legacy binaries (for example `wepp_dcc52a6`) may not emit these optional
  `H.wat` columns.
- Missing optional columns are expected for legacy producers and must not cause
  parse failures.
- `wepppy` must default missing optional terms to `null` at interchange and
  `totalwatsed3` aggregation stages.

## Water Balance Contract

`totalwatsed3` water-balance auditing is contractually defined by
`tools/totalwatsed3_daily_closure_audit.py`.

Daily water-balance terms (mm):
- Primary input: `Precipitation`.
- Diagnostic input: `Rain+Melt`.
- Outflows: `Runoff`, `Lateral Flow`, `Percolation`, `ET`, `Interception` (defaults to `0` when absent).
- Legacy storage state: `S_legacy = Total-Soil Water + frozwt + Snow-Water`.
- Enriched storage state (optional): `S_enriched = SoilWaterTotal + Snow-Water`.

Daily storage delta:
- `ΔS_legacy(t) = S_legacy(t) - S_legacy(t-1)`.
- `ΔS_enriched(t) = S_enriched(t) - S_enriched(t-1)` when `SoilWaterTotal` is available.
- For the first day, audit uses zero delta (`np.diff(..., prepend=first_value)`).

Daily closure definitions (mm):
- Primary reported closure:
  `C_reported_precip = Precipitation - (Runoff + Lateral Flow + ET + Percolation + Interception) - ΔS_legacy`.
- Primary reconstructed closure:
  `C_reconstructed_precip = Precipitation - (runvol/Area*1000 + latqcc/Area*1000 + (Ep+Es+Er)/Area*1000 + Dp/Area*1000 + Interception) - ΔS_legacy`.
- Diagnostic rain/melt closure (reported/reconstructed) uses `Rain+Melt` in place of `Precipitation`.
- Enriched variants replace `ΔS_legacy` with `ΔS_enriched` when available.

Whole-run closure definitions:
- Totals are sums of daily closures over all rows.
- Primary percentages normalize by `precip_total_mm`.
- Diagnostic rain/melt percentages normalize by `rain_melt_total_mm`.
- Summary contract includes:
  - `whole_run_closure.closure_basis_primary = "precipitation"`
  - `whole_run_closure.closure_basis_diagnostic = "rain_melt"`
  - backward-compatible aliases `closure_*_pct_of_rain_melt` that map to diagnostic rain/melt closure percentages.

Availability and fallback contract:
- When optional reported depth columns are absent, audit reconstructs from volume columns (`P`, `RM`, `runvol`, `latqcc`, `Dp`, `Ep`, `Es`, `Er`) and `Area`.
- `SoilWaterTotal`/profile-capacity diagnostics are optional and remain null/unavailable for legacy producers.
- `Interception` is optional at ingestion. If absent or null, totalwatsed3/audit consume it as `0` to preserve legacy closure behavior.
- Output artifacts are:
  - `daily_closure_audit_summary.json`
  - `daily_closure_audit_top_days.csv`
  under the audit output directory (default sibling `audit_totalwatsed3_daily_closure`).

## Schema for totalwatsed3, use `schema_utils.pa_field`

| Column | Type | Units | Description | Calculation |
| --- | --- | --- | --- | --- |
| year | int16 |  |  |  |
| sim_day_index | int32 |  |  |  |
| julian | int16 |  |  |  |
| month | int8 |  |  |  |
| day_of_month | int8 |  |  |  |
| water_year | int16 |  |  |  |
| runvol | double | m^3 | Runoff volume | sum(pass.runvol ) |
| sbrunv | double | m^3 | Subsurface runoff volume | sum(pass.sbrunv ) |
| tdet | double | kg | Total detachment | sum(pass.tdet ) |
| tdep | double | kg | Total deposition | sum(pass.tdep ) |
| seddep_1 | double | kg | Sediment Class 1 deposition | sum(pass.sedcon_1 * pass.runvol) |
| seddep_2 | double | kg | Sediment Class 2 deposition | sum(pass.sedcon_2 * pass.runvol) |
| seddep_3 | double | kg | Sediment Class 3 deposition | sum(pass.sedcon_3 * pass.runvol) |
| seddep_4 | double | kg | Sediment Class 4 deposition | sum(pass.sedcon_4 * pass.runvol) |
| seddep_5 | double | kg | Sediment Class 5 deposition | sum(pass.sedcon_5 * pass.runvol) |
| sed_del | double | kg | Total sediment delivery | seddep_1 + seddep_2 + seddep_3 + seddep_4 + seddep_5 |
| sed_vol_conc | double | m^3/m^3 | Volumetric sediment concentration | sum(seddep_i / rho_i) / runvol where rho_i is class density |
| Area | double | m^2 | Area that depths apply over | sum(wat.Area) |
| P | double | m^3 | Precipitation | sum(wat.P * 0.001 *  wat.Area) |
| RM | double | m^3 | Rainfall+Irrigation+Snowmelt | sum(wat.RM * 0.001 *  wat.Area) |
| Q | double | m^3 | Daily runoff over eff length | sum(wat.Q * 0.001 *  wat.Area) |
| Dp | double | m^3 | Deep percolation | sum(wat.Dp * 0.001 *  wat.Area) |
| latqcc | double | m^3  | Lateral subsurface flow | MOFE: sum(case when ofe_id=last_ofe then wat.latqcc*0.001*wat.Area else 0 end); single OFE: sum(wat.latqcc*0.001*wat.Area) |
| QOFE | double | m^3  | Daily runoff scaled to single OFE | sum(wat.QOFE * 0.001 *  wat.Area) |
| Ep | double | m^3 | Plant transpiration | sum(wat.Ep * 0.001 *  wat.Area) |
| Es | double | m^3 | Soil evaporation | sum(wat.Es * 0.001 *  wat.Area) |
| Er | double | m^3 | Residue evaporation | sum(wat.Er * 0.001 *  wat.Area) |
| UpStrmQ | double | mm  | Runon added to OFE | sum(wat.UpStrmQ * 0.001 *  wat.Area) / Area * 1000 |
| SubRIn | double | mm  | Subsurface runon added to OFE | sum(wat.SubRIn * 0.001 *  wat.Area) / Area * 1000 |
| Total-Soil Water | double | mm  | Unfrozen water in soil profile | sum(wat.Total-Soil Water * 0.001 *  wat.Area) / Area * 1000 |
| SoilWaterTotal | double | mm | Area-weighted full-profile soil water (`watcon + frozwt`) from WEPP | sum(wat.SoilWaterTotal * 0.001 * wat.Area) / Area * 1000 when available, else null |
| ProfileDepth | double | mm | Area-weighted full soil profile depth (`solthk(nsl)`) | sum(wat.ProfileDepth * 0.001 * wat.Area) / Area * 1000 when available, else null |
| ProfilePorosityCap | double | mm | Area-weighted full-profile porosity storage capacity (`sum(por*dg)`) | sum(wat.ProfilePorosityCap * 0.001 * wat.Area) / Area * 1000 when available, else null |
| ProfileFCStore | double | mm | Area-weighted full-profile field-capacity storage (`sum(thetfc*dg)`) | sum(wat.ProfileFCStore * 0.001 * wat.Area) / Area * 1000 when available, else null |
| ProfileWPStore | double | mm | Area-weighted full-profile wilting-point storage (`sum(thetdr*dg)`) | sum(wat.ProfileWPStore * 0.001 * wat.Area) / Area * 1000 when available, else null |
| TSMF | double | frac | Area-weighted true soil moisture fraction (full profile) | sum(soil.TSMF * wat.Area where soil.TSMF not null) / sum(wat.Area where soil.TSMF not null) |
| frozwt | double | mm  | Frozen water in soil profile | sum(wat.frozwt * 0.001 *  wat.Area) / Area * 1000 |
| Snow-Water | double | mm  | Water in surface snow | sum(wat.Snow-Water * 0.001 *  wat.Area) / Area * 1000 |
| QRain | double | mm | Area-weighted rain-generated runoff partition | sum(element.QRain * 0.001 * wat.Area where element.QRain not null) / sum(wat.Area where element.QRain not null) * 1000 |
| QSnow | double | mm | Area-weighted snow-generated runoff partition | sum(element.QSnow * 0.001 * wat.Area where element.QSnow not null) / sum(wat.Area where element.QSnow not null) * 1000 |
| Tile | double | mm  | Tile drainage | sum(wat.Tile * 0.001 *  wat.Area) / Area * 1000 |
| Irr | double | mm  | Irrigation | sum(wat.Irr * 0.001 *  wat.Area) / Area * 1000 |
| Precipitation | double | mm | Precipitation | P / Area * 1000 |
| Rain+Melt | double | mm | Rainfall+Irrigation+Snowmelt | RM / Area * 1000 |
| Percolation | double | mm | Deep percolation | Dp / Area * 1000 |
| Lateral Flow | double | mm  | Lateral subsurface flow | latqcc / Area * 1000 |
| Runoff | double | mm  | Daily runoff depth from PASS runoff volume | runvol / Area * 1000 |
| Transpiration | double | mm | Plant transpiration (Ep depth normalized) | Ep / Area * 1000 |
| Evaporation | double | mm | Soil (Es) + Residue (Er) evaporation (depth normalized) | (Es+Er) / Area * 1000 |
| ET | double | mm | Total ET (depth normalized Ep+Es+Er)  | (Ep+Es+Er) / Area * 1000 |
| Interception | double | mm | Daily canopy/residue interception flux (producer-authoritative when present) | sum(wat.Interception * 0.001 * wat.Area) / Area * 1000 when available; else `0` |
| Baseflow | double | mm | Baseflow | reimplement running calc from totalwatsed.py provided below |
| Aquifer losses | double | mm | Aquifer losses | reimplement running calc from totalwatsed.py provided below |
| Reservoir Volume | double | mm | Reservoir Volume | reimplement running calc from totalwatsed.py provided below |
| Streamflow | double | mm | Streamflow | Runoff + Lateral Flow + Baseflow |
| wind_transport | double | tonne | Ash transported by wind | Aggregated mass from first-year ash hillslope outputs |
| wind_transport_per_ha | double | tonne/ha | Ash transported by wind per unit area | wind_transport / contributing area_ha |
| wind_transport_black | double | tonne | Black ash transported by wind | Aggregated black-ash mass from first-year ash outputs |
| wind_transport_black_per_ha | double | tonne/ha | Black ash transported by wind per black-ash area | wind_transport_black / black_ash_area_ha |
| wind_transport_white | double | tonne | White ash transported by wind | Aggregated white-ash mass from first-year ash outputs |
| wind_transport_white_per_ha | double | tonne/ha | White ash transported by wind per white-ash area | wind_transport_white / white_ash_area_ha |
| water_transport | double | tonne | Ash transported by water | Aggregated mass from first-year ash hillslope outputs |
| water_transport_per_ha | double | tonne/ha | Ash transported by water per unit area | water_transport / contributing area_ha |
| water_transport_black | double | tonne | Black ash transported by water | Aggregated black-ash mass from first-year ash outputs |
| water_transport_black_per_ha | double | tonne/ha | Black ash transported by water per black-ash area | water_transport_black / black_ash_area_ha |
| water_transport_white | double | tonne | White ash transported by water | Aggregated white-ash mass from first-year ash outputs |
| water_transport_white_per_ha | double | tonne/ha | White ash transported by water per white-ash area | water_transport_white / white_ash_area_ha |
| ash_transport | double | tonne | Total ash transported (wind + water) | Aggregated mass from first-year ash hillslope outputs |
| ash_transport_per_ha | double | tonne/ha | Total ash transported per unit area | ash_transport / contributing area_ha |
| ash_transport_black | double | tonne | Black ash transported (wind + water) | Aggregated black-ash mass from first-year ash outputs |
| ash_transport_black_per_ha | double | tonne/ha | Black ash transported per black-ash area | ash_transport_black / black_ash_area_ha |
| ash_transport_white | double | tonne | White ash transported (wind + water) | Aggregated white-ash mass from first-year ash outputs |
| ash_transport_white_per_ha | double | tonne/ha | White ash transported per white-ash area | ash_transport_white / white_ash_area_ha |
| transportable_ash | double | tonne | Ash mass still available for transport | Aggregated transportable ash mass after daily updates |
| transportable_ash_per_ha | double | tonne/ha | Ash mass still available per unit area | transportable_ash / contributing area_ha |
| ash_vol_conc | double | m^3/m^3 | Volumetric ash concentration | ash_solids_volume / runvol |
| sed+ash_vol_conc | double | m^3/m^3 | Combined sediment + ash volumetric concentration | (sed_solids_volume + ash_solids_volume) / runvol |
| ash_black_pct_by_vol | double | percent | Black ash fraction by solids volume | 100 * ash_black_solids_volume / ash_solids_volume |

Ash metrics are harvested from the per-hillslope ash transport parquet files under
``ash/H{wepp_id}_ash.parquet``. Each file is loaded with `read_hillslope_out_fn`,
filtered to the first fire year (``year0 == year``), and converted from
tonne-per-hectare to total tonnes using the watershed hillslope area. The
aggregator respects the optional ``wepp_ids`` filter so channel-level exports
receive localized totals, recomputes per-area ratios after summing, and derives
`ash_vol_conc`, `sed+ash_vol_conc`, and `ash_black_pct_by_vol` from ash solids
volume using ash-type bulk densities (from `Ash.meta` when available, else
defaults).

Division guard semantics follow implementation behavior in `totalwatsed3.py`:
- Depth conversions from volume use safe division by `Area`; zero/absent area yields `0.0`.
- `*_per_ha` ash ratios and volumetric concentration fields use safe division; zero denominator yields `0.0`.
- Null-aware weighted optional terms (`TSMF`, `QRain`, `QSnow`) remain `null` when no valid contributing area is available.


totalwatsed.py
```
...
    # calculate Res volume, baseflow, and aquifer losses
    _res_vol = np.zeros(d.shape[0])   # Reservoir Volume
    _res_vol[0] = baseflow_opts.gwstorage
    _baseflow = np.zeros(d.shape[0])  # Baseflow
    _aq_losses = np.zeros(d.shape[0])  # Aquifer Losses

    for i, perc in enumerate(d['Percolation (mm)']):  # Dp
        if i == 0:
            continue

        _aq_losses[i - 1] = _res_vol[i - 1] * baseflow_opts.dscoeff 
        _res_vol[i] = _res_vol[i - 1] - _baseflow[i - 1] + perc - _aq_losses[i - 1]
        _baseflow[i] = _res_vol[i] * baseflow_opts.bfcoeff
```

## interchange specs for relevant input files from `generate_interchange_documentation`


### `H.pass.parquet`

Event/subevent sediment and runoff delivery by hillslope (PASS).

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| wepp_id | int32 |  |  |
| event | string |  | Record type: EVENT, SUBEVENT, NO EVENT |
| year | int16 |  |  |
| sim_day_index | int32 |  |  |
| julian | int16 |  |  |
| month | int8 |  |  |
| day_of_month | int8 |  |  |
| water_year | int16 |  |  |
| dur | double | s | Storm duration |
| tcs | double | h | Overland flow time of concentration |
| oalpha | double | unitless | Overland flow alpha parameter |
| runoff | double | m | Runoff depth |
| runvol | double | m^3 | Runoff volume |
| sbrunf | double | m | Subsurface runoff depth |
| sbrunv | double | m^3 | Subsurface runoff volume |
| drainq | double | m/day | Drainage flux |
| drrunv | double | m^3 | Tile Drainage volume |
| peakro | double | m^3/s | Peak runoff rate |
| tdet | double | kg | Total detachment |
| tdep | double | kg | Total deposition |
| sedcon_1 | double | kg/m^3 | Sediment concentration 1 |
| sedcon_2 | double | kg/m^3 | Sediment concentration 2 |
| sedcon_3 | double | kg/m^3 | Sediment concentration 3 |
| sedcon_4 | double | kg/m^3 | Sediment concentration 4 |
| sedcon_5 | double | kg/m^3 | Sediment concentration 5 |
| clot | double | m^3/s | Friction flow 1 |
| slot | double | % | % of exiting sediment in the silt size class |
| saot | double | % | % of exiting sediment in the small aggregate size class |
| laot | double | % | % of exiting sediment in the large aggregate size class |
| sdot | double | % | % of exiting sediment in the sand size class |
| gwbfv | double |  | Groundwater baseflow |
| gwdsv | double |  | Groundwater deep seepage |


### `H.wat.parquet`

Hillslope water balance per OFE; aligns with wat.out content.

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| wepp_id | int32 |  |  |
| ofe_id | int16 |  |  |
| year | int16 |  |  |
| sim_day_index | int32 |  | 1-indexed simulation day |
| julian | int16 |  |  |
| month | int8 |  |  |
| day_of_month | int8 |  |  |
| water_year | int16 |  |  |
| OFE | int16 |  |  |
| P | double | mm | Precipitation |
| RM | double | mm | Rainfall+Irrigation+Snowmelt |
| Q | double | mm | Daily runoff over eff length |
| Ep | double | mm | Plant transpiration |
| Es | double | mm | Soil evaporation |
| Er | double | mm | Residue evaporation |
| Dp | double | mm | Deep percolation |
| UpStrmQ | double | mm | Runon added to OFE |
| SubRIn | double | mm | Subsurface runon added to OFE |
| latqcc | double | mm | Lateral subsurface flow |
| Total-Soil Water | double | mm | Unfrozen water in soil profile |
| frozwt | double | mm | Frozen water in soil profile |
| Snow-Water | double | mm | Water in surface snow |
| QOFE | double | mm | Daily runoff scaled to single OFE |
| Tile | double | mm | Tile drainage |
| Irr | double | mm | Irrigation |
| Area | double | m^2 | Area that depths apply over |
| SoilWaterTotal | double | mm | Full-profile soil water (`watcon + frozwt`); optional additive term |
| ProfileDepth | double | mm | Full-profile depth (`solthk(nsl)`); optional additive term |
| ProfilePorosityCap | double | mm | Full-profile porosity capacity (`sum(por*dg)`); optional additive term |
| ProfileFCStore | double | mm | Full-profile field-capacity storage (`sum(thetfc*dg)`); optional additive term |
| ProfileWPStore | double | mm | Full-profile wilting-point storage (`sum(thetdr*dg)`); optional additive term |
| Interception | double | mm | Daily canopy/residue interception flux (`I`); optional additive outflow term |
