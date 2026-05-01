# Uncapped-Spectacular H2637 Ablation Campaign

**Status**: Complete (2026-04-30)  
**Timezone**: UTC

## Overview
`uncapped-spectacular` hillslope `H2637` showed a severe one-day closure anomaly in 1987 (`julian=44`). This package executed a structured ablation campaign (Linux production replay, Linux historical comparator, and required Windows comparator on `blarhg`) and captured attribution evidence.

## Objectives
- Stand up a dedicated ablation work package for `H2637` with an active ExecPlan and tracker.
- Pull and checksum the full `H2637` hillslope input/output source bundle from `wepp1`.
- Execute one-change-per-lane campaign structure with explicit Linux and Windows comparator lanes.
- Capture attribution artifacts and handoff-ready outcomes.

## Scope

### Included
- Package scaffolding (`package.md`, `tracker.md`, `prompts/active`, `artifacts/`).
- Source staging from `wepp1` for:
  - `wepp/runs/p2637.{run,cli,slp,sol,man,err}`
  - `wepp/output/H2637.{wat,pass,soil,element,loss,plot,ebe}.dat`
- Integrity artifacts (`manifest.csv`, `checksums.sha256`).
- Incident execution under `/workdir/wepp-forest/docs/ablation/20260430_uncapped-spectacular_h2637_hillslope_closure-spike/`.
- Linux + Windows comparator lane evidence and package evaluation summary.

### Explicitly Out of Scope
- Immediate physics/binary code patching in `wepp-forest`.
- Production run mutation under `/geodata/wc1/runs/un/uncapped-spectacular`.
- UI/report contract changes in WEPPcloud.

## Stakeholders
- **Primary**: Hydrology/model QA investigators for `uncapped-spectacular`.
- **Reviewers**: WEPP numerical stability maintainers and WEPPcloud operators.
- **Security Reviewer**: Not required unless scope expands to auth/session/secrets/queue surfaces.
- **Informed**: Erin and incident triage participants.

## Success Criteria
- [x] New package scaffold exists and is registered in `PROJECT_TRACKER.md`.
- [x] `H2637` source input/output bundle is staged locally from `wepp1`.
- [x] Staged bundle has manifest and SHA256 integrity records.
- [x] Active ablation lane matrix executed and attribution evidence captured.
- [x] Windows comparator (`wepppy-win-bootstrap.exe` on `blarhg`) lane results captured and compared.

## Key Outcomes

- Source + Linux production-binary replay (`C000`) reproduce the day-44 legacy closure spike.
- Historical comparator binary (`C010`, `wepp_dcc52a6_hill`) and Windows bootstrap comparator (`C020`) do not reproduce the day-44 spike.
- Day-45 residuals are near zero across lanes.
- In this replay/evaluation, the dominant day-44 term is OFE 19 (not OFE 14).

## Dependencies

### Prerequisites
- `wepp1` access to `/geodata/wc1/runs/un/uncapped-spectacular`.
- `blarhg` access for Windows comparator runs.
- `wepp-forest` ablation protocol (`docs/ablation/README.md`, `docs/ablation/protocol.md`).

### Blocks
- Routine-level source-cause isolation remains a follow-up package in `wepp-forest`.

## Related Packages
- **Related**: [20260430_hillslope_daily_closure_audit](../20260430_hillslope_daily_closure_audit/package.md)
- **Related**: [20260429_uncapped_spectacular_totalwatsed3_runoff_reconciliation](../20260429_uncapped_spectacular_totalwatsed3_runoff_reconciliation/package.md)
- **Related**: [20260422_jagged_hyperpigmentation_hillslope_ablation_queue](../20260422_jagged_hyperpigmentation_hillslope_ablation_queue/package.md)

## Timeline Estimate
- **Expected duration**: 2-3 focused sessions.
- **Actual duration**: 1 focused session for prep + lane execution.
- **Complexity**: Medium.
- **Risk level**: Medium (attribution complete; routine-level causality still open).

## Security Impact and Review Gate
- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: artifact staging and numerical behavior analysis only; no attack-surface changes.
- **Security review artifact**: `N/A`

## References
- `wepp1:/geodata/wc1/runs/un/uncapped-spectacular` - production source artifacts.
- `C:\src\wepppy-win-bootstrap\bin\wepppy-win-bootstrap.exe` on `blarhg` - required Windows comparator.
- `/workdir/wepp-forest/docs/ablation/20260430_uncapped-spectacular_h2637_hillslope_closure-spike/` - canonical incident record.
- `docs/work-packages/20260430_uncapped_spectacular_h2637_ablation_campaign/artifacts/evaluation_summary.md` - package evaluation summary.

## Deliverables
- Staged source snapshot under `artifacts/repro/source_wepp1/`.
- Integrity files under `artifacts/repro/manifest.csv` and `artifacts/repro/checksums.sha256`.
- Active ablation campaign ExecPlan and completed tracker.
- Package evaluation summary at `artifacts/evaluation_summary.md`.
- Compact incident evidence snapshot at `artifacts/incident_snapshot/`.

## Follow-up Work
- Open focused source-level ablation in `wepp-forest` to isolate day-44/OFE19 causal boundary in `wepp_260429_hill`.
- Expand recurrence checks to adjacent hillslopes if needed for blast-radius assessment.
