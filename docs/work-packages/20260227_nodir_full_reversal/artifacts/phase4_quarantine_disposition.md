# Phase 4 Quarantine Disposition

- Generated: 2026-02-27 08:56Z
- Source artifacts:
  - `phase3_migration_summary.md`
  - `phase3_quarantined_runs.md`

## Phase 3 Carryover State

- Bulk apply status counts: `{'already_directory': 52, 'readonly_required': 3880}`
- Quarantined run/root pairs: `3880`
- Unique quarantined runs: `970`
- Quarantine disposition from Phase 3: `open_for_retry_after_readonly_prep`

## Phase 4 Runtime-Removal Risk Acceptance

- Decision: proceed with Phase 4 runtime NoDir removal while retaining Phase 3 quarantine ledger as the operations backlog.
- Rationale: Phase 4 removes runtime archive dependencies and must not be blocked on maintenance-window rollout for historical runs.
- Operational constraint: quarantined runs that still contain archive-form roots require readonly prep before migration re-apply.

## Retry Ownership and Plan

- Owner: operations/on-call for run maintenance windows.
- Preconditions for retry:
  - create `WD/READONLY` for targeted runs,
  - rerun restore apply in resume mode using the canonical Phase 3 audit flow.
- Tracking source of truth: `phase3_bulk_apply_audit.jsonl` plus `phase3_quarantined_runs.md` summary.
- Success criteria for backlog closure:
  - all `readonly_required` entries moved to terminal success statuses (`restored` or `already_directory`),
  - no residual archive-only runtime roots required by active workloads.
