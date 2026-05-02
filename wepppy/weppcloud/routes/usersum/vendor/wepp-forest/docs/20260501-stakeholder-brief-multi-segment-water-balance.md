# Stakeholder Brief: Multi-Segment Hillslope Water-Balance Correction — What Changed, Why, and What to Expect

Date: 2026-05-01
Audience: Hydrologists, land managers, program staff, and analysts who use WEPP results, particularly anyone working with multi-segment hillslope (MOFE) outputs
Status note (2026-05-02 Stage 10C): U6C is promoted and deployed as release `wepp_260501` / `wepp_260501_hill`.

## The short version

WEPP represents a hillslope as one or more strips of land called **Overland Flow Elements** (OFEs). A **single-OFE** run uses one strip; a **multi-OFE** (MOFE) run stacks several strips down the slope so runoff, sediment, and cover state pass from each upslope element to the next. The MOFE configuration is the common choice for hillslopes with substantial along-slope variation — fire-disturbed transitions, riparian buffers, road and trail crossings, agricultural field sequences with changing management.

While running a routine per-segment water-balance audit on a long fire-disturbed MOFE simulation, we found a defect in WEPP's hourly hydrology code. On long downhill chains during large storm events, the model can produce per-segment runoff that exceeds anything physically possible. In our worst observed case, a single 30-meter slope segment near the bottom of a long cascade reported runoff equivalent to **180 inches of rainfall draining from that one segment in a single day** — a number that no real storm anywhere on Earth could deliver to that contributing area.

We have identified the underlying cause, designed and validated a fix that enforces conservation of mass at the segment-runoff calculation, and verified lane U6C against a stratified Stage 9A test set without finding a new failure class. Stage 10C has now promoted and deployed this fix as release `wepp_260501` / `wepp_260501_hill`. A detector triage step is documented in the production audit runbook (Stage 9C).

**The largest observed effects are in per-segment outputs from long MOFE cascades during extreme events.** The bias is **one-directional** in observed anomaly cases (too high, not too low) and scales with hillslope length and storm magnitude. Small-magnitude corrections were also observed in control contexts, so this brief does not claim MOFE exclusivity. The existing canonical advice to clip hillslope length on single-OFE setups remains valid; it addresses different physical concerns (calibration envelope, regime shift) and is unrelated to this defect.

## The hydrology, in plain terms

Real hillslopes are not uniform strips. Soils, vegetation, slope, and recent disturbance change as you walk down the slope. WEPP's MOFE configuration represents that variability by chaining several OFEs together, with each downslope element receiving runoff and sediment from the element above it. This is the standard way the model handles spatially variable hillslopes — fire scars, riparian buffers, road segments, harvest blocks.

To do that handoff, WEPP tracks two numbers for each segment: the segment's own **slope length** (how long the segment is along the slope, in meters) and an **effective contributing flow length** that represents how much upslope contribution is being routed into that segment. On a single-OFE run, those two numbers are equal — a strip contributes only to itself. On a multi-OFE run, the effective contributing length grows as you move down the cascade, because each downslope segment is receiving flow that originated farther up the hillslope.

This is the design of the model and it is the right design for a multi-OFE configuration. The defect is not in the concept; it is in how the accumulation was bounded — or rather, in the absence of a bound.

## The defect, in concrete terms

In the segment-routing routine, the effective contributing length grew without any physical upper bound. On a long cascade of segments during an extreme storm, the accumulated length could become very large compared to the actual physical geometry of the hillslope. The runoff calculation then produced a per-segment discharge that could exceed the total water that physically entered that segment from precipitation, upstream contribution, snowmelt, irrigation, and subsurface inflow combined.

The clearest example came from a hillslope at the bottom of a 19-segment cascade on day 44 of 1987 in a fire-disturbed simulation. The relevant numbers from the simulator's internal state were:

