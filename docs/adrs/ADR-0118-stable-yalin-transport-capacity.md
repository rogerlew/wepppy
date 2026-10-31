# ADR-0118: Stable Yalin transport capacity near critical shear

- Status: Accepted for the shared Yalin-factor precision repair in 261029 artifact revision 2.
- Date: 2026-10-30.
- Decision venue: owner-authorized Roads native accounting ablation and undeployed261029 reissue.
- Participants: project owner, implementing Codex agent and independent scientific/implementation agents.
- Decision owner: project owner; independent scientific acceptance recorded.
- Implementer: Codex.

## Context

The full-period Cedar channel audit finds77 tiny negative intermediate particle
loads in experimental U9a, versus80 in U6. Those loads are separate from the
large outlet sediment increase, which paired channel traces attribute to
recovered transport through the repaired all-top guard. Matched observation classifies all77:34 first-negative productions originate
in negative TRNCAP capacity from positive sigma, followed by positive-QLAT
CASE12 (28) or CASE34 (6). The other43 propagate an existing negative load
(42 prior-segment transfers and one connected channel inlet). All nine standard
outputs and all77 violation lines match the unaltered experimental candidate.

Independent actual-source controls establish a shared mathematical defect in
TRNCAP (channels) and YALIN (hillslopes). Both use the factor
`f(sigma) = 1 - log(1 + sigma) / sigma`, which must be positive for positive
sigma. Single-precision addition and subtraction near zero can instead produce
a negative factor. Native fixture-first commit`a8780759b` retains1,152
O0/O2 records with actual SHIELD and released portable math, complete rounded
inputs and90-digit references; no constitutive routine is stubbed.

Example channel capacity is−1.81731507013e−12 against a positive reference
2.20977892336e−18. The hillslope sibling returns−2.91266559482e−11 against
+3.55233435855e−16. This is numerical cancellation, not evidence for changing
critical shear, erodibility, particle fractions or empirical Yalin coefficients.

## Decision

Share REAL function YALINF between the two callers, alongside their existing
SHIELD dependency. Evaluate the same factor with double intermediates:

```text
f(sigma) = sigma/2 - sigma^2/3 + sigma^3/4 - ...
```

Use12 terms when abs(sigma)<0.01, the exact zero limit when sigma=0, and
`1 - log(1 + sigma) / sigma` in double precision otherwise. Convert once to the
native REAL factor. At the series boundary the omitted term is below1e−27;
the switch controls arithmetic accuracy, not physical parameterization.
The valid physical callers supply nonnegative sigma. No load/capacity floor or
negative-value clipping is introduced.

Change only this factor in TRNCAP and YALIN. Preserve their native excess-shear
calculation, Shields function, empirical coefficients, unit systems, particle
weighting, channel allocation/iteration and existing QS floor, and hillslope
sand correction. Appending the helper to SHIELD keeps the existing link graph
and avoids duplicate numerical implementations or a new dependency.

## Alternatives rejected

- Clipping negative capacity conceals the wrong positive value and cannot satisfy
  the high-precision reference near threshold.
- Repairing only channels leaves the identical demonstrated hillslope defect.
- Changing critical shear or fitted sediment parameters changes the scientific
  model to compensate for an arithmetic error.
- Treating unchanged negative locations as a passing positivity audit would
  silently weaken the release criterion.

## Validation and consequences

Require independent native O0/O2 producer controls and high-precision checks of
zero, tiny, threshold-adjacent and large sigma; class allocation and weighting
must retain their intended behavior. Keep original red scripts/receipts unchanged.
The retained `review-U9a-Cedar-negative-causality.json` closes first-producer
classification; require fresh U10 full-period sign checks to establish repair.

This shared repair can alter hillslope erosion as well as channel transport.
Previous channel-only exact parity and magnitude scores cannot be carried into
U10 without rerunning the frozen840-case Roads panel, Disturbed, native suite,
watchlist and fresh matched Cedar study. No field-calibration claim follows from
more accurate evaluation of the equation. The authorized261029 revision2 pair
and report must identify the actual final source, toolchain, results and limits.

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
