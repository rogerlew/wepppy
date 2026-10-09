# Low-Severity Forest: 4 Versus 6 cm RRINIT

Subsequent decision: Roger approved the 6 cm value after this assessment.
[ADR-0083](../../adrs/ADR-0083-low-severity-forest-initial-random-roughness.md)
records adoption in the template and packaged extended lookup. The report,
runner and archived artifacts below describe the pre-adoption experiment;
reproducing it requires its recorded pre-adoption input versions, not today's
default template. Do not overwrite these historical artifacts.

2026-10-09. Requested follow-up to the [completed sensitivity study](sensitivity-results.md).
Assessment only: production templates, model binaries and default values are unchanged.

## Decision

The canonical matrix identifies no meaningful runoff penalty or new severity-rank
inversion from changing low-severity forest RRINIT from 0.04 to 0.06 m. It does
identify a persistent sediment effect in the sandy-loam fixture: hillslope PASS
sediment delivery decreases 17.49%, or 143.33 kg over 100 years on 0.900096 ha.
That is a decrease from 9.10 to 7.51 kg/ha/year. Other soil fixtures show no
runoff, peak or sediment changes at output precision.

Decision interpretation clarified by Roger after adoption: this fixes a
parameterization inconsistency, with more sensible event-level sediment
ordering. The earlier conditional "accepting a sediment consequence" framing
is superseded. Sediment changes are documented consequences of the correction,
not an assumed degradation. The change crosses an existing interrill-delivery
cutoff rather than uniformly scaling delivery. No broader recalibration or
other parameter edits are implied; absolute accuracy against observations
remains unestablished. Numerical results and original experiment artifacts are
unchanged by this interpretation update.

## Design and Provenance

- Fresh current-default matrix: 96 runs, four soils, six vegetation types and
  four severity states. Canonical 87.9 m profile, approximately 38.56% mean
  slope, 102.4 m width; no gentler-profile extension in this follow-up.
- Sixteen additional trials: low-severity forest, deciduous forest, mixed forest
  and young forest, each on four soils, with only management RRINIT changed.
  The parser verifies that restoring RRINIT exactly restores the baseline
  serialized management. All other inputs remain identical within a contrast.
- The proposed 96-cell matrix replaces these 16 baseline cells and reuses the
  80 unchanged controls. Those unchanged cells were not redundantly simulated
  a second time. Four forest labels share burned templates and are not four
  independent parameterizations; all four give identical low-burn results for
  a given soil, verified across the comparison fields.
- Synthetic McKenzie Bridge forcing: 2000-2099, fixed seed 26109, 36,525 finite
  daily records, same separately generated canonical fixture as the prior study.
- Released `wepp_261009_hill`, SHA256
  `37d8deaf7a4c78e83104db4d896db3ee10b77a5f5d3f3abe5ad718390e2cc228`.
  All 112 runs use the same frozen binary and host runtime. No host/container
  mixing within these contrasts and no private run fixture is required.
- All 112 runs completed 100 simulation years successfully. Native PASS, EBE
  and SOIL readback checks found finite selected numeric outputs and unique
  dates; PASS and SOIL each contain all 36,525 days. Every input/output checksum
  was rechecked after analysis. Fourteen existing harness checks passed.

## Full-Record Results

The following results apply identically to all four affected forest labels.
Runoff is hillslope surface runoff, not routed channel discharge. Sediment is
delivered hillslope sediment, not gross channel erosion or outlet sediment.
Values refer to the complete 100-year record.

| Soil | Surface runoff, EBE mm, 4 -> 6 cm | PASS sediment, kg, 4 -> 6 cm | Record maximum peak, m3/s, 4 -> 6 cm |
| --- | ---: | ---: | ---: |
| Clay loam | 41,620.0 -> 41,620.0 | 111,737.85 -> 111,737.85 | 0.11104 -> 0.11104 |
| Loam | 36,859.0 -> 36,859.0 | 21,630.31 -> 21,630.31 | 0.13427 -> 0.13427 |
| Sandy loam | 11,975.9 -> 11,975.9 | 819.45 -> 676.12 (-17.49%) | 0.17035 -> 0.17038 (+0.0176%) |
| Silt loam | 25,505.6 -> 25,505.6 | 8,824.65 -> 8,824.65 | 0.12931 -> 0.12931 |

The higher-precision sandy-loam PASS surface volume changes from 107,491.6793
to 107,491.6443 m3: -0.035 m3, or -0.0000326%. Lateral volume increases
0.0143 m3; recorded drain and baseflow volumes are unchanged. This is not a
material water-yield departure in this experiment. The existing PASS minus
EBE depth-equivalent volume discrepancy changes from -302.9176 to -302.9526 m3;
it is disclosed rather than forced to zero.

EBE sediment delivery is 7.9 -> 6.7 kg/m over 100 years (-15.19%). PASS
sediment is independently calculated as the sum of particle concentrations
times event runoff volume. Retain both measures: rounded event-level EBE
delivery and concentration-derived PASS mass do not give identical percentages.
Neither is a substitute for an independent sediment observation.

## Event and Annual Context

For sandy loam, all 743 PASS EVENT dates and 808 EBE dates are preserved;
there are no new or lost runoff-event dates. Output comparisons show:

