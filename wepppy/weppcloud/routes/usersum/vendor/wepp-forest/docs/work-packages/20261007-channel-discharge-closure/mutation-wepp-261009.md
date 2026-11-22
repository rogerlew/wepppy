# WEPP 261009 mutation study

2026-10-09. Fresh rerun with the released hourly MIXPEAK implementation.
All 1,368 planned cases complete with zero failures. Figures 1-3 below replace
the earlier daily-v2 figures for evaluating this release; historical figures
remain unchanged. This study does not deploy the model or complete the separate
disturbed-parameterization study.

## Design and Identity

The original frozen design is retained: 140 hillslopes in both burned and
undisturbed scenarios for the complete 1980-2024 period. There are 280
unmutated controls and 1,088 eligible mutations: first-horizon Ksat times
0.99/1.01, and paired initial interrill/rill cover minus/plus 0.01. The original
32 ineligible mutations remain excluded, not clipped or replaced.

Both axes use wepp_261009. The unmutated controls are not wepp_260803.
Original climate, management, hourly context and rrinit are unchanged from the
frozen inputs. This is a hillslope sensitivity study, not an outlet-routing
comparison or an additional physical model patch.

| Artifact | SHA-256 |
| --- | --- |
| Released hillslope binary | 37d8deaf7a4c78e83104db4d896db3ee10b77a5f5d3f3abe5ad718390e2cc228 |
| Observation-only hillslope binary | 080f8f62ff510d5a5397840f0dac8656be8c7aec31814f282fb88821d3c6affd |

The observer is built from the exact release source with only the retained IRS
exit output hook added. It records full-precision runoff, peak and realized
return depth; it does not change physical operands. Two unmutated H106 controls
and their eight eligible mutations also run with the uninstrumented release:
all seven standard output files, including PASS, match byte-for-byte. There are
therefore 1,378 total model executions, of which 1,368 are study cases.

All 1,368 cases pass trace-to-element-report readback with one-to-one date keys.
Maximum absolute differences are 0.000507 mm runoff and 0.000504 mm/h peak,
consistent with the printed report precision. The original patch reverse-check
and sole-source-change audit pass. An initial literal diff comparison rejected
different alignment of repeated return/end context, not a physical source change;
that verification attempt is retained in the audit record.

## Results

The outer ledger contains 225,658 hillslope-date-mutation rows: 225,042 paired
events, 320 unmutated-only and 296 mutated-only events. Missing events are never
zero-filled. One event may appear under several mutations, so these are not
independent storm counts.

| Figure | Metric | Eligible pairs | Beyond twofold guides | Beyond fivefold guides | Outside axes |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | Runoff depth, mm | 218,974 | 453 | 34 | 86 |
| 2 | Hillslope sediment delivery, kg/m | 129,496 | 329 | 72 | 0 |
| 3 | Hillslope peak flow, mm/h | 200,984 | 966 | 209 | 179 |

Twofold means mutant/control below 0.5 or above 2; fivefold means below 0.2
or above 5. These are descriptive guides inherited from the original study,
not acceptance thresholds. Original marker shapes, scenario colors and
transparency conventions are retained. Same-direction responses and ties are
not automatically physical errors.

### Figure 1. Runoff

![Figure 1: WEPP 261009 runoff sensitivity](../../ablation/20261007_channel_discharge_closure/artifacts/repro/release-261009-mutation/figures/figure-1.png)

Both events must be present; unmutated runoff is at least 0.01 mm and mutated
runoff is positive. Original axes are 0.008-200 mm. The 86 eligible pairs outside
the axes remain included in counts and statistics.

### Figure 2. Erosion Metric: Sediment Delivery

![Figure 2: WEPP 261009 hillslope sediment-delivery sensitivity](../../ablation/20261007_channel_discharge_closure/artifacts/repro/release-261009-mutation/figures/figure-2.png)

This preserves the original report's erosion metric: event sediment delivered
at the hillslope outlet, in kg/m, not gross soil detachment or channel export.
Both printed deliveries must be positive. There are 540 unmutated-positive-only
and 583 mutated-positive-only records, retained separately. Of the plotted
pairs, 71,510 are equal at output precision; the low-value stair steps reflect
that precision. Sediment axes follow the original enclosing-power-of-ten rule.

### Figure 3. Peak Flow

![Figure 3: WEPP 261009 peak-flow sensitivity](../../ablation/20261007_channel_discharge_closure/artifacts/repro/release-261009-mutation/figures/figure-3.png)

Both events must be present; unmutated peak is at least 0.36 mm/h and mutated
peak is positive. Original axes are 0.3-800 mm/h. Gray indicates no surface
return in either run; color indicates return in at least one run.
The 179 eligible pairs outside the axes remain counted.

Of the 966 twofold peak departures (about 0.48% of eligible pairs), 543 have
surface return and 423 do not. There are 540 twofold peak departures with runoff
differing by less than 5%. Among the 209 fivefold departures, 25 have return and
184 do not. The largest peak on either side of a twofold departure is about
54.2 mm/h; the corresponding fivefold maximum is about 19.64 mm/h. Maximum peak
over the entire eligible cohort is about 200.8 mm/h. Residual nonlinear
sensitivity is therefore still present; no new repair or automatic deployment
decision is inferred from these figures.

## Reproduction and Evidence

Frozen original inputs: /workdir/hand-to-mouth-fixed-census-20261006-v2.
New raw root: /wc1/holdouts/wepp-261009-mutation-20261009.
Every input hash and planned mutation source value is checked before execution.
External inputs are supplementary study resources, not mandatory release gates.

From the repository root, using /home/workdir/wepppy/.venv/bin/python:

```bash
python docs/work-packages/20261007-channel-discharge-closure/run_release_mutation.py prepare
```

Apply mutation_support/observer.patch to the isolated observer-src directory
only; run make clean, then make -j4 FC=/usr/bin/gfortran wepp_hill, followed by
make prepare_watershed_includes. Production source and binaries are untouched.

```bash
python docs/work-packages/20261007-channel-discharge-closure/run_release_mutation.py execute
python docs/work-packages/20261007-channel-discharge-closure/run_release_mutation.py audit
python docs/work-packages/20261007-channel-discharge-closure/checkpoint_release_mutation.py
```

The output directory is creation-guarded; do not overwrite this completed run.
Analysis/rendering tests pass: 22 tests, two dependency deprecation warnings.
All three PNGs were visually inspected for labels, legends and clipping.
[Archived evidence](../../ablation/20261007_channel_discharge_closure/artifacts/repro/release-261009-mutation)
contains figures, statistics, scripts, plan/input identities, all receipts,
readback results, observer parity and checksums. Large raw outputs and paired
Parquet ledgers remain external, with their hashes recorded in the manifest.
