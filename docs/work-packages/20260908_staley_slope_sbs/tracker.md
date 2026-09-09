# Staley slope/SBS tracker

Status: scaffolded, not executing; 2026-09-09 05:08 UTC.
WEPPpy starting revision: `49c50ecba`. Record WBT revision on execution.

- [x] Inspect manuscript, WBT FVSlope/Slope, existing watershed audit and SBS owner.
- [x] Scaffold bounded Rust implementation/evaluation package and canonical proposal.
- [x] Owner adopted Horn 3×3; recorded ADR-0058.
- [x] Owner accepted uncertainty preservation; bounds with unavailable point T
  when any intersection cell remains unresolved (ADR-0058).
- [ ] Resolve DEM source and neighborhood edges.
- [ ] Specify CLI/output types/class map/units/edges and publication behavior.
- [ ] Implement Rust tool(s), both bindings, analytical and boundary tests.
- [ ] Run three-site sensitivity and rebuilt-binary generated-output checks.
- [ ] Correctness/security reviews, validation, documentation and closeout.

## Decisions and discoveries

User requested owned WBT slope/SBS tooling and a determination of the appropriate
slope algorithm. Whole project watershed/outlet remains accepted scope.
FVSlope is D8-direction drop/distance; projected WBT Slope uses Florinsky 5×5.
The inspected manuscript states 10 m terrain and ≥23° but does not identify a
stencil. Owner subsequently adopted Horn 3×3 (2026-09-09 UTC, ADR-0058).
Owner accepted uncertainty-preserving support: unresolved cells retain bounds
and no point T. Raw DEM and neighborhood edges remain proposed. This is an
engineering choice, not proof of original calibration preprocessing.

## Next steps and evidence

[Findings/decision register](artifacts/slope_method_findings.md) separates
confirmed evidence, engineering recommendations and owner choices. Source and
comparison work can proceed when execution is requested; dependent scientific
policy requires resolution before publication as an accepted contract.
No tests, generated slope artifacts, implementation or deployment claimed yet.

## Historical evidence update — 2026-09-09 UTC

Verified historical ArcGIS planar M1 path and September 2023 pysheds migration.
[Durable evidence](../../../wepppy/nodb/mods/postfire_debris_flow/docs/historical_slope_evidence.md)
records exact revisions/lines and confidence. Horn now has legacy workflow
support; original calibration equivalence remains unconfirmed. Current pfdf
D8 slope is a suspected preprocessing regression; measure its effect without
requiring parity. Separate historical zero-filling from accepted uncertainty.
