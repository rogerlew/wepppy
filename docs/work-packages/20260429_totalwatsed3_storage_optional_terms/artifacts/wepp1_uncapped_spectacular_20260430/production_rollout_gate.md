# wepp1 Production Rollout Gate - uncapped-spectacular

Timestamp: 2026-04-30 04:09 UTC

Host identity:
- Host: `wepp1`
- Host run path: `/geodata/wc1/runs/un/uncapped-spectacular`
- Container run path: `/wc1/runs/un/uncapped-spectacular`
- Execution container: `docker-weppcloud-1`
- No container takedown or restart was performed.

## Source Patching

`weppcloud` container files were backed up and surgically patched before the one-shot regeneration:

- `/workdir/wepppy/wepppy/wepp/interchange/totalwatsed3.py.bak.20260430T040450Z`
- `/workdir/wepppy/tools/totalwatsed3_daily_closure_audit.py.bak.20260430T040450Z`

The host worktree copies were also backed up at:

- `/workdir/wepppy/wepppy/wepp/interchange/totalwatsed3.py.bak.20260430T040412Z`
- `/workdir/wepppy/tools/totalwatsed3_daily_closure_audit.py.bak.20260430T040412Z`

## Regeneration

Command shape:

```bash
docker exec -i docker-weppcloud-1 bash -lc \
  "cd /workdir/wepppy && PYTHONPATH=/workdir/wepppy /opt/venv/bin/python -" \
  < wepp1_regenerate_totalwatsed3.py
```

Output:

- Regenerated: `/wc1/runs/un/uncapped-spectacular/wepp/output/interchange/totalwatsed3.parquet`
- Backup: `/wc1/runs/un/uncapped-spectacular/wepp/output/interchange/totalwatsed3.parquet.bak.20260430T040509Z`
- New size: `3,242,385` bytes

Hashes:

- New `totalwatsed3.parquet`: `20f39d30280c9ccaf20754778e57c9e5595711ea334c8ffab82def2d89f68ca2`
- Backup `totalwatsed3.parquet.bak.20260430T040509Z`: `d649088f1948c3f98de4f4c5868824aba920b8552bacc07da4cfaf40f37c8e73`
- Audit summary JSON: `26466d774a6d6392df6d4892bd9dbc6f4440ebf5a1d52d3e4e7180673a6be73e`
- Hillslope reconciliation JSON: `9355d3d3067b57a0a33764e1bccd3789c3fc46c0162a9b6b1be48f7214fb9a65`

## Schema Availability

The regenerated `totalwatsed3.parquet` exposes:

- WAT storage/capacity columns: `SoilWaterTotal`, `ProfileDepth`, `ProfilePorosityCap`, `ProfileFCStore`, `ProfileWPStore`
- Optional partition/soil columns: `TSMF`, `QRain`, `QSnow`

The source `H.wat.parquet` for this production run is legacy and does not contain the five new WAT storage/capacity terms, so all five storage/capacity outputs are null for all `12,419` rows. `TSMF` is populated for all rows. `QRain` and `QSnow` are populated for `12,409` of `12,419` rows.

## Whole-Run Closure

Rows: `12,419`

- Rain + melt total: `81,950.594588 mm`
- Runoff total: `30,791.486211 mm`
- Lateral flow total: `38,852.165811 mm`
- ET total: `25,728.616661 mm`
- Percolation total: `218.323646 mm`
- Legacy storage change: `173.467018 mm`
- Reconstructed closure with legacy storage: `-13,813.464759 mm`
- Closure as percent of rain + melt: `-16.855844%`
- Mean absolute daily closure with storage: `1.877172 mm`
- Daily closure quantiles: p50 `0.007254 mm`, p90 `0.207403 mm`, p95 `2.077282 mm`, p99 `9.756166 mm`, max abs `541.600205 mm`
- Runoff consistency after regeneration: max abs `0.0 mm`

Largest whole-run outlier day:

- Date: 1996-02-06 (`year=1996`, `julian=37`)
- Rain + melt: `170.919102 mm`
- Precipitation: `118.967877 mm`
- Runoff: `722.410355 mm`
- Lateral flow: `9.192623 mm`
- ET: `1.658669 mm`
- Percolation: `0.020000 mm`
- Storage delta: `-20.762340 mm`
- Closure with storage: `-541.600205 mm`

## Hillslope Reconciliation

### H2637

- Rows: `12,419`
- Enriched storage available: `false`
- Rain + melt total: `104,595.080526 mm`
- Runoff total: `175,989.238678 mm`
- Lateral flow total: `24,381.336842 mm`
- ET total: `22,917.927368 mm`
- Percolation total: `242.962632 mm`
- Storage change: `310.269474 mm`
- Closure with storage total: `-119,246.654467 mm`
- Closure as percent of rain + melt: `-114.007900%`
- Mean absolute daily closure: `10.859044 mm`
- QRain total: `18,041.345579 mm`
- QSnow total: `23,525.836526 mm`
- QRain + QSnow total: `41,567.182105 mm`
- Top closure day: 1996-02-06, closure `-2,433.117073 mm`, rain + melt `202.042632 mm`, runoff `2,669.010757 mm`, storage delta `-37.653684 mm`

### H2809

- Rows: `12,419`
- Enriched storage available: `false`
- Rain + melt total: `106,763.031579 mm`
- Runoff total: `361,292.396776 mm`
- Lateral flow total: `17,997.680000 mm`
- ET total: `24,007.434737 mm`
- Percolation total: `245.588421 mm`
- Storage change: `336.650526 mm`
- Closure with storage total: `-297,116.718881 mm`
- Closure as percent of rain + melt: `-278.295506%`
- Mean absolute daily closure: `25.264905 mm`
- QRain total: `46,615.119368 mm`
- QSnow total: `55,326.764368 mm`
- QRain + QSnow total: `101,941.883737 mm`
- Top closure day: 1996-02-06, closure `-2,851.188677 mm`, rain + melt `206.148947 mm`, runoff `3,100.191309 mm`, storage delta `-45.809474 mm`

## Artifacts

- `daily_closure_audit_summary.json`
- `daily_closure_audit_top_days.csv`
- `hillslope_reconciliation_H2637_H2809.json`
- `hillslope_storage_reconciliation.py`
- `wepp1_regenerate_totalwatsed3.py`
