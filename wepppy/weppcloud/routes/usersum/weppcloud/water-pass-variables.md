# Water and PASS variables: ET, Dp and runoff

Use this reference with [Understanding water balance and runoff](water-balance-and-runoff.md). The units below describe physical values. Some older Parquet metadata labels are incomplete or wrong; a new README does not change the data or correct those labels. Do not build a conservation calculation by summing every numeric column.

## Identity and time fields

H.wat has one row per **native hillslope, OFE and simulation day**. H.pass has one record type per **native hillslope and simulation day**, expanded into a common column layout. These are daily files even when the model uses hourly internal water-balance calculations.

| Field | Meaning and use |
| --- | --- |
| wepp_id | Native WEPP hillslope ID; not necessarily a Topaz/map ID. Preserve this identity until aggregation is complete. |
| ofe_id; OFE (WAT) | OFE number within the native hillslope; OFE retains the raw field. Determine the terminal OFE from complete topology, before filtering dates. |
| year | Calendar year resolved by interchange using the simulation calendar; raw files can use simulation-year numbering. |
| julian | Day of year, not an astronomical Julian date. |
| sim_day_index | One-based simulation day. |
| month; day_of_month | Calendar month and day derived from the resolved date. |
| water_year | Water-year label (October through September, labeled by ending year). |
| event (PASS) | EVENT, SUBEVENT or NO EVENT; controls which physical fields were emitted. |

Check date support and identity mapping before joining. Missing records are not automatically dry days. Optional fields unavailable in old layouts are null, not zero measurements.

## H.wat water fields: ET, Dp and runoff

All water depths below are **mm**. Flux fields are daily amounts; stock fields are daily snapshots. Positive loss/outflow fields denote water leaving the stated local or hillslope boundary; runon denotes an input to the receiving OFE. The table is an interpretation guide, not an assertion that every model/version guarantees nonnegative diagnostics.

| Field | Spatial basis and interpretation | Aggregation |
| --- | --- | --- |
| P | Precipitation on the local OFE | Area-weight daily, then sum days. |
| RM | Rainfall + irrigation + snowmelt input term on the local OFE | Area-weight; do not add to P or count snowmelt twice when using snow storage. |
| Irr | Irrigation on the local OFE | Area-weight daily. |
| Ep | Plant transpiration from the local OFE | Area-weight daily; ET = Ep + Es + Er. |
| Es | Soil evaporation from the local OFE | Area-weight daily. |
| Er | Residue evaporation from the local OFE | Area-weight daily; not a guarantee that all interception evaporation is exported. |
| Dp | Deep percolation from the local profile | Area-weight daily; not watershed outlet baseflow. |
| Q | Producer-normalized cumulative surface runoff; terminal row gives physical whole-hillslope runoff for supported producers | Select terminal Q; no additional terminal-area weighting. Never sum intermediate Q values as external exports. |
| QOFE | Producer-version-dependent runoff diagnostic: historical local-area normalization or current Q alias | Do not infer normalization from values or use as a universal whole-hill budget term. |
| UpStrmQ | Surface runon entering the receiving OFE | Internal-transfer diagnostic; not additional external hillslope precipitation. |
| SubRIn | Subsurface runon entering the receiving OFE | Internal-transfer diagnostic; not an independent whole-hill input. |
| latqcc | Lateral outflow depth over the local OFE area | External hillslope depth = terminal value × terminal area / total hill area. |
| Tile | Tile drainage diagnostic | Existing reductions are not certified whole-hill external flow; verify producer/path before closure. |
| Total-Soil Water | Unfrozen profile-water stock over the local OFE | Weight snapshots; use changes, not sums of daily stocks. |
| frozwt | Frozen profile-water stock over the local OFE | Weight snapshots; combine with unfrozen stock only when using that storage basis. |
| Snow-Water | Surface snow-water stock over the local OFE | Weight snapshots; use boundary differences. |
| SoilWaterTotal (optional) | Producer total profile water, watcon + frozwt | Preferred total profile stock when available; do not add frozwt again. |
| ProfileDepth (optional) | Full profile depth, solthk(nsl) | Geometry descriptor, not water flux. |
| ProfilePorosityCap (optional) | Profile porosity storage capacity, sum(por × dg) | Capacity, not actual stored water or daily loss. |
| ProfileFCStore (optional) | Profile field-capacity storage, sum(thetfc × dg) | Capacity descriptor. |
| ProfileWPStore (optional) | Profile wilting-point storage, sum(thetdr × dg) | Capacity descriptor. |
| InterceptionStorage (optional) | Plant/residue carryover storage, pintlv + resint | Weight snapshots and use differences; absent is unknown. |
| Area | **m²**, local OFE area, not the denominator of every water column | Sum distinct OFE areas once per native hill; do not sum area over dates. |

