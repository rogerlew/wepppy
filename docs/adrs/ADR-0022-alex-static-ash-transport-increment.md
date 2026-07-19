# ADR: Alex Static Ash-Transport Increment

Status: Accepted
Date: 2026-07-18
Review Date: 2026-08-18

## Context

The Watanabe/Alex ash model exposes a static exponential transport mode with
initial transport capacity `A` in tonne ha⁻¹ mm⁻¹ and depletion coefficient
`B` in mm⁻¹. The implementation introduced in September 2025 passed the array
slice `cum_ash_runoff_mm[:i]` to scalar `math.exp`, used an ambiguous sign and
parenthesis convention, and failed when a runoff event occurred after the slice
contained multiple values.

The defect became production-visible after the July 2026 selector-propagation
fix began honoring `ash_model=alex` and `transport_mode=static` from the UI.

## Decision

For each daily ash-runoff increment, static transport is:

`delta_M = (A / B) * [exp(-B * Q_previous) - exp(-B * (Q_previous + delta_Q))]`

`Q_previous` is the scalar cumulative ash runoff through the previous timestep,
`cum_ash_runoff_mm[i - 1]`, and `delta_Q` is the current timestep's ash runoff,
`ash_runoff_mm[i]`. The result is a nonnegative daily transport increment in
tonne ha⁻¹ before the existing available-ash clipping is applied.

## Decision Provenance

Decision Venue: Codex maintenance conversation, 2026-07-18 22:38 PDT
Participants Present: WEPPpy requesting maintainer, Codex
Decision Owner(s): WEPPpy requesting maintainer
Implementer(s): Codex

## Change Summary

Previously, the static branch evaluated an array in `math.exp`, did not multiply
the current runoff increment by `B` inside the exponent, and placed the
exponential terms in an order that did not express a nonnegative depletion
increment. The new implementation evaluates two scalar cumulative-runoff
states and subtracts the later state from the earlier state.

Output columns, units, parquet schemas, controller state, and request fields are
unchanged. Only Watanabe/Alex static-mode transport values change; Watanabe/Alex
dynamic mode and the Srivastava model retain their existing calculations.

## Rationale

The selected equation integrates the exponentially depleted capacity between
the previous and current cumulative-runoff states. It preserves the declared
units, returns zero for zero runoff, remains nonnegative for nonnegative runoff,
and decreases for equal runoff increments as cumulative runoff increases.

## Alternatives Considered

1. Replace `[:i]` with `[i]` only - rejected because the current cumulative
   value is not assigned until later in the timestep and the sign and
   parenthesis defects would remain.
2. Apply NumPy exponentiation to the historical slice - rejected because the
   model requires one daily scalar increment, not a vector of all prior states.
3. Disable static mode - rejected because static Watanabe transport is an
   explicitly supported and required workflow.

## Consequences

Previously failing Alex/static jobs can be rerun without state migration. Their
transport results will differ from any output produced by workarounds based on
the invalid expression. Static-mode results remain subject to the existing
available-ash clipping, decomposition, wind, and mass-balance logic.

## Evidence

- `docs/projects/nasa-roses-utility-watersheds/watar-integration-plan.md`
- Forest baseline RQ job `67d03de4-4b15-4f72-a428-470571021bd4`, which
  reproduced the production array-to-scalar failure on 2026-07-18.
- Forest verification RQ job `b8f5d3ee-e45a-48fd-874e-3c3d839ed807`, which
  finished in 59.1 seconds and generated 106 hillslope parquet files plus five
  post-processing parquet datasets on 2026-07-18.
- `tests/nodb/mods/test_ash_multi_year_model_alex_static.py`

## Risk and Rollback Notes

The primary risk is a mismatch between the approved equation and independently
expected Watanabe static-mode results. Monitor exact test vectors and cloned-run
outputs. Rollback should revert this ADR and the formula together; do not restore
the array expression or silently switch affected runs to dynamic or Srivastava
mode.

## Implementation Notes

Keep the formula in a private scalar helper so exact vectors can test it without
running the full hillslope simulation. Full-path regression coverage must also
exercise cumulative runoff, clipping, dynamic-parameter independence, and mass
balance through the model loop and a real RQ worker job.
