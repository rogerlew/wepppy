# Roads Step-4 Code Review (2026-04-08)

## Scope

- Work package: `20260327_roads_outslope_unrutted_mofe_replacement`
- Primary implementation files:
  - `wepppy/nodb/mods/roads/roads.py`
  - `tests/nodb/mods/test_roads_controller.py`
  - `/workdir/wepppyo3/wepp_interchange/src/hill_pass_combine.rs`
- Spec alignment target:
  - `wepppy/nodb/mods/roads/specification.md` (step-4 contract section)

## Findings

### CR-01 (High): Phase-4 defaults and bounds drift from locked contract

- Prior state:
  - `rfg_pct_default` remained `15` instead of `20`.
  - Fill and buffer bounds were effectively capped by a generic `40%` slope clamp.
  - Required outslope-unrutted fill/buffer fields could silently default on non-numeric values.
- Resolution:
  - Updated defaults (`rfg_pct_default=20`).
  - Added explicit phase-4 bound enforcement for run params.
  - Added strict outslope-unrutted required-profile parsing with missing/invalid/out-of-range failure.
- Status: Resolved.

### CR-02 (Medium): Contributor ordering did not follow `D_med` ranking

- Prior state:
  - Contributors were processed by segment ID order, not by deterministic upslope-to-downslope (`D_med`) ordering.
- Resolution:
  - Added deterministic strip ordering by `discha_median_m` descending, tie-break by `segment_hillslope_id`.
- Status: Resolved.

### CR-03 (Medium): `phase4` combiner path was implicit

- Prior state:
  - `phase4` strategy parsed correctly but shared a combined `phase1|phase4` branch.
- Resolution:
  - Added explicit `combine_peakro_phase4` strategy hook with dedicated branch dispatch.
  - Current math intentionally matches phase-1 hydrograph superposition while preserving an explicit extension point.
- Status: Resolved.

### CR-04 (Medium): Step-4 implementation status mismatch in specification text

- Prior state:
  - Spec still labeled outslope-unrutted section as concept draft.
- Resolution:
  - Updated status/scope wording to implemented step-4 contract and synchronized details with code behavior.
- Status: Resolved.

## Residual Risks

- No unresolved medium/high code findings remain in this review scope.
- Low risk remains around future phase-4 combiner divergence (strategy hook exists; math is currently shared by design).

## Verdict

- Code review gate (Milestone 7): Pass.
