# RUSLE LS Full-Extent Routing + Conservative Small-Defect Fallback

**Status**: Closed (2026-05-07)
**Timezone**: UTC

## Overview
This package removes a regression that constrained `RusleLsFactor` routing to the watershed boundary mask and restores LS application to the full map extent. It also hardens `RusleLsFactor` against small hydrologic-correction defects by adding a conservative single-cell-pit fallback path while retaining fail-fast behavior for larger DEM problems.

## Objectives
- Revert watershed-boundary confinement in `wepppy` RUSLE controller wiring so LS routing runs across full DEM/map extent unless an explicit stop mask is provided.
- Add bounded conservative fallback in `RusleLsFactor` for small interior no-flow defects from DInf-derived SCA inputs.
- Preserve strict explicit failure for larger interior no-flow defect patterns.
- Update RUSLE LS contract documentation and work-package artifacts.
- Record QA evidence with targeted tests/build checks across both repositories.

## Scope

### Included
- `wepppy/nodb/mods/rusle/rusle.py` wiring changes removing auto-generated outside-watershed blocking mask.
- `tests/nodb/mods/test_rusle_controller.py` updates for revised LS input behavior.
- `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/terrain_analysis/rusle_ls_factor.rs` fallback/metadata hardening.
- `/workdir/weppcloud-wbt/whitebox_tools.py` and `/workdir/weppcloud-wbt/WBT/whitebox_tools.py` docstring updates.
- `wepppy/nodb/mods/rusle/specification.md` contract updates for full-extent LS and conservative fallback.
- Package tracker/execplan/QA artifacts and root tracker updates.

### Explicitly Out of Scope
- Changes to `R`, `K`, `C`, or `P` scientific equations.
- New user-facing knobs for fallback thresholds in this package.
- Broad hydrologic conditioning pipeline redesign.

## Stakeholders
- **Primary**: WEPPpy/WEPPcloud model operators and RUSLE users.
- **Reviewers**: Rusle/NoDb maintainers.
- **Security Reviewer**: N/A (security impact triage `none`).
- **Informed**: weppcloud-wbt maintainers.

## Success Criteria
- [x] LS routing in `wepppy` no longer auto-creates/passes outside-watershed blocking mask.
- [x] `RusleLsFactor` applies conservative fallback for small interior no-flow defects and still fails fast for larger defects.
- [x] LS metadata explicitly reports no-flow guard/fallback outcome.
- [x] Targeted validation commands pass in both repos and evidence is recorded.
- [x] Spec/work-package documentation reflects the updated contract and rationale.

## Dependencies

### Prerequisites
- Existing `RusleLsFactor` tool integration package: `docs/work-packages/20260320_rusle_ls_factor_wbt/`.

### Blocks
- None.

## Related Packages
- **Depends on**: [20260320_rusle_ls_factor_wbt](../20260320_rusle_ls_factor_wbt/package.md)
- **Related**: [20260321_rusle_c_modes_implementation](../20260321_rusle_c_modes_implementation/package.md)
- **Follow-up**: None currently.

## Timeline Estimate
- **Expected duration**: 1 focused session
- **Complexity**: Medium
- **Risk level**: Medium (scientific-behavior and QA sensitivity)

## Security Impact and Review Gate
- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: Scientific raster-routing behavior and DEM preprocessing robustness only; no auth/secret/path/egress surface changes.
- **Security review artifact**: `N/A`

## Hardening and Callus Softening (Required for incident/remediation packages)
- **Failure signature(s)**:
  - Unwanted LS confinement outside watershed (`ls_blocking_mask_outside_watershed.tif` behavior).
  - Strict failure on small DEM interior no-flow artifacts despite otherwise corrected DEM.
- **Related prior hardening efforts**:
  - `docs/work-packages/20260320_rusle_ls_factor_wbt/`
- **Health signals**:
  - LS runs cover full map extent when no explicit blocking mask is supplied.
  - Small-defect DEMs no longer hard-fail when conservative correction resolves no-flow cells.
- **Danger signals**:
  - Fallback engages on large defects.
  - Silent acceptance when no-flow remains after fallback.
- **Observation window**: immediate + next integration cycle.
- **Temporary calluses introduced**: none.
- **Callus softening hypothesis (if applicable)**: N/A.

## References
- `wepppy/nodb/mods/rusle/rusle.py`
- `wepppy/nodb/mods/rusle/specification.md`
- `tests/nodb/mods/test_rusle_controller.py`
- `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/terrain_analysis/rusle_ls_factor.rs`
- `/workdir/weppcloud-wbt/whitebox_tools.py`
- `/workdir/weppcloud-wbt/WBT/whitebox_tools.py`

## Deliverables
- Updated code and tests in `wepppy`.
- Updated `RusleLsFactor` fallback implementation + metadata + wrapper docs in `weppcloud-wbt`.
- Updated RUSLE LS specification.
- Work-package tracker, execplan, QA review artifact, and root tracker update.

## Follow-up Work
- Consider exposing fallback thresholds as explicit advanced sensitivity controls if operators request tunability.
- Add fixture-driven defect-pattern regression tests in `weppcloud-wbt` for fallback-engaged grids.

## Closure Notes

**Closed**: 2026-05-07

**Summary**: Removed implicit watershed-boundary LS confinement in `wepppy` by deleting auto-generated outside-watershed blocking mask wiring. Added bounded conservative fallback in `RusleLsFactor` for small interior no-flow defects using `BreachSingleCellPits`, with re-validation and continued fail-fast for larger/unresolved defect patterns. Updated wrapper documentation and RUSLE LS specification to reflect the revised contract.

**Validation**: Targeted `wepppy` tests passed (`10 passed`), `weppcloud-wbt` check/test commands passed (`cargo check`, filtered `cargo test` with `7 passed`, wrapper `py_compile`), and docs lint passed (`5 files validated, 0 errors, 0 warnings`). See `artifacts/20260507_qa_review.md`.

**Lessons Learned**: LS extent behavior and DEM-defect behavior are split across `wepppy` orchestration and WBT core; contract docs need to keep both layers synchronized to avoid future assumption drift.
