# Generative Inputs Fuzzing Milestone 5: Single-OFE Sensitivity Calibration

**Status**: Completed (2026-04-22 UTC)
**Timezone**: UTC

## Overview

Milestone 4 preserved single-OFE controls and doubled campaign scale, but still
produced a `PASS`-only outcome (`216/216`). Milestone 5 converts that result
into calibrated confidence by adding three required capabilities:

- positive controls in every campaign run,
- larger single-OFE campaign scale (`>= 1000` executed cases),
- secondary output oracle detection beyond trap/signature classification.

## Objectives

- Prove campaign sensitivity with deterministic positive controls.
- Increase statistical confidence by executing a larger stratified single-OFE run.
- Detect silent numeric pathologies (`NaN`/`Inf`/obvious physical impossibilities)
  even when process exit status is clean.
- Publish explicit confidence bounds and calibration disposition.

## Scope

### Included

- Positive-control lane and sensitivity gate for campaign + summarize flow.
- Secondary output oracle contract and per-case oracle manifest.
- Large calibrated single-OFE campaign (stratified dry/mesic/wet x
  gradual/moderate/steep).
- Confidence summary artifact with overall and per-bin upper-bound estimates.
- Required gates and evidence updates.

### Explicitly Out of Scope

- Multi-OFE generation or execution.
- Fortran source patching.
- Final scientific parity adjudication.

## Normative Constraints

1. Single-OFE hard scope
- Execute only single-OFE campaign cases.
- Continue quarantining `SOIL_MULTI_OFE` and parser-invalid seeds.

2. Preserve M3/M4 controls
- Keep preflight quarantine and mandatory 3x3 climate/slope coverage.
- Keep profile attribution and adaptive selection lineage in manifests.

3. Positive controls are mandatory
- Each campaign run must include a deterministic positive-control set proving
  non-pass detection is alive.
- Sensitivity gate fails if any required control is not detected as non-pass.

4. Secondary oracle is mandatory
- Add output-sanity checks independent of trap/exit-code/signature classifier.
- Oracle flags must be persisted per case and folded into boundary triage.

5. Campaign scale target
- Primary run must execute at least `1000` single-OFE generated cases.
- Maintain per-bin minimum floors while allowing weighted oversampling.

## Success Criteria

- [ ] Positive-control lane implemented and sensitivity gate passes.
- [ ] Secondary oracle implemented with explicit contract and case-level outputs.
- [ ] Calibrated campaign executes `>= 1000` single-OFE cases.
- [ ] 3x3 climate/slope coverage preserved with per-bin evidence.
- [ ] Confidence artifact includes overall + per-bin upper bounds.
- [ ] Milestone 0/1/2/3/4 regression gates remain green.

## Dependencies

### Prerequisites

- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone4-single-ofe-boundary-amplification/`
- `/home/workdir/wepp-forest/generative-inputs-fuzzing/results/milestone4_single_ofe_campaign/`
- `/home/workdir/wepppy/wepppy/wepp/fuzzing/single_ofe_stratified_campaign.py`
- `/home/workdir/wepppy/wepppy/wepp/fuzzing/seeded_soil_landuse_generators.py`

### Blocks

- Compose/runtime dependency failure in execution environment.
- Missing/invalid positive-control corpus for sensitivity validation.

## Timeline Estimate

- **Expected duration**: 3-7 days.
- **Complexity**: High.
- **Risk level**: High.

## Security Impact and Review Gate

- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: local fuzzing/tooling and evidence flows only.
- **Security review artifact**: `N/A`

## Deliverables

- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone5-single-ofe-sensitivity-calibration/tracker.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone5-single-ofe-sensitivity-calibration/prompts/active/milestone5_single_ofe_sensitivity_calibration_execplan.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone5-single-ofe-sensitivity-calibration/artifacts/command_log.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone5-single-ofe-sensitivity-calibration/artifacts/positive_control_plan.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone5-single-ofe-sensitivity-calibration/artifacts/oracle_contract.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone5-single-ofe-sensitivity-calibration/artifacts/confidence_targets.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone5-single-ofe-sensitivity-calibration/notes/review_*.md`

## Follow-up Work

- Milestone 6: single-OFE boundary patch closure from calibrated queue.
- Milestone 7: gated multi-OFE pilot only after M6 closure.

## Closure Notes

- M5-A..M5-D implemented in code and validated with required gate suite.
- Calibrated run executed `1008` single-OFE cases with full 3x3 coverage.
- Sensitivity gate passed (`5/5` positive controls detected).
- Composite non-pass queue generated from oracle + signature contract (`140`
  oracle-flagged cases; signature lane pass-only).
