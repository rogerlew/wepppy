# WB-06 Work Package: Water-Balance Downstream Contract Integration

**Status**: Completed
**Timezone**: UTC

## Overview

WB-06 validates the WEPPpy-facing output contract after the WB-05E
water-balance closure repair. WB-05E closed the known four-project defect
surface and added optional trailing `InterceptionStorage` to hillslope `H.wat`
so live plant/residue interception carryover is visible as conserved storage.

WB-06 does not cut over production accounting to the new process kernels. The
process water-balance path remains provenance-gated behind `wepp_observe.on`.
WB-06 integrates and validates the production output contract that downstream
WEPPpy parsers, reports, audits, and aggregators consume. WB-08 owns process
kernel production cutover and legacy accounting retirement.

## Objective

Deliver downstream compatibility evidence for water-balance outputs:

- `H.wat` parser compatibility with optional trailing `InterceptionStorage`,
- report compatibility for hillslope water-balance output,
- `totalwatsed3` aggregation compatibility,
- `chnwb` non-regression evidence,
- closure-audit basis labels that match WB-05E conserved-state scoring,
- contract-drift checklist with zero unresolved blockers,
- WB-07 and WB-08 handoff notes.

## Scope

### Included

- Update or validate downstream WEPPpy parsers against `InterceptionStorage`.
- Verify current and legacy `H.wat` layouts are handled intentionally.
- Verify report and aggregation consumers tolerate the optional column.
- Validate closure-audit tooling labels the conserved-state basis explicitly:
  `P + Irr` external input and
  `SoilWaterTotal + Snow-Water + InterceptionStorage` storage.
- Preserve explicit failure on unknown or malformed output headers.
- Publish compatibility evidence and a gate disposition note.

### Explicitly Out of Scope

- Changing process-kernel physics; belongs to WB-04/WB-05/WB-05E repair lanes.
- Making process kernels the production accounting source; belongs to WB-08.
- Performance benchmark acceptance and observability alias rollout; belongs to
  WB-07.
- Weakening closure gates or reviving WB-05D audit-contract supersession.

## Success Criteria

- [x] `H.wat` parser/report tests pass with optional `InterceptionStorage`.
- [x] Legacy `H.wat` rows without `InterceptionStorage` remain compatible where
  backward compatibility is intended.
- [x] Unknown/malformed `H.wat` headers fail explicitly.
- [x] `totalwatsed3` aggregation tests pass or approved drift is documented.
- [x] `chnwb` tests pass or approved non-water-balance drift is documented.
- [x] Representative closure-audit tooling remains contract-consistent.
- [x] WB-02 change-control references are reconciled in the final gate memo.
- [x] Divergence ledger has zero `UNRESOLVED` entries.
- [x] WB-07/WB-08 handoff notes are published.
- [x] WB-00 board/dependency state is updated at closeout.

## Deliverables

- `artifacts/source_target_manifest.md`
- `artifacts/compatibility_test_plan.md`
- `artifacts/parser_report_acceptance_plan.md`
- `artifacts/contract_drift_checklist.md`
- `artifacts/divergence_ledger.md`
- `artifacts/wb07_handoff_checklist.md`
- `artifacts/wb08_cutover_prereq_note.md`
- `notes/2026-05-04_wb06_disposition.md`
- updated `tracker.md`
- updated WB-00 board/dependency state

## Dependencies

- Completed WB-05E closure repair:
  `docs/work-packages/20260503-wb05e-goblin-mode-global-closure-repair/`
- WB-06 kickoff memo:
  `docs/work-packages/20260503-wb00-waterbalance-program-bootstrap/artifacts/wb06_kickoff_memo.md`
- Approved `InterceptionStorage` change request:
  `docs/work-packages/20260503-wb02-waterbalance-spec-freeze/artifacts/contract_change_requests/WB02-CC-20260504-02-wb05e-interception-storage-output.md`
- Output mapping contract:
  `docs/schemas/watbal_output_mapping.schema.md`
- Core closure contract:
  `docs/schemas/watbal_core.schema.md`

## Security Impact and Review Gate

- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Rationale**: parser/report compatibility and numerical output contract
  validation only; no auth/session/secret surface is intentionally changed.

## References

- `prompts/active/wb06_waterbalance_downstream_contract_integration_execplan.md`
- `prompts/active/wb06_waterbalance_downstream_contract_integration_agent_prompt.md`
- `docs/work-packages/20260503-wb00-waterbalance-program-bootstrap/artifacts/wb06_kickoff_memo.md`
- `docs/work-packages/20260503-wb00-waterbalance-program-bootstrap/artifacts/program_governance.md`
- `docs/work-packages/20260503-wb05e-goblin-mode-global-closure-repair/artifacts/global_closure_scoreboard.md`
