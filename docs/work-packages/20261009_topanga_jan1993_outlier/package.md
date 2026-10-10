# Topanga January 1993 Event Outlier

Owner: Roger Lew. Opened 2026-10-10 02:05 UTC (2026-10-09 Pacific).
Status: release and vendoring complete, 2026-10-10, on Roger's explicit
authorization. See [release handoff](release-handoff.md),
[ADR-0084](../../adrs/ADR-0084-chrqin-source-normalization-release.md) and
[candidate results](candidate-results.md).
Subsequent proceed authorization covered the minimal repair and same-build
Topanga/Rattlesnake validation, superseding earlier no-patch boundaries below.
The later release authorization supersedes the earlier promotion hold, not
the measured consequences. Production deployment remains outside this task.

Follow-up [mutation and disturbed-ranking studies](hillslope-studies.md) are
complete with exact hillslope output parity versus wepp_261009. This closes
those requested checks; the reported channel-event consequences remain disclosed.

[Cedar water verification](cedar-results.md) is also complete: fresh paired
24-year runs preserve totalwatsed exactly versus 261009 and sampled outlet
volume within +0.001008% of 260803. Accounting gaps and timing limitations
remain documented, including the Rattlesnake sediment consequences considered
before the explicit release decision.

## Historical Opening and Diagnosis (Superseded Where Noted)

Mechanism update: [CHRQIN normalization indexing defect located](mechanism-findings.md).
An observer-neutral trace and actual-routine reproducer identify the first
inflation before channel routing. Status is diagnosis complete for this
mechanism; a bounded candidate and its validation remain to be completed.

Roger's subsequent site-specific adjudication supersedes the opening premise:
approximately 700 m3/s is not realistic here at any duration. Together with
the controlled 27.85 -> 707.64 m3/s release comparison, this establishes an
unacceptable defect in the new result. The remaining investigation concerns
where and why it forms, not whether the peak should be accepted. Earlier
outlier-first records remain historical evidence, not the current disposition.

Earlier: the [lower-network trace](upstream-findings.md) places a large pulse
at WEPP element 406, before it reaches the outlet. The remaining immediate
question at that stage concerned the inputs and state at 406, not an outlet-only defect.

New control: [same-input WEPP 260803 comparison](260803-comparison.md) finds
27.85154 versus 707.63910 m3/s for the undisturbed January 18 peak, with nearly
unchanged daily volume. The investigation now concerns a release-dependent
outlier. That control supports the source-normalization diagnosis above.

Current authorization: Roger approved output-only replay capture after the
opening readback. Pinned same-build regeneration of removed text PASS files
precedes paired peak-only/full-series watershed runs. Physical parameters and
600-second routing remain unchanged; full 1980-2024 history is preserved.
No behavioral model change or broader campaign is authorized. Continued
diagnosis follows observability-before-behavior with one bounded mechanism at
a time; it does not reopen routing reconstruction or comprehensive closure.

## Question

Why does `scrawny-relay`'s undisturbed GridMET scenario report an outlet peak
of 707.6391 m3/s on January 18, 1993, compared with 76.03957 m3/s burned,
when their daily outlet volumes are 218,608.19 and 213,282.16 m3 respectively?
Determine what the modeled forcing, antecedent state, source timing and routing
support before judging this response. A rare large peak or a burned/unburned
rank reversal alone does not establish a defect.

## Starting Evidence

The [pre-investigation comparison record](../../investigations/2026-10-09-watershed-return-period-comparisons/report.md)
preserves eight watershed series, including both `scrawny-relay` scenarios.
Both completed `wepp_261009` on GridMET 1980-2024. The event appears in both
watershed EBE and the separately published channel peak output. The first
two-year exclusion does not remove it. Encouraging Rattlesnake and Topanga
2-/5-year results remain evidence, not justification for accepting or rejecting
this individual event.

## Scope and Complexity Budget

Start with read-only analysis of the retained output window and the existing
source implementation. Preserve local event extracts with provenance; compare
burned and undisturbed counterparts, antecedent wet days and other large peaks.
Distinguish plausible hydrological concentration, source timing/coincidence,
parameter sensitivity, reporting/identity issues and numerical behavior.

No model/source patch, parameter revision, routing reconstruction, companion
transport, new runtime flag, comprehensive conservation exercise, release,
vendoring or deployment. No full-record campaign is implied. First identify
the narrowest missing observation. Any rerun or instrumentation proposal must
state the question it resolves and preserve same-build input/PASS provenance.
If later authorized, follow Forest's observability-before-behavior ablation
protocol. The broad defect-repair workflow is not activated by this outlier.

## Deliverables and Completion

The [opening findings](opening-findings.md) and hashed January 10-24 extracts
are available. They identify the absence of time-step outlet observations as
the immediate limitation; no causal or defect classification has been made.

The authorized [output-only replay](output-replay.md) is now complete. Both
45-year controls reproduce original outputs and both full-series captures are
observer-neutral. The outlet's irregular early pulse is observable; its source
and physical/numerical interpretation remain open.

Produce a reproducible event record, competing hypotheses with supporting and
contradicting evidence, and a bounded recommendation. Valid outcomes include
a supported modeled response, a demonstrated implementation/reporting issue,
a scientific assumption needing Roger's judgment, or insufficient observations
with a specific next measurement. Do not force monotonic event rankings or
invent numerical thresholds to manufacture any conclusion.

Security impact: none. Local scientific outputs are read without modifying live
projects or accessing credentials. No dedicated security review is required.
No production behavior change is authorized, so no implementation correctness
closeout or parameterization ADR is yet applicable.
