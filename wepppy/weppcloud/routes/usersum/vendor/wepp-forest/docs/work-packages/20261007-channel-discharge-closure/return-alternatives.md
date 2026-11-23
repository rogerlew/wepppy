# Surface return alternatives: simplicity and correctness

2026-10-08. Roger requested deeper assessment, emphasizing simplicity rather than
another attempt to make the entire legacy model physically complete.
**Assessment only:** no new producer implementation, hillslope/watershed run,
timing assumption approval, release, vendoring or deployment.

## Recommendation

Do not start an ET, infiltration or percolation reconstruction. Deeper inspection
weakens my earlier recommendation to start with producer scheduling: a small
edit there can have a large physical scope, yet do little to the target burst.

The most promising small rule to specify for one feasibility test is a
**return-only rectangular source that retains the legacy storm support and
extends it only when needed to carry the return volume below its hourly peak**:

```text
Physical erosion peak remains: Pr + Ps
Ps = existing hourly return maximum, on the appropriate area basis

Return source support: Ts = max(Tb, Vs / Ps)
Return source rate:    Qs = Vs / Ts
Return source origin: existing computational event origin, t = 0
Rainfall source:      unchanged native rainfall-only reconstruction
```

Here Tb is the existing rainfall/storm support, not erosion effective duration.
Vs and Ps must use the same area basis and time units. At the consumer, use the
same caller volume allocation as the hourly parent. Do not derive Ps by
subtracting a return rate from a combined, floor/cap-adjusted published peak.

**This is a proposed engineering approximation, not a demonstrated physical
timing correction.** It preserves return volume and the hourly physical erosion
estimator, but the reconstructed return rate can be below Ps. It treats the
hourly maximum as a ceiling for channel-source forcing, not a rate that must be
attained. It also discards the computed hourly placement of return in favor of
the existing event clock. Both choices require Roger's explicit agreement.
Compared with literal unattenuated hourly forcing, it reduces the return peak
entering the channel on some events. Keeping the hourly producer estimator does
not by itself authorize that change.

If maintaining the exact hourly maximum at the channel inlet is also mandatory,
this proposal does not satisfy that stronger requirement. The simple
peak-preserving alternatives below retain the burst or move it elsewhere; no
successful minimal solution under all those constraints is established.

## What the additional evidence says

Read-only analysis covers all 61,645 eligible positive-return EVENT records on
463 Cedar hillslopes, representing 23.651 million m3 of unallocated return.
These are the active single-OFE/non-contoured hourly component records, not all
watershed runoff or all possible model modes.

| Source characteristic | Records | Share of eligible records | Share of eligible return volume |
| --- | ---: | ---: | ---: |
| More than half of return in hour 24 | 8,879 | 14.40% | 1.98% |
| At least 90% in hour 24 | 4,450 | 7.22% | 0.67% |
| One-hour equivalent support | 3,849 | 6.24% | 0.55% |
| More than 12-hour equivalent support | 20,295 | 32.92% | 49.93% |

These grouping boundaries describe the population; they are not proposed
eligibility thresholds. The small volume share explains why annual agreement
can hide a serious event-level change. It does not make those events unimportant.

The hourly-return maximum is a median 3.24 times the daily mean, reaching 24
times for single-hour return. The original hourly records' return-volume-weighted
centroid is 14.93 hours into the computational day. Uniform daily forcing would
move it to 12 hours; a peak-height box starting at zero would move it to 6.54
hours. The proposed legacy-supported box gives 9.11 hours. These are source
arithmetic, not outlet timing predictions or observed physical clock times.

### Native source comparison on the problem days

The existing, identity-verified CHRQIN harness reconstructs the baseline and
rainfall-only contributions. Hypothetical return shapes are then added with
interval-overlap means. This compares current-day contributions from the same
selected active hills, at 600-second resolution. It excludes baseflow, other
hills, receiving-channel lateral rescaling, prior-day boundaries and routing.

| Source day | Representation | Aggregate source peak m3/s | Sampled source centroid h |
| --- | --- | ---: | ---: |
| 1990-10-21 | Native baseline | 0.1556 | 5.006 |
| 1990-10-21 | Literal hourly return | 1.3872 | 23.567 |
| 1990-10-21 | Peak-height return box | 1.3872 | 0.593 |
| 1990-10-21 | Proposed legacy-supported return box | 0.1531 | 5.042 |
| 1990-10-21 | Daily-flat return, hourly erosion peak retained | 0.0587 | 12.083 |
| 1998-09-18 | Native baseline | 0.3290 | 5.211 |
| 1998-09-18 | Literal hourly return | 2.8564 | 23.324 |
| 1998-09-18 | Peak-height return box | 2.8564 | 0.743 |
| 1998-09-18 | Proposed legacy-supported return box | 0.3245 | 5.254 |
| 1998-09-18 | Daily-flat return, hourly erosion peak retained | 0.1326 | 12.083 |
| 1994-10-27 | Native baseline | 13.5585 | 5.603 |
| 1994-10-27 | Literal hourly return | 9.2062 | 12.695 |
| 1994-10-27 | Proposed legacy-supported return box | 9.2266 | 7.448 |

