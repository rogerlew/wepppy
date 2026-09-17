# Preserve Daymet acquisition artifacts

## Purpose / Big Picture

Retain original Daymet precipitation, temperature and radiation for reliable auditing while publishing the same generated climate.

## Progress

- [x] (2026-09-17 UTC) Confirm overwrite and operator intent; prepare contract delta.
- [x] Obtain independent contract reviews and commit ancestor aa4fbc502.
- [x] Isolate PRN conversion and remove source overwrites in both Daymet helpers.
- [x] Verify physical units, source immutability and generated artifacts with tests and real CLIGEN.
- [x] (2026-09-17 UTC) Record review, validation and closure.

## Surprises & Discoveries

ADR-0006 currently requires provenance columns in the source parquet. Amend that placement requirement while retaining the existing CSV and physical normalization rule.

## Decision Log

2026-09-17 UTC: follow the user's explicit source-read-only instruction. Use caller copy for PRN conversion to avoid changing unrelated df_to_prn callers. Preserve existing historical files; do not infer or rewrite their units.

## Outcomes & Retrospective

Source preservation now passes; 42 focused tests and real CLIGEN replay verify unchanged PRN/CLI bytes. Archive/restore and live existing-artifact browse/download checks pass. Full-suite check passes: 8,983 passed, 99 skipped, 3,155 warnings. No runtime identity, permission, job-wiring, or parameterization changes.

## Context and Orientation

wepppy/nodb/core/climate_build_helpers.py writes single-location source parquet before and after PRN conversion; df_to_prn mutates its DataFrame. The interpolated helper also rewrites source after radiation normalization. Tests in tests/nodb/test_climate_build_helpers.py currently expect these radiation rewrites. docs/adrs/ADR-0006-observed-daymet-radiation-toa-normalization.md governs normalization. docs/schemas/climate-parquet-lineage-contract.md will specify acquisition artifact ownership separately from wepp_cli.parquet.

## Plan of Work

Amend contracts and checkpoint first. Pass a copy to single-location df_to_prn and remove final source writes from both builders. Keep radiation helper's working DataFrame behavior and CSV unchanged. Update tests to verify source data/bytes, PRN conversions and generated CLI radiation together. Add failed-build and legacy-source preservation coverage as needed.

## Concrete Steps

From /home/workdir/wepppy, run wctl run-pytest tests/nodb/test_climate_build_helpers.py, then relevant climate suites and wctl run-pytest tests --maxfail=1. Retain logs under this package's artifacts. Exercise the single-location builder with retained publisher data and the real CLIGEN binary in an isolated artifact directory; inspect generated PRN and CLI and source hashes. Use wctl doc-lint for changed docs.

## Validation and Acceptance

Source parquet equals acquired physical-unit data; PRN retains documented converted units; CLI values remain consistent with rounding and radiation bounds. Interpolated source bytes must be unchanged even when normalized radiation differs. Failed downstream processing must not overwrite source. No live assessment is modified.

## Idempotence and Recovery

All acceptance builds use isolated output directories. Do not repair legacy live data automatically. Reverse the bounded code change to roll back, preserving evidence; do not delete failed artifacts.

## Artifacts and Notes

Retain contract decisions/reviews, focused/full test logs and real build comparison evidence. Update tracker on closure.

## Interfaces and Dependencies

Existing pandas, ClimateFile, CLIGEN and radiation CSV; no dependency or public signature changes.

Revision 2026-09-17 UTC: implementation and focused/runtime verification complete; broad sanity and final closeout subsequently completed with all gates passing.

Final revision 2026-09-17 UTC: package closed; all acceptance evidence retained. Existing historical artifacts remain unchanged.
