# Staley slope/SBS tracker

Status: scaffolded, not executing; 2026-09-09 05:08 UTC.
WEPPpy starting revision: `49c50ecba`. Record WBT revision on execution.

- [x] Inspect manuscript, WBT FVSlope/Slope, existing watershed audit and SBS owner.
- [x] Scaffold bounded Rust implementation/evaluation package and canonical proposal.
- [ ] Resolve slope/source and missing-support policies; write parameterization ADR.
- [ ] Specify CLI/output types/class map/units/edges and publication behavior.
- [ ] Implement Rust tool(s), both bindings, analytical and boundary tests.
- [ ] Run three-site sensitivity and rebuilt-binary generated-output checks.
- [ ] Correctness/security reviews, validation, documentation and closeout.

## Decisions and discoveries

User requested owned WBT slope/SBS tooling and a determination of the appropriate
slope algorithm. Whole project watershed/outlet remains accepted scope.
FVSlope is D8-direction drop/distance; projected WBT Slope uses Florinsky 5×5.
The inspected manuscript states 10 m terrain and ≥23° but does not identify a
stencil. Horn 3×3/raw DEM is a recommendation, not proven original processing.
No algorithm or partial-support policy is silently approved by scaffolding.

## Next steps and evidence

[Findings/decision register](artifacts/slope_method_findings.md) separates
confirmed evidence, engineering recommendations and owner choices. Source and
comparison work can proceed when execution is requested; dependent scientific
policy requires resolution before publication as an accepted contract.
No tests, generated slope artifacts, implementation or deployment claimed yet.
