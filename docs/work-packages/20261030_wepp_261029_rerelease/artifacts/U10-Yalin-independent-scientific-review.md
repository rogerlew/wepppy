# U10 shared Yalin capacity review

This is an independent AI scientific review, not institutional peer review.
Scope: the shared factor in TRNCAP and YALIN, and the Cedar Creek negative
intermediate class transfers retained from U9a. Runtime edits are owned by
the implementation lane; this reviewer changes only evidence and review files.

## Equation and repair scope

The physical positive-excess-shear domain gives nonnegative sigma. The factor

`f(sigma) = 1 - log(1 + sigma) / sigma`

has the integral representation

`f(sigma) = integral_0^1 sigma*t / (1 + sigma*t) dt`.

Consequently `f(0) = 0`, and `0 < f(sigma) < 1` for positive sigma. It is
monotonically increasing. A negative value in that domain is arithmetic
failure, not a physically meaningful negative transport capacity. The two
native consumers previously evaluated the cancellation-prone expression in
single precision. A small positive sigma can therefore produce a negative
factor, including before any sediment deposition solver is called.

U10 evaluates the same equation in a shared helper appended to SHIELD, an
existing link dependency of both callers. For absolute sigma below 0.01,
it evaluates the alternating series `sigma/2 - sigma^2/3 + ...` in double
precision; twelve terms make truncation negligible compared with the final
single-precision result. At zero it returns the exact limit; elsewhere it
uses the direct expression in double precision. This is a justified numerical
repair without a capacity floor or altered physical parameter. Positive
values too small to represent in the returned precision may round to zero.

The repair leaves excess-shear selection, particle weights, the in-place
small-QS floor, TRNCAP redistribution, sand adjustment, and downstream
allocation rules intact. Their invariants are not established solely by the
factor proof. The retained unequal-class native tests and fresh whole-run
checks must cover those consumers. YALIN is also a hillslope consumer, so
hillslope parity with U9a cannot be assumed and all final gates must use the
new source and matched binary pair.

## Required evidence and limits

The committed bounded red proof `a8780759b` exercises actual TRNCAP, YALIN,
and SHIELD calls at both optimization levels. It establishes this shared
failure independently of the Cedar scenario. Native green controls must
cover zero and small positive sigma, both sides of the series threshold,
ordinary and large sigma, and unequal particle classes. Accuracy must be
checked against an independent high-precision evaluation, with literal
nonnegativity in the physical domain.

The richer frozen-U9a Cedar observation now reproduces all nine standard
watershed outputs and all 77 prior negative-transfer records exactly. The
34 first-negative frames all contain positive sigma but negative TRNCAP
factor and capacity before positive-QLAT CASE12 (28) or CASE34 (6). The
other 43 records propagate negative entering load. The executable classifier
`review_cedar_negative_causality.py` and its receipt
`review-U9a-Cedar-negative-causality.json` retain those states and provenance
in the incident's `artifacts/repro`. This establishes the field-case causal
link without relying only on a synthetic instability example.

The exact first Cedar five-class input has also been replayed against actual
frozen U9a and U10 sources at both optimization levels. The old negative
class-5 capacity forces redistribution that suppresses classes 1–4 to the
existing QS floor near `1e-31`. Correcting the factor restores their ordinary
positive capacities, approximately `1.75e-4`, `6.81e-5`, `1.70e-4`, and
`3.37e-5`; class 5 changes from `-2.056e-11` to `+2.749e-15`. Thus the repair
can change more than a tiny negative residual. The independent native receipt
is `review-U10-Cedar-capacity.json`, with exact inputs in
`review-cedar-negative-capacity-input.json`. This bounded replay does not
replace the required fresh U10 studies.

Release acceptance additionally requires a fresh U10 Cedar run, full-period
channel class sign/finiteness observations with unchanged standard outputs,
particle-output audits, and review of changed hillslope and watershed
quantities. Removing the known cancellation does not justify assuming there
are no other negative producers. The material U9a increase in sediment
transport remains a separate, already attributed effect of the channel
source/guard/constant-discharge repairs; it is not evidence of measured
sediment calibration.

## Why the earlier audit did not establish this invariant

The converted PASS particle audit validates exported hillslope records. It does
not inspect channel-internal class transfers. Subsequent redistribution, the
existing QS floor, aggregation, and printed precision can hide a negative
intermediate value from final output checks. The full-period CHNRT sign
observation exposed this separate producer defect. Retained tests now exercise
the actual shared factor and both native consumers; the fresh full-period
channel observation remains the end-to-end check. Neither substitutes for
the other.

