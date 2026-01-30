# Interchange Documentation

_Interchange Version: 1.2_

## Hillslope Products

### `H.element.parquet`

Daily hillslope element hydrology and sediment metrics.

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| wepp_id | int32 |  |  |
| ofe_id | int16 |  |  |
| year | int16 |  |  |
| julian | int16 |  |  |
| month | int8 |  |  |
| day_of_month | int8 |  |  |
| water_year | int16 |  |  |
| OFE | int16 |  |  |
| Precip | double | mm |  |
| Runoff | double | mm |  |
| EffInt | double | mm/h | Effective rainfall intensity |
| PeakRO | double | mm/h | Peak runoff rate |
| EffDur | double | h |  |
| Enrich | double |  | Sediment enrichment ratio |
| Keff | double | mm/h | Effective hydraulic conductivity |
| Sm | double | mm |  |
| LeafArea | double |  | Leaf area index |
| CanHgt | double | m | Canopy height |
| Cancov | double | % | Canopy cover |
| IntCov | double | % | Interrill cover |
| RilCov | double | % | Rill cover |
| LivBio | double | kg/m^2 |  |
| DeadBio | double | kg/m^2 |  |
| Ki | double | kg s/m^4 | Interrill erodibility |
| Kr | double | s/m | Rill erodibility |
| Tcrit | double |  |  |
| RilWid | double | m |  |
| SedLeave | double | kg/m |  |

Preview:

wepp_id | ofe_id | year | julian | month | day_of_month | water_year | OFE | Precip | Runoff | EffInt | PeakRO | EffDur | Enrich | Keff | Sm | LeafArea | CanHgt | Cancov | IntCov | RilCov | LivBio | DeadBio | Ki | Kr | Tcrit | RilWid | SedLeave
--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---
 |  |  |  |  |  |  |  | mm | mm | mm/h | mm/h | h |  | mm/h | mm |  | m | % | % | % | kg/m^2 | kg/m^2 | kg s/m^4 | s/m |  | m | kg/m
1 | 1 | 2010 | 1 | 1 | 1 | 2010 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 30 | 330.42 | 5 | 0.6 | 99.9 | 60 | 60 | 6.908 | 0.183 | 0.03 | 0.034 | 2 | 0.15 | 0
1 | 1 | 2010 | 15 | 1 | 15 | 2010 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 30 | 349.904 | 5 | 0.6 | 99.9 | 60 | 60 | 6.908 | 0.183 | 0.03 | 0.034 | 2 | 0.15 | 0
1 | 1 | 2010 | 32 | 2 | 1 | 2010 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 30 | 362.029 | 5 | 0.6 | 99.9 | 60.001 | 60.001 | 6.908 | 0.183 | 0.03 | 0.034 | 2 | 0.15 | 0

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

Preview:

wepp_id | ofe_id | year | sim_day_index | julian | month | day_of_month | water_year | OFE | P | RM | Q | Ep | Es | Er | Dp | UpStrmQ | SubRIn | latqcc | Total-Soil Water | frozwt | Snow-Water | QOFE | Tile | Irr | Area
--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---
 |  |  |  |  |  |  |  |  | mm | mm | mm | mm | mm | mm | mm | mm | mm | mm | mm | mm | mm | mm | mm | mm | m^2
1 | 1 | 2010 | 1 | 1 | 1 | 1 | 2010 | 1 | 12.2 | 4.07 | 0 | 0.81 | 0.1 | 0 | 0.24 | 0 | 0 | 0 | 330.42 | 0 | 8.13 | 0 | 0 | 0 | 100776
1 | 1 | 2010 | 2 | 2 | 1 | 2 | 2010 | 1 | 0 | 0 | 0 | 0.61 | 0.07 | 0 | 0.24 | 0 | 0 | 0.03 | 329.46 | 0 | 8.13 | 0 | 0 | 0 | 100776
1 | 1 | 2010 | 3 | 3 | 1 | 3 | 2010 | 1 | 2.9 | 0 | 0 | 0.57 | 0.07 | 0 | 0.24 | 0 | 0 | 0.07 | 328.51 | 0 | 11.03 | 0 | 0 | 0 | 100776

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

Preview:

