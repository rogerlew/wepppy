# Phase 8 Wepp1 Apply Approval

- Approver: Roger Lew
- Approver role: Human operator
- Approval timestamp (UTC): 2026-02-28T03:50:58Z
- Approval token value: none
- Approved command line:

```bash
wctl exec weppcloud /opt/venv/bin/python wepppy/tools/migrations/unroll_root_resources_batch.py \
  --host wepp1 \
  --mode apply \
  --roots /wc1/runs,/wc1/batch \
  --wepp1-approval-file docs/work-packages/20260227_nodir_full_reversal/artifacts/phase8_wepp1_approval.md \
  --audit-jsonl /tmp/phase8_wepp1_apply_audit.jsonl \
  --summary-json /tmp/phase8_wepp1_apply_summary.json
```

I Roger Lew, do solemnly swear I am a human and approve of the phase 5 gate.

wepp1 apply approved
