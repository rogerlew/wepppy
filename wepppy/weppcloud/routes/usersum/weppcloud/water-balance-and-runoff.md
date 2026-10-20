# Understanding water balance and runoff

Start here when comparing a spreadsheet with a WEPPcloud report, especially when a hillslope contains multiple **overland flow elements (OFEs)**. An OFE is a section along a hillslope; water can move from one section into the next. A depth in millimeters has meaning only with its area and time interval.

## Choose the output that answers your question

| Question | Output | Meaning |
| --- | --- | --- |
| How much water physically left each hillslope? | Average annual hillslope water balance; daily hillslope water loader; water dashboard events; H.wat feature exports | Surface runoff uses terminal WAT Q, including small runoff omitted by PASS. ET and deep percolation use area-weighted local OFE depths. |
| How much runoff was passed onward for delivery accounting? | H.pass; named Runoff in totalwatsed3; yearly water balance and daily streamflow graph | Threshold-filtered PASS runoff volume, divided by the contributing hillslope area. It can be less than physical WAT runoff. |
| What happened within one section? | H.wat per OFE and day | Local inputs, losses, stocks and transfers. Intermediate Q and runon are not additional whole-hillslope exports. |
| What left the routed watershed outlet? | Watershed outlet and channel routing outputs | Routing results. Summed hillslope contributions in totalwatsed3 are not routed watershed outlet discharge. |

The average annual report contains separate hillslope and channel tables; do not add their throughflows as independent losses. Ash uses physical WAT water. AshPost replaces contributions in a PASS-based baseline and therefore subtracts the matching PASS contribution, not physical WAT runoff.

## ET and deep percolation: weight local areas each day

In H.wat, evapotranspiration **ET = Ep + Es + Er** (plant transpiration, soil evaporation and residue evaporation). **Dp** is deep percolation. For local depths such as ET, Dp, precipitation P and irrigation Irr:

`hill depth = sum(local depth * local OFE Area) / sum(local OFE Area)`

Compute this for each native hillslope and day, then sum the daily depths for a time period. For multiple hillslopes, combine volumes and divide by their combined area. Do not average OFEs equally, count the area again on every date, or collapse multiple native hillslopes into a map feature before choosing their outlets.

## Surface runoff Q and lateral flow latqcc have different denominators

For the supported constant-width hillslope producers, **terminal Q already represents physical runoff depth over the full native hillslope area**. Select the last OFE from the complete hillslope topology. Do not multiply terminal Q by the last OFE's fraction of the hill area.

**latqcc is a local OFE depth.** Only the terminal OFE's lateral outflow leaves the hillslope; upstream lateral outflow is transferred internally. Its hillslope depth is `terminal latqcc * terminal Area / total hill Area`.

**QOFE is version-sensitive**: older producers used local normalization; newer producers can write QOFE equal to Q. Never determine normalization from the values alone. QOFE and sums of all OFE Q values are diagnostics, not substitutes for terminal physical Q. Custom variable-width producers or unknown normalizations require separate verification.

## Two-OFE worked example

These are illustrative daily values, not a complete closed water budget.

| Term | Upper OFE, 250 m² | Lower/terminal OFE, 750 m² | Whole hillslope, 1,000 m² |
| --- | --- | --- | --- |
| ET (mm) | 2 | 6 | `(2*250 + 6*750)/1000 = 5` |
| Dp (mm) | 1 | 3 | `(1*250 + 3*750)/1000 = 2.5` |
| latqcc (mm) | Internal transfer | 6 | `6*750/1000 = 4.5` |
| Physical terminal Q (mm) | Internal diagnostic | 8 | `8`, without further area scaling |

A depth becomes volume through `m³ = mm * m² / 1000`: ET is 5 m³, deep percolation 2.5 m³, lateral export 4.5 m³ and surface export 8 m³. In a spreadsheet, use actual exported areas rather than rounded slope fractions. A lower-OFE budget also needs upstream surface and subsurface inputs; omitting those inputs produces an apparent imbalance.

For example, after loading an authenticated download as a pandas DataFrame named `wat`:

```python
# Use the complete native hillslope topology, before date filtering.
area = wat.groupby(["wepp_id", "ofe_id"])["Area"].agg(["min", "max"])
assert (area["min"] > 0).all() and (area["min"] == area["max"]).all()
hill_area = area["min"].groupby(level="wepp_id").sum()
terminal = area.reset_index().groupby("wepp_id")["ofe_id"].max()
assert not wat.duplicated(["wepp_id", "year", "julian", "ofe_id"]).any()
wat = wat.assign(ET=wat.Ep + wat.Es + wat.Er)
for (hill, year, day), rows in wat.groupby(["wepp_id", "year", "julian"]):
    assert set(rows.ofe_id) == set(area.loc[hill].index)
    assert rows[["Area", "ET", "Dp", "Q", "latqcc"]].notna().all().all()
    outlet = rows.loc[rows.ofe_id == terminal[hill]].iloc[0]
    et_mm = (rows.ET * rows.Area).sum() / hill_area[hill]
    dp_mm = (rows.Dp * rows.Area).sum() / hill_area[hill]
    runoff_mm = outlet.Q
    lateral_mm = outlet.latqcc * outlet.Area / hill_area[hill]
    print(hill, year, day, et_mm, dp_mm, runoff_mm, lateral_mm)
```

This teaching example assumes a supported producer and finite input values; production consumers perform additional validation. See [dataset access from Python and R](profile-jwt-dataset-access-python-r.md) for downloading files. A missing expected terminal row is not zero runoff: scientific reports/loaders fail validation and dashboard events show unavailable data.

## PASS EVENT, SUBEVENT and NO EVENT

Hillslope PASS is a delivery file, not a complete physical water budget. The ordinary producer emits EVENT when its internal terminal runoff reaches 0.001 m. That internal depth is not necessarily the printed terminal WAT Q, so filtering WAT Q at 1 mm does not reproduce PASS.

EVENT includes surface runoff and sediment. SUBEVENT includes qualifying subsurface/tile contributions but no surface runoff fields. NO EVENT can still contain groundwater values. Small lateral volumes may also be suppressed (the ordinary non-surface-event branch tests lateral volume above 0.01 m³ or positive tile drainage). Interchange expands record layouts; zero-filled non-emitted fields mean no exported contribution, not proof of no physical process. A missing row or null optional field is different from zero.

Use **runvol**, in m³, when combining hillslope PASS runoff. Convert the sum to mm using the sum of the corresponding hillslope areas. The PASS `runoff` depth uses the producer's effective-flow basis and must not be multiplied blindly by total hillslope area.

## Time, storage and closure

Hourly water-balance calculations still produce daily H.wat rows. Fluxes are daily amounts; soil water, frozen water and snow water are snapshots. A period's storage change is ending storage minus starting storage, not a sum of daily stocks. Missing boundary snapshots prevent a complete closure check.

A whole-system budget needs a consistent boundary: external precipitation plus irrigation, external exports, and changes in soil, snow and interception storage. RM contains snowmelt, which is already an internal transfer when snow storage is included. Do not add RM and P as independent inputs. Ep + Es + Er does not necessarily include every interception evaporation term used by the model. A residual from exported fields alone is not proof of a model conservation failure.

Use SoilWaterTotal when available for total profile water; otherwise unfrozen Total-Soil Water plus frozwt is the profile-water candidate. Optional fields absent from old producers remain unavailable, not zero. Soil/profile capacities are not daily losses. Legacy annual storage/Tile/QOFE exports are diagnostic and do not certify closure.

The average annual hillslope report divides accumulated values by `max(number of water-year bins - 1, 1)`. The yearly water-balance report excludes the first two available water-year bins (which can include partial bins) by default, with user-adjustable exclusions. Match time windows and divisors before comparing reports or spreadsheets.

## Versions and historical runs

The interchange schema version describes file layout, the model executable identifies producer behavior, and the report accounting marker identifies consumer calculations. They are different. New documentation or a regenerated README does not update old reports or prove their accounting. Current physical-water consumers use the `mofe-water-v2` marker; historical results without sufficient accounting evidence can remain unverified until regenerated.

Historical model briefs in Usersum describe their dated source lineage; they are not universal definitions for every executable. Ordinary and hourly outputs have runtime validation; contour formulas have source evidence but limited runtime validation. The six-year isolated model replay failure remains a separate model limitation. No documentation change fixes that failure or deploys a model.

See [Water and PASS variables](water-pass-variables.md), [WEPP Interchange Outputs](wepp-interchange.md), and [WEPP Run Results](wepp-run-results.md). Developers can consult the [current aggregation contract](../../../../../docs/schemas/hillslope-water-aggregation-contract.md) and [ADR-0099](../../../../../docs/adrs/ADR-0099-mofe-physical-water-consumers.md).