wepp_id | event | year | sim_day_index | julian | month | day_of_month | water_year | dur | tcs | oalpha | runoff | runvol | sbrunf | sbrunv | drainq | drrunv | peakro | tdet | tdep | sedcon_1 | sedcon_2 | sedcon_3 | sedcon_4 | sedcon_5 | clot | slot | saot | laot | sdot | gwbfv | gwdsv
--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---
 |  |  |  |  |  |  |  | s | h | unitless | m | m^3 | m | m^3 | m/day | m^3 | m^3/s | kg | kg | kg/m^3 | kg/m^3 | kg/m^3 | kg/m^3 | kg/m^3 | m^3/s | % | % | % | % |  | 
1 | SUBEVENT | 2010 | 1 | 1 | 1 | 1 | 2010 | 0 | 0 | 0 | 0 | 0 | 3.2923e-06 | 0.33178 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.98679 | 0
1 | SUBEVENT | 2010 | 2 | 2 | 1 | 2 | 2010 | 0 | 0 | 0 | 0 | 0 | 3.1967e-05 | 3.2215 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1.9341 | 0
1 | SUBEVENT | 2010 | 3 | 3 | 1 | 3 | 2010 | 0 | 0 | 0 | 0 | 0 | 6.5672e-05 | 6.6182 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2.8435 | 0

### `H.loss.parquet`

Average annual particle class fractions at the hillslope outlet.

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| wepp_id | int32 |  |  |
| class_id | int8 |  |  |
| Class | int8 |  | Sediment particle size class |
| Diameter | double | mm |  |
| Specific Gravity | double |  |  |
| % Sand | double | % |  |
| % Silt | double | % |  |
| % Clay | double | % |  |
| % O.M. | double | % |  |
| Sediment Fraction | double |  |  |
| In Flow Exiting | double |  |  |

Preview:

wepp_id | class_id | Class | Diameter | Specific Gravity | % Sand | % Silt | % Clay | % O.M. | Sediment Fraction | In Flow Exiting
--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---
 |  |  | mm |  | % | % | % | % |  | 
1 | 1 | 1 | 0.002 | 2.6 | 0 | 0 | 100 | 17.1 | 0.045 | 0.085
1 | 2 | 2 | 0.01 | 2.65 | 0 | 100 | 0 | 0 | 0.088 | 0.165
1 | 3 | 3 | 0.03 | 1.8 | 0 | 69.3 | 30.7 | 5.3 | 0.307 | 0.539

### `H.soil.parquet`

Daily soil state variables per OFE from soil.dat.

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
| Poros | double | % | Soil porosity |
| Keff | double | mm/hr | Effective hydraulic conductivity |
| Suct | double | mm | Suction across wetting front |
| FC | double | mm/mm | Field capacity |
| WP | double | mm/mm | Wilting point |
| Rough | double | mm | Surface roughness |
| Ki | double | adjsmt | Interrill erodibility adjustment factor |
| Kr | double | adjsmt | Rill erodibility adjustment factor |
| Tauc | double | adjsmt | Critical shear stress adjustment factor |
| Saturation | double | frac | Saturation as fraction (10mm profile) |
| TSW | double | mm | Total soil water |

Preview:

wepp_id | ofe_id | year | sim_day_index | julian | month | day_of_month | water_year | OFE | Poros | Keff | Suct | FC | WP | Rough | Ki | Kr | Tauc | Saturation | TSW
--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---
 |  |  |  |  |  |  |  |  | % | mm/hr | mm | mm/mm | mm/mm | mm | adjsmt | adjsmt | adjsmt | frac | mm
1 | 1 | 2010 | 1 | 1 | 1 | 1 | 2010 | 1 | 51.45 | 30 | 10.87 | 0.23 | 0.1 | 20 | 0.03 | 0.56 | 2 | 0.48 | 24.79
1 | 1 | 2010 | 2 | 2 | 1 | 2 | 2010 | 1 | 51.45 | 30 | 10.37 | 0.23 | 0.1 | 20 | 0.03 | 0.56 | 2 | 0.46 | 23.54
1 | 1 | 2010 | 3 | 3 | 1 | 3 | 2010 | 1 | 51.45 | 30 | 12.15 | 0.23 | 0.1 | 20 | 0.03 | 0.56 | 2 | 0.45 | 23.12

### `H.ebe.parquet`

