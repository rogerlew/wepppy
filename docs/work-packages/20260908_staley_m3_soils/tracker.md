# Tracker — Staley M3 Soils

## Quick Status

**Updated**: 2026-09-09 UTC
**Phase**: Closed — offline implementation and experiment complete
**Security impact**: high; dedicated security and correctness gates pass
**Recommendation**: retain original STATSGO; no automatic SSURGO substitution

## Task Board

- [x] Scope and source inventory recorded; live projects remain read-only.
- [x] M1: Freeze 111 map units, 390 components, 1,506 horizons and THICK windows.
- [x] M2: Verify embedded original SAS; freeze offline contract and ADR-0053.
- [x] M3: Implement/test read-only builder and source-to-M3 propagation.
- [x] M4: Complete 72 comparisons and 924 diagnostic scenarios on 12 outlets.
- [x] M5: Final reproducibility published, durable docs promoted, prompts archived.

## Decisions

- **2026-09-09 02:17 UTC** — User requested the M3 soil work package after
  completing terrain tooling and the 10 m recommendation. Reuse that panel;
  isolate soil-source effects rather than repeat terrain-resolution evaluation.
- **2026-09-09 02:17 UTC** — Keep live soil rebuilds and production UI/NoDb/RQ
  changes outside scope. Deliver executable offline derivation and evidence
  without masking unresolved empirical source substitution.

## Discoveries and Risks

All three live `soils/` directories are absent. Frozen study inputs do not imply
project readiness. All acquired spatial keys resolve to Non-MLRA Soil Survey
Areas, but spatial/table vintages differ. Original SAS excludes WATER and
renormalizes missing component support; it does not explicitly filter bedrock.
Weathered material, repeated profile endpoints, absent component horizons and
unknown within-unit component locations constrain source interpretation.

Strict soil has no support at two Topanga outlets; all catchments are partial
under both evaluated policies. No production SSURGO source or cutoff is approved.
The small panel includes nested catchments and one 22.9858 km2 diagnostic.

## Validation and Handoff

35 focused tests pass. Full suite: 7,766 passed, 72 skipped. Independent
correctness and security reviews pass with no unresolved findings. Same-session
acquisition reproduction is byte-identical for the 12 source data files.
Final command evidence is in [validation](artifacts/validation.md); scientific
outcomes are in [soil_decision](artifacts/soil_decision.md). Canonical authority
is the module's `docs/m3_soil_thickness.md`, not this package history.

Final reproduction: four numerical tables byte-identical and 30 raster arrays
exactly equal; input/code hashes verified. Stubtest, stub hygiene, scoped docs
lint and spelling checks pass. No branch, commit, deployment or live writes.