- Slope length of the segment: **30 meters**
- Effective contributing length the model was using: **300 meters** (about ten times the segment's own length)
- Reported runoff exiting that segment in one day: **about 4,592 millimeters** (roughly 180 inches)

That last number is not physically achievable. The total catchment area feeding into that segment, multiplied by the daily precipitation, multiplied by a worst-case runoff coefficient of 1.0, cannot deliver 180 inches of water to a 30-meter slope segment in a single day. The model's internal arithmetic was self-consistent, but it was not bounded by what physics permits.

The same pattern appeared, at varying magnitudes, on every long cascade we examined. The bias was always in the same direction (runoff and sediment numbers too high) and always concentrated on the late segments of the cascade during extreme storm events. A control set of well-behaved hillslopes also showed small-magnitude expressions of the same mechanism — corrections of less than a quarter of a millimeter per segment per day on the worst-affected days — confirming that the defect is continuous in magnitude across the model's domain rather than restricted to extreme-anomaly cases.

## How we investigated it

Like every other recent WEPP fix, this defect was tracked through a structured **ablation campaign** — the same evidence-driven discipline described in the [April 2026 stakeholder brief on compiler fragility](20260414-stakeholder-brief-compiler-fragility.md). The shape of an ablation campaign is the same regardless of which defect is being investigated:

1. Reproduce the failure from a clean environment, capturing the exact inputs, the binary identity, and the simulator's internal state at the failure boundary.
2. Add diagnostic observability before adding any candidate fix, so the model's internal state on the failing day is fully visible.
3. Form hypotheses about the cause that cite specific signals from the diagnostic output, not intuition.
4. Design candidate fixes (called **lanes**), with each lane changing one thing about the model's behavior and holding everything else constant.
5. Run each lane and compare its outcome against the unmodified baseline and against the other lanes.
6. Keep the smallest change that demonstrably resolves the defect; roll back any change that does not.

What was unusual about this campaign was its length. Twelve candidate lanes were tested before the right fix was identified and validated. The previous compiler-fragility fixes were typically resolved in one or two lanes; this one took twelve. The reason is worth understanding because it bears on the trustworthiness of the final fix.

The first family of attempted fixes tried to correct the symptom at the moment the runoff number was written to the output file. Each version of this approach made the audit numbers look better, but verification showed that none of them actually changed what the model was computing internally — the corrected numbers were being produced at write time only, while the simulator's hydraulic state and the dependent sediment and routing files were still computed from the unbounded values. This was the first hard lesson of the campaign: **a fix that does not modify the model's internal state is not a real fix.**

The second family of attempted fixes did modify internal state but tried to apply the correction only on hillslopes that were obviously misbehaving, while leaving well-behaved control hillslopes byte-for-byte unchanged. Each version of this approach demonstrated that no clean rule exists for separating "obviously misbehaving" from "well-behaved." Because the defect is continuous in magnitude, control hillslopes also show small expressions of the same mechanism, and any rule strict enough to catch the obvious anomalies also touches the controls. This was the second hard lesson: **the bug is continuous, and any fix that respects mass conservation will produce small corrections on every cascade-bearing hillslope, not just the catastrophic ones.**

The third family of attempted fixes tried to find a soft, tunable correction that would close the obvious anomalies while leaving controls unchanged. One such candidate appeared to succeed against the original audit metric, with anomaly residuals dropping by three orders of magnitude. A required verification step — a symmetric absolute-residual audit and a sensitivity sweep across the candidate's tuning parameters — revealed that the apparent success was a measurement artifact. The fix was redistributing the closure deficit across segments rather than eliminating it: pushing residuals from negative to positive on some segments while reading only the most-negative residual to report success. Under symmetric measurement, the worst absolute residual was 68 millimeters on a control hillslope segment, not the reported 0.005 millimeters. This was the third hard lesson: **one-sided metrics can mask deficit redistribution, and any candidate fix must be verified against a symmetric measurement before it is trusted.**

The deployed remediation lane (U6C in the campaign record) is conceptually the simplest of the twelve candidates. It enforces conservation of mass at the segment-runoff calculation. The campaign needed eleven other lanes to demonstrate that no alternative would work — that simpler-looking fixes were either symptoms-only, calibration-by-fitting, or measurement artifacts. Without that evidence base, a future investigator would be tempted to retry one of those approaches; with it, the discipline that produced the right answer is now an audit trail.

## The fix

The corrected code applies a single check during the hourly water-balance update on each non-contour multi-OFE segment. Before writing the per-segment runoff, the model computes how much water physically entered that segment from all sources combined: precipitation, runoff from the upslope segment, snowmelt, irrigation, and subsurface inflow. If the segment's runoff calculation would exceed that total, the underlying runoff state is reduced so that the per-segment runoff exactly equals the available water. If it would not exceed, the original calculation is left unchanged.

There are no tunable parameters in the fix. The check is exact mass conservation. It applies to every multi-OFE segment uniformly, regardless of hillslope, regardless of disturbance class, regardless of storm intensity. It leaves all subsurface terms, evapotranspiration, and percolation unmodified to avoid disturbing the sediment-loss calculation that depends on them.

The scientific basis for the fix is direct conservation of mass: runoff exiting a segment cannot exceed the water that physically entered it. This is the most fundamental constraint in hydrology and it is the constraint the unbounded recurrence was violating. The fix does not introduce any new physics; it enforces a physical constraint that should have been present all along and was not.

## What the deployed U6C release produced in validation

After the fix is applied, the three originally identified anomaly hillslopes show day-44 worst-segment closure residuals of 0.010, 0.010, and 0.020 millimeters — two orders of magnitude below our internal correctness threshold of 1 millimeter, verified under symmetric absolute-residual measurement (so the closure is real, not redistributed deficit). Control hillslopes show small expected corrections on the order of 0.12 to 0.23 millimeters on day-44 worst segments, corresponding to the small-magnitude expressions of the same mechanism that the cap correctly trims.

A broader stratified test set of 20 hillslopes drawn from four production run pools, covering the full range of segment counts, slope lengths, disturbance regimes, and detector severities, found:

- **Zero runtime failures** on any case.
- **Zero day-44 residual changes** (these cases happened on different storm-event timing than the original anomaly).
- **Nine of 20 cases showed full-period improvement** (full-simulation maximum residual reduced); the other 11 were unchanged.
- **Zero cases showed any regression** of any kind.

In Stage 9A evidence, U6C improved or preserved behavior on all sampled cases and did not surface a new failure class.

## Impact on multi-segment (MOFE) projects

If your work uses multi-OFE WEPP runs and consumes per-segment outputs, this is the impact you should expect.

**Per-segment runoff and sediment-yield numbers on long cascades during extreme storm events were biased high.** The bias scales with cascade length (more segments, larger bias) and with storm magnitude (larger storms, larger bias). The bias was always in the direction of overestimation; it never produced underestimates.

**The largest biases concentrated at the late segments of the cascade.** A run with three OFEs would show essentially no bias on segment 1, very little on segment 2, and the largest bias (if any) on segment 3. A run with ten OFEs would concentrate the bias on segments 7 through 10, with segment 10 typically the worst. A run with twenty OFEs could see severe biases on segments 17 through 20.

**Aggregate totals were less affected than per-segment detail.** A hillslope-aggregate runoff or sediment-yield number summed across all segments will reflect some of the bias if the late segments contributed substantially to the total, but the relative magnitude is smaller than the per-segment magnitude on the worst-affected segments. Watershed-level totals composed across many hillslopes will average out further.

**Disturbed-fire MOFE configurations were among the most affected.** Post-fire parameter changes (reduced infiltration, altered cover, modified soil hydraulic properties) tend to amplify runoff into the cascade, which amplifies the cascade-driven bias the bug produced. If your MOFE work involves post-fire watersheds or fire-effect quantification, treat the per-segment outputs from the most disturbed cascades as the priority for re-evaluation against the corrected model.

**Recommended action for MOFE users:**

- For **ongoing decisions** that depend on per-segment runoff or sediment-yield numbers from long MOFE cascades on storm-event days: pause or qualify those numbers until they can be re-checked against the corrected model. The corrected outputs will typically be lower than the pre-fix outputs on the affected segments.
- For **published reports or peer-reviewed work**: the question of re-issuance depends on whether your specific results sit in the affected regime. Send us the run identifier and we will evaluate it against the incident evidence and current detector workflow. Stage 10A did **not** execute an archive-wide sweep, so this brief does not claim archive-wide prevalence.
- For **new MOFE work**: use deployed release `wepp_260501` / `wepp_260501_hill` for this fix family. The detector triage step is documented in the audit runbook and should be treated as advisory evidence.

## Impact on single-OFE projects

If your work uses single-OFE WEPP runs, the impact is much smaller and probably zero for typical use.

**The cascade-amplification mechanism does not apply to single-OFE runs.** A single-OFE run has no upstream segment to receive contribution from, so the effective contributing length cannot grow beyond the segment's own slope length. The mathematical structure that produced the bug in MOFE runs simply is not present in single-OFE runs.

**Some single-OFE runs do show small corrections on cap-binding days.** Even in single-OFE configurations, the model can occasionally produce a per-segment runoff that exceeds the available water budget on a specific day under specific conditions (heavy rainfall on saturated soil, snowmelt amplification on a short slope). The mass-conservation cap will trim those overshoots when they occur. The magnitude of the trim is small — typically well under 1 millimeter on the affected days, and most days are unaffected.

**Standard single-OFE workflows are essentially unchanged.** If you run WEPP at a single profile scale with one slope, one soil, one management, and one climate, you should expect outputs to be either identical or trivially different from the pre-fix outputs.

**The canonical advice to clip hillslope length on single-OFE setups remains valid and is not changed by this fix.** That guidance addresses physical concerns that are unrelated to the cascade-amplification defect:

- **Calibration envelope.** WEPP's empirical erodibility and transport equations were calibrated at plot scale (typically 10 to 30 meters). Single-OFE runs much longer than that are extrapolating beyond the calibration envelope, which is a separate accuracy concern.
- **Hortonian regime breakdown.** Long single-OFE slopes can shift toward saturation excess or subsurface return flow, regimes WEPP does not represent well. The clipping advice partly addresses this.
- **Uniform-plane simplification.** Real long slopes are rarely uniform; clipping keeps the model in the regime where its uniform-plane representation is a reasonable approximation.

None of those concerns are touched by the present fix. The clipping advice continues to be the right setup convention for single-OFE work, for the same reasons it has been for the past two decades.

**Recommended action for single-OFE users:** typically nothing operationally immediate. Continue applying the existing clip-hillslope-length convention and use deployed release `wepp_260501` / `wepp_260501_hill` where this promotion is required in your environment.

## Impact on watershed-aggregate outputs

Watershed-level totals composed across many hillslopes will see very small changes. The mass-conservation cap reduces some per-segment runoff numbers on cascade-bearing hillslopes during specific events; those reductions propagate into hillslope totals, which propagate into watershed totals, but the watershed-scale averaging substantially dampens the per-segment effect.

If your work depends on watershed-aggregate runoff or sediment yield (the typical use case for management planning, watershed assessment, and regulatory reporting), corrected and pre-fix watershed numbers are expected to be close in most settings. The exception risk remains watersheds composed largely of long disturbed-fire cascades, where per-segment bias was largest and watershed-scale dampening is less effective. Stage 10A was a narrative waiver (no archive-wide sweep), so this brief does not claim that all affected watersheds have already been identified.

## Stage 10A scope limit and residual risk (explicit)

Stage 10A for this incident was completed as a documented narrative waiver, not as an archive-wide detector execution:

- No detector sweep was executed across `/geodata/wc1/runs/` in Stage 10A.
- This brief does not claim archive-wide prevalence (or absence) for this defect family.
- Residual risk remains that low-magnitude expressions may exist outside the currently analyzed evidence set.

If operating scope expands or governance requires quantitative historical-debt sizing, a future full archive sweep is a mandatory reopen action per the Stage 10A disposition.

## How to interpret historical work that used the pre-fix model

Three bands of confidence are reasonable:

**High confidence in pre-fix results:** standard single-OFE work, watershed-aggregate totals on watersheds without long disturbed cascades, and undisturbed multi-OFE work on short cascades.

**Moderate confidence in pre-fix results:** multi-OFE work on moderate cascades (5 to 10 segments) without extreme storm events, multi-OFE work on long cascades but only consuming hillslope-aggregate (not per-segment) outputs, watershed-aggregate totals on watersheds with some long disturbed cascades but not many.

**Lower confidence in pre-fix results, recommend re-checking:** per-segment runoff or sediment-yield outputs from MOFE runs with long cascades (15+ segments), per-segment outputs from disturbed-fire MOFE runs of any cascade length on extreme-storm years, any analysis that depends on the per-segment distribution of erosion across a long cascade rather than just the total.

If you are not sure which band your work falls into, send us the run identifier and we will review it against the current incident evidence and detector workflow.

## A few words about what we did not change

It is just as important to be clear about what the fix does not do.

- **The fix does not change WEPP's hydrologic or erosion physics.** It enforces a mass-conservation constraint that was already implicit in the model's formulation but not enforced by the code.
- **The fix does not introduce any tunable parameter.** There is no setting that can be adjusted to "soften" or "tighten" the cap. The cap is exact mass conservation.
- **The fix does not change the model on hillslopes where the bug was not present.** Standard single-OFE workflows produce essentially the same numbers as before.
- **The fix does not change which input setups are valid.** Any input that was valid before is still valid. The MOFE configuration is still the right tool for spatially variable hillslopes.
- **The fix does not deprecate or replace the existing canonical clipping advice for single-OFE runs.** That advice addresses different concerns and remains valid.
- **This brief does not claim archive-wide historical quantification.** Stage 10A explicitly recorded a waiver/no-sweep scope, with reopen triggers for any future full-archive quantification requirement.

## Where to find the evidence

The complete ablation package for this work, including every candidate fix, every test result, every governance decision memo, and every supporting artifact, lives at:

- [docs/ablation/20260430_uncapped-spectacular_h2637_ofe19-root-cause/](ablation/20260430_uncapped-spectacular_h2637_ofe19-root-cause/) — the incident package, with the complete twelve-lane investigation.
- [docs/science-contracts/wepp_hydrology_assumption_register.md](science-contracts/wepp_hydrology_assumption_register.md) — the assumption register entry for this defect (CONFLICT-001), including the underlying cause, the resolution, and the full evidence trail.
- [docs/science-contracts/contracts/SC-SED-001.md](science-contracts/contracts/SC-SED-001.md) — the formal sediment-coupling contract that documents the constraints the corrected hydrology code now honors, opened during the campaign.

Anyone with access to the wepp-forest repository can open these documents, walk through the campaign in chronological order, reproduce any intermediate result, and verify that the fix performs as described.

## Bottom line

WEPP's multi-segment hillslope configuration was producing inflated per-segment runoff and erosion numbers on long cascades during extreme storm events, because an internal contributing-length parameter was allowed to grow without a physical bound. U6C enforces conservation of mass at the segment-runoff calculation, has no tunable parameters, and Stage 9A stratified evidence found no new failure class on the sampled set.

If your work uses MOFE per-segment outputs from long cascades on storm-event days, especially in disturbed-fire contexts, those numbers were biased high and should be re-checked against the corrected model. If your work is single-OFE or aggregate at the watershed scale, the impact is small to negligible. The existing canonical advice to clip hillslope length on single-OFE setups was always responding to different concerns and remains the right convention.

Stage 10A did not execute a full historical-debt sweep, so archive-wide prevalence remains an explicit residual risk. In the meantime, send us the run identifier for any specific work you are concerned about and we will review it using the current evidence package and detector-guided audit workflow.