Event-by-event hillslope runoff and sediment summaries.

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| wepp_id | int32 |  |  |
| year | int16 |  |  |
| sim_day_index | int32 |  | 1-indexed simulation day |
| month | int8 |  |  |
| day_of_month | int8 |  |  |
| julian | int16 |  |  |
| water_year | int16 |  |  |
| Precip | double | mm | Storm precipitation depth |
| Runoff | double | mm | Runoff depth scaled by effective flow length |
| IR-det | double | kg/m^2 | Weighted interrill detachment over the hillslope |
| Av-det | double | kg/m^2 | Average soil detachment across detachment regions |
| Mx-det | double | kg/m^2 | Maximum soil detachment across detachment regions |
| Det-point | double | m | Location of maximum soil detachment along hillslope |
| Av-dep | double | kg/m^2 | Average sediment deposition across deposition regions |
| Max-dep | double | kg/m^2 | Maximum sediment deposition across deposition regions |
| Dep-point | double | m | Location of maximum sediment deposition along hillslope |
| Sed.Del | double | kg/m | Storm sediment load per unit width at hillslope outlet |
| ER | double |  | Specific surface enrichment ratio for event sediment |
| Det-Len | double | m | Effective detachment flow length |
| Dep-Len | double | m | Effective deposition flow length |

Preview:

wepp_id | year | sim_day_index | month | day_of_month | julian | water_year | Precip | Runoff | IR-det | Av-det | Mx-det | Det-point | Av-dep | Max-dep | Dep-point | Sed.Del | ER | Det-Len | Dep-Len
--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---
 |  |  |  |  |  |  | mm | mm | kg/m^2 | kg/m^2 | kg/m^2 | m | kg/m^2 | kg/m^2 | m | kg/m |  | m | m
1 | 2010 | 153 | 6 | 2 | 153 | 2010 | 33.6 | 0.1 | 0 | 0 | 0 | 73.9 | 0 | 0 | 0 | 0 | 1.5 |  | 
1 | 2019 | 3384 | 4 | 7 | 97 | 2019 | 28 | 0 | 0 | 0 | 0 | 94.8 | 0 | 0 | 0 | 0 | 1.5 |  | 
1 | 2019 | 3385 | 4 | 8 | 98 | 2019 | 28.3 | 0.5 | 0 | 0 | 0 | 75.8 | 0 | 0 | 0 | 0 | 1.5 |  | 

## Watershed Products

### `chan.out.parquet`

Peak discharge report for watershed channels (chan.out).

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| year | int16 |  | Calendar year |
| simulation_year | int16 |  | Simulation year from chan.out |
| julian | int16 |  | Julian day reported by WEPP |
| month | int8 |  | Calendar month derived from Julian day |
| day_of_month | int8 |  | Calendar day-of-month derived from Julian day |
| water_year | int16 |  | Water year computed from Julian day |
| Elmt_ID | int32 |  | Channel element identifier |
| Chan_ID | int32 |  | Channel ID reported by WEPP |
| Time (s) | double | s | Time to peak discharge |
| Peak_Discharge (m^3/s) | double | m^3/s | Peak discharge within the reporting interval |

Preview:

year | simulation_year | julian | month | day_of_month | water_year | Elmt_ID | Chan_ID | Time (s) | Peak_Discharge (m^3/s)
--- | --- | --- | --- | --- | --- | --- | --- | --- | ---
 |  |  |  |  |  |  |  | s | m^3/s
2010 | 2010 | 1 | 1 | 1 | 2010 | 94 | 27 | 600 | 0.0389
2010 | 2010 | 2 | 1 | 2 | 2010 | 94 | 27 | 4200 | 0.0707
2010 | 2010 | 3 | 1 | 3 | 2010 | 94 | 27 | 4200 | 0.105

### `chanwb.parquet`

