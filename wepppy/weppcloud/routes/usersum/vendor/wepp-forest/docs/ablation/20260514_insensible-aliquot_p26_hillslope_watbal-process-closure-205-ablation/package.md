# P26 Hillslope Watbal Process-Closure 205 Ablation and Structural RCA

**Status**: Resolved (2026-05-15 UTC) for the reopened cross-release hillslope water-balance regression cohort (`wepp_260507_hill` vs `wepp_260513_hill`).
**Timezone**: UTC

## Overview

`run_hillslope` for run `insensible-aliquot` failed on `p26.run` with `ERROR STOP 205` from the process closure guard (`watbal_process_probe -> wb_closure_guard_assert_process`). Candidate 1 rerouted rain mass to `rain(iplane)` and kept `wmelt(iplane)` melt-only, resolving the original p26 hard-stop (`exit 0`) with target-tuple residuals at floating-point noise.

This package was reopened because cross-run replay evidence showed a broader regression in `wepp_260513_hill` relative to `wepp_260507_hill` on the same run cohort (57 `ERROR STOP 205` failures vs 0, with p26 passing in both). The reopened scope (T1G) completed with commit-level attribution and a Gate-2-conformant WB30 fix that restores cohort closure.

## Objectives

- Reproduce the failure from a staged copy of `p26` inputs with shared context.
- Isolate first and downstream failing boundaries for closure residuals.
- Verify whether threshold sweeps indicate policy-only failure or a recurring structural signal.
- Capture pre-assert process probes at the failing tuple in default mode.
- Resolve the raw-vs-kernel wmelt contradiction at the adapter boundary.
- Land Phase 1 non-fatal WBK08 clamp+preserve surveillance counter for baseline data.
- Restore source parity after temporary threshold ablation patches.

## Scope

### Included

- Failure analysis for `/wc1/runs/in/insensible-aliquot/wepp/runs/p26.err`.
- Full staged replay and lane matrix execution (`L00`, `O1`, `G1`, `G2`, `G0`, `O2B-D`, `O2E`, `O3B-C`).
- Structural probe expansion plus WBK08 shortfall-status export.
- WBK01 boundary probe at normalization call site.

### Explicitly Out of Scope

- Promotion of global closure-threshold relaxation as remediation.
- Broader hydrology retuning outside this confirmed failure class.

## Implementation Fidelity and Evidence

- **Fidelity target**: `faithful extraction`
- **Authoritative source path(s)**:
  - `/workdir/wepp-forest/fpm-src/watbal_closure_guard.f90`
  - `/workdir/wepp-forest/fpm-src/watbal_process_kernels.f90`
  - `/workdir/wepp-forest/fpm-src/watbal_hourly_adapter.f90`
  - `/workdir/wepp-forest/src/watbal_process_probe.f90`
- **Acceptance evidence type**: `both`

## Success Criteria

- [x] Work-package scaffold created under `docs/ablation`.
- [x] Baseline failure signature captured with traceback anchors.
- [x] Ablation matrix executed with reproducible per-lane evidence.
- [x] Threshold sweep bounded (`4.12` fail / `4.13` pass) and explicitly retired as remediation.
- [x] Default-mode targeted probes captured before closure assert.
- [x] WBK08 shortfall-status export captured recurring `WBK08_OUTPUT_SCALED_D06_PRESERVED` pattern.
- [x] WBK01 boundary probe confirmed raw-vs-normalized wmelt behavior at failing tuple.
- [x] Source threshold restored and baseline parity re-verified.

## Key Findings

1. Baseline (`1.0 mm`) fails deterministically at `year=1 julian=84 ofe=1` with residual `-3.94836490 mm`.
2. Threshold sweeps (`G1`/`G2`) only move the boundary (`4.0 mm` shifts failure to `year=7 julian=347`); this demonstrates recurrence and does not resolve root cause.
3. Default-mode tuple probes (`O2D`/`O2E`) confirm OFE1 deficit signature:
   - `inputs_total_mm=0.0`, `outputs_total_mm=6.0087`, `storage_delta_mm=-2.0604`, `residual_mm=-3.9484`.
4. WBK08 export (`O2E/O3B`) shows repeated pre-failure status `WBK08_OUTPUT_SCALED_D06_PRESERVED` from day 56 through day 83 on OFE1/OFE2.
5. WBK01 boundary probe (`O3B`) resolves the wmelt contradiction:
   - `raw_wmelt_mm=54.7`
   - `normalized_wmelt_mm=0.0`
   - `wbk01_status_message=WBK01_MELT_SNOWPACK_CAP`
   This explains why closure sees `inputs_total_mm=0` at the assert tuple.
6. `4.13 mm` is a diagnostic upper bound for this replay, not an acceptable remediation target.
7. Phase 1 surveillance counter now records clamp+preserve co-occurrence events with suppression-magnitude buckets and per-run summary:
   - `process_accounting_wbk08_clamp_preserve_counter`
   - `process_accounting_wbk08_clamp_preserve_counter_path`
   - default outputs:
     - `../output/wbk08_clamp_preserve_counter_events.csv`
     - `../output/wbk08_clamp_preserve_counter_summary.csv`
   - event rows include `event_basis`:
     - `suppressed` (true raw-normalized suppression),
     - `raw_preserve` (preserve-path silent-pass cohort, e.g. day 83 OFE1 wmelt `0.5 mm`).
8. Counter-off/on parity replays preserve incident behavior:
   - both lanes terminate with `ERROR STOP 205`,
   - both lanes retain the same tuple residual `-3.94836490 mm`,
   - only counter-on emits the new event/summary files.
