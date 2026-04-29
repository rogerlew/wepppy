# wepp1 Artifact Manifest - uncapped-spectacular totalwatsed3 refresh

## Primary artifact (requested)
- Host: `wepp1`
- Path: `/geodata/wc1/runs/un/uncapped-spectacular/wepp/output/interchange/totalwatsed3.parquet`

## Parquet integrity snapshots
- Pre-refresh:
  - SHA256: `bc507b37895883e40f8d7eea96eb1ce38fafaf3f874afc617274a874cb72dea1`
  - Stat: `2026-04-28 14:49:20.882843000 -0700`, size `2954086` bytes
- Post-refresh:
  - SHA256: `d649088f1948c3f98de4f4c5868824aba920b8552bacc07da4cfaf40f37c8e73`
  - Stat: `2026-04-29 14:31:49.132282000 -0700`, size `2954592` bytes

## Runtime patch evidence
- Host source backup: `/workdir/wepppy/wepppy/wepp/interchange/totalwatsed3.py.bak.20260429T211546Z`
- Runtime container backup: `/workdir/wepppy/wepppy/wepp/interchange/totalwatsed3.py.bak.20260429T212748Z`
- Runtime line verified in container module path:
  - `merged["Runoff"] = _safe_depth(merged["runvol"].to_numpy(dtype=np.float64, copy=False), area)`

## No-downtime evidence
- Container: `docker-weppcloud-1`
- `StartedAt` pre/post: `2026-04-29T07:16:25.521338171Z` (unchanged)
- State/health post: `running healthy`

## Post-refresh consistency check
- Query: `max(abs(Runoff - runvol/Area*1000.0))`
- Result: `0.0`
- Max runoff depth post-refresh: `722.4103546234194 mm`

## Closure audit outputs (wepp1)
- Directory: `/geodata/wc1/runs/un/uncapped-spectacular/wepp/output/interchange/audit_totalwatsed3_daily_closure_20260429`
- Summary JSON:
  - `/geodata/wc1/runs/un/uncapped-spectacular/wepp/output/interchange/audit_totalwatsed3_daily_closure_20260429/daily_closure_audit_summary.json`
- Top anomalies CSV:
  - `/geodata/wc1/runs/un/uncapped-spectacular/wepp/output/interchange/audit_totalwatsed3_daily_closure_20260429/daily_closure_audit_top_days.csv`

## Key audit outcomes
- `rows`: `12419`
- `runoff_consistency_mm.max_abs`: `0.0`
- `max_reported_runoff_mm`: `722.4103546234194`
- `max_runoff_to_precip_reported_pct`: `79413.84253448747`