Daily channel routing water balance.

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| year | int16 |  | Calendar year |
| simulation_year | int16 |  | Simulation year from chanwb.out |
| julian | int16 |  | Julian day reported by WEPP |
| month | int8 |  | Calendar month derived from Julian day |
| day_of_month | int8 |  | Calendar day-of-month derived from Julian day |
| water_year | int16 |  | Water year computed from Julian day |
| Elmt_ID | int32 |  | Channel element identifier |
| Chan_ID | int32 |  | Channel ID reported by WEPP |
| Inflow (m^3) | double | m^3 | Total inflow above channel outlet, includes baseflow, all sources |
| Outflow (m^3) | double | m^3 | Water flow out of channel outlet |
| Storage (m^3) | double | m^3 | Water surface storage at the end of the day |
| Baseflow (m^3) | double | m^3 | Portion of inflow from baseflow |
| Loss (m^3) | double | m^3 | Transmission loss in channel, infiltration |
| Balance (m^3) | double | m^3 | Water balance error at end of day (inflow - outflow - loss - Δstorage) |

Preview:

year | simulation_year | julian | month | day_of_month | water_year | Elmt_ID | Chan_ID | Inflow (m^3) | Outflow (m^3) | Storage (m^3) | Baseflow (m^3) | Loss (m^3) | Balance (m^3)
--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---
 |  |  |  |  |  |  |  | m^3 | m^3 | m^3 | m^3 | m^3 | m^3
2010 | 2010 | 1 | 1 | 1 | 2010 | 94 | 27 | 3367.44 | 3362.55 | 22.9 | 0 | 4.88 | 0
2010 | 2010 | 2 | 1 | 2 | 2010 | 94 | 27 | 6044.85 | 6029.68 | 34.52 | 0 | 3.55 | 0
2010 | 2010 | 3 | 1 | 3 | 2010 | 94 | 27 | 8937.08 | 8924.02 | 45.16 | 0 | 2.42 | 0

### `chnwb.parquet`

Channel OFE water balance (chnwb.txt).

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| wepp_id | int32 |  | Channel (OFE) identifier |
| julian | int16 |  | Julian day |
| year | int16 |  | Calendar year |
| simulation_year | int16 |  | Simulation year value from input file |
| month | int8 |  | Calendar month |
| day_of_month | int8 |  | Calendar day of month |
| water_year | int16 |  | Computed water year |
| OFE | int16 |  | Channel OFE index |
| J | int16 |  | Julian day as reported |
| Y | int16 |  | Simulation year as reported |
| P (mm) | double | mm | precipitation |
| RM (mm) | double | mm | rainfall + irrigation + snowmelt |
| Q (mm) | double | mm | daily runoff over effective length |
| Ep (mm) | double | mm | plant transpiration |
| Es (mm) | double | mm | soil evaporation |
| Er (mm) | double | mm | residue evaporation |
| Dp (mm) | double | mm | deep percolation |
| UpStrmQ (mm) | double | mm | Runon added to OFE |
| SubRIn (mm) | double | mm | Subsurface runon added to OFE |
| latqcc (mm) | double | mm | lateral subsurface flow |
| Total Soil Water (mm) | double | mm | Unfrozen water in soil profile |
| frozwt (mm) | double | mm | Frozen water in soil profile |
| Snow Water (mm) | double | mm | Water in surface snow |
| QOFE (mm) | double | mm | Daily runoff scaled to single OFE |
| Tile (mm) | double | mm | Tile drainage |
| Irr (mm) | double | mm | Irrigation |
| Surf (mm) | double | mm | Surface storage |
| Base (mm) | double | mm | Portion of runon from external baseflow |
| Area (m^2) | double | m^2 | Area that depths apply over |

Preview:

wepp_id | julian | year | simulation_year | month | day_of_month | water_year | OFE | J | Y | P (mm) | RM (mm) | Q (mm) | Ep (mm) | Es (mm) | Er (mm) | Dp (mm) | UpStrmQ (mm) | SubRIn (mm) | latqcc (mm) | Total Soil Water (mm) | frozwt (mm) | Snow Water (mm) | QOFE (mm) | Tile (mm) | Irr (mm) | Surf (mm) | Base (mm) | Area (m^2)
--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---
 |  |  |  |  |  |  |  |  |  | mm | mm | mm | mm | mm | mm | mm | mm | mm | mm | mm | mm | mm | mm | mm | mm | mm | mm | m^2