9. Track 1 producer trace (diagnosis-only) attributes the `raw_wmelt` tuples to `winter.for` day-end broadcaster `WINTER_L464` (`wmelt=totmel`) with upstream hourly contributors in `melt.for`/`snowd.for`; see `artifacts/T1_wmelt_producer_diagnostic.md`.
10. Track 1B rain-on-snow conflation falsification (diagnosis-only) confirms `WINTER_L459` rain-add dominates `WINTER_L464` broadcast on failure cohorts (`82-95%` contribution on day-84/year-7 tuples) and sharpens day-84 disposition to precipitation-path bypass (`hrrain=51.7 mm`, `precipitation_input=0`, `rain_channel=0`, `wmelt_channel=54.7 mm`); see `artifacts/T1B_rainmelt_conflation.md`.
11. Track 1C rain-routing contract determination (diagnosis-only) confirms kernel process-water accounting does not consume `precipitation_input` (`inputs_total` remains `rain+wmelt+irrigation+runon`), so rain-on-snow channel semantics are currently hybrid/undefined and require explicit contract decision before producer fix; see `artifacts/T1C_rain_routing_contract.md`.
12. Track 1D Candidate 1 producer fix (`winter` melt/rain split + `contin` rain suppression removal) resolves the day-84/day-347 closure hard-stop (`exit 0`; day-84 and day-347 residuals near machine epsilon).
13. Post-fix Phase 1 surveillance still reports `bucket_ge_10_mm=20` and `bucket_ge_1_mm=3`; this is treated as a separate producer-side over-computation class, not a blocker to p26 closure, and is carried by `docs/ablation/20260515_winter_producer_overcomputation/`.
14. T1G bisection confirms `WB30` (`163d4914`) is first-bad and `WB18` is not first-bad for the reopened cohort:
   - sentinel set passes at `WB30^` and `WB18^`,
   - same set fails at `WB30`,
   - same set fails on Candidate-1 baseline (`c2f2bf6d`) and passes after Shape-A fix.
15. T1G Gate-2 fix (Shape A) in WB30 shortfall reconciliation removes D06-preserve asymmetry under suppression and restores conservation on normalized inputs.
16. Full reopened cohort validation passes with fixed master build:
   - `477 ok / 0 failed / 0 ERROR STOP 205`,
   - representative counter subset `ge_10_mm=0`, `ge_1_mm=0`,
   - Candidate-1 p26 tuple residuals remain at floating-point noise (`~1e-15`).

## Disposition

- **Rejected remediation**: global threshold bump to `4.13 mm`.
- **Reason**: masks a structural mass-closure gap.
- **Current package conclusion**: resolved. Reopened release-regression attribution is complete and remediation is validated.
- **Residual risk disposition**: Gate 0 producer-correctness work remains tracked in follow-on package `20260515_winter_producer_overcomputation`; this package closes the Gate-2 cohort regression class.

## References

- `/wc1/runs/in/insensible-aliquot/wepp/runs/p26.err`
- `artifacts/ablation_stage_matrix.csv`
- `artifacts/ablation_stage_summary.json`
- `artifacts/summary_verdict.md`
- `artifacts/logs/O2E_target84_missing_input_diagnostic.csv`
- `artifacts/logs/O2E_target84_derived_balance.csv`
- `artifacts/logs/O2E_wbk08_export.csv`
- `artifacts/logs/O3B_wbk01_input_probe.csv`
- `artifacts/logs/O3B_kernel_boundary_vs_preassert.csv`
- `artifacts/logs/O3C_wmelt_consecutive_rows.csv`
- `artifacts/T1B_rainmelt_decomposition.csv`
- `artifacts/T1B_kernel_channel_rain.csv`
- `artifacts/T1B_rainmelt_conflation.md`
- `artifacts/T1C_kernel_rain_routing_trace.csv`
- `artifacts/T1C_rain_routing_contract.md`
- `artifacts/T1D_rain_routing_fix.md`
- `artifacts/T1F_260507_vs_260513_regression_assessment.md`
- `artifacts/T1G_wb30_bisection_evidence.csv`
- `artifacts/T1G_wb30_fix.md`
- `/workdir/wepp-forest/docs/contracts/wbk08-clamp-preserve-mass-closure-invariant.md`

## Deliverables

- Completed lane matrix and summary artifacts.
- Default-mode targeted probe evidence for failing tuple.
- WBK08 shortfall export evidence showing recurring pre-failure shortfall class.
- WBK01 boundary probe evidence for raw vs normalized input discrepancy.
- Phase 1 clamp+preserve counter outputs (`events` + `summary`) for Phase 2 baseline.
- Track 1 producer trace artifact (`artifacts/T1_wmelt_producer_trace.csv`) and diagnostic report (`artifacts/T1_wmelt_producer_diagnostic.md`).
- Track 1B rainmelt decomposition artifact (`artifacts/T1B_rainmelt_decomposition.csv`), kernel-channel artifact (`artifacts/T1B_kernel_channel_rain.csv`), and verdict report (`artifacts/T1B_rainmelt_conflation.md`).
- Track 1C kernel-routing trace artifact (`artifacts/T1C_kernel_rain_routing_trace.csv`) and contract verdict report (`artifacts/T1C_rain_routing_contract.md`).
- Track 1D fix attempt report (`artifacts/T1D_rain_routing_fix.md`) with executed pass/fail gate evidence.
- Restored-threshold parity verification artifacts.
