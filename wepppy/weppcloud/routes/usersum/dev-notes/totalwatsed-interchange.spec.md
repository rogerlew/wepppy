# Daily combined output over hillslope `H.wat.parquet` and `H.pass.parquet` interchange outputs

At after `run_wepp_hillslope_interchange` create `interchange/totalwatsed3.parquet`

Kitchen sink of daily (`day` is day index) measures for watershed.

`def run_totalwatsed3(interchange_dir, baseflow_opts: BaseflowOpts, wepp_ids = None | List[int])`

if `wepp_ids` is None aggregate all the wepp_ids, otherwise filter to only include wepp_ids

## Specification
- H.wat.parquet -> wat
- H.pass.parquet -> pass

## Schema for totalwatsed3, use `schema_utils.pa_field`

| Column | Type | Units | Description | Calculation |
| --- | --- | --- | --- | --- |
| year | int16 |  |  |  |
| day | int16 |  |  |  |
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
| Area | double | m^2 | Area that depths apply over | sum(wat.Area) |
| P | double | m^3 | Precipitation | sum(wat.P * 0.001 *  wat.Area) |
| RM | double | m^3 | Rainfall+Irrigation+Snowmelt | sum(wat.RM * 0.001 *  wat.Area) |
| Q | double | m^3 | Daily runoff over eff length | sum(wat.Q * 0.001 *  wat.Area) |
| Dp | double | m^3 | Deep percolation | sum(wat.Dp * 0.001 *  wat.Area) |
| latqcc | double | m^3  | Lateral subsurface flow | sum(wat.latqcc * 0.001 *  wat.Area) |
| QOFE | double | m^3  | Daily runoff scaled to single OFE | sum(wat.QOFE * 0.001 *  wat.Area) |
| Ep | double | m^3 | Plant transpiration | sum(wat.Ep * 0.001 *  wat.Area) |
| Es | double | m^3 | Soil evaporation | sum(wat.Es * 0.001 *  wat.Area) |
| Er | double | m^3 | Residue evaporation | sum(wat.Er * 0.001 *  wat.Area) |
| UpStrmQ | double | mm  | Runon added to OFE | sum(wat.UpStrmQ * 0.001 *  wat.Area) / Area * 1000 |
| SubRIn | double | mm  | Subsurface runon added to OFE | sum(wat.SubRIn * 0.001 *  wat.Area) / Area * 1000 |
| Total-Soil Water | double | mm  | Unfrozen water in soil profile | sum(wat.Total-Soil Water * 0.001 *  wat.Area) / Area * 1000 |
| frozwt | double | mm  | Frozen water in soil profile | sum(wat.frozwt * 0.001 *  wat.Area) / Area * 1000 |
| Snow-Water | double | mm  | Water in surface snow | sum(wat.Snow-Water * 0.001 *  wat.Area) / Area * 1000 |
| Tile | double | mm  | Tile drainage | sum(wat.Tile * 0.001 *  wat.Area) / Area * 1000 |
| Irr | double | mm  | Irrigation | sum(wat.Irr * 0.001 *  wat.Area) / Area * 1000 |
| Precipitation | double | mm | Precipitation | P / Area * 1000 |
| Rain+Melt | double | mm | Rainfall+Irrigation+Snowmelt | RM / Area * 1000 |
| Percolation | double | mm | Deep percolation | Dp / Area * 1000 |
| Lateral Flow | double | mm  | Lateral subsurface flow | latqcc / Area * 1000 |
| Runoff | double | mm  | Daily runoff scaled to single OFE | QOFE / Area * 1000 |
| Transpiration | double | mm | Plant transpiration (Ep depth normalized) | Ep / Area * 1000 |
| Evaporation | double | mm | Soil (Es) + Residue (Er) evaporation (depth normalized) | (Es+Er) / Area * 1000 |
| ET | double | mm | Total ET (depth normalized Ep+Es+Er)  | (Ep+Es+Er) / Area * 1000 |
| Baseflow | double | mm | Baseflow | reimplement running calc from totalwatsed.py provided below |
| Aquifer losses | double | mm | Aquifer losses | reimplement running calc from totalwatsed.py provided below |
| Reservoir Volume | double | mm | Reservoir Volume | reimplement running calc from totalwatsed.py provided below |
| Streamflow | double | mm | Streamflow | Runoff + Lateral Flow + Baseflow |


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
| day | int16 |  |  |
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
