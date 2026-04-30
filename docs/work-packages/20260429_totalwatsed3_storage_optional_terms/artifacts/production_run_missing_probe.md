# Production Run Probe - `uncapped-spectacular`

Timestamp: 2026-04-30 03:43 UTC

Milestone 5 could not regenerate or audit the requested production artifact because
the rollout-gate run is not mounted in this workspace.

Checked paths:

- `/geodata/wc1/runs/un/uncapped-spectacular/wepp/output/interchange/totalwatsed3.parquet` - missing; `/geodata/wc1` is not present.
- `/wc1/runs/un/uncapped-spectacular/wepp/output/interchange/totalwatsed3.parquet` - missing.
- `/wc1/runs/un/uncapped-spectacular` - missing.

Command evidence:

    find /wc1/runs -maxdepth 2 -type d -iname '*uncapped*' -o -iname '*spectacular*'
    # no results

    wctl run-python - <<'PY'
    from pathlib import Path
    for raw in [
        '/geodata/wc1/runs/un/uncapped-spectacular/wepp/output/interchange/totalwatsed3.parquet',
        '/wc1/runs/un/uncapped-spectacular/wepp/output/interchange/totalwatsed3.parquet',
    ]:
        print(raw, Path(raw).exists())
    PY
    # /geodata/.../totalwatsed3.parquet False
    # /wc1/.../totalwatsed3.parquet False

Resolution: the run was confirmed on wepp1 at
`/geodata/wc1/runs/un/uncapped-spectacular`. Milestone 5 was completed there on
2026-04-30 04:09 UTC without container takedown. See
`wepp1_uncapped_spectacular_20260430/production_rollout_gate.md`.
