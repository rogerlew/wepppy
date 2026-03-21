# RUSLE POLARIS K Implementation + NRCS Benchmark Harness

**Status**: Closed (2026-03-21)

## Overview
This package scopes Milestone 4 from `wepppy/nodb/mods/rusle/specification.md`: complete `K` implementation for `polaris_nomograph` and `polaris_epic`, plus a benchmark/reference path against NRCS gridded `K` fields. It also defines the test harness and acceptance checks needed so the resulting `K` surfaces are auditable before full end-to-end `Rusle` controller integration.

## Objectives
- Implement `polaris_nomograph` and `polaris_epic` `K` generation on the run DEM grid using the existing POLARIS NoDb acquisition pipeline.
- Add a reference harness for point-location extraction using one or more of: `gnatsgo_kffact`, `gnatsgo_kwfact`, `gssurgo_kffact`, `gssurgo_kwfact`.
- Add a sanity comparison step that reports `polaris_nomograph` and `polaris_epic` against reference/benchmark values at shared points.
- Produce run-scoped `K` artifacts and metadata with explicit provenance and approximation disclosures.
- Complete a dedicated correctness review pass and a dedicated QA-review pass before package closure.

## Scope

### Included
- `K` factor computation implementation for `polaris_nomograph` and `polaris_epic`.
- Reference harness implementation for NRCS benchmark point extraction.
- Comparison/report utilities for POLARIS vs reference values.
- Targeted regression tests and fixture inputs for `K` modes and harness behavior.
- Package docs, ExecPlan, tracker updates, and review/QA artifacts.

### Explicitly Out of Scope
- Full `Rusle` controller completion for `C`, `P`, masking, and `A` composition.
- UI exposure of `k_mode` switches in end-user workflows.
- New external dependencies beyond currently approved stack components.
- Regulatory or calibration claims beyond detachment-potential benchmarking.

## Implemented `wepppy/nodb/mods/rusle/` File Structure

```text
wepppy/nodb/mods/rusle/
├── __init__.py
├── ls_integration.py
├── specification.md
├── k_integration.py                    # mode dispatch + raster orchestration
├── k_nomograph.py                      # POLARIS nomograph-facing estimator
├── k_epic.py                           # POLARIS EPIC estimator
├── k_reference.py                      # gnatsgo/gssurgo point benchmark harness
├── k_compare.py                        # sanity comparison summaries/threshold checks
├── k_manifest.py                       # metadata/provenance payload helpers
├── data/
│   ├── k_structure_class_lookup.csv    # modeled structure class mapping (if approved)
│   ├── k_permeability_class_lookup.csv # modeled permeability class mapping (if approved)
│   └── k_reference_points_template.csv # lat/lon + benchmark expectations template
└── docs/
    └── README.md
```

Test and artifact companion paths expected in this package:

```text
tests/nodb/mods/
├── test_rusle_k_nomograph.py
├── test_rusle_k_epic.py
├── test_rusle_k_reference_harness.py
├── test_rusle_k_compare.py
└── test_rusle_k_integration.py

docs/work-packages/20260321_rusle_k_polaris_implementation/artifacts/
├── milestone4_review.md
├── milestone5_qa_review.md
└── k_benchmark_comparison_summary.md
```

## Stakeholders
- **Primary**: RUSLE NoDb maintainers and erosion-model integration maintainers.
- **Reviewers**: NoDb controller maintainers; soil/raster maintainers.
- **QA Reviewers**: test and quality maintainers for regression and fixture hygiene.
- **Informed**: downstream users of RUSLE map products and run-manifest consumers.

## Success Criteria
- [x] `polaris_nomograph` `K` mode implemented with explicit approximation metadata and passing targeted tests.
- [x] `polaris_epic` `K` mode implemented and passing targeted tests.
- [x] NRCS reference harness supports at least one configured benchmark source (`gnatsgo_*` or `gssurgo_*`) with deterministic point extraction outputs.
- [x] Sanity comparison report produced for `polaris_nomograph` and `polaris_epic` vs selected benchmark fields.
- [x] Review pass completed with all high/medium findings resolved.
- [x] QA-review pass completed with all high/medium findings resolved.
- [x] `wctl run-pytest tests --maxfail=1` passes before closeout.

## Dependencies

