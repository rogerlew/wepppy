# Milestone 4 Correctness Review

## Scope
Reviewed the migration implementation across:

- `wepppy/climates/cligen/cligen.py`
- `wepppy/nodb/core/climate_artifact_export_service.py`
- `wepppy/wepp/interchange/_utils.py`
- `wepppy/wepp/reports/return_periods.py`
- `tests/climate/test_cligen_peak_intensity_contract.py`
- `tests/nodb/test_climate_artifact_export_service.py`
- `tests/wepp/interchange/test_utils_phase7.py`

Cross-repo API implementation reviewed in:

- `/home/workdir/wepppyo3/cli_revision/src/lib.rs`
- `/home/workdir/wepppyo3/release/linux/py312/wepppyo3/climate/__init__.py`

Review date: 2026-03-21
Reviewer: Codex

## Findings

### High
- None.

### Medium
- None.

### Low
- `wepppy/climates/cligen/cligen.py`: migration fallback boundary originally used broad exception catches; narrowed to explicit boundary catches (`ImportError` for optional import and explicit runtime/value/type/attribute failures for non-breakpoint fallback).
- `/home/workdir/wepppyo3/cli_revision/src/lib.rs`: removed unused `#[macro_use] extern crate pyo3;` import to keep Rust target warning-free for this package.
- A transient reviewer claim of a non-breakpoint native-path segmentation fault was not reproducible; repeated full-suite sanity runs passed after final migration/test hardening.

## Resolution Summary
- All identified correctness-impacting risks in this package scope are resolved.
- Breakpoint intensity sentinel behavior is removed in migrated outputs; breakpoint rows now emit real `peak_intensity_*` values and nullable `tp/ip` with derived `dur`.
- Static-`R` API contract is implemented and callable via `wepppyo3.climate.compute_static_r_from_cli`.

## Residual Risks
- Cross-validation against additional long real-world CLI fixtures (beyond current smoke/regression tests) remains a follow-up hardening opportunity, not a blocker for this package scope.
