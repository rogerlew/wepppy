# Hourly routing: midnight diagnosis and implementation results

2026-10-08. Authorized defect-first diagnosis and implementation, with a hold
if the full hourly integration could not be made defensible. Baseline remains
`wepp_260803` at 10 cm. No daily averaging, release, vendoring or deployment.

## Decision

**A real channel restart defect is repaired and tested on an isolated branch.
It does not resolve the hourly candidate's problematic late pulses. Hold the
full candidate; do not add a timing or smoothing patch to manufacture acceptance.**

Retain the state repair for review because it corrects a demonstrated native
restart error, not because it materially improves Cedar. Its incremental effect
on Cedar is very small. The hourly source still places most return in hour 24
on the two controls, and the source/consumer sampling convention has a separate
unresolved mismatch. Neither finding authorizes replacing the hourly estimator.

## Defects separated

| Finding | Disposition | Evidence / limitation |
| --- | --- | --- |
| Internal channel profile discarded at midnight | `BUG_FIXED` in experimental branch | WSHCHR kept inlet/outlet values but replaced the internal profile with a straight line. Exact state retention restores uninterrupted native behavior on the same grid. |
| Daily segment count changes | Bounded transfer implemented; review required | Linear interpolation of nodal discharge, with endpoint preservation and no new extrema between adjacent values. Not a claim of exact storage conservation. |
| Interval-mean source treated as point samples | `BUG_PRESERVED` in this candidate | Actual MIXRETURN and point-mode lateral forcing show a half-step boundary discrepancy. No global approximation-mode switch or unproved top/lateral source-operator patch was bundled. |
| Hour-24 source concentration from daily scheduling | `REQUIRES_SCIENCE_REVIEW` | Earlier process tracing and current unchanged pulse results remain. No ET, infiltration or source-timing changes were made. |

These are different mechanisms. A known midnight defect was present, but the
existence of that defect did not establish it as the cause of the observed
following-day pulses.

## Native diagnostic

The harness runs actual WSHCHR, CHRQIN, MIXRETURN, EQROOT and MANN, not a surrogate
routing equation. It supplies an hourly return pulse plus constant background
flow to a synthetic 5 km channel. Identical forcing is run continuously for
48 hours and as two daily calls. The reference is uninterrupted native execution,
not exact physical truth or a demand for universal conservation.

Six method/path controls reproduce the unmodified routine exactly with inactive
hooks, both with and without observation. Causal controls freeze the grid and
reference coefficient selection; separate runs retain native grid selection.
The first diagnostic state-retention lane deliberately stops rather than
inventing a transfer when the grid changes. Those six intentional stops are
retained as evidence, not counted as model crashes or successful repairs.

For a 3,600 m3 final-hour return pulse, these are the **48-hour outlet-integral
errors caused by restarting**, relative to uninterrupted native execution with
native grid selection:

| Routing method | Lateral source, legacy reset m3 | Top source, legacy reset m3 | Retained-state result |
| --- | ---: | ---: | --- |
| Kinematic wave | -809.950 | +1,314.880 | Exact reference trajectory |
| Fixed-coefficient Muskingum-Cunge | -1,121.128 | +1,271.753 | Exact reference trajectory |
| Variable-parameter Muskingum-Cunge | -905.195 | +2,413.763 | Exact reference trajectory |

The error can add or remove represented outflow depending on the spatial profile;
it is not merely an extra copy of the last timestep. The repair also gives exact
restart agreement in all 18 fixed-grid cases covering steady flow, noon and
last-hour pulses through top and lateral paths. On the tested native grid-change
controls, the largest remaining integrated difference from the continuous
reference is about 0.0263 m3, versus a legacy difference of about 4.0885 m3 in
that case. Grid/coefficients still differ from the uninterrupted run; no universal
accuracy claim is made from that comparison.

![Native restart comparison](../../ablation/20261007_channel_discharge_closure/artifacts/repro/hourly-midnight/restart-comparison.png)

### Separate forcing-boundary diagnostic

