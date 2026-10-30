# ADR-0116: Anchor channel lateral sediment to its assigned source mass

- Status: Proposed; isolated U7 native ablation, no release or default change.
- Date: 2026-10-30.
- Decision venue: WEPPcloud Roads development conversation, America/Los_Angeles.
- Participants: project owner and Codex, with independent scientific and implementation reviewers.
- Decision owner: project owner, authorizing defect investigation and remediation.
- Implementer: Codex.

## Context

Independent watershed tracing during ADR-0114/0115 validation reproduces all nine
released and candidate output files exactly. On Cedar Creek 1985-11-06, one
channel's lateral hill supplies about 1.845 kg, but CHNRT injects about 136,060 kg.
The source-prefix reproduction and ten controls were committed in the native
repository as `b0f33584f` before repair.

CHNRT multiplies a lateral sediment concentration by an effective hydraulic flow.
Its concentration weights use actual lateral water volume, while the hydraulic
flow can represent a different volume. CHNERO's existing large-top-flow guard
makes this extreme: it truncates virtual top length to zero, which CHNRT
interprets as all-lateral flow. Clean channel water can amplify the source even
without that guard; negative effective lateral volume can suppress a real source.
This is a legacy shared channel defect, not a Roads sediment coefficient issue.

## Proposed decision and isolated scope

In U7, compute each class's actual lateral input mass as the sum of
`tmpvol(element) * sedcon(class, element)` for the four assigned left/right
hillslope and impoundment slots. For a valid routed event, distribute that mass
uniformly over the actual computational span `x(nptsc)-x(1)` and `rundur`.
This makes integration by the existing segment DX values recover the assigned
source, independent of peak, effective hydraulic length, or clean-water dilution.

Retain the existing lateral conversion constants `35.31984 * 0.06241818`.
Their SI roundtrip with `0.453592` is approximately 0.99998898248, so validation
must state the small existing unit-rounding discrepancy rather than claim exact
SI identity. The separate top-load factor 2.2064 has a different discrepancy;
changing it is outside this isolated lane.

Preserve positive `rvolat` eligibility. Zero duration or nonpositive computational
span returns no flux and avoids division; such positive-source inputs are invalid
routing domains, not successful conservation cases. Normalize against the actual
integrated span rather than nominal length because large virtual coordinates
round in single precision.

U7 does not modify water routing, channel hydraulics, the 1e5 guard, sediment
transport/deposition formulas, soil properties, erosion parameters or output
formats. The guard's incorrect all-top hydraulic limit is a separate confirmed
investigation and cannot be declared repaired by mass normalization.

## Alternatives and rationale

Clipping final sediment or fitting a coefficient would conceal created source
mass. Replacing hydraulic geometry at the same time would prevent attribution.
Scaling by nominal physical length misses computational-coordinate rounding.
Independent source summation also avoids cross-weighting a hill and impoundment
when both occupy a side; the input parser does not prohibit that combination.

## Validation and risks

Require actual-source controls across both sides of the guard, ordinary support
mismatch, each contributing slot, mixtures, zero source, negative effective
hydraulic lateral volume, and defensive invalid domains. A newly reachable
positive sediment source with zero effective lateral hydraulic flow also requires
full consumer assessment: CASE12/CASE34 contain no-lateral-water assumptions.
A producer-only conservation result cannot establish complete routing correctness.

After bounded controls, retain isolated Cedar results and paired broader native,
Roads, Disturbed and watchlist evidence for the final selected repair. Keep U6
source `97b2b1e3e` and installed `wepp_261029` as immutable comparators. No withheld
Roads materials, parameter retuning, release promotion or UI implementation is
implied. Roll back an invalid experimental lane; retain its evidence.

## Evidence

Native work package:
`/workdir/wepp-forest-release-20261009/docs/work-packages/20261030-roads-native-accounting/`.
See `artifacts/U6-Cedar-channel-independent-scientific-review.md`,
`artifacts/U7-independent-channel-lateral-mass-review.md`, and incident reproduction
`review_channel_lateral_mass.py` with `review-channel-lateral-mass-red.json`.