The Cedar input manifest also contains a copied `pw0.err` sidecar with an
older completion footer. That file is not a current-run completion sentinel.
The retained observer instead requires the actual process exit status, all
24 fresh stdout year markers, and exact equality of the nine standard outputs.
The final acceptance receipts must use those executable checks.

## Final matched U10 channel evidence

The final source is `ba9f2ad91b5165d5cd2954bd64b5df608798541e`. The actual
system-built dated pair is frozen in `U10-build`: watershed SHA-256
`819b91721f67c4a86a5ecea14c5beb840e9a705025da2a2cedf2b97a5e067715`,
hillslope `21d8480041d2efed942abb8471271ce1a11c5f72190d45c0c42dbe0028c019ed`.
The fresh 864-hillslope/24-year Cedar lane and observed replay use this pair's
own generated PASS files. The observed replay reproduces all nine standard
watershed outputs exactly.

There are **zero negative or nonfinite intermediate class transfers** over
the full 24-year observed run. The sixteen declared detail dates contain
5,936 channel-events and 29,680 actual lateral source-class records. Maximum
relative source residual is `1.8392e-7` after the retained unit conversion;
maximum local signed-bed closure residual is `3.5307e-8`. Segment joins are
exact. These are local and declared-panel checks, not a whole-watershed
sediment closure claim. The maximum printed publication-versus-segment
residual is 0.00212 kg.

All four established adverse channel exports, including channels 235 and 245,
are exactly unchanged from U9a. Across the sixteen dates, the largest absolute
change in event-summed local bed erosion is 0.00189 kg; the corresponding
maximum for deposition is 0.00447 kg. There is no new broad bed-exchange
increase in this panel. The receipt is `review-U10-Cedar-channel-audit.json`,
SHA-256 `4ecbe7922b3ac21fa79b4de9a4785973e55d03cc626bd425ca4ad480a86fa7fc`.

Direct completed native outlet readback gives 517,815.77 kg versus U9a's
517,815.78 kg. Only one of 8,766 printed daily sediment values changes:
1999-11-25 decreases by 0.01 kg. The broader increase versus the original
release therefore retains the U9a recovered-transport attribution. Independent
converted semantic and particle checks have also completed successfully.

## Final semantic scope and limits

Native conversion accepts all 7,573,824 PASS and 16,690,464 WAT records with
zero rejections. All audited water fields are finite and nonnegative; all
particle concentrations and fractions have zero negative, nonfinite, or null
records. All 864 hillslope WAT, soil, element, and plot files remain exactly
U9a. Fourteen EBE, 25 PASS, and one loss file change across 26 hillslopes.
All three channel water output files are exactly U9a, and all eleven reviewed
daily water/source/peak quantities agree on every one of 8,766 dates.

Relative to the original release, the final sediment total is 517,815.77 kg
versus 180,137.20 kg, an increase of 187.456%. This is a material model-output
change, not calibration evidence. The detailed U9a attribution establishes
recovery of incoming transport previously lost at the hydraulic guard and
constant-discharge branch, while removing fabricated lateral source mass;
U10 preserves that attribution. Annual sediment changes versus the original
range from -0.303% to +1,286.54%, so an aggregate-only presentation is
insufficient. Published water volume increases by 313.78 m³ (0.00002475%);
maximum sampled peak is unchanged, but individual daily sampled peaks can
differ by 0.71 m³/s. These earlier hydrology/event-state effects are retained
from U9a; U10 changes none of the daily water or peak quantities.

The independent receipt `review-U10-Cedar-semantics.json` retains daily
extremes, annual/monthly groups, and exact file comparisons against U9a and
the original release. Source and bed closure remain local checks on the
declared sixteen dates. The original physical constitutive approximations,
unit conversions, lack of measured-sediment calibration, and unresolved Roads
magnitude objectives are not waived by this review. In particular, native
repair acceptance does not imply the Roads parameterization program has met
its magnitude targets or authorize changing its defaults.

## Disposition

**Accept the final U10 native repair for scientific release review.** The
shared-factor repair is mathematically justified and correctly scoped to both
confirmed consumers. The confirmed intermediate-negative-load blocker is
closed by matched full-period evidence. The complete fresh semantic, particle,
source, and signed-bed audits find no remaining scientific blocker within the
reviewed scope. No nonnegative gate was relaxed, and no negative capacity or
load is clipped by this repair.

This disposition applies to the exact source and matched dated pair identified
above, with the material watershed sediment changes and stated limitations
published. Operational release/vendoring gates remain owned by the release
orchestrator. This is independent AI review, not institutional peer review or
validation against measured watershed sediment.