**These are not Cedar outlet predictions.** The proposed rule is promising
because it avoids newly concentrating the two ordinary source events while
retaining a lower source peak on the large October event. Actual watershed
behavior, timing, sediment transport and the original trigger consequences
would still require fresh matching-build validation.

The new return alternatives carry the same allocated return volume and use the
same rainfall reconstruction. Their represented total source volumes agree
with each other. The baseline native curve has its known reconstruction
discrepancy; matching that over/underrepresentation is not the objective.

## Alternatives ranked

| Alternative | Implementation and behavioral scope | Assessment |
| --- | --- | --- |
| Keep literal hourly forcing | No further code; retains the measured hourly candidate and its late pulses | Honest fallback, but not a demonstrated resolution under the current standard. |
| Legacy-supported return rectangle; hourly peak retained for erosion | Small source-assembly change using existing quantities; no soil-water scheduling or new user parameter | Best first specification for one bounded test, if the timing and peak-ceiling assumptions are explicitly approved. |
| Peak-height rectangle, duration Vs/Ps | Small code change; preserves return volume and maximum, but needs a timing convention | Moving it to day zero relocates the burst rather than suppressing its amplitude. Retaining its original centroid leaves a final-hour-only pulse unchanged. |
| Daily-flat return only at the channel source | Small code change; daily hillslope water/erosion calculations can remain unchanged | Coarser than necessary for many events; changes timing and can reduce delivered return peak by a factor of 24. Requires explicit approval; daily-v2 results do not validate this hybrid. |
| Move the existing last-hour PURK call after ET | Few lines, but changes soil-water and runoff partitioning | A cheap process-order diagnostic is possible, but the evidence below suggests limited direct leverage on the burst. Not the first implementation campaign. |
| Separate and redistribute only residue-driven return | Requires a residue diagnostic, source attribution/allocation, state/area handling and consumer semantics | Appears targeted but introduces difficult attribution assumptions. Do not begin by inventing min(release, return) as a physical identity. |
| Add hillslope attenuation or source carry | New response assumption/state lifecycle; existing tcs is not automatically its calibration | Larger scope and not clearly sufficient. Channel carry already exists; the repaired state defect did not remove the pulses. |
| Make ET/infiltration genuinely hourly | Broad process/timing, soil-state and output consequences | Outside the bounded objective. This is the path most likely to reopen the failed comprehensive-correctness campaign. |

### Why the legacy-supported rectangle is different

For a returned volume Vs and maximum hourly rate Ps, equivalent rectangular
duration Vs/Ps lies between one and 24 hours for the represented hourly weights.
The proposed support is never shorter than the existing storm support. Its
rate is equivalently `min(Vs/Tb, Ps)` when Tb is positive: it does not create a
sharper return pulse merely because daily bookkeeping put water into one hour.

Across the actual population, only 7,149 records (11.60%, carrying 15.06% of
eligible return volume) need support longer than Tb. Every proposed duration
fits within the existing day; observed proposed supports range from 2.5 to
24 hours. The median reconstructed return rate is about 0.509 times Ps.
That reduction is an explicit approximation, not hidden behind the phrase
"hourly estimator retained."

This is not the rejected endpoint rule. It does not use the last positive return
hour to stretch the complete mixed hydrograph. It leaves rainfall support alone,
and uses Vs/Ps only because the return shape is explicitly rectangular, not
because every CHRQIN shape has that duration-volume relationship. No numerical
duration inversion or existing rainfall-branch rewrite is needed.

It also does not repeat the earlier pure-return-only eligibility mistake: small
positive rainfall remains represented independently. No rainfall-fraction or
return-dominance threshold is proposed. As return volume tends to zero, its
added source tends to zero without moving the rainfall hydrograph. This does
not remove inherited native rainfall-solver or sampling discontinuities.

The remaining accuracy cost is real: returned water could physically be sharper,
later or differently distributed than this event-scale representation. Legacy
storm support is a behavioral reference and available timescale, not proof of
return-water travel time. Numerical simplicity must not be presented as new
physical knowledge.

### Why the other simple shapes are not free solutions

A one-hour return pulse has Vs/Ps = one hour. A rectangle preserving volume,
maximum and its 23.5-hour centroid is exactly the original final-hour pulse.
Changing its shape without changing any of those facts cannot greatly flatten it.

Starting all peak-height rectangles at day zero retains the high source rate,
but advances the two controls' return centroids by about 22.6-23.0 hours. It can
simply move the problem earlier or increase overlap with rainfall. Synchronizing
individual peaks increases the aggregate return-source maximum by up to 7.36%
over the 1,292 active source days, although the two selected controls already
have synchronized maxima. Do not call relocation a successful repair.

A triangle at the same maximum requires twice the rectangular support. It cannot
fit within 24 hours for 32.92% of eligible records, carrying 49.93% of the return
volume, without changing the maximum or volume. A generic "smoother shape" is
therefore not automatically a simple, compatible answer.

