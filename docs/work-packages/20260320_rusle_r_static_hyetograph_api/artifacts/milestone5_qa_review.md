# Milestone 5 QA Review

## Scope
QA review covered migration behavior, regression tests, and validation gates for:

- `wepppy/climates/cligen/cligen.py`
- `wepppy/nodb/core/climate_artifact_export_service.py`
- `wepppy/wepp/interchange/_utils.py`
- `wepppy/wepp/reports/return_periods.py`
- `tests/climate/test_cligen_peak_intensity_contract.py`
- `tests/nodb/test_climate_artifact_export_service.py`
- `tests/wepp/interchange/test_utils_phase7.py`

Review date: 2026-03-21
QA reviewer: Codex

## Findings

### High
- None in changed-scope functionality.

### Medium
- None in changed-scope functionality.

### Low
- None.

## Coverage Assessment
- Added coverage verifies:
  - breakpoint dataframe contract (`dur`, nullable `tp/ip`, real `peak_intensity_*` values)
  - deterministic breakpoint numeric windows for a fixed simple fixture (`peak_intensity_10/15/30/60`)
  - non-breakpoint repeated-call stability for peak-intensity helper usage
  - static-`R` API schema plus aggregation invariants (sorted annual rows and mean consistency)
  - climate artifact/interchange/report parquet generation includes canonical peak-intensity columns including `peak_intensity_60`
  - canonical-versus-legacy coalescing precedence and nullable `dur/tp/ip` backfill in parquet export
- Rust-side unit tests verify:
  - non-breakpoint peak intensity computation
  - breakpoint interval/intensity semantics
  - static-`R` annual aggregation behavior

## Recommended Follow-ups (Non-blocking)
1. Add one long-run fixture parity test set (multiple real CLI files) to broaden numerical confidence beyond bounded regression fixtures.