1 | 1 | 2010 | 2010 | 1 | 1 | 2010 | 1 | 1 | 2010 | 12.7 | 0 | 93.0983 | 0 | 0.88 | 0 | 0 | 107.454 | 0 | 0 | 180.21 | 0.11 | 12.7 | 93.0983 | 0 | 0 | 0.87 | 0 | 395.68
2 | 1 | 2010 | 2010 | 1 | 1 | 2010 | 2 | 1 | 2010 | 12.7 | 0 | 0 | 0 | 0.88 | 0 | 0 | 4.15367 | 0 | 0 | 170.01 | 0.11 | 12.7 | 0 | 0 | 0 | 0.03 | 0 | 605.84
3 | 1 | 2010 | 2010 | 1 | 1 | 2010 | 3 | 1 | 2010 | 12.7 | 0 | 2486.33 | 0 | 0.88 | 0 | 0 | 2500.68 | 0 | 0 | 180.21 | 0.11 | 12.7 | 2486.33 | 0 | 0 | 6.85 | 0 | 35.04

### `ebe_pw0.parquet`

Watershed event-by-event runoff and sediment delivery.

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| year | int16 |  | Calendar year |
| sim_day_index | int32 |  | 1-indexed simulation day |
| simulation_year | int16 |  | WEPP simulation year reported in output |
| month | int8 |  | Calendar month |
| day_of_month | int8 |  | Calendar day of month |
| julian | int16 |  | Julian day from WEPP output |
| water_year | int16 |  | Water year derived from year/julian |
| precip | double | mm | Watershed precipitation depth for the event |
| runoff_volume | double | m^3 | Watershed runoff volume for the event |
| peak_runoff | double | m^3/s | Peak watershed discharge |
| sediment_yield | double | kg | Sediment yield at the watershed outlet |
| soluble_pollutant | double | kg | Soluble pollutant mass delivered at watershed outlet |
| particulate_pollutant | double | kg | Particulate pollutant mass delivered at watershed outlet |
| total_pollutant | double | kg | Total pollutant mass delivered (soluble + particulate) |
| element_id | int32 |  | Channel element identifier (Elmt_ID) |

Preview:

year | sim_day_index | simulation_year | month | day_of_month | julian | water_year | precip | runoff_volume | peak_runoff | sediment_yield | soluble_pollutant | particulate_pollutant | total_pollutant | element_id
--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---
 |  |  |  |  |  |  | mm | m^3 | m^3/s | kg | kg | kg | kg | 
2010 | 1 | 1 | 1 | 1 | 1 | 2010 | 12.7 | 3362.55 | 0.03892 | 179.37 | 0 | 0 | 0 | 94
2010 | 2 | 1 | 1 | 2 | 2 | 2010 | 0 | 6029.68 | 0.07071 | 345.59 | 0 | 0 | 0 | 94
2010 | 3 | 1 | 1 | 3 | 3 | 2010 | 3 | 8924.02 | 0.10453 | 518.56 | 0 | 0 | 0 | 94

### `soil_pw0.parquet`

Watershed soil-profile state variables.

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| wepp_id | int32 |  |  |
| ofe_id | int16 |  |  |
| year | int16 |  |  |
| day | int16 |  |  |
| julian | int16 |  |  |
| month | int8 |  |  |
| day_of_month | int8 |  |  |
| water_year | int16 |  |  |
| OFE | int16 |  |  |
| Poros | double | % | Soil porosity |
| Keff | double | mm/hr | Effective hydraulic conductivity |
| Suct | double | mm | Suction across wetting front |
| FC | double | mm/mm | Field capacity |
| WP | double | mm/mm | Wilting point |
| Rough | double | mm | Surface roughness |
| Ki | double | adjsmt | Interrill erodibility adjustment factor |
| Kr | double | adjsmt | Rill erodibility adjustment factor |
| Tauc | double | adjsmt | Critical shear stress adjustment factor |
| Saturation | double | frac | Saturation as fraction |
| TSW | double | mm | Total soil water |

Preview:

wepp_id | ofe_id | year | day | julian | month | day_of_month | water_year | OFE | Poros | Keff | Suct | FC | WP | Rough | Ki | Kr | Tauc | Saturation | TSW
--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---
 |  |  |  |  |  |  |  |  | % | mm/hr | mm | mm/mm | mm/mm | mm | adjsmt | adjsmt | adjsmt | frac | mm
