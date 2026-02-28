# Phase 8 Forest Dry-Run Report

- Date: 2026-02-27
- Command:
  - `python3 wepppy/tools/migrations/unroll_root_resources_batch.py --host forest --mode dry-run --audit-jsonl docs/work-packages/20260227_nodir_full_reversal/artifacts/phase8_forest_dry_run_audit.jsonl --summary-json docs/work-packages/20260227_nodir_full_reversal/artifacts/phase8_forest_dry_run_summary.json`
- Exit code: `1`

## Inventory Summary

- Roots scanned: `/wc1/runs`, `/wc1/batch`
- Runs discovered: `2744`
- Eligible runs (`apply_nodir=false` + in-scope root resources): `164`
- Ineligible/skipped runs: `2577`
- Dry-run run-status counts:
  - `dry_run`: `164`
  - `skipped`: `2577`
  - `error`: `3`
- In-scope root files discovered: `1024`
- Planned moves: `1022`
- Predicted conflicts: `2`

### Planned Move Counts by Resource Type

- `landuse`: `163`
- `soils`: `159`
- `climate`: `178`
- `watershed`: `477`
- `wepp_cli_pds_mean_metric.csv`: `45`

### Predicted Conflict Runs

1. `ill-taco` (`/wc1/runs/il/ill-taco`) `soils.parquet -> soils/soils.parquet` (hash mismatch)
2. `real-time-preserver` (`/wc1/runs/re/real-time-preserver`) `soils.parquet -> soils/soils.parquet` (hash mismatch)

### Dry-Run Error Notes

- `3` runs reported config resolution errors due missing config file `ext-disturbed9002.cfg` under `wepppy/nodb/configs`:
  - `/wc1/runs/rl/rlew-pale-faced-override`
  - `/wc1/runs/rl/rlew-unchangeable-formula`
  - `/wc1/runs/rl/rlew-womanly-surge`

## Review Conclusion

- Forest dry-run completed with auditable inventory and explicit conflict prediction.
- Forest apply proceeded in Phase 3 with explicit conflict-safe behavior and follow-up verification artifacts.
