# RUSLE C Modes Implementation (`observed_rap` + `scenario_sbs`)

**Status**: Closed (2026-03-21)

## Overview
This package scopes Milestone 5 from `wepppy/nodb/mods/rusle/specification.md`: implement the shared RUSLE `C` engine plus both required source modes, `observed_rap` and `scenario_sbs`, with explicit run-scoped artifacts, manifest metadata, targeted regression tests, dedicated correctness review, dedicated QA review, and full package closeout.

The implementation is intentionally bounded to RUSLE `C`. It does not broaden into the full `Rusle` NoDb controller, `P` support, final `A = R * K * LS * C * P` composition, or UI exposure beyond the auditable factor-integration layer needed for later controller work.

## Objectives
- Implement `observed_rap` using the locked v1 simplified `RUSLE2` surface-cover form:
  - `fg = clamp(100 - bare_ground_pct, 0, 100)`
  - `C = exp(-0.04 * fg)`
  - neutral canopy/roughness/biomass/consolidation terms in v1
- Implement `scenario_sbs` as a disturbed-only static lookup path keyed by canonical disturbed family plus `sbs_class`.
- Create the runtime lookup substrate (`wepppy/nodb/mods/rusle/data/rusle_c_lookup.csv`) consistent with the specification tables and non-burnable policy.
- Emit auditable run-scoped artifacts under `wd/rusle/`, including `c.tif`, `manifest.json`, and `scenario_sbs` support artifacts such as DEM-aligned `disturbed_class.tif`.
- Add focused regression coverage for formulas, nodata/masking behavior, RAP band handling, lookup policy, raster alignment, normalization, and catalog/manifest writes.
- Complete dedicated correctness and QA review artifacts before package closure.

## Scope

### Included
- New RUSLE `C` implementation modules under `wepppy/nodb/mods/rusle/`.
- A shared `C` formula helper for `fg` and `C`.
- `observed_rap` raster alignment and formula application.
- `scenario_sbs` lookup loading, canonical disturbed-family normalization, DEM-aligned disturbed-class raster generation, and SBS application.
- Run-scoped manifest/catalog updates for `C` artifacts and mode metadata.
- Targeted unit/integration tests for both modes and their runtime artifacts.
- Work-package docs, active/completed ExecPlan lifecycle, review artifacts, QA artifact, and closeout sync.

### Explicitly Out of Scope
- Full `Rusle` NoDb controller implementation and `A` raster composition.
- New NDVI-based `C` shortcuts or alternate `C` science.
- New `P` support, treatment-practice modeling, or recovery-time-axis behavior.
- Silent fallback behavior for unsupported classes or missing lookup rows.
- Changes to disturbed or RAP science outside what is needed to satisfy the locked `C` contracts.

## Expected `wepppy/nodb/mods/rusle/` File Structure

```text
wepppy/nodb/mods/rusle/
├── __init__.py
├── c_formula.py                    # shared fg + C math
├── c_lookup.py                     # runtime lookup loading and family normalization
├── c_integration.py                # mode dispatch, raster alignment, artifact writes
├── c_manifest.py                   # C-manifest helper
├── k_*.py
├── ls_integration.py
├── specification.md
└── data/
    └── rusle_c_lookup.csv
```

Expected companion tests and package artifacts:

```text
tests/nodb/mods/
├── test_rusle_c_formula.py
├── test_rusle_c_lookup.py
└── test_rusle_c_integration.py

docs/work-packages/20260321_rusle_c_modes_implementation/artifacts/
├── milestone4_review.md
├── milestone5_qa_review.md
└── final_validation_summary.md
```

## Stakeholders
- **Primary**: RUSLE NoDb maintainers and erosion-map maintainers.
- **Reviewers**: NoDb/raster maintainers and disturbed-workflow maintainers.
- **QA Reviewers**: test-harness maintainers and regression/fixture reviewers.
- **Informed**: downstream RUSLE factor consumers and query-engine/catalog users.

## Success Criteria
- [x] `observed_rap` implemented with the exact locked formula contract and targeted tests.
- [x] `scenario_sbs` implemented with static lookup behavior, DEM-aligned `disturbed_class` raster generation, and targeted tests.
- [x] Non-burnable policy enforced exactly as documented in the spec.
- [x] Run-scoped audit artifacts written and cataloged for `C` outputs and mode metadata.
- [x] Dedicated correctness review completed with no unresolved high/medium findings.
- [x] Dedicated QA review completed with no unresolved high/medium findings.
- [x] Full required validation gates pass before closeout.

