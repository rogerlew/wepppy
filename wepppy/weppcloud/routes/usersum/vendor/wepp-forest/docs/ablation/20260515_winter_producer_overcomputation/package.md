# Winter Producer Overcomputation Follow-On Package

**Status**: active  
**Scope**: hillslope (Gate 0 producer-correctness investigation)  
**Timezone**: UTC

## Objective

Investigate producer-side root cause(s) of `wmelt > snowpack` over-computation.

This package no longer uses the original p26 post-fix 23-event manifest as its active failing cohort premise. That manifest is retained for historical traceability only. Active failing cohorts are now discovered by Phase 3 fail-fast firings (`ERROR STOP 206`) under the operational clamp+preserve invariant.

## Origin Package

- `docs/ablation/20260514_insensible-aliquot_p26_hillslope_watbal-process-closure-205-ablation/`
- p26 closure class resolved under Candidate 1 + WB30 Shape A; Phase 3 promotion provides default discovery of Gate 0 producer defects.

## Implementation Fidelity and Sources

- **Fidelity target**: `faithful extraction`
- **Authoritative sources**:
  - `/home/workdir/wepp-forest/src/winter.for`
  - `/home/workdir/wepp-forest/src/melt.for`
  - `/home/workdir/wepp-forest/src/snowd.for`
  - `/home/workdir/wepp-forest/fpm-src/watbal_process_kernels.f90`
  - `/home/workdir/wepp-forest/src/watbal_process_probe.f90`

## Evidence Index

- historical/superseded seed cohort (pre-Shape-A baseline):
  - `artifacts/evidence/L00_t1d_counter_on_events.csv`
  - `artifacts/evidence/failing_tuples_ge10_ge1.csv`
  - `artifacts/evidence/SUPERSEDED.md`
- background decomposition/contract artifacts:
  - `artifacts/evidence/T1B_rainmelt_decomposition.csv`
  - `artifacts/evidence/T1C_kernel_rain_routing_trace.csv`
- governing invariant snapshot:
  - `artifacts/evidence/wbk08-clamp-preserve-mass-closure-invariant.md`

## Out of Scope For This Scope-Refinement Change

- No new traces or probes.
- No source edits in producer code.
- No watchlist execution.
- No Gate 0 investigation execution (separate prompt).
