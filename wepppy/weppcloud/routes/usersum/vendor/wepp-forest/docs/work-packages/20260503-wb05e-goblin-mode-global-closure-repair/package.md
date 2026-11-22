# WB-05E Work Package: Goblin Mode Global Closure Repair

**Status**: Full current-source closure achieved; WB-06/WB-07 gate accepted for restart
**Timezone**: UTC

## Overview

WB-05E is the special-ops source-repair package for the **new process-based
water-balance implementation**. WB-05B found material closure failures in
`1166/1166` forest hillslopes, and WB-05C reproduced first-tranche failures
directly from raw `H.wat` and `H.pass` interchange terms. WB-05E uses that
evidence to make the rewritten process-based water-balance close, then wires
that implementation into the production replay path.

The WB-05C/WB-05D supersession closeout was not accepted as a downstream
unblock because no source-side invariant probe or repair was completed. WB-05E
now closes the known WB-05B defect surface with current-source process
provenance; WB-06/WB-07 may restart with the recorded contract-change and
compatibility obligations.

## Operating Mode

Use `.codex/skills/goblin-mode/SKILL.md` with Special-Ops Activation.

The active Goblin Mode agent owns the repair workspace while this package is
executing. Branches, worktrees, scratch commits, and exploratory checkpoints
are allowed as needed. The closure mission is the highest workspace priority
until the blocker is retired or the human operator redirects it.

Goblin Mode may remove process friction, but it must not remove the invariant:
closure is water-balance.

## Objective

Make the four known forest project scoreboards close at hillslope/day/OFE and
adjacent-transfer granularity by repairing and wiring the new process-based
water-balance implementation. The scoreboard must exercise the new routines,
not patched legacy `watbal*.for` accounting.

## Source Target Contract

Primary repair targets:

- `fpm-src/watbal_process_types.f90`
- `fpm-src/watbal_process_kernels.f90`
- `fpm-src/watbal_daily_adapter.f90`
- `fpm-src/watbal_hourly_adapter.f90`
- `src/watbal.f90`
- `src/watbal_hourly.f90`
- production build/call-site wiring needed to route replay execution through
  the new process-based implementation.

Legacy fixed-form files such as `src/watbal.for` and
`src/watbal_hourly.for` are evidence and integration context, not the repair
center of gravity. Do not patch legacy water-balance accounting in place as the
WB-05E solution.

Allowed legacy `.for` edits are limited to:

- temporary instrumentation/checkpoints,
- call-site glue needed to invoke the new process-based implementation,
- retirement shims that remove old behavior from the production path,
- mechanical synchronization after an accepted `.f90` repair.

Any legacy `.for` edit must be recorded in `artifacts/repair_lane_log.md` with
why it was unavoidable and how it preserves the new process-based source of
truth.

## Target Projects

- `moth-eaten-blackhead`
- `cochlear-beriberi`
- `ordained-incentive`
- `uninsured-deformation`

## Scope

### Included

- Broad intuitive source repair across the new process kernels, adapters,
  scheduler wiring, transfer accounting, storage accounting, and output mapping.
- Workspace ownership for the active Goblin Mode agent, including branches and
  worktrees.
- Production wiring so `src/wepp_hill`/scoreboard execution uses the new
  process-based routines.
- Sentinel feedback using WB-05C first-tranche seeds.
- Full-scoreboard validation against all WB-05B defect seeds and all four
  forest projects.
- Post-hoc explanation, simplification, divergence classification, and contract
  documentation after closure is achieved.

### Explicitly Out of Scope

- Unblocking WB-06 before the known defect surface closes.
- Treating legacy parity as the acceptance target.
- Patching `src/watbal.for` or `src/watbal_hourly.for` as the durable
  water-balance repair.
- Weakening closure audits, loosening thresholds, or reclassifying non-closure
  as passing evidence.
- Deferring known source-side conservation failures to downstream output
  contract work without a source-side probe.

## Success Criteria

- [x] WB-05C first-tranche sentinel tests assert closure and pass without
  strict `xfail`.
- [x] Scoreboard evidence proves the production replay path exercised the new
  process-based water-balance implementation.
- [x] Four-project closure scoreboard shows no material unresolved
  hillslope/day/OFE or adjacent-transfer failures.
- [x] `defect_seeds.csv` has every seed marked `closed_wb05e`; no bulk
  supersession from WB-05D alone.
- [x] Production source changes are explained post-hoc with mechanism notes.
- [x] Targeted regression tests cover repaired mechanisms.
- [x] Full required gates for touched code pass or are explicitly blocked with
  evidence.
- [x] WB-06/WB-07 unblock checklist is updated only after closure evidence.

Former blocker `WB05C-OR-H0066` (`ordained-incentive` H66, year 2017, julian
125, target OFE 9) is closed. Current scoreboard result is `1166/1166` closed
with process provenance on every row.

## Deliverables

- `artifacts/special_ops_charter.md`
- `artifacts/global_closure_scoreboard.md`
- `artifacts/workspace_control_plan.md`
- `artifacts/source_target_contract.md`
- `artifacts/integration_wiring_plan.md`
- `artifacts/sentinel_test_plan.md`
- `artifacts/repair_lane_log.md`
- `artifacts/posthoc_review_plan.md`
- `artifacts/wb06_wb07_unblock_gate.md`
- `tracker.md`
- `prompts/active/wb05e_goblin_mode_global_closure_repair_execplan.md`
- `prompts/active/wb05e_goblin_mode_global_closure_repair_agent_prompt.md`
- `notes/2026-05-03_wb05e_disposition.md`

## Dependencies

- WB-05B closure sweep evidence.
- WB-05C first-tranche raw-term reproduction.
- `.codex/skills/goblin-mode/SKILL.md` Special-Ops Activation.

## Security Impact and Review Gate

- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Rationale**: local numerical model source repair and validation only.
