# M1 predictor integration tracker

Status: scaffolded, not executing; 2026-09-09 15:06 UTC.
WEPPpy baseline `2c4d1a94f`; WBT baseline `a97abb7` (verify on execution).

- [x] Review completed slope/SBS and scalar engine contracts; inspect RUSLE K precedent.
- [x] Scaffold package and canonical proposal; register open K decisions.
- [ ] Verify K units/scale and settle K coverage/dependency contract with ADR.
- [ ] Inventory read-only project sources and document compatibility/schema plan.
- [ ] Implement lossless prepared inputs, WBT invocation and T/F/S composition.
- [ ] Demonstrate generated artifacts and scalar scenarios; focused/full tests.
- [ ] Independent correctness/security reviews and synchronized closeout docs.

## Decisions and discoveries

2026-09-09 15:06 UTC: next scope is local M1 predictor composition. Existing
project domain, Horn/raw DEM/strict neighbors, uncertainty-preserving T and
observed-support dNBR F are accepted. K units must be verified; K partial support
and artifact-only versus full-RUSLE readiness remain unresolved.

WBT requires explicit finite NoData, SampleFormat, classic uncompressed scalar
GeoTIFFs without palette/tiles; native project rasters may not satisfy these.
This is a preparation contract, not permission to discard source masks or
reinterpret palette colors. WBT fingerprints are FNV diagnostics; composition
must retain SHA-256 provenance and source-stability checks independently.

## Next handoff

Start the [active plan](prompts/active/m1_predictors_execplan.md) only when
execution is requested. Decisions are listed in the
[register](artifacts/decision_register.md). No runtime edits, tests or generated
M1 bundles exist for this scaffold. Do not amend completed predecessor packages.