Actual MIXRETURN creates six 600-second means for a one-hour, 1 m3/s pulse.
Their interval sum is 3,600 m3. Applied to the adjacent-point averaging used by
lateral point mode, a last-hour pulse places 3,300 m3 before midnight and 300 m3
in the following first interval. A cold-start first-hour pulse instead gives
3,900 m3 under that point interpretation. A noon pulse retains 3,600 m3 over
the full pulse. These are source-operator measurements, not watershed water-loss
estimates.

An additional pure-return control uses the already-existing cell-mean mode only
as a diagnostic. The fixed-coefficient lateral peak stays approximately
0.456525 m3/s while shifting one 600-second sample earlier. Top-source results
are unchanged by that mode switch. It does not supply a general fix for mixed
rainfall, return and upstream-channel inputs, nor evidence that it removes the
Cedar pulses. The candidate therefore leaves the global mode unchanged.

## Implemented patch

Worktree: `/home/workdir/wepp-forest-hourly-midnight-20261008`.
Branch: `candidate/hourly-midnight-20261008`.
Base: `f24c957e3` plus the archived hourly component source, not daily v2.

Relative to the archived hourly source, only three source files differ:

- `src/chrstate.for`: retains each channel's final nodal discharge profile and
  segment count. On the same grid it copies state exactly; on a changed uniform
  grid it uses bounded linear interpolation. The caller's upstream boundary
  remains authoritative. Initial-run reset clears the saved state.
- `src/wshchr.for`: one call restores the profile after existing initialization;
  another saves it after routing. No routing recurrence, coefficient calculation,
  source volume, rainfall duration, source weight or ledger equation is changed.
- `src/makefile`: links the helper into the matching watershed/hillslope builds.

This is channel routing memory, not a new hillslope water reservoir or source
tail beyond the 24-hour constraint. It is implemented and exercised in actual
watershed runs, but remains uncommitted, unmerged and unpromoted. No older channel
patch bundle or daily-mean estimator was added.

## Fresh watershed validation

All 864 Cedar hillslopes and the complete 1980-2003 watershed finish successfully.
All 6,048 hillslope output files, including PASS, are byte-identical to the hourly
parent. All 140 independent-watershed hillslopes and its complete 1980-2024
watershed also finish; their 980 hillslope files are exact to the hourly parent.
Every simulation uses freshly generated matching-build passes.

Fresh conversion with the retained v1 reader accepts 7,573,824 PASS and 16,690,464
WAT records with no rejections. Totalwatsed streamflow remains +0.393 m3 relative
to `wepp_260803` over Cedar's full record. Installed reader extensions are unchanged.

### What the state repair changes in Cedar

| Measure | Hourly parent -> hourly plus state repair |
| --- | ---: |
| Sampled outlet integral, full record | +30.30 m3 (+0.00000239%) |
| Daily-ledger volume, full record | +0.96 m3 |
| Sum of absolute daily integral-ledger gaps | -91.22 m3 |
| Outlet sediment, full record | +0.09 kg |
| Published hydrograph changed days | 130 of 8,766 |
| Largest published instantaneous change | 0.01 m3/s |
| Largest absolute daily volume change | 12 m3 (about 0.0101% on that day) |

The recession-turn screen adds five turns, each one printed discharge increment
(0.0001-0.01 m3/s); none of the large preexisting turns is removed. The screen
count changes 883 -> 888, not a claim of five new physical storms. Differences
at this scale should not be oversold as measurable hydrologic improvement.

### What it does not fix

The **entire published hydrographs** for the retained 1990 small-control window,
1998 small-control window and October 25-30, 1994 window are identical to the
hourly parent. In particular:

| Time | wepp_260803 m3/s | Hourly parent m3/s | State repair m3/s |
| --- | ---: | ---: | ---: |
| 1990-10-22 01:10 | 0.530 | 1.260 | 1.260 |
| 1998-09-19 01:10 | 0.351 | 2.000 | 2.000 |

The October event retains +0.148% sampled volume, about +117 minutes centroid,
and +72.3% October 28 daily volume relative to baseline. Its October 28
integral-ledger discrepancy remains -20,207.65 m3 versus baseline -7,260.18 m3.
The previously concerning timing behavior is not resolved by channel state carry.

Full-record sampled volume remains +0.04362% relative to baseline. Outlet sediment
is 258,748.76 kg versus 202,652.51 kg (+27.68%); this is the hourly candidate,
not the daily-v2 sediment comparison. Hill sediment and physical peak behavior
remain those of the hourly correction. No aggregate score overrides the event
findings.

