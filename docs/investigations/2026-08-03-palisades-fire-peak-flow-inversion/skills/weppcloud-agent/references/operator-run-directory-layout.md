# Operator-only: WEPPcloud run directory layout (practical)

This reference assumes you can identify a concrete `run_dir` on disk (server access or local dev stack). Many downstream tasks (exports, reports, plots) depend on it.

Do not use this reference for normal WEPPcloud web users.

## Run roots and directories

Environment variables (with typical defaults):
- `PRIMARY_RUN_ROOT` → `/geodata/weppcloud_runs`
- `PARTITIONED_RUN_ROOT` → `/wc1/runs`
- `BATCH_ROOT` → `/wc1/batch`

Common patterns:
- Primary: `<PRIMARY_RUN_ROOT>/<runid>/`
- Partitioned: `<PARTITIONED_RUN_ROOT>/<prefix>/<runid>/` where `<prefix>` is the first 1–2 chars of `runid`.
- Batch: `batch;;<batch_name>;;<runid>` resolves to `<BATCH_ROOT>/<batch_name>/runs/<runid>/` (or `_base`).
- Config directory: many runs store configs under `<run_root>/<config>/`. If that folder exists, treat it as `run_dir`; otherwise `run_root` may already be the `run_dir`.
- Pup (optional): some workflows use `<run_root>/_pups/<pup>/` as an alternate `run_dir`.

Use `scripts/resolve_run_dir.py` to resolve these cases consistently.

## Output locations (within `run_dir`)

High-value directories:
- `wepp/output/` – classic WEPP outputs (text outputs, per-element files, etc.)
- `wepp/output/interchange/` – parquet datasets used by the report/query stacks
- `export/` – various exports (CSVs, GeoJSON, ArcMap exports, WEPPcloudR HTML output)

High-value interchange assets (examples):
- `wepp/output/interchange/totalwatsed3.parquet` – watershed totals / water balance tables
- `wepp/output/interchange/loss_pw0.out.parquet` – outlet delivery metrics
- `wepp/output/interchange/loss_pw0.chn.parquet` – channel summaries
- `wepp/output/interchange/loss_pw0.hill.parquet` – hillslope summaries
- `wepp/output/interchange/ebe_pw0.parquet` – event-by-event output (often for return periods)
- `wepp/output/interchange/chnwb.parquet` – channel water balance
- `wepp/output/interchange/H.wat.parquet` – hillslope water balance