### Prerequisites
- Completed LS package: `docs/work-packages/20260320_rusle_ls_factor_wbt/`.
- Completed static-`R` package: `docs/work-packages/20260320_rusle_r_static_hyetograph_api/`.
- Baseline design document: `wepppy/nodb/mods/rusle/specification.md`.
- Existing POLARIS NoDb acquisition support: `wepppy/nodb/mods/polaris/polaris.py`.

### Blocks
- Full `Rusle` NoDb controller integration for `A = R * K * LS * C * P`.
- Downstream RUSLE benchmark/validation packages that depend on finalized `K` outputs.

## Related Packages
- **Depends on**: [20260320_rusle_ls_factor_wbt](../20260320_rusle_ls_factor_wbt/package.md)
- **Depends on**: [20260320_rusle_r_static_hyetograph_api](../20260320_rusle_r_static_hyetograph_api/package.md)
- **Related**: [20260313_polaris_nodb_runs_client](../20260313_polaris_nodb_runs_client/package.md)
- **Follow-up**: full RUSLE controller integration package (Milestones 5-7 in the spec)

## Timeline Estimate
- **Expected duration**: 1-2 weeks (implementation + benchmark harness + review/QA)
- **Complexity**: High
- **Risk level**: High (equation semantics, reference-data alignment, raster comparison tolerances)

## Milestone 0 Decision Resolution (Locked 2026-03-21)
- `polaris_nomograph` uses modeled structure/permeability classes:
  - structure from texture proxy (`clay`/`sand`) as classes `1-4`
  - permeability from `ksat_cm_hr` proxy as classes `1-6`
- Near-surface support is fixed to `0_5` and `5_15` with thickness weights `5 cm` and `10 cm`.
- `polaris_epic` organic conversion is fixed to `OC = OM / 1.724`, with OM clamp `[0, 20]%`.
- Benchmark precedence is fixed to:
  1. `gssurgo_kffact`
  2. `gnatsgo_kffact`
  3. `gssurgo_kwfact`
  4. `gnatsgo_kwfact`
- Sanity-comparison thresholds are fixed to `abs_error_warn = 0.10`, `rel_error_warn = 0.35` by default.
- Optional `cfvo` adjustment is deferred and not part of this package scope.

## References
- `wepppy/nodb/mods/rusle/specification.md` - canonical RUSLE design and K-mode intent.
- `wepppy/nodb/mods/polaris/polaris.py` - run-scoped POLARIS acquisition/alignment contract.
- `docs/work-packages/20260320_rusle_ls_factor_wbt/package.md` - LS completion context.
- `docs/work-packages/20260320_rusle_r_static_hyetograph_api/package.md` - static `R` completion context.

## Deliverables
- Closed work-package scaffold (`package.md`, `tracker.md`, completed ExecPlan).
- Implemented `K` modules and tests for `polaris_nomograph`/`polaris_epic`.
- Reference harness for at least one NRCS benchmark mode plus comparison summary artifact.
- Review + QA-review artifacts with resolved findings.

## Follow-up Work
- Integrate completed `K` modes into full `Rusle` controller and run artifact contract.
- Expand benchmark coverage to additional landscapes/soil regimes after initial closure.
- Add optional `cfvo` path if deferred from this package.

## Closeout Notes (2026-03-21)
- Implemented:
  - `wepppy/nodb/mods/rusle/k_nomograph.py`
  - `wepppy/nodb/mods/rusle/k_epic.py`
  - `wepppy/nodb/mods/rusle/k_reference.py`
  - `wepppy/nodb/mods/rusle/k_compare.py`
  - `wepppy/nodb/mods/rusle/k_manifest.py`
  - `wepppy/nodb/mods/rusle/k_integration.py`
- Added tests:
  - `tests/nodb/mods/test_rusle_k_nomograph.py`
  - `tests/nodb/mods/test_rusle_k_epic.py`
  - `tests/nodb/mods/test_rusle_k_reference_harness.py`
  - `tests/nodb/mods/test_rusle_k_compare.py`
  - `tests/nodb/mods/test_rusle_k_integration.py`
- Validation:
  - Targeted K suite passed (`16 passed`).
  - Full suite passed (`2410 passed, 34 skipped`).
  - Review and QA-review artifacts completed in `artifacts/`.