## Dependencies

### Prerequisites
- Completed LS package: `docs/work-packages/20260320_rusle_ls_factor_wbt/`.
- Completed static-`R` package: `docs/work-packages/20260320_rusle_r_static_hyetograph_api/`.
- Completed `K` package: `docs/work-packages/20260321_rusle_k_polaris_implementation/`.
- Baseline design document: `wepppy/nodb/mods/rusle/specification.md`.
- Existing Disturbed/RAP/landuse contracts:
  - `wepppy/nodb/mods/disturbed/disturbed.py`
  - `wepppy/nodb/mods/rap/rap.py`
  - `wepppy/nodb/core/landuse.py`

### Blocks
- Full RUSLE controller work (Milestones 6-7) depends on this package shipping auditable `C` outputs.

## Related Packages
- **Depends on**: [20260320_rusle_ls_factor_wbt](../20260320_rusle_ls_factor_wbt/package.md)
- **Depends on**: [20260320_rusle_r_static_hyetograph_api](../20260320_rusle_r_static_hyetograph_api/package.md)
- **Depends on**: [20260321_rusle_k_polaris_implementation](../20260321_rusle_k_polaris_implementation/package.md)
- **Follow-up**: full `Rusle` controller integration and validation runs package(s)

## Timeline Estimate
- **Expected duration**: 1-2 focused sessions
- **Complexity**: High
- **Risk level**: High (raster alignment, disturbed-family normalization, explicit failure policy)

## Locked Package Decisions (Milestone 0)
- The implementation surface is a focused `run_rusle_c_factor(...)` integration layer under `wepppy/nodb/mods/rusle/`, not the full `Rusle` controller.
- `observed_rap` consumes a RAP multiband raster and aligns required bands to the DEM grid before computing `fg` and `C`.
- `scenario_sbs` builds a DEM-aligned `rusle/disturbed_class.tif` from a landuse raster plus `wepppy/wepp/management/data/disturbed.json`, then applies a normalized SBS severity raster.
- Unsupported unmasked classes and missing required lookup rows must fail fast with explicit errors; no silent fallbacks.
- Auditable runtime artifacts include manifest metadata and mode-specific support files (`c_fg.tif`, `disturbed_class.tif`, lookup copy, and normalized SBS raster when applicable).

## References
- `wepppy/nodb/mods/rusle/specification.md`
- `wepppy/nodb/mods/disturbed/README.md`
- `wepppy/wepp/management/data/disturbed.json`
- `wepppy/nodb/mods/rap/rap.py`
- `wepppy/nodb/core/landuse.py`

## Deliverables
- Active/closed work-package scaffold and ExecPlan lifecycle.
- New RUSLE `C` modules and lookup substrate.
- Targeted tests for `observed_rap` and `scenario_sbs`.
- Dedicated correctness review artifact, QA-review artifact, and final validation summary.

## Closeout Notes (2026-03-21)
- Implemented:
  - `wepppy/nodb/mods/rusle/c_formula.py`
  - `wepppy/nodb/mods/rusle/c_lookup.py`
  - `wepppy/nodb/mods/rusle/c_manifest.py`
  - `wepppy/nodb/mods/rusle/c_integration.py`
  - `wepppy/nodb/mods/rusle/data/rusle_c_lookup.csv`
- Updated exports:
  - `wepppy/nodb/mods/rusle/__init__.py`
- Added tests:
  - `tests/nodb/mods/test_rusle_c_formula.py`
  - `tests/nodb/mods/test_rusle_c_lookup.py`
  - `tests/nodb/mods/test_rusle_c_integration.py`
- Validation:
  - Targeted `RUSLE C` suite passed (`19 passed`).
  - Broad-exception changed-file enforcement passed.
  - Code-quality observability completed in observe-only mode.
  - Full WEPPpy sanity gate passed (`2429 passed, 34 skipped`).
  - Review, QA, and final validation artifacts completed under `artifacts/`.

## Follow-up Work
- Wire `C` into the future full `Rusle` controller and final `A` composition.
- Extend `scenario_sbs` only through a separate validated recovery-trajectory package if needed.
