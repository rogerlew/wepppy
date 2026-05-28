# ADR: RUSLE K Conservative Second-Stage Gap Fill

Status: Accepted  
Date: 2026-05-27  
Review Date: 2027-05-27

## Context

The existing RUSLE POLARIS `K` preprocessing filled only small interior nodata
components (`<=64` px) before near-surface aggregation. In stony Southern
California runs, this left substantial off-channel nodata islands in `K` and
`A` outputs, producing visually spotty coverage despite valid surrounding
terrain.

The existing stage-1 behavior should remain conservative and unchanged. The
requested change is to add a bounded second stage that can fill medium interior
holes while preserving strict safeguards against broad interpolation.

## Decision

Keep the current stage-1 policy and add a second conservative fill stage.

Stage-1 (unchanged):

- candidate size: `1-64` px
- candidate fraction guard: `<=10%`
- search distance: `6` px
- edge-connected components excluded

Stage-2 (new):

- candidate size: `65-4096` px
- candidate fraction guard: `<=5%`
- search distance: `12` px
- runs only on residual nodata after stage-1
- edge-connected components excluded

Both stages keep smoothing iterations at `0` and use inverse-distance filling.

Manifest reporting is expanded so policy and outcomes are explicit for each
stage while retaining stage-1 top-level keys for backward compatibility.

## Decision Provenance (Required for Parameterization Changes)

Decision Venue: Codex user request thread, 2026-05-27 PDT  
Participants Present: User, Codex  
Decision Owner(s): User / WEPPcloud operator request  
Implementer(s): Codex

## Change Summary

Old behavior:

- one-stage conservative fill only (`<=64` px).
- medium interior gaps remained unresolved by design.

New behavior:

- two-stage conservative fill:
  - stage-1 small holes (existing behavior), then
  - stage-2 medium holes (`65-4096` px) under stricter fraction guard.
- manifest includes nested stage policy/outcome metadata.

## Rationale

- Preserves previously validated stage-1 behavior.
- Adds a controlled pathway for medium residual holes that materially affect map
  continuity.
- Keeps conservative controls explicit and auditable.
- Avoids introducing UI knobs or unconstrained interpolation.

## Alternatives Considered

1. Increase stage-1 max hole size and keep one stage - Rejected.
   This would blur the distinction between small and medium fill behavior and
   hide the contract change behind existing keys.
2. Leave behavior unchanged and accept spotty coverage - Rejected.
   Operational output quality remained poor for affected runs.
3. Fill all remaining interior holes without size/fraction guard - Rejected.
   Too aggressive and risks inventing large synthetic surfaces.

## Consequences

- Positive:
  - Improved `K` continuity in runs with medium interior POLARIS nodata islands.
  - Better downstream `A` coverage in off-channel hillslope areas.
  - Explicit stage provenance in manifest supports review and tuning.
- Risks:
  - Over-fill risk is reduced but not eliminated; bounded by stage-2 fraction
    and component-size guards.

## Evidence

- Work package: `docs/work-packages/20260527_rusle_k_second_stage_gap_fill/package.md`
- Runtime implementation: `wepppy/nodb/mods/rusle/k_integration.py`
- Regression tests: `tests/nodb/mods/test_rusle_k_integration.py`
- Run diagnosis motivating change: `/wc1/runs/st/strained-mod/rusle/` showed
  residual off-channel `K` gaps after stage-1-only fill.

## Risk and Rollback Notes

- Monitor sensitivity by comparing affected runs before/after rollout.
- If stage-2 fill appears too aggressive, rollback path is to disable stage-2
  and retain stage-1 behavior unchanged.

## Implementation Notes

- Backward-compatible top-level stage-1 policy keys are preserved in
  `k.gap_fill_policy` and per-property summaries while nested `stage1`/`stage2`
  records carry the full two-stage contract.
