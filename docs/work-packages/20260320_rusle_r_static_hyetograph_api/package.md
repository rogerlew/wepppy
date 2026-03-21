# RUSLE Static R + WEPPpyo3 Hyetograph API Migration

**Status**: Closed (2026-03-21)

## Overview
This package delivers the next RUSLE capability after `LS`: a production static-`R` computation from WEPP `.cli` inputs and shared Rust hyetograph helpers in `wepppyo3.climate`. The package also migrates current WEPPpy callsites that depend on Python hyetograph/intensity routines so they use the new public API, including breakpoint-climate parity informed by WEPP internals in `/workdir/wepp-forest`.

## Objectives
- Implement `cligen_static` runtime `R` in `wepppyo3.climate` using segment-based storm energy and `I30` (`EI30`) from WEPP storm shape reconstruction.
- Add reusable Rust hyetograph helper APIs that cover both non-breakpoint (`prcp/dur/tp/ip`) and breakpoint (`nbrkpt` cumulative table) storm representations.
- Define and freeze the preferred public API based on current WEPPpy usage patterns, then migrate existing callsites to that API.
- Add regression coverage for non-breakpoint and breakpoint climates, including parity checks against existing Python behavior where comparable.
- Include explicit correctness review and QA-review passes before closeout.

## Scope

### Included
- `wepppyo3` climate Rust/PyO3 API additions for hyetograph reconstruction, peak-intensity windows, and static-`R` computation.
- Breakpoint-climate rain-intensity parity work based on WEPP source behavior (`stmget.for`, `brkpt.for`, `disag.for`) in `/workdir/wepp-forest`.
- WEPPpy integration/migration for current Python hyetograph/intensity callsites:
  - `wepppy/climates/cligen/cligen.py`
  - `wepppy/nodb/core/climate_artifact_export_service.py`
  - `wepppy/wepp/interchange/_utils.py`
  - `wepppy/wepp/reports/return_periods.py`
- API/docs updates and test updates in both repos.
- Final review pass + QA-review pass with resolved findings.

### Explicitly Out of Scope
- New gridded runtime `R` modes (`mrms_ei30`, `legacy_r_grid`, `prism_atlas_regression`).
- Full `Rusle` controller implementation for all factors (`K/C/P`) beyond work needed to consume static `R` APIs.
- UI redesign for Storm Event Analyzer beyond bounded integration changes required by API migration.
- New external dependencies not already justified by repository standards.

## Stakeholders
- **Primary**: RUSLE NoDb maintainers, climate/erosivity maintainers, and `wepppyo3` maintainers.
- **Reviewers**: cross-repo code reviewers for `wepppy` and `wepppyo3`; WEPP domain reviewer for erosivity conventions.
- **QA Reviewers**: test/quality maintainers validating regression coverage and gate completeness.
- **Informed**: Storm Event Analyzer and return-period report maintainers.

## Success Criteria
- [x] Static `R` API is implemented in `wepppyo3.climate` and returns at minimum mean annual `R` plus per-year annual erosivity totals.
- [x] Shared hyetograph helpers support both non-breakpoint and breakpoint storm representations with tested WEPP parity.
- [x] Preferred public API is documented and callsites are migrated from legacy Python routines to the new API.
- [x] Breakpoint climates no longer rely on sentinel `-1` intensity placeholders in exported climate artifacts.
- [x] Focused tests pass in `wepppyo3` and `wepppy`, plus full WEPPpy sanity gate (`wctl run-pytest tests --maxfail=1`).
- [x] Review pass completed with all high/medium findings resolved.
- [x] QA-review pass completed with test-quality findings resolved and verification evidence captured.

## Dependencies

### Prerequisites
- Locked RUSLE `LS` package completion: `docs/work-packages/20260320_rusle_ls_factor_wbt/`.
- RUSLE specification baseline: `wepppy/nodb/mods/rusle/specification.md`.
- WEPP parity references in `/workdir/wepp-forest` (`src/stmget.for`, `src/brkpt.for`, `src/disag.for`).
- Canonical `wepppyo3` release path: `/workdir/wepppyo3/release/linux/py312/`.

### Blocks
- End-to-end RUSLE NoDb implementation that consumes production static `R`.
- Any downstream analytics that assume breakpoint climates have fully populated intensity windows.

