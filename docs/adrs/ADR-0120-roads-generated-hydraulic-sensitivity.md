# ADR-0120: Bounded generated-road hydraulic sensitivity

Status: Accepted for research execution only; production parameterization unaccepted

Date: 2026-10-31

## Context

After native revision-3 repairs, the generated Roads candidate passes all 840
physical checks but fails the magnitude acceptance gate. Whole legacy-soil
controls recover most misses; switching generated soils to daily mode does not
transfer that success and regresses controls. Initialized hydraulic states show
that the experimental road conductivity cap retains source-soil pore/storage
properties. Neither the shared soil writer nor the 200 mm break is defective
on this evidence.

## Decision

Permit a predeclared, incremental road-only pore/conductivity sensitivity in the
research harness. Require separate component lanes, exact input readbacks,
initialized-state observation, native physical audits and passing controls.
Do not promote these coefficients as physical road defaults or change general
SSURGO/Disturbed behavior. Keep source material, deeper horizons and restrictions.

## Decision Provenance

Decision Venue: user/Codex workspace conversation, 2026-10-31,
America/Los_Angeles; exact message time not retained.

Participants Present: requesting user and Codex.

Decision Owner(s): requesting user authorized autonomous Roads scientific
exploration and the next hydraulic audit. Codex selected this bounded research
contrast under that authority; the user did not specifically approve its
coefficients or any production rule.

Implementer(s): Codex.

## Change Summary

The baseline is the existing generated `erosion_road_cap` research candidate.
Only road horizons ending at or above 200 mm are eligible. Three lanes:

- Pore: `bd0 = min(2, max(0.8, source_bd))`, `phi0 = 1 - bd0/2.65`,
  `bd1 = bd0 + 2.65*0.02`; scale input FC/WP by `(phi0-0.02)/phi0`.
- Conductivity: divide the existing capped road K by 2.4.
- Coupled: apply both treatments.

The native density input clamp precedes the perturbation. Appended VG water-content
scale values follow the pore ratio, VG K follows the conductivity ratio, and VG
shape parameters remain fixed. This revision does not consume the appended VG
arrays downstream; active FC/WP/K columns are changed explicitly. All other soil
lines and non-soil inputs remain identical. No repeated source conditioning.

## Rationale and Alternatives

A primary field study motivates a modest coupled sensitivity, while leaving
transfer limitations explicit. A universal absolute density target would erase
material differences without adequate support. Density-only edits leave the
storage/retention hypothesis unspecified; a global runtime switch already failed
controls. Replacing generated profiles with legacy templates would not meet the
program objective. [Martin et al.](https://doi.org/10.1186/s13595-024-01265-4).

## Consequences and Risk

The empirical context is trafficked forest soil, not a universal constructed-road
model. Uniform treatment through 200 mm and fixed normalized retention shape are
research assumptions. Applying the change to an already capped road is an
incremental sensitivity, not a total-construction parameter estimate. Paved-road
and fill treatment require separate justification. Numerical agreement alone
cannot close these scientific gaps.

## Evidence

- [Source/native audit and physical rationale](../work-packages/20261029_roads_parameterization_program/artifacts/generated-role-hydraulic-audit-r3-findings.md)
- [Frozen experiment declaration](../work-packages/20261029_roads_parameterization_program/artifacts/road-pore-screen-r3-declaration.json)
- [Live program tracker](../work-packages/20261029_roads_parameterization_program/tracker.md)

## Risk and Rollback Notes

No production values change, so no runtime rollback is required. Retain failed
lanes and reject promotion on physical failure or control regression. Do not tune
these coefficients after seeing outcomes. Any future production rule requires an
amended/new ADR, full development and withheld validation, broader runtime and
geometry checks, and independent scientific review. UI specification/layout
approval remains a separate human gate before implementation.

## Execution disposition

The frozen screen completed 348 runs with 348 independently recomputed physical
passes. Pore-only, conductivity-only and coupled lanes recover 1, 24 and 25 of
96 misses respectively, each retaining 20/20 passing controls. Forty-two small-
reference misses remain under the coupled treatment. No standalone production
rule is accepted; retain the conductivity response as a component hypothesis.
See [results and verification](../work-packages/20261029_roads_parameterization_program/artifacts/road-pore-screen-r3-findings.md).
