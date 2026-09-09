# Staley slope/SBS tracker

Status: completed local backend; 2026-09-09 UTC.
Execution starting revisions: WEPPpy `68f4804e28560ca7da1cb9c55d57d3d3259d3f1d`;
WBT `01381f54c469564abc6776ff97d70b4966340726`. Both were clean.

- [x] Inspect manuscript, WBT FVSlope/Slope, existing watershed audit and SBS owner.
- [x] Scaffold bounded Rust implementation/evaluation package and canonical proposal.
- [x] Owner adopted Horn 3×3; recorded ADR-0058.
- [x] Owner accepted uncertainty preservation; bounds with unavailable point T
  when any intersection cell remains unresolved (ADR-0058).
- [x] Resolve raw DEM source and strict nine-valid-cell edges.
- [x] Freeze StaleySlopeSbs CLI, output schema, explicit class map and fresh-directory publication contract.
- [x] Registered StaleySlopeSbs, both bindings, analytical and boundary tests.
- [x] Six-terrain panel, both real bindings, generated-output/provenance checks.
- [x] Correctness/security reviews closed, all gates and documentation complete.

## Decisions and discoveries

User requested owned WBT slope/SBS tooling and a determination of the appropriate
slope algorithm. Whole project watershed/outlet remains accepted scope.
FVSlope is D8-direction drop/distance; projected WBT Slope uses Florinsky 5×5.
The inspected manuscript states 10 m terrain and ≥23° but does not identify a
stencil. Owner subsequently adopted Horn 3×3 (2026-09-09 UTC, ADR-0058).
Owner accepted uncertainty-preserving support: unresolved cells retain bounds
and no point T. Execution adopts raw DEM and strict nine-valid-cell edges (ADR-0058 execution disposition). This is an
engineering choice, not proof of original calibration preprocessing.

## Completed evidence and successors

[Validation](artifacts/validation.md): 157 Rust tests, 60 analytical CLI/binding
checks, 24 direct security cases, 48 terrain method rows and 432 probability
scenarios. [Terrain report](artifacts/terrain_report.md) and independent
[correctness](artifacts/correctness_review.md)/[security](artifacts/security_review.md)
reviews retain numeric results and limits. All medium/high findings are closed.

Backend implementation is complete locally; no deployment or live installation.
Stage 3 is not complete: production prepared inputs/orchestration, K integration
and normalized dNBR composition remain successors. Source data and routing are
unchanged; synthetic SBS is clearly labeled and is not observed burn evidence.

## Historical evidence update — 2026-09-09 UTC

Verified historical ArcGIS planar M1 path and September 2023 pysheds migration.
[Durable evidence](../../../wepppy/nodb/mods/postfire_debris_flow/docs/historical_slope_evidence.md)
records exact revisions/lines and confidence. Horn now has legacy workflow
support; original calibration equivalence remains unconfirmed. Current pfdf
D8 slope is a suspected preprocessing regression; measure its effect without
requiring parity. Separate historical zero-filling from accepted uncertainty.
