# ADR-0117: Preserve all-top channel support and its deposition boundary

- Status: Accepted for the bounded all-top guard and constant-discharge transport repair in 261029 artifact revision 2.
- Date: 2026-10-30.
- Decision venue: WEPPcloud Roads development conversation, America/Los_Angeles.
- Participants: project owner and Codex, with independent scientific and implementation reviewers.
- Decision owner: project owner, authorizing defect investigation and remediation.
- Implementer: Codex.

## Context

Channel investigation following ADR-0116 identifies two coupled legacy defects.
CHNERO's existing soil-version-2006 guard truncates the virtual top length when
`topvol/latvol > 1e5`, but leaves positive lateral hydraulic eligibility. CHNRT
then initializes upstream discharge to zero and treats the full outlet peak as
lateral flow. Native guard controls were committed as `fa0cdaee7` before repair.

The existing zero-lateral-water deposition branches also lose the incoming load
and ignore distributed source response. Full native sediment-chain controls
(`5427a6afe`, `cd4d46bb1`) show constant capacity of 1 lb/s forcing an entering
2.2064 lb/s to 1 lb/s even as settling velocity tends to zero; exactly zero
settling produces zero load. Independent constant-discharge equations preserve
the incoming load in that limit. Merely adding a source-response correction
would preserve this confirmed no-source defect.

## Accepted guard decision (U8)

Only within the existing large-top-flow guard, keep physical-only geometry and
mark the local effective lateral hydraulic operand zero. CHNRT then uses its
existing all-top discharge path. Leave actual runoff, lateral source inventories,
peak, threshold, old-soil behavior and watershed water routing unchanged.

This is a bounded limiting approximation, not exact continuity: the upstream
fraction below the threshold is about 0.99999 and the all-top approximation is 1.
The retained step is at most about 1e-5 instead of the old near-unit collapse.
Fourteen paired native controls preserve every nonguarded control byte-for-byte.
The approximation cannot delete actual lateral sediment; ADR-0116 assigns that
mass independently. Correct zero-lateral-water deposition consumers before
accepting the combined guard/source change.

## Accepted deposition equation and scope

For a constant-discharge segment, use class load G and total-width capacity T
in lb/s, distributed source S in lb/s/ft, and
`lambda = settling_velocity * representative_flow_width / discharge` in 1/ft.
Adopt the existing segment-average width approximation explicitly. Capacity is
linear between `TC_upper * width_upper` and `TC_lower * width_lower`.

The existing physical deposition law gives `G' = lambda*(T-G) + S`.
Let D=lambda*(T-G), C=T'-S and z be distance from the entering boundary:

```text
D(z) = C + (D0-C)*exp(-lambda*z)
G(z) = G0 + S*z + D0*z*exprel(-lambda*z)
       + C*z*(1-exprel(-lambda*z))
D0 = lambda*(T0-G0)
```

Evaluate the small exponential differences stably from the actual entering load;
do not recover load by dividing a rounded deposition rate by tiny lambda.
At lambda=0 the source-advection limit is G0+S*z. Track the capacity gap separately
from deposition-rate signs so zero-settling capacity crossings remain visible.
For initially overloaded flow and C>0, the deposition-end distance is
`log1p(lambda*(G0-T0)/C)/lambda`, continuously extended to `(G0-T0)/C` at zero.

The correction is limited to zero-lateral-hydraulic-flow deposition.
Positive-lateral-flow equations remain separate. CASE12 endpoint loads, rates
and deposition-end transitions and CASE34 deposition beginning at XDBEG must be
consistent. Preserve the existing detachment-capacity machinery; mixed-class
under-capacity states must not gain unbounded bed detachment from extending a
deposition equation outside its domain. The U9a implementation retains passive transport for under-capacity classes
while the cohort deposits, source-driven interior onset, and the existing XDEMAX
and DETACH/DCAP handoff. Exact filled-capacity equilibrium remains saturated;
this phase convention is documented rather than claimed as legacy parity.

## Numerical boundary preservation (U9a)

Native strong-decay controls (0fa5c4271) expose cancellation in the initial
incremental load evaluation. Actual CASE12 controls (e3956de4c) also prove that
single-precision DTCDX reconstructs negative capacity from a nonnegative upper
capacity and exact zero lower endpoint. Both reproductions precede repair.

Carry actual upper/lower capacities into CHNCST and CHNC12 and derive phase
slopes internally in double precision. With E=exp(-z), R=exprel(-z), evaluate

`G = G0*E + T0*(R-E) + Tend*(1-R) + S*distance*R`.

All weights are nonnegative on the valid domain. Compute both small differences
from the same series; no clipping or new physical cutoff is introduced. Interpolate
root/onset capacity as a convex combination of the actual endpoints. Zero-distance
identity and zero-settling source advection remain explicit. The helper's fourth
argument is the actual lower capacity, not a rounded capacity gradient.

Independent scoped validation passes 155 tests of source accounting, mixed
phases, high-precision equations, strong decay, endpoint rounding and positive-
lateral-flow nonactivation. Separate retained probes cover guarded hydraulics
and the complete native consumer chain. Final broad native and watershed acceptance remains separate.

## Alternatives, validation and rollback

Reject output clipping, a source-only additive patch that preserves the failed
no-source limit, or a generic virtual-geometry rewrite. Require native guard
nonactivation and limiting controls, independent constant-Q references with
zero/tiny settling and linear capacity, roots inside/outside a segment, source
mixtures and mixed-class detachment transitions. Producer-only mass closure and
bed exchange defined as a residual cannot prove physical correctness.

Retain isolated U7 and U8 evidence, then execute the final combined native,
Roads, Disturbed, watchlist and matched Cedar studies. Preserve U6 source and
the installed release as comparators. Revert a disproved experimental formulation;
never tune Roads coefficients to conceal a native source or support defect.

## Revision 2 acceptance

The final matched source `ba9f2ad91b5165d5cd2954bd64b5df608798541e` is
scientifically accepted for the bounded repairs above and vendored under the
owner-authorized undeployed `wepp_261029` identity, artifact revision 2.
Validation includes 1,059 native tests, 840 Roads physical cases, 99 Disturbed
tests, 18 watchlist cases and fresh matched Cedar outputs. The full 24-year
channel audit has zero negative/nonfinite class transfers, with all nine
standard outputs unchanged by observation. Operational release evidence and
the preserved original identities are in the
[reissue package](../work-packages/20261030_wepp_261029_rerelease/package.md).

Cedar outlet sediment is 517,815.77 kg, about 187.456% above the original
release, principally from recovered channel transport. This is not field
calibration or complete physical budget closure. Regenerate all contributing
hillslope, PASS and watershed outputs with the exact matched pair. Roads
magnitude acceptance remains unmet (719/766 meaningful-reference and 30/74
small-reference cases); defaults and the human UI specification/layout gate
remain unchanged. Earlier experimental dispositions above are retained as
history and do not authorize the rejected C3 formulation.
