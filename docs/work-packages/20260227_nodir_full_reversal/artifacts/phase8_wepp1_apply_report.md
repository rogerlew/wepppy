# Phase 8 Wepp1 Apply Report

- Date: 2026-02-28
- Apply command (approved gate artifact + container root mapping):
  - `wctl exec weppcloud /opt/venv/bin/python wepppy/tools/migrations/unroll_root_resources_batch.py --host wepp1 --mode apply --roots /wc1/runs,/wc1/batch --wepp1-approval-file docs/work-packages/20260227_nodir_full_reversal/artifacts/phase8_wepp1_approval.md --audit-jsonl /tmp/phase8_wepp1_apply_audit.jsonl --summary-json /tmp/phase8_wepp1_apply_summary.json`
- Apply exit code: `1` (expected by script contract when any run ends `error`)

## Final Apply Artifact Summary

- Roots scanned: `/wc1/runs`, `/wc1/batch`
- Runs discovered: `1853`
- Eligible runs with in-scope WD-root files at apply time: `2`
- Final run-status counts:
  - `ok`: `0`
  - `conflict_requires_manual_resolution`: `2`
  - `error`: `3`
  - `skipped`: `1848`
- File actions:
  - `moved`: `0`
  - `dedup_deleted_source`: `0`
  - `conflict`: `2`
  - `error`: `0`
  - `skipped`: `1848`

## Scope Reconciliation Note (Phase 4 Dry-Run vs Phase 6 Apply)

- Historical Phase 4 wepp1 dry-run artifact (`phase8_wepp1_dry_run_*`) captured an earlier root snapshot with `6993` discovered runs and `252` eligible runs.
- Phase 6 apply captured a different current root snapshot with `1853` discovered runs and `2` eligible runs.
- Reconciliation command executed after apply against the same roots:
  - `wctl exec weppcloud /opt/venv/bin/python wepppy/tools/migrations/unroll_root_resources_batch.py --host wepp1 --mode dry-run --roots /wc1/runs,/wc1/batch --audit-jsonl /tmp/phase8_wepp1_phase6_reconcile_dry_run_audit.jsonl --summary-json /tmp/phase8_wepp1_phase6_reconcile_dry_run_summary.json`
  - Exit: `1` (explicit run errors present, by contract)
  - Current snapshot totals: `1858` discovered, `2` eligible, `2` predicted conflicts, `3` run errors.
- This reconciliation confirms Phase 6 apply executed against the current `/wc1` tree and that current eligible/conflict surfaces align with current-snapshot dry-run results.

## Conflict Ledger (Manual Resolution Required)

1. `ill-taco` (`/wc1/runs/il/ill-taco`)
   - Source: `soils.parquet`
   - Target: `soils/soils.parquet`
   - Source SHA-256: `ba1c67c3fe09577804789abca46de443155d60ec9fefb4348a44e9876854420c`
   - Target SHA-256: `d9da489b704c5b081aec4809fff73531572391771a1ca2cd71d5386bc059cbbf`
   - Message: `target exists with different hash; leaving files untouched`
2. `real-time-preserver` (`/wc1/runs/re/real-time-preserver`)
   - Source: `soils.parquet`
   - Target: `soils/soils.parquet`
   - Source SHA-256: `c3a4e5d50e1d06ec2bd636db225311bb5e8f7c5397fc73b642eb7426f3899aa8`
   - Target SHA-256: `d9da489b704c5b081aec4809fff73531572391771a1ca2cd71d5386bc059cbbf`
   - Message: `target exists with different hash; leaving files untouched`

## Run-Error Ledger

- `config-resolution / missing cfg`: `3`
  - Message: `failed reading cfg file /workdir/wepppy/wepppy/nodb/configs/ext-disturbed9002.cfg: [Errno 2] No such file or directory: '/workdir/wepppy/wepppy/nodb/configs/ext-disturbed9002.cfg'`
  - Runs:
    - `rlew-pale-faced-override` (`/wc1/runs/rl/rlew-pale-faced-override`)
    - `rlew-unchangeable-formula` (`/wc1/runs/rl/rlew-unchangeable-formula`)
    - `rlew-womanly-surge` (`/wc1/runs/rl/rlew-womanly-surge`)

## Verification

- Canonical targets for successful move/dedup actions:
  - No `moved` or `dedup_deleted_source` actions occurred in this apply run, so there were no successful migrations requiring target-presence verification in Phase 6 output.
- Remaining WD-root in-scope files after apply:
  - Audit records show in-scope WD-root discovery only on the two conflict runs above (`files_discovered=1` each).
  - All other runs are either `skipped` with `files_discovered=0` or `error` before migration planning (`files_discovered=0`).
  - Therefore, in-scope WD-root residuals in this apply artifact are confined to explicit conflict/error outcomes; no `ok` run retained in-scope WD-root files.

## Conclusion

- Wepp1 apply executed using the approved gate artifact and correct container root mapping.
- No files were moved/deduplicated in this run.
- Two explicit conflicts and three config-resolution errors remain operator-visible for manual follow-up.
