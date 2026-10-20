# Interchange Documentation

_Interchange Version: unknown (manifest missing; documentation generator 1.2)_

## Understanding these outputs

This is a run-specific column reference with at most three sample rows per file. For interpretation, open WEPPcloud Help (Usersum) and search for **Understanding water balance and runoff** or **Water and PASS variables**. The same guides are linked from WEPP Results.

H.wat contains daily native hillslope/OFE rows. Area is the local OFE area, not the denominator of every depth: terminal Q is physical whole-hill runoff; terminal latqcc needs terminal-area weighting; ET and Dp need all-OFE area weighting. H.pass is threshold-filtered delivery, not a complete physical water budget.

Interchange version describes schema layout, not the model executable or report accounting version. A missing manifest does not identify the original file version. Metadata below is read from the actual files and may retain historical descriptions or incorrect unit labels (notably PASS sediment fractions). Regenerating this README does not rewrite data, refresh old reports, or certify producer normalization or accounting provenance.

## Hillslope Products

### `H.wat.parquet`

Daily water fields per native hillslope/OFE, including hourly-model runs; local and cumulative depths require different aggregation.

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
| Q | double | mm | Producer-normalized cumulative runoff; terminal Q is physical whole-hillslope depth for supported hillslope writers; do not area-scale terminal Q again |
| Ep | double | mm | Plant transpiration |
| Es | double | mm | Soil evaporation |
| Er | double | mm | Residue evaporation |
| Dp | double | mm | Deep percolation |
| UpStrmQ | double | mm | Runon added to OFE |
| SubRIn | double | mm | Subsurface runon added to OFE |
| latqcc | double | mm | Local OFE lateral outflow depth; whole-hill export uses terminal value times terminal area divided by full hill area |
| Total-Soil Water | double | mm | Unfrozen water in soil profile |
| frozwt | double | mm | Frozen water in soil profile |
| Snow-Water | double | mm | Water in surface snow |
| QOFE | double | mm | Version-sensitive runoff diagnostic: historical local normalization or current Q alias; not a universal local depth |
| Tile | double | mm | Tile drainage |
| Irr | double | mm | Irrigation |
| Area | double | m^2 | Local OFE area; not the denominator of cumulative Q |
| SoilWaterTotal | double | mm | Full-profile soil water depth (watcon + frozwt), optional producer-authoritative term |
| ProfileDepth | double | mm | Full soil profile depth (solthk(nsl)), optional producer-authoritative term |
| ProfilePorosityCap | double | mm | Full-profile porosity storage capacity (sum(por * dg)), optional producer-authoritative term |
| ProfileFCStore | double | mm | Full-profile field-capacity storage (sum(thetfc * dg)), optional producer-authoritative term |
| ProfileWPStore | double | mm | Full-profile wilting-point storage (sum(thetdr * dg)), optional producer-authoritative term |
| InterceptionStorage | double | mm | Plant/residue interception carryover storage (pintlv + resint), optional producer-authoritative term |

Preview:

wepp_id | ofe_id | year | sim_day_index | julian | month | day_of_month | water_year | OFE | P | RM | Q | Ep | Es | Er | Dp | UpStrmQ | SubRIn | latqcc | Total-Soil Water | frozwt | Snow-Water | QOFE | Tile | Irr | Area | SoilWaterTotal | ProfileDepth | ProfilePorosityCap | ProfileFCStore | ProfileWPStore | InterceptionStorage
--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---
 |  |  |  |  |  |  |  |  | mm | mm | mm | mm | mm | mm | mm | mm | mm | mm | mm | mm | mm | mm | mm | mm | m^2 | mm | mm | mm | mm | mm | mm
1 | 1 | 2000 | 1 | 1 | 1 | 1 | 2000 | 1 | 12.2 | 0 | 0 | 0.56 | 0 | 0 | 0.24 | 0 | 0 | 0.34 | 566.7 | 0 | 12.2 | 0 | 0 | 0 | 105300 |  |  |  |  |  |
1 | 1 | 2000 | 2 | 2 | 1 | 2 | 2000 | 1 | 5.8 | 0 | 0 | 0.41 | 0 | 0 | 0.24 | 0 | 0 | 0.56 | 565.48 | 0 | 18 | 0 | 0 | 0 | 105300 |  |  |  |  |  |
1 | 1 | 2000 | 3 | 3 | 1 | 3 | 2000 | 1 | 0 | 0 | 0 | 0.52 | 0 | 0 | 0.24 | 0 | 0 | 0.82 | 563.9 | 0 | 18 | 0 | 0 | 0 | 105300 |  |  |  |  |  |

### `H.pass.parquet`

Event/subevent sediment and runoff delivery by hillslope (PASS).

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| wepp_id | int32 |  |  |
| event | string |  | Record type: EVENT, SUBEVENT, NO EVENT |
| year | int16 |  |  |
| sim_day_index | int32 |  | 1-indexed simulation day since start year |
| julian | int16 |  |  |
| month | int8 |  |  |
| day_of_month | int8 |  |  |
| water_year | int16 |  |  |
| dur | double | s | Storm duration |
| tcs | double | h | Overland flow time of concentration |
| oalpha | double | unitless | Overland flow alpha parameter |
| runoff | double | m | EVENT internal terminal runoff depth on producer effective-flow basis; use runvol for area aggregation |
| runvol | double | m^3 | Threshold-filtered PASS surface runoff volume; not all physical WAT runoff |
| sbrunf | double | m | Terminal local subsurface depth when emitted by PASS event filtering |
| sbrunv | double | m^3 | Exported terminal subsurface volume after PASS event filtering |
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
| clot | double | m^3/s | Clay sediment fraction (dimensionless); legacy m^3/s unit label is incorrect |
| slot | double | % | Silt sediment fraction (dimensionless); legacy percent unit label is incorrect |
| saot | double | % | Small aggregate sediment fraction (dimensionless); legacy percent unit label is incorrect |
| laot | double | % | Large aggregate sediment fraction (dimensionless); legacy percent unit label is incorrect |
| sdot | double | % | Sand sediment fraction (dimensionless); legacy percent unit label is incorrect |
| gwbfv | double |  | Daily groundwater baseflow volume in m^3; legacy machine-unit metadata absent |
| gwdsv | double |  | Daily groundwater deep-seepage volume in m^3; legacy machine-unit metadata absent |

Preview:

wepp_id | event | year | sim_day_index | julian | month | day_of_month | water_year | dur | tcs | oalpha | runoff | runvol | sbrunf | sbrunv | drainq | drrunv | peakro | tdet | tdep | sedcon_1 | sedcon_2 | sedcon_3 | sedcon_4 | sedcon_5 | clot | slot | saot | laot | sdot | gwbfv | gwdsv
--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---
 |  |  |  |  |  |  |  | s | h | unitless | m | m^3 | m | m^3 | m/day | m^3 | m^3/s | kg | kg | kg/m^3 | kg/m^3 | kg/m^3 | kg/m^3 | kg/m^3 | m^3/s | % | % | % | % |  |
1 | SUBEVENT | 2000 | 1 | 1 | 1 | 1 | 2000 | 0 | 0 | 0 | 0 | 0 | 0.00033568 | 35.348 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1.0311 | 0
1 | SUBEVENT | 2000 | 2 | 2 | 1 | 2 | 2000 | 0 | 0 | 0 | 0 | 0 | 0.00056243 | 59.224 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2.021 | 0
1 | SUBEVENT | 2000 | 3 | 3 | 1 | 3 | 2000 | 0 | 0 | 0 | 0 | 0 | 0.0008228 | 86.641 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2.9712 | 0

## Watershed Products