![Cedar three-way comparison](../../ablation/20261007_channel_discharge_closure/artifacts/repro/hourly-midnight/warming/three-way/windows.png)

The hourly-parent and state-repair curves overlap exactly in these windows.

### Independent watershed and controls

On the independent 45-year case, the incremental state repair changes reported
water volume +1.55 m3 and sediment +1.84 kg. All 16,437 dates match; maximum
daily ledger difference is 0.60 m3 and maximum daily peak difference 0.00017 m3/s.
Rounded annual outlet water/sediment remain 2,053,454 m3/year and 1,255.9 tonnes/year,
versus baseline 2,053,457 m3/year and 1,218.9 tonnes/year. These are compatibility
and non-regression observations, not field validation.

Fresh H106 trigger/control runs preserve the hourly physical correction:
240.274/274.596 -> 1.605/2.038 mm/h, with runoff unchanged. Observer off/on outputs
match, and the Ksat-1 no-return control preserves its runoff, peak and sediment
results. Physical sediment effects remain those documented for the hourly parent.

Validation completed: 47 focused tests, 134 full pytest tests (two existing
tarfile warnings), both maintained host smokes, 12/12 permanent watchlist cases,
and system ELF loader checks. The historical dual-binary pytest guard test still
uses its historical executables; it is not substituted for the fresh candidate
watershed runs. No reader source changed; fresh conversion used the frozen v1
extension rather than the incompatible daily-v2 reader.

## Why hold here

The source already concentrates 90-98% of the two controls' returned water in
the final hour. Correcting the internal restart does not change that input.
The remaining mean/point mismatch needs a coherent component-specific consumer
contract for both top and lateral inflow. A global mode switch changes unrelated
rainfall behavior and does not address both paths; simply clearing aggregate q0
would also discard legitimate boundary continuity.

Most importantly, neither is evidence that the scheduling-driven source pulse
should be removed by numerical routing. Retaining its hourly bin timing and all
its water within the day constrains how much it can be flattened. Any different
return timing/attenuation or upstream scheduling change needs an explicit
scientific decision. No such assumption was inserted during this campaign.

**Keep the isolated state repair as a tested correctness patch for review;
withhold acceptance of the combined hourly candidate.** No general routing
rewrite, precision campaign, automatic daily averaging or further rescue patch
is proposed as completed work. The full work package remains unresolved.

## Provenance and reproduction

| Artifact | SHA-256 |
| --- | --- |
| Candidate watershed | `80af8861cb47601d010a5487933a96d2b538912fd5fb878f0a1880af56f0d1ac` |
| Candidate hillslope | `228f045df0a8289996e849a1511716cdb92224073ba09d704285e4191faa46ff` |

Raw roots are `/wc1/holdouts/channel-discharge-hourly-midnight-20261008` and its
`-warming`, `-independent` and `-triggers` companions. Source, diagnostics,
receipts, complete comparisons and hashes are preserved in the
[compact archive](../../ablation/20261007_channel_discharge_closure/artifacts/repro/hourly-midnight).
Large watershed inputs, binaries and Parquet outputs stay outside git.

Candidate build commands, from the isolated `src` directory, were sequential:

```bash
make clean
make -j4 FC=/usr/bin/gfortran wepp
make -j4 FC=/usr/bin/gfortran wepp_hill
make prepare_watershed_includes
```

Execution scripts are `probe_midnight.py`, `probe_midnight_transfer.py`,
`probe_midnight_forcing.py`, `run_midnight_watershed.py`,
`run_component_triggers.py`, `convert_component_yield.py`,
`assess_midnight_watershed.py` and `finish_midnight_evidence.py` in this package.
The frozen [plan](midnight-repair.md), instrumented driver sources, diagnostic
patch and candidate diff are retained. Native probe builds used gfortran with
`-O2 -fno-align-commons -mcmodel=medium -ffixed-form -ffixed-line-length-72
-finit-local-zero -ffpe-trap=invalid,zero,overflow -no-pie` against frozen hourly
includes and the actual routines named above. Fixed-grid controls are explicitly
diagnostic; no fixed-grid override exists in the candidate.
