# Decision register

Status: proposed numerical policies, 2026-09-09 04:18 UTC. This register is an
execution aid, not canonical authority. Record acceptance in the module
specification, detailed engine contract and parameterization ADR before code.

## Resolved scope

One existing project watershed, one existing canonically resolved project
outlet; manually selected suspected burned basin. No nested/channel assessment
or second delineation. ADR-0055 records explicit owner direction.

## Decisions needed for this package

| ID | Recommendation | Rationale and unresolved detail |
| --- | --- | --- |
| N01 | Require explicit model, duration (15/30/60 min), and finite supplied predictors/rainfall. Reject invalid numeric inputs with a documented error; do not turn them into zero probability. | Scientific missing-data availability belongs to the later integration layer. Accept negative finite M1 dNBR; define physical ranges for the other predictors without inventing calibration cutoffs. |
| N02 | Accept nonnegative rainfall, including zero; evaluate the published sigmoid without clamping the rainfall-response coefficient or overriding the intercept. | The empirical equation can return nonzero probability at zero rainfall. Label this mathematical behavior; do not imply rainfall-triggered debris flows occur without rain. A negative response coefficient is possible with negative dNBR and must not be silently repaired. |
| N03 | Define an inverse threshold as a nonnegative solution of p(R) = target, with explicit finite target 0 < p < 1. Return structured unavailable/nonunique reasons for no solution or nonunique solutions; no negative threshold, zero clipping, or JSON infinity. | Distinguish an equality solution from minimum rainfall to reach/exceed a probability. Zero response coefficient with matching target has nonunique solutions; negative coefficient may still have a nonnegative equality solution. State interpretation and tolerance policy explicitly. |
| N04 | Caller supplies target probability; no engine default of 50% or 75%. Use stable float64 calculations and report overflow explicitly. | UI threshold defaults belong to the rainfall/results contract. Determine supported input shapes and finite-arithmetic policy in the detailed contract; use exact zero tests unless a justified tolerance is accepted in the ADR. |

## Evidence and engineering work, not new user choices

Check all six published coefficient rows against the local Staley PDF and
record page/table evidence. Resolve WBT mask labels, grid, resolved outlet cell,
raw versus conditioned elevations, and incomplete-domain diagnostics from
existing owners. Reuse the existing delineation; an inconsistency should be
reported, not silently repaired. These investigations do not require asking
the user to select another basin or approve ordinary artifact-path choices.

## Deferred to successor packages

Slope method and SBS classes/NoData; M1 K unit compatibility and K-only versus
full-RUSLE readiness; M3 material/incomplete-component/fallback policy and
10 m enforcement; climate source/scenario defaults; locale, publication,
freshness, unitized presentation and dashboard contracts remain on the
[roadmap](../../../../wepppy/nodb/mods/postfire_debris_flow/implementation_roadmap.md).
They do not block a pure engine consuming explicit prepared predictors.
