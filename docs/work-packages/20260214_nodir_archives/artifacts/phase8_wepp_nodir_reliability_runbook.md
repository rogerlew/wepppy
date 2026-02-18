# Phase 8 WEPP NoDir Reliability Runbook Delta

Date captured: 2026-02-17 (UTC)

## Purpose

This runbook documents reliability outcomes and operational guidance for the Phase 8 WEPP archive-first read refactor.

## What Changed

Runtime changes:
- Added `wepppy/nodir/wepp_inputs.py` for archive/dir-neutral WEPP input reads, scoped glob/list operations, and explicit file materialization.
- Refactored WEPP prep reads in `wepppy/nodb/core/wepp.py` to consume archived `landuse`, `soils`, and `watershed` inputs without root thaw/freeze.
- Kept file-level materialization only for path-only consumers (`WeppSoilUtil`, management file loader, slope clipping/open cases).

RQ orchestration changes:
- Removed read-only mutation wrappers from:
  - `_prep_slopes_rq`
  - `_prep_multi_ofe_rq`
  - `_prep_managements_rq`
  - `_prep_soils_rq`
  - `_prep_climates_rq`
  - `_run_flowpaths_rq`
  - `_prep_watershed_rq`
  - `_prep_remaining_rq`
- Added `run_wepp_rq` mixed-root preflight recovery: any NoDir root in mixed state (`dir + .nodir`) is frozen back to canonical archive form before stage enqueue.
- Added `_prep_watershed_rq` mixed-root preflight recovery (`roots=("watershed",)`) so standalone watershed-prep jobs apply the same canonicalization path when they bypass `run_wepp_rq`.

## Reliability Outcomes

- Archived-root prep paths no longer rely on `WD/<root>/...` existence for `landuse`, `soils`, and `watershed` reads.
- Read-only prep stages no longer create thaw/freeze transitional windows, including `_prep_remaining_rq`.
- Canonical NoDir errors remain preserved through helper calls (`NODIR_MIXED_STATE`, `NODIR_INVALID_ARCHIVE`, `NODIR_LOCKED`).

Regression evidence:
- `tests/nodir/test_wepp_inputs.py` validates dir + archive reads plus canonical error propagation.
- `tests/nodb/test_wepp_nodir_read_paths.py` validates archive-backed WEPP read paths for channel/hillslope prep without directory-form roots.
- `tests/rq/test_wepp_rq_nodir.py` now asserts read-only stages do not call `mutate_roots(...)` and verifies mixed-root recovery freeze behavior.

## Operational Verification Checklist

- [x] Read-only WEPP prep stages run without NoDir mutation wrappers.
- [x] Archive-backed WEPP prep path tests pass for channel/hillslope reads.
- [x] Canonical NoDir error codes are still surfaced by helper-level tests.
- [x] Stage-overhead perf evidence confirms root lock churn removal.

## Incident Response (Phase 8)

If archived-root prep fails post-rollout:
1. Capture failing stage name and logical path from WEPP logs.
2. Verify archive integrity and entry presence for the referenced root/path.
3. Confirm the stage is using helper-based archive-first read logic (no local wrapper hotfixes).
4. Check for mixed/invalid/transitioning root state and handle per NoDir contracts.

If a hot rollback is required:
1. Revert Phase 8 runtime changes in `wepppy/nodir/wepp_inputs.py`, `wepppy/nodb/core/wepp.py`, and `wepppy/rq/wepp_rq.py`.
2. Re-run required WEPP/RQ NoDir regressions.
3. Restore previous wrapper behavior only if runtime rollback is confirmed clean.

## Residual Risks

- Measurements focus on orchestration overhead; full-production WEPP runtime variance (I/O pressure, large archive cache behavior) should still be observed during staged rollout.
- The helper intentionally supports only final-segment wildcard globs (`glob_input_files`); broader wildcard patterns remain unsupported by design.
