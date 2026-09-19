# Manual versus Omni comparison, mixed binaries

Requested comparison: repaired manual runs using `wepp_dcc52a6`, versus Forest
Omni batch `ef226e0f-a5f7-4daf-bee6-9db5f420c7aa` using `wepp_260803`.
Read-only analysis; no model settings or runs changed.

## Sources and metrics

Manual values come from
`../../20260917_mofe_scenario_artifact_integrity/artifacts/mofe-production-hillslope-response-summary.csv`.
Read-only SHA256 checks on wepp1 confirmed all eight live manual/baseline
`loss_pw0.hill.parquet` files still match that package's
`mofe-production-summary-sources.json` receipts.
Omni values were recomputed directly from each scenario's
`wepp/output/interchange/loss_pw0.hill.parquet` on local Forest.

All are 455-hillslope, 22-year summaries. Runoff is sum volume / (sum hectares
times 10), in mm/year. Sediment is sum hillslope yield / 1000, in tonnes/year;
this is **not watershed outlet sediment delivery**. Percent difference is
100 times (Omni / manual - 1), with manual as denominator.

## Paired results

| Pair | Manual runoff | Omni runoff | Difference | Manual sediment | Omni sediment | Difference |
| --- | --- | --- | --- | --- | --- | --- |
| Low | 941.757 | 942.002 | +0.026% | 771.629 | 3497.970 | +353.3% |
| Moderate | 949.476 | 950.157 | +0.072% | 979.628 | 3850.155 | +293.0% |
| High | 1046.573 | 1047.930 | +0.130% | 4513.510 | 16722.439 | +270.5% |
| Prescribed | 904.908 | 905.584 | +0.075% | 238.380 | 1139.695 | +378.1% |
| Manual 30% canopy / Omni 40% canopy, 75% ground | 972.926 | 827.751 | -14.92% | 10261.264 | 811.182 | -92.09% |
| Manual 50% canopy / Omni 65% canopy, 85% ground | 947.852 | 820.456 | -13.44% | 7200.910 | 653.501 | -90.92% |

Manual run mapping: low `equestrian-bonheur`, moderate `tactful-aging`, high
`incorporate-cerebrum`, prescribed `neoliberal-dictate`, 30% canopy
`acetic-surprise`, 50% canopy `uncrowned-bolt`.

Manual baseline: 738.918 mm/year and 128.452 tonnes/year. Manual SBS:
948.659 mm/year and 2186.056 tonnes/year. Neither has a newly executed 260803
counterpart in this six-scenario batch; do not invent a paired percent difference.

## Rank agreement and the 20% expectation

For the four fire treatments, both metrics in both workflows rank
high > moderate > low > prescribed. Runoff easily meets the requested 20%
tolerance; sediment yield fails for every fire pair.

Across all six, manual sediment ranks 30% canopy > 50% canopy > high > moderate
> low > prescribed. Omni sediment ranks high > moderate > low > prescribed
> 40/75 thinning > 65/85 thinning. Both thinning pairs retain their internal
canopy ordering, but their positions relative to fire do not agree.

Manual runoff ranks high > 30% canopy > moderate > 50% canopy > low > prescribed;
Omni runoff ranks high > moderate > low > prescribed > 40/75 > 65/85.
Thus the earlier statement that Omni's internal rank order is correct must not
be interpreted as agreement with the full manual ordering.

## Parameterization and numerical caveats

These are confirmed differences, not an attribution of the observed deltas:

- Different binary versions. The 260803 batch has no plot overflow; the earlier
  dcc52a6 Omni attempt overflowed. This is evidence of a binary-associated
  difference, not a controlled isolation of all model changes.
- Manual fire scenarios retain 13 grass/bare-remapped segments (431, 430, 429,
  or 432). Omni uniform fires assign all 1065 OFEs to forest-fire classes;
  Omni prescribed fire leaves 13 bare OFEs unchanged.
- Manual thinning uses 1021 treated, 43 forest, one bare OFE, canopy 0.30/0.50,
  and effective template ground cover 0.75 in both cases. Stored 0.9/0.8 ground
  metadata is not active in MOFE synthesis. Omni treats 1052 forest OFEs and
  preserves 13 bare OFEs; canopy/ground pairs are 0.40/0.75 and 0.65/0.85.

Gross hillslope soil loss is also dramatically different (tonnes/year):

| Pair | Manual | Omni |
| --- | --- | --- |
| Low | 112924210.673 | 3558.918 |
| Moderate | 791736.363 | 3930.347 |
| High | 5297042.372 | 17189.025 |
| Prescribed | 572345.167 | 1178.960 |
| Lower-canopy thinning | 37189.452 | 831.289 |
| Higher-canopy thinning | 24787.218 | 671.004 |

Do not confuse gross soil loss with sediment yield: the earlier manual audit
already noted large gross erosion/deposition cancellation. These values warrant
scientific review; successful input repair was not validation of model numerics.

## Disposition

Hydrologic agreement for the fire treatments is strong. Sediment equivalence
and full cross-workflow rank consistency are **not demonstrated**. Keep the
segment-eligibility artifact acceptance separate: prescribed/thinning eligibility
and bare-neighbor preservation pass their generated/prepared checks.

The smallest next controlled comparison is to rerun preserved manual inputs
with 260803, preferably on copies, then compare matched treatments. That would
separate binary effects from remaining differences in affected OFEs and cover.
No such rerun is authorized or executed by this read-only comparison.