Daily-flat channel return has the opposite problem: for the two controls its
return-only rates would be approximately 0.0587 and 0.1326 m3/s instead of hourly
maxima 1.3872 and 2.8564 m3/s, and its source centroids would move about 11.2-11.5
hours earlier relative to the hourly bins. It may be an acceptable coarse model,
but it is a deliberate loss of peak and timing information at the channel input.
Keeping the physical erosion peak hourly would distinguish it from the unapproved
daily-v2 estimator; it would not make the routing approximation physically exact.

## Why producer rescheduling is not the obvious minimal repair

The actual sequence is hourly input, PURK, final-hour daily ET/residue release,
upward redistribution, drainage/lateral flow, then surface surplus. A simple
reorder could put the existing final-hour PURK call after ET, without adding a
25th percolation step. It would not require a new reservoir or transport file.

However, all 12 traced positive-return cases have top-layer saturation at least
0.95 before PURK, so its conductivity multiplier is already at its maximum.
PERC caps its computed daily seepage by available excess, then PURK divides by
24 in hourly mode. Holding ET/release, conductivity and other operands fixed,
adding residue R before that call can increase top-layer percolation by at most
R/24. The observed roughly 2.6 mm releases give about 0.109 mm additional drainage,
only 1.48-4.54% of the observed 2.4-7.4 mm final-hour return.

This is a conditional local bound, not a prediction of the fully coupled
counterfactual. Reordering ET can also change evaporation, transpiration,
lower-layer drainage and upward redistribution. Those changes could have larger
effects, but then the patch is succeeding by changing the water balance, not
merely repairing an event timestamp. Daily runoff, baseflow and erosion history
would require a different validation scope.

Do not "fix" the existing PERC/PURK timestep convention as a follow-on to make
this reorder more effective. That would expand the target into percolation
physics. Nor should PURK be called a second time after ET: that adds processing
time to all available profile water, not just the residue remainder.

The residue-only alternative also lacks a unique surface-water allocation. On
H259 in the 1990 control, 2.616 mm residue release accompanies 4.174 mm final-hour
return; simply subtracting the release still leaves 1.558 mm. On H367, the
2.616 mm release exceeds the 2.489 mm surface return. These are not parcel
attribution or rerun results. Late saturation remains even if residue timing
is changed.

Finally, existing tcs is below an hour in 61,619 of 61,645 eligible records;
the two problem days' return-volume-weighted values are about 18 and 14 minutes.
That is not an already-justified multi-hour smoothing time. Adding a response
kernel would require its own physical interpretation, and causal attenuation
of final-hour water naturally raises cross-day source-state questions.

## One bounded next test, not another campaign

The decision to request is specific: **retain the hourly physical erosion
estimator, but permit an event-scale return source with the hourly maximum as
its ceiling and legacy storm support as its minimum duration.** Do not infer
agreement to that choice from authorization to continue assessment.

If approved, freeze the formula, computational origin and component semantics
before implementation. Use existing component quantities; settle PASS contract
versioning explicitly and use fresh matching-build passes. Do not silently
reinterpret old experimental files.

Start with both original H106 triggers, the two small-event controls, the
43.484 mm rainfall control with 0.01 mm late return, and zero/vanishing rainfall
and return cases, including first-day initialization and midnight. Demonstrate
unchanged hourly physical peaks and non-PASS
hillslope outputs relative to the hourly parent. Measure full event and adjacent
day behavior, not only whether a 01:10 peak disappears. Use interval overlap
for the return endpoint; do not reintroduce a whole-cell truncation.
Ts is a local return-source support only: do not write it back into the legacy
storm duration or erosion effective-duration fields.

Only if that fixed rule helps should one full Cedar/independent validation follow.
Assess water volume, timing, pulses, daily accounting and sediment under the
existing practical standard. Existing nonzero discrepancies may remain; aggregate
fit cannot hide a serious event regression. Stop if the rule merely moves the
unwanted pulse or broadly worsens ordinary events. Do not tune its origin, add
duration multipliers, introduce an eligibility threshold, or follow it with a
soil-water rewrite to rescue a failed candidate.

## Evidence and limits

Read-only outputs: `/wc1/holdouts/channel-discharge-return-options-20261008`.
Scripts: `assess_return_options.py`, `assess_return_boxes.py` and
`assess_return_support.py`. The latter invokes the previously verified baseline
CHRQIN probe, SHA-256
`1350bb0a61a8b1c709b810fd733ec56fe2257a89b1f1d06257687a33f5509c37`.
It evaluates 682 selected hillslope-day inputs twice, for baseline and isolated
rainfall reconstruction. No producer source is edited or watershed rerun.

Eleven arithmetic/geometry checks pass, including partial cells, the no-return
limit and rejection rather than clipping of support beyond the day. They are
analysis tests, not proof of an implemented or accepted physical candidate.
Input hashes, summaries, source-probe inputs/outputs and label mapping are in
[the evidence archive](../../ablation/20261007_channel_discharge_closure/artifacts/repro/return-options).
Full derived population CSVs remain in the external root with recorded hashes.

Earlier [hour-24 tracing](hour24-attribution.md),
[midnight repair results](midnight-repair-results.md) and failed/withheld candidate
results remain unchanged. They inform this assessment; none validates the new
proposed approximation by inheritance.