Legacy metadata may say Q is “over eff length,” QOFE is always “scaled to single OFE,” or Area is where all depths apply. Those descriptions do not resolve producer normalization; use the current guide and the actual producer contract. Channel water files have separate scope and cannot inherit hillslope terminal-Q rules automatically.

## H.pass water and routing fields

PASS exports **delivery**, including an event gate. EVENT requires internal terminal runoff at least 0.001 m; the test is not on printed WAT Q. SUBEVENT omits surface runoff; NO EVENT still permits groundwater exports. The ordinary subsurface branch can suppress lateral volumes at or below 0.01 m³ unless tile drainage qualifies. The parser's zero-filled non-emitted fields describe exported contributions, not all physical losses.

| Field | Physical units | Meaning and combination rule |
| --- | --- | --- |
| dur | s | Storm duration for EVENT; not a daily amount. |
| tcs | h | Overland-flow time of concentration used for routing. |
| oalpha | dimensionless | Routing alpha parameter; do not sum as water. |
| runoff | m | Internal terminal runoff depth on the producer effective-flow basis, EVENT only. Do not assume total hillslope area is its denominator. |
| runvol | m³ | Threshold-filtered exported surface runoff volume. Sum matching hill/day volumes; divide by corresponding total area and multiply by 1,000 for mm. |
| sbrunf | m | Terminal local subsurface depth when emitted. |
| sbrunv | m³ | Exported subsurface volume = sbrunf × terminal slope length × terminal width for the ordinary writer. Sum volumes, not depths. |
| drainq | m/day | Producer tile drainage flux; verify local spatial basis before turning it into whole-hill depth. |
| drrunv | m³ | Exported tile drainage volume. |
| peakro | m³/s | Exported peak surface runoff rate; summing asynchronous hillslope peaks does not yield routed watershed peak discharge. |
| gwbfv | m³ | Daily groundwater baseflow volume when emitted; historical Arrow unit metadata is absent. |
| gwdsv | m³ | Daily groundwater deep-seepage volume when emitted; historical Arrow unit metadata is absent. |

## H.pass sediment fields

These fields do not belong in a water-volume sum.

| Field | Physical units | Meaning |
| --- | --- | --- |
| tdet | kg | Hillslope total detachment for the record. |
| tdep | kg | Hillslope total deposition for the record. |
| sedcon_1 … sedcon_5 | kg/m³ | Concentrations for clay, silt, small aggregates, large aggregates, and sand. Multiply each by runvol to obtain that class's exported mass. |
| clot; slot; saot; laot; sdot | dimensionless fractions | Corresponding exiting sediment fractions, written directly from frcflw. They are not flow rates and are not percentage numbers requiring division by 100. |

**Machine-metadata caveat:** inherited H.pass metadata labels clot as m³/s and the other four fractions as %. Those labels are wrong for the ordinary writer's raw fractions. Corrected descriptions warn about this, but the machine-unit labels remain unchanged for compatibility with existing export conversion and column naming. Use the physical units above in custom analysis; do not trust automated conversion of these five fields. Updating those machine labels requires a separate compatibility change. Groundwater fields similarly lack machine-unit labels even though their physical volumes are m³.

## Raw layouts, watershed PASS and derived tables

Raw H*.wat text contains an OFE and day record with a producer-specific column layout. Interchange adds identities/calendar fields and accommodates optional trailing fields. H*.pass text is variable-length by event type; supported binary HBP is another delivery encoding, not a different physical water balance. Do not parse every PASS record as a full EVENT row.

Watershed `pass_pw0.events.parquet` and `pass_pw0.metadata.parquet` represent a different combined PASS layout and its hillslope areas/particle metadata. They are not raw H.pass rows or proof of routed outlet flow; inspect their own run-specific schemas. Routed channel/outlet files answer watershed discharge questions.

In totalwatsed3, named **Runoff** uses PASS runvol / combined hill area. Named **Lateral Flow** uses terminal WAT lateral volume / combined hill area. Raw Q/QOFE sums are legacy diagnostics; their existence is not a closure guarantee. Storage and capacity columns are not interchangeable with flows. See [the derivation reference](../../../../wepp/interchange/README.totalwatsed3.md).

See [WEPP Interchange Outputs](wepp-interchange.md) for the file inventory and [WEPP Run Results](wepp-run-results.md) for report selection. The run's **Output files, columns, and sample data** page lists actual available columns and a three-row preview; it does not infer producer lineage or certify historical accounting.
