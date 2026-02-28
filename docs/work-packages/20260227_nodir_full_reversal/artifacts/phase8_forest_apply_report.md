# Phase 8 Forest Apply Report

- Date: 2026-02-27
- Apply command:
  - `python3 wepppy/tools/migrations/unroll_root_resources_batch.py --host forest --mode apply --audit-jsonl docs/work-packages/20260227_nodir_full_reversal/artifacts/phase8_forest_apply_audit.jsonl --summary-json docs/work-packages/20260227_nodir_full_reversal/artifacts/phase8_forest_apply_summary.json`

## Execution Notes

Apply was executed twice during Phase 3:

1. Initial apply run (exit `1`) migrated the bulk of eligible files, then surfaced transient/no-longer-present source-file conditions in active batch trees.
2. Script behavior was hardened for idempotent no-op handling of disappearing source files, then apply was rerun (exit `0`) to converge on a clean final state.

The persisted Phase 8 apply audit/summary artifacts represent the final convergence run.

## Final Apply Artifact Summary

- Roots scanned: `/wc1/runs`, `/wc1/batch`
- Runs discovered: `2744`
- Eligible runs with remaining in-scope root files at convergence start: `11`
- Final run-status counts:
  - `ok`: `9`
  - `conflict_requires_manual_resolution`: `2`
  - `skipped`: `2733`
  - `error`: `0`
- File actions:
  - `dedup_deleted_source`: `10`
  - `conflict`: `2`
  - `moved`: `0`
  - `error`: `0`

## Conflict Ledger (Manual Resolution Required)

1. `ill-taco` (`/wc1/runs/il/ill-taco`)
   - `soils.parquet` vs `soils/soils.parquet` hash mismatch
2. `real-time-preserver` (`/wc1/runs/re/real-time-preserver`)
   - `soils.parquet` vs `soils/soils.parquet` hash mismatch

## Post-Apply Verification

- Final apply run reported zero file-level errors.
- Remaining in-scope WD-root files are limited to the two explicit conflict runs above.
- Canonical targets for non-conflict files were present/readable at action time (hash-calculated during dedup/move logic).

## Conclusion

- Forest apply migration completed for non-conflict eligible runs.
- No silent overwrite behavior observed.
- Two conflict runs remain explicitly quarantined for manual data resolution.