- Surface volumes change on four PASS dates. The largest change is -0.032 m3
  on synthetic year 2041, day 194, from 16.045 to 16.013 m3. EBE runoff is
  unchanged on every event and in every year at its reporting precision.
- Peaks change on 28 dates. The largest absolute peak change is
  0.088283 -> 0.088103 m3/s on 2009 day 241 (-0.204%). The largest relative
  peak change is approximately -0.508% on 2041 day 194,
  0.0080965 -> 0.0080554 m3/s. The 95th-percentile peak is unchanged.
- PASS sediment decreases on 30 dates, increases on none, and falls from
  positive delivery to zero on 24 dates. This is a real modeled change to
  small-event sediment behavior, not just an aggregate difference.
- Largest single-event mass decrease: 298.156 -> 283.585 kg on 2079 day 197,
  a decrease of 14.571 kg (4.89%). A smaller event on 2083 day 32 drops from
  9.041 kg to zero. These examples distinguish modest fractional change in
  the largest event from complete suppression of some smaller events.
- Annual sediment totals change in 25 of 100 years. The largest annual
  decrease is 14.571 kg in 2079. In 2083 the total falls from 15.620 to
  1.925 kg. This effect persists beyond initialization; first-year delivered
  sediment is zero for both runs.

For the other three soils, every compared EBE runoff/delivery value and PASS
event volume, peak and delivered sediment value is unchanged at output precision.
This is not a claim that all internal model state is identical.

## Mechanism and Rankings

In the sandy-loam fixture, reported effective roughness remains exactly 4 or
6 cm for all 36,525 days. The existing `PARAM` calculation applies
`rif = max(0, min(1, 1.14 - 23 * rrc))` for these landuse-1 templates.
The roughness factor is 0.22 at 4 cm and zero at 6 cm. Through the existing
particle-specific delivery relationship, the latter eliminates interrill
delivery. Rill processes remain active: this does not mean all erosion is zero.
The summed printed EBE interrill-detachment field decreases from 0.012 to zero
kg/m2, while summed mean-detachment values increase from 0.07 to 0.09 kg/m2.
These coarse printed diagnostics must not be confused with delivered mass or
interpreted as a uniform reduction of every erosion component.

The other soils have already reduced roughness by the first reported states:
maximum reported roughness is 1.293-1.470 cm for the 4 cm initialization and
1.939-2.204 cm for 6 cm, eventually reaching the 0.6 cm floor. Neither run
remains above the cutoff. This is consistent with the previously traced
soil-state-dependent decay; it is not a universal claim about these texture names.

Weak ordering means unburned <= low <= moderate <= high, allowing printed ties.
There are 24 labeled soil/vegetation contexts, not 24 independent watersheds.

| Metric | Current defaults | Low forest at 6 cm |
| --- | ---: | ---: |
| EBE cumulative runoff ordered | 23/24 | 23/24 |
| PASS delivered sediment ordered | 24/24 | 24/24 |
| Record maximum peak ordered | 18/24 | 18/24 |

No ordering failures are introduced or removed. The existing sandy-loam
tall-grass runoff reversal is outside the changed template. Six peak-order
exceptions remain, including the four clay-loam forest contexts whose low-burn
peaks do not change. A neater roughness table is not proof of more accurate
modeled severity contrasts.

The preceding counts describe full-record metrics, not same-date event
sediment rankings. A follow-up comparison of sandy-loam mature-forest PASS
sediment on the union of 3,465 EVENT dates (absent EVENT sediment counted as
zero) finds 17 dates where low severity exceeds moderate at 4 cm, and none
at 6 cm. With the revision, unburned <= low <= moderate <= high delivered
sediment holds on every compared date. For example, on synthetic 2016 day 23,
the series changes from 0, 8.350, 0, 2,181.811 kg to
0, 0, 0, 2,181.811 kg. Thus event-level sediment ordering improves even though
the full-record ranking counts are unchanged. This conclusion is specific to
delivered sediment; runoff and peak ordering need not improve on every date.

## Evidence and Reproduction

[Compact artifacts](artifacts/low-forest-4v6/) include all 112 case summaries,
16 comparisons, 1,600 paired annual records, largest event departures, both
96-cell matrix rankings, source identities, input/output receipts and logs.
Raw model outputs and per-event/soil Parquet files remain in
`/wc1/holdouts/rrinit-low-forest-4v6-20261009` as generated evidence, not a
required preexisting resource. The runner rebuilds its inputs from repository
fixtures and templates. It refuses to overwrite an existing preparation root.

From `/home/workdir/wepppy`:

```bash
.venv/bin/python docs/work-packages/20261009_rrinit_parameter_review/low_forest_trial.py prepare
.venv/bin/python docs/work-packages/20261009_rrinit_parameter_review/low_forest_trial.py execute
.venv/bin/python docs/work-packages/20261009_rrinit_parameter_review/low_forest_trial.py analyze
wctl run-pytest tests/disturbed/test_matrix_contracts.py tests/disturbed/test_route_coefficients.py -q
```

This follow-up does not rerun the full unrelated WEPPpy test suite. It does
not establish watershed-routing effects, subdaily timing parity, sediment
accuracy against observations, or behavior on gentler terrain, other climates
and other soil states. It supports a bounded default-consistency decision with
an explicit sediment consequence, not a blanket physical validation.