## Related Packages
- **Depends on**: [20260320_rusle_ls_factor_wbt](../20260320_rusle_ls_factor_wbt/package.md)
- **Related**: [20260313_polaris_nodb_runs_client](../20260313_polaris_nodb_runs_client/package.md)
- **Follow-up**: full RUSLE NoDb factor integration package (to be scoped after static `R` + API migration lands)

## Timeline Estimate
- **Expected duration**: 1-2 weeks (cross-repo implementation + migration + validation)
- **Complexity**: High
- **Risk level**: High (cross-repo API changes, scientific contract choices, breakpoint parity)

## References
- `wepppy/nodb/mods/rusle/specification.md` - locked RUSLE direction and static `R` requirements.
- `/workdir/wepp-forest/src/stmget.for` - non-breakpoint parsing and `ip` correction behavior.
- `/workdir/wepp-forest/src/brkpt.for` - breakpoint intensity derivation from cumulative rainfall/time.
- `/workdir/wepp-forest/src/disag.for` - non-breakpoint disaggregation + 5-minute minimum timestep behavior.
- `wepppy/climates/cligen/cligen.py` - current Python hyetograph and peak-intensity routines.
- `wepppy/nodb/core/climate_artifact_export_service.py` - climate parquet export path currently using Python intensity derivation.
- `wepppy/wepp/interchange/_utils.py` - CLI parquet materialization fallback path.
- `wepppy/wepp/reports/return_periods.py` - return-period staging climate fallback generation.
- `/workdir/wepppyo3/cli_revision/src/lib.rs` - current `wepppyo3.climate` Rust entrypoint.

## Decision Checkpoint (2026-03-20)
- **Resolved Q1 (static-`R` energy/units contract)**: use WEPP/AH537-aligned SI unit energy relation for segment-based storm energy:
  - `e(i_mm_hr) = min(0.119 + 0.0873 * log10(i_mm_hr), 0.283)`, `e = 0` for `i <= 0`
  - `E_event = sum(e * delta_v_mm)`; `EI30_event = E_event * I30_event`
  - `R_year = sum(EI30_event)`; run-level `R` is mean annual `R_year`
- **Resolved Q3 (fallback policy)**: allow temporary fallback only where legacy Python behavior already exists; do not add new Python-only fallback paths (explicitly includes no new breakpoint-only Python fallback).
- **Resolved Q2 (public hyetograph API shape)**: expose both low-level segment builders and peak-intensity helpers; canonical WEPPpy callsite surface is peak helpers with canonical keys `peak_intensity_10`, `peak_intensity_15`, `peak_intensity_30`, `peak_intensity_60`.
- **Resolved Q4 (breakpoint artifact compatibility)**: exported climate artifacts must always include `dur`, `tp`, `ip`, `storm_duration_hours`, `storm_duration`, and `peak_intensity_10/15/30/60`; breakpoint rows use real peak intensities, keep `tp/ip` nullable, and derive duration from breakpoint intervals with WEPP-consistent semantics.
- **Resolved Q5 (release scope)**: phase-1 release synchronization is source changes plus canonical `py312` artifacts used by the WEPPpy stack (`/workdir/wepppyo3/release/linux/py312/`) only.

## Deliverables
- Completed ExecPlan with milestone-by-milestone implementation record.
- New/updated `wepppyo3.climate` APIs for hyetograph reconstruction and static `R`.
- WEPPpy migration PR-level changes for current Python hyetograph/intensity callsites.
- Added/updated tests for non-breakpoint and breakpoint parity and static `R` regression.
- Package artifacts capturing review pass, QA-review pass, and final validation summary.

## Closeout Notes (2026-03-21)
- Implemented and validated the `wepppyo3.climate` static-`R` + hyetograph API set and synchronized py312 release artifacts.
- Migrated in-scope WEPPpy climate consumers to canonical API outputs, including breakpoint intensity contract upgrades (`peak_intensity_10/15/30/60`, nullable `tp/ip`, derived `dur`).
- Completed dedicated correctness and QA-review milestones with no unresolved high/medium findings in changed scope.
- Validation artifact: `artifacts/final_validation_summary.md`.

## Follow-up Work
- Integrate static `R` API into the full RUSLE factor pipeline/controller.
- Evaluate optional event-oriented/design-storm erosivity mode as a separate package, if needed.
- Consider Storm Event Analyzer enhancements for richer breakpoint-event visualization if required by product scope.
