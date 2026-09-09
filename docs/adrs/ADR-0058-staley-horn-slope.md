# ADR-0058: Horn surface slope for Staley M1

## Status and provenance

Accepted algorithm and uncertainty-preserving intersection support; implementation
pending. Venue: user/Codex repository
conversation, recorded 2026-09-09 UTC. Participants: repository owner and Codex.
Decision owner: user, explicitly stating “adopt horn”, then accepting
“preserving uncertainty should be fine”. Implementer: Codex for
this documentation; Rust implementation has not started.

## Decision and rationale

Select planar Horn 3×3 surface slope for the Staley M1 ≥23° intersection.
The earlier candidate is now the selected algorithm. Preserve existing D8
FVSlope and generic WBT Slope behavior. Horn measures a neighborhood surface
gradient independently of the routed receiver direction, with an explicit
stencil that can be verified against analytical surfaces and independent tools.

Raw DEM is still the recommended source. This algorithm decision does not
approve DEM conditioning, missing-neighbor interpolation, new resolution
restrictions, or a production caller. Resolve those
separately in the [canonical contract](../../wepppy/nodb/mods/postfire_debris_flow/docs/slope_sbs.md).

## Accepted uncertainty policy

Preserve true/false/unknown intersection states. For N watershed cells, Y
known true and U unknown, report T bounds Y/N and (Y+U)/N. If U=0, publish
T=Y/N; otherwise publish coverage/bounds with unavailable point T. Processing
may succeed without a model-ready point estimate. Known unburned/low SBS or
known slope below 23° determines false even if the other operand is missing.
Report separate input coverage so logical determination is not confused with
complete source observation.

The owner accepted this policy after an example with 300 true, 600 false and
100 unknown cells: T lies in [0.30, 0.40]. Reject zero filling or extrapolating
300/900 as the watershed predictor, since missing areas may differ systematically.
Bounds describe unknown data, not statistical confidence. Propagation into
probability bounds is outside this decision; a single M1 probability requires
a determined T. Raw DEM and neighborhood edge policies remain separate.

## Alternatives and evidence

FVSlope is routed drop/distance; WBT's projected generic Slope uses Florinsky
5×5. Neither is selected for this predictor. The inspected Staley manuscript
specifies terrain resolution and the threshold but does not establish the
original differentiation stencil. This is an owner-approved engineering choice,
not a claim of calibration preprocessing equivalence. See the
[source findings](../work-packages/20260908_staley_slope_sbs/artifacts/slope_method_findings.md).
No GPL implementation or tests are copied or translated.

## Risks, verification and rollback

Cells near 23° can change classification with method, conditioning or resolution.
The planned analytical and three-site comparisons must measure those effects;
algorithm approval does not waive them. Comparison results support limitations
and future decisions, not predictive validation. No production state changes
exist to roll back. Any later algorithm change requires a documented contract
and parameterization revision rather than switching an existing tool default.