1 | 1 | 2010 | 1 | 1 | 1 | 1 | 2010 | 1 | 42.32 | 0.21 | 8.54 | 0.21 | 0.1 | 20 | 0.1 | 1 | 1.11 | 0.78 | 32.86
2 | 2 | 2010 | 1 | 1 | 1 | 1 | 2010 | 2 | 42.32 | 0.21 | 8.54 | 0.21 | 0.1 | 20 | 0.1 | 1 | 1.11 | 0.67 | 28.39
3 | 3 | 2010 | 1 | 1 | 1 | 1 | 2010 | 3 | 42.32 | 0.21 | 8.54 | 0.21 | 0.1 | 20 | 0.08 | 1 | 1.11 | 0.78 | 32.86

### `loss_pw0.hill.parquet`

Average annual hillslope loss summary.

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| Type | string |  |  |
| wepp_id | int32 |  |  |
| Runoff Volume | double | m^3 |  |
| Subrunoff Volume | double | m^3 |  |
| Baseflow Volume | double | m^3 |  |
| Soil Loss | double | kg |  |
| Sediment Deposition | double | kg |  |
| Sediment Yield | double | kg |  |
| Hillslope Area | double | ha |  |
| Solub. React. Pollutant | double | kg |  |
| Particulate Pollutant | double | kg |  |
| Total Pollutant | double | kg |  |

Preview:

Type | wepp_id | Runoff Volume | Subrunoff Volume | Baseflow Volume | Soil Loss | Sediment Deposition | Sediment Yield | Hillslope Area | Solub. React. Pollutant | Particulate Pollutant | Total Pollutant
--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---
 |  | m^3 | m^3 | m^3 | kg | kg | kg | ha | kg | kg | kg
Hill | 1 | 0 | 27963 | 8957.4 | 0 | 0 | 0 | 10.1 | 0 | 0 | 0
Hill | 2 | 0 | 31594.6 | 9790.1 | 0 | 0 | 0 | 11.4 | 0 | 0 | 0
Hill | 3 | 0 | 33808.3 | 6550.2 | 0 | 0 | 0 | 10.4 | 0 | 0 | 0

### `loss_pw0.chn.parquet`

Average annual channel loss summary.

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| Type | string |  |  |
| chn_enum | int32 |  |  |
| Discharge Volume | double | m^3 |  |
| Sediment Yield | double | tonne |  |
| Soil Loss | double | kg |  |
| Upland Charge | double | m^3 |  |
| Subsuface Flow Volume | double | m^3 |  |
| Contributing Area | double | ha |  |
| Solub. React. Pollutant | double | kg |  |
| Particulate Pollutant | double | kg |  |
| Total Pollutant | double | kg |  |
| wepp_id | int32 |  |  |

Preview:

Type | chn_enum | Discharge Volume | Sediment Yield | Soil Loss | Upland Charge | Subsuface Flow Volume | Contributing Area | Solub. React. Pollutant | Particulate Pollutant | Total Pollutant | wepp_id
--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---
 |  | m^3 | tonne | kg | m^3 | m^3 | ha | kg | kg | kg | 
Channel | 1 | 100564 | 1.3 | 1313.5 | 100650 | 0.6 | 43.1 | 0 | 0 | 0 | 68
Channel | 2 | 134206 | 3.3 | 3245.8 | 134334 | 0.7 | 49.1 | 0 | 0 | 0 | 69
Channel | 3 | 64108.7 | 0.1 | 73.3 | 64116.3 | 0.2 | 12.4 | 0 | 0 | 0 | 70

### `loss_pw0.out.parquet`

Average annual watershed outlet summary.

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| key | string |  |  |
| value | double |  |  |
| units | string |  |  |

Preview:

key | value | units
--- | --- | ---
 |  | 
Total contributing area to outlet | 676.35 | ha
Avg. Ann. Precipitation volume in contributing area | 6051582 | m^3/yr
Avg. Ann. irrigation volume in contributing area | 0 | m^3/yr

### `loss_pw0.class_data.parquet`

Average annual particle size fractions at the outlet.

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| Class | int8 |  |  |
| Diameter | double | mm |  |
| Specific Gravity | double |  |  |
| Pct Sand | double | % |  |
| Pct Silt | double | % |  |
| Pct Clay | double | % |  |
| Pct OM | double | % |  |
| Fraction In Flow Exiting | double |  |  |

Preview:

Class | Diameter | Specific Gravity | Pct Sand | Pct Silt | Pct Clay | Pct OM | Fraction In Flow Exiting
--- | --- | --- | --- | --- | --- | --- | ---
 | mm |  | % | % | % | % | 
1 | 0.002 | 2.6 | 0 | 0 | 100 | 42.9 | 0.025
2 | 0.01 | 2.65 | 0 | 100 | 0 | 0 | 0.177
3 | 0.03 | 1.8 | 0 | 78.9 | 21.1 | 9 | 0.175

### `loss_pw0.all_years.hill.parquet`

Per-year hillslope loss summary.

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| year | int16 |  |  |
| Type | string |  |  |
| wepp_id | int32 |  |  |
| Runoff Volume | double | m^3 |  |
| Subrunoff Volume | double | m^3 |  |
| Baseflow Volume | double | m^3 |  |
| Soil Loss | double | kg |  |
| Sediment Deposition | double | kg |  |
| Sediment Yield | double | kg |  |
| Solub. React. Pollutant | double | kg |  |
| Particulate Pollutant | double | kg |  |
| Total Pollutant | double | kg |  |

Preview:

year | Type | wepp_id | Runoff Volume | Subrunoff Volume | Baseflow Volume | Soil Loss | Sediment Deposition | Sediment Yield | Solub. React. Pollutant | Particulate Pollutant | Total Pollutant
--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---
 |  |  | m^3 | m^3 | m^3 | kg | kg | kg | kg | kg | kg
2010 | Hill | 1 | 0 | 10818.8 | 8412.4 | 0 | 0 | 0 | 0 | 0 | 0
2010 | Hill | 2 | 0 | 30097.6 | 9540 | 0 | 0 | 0 | 0 | 0 | 0
2010 | Hill | 3 | 0 | 33792.6 | 6997.9 | 0 | 0 | 0 | 0 | 0 | 0

### `loss_pw0.all_years.chn.parquet`

Per-year channel loss summary.

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| year | int16 |  |  |
| Type | string |  |  |
| chn_enum | int32 |  |  |
| Discharge Volume | double | m^3 |  |
| Sediment Yield | double | tonne |  |
| Soil Loss | double | kg |  |
| Upland Charge | double | m^3 |  |
| Subsuface Flow Volume | double | m^3 |  |
| Solub. React. Pollutant | double | kg |  |
| Particulate Pollutant | double | kg |  |
| Total Pollutant | double | kg |  |
| wepp_id | int32 |  |  |

Preview:

year | Type | chn_enum | Discharge Volume | Sediment Yield | Soil Loss | Upland Charge | Subsuface Flow Volume | Solub. React. Pollutant | Particulate Pollutant | Total Pollutant | wepp_id
--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---
 |  |  | m^3 | tonne | kg | m^3 | m^3 | kg | kg | kg | 
2010 | Channel | 1 | 107967 | 1.3 | 1333.9 | 108060 | 0.6 | 0 | 0 | 0 | 68
2010 | Channel | 2 | 123914 | 3 | 2884.3 | 124055 | 0.7 | 0 | 0 | 0 | 69
2010 | Channel | 3 | 66991.5 | 0.4 | 66.2 | 66999.8 | 0.2 | 0 | 0 | 0 | 70

### `loss_pw0.all_years.out.parquet`

Per-year watershed outlet summary.

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| year | int16 |  |  |
| key | string |  |  |
| value | double |  |  |
| units | string |  |  |

Preview:

year | key | value | units
--- | --- | --- | ---
 |  |  | 
2010 | Total contributing area to outlet | 676.35 | ha
2010 | Total precipitation volume in contributing area | 6668780 | m^3
2010 | Total irrigation volume in contributing area | 0 | m^3

### `loss_pw0.all_years.class_data.parquet`

Per-year particle size fractions at the outlet.

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| year | int16 |  |  |
| Class | int8 |  |  |
| Diameter | double | mm |  |
| Specific Gravity | double |  |  |
| Pct Sand | double | % |  |
| Pct Silt | double | % |  |
| Pct Clay | double | % |  |
| Pct OM | double | % |  |
| Fraction In Flow Exiting | double |  |  |

Preview:

