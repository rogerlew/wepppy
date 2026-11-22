# WB-05F Work Package: Process-Guard Replay Closure Repair

**Status**: Completed
**Timezone**: UTC

## Overview

WB-05F is a Goblin Mode blocker package for the process-based water-balance
rewrite. After the runtime closure guard was moved off legacy fixed-form
`watbal*.for` accounting and onto the process adapter/probe path, the first
WB-05E replay sentinel stopped with a process closure failure:

- seed: `WB05C-CO-H0001`
- project: `cochlear-beriberi`
- replay target: year `9`, julian `9`, target OFE `8`
- first process-guard failure: year `9`, julian `9`, OFE `1`
- failure: `kernel_residual_mm = -15.8066`,
  `interchange_residual_mm = -15.8066`
- return code: `205`

The earlier WB-05E current-source scoreboard closed exported `H.wat` terms, but
the process guard proves the rewrite itself still has a conserved-state defect
before WB-08 cutover. WB-05F repairs the process implementation, not the legacy
fixed-form output path.

## Operating Mode

Use `.codex/skills/goblin-mode/SKILL.md` with Special-Ops Activation.

The active Goblin Mode agent owns the repair workspace for this package. They
may create branches, worktrees, scratch commits, and exploratory checkpoints as
needed. The invariant is non-negotiable: the process rewrite must conserve
water under the declared closure basis.

## Objective

Make the process-based water-balance guard pass for the WB-05E replay path,
starting with `WB05C-CO-H0001` year `9` julian `9` OFE `1`, then prove the
repair generalizes across the known WB-05B process-guard replay surface.

## Scope

### Included

- Reproduce the `WB05C-CO-H0001` process-guard failure with durable stderr,
  stdout, observe log, command, binary, and source commit evidence.
- Trace the process residual through the process adapters, kernels, storage
  state, transfer terms, and scheduler/probe mapping.
- Repair the process-based implementation wherever first-principles closure
  requires: `fpm-src/`, process adapters, process kernels, process types,
  probe wiring, scheduler glue, transfer accounting, storage accounting, and
  output mapping used by the process path.
- Add failing-first regression coverage for the H0001 process residual.
- Run sentinel replay for at least H0001, H0002, and H0003; run the full
  WB-05B seed scoreboard at major checkpoints.
- Preserve legacy fixed-form `watbal*.for` as integration context, not the
  durable repair target.
- Update WB-00 board/dependency state after closeout.

### Explicitly Out of Scope

- Patching legacy `src/watbal.for` or `src/watbal_hourly.for` accounting as the
  durable fix.
- Weakening `max_abs < 1.0 mm` process closure enforcement.
- Reclassifying process-guard failures as output-contract drift without a
  source-side repair or human-approved science escalation.
- Reopening WB-06 downstream parser/report compatibility unless a source repair
  changes a downstream contract.

## Success Criteria

- [x] H0001 process-guard replay returns `0` and emits process provenance.
- [x] H0001 process `kernel_residual_mm` and `interchange_residual_mm` are both
  strictly below `1.0 mm` at every guarded replay point.
- [x] Sentinel process-guard replay for H0001/H0002/H0003 closes or has explicit
  classified blockers with repair lanes.
- [x] Full WB-05B process-guard scoreboard closes, or every remaining failure is
  recorded with human-approved science escalation.
- [x] Regression tests assert closure rather than accepting non-closure.
- [x] Repair lane log records each broad/intuitive lane and its disposition.
- [x] Post-hoc review explains why the retained changes work and removes or
  documents exploratory residue.
- [x] WB-08 blocker disposition updated after this package closed.

## Deliverables

- `artifacts/special_ops_charter.md`
- `artifacts/failure_reproduction.md`
- `artifacts/source_target_contract.md`
- `artifacts/sentinel_process_guard_plan.md`
- `artifacts/repair_lane_log.md`
- `artifacts/posthoc_review_plan.md`
- `artifacts/process_guard_mechanism.md`
- `artifacts/process_guard_scoreboard_summary.md`
- `artifacts/wb08_cutover_blocker.md`
- `notes/README.md`
- `notes/2026-05-04_wb05f_disposition.md`
- `tracker.md`
- `prompts/active/wb05f_process_guard_replay_closure_repair_execplan.md`
- `prompts/active/wb05f_process_guard_replay_closure_repair_agent_prompt.md`

## Dependencies

- WB-05E closure and process-provenance evidence:
  `docs/work-packages/20260503-wb05e-goblin-mode-global-closure-repair/`
- Runtime process guard commit:
  `88a3ba60 Enforce process water-balance closure guard`
- WB-05B seed manifest:
  `docs/work-packages/20260503-wb05b-forest-hillslope-closure-sweep/artifacts/audits/_meta/defect_seeds.csv`
- Goblin Mode skill:
  `.codex/skills/goblin-mode/SKILL.md`

## Security Impact and Review Gate

- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Rationale**: local numerical model source repair and validation only.
