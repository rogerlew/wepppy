# Phase 8 Wepp1 Approval Packet (Dry-Run Scope)

- Date: 2026-02-28
- Historical state: `post-apply` (Phase 6 execution complete); checklist and pre-apply wording below are preserved as recorded gate-time evidence.
- Dry-run command (container path mapping on wepp1):
  - `wctl exec weppcloud /opt/venv/bin/python wepppy/tools/migrations/unroll_root_resources_batch.py --host wepp1 --mode dry-run --roots /wc1/runs,/wc1/batch --audit-jsonl /tmp/phase8_wepp1_dry_run_audit.jsonl --summary-json /tmp/phase8_wepp1_dry_run_summary.json`
- Exit code: `1`

## Dry-Run Outcome

- `status`: `error`
- Roots scanned:
  - `/wc1/runs`
  - `/wc1/batch`
- Totals:
  - runs discovered: `6993`
  - eligible runs (`apply_nodir=false` + in-scope roots): `252`
  - dry-run runs: `252`
  - skipped runs: `6281`
  - run errors: `460`
  - files discovered: `1571`
  - planned moves: `1554`
  - predicted conflicts: `11`

## Inventory Fields for Approval

- Eligible run count: `252`
- Planned move count by resource type:
  - `watershed`: `726`
  - `climate`: `239`
  - `landuse`: `237`
  - `soils`: `234`
  - `wepp_cli_pds_mean_metric.csv`: `118`
- Predicted conflict count: `11` (all `soils.parquet` hash mismatches)

## Dry-Run Error Disposition

- `460` runs failed before migration planning due config-resolution errors (missing cfg files under `/workdir/wepppy/wepppy/nodb/configs`, primarily `salvage-north_star_*` variants).
- Apply approval should be gated on explicit decision:
  - either remediate these config surfaces,
  - or accept that apply will proceed only for resolvable runs and leave unresolved runs as explicit errors.

## Proposed Maintenance Window

- Proposed window:
  - Start: 2026-03-02 01:00 UTC
  - End: 2026-03-02 04:00 UTC

## Rollback / Incident Contact Checklist

- [ ] On-call WEPPcloud operator assigned
- [ ] Wepp1 container mount mapping validated (`/wc1 -> /geodata/wc1`)
- [ ] Incident bridge channel designated
- [ ] Backup and restore owner identified

## Approved Apply Command (Executed in Phase 6)

```bash
wctl exec weppcloud /opt/venv/bin/python wepppy/tools/migrations/unroll_root_resources_batch.py \
  --host wepp1 \
  --mode apply \
  --roots /wc1/runs,/wc1/batch \
  --wepp1-approval-file docs/work-packages/20260227_nodir_full_reversal/artifacts/phase8_wepp1_approval.md \
  --approval-token <approved-token> \
  --audit-jsonl /tmp/phase8_wepp1_apply_audit.jsonl \
  --summary-json /tmp/phase8_wepp1_apply_summary.json
```

## Gate Status

- Wepp1 apply approval is complete in this run (see `artifacts/phase8_wepp1_approval.md`).
- Phase 4 dry-run inventory is complete by artifact contract (inventory + approval packet published).
- The `460` run-level dry-run errors are explicit approval-disposition items for Phase 5, not an execution blocker for Phase 4 completion.
- Phase 5 explicit human approval is recorded.
- Phase 6 apply execution and verification are complete (see `artifacts/phase8_wepp1_apply_report.md` and `artifacts/phase8_final_verification.md`).