year | Class | Diameter | Specific Gravity | Pct Sand | Pct Silt | Pct Clay | Pct OM | Fraction In Flow Exiting
--- | --- | --- | --- | --- | --- | --- | --- | ---
 |  | mm |  | % | % | % | % | 
2010 | 1 | 0.002 | 2.6 | 0 | 0 | 100 | 42.9 | 0.028
2010 | 2 | 0.01 | 2.65 | 0 | 100 | 0 | 0 | 0.179
2010 | 3 | 0.03 | 1.8 | 0 | 78.9 | 21.1 | 9 | 0.19

### `pass_pw0.events.parquet`

Watershed PASS events table (runoff and sediment delivery).

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| event | string |  |  |
| year | int16 |  |  |
| sim_day_index | int32 |  |  |
| julian | int16 |  |  |
| month | int8 |  |  |
| day_of_month | int8 |  |  |
| water_year | int16 |  |  |
| wepp_id | int32 |  |  |
| dur | double |  |  |
| tcs | double |  |  |
| oalpha | double |  |  |
| runoff | double |  |  |
| runvol | double |  |  |
| sbrunf | double |  |  |
| sbrunv | double |  |  |
| drainq | double |  |  |
| drrunv | double |  |  |
| peakro | double |  |  |
| tdet | double |  |  |
| tdep | double |  |  |
| gwbfv | double |  |  |
| gwdsv | double |  |  |
| sedcon_1 | double |  |  |
| sedcon_2 | double |  |  |
| sedcon_3 | double |  |  |
| sedcon_4 | double |  |  |
| sedcon_5 | double |  |  |
| frcflw_1 | double |  |  |
| frcflw_2 | double |  |  |
| frcflw_3 | double |  |  |
| frcflw_4 | double |  |  |
| frcflw_5 | double |  |  |

Preview:

event | year | sim_day_index | julian | month | day_of_month | water_year | wepp_id | dur | tcs | oalpha | runoff | runvol | sbrunf | sbrunv | drainq | drrunv | peakro | tdet | tdep | gwbfv | gwdsv | sedcon_1 | sedcon_2 | sedcon_3 | sedcon_4 | sedcon_5 | frcflw_1 | frcflw_2 | frcflw_3 | frcflw_4 | frcflw_5
--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---
 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 
SUBEVENT | 2010 | 1 | 1 | 1 | 1 | 2010 | 1 | 0 | 0 | 0 | 0 | 0 | 3.2923e-06 | 0.33178 | 0 | 0 | 0 | 0 | 0 | 0.98679 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0
SUBEVENT | 2010 | 1 | 1 | 1 | 1 | 2010 | 2 | 0 | 0 | 0 | 0 | 0 | 0.00020362 | 23.271 | 0 | 0 | 0 | 0 | 0 | 1.1191 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0
SUBEVENT | 2010 | 1 | 1 | 1 | 1 | 2010 | 3 | 0 | 0 | 0 | 0 | 0 | 0.00074581 | 77.863 | 0 | 0 | 0 | 0 | 0 | 1.0223 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0

### `pass_pw0.metadata.parquet`

Watershed PASS metadata (particle diameters, areas, concentrations).

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| wepp_id | int32 |  |  |
| climate_file | string |  |  |
| area | double | m^2 |  |
| srp | double | mg/L |  |
| slfp | double | mg/L |  |
| bfp | double | mg/L |  |
| scp | double | mg/kg |  |
| dia_1 | double | m |  |
| dia_2 | double | m |  |
| dia_3 | double | m |  |
| dia_4 | double | m |  |
| dia_5 | double | m |  |

Preview:

wepp_id | climate_file | area | srp | slfp | bfp | scp | dia_1 | dia_2 | dia_3 | dia_4 | dia_5
--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---
 |  | m^2 | mg/L | mg/L | mg/L | mg/kg | m | m | m | m | m
1 | p1.cli | 100780 | 0 | 0 | 0 | 0 | 2e-06 | 1e-05 | 3e-05 | 0.00035 | 0.0002
2 | p2.cli | 114280 | 0 | 0 | 0 | 0 | 2e-06 | 1e-05 | 3e-05 | 0.0003 | 0.0002
3 | p3.cli | 104400 | 0 | 0 | 0 | 0 | 2e-06 | 1e-05 | 3e-05 | 0.00034 | 0.0002
