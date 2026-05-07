# RUSLE POLARIS K Conservative Small-Hole Fill

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current while work proceeds.

## Purpose / Big Picture

Add conservative spatially weighted interpolation for small interior POLARIS `NoData` defects so `RUSLE K` rasters avoid spotty coverage while preserving guardrails against broad or edge-connected missing areas.

## Progress

- [x] Implemented conservative IDW small-hole fill stage in `k_integration` before near-surface aggregation.
- [x] Added manifest policy + per-property fill summaries.
- [x] Added regression tests for fill and skip cases.
- [x] Updated RUSLE specification contract.
- [x] Ran full QA gate and finished review/disposition artifacts.
- [x] Closed package and archived ExecPlan.

## Surprises & Discoveries

- POLARIS mask propagation into K was exact; spotty coverage in some runs is from source `NoData`, not K-only masking.
- Some runs with visually spotty K had `NoData=0`; appearance was dominated by valid zero-valued nomograph K.

## Decision Log

- Decision: use inverse-distance weighted fill via `rasterio.fill.fillnodata` for interpolation kernel.
  - Rationale: established geospatial algorithm already available in stack.
- Decision: constrain fill to small interior components and max candidate coverage fraction.
  - Rationale: keep correction conservative and avoid broad extrapolation.

## Outcomes & Retrospective

- Implemented conservative POLARIS gap-fill policy for K inputs:
  - interior components only
  - component size `<=64` pixels
  - candidate coverage guard `<=10%`
  - IDW search distance `6 px`
- Added auditable manifest reporting:
  - `k.gap_fill_policy`
  - `k.gap_fill_summary` (per property + depth)
- Validation results:
  - targeted K integration: `5 passed`
  - targeted RUSLE K/controller slice: `26 passed`
  - broad suite `tests --maxfail=1`: one unrelated baseline failure in
    `tests/nodb/test_base_boundary_characterization.py::test_dump_forces_monotonic_signature_after_second_same_size_rewrite`
  - doc lint: `4 files validated, 0 errors, 0 warnings`

## Validation Plan

1. `wctl run-pytest tests/nodb/mods/test_rusle_k_integration.py --maxfail=1`
2. `wctl run-pytest tests/nodb/mods/test_rusle_k_epic.py tests/nodb/mods/test_rusle_k_nomograph.py tests/nodb/mods/test_rusle_k_compare.py tests/nodb/mods/test_rusle_k_reference_harness.py tests/nodb/mods/test_rusle_k_integration.py tests/nodb/mods/test_rusle_controller.py --maxfail=1`
3. `wctl doc-lint --path wepppy/nodb/mods/rusle/specification.md --path docs/work-packages/20260507_rusle_k_polaris_gap_fill/package.md --path docs/work-packages/20260507_rusle_k_polaris_gap_fill/tracker.md --path docs/work-packages/20260507_rusle_k_polaris_gap_fill/prompts/completed/rusle_k_polaris_gap_fill_execplan.md`
