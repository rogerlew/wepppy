# Generative Inputs Fuzzing Milestone 4: Single-OFE Boundary Amplification

**Status**: Open (2026-04-21 UTC)
**Timezone**: UTC

## Overview

Milestone 3 proved single-OFE preflight, mandatory climate/slope stratification,
and scaled campaign execution. However, campaign yield was low (`PASS`-only
signature cluster). Milestone 4 increases boundary yield without relaxing the
single-OFE safety envelope.

This package introduces targeted mutation-pressure profiles and adaptive
oversampling while preserving the Milestone 3 preflight/stratification contract.

## Objectives

- Increase non-pass boundary discovery in single-OFE campaigns.
- Keep single-OFE-only scope and preserve Milestone 3 controls.
- Add targeted mutation profiles around known arithmetic fragility zones.
- Add adaptive oversampling of high-warning/high-novelty seed segments.
- Produce patch-ready non-pass signature queue with minimized repro lineage.

## Scope

### Included

- Mutation-pressure profile design and implementation for single-OFE seeds.
- Adaptive sampling logic driven by soft-invariant warning density and novelty.
- Yield-target gating and campaign stop/continue criteria.
- Scaled reruns with stratification retained.
- Evidence artifacts for yield and candidate boundary triage.

### Explicitly Out of Scope

- Multi-OFE fuzzing generation/execution.
- Multi-OFE triage and patching.
- Broad WEPP scientific parity adjudication.

## Normative Constraints

1. Single-OFE hard scope
- Only single-OFE campaign cases may be executed.
- Any multi-OFE candidate remains quarantined.

2. Preserve M3 controls
- Do not remove preflight quarantine stages from Milestone 3.
- Do not remove climate/slope stratification bins (`dry|mesic|wet` and
  `gradual|moderate|steep`).

3. Mutation-pressure profiles (required)
Implement and document profiles targeting fragile arithmetic regimes, including:
- near-zero denominator boundaries,
- zero/near-zero event duration and intensity edges,
- conductivity/saturation extreme combinations,
- high-contrast texture/density transitions,
- slope-response stress windows.

4. Adaptive oversampling (required)
- Increase sampling weight for seed groups with high soft-warning density and/or
  novel signatures from previous runs.
- Keep reproducibility through explicit RNG seeds and logged weighting factors.

5. Yield targets (required)
Milestone 4 is considered successful only if at least one target is met:
- `>= 3` unique non-pass canonical signature keys, or
- `>= 1` unique non-pass signature appearing in `>= 5` cases.

## Success Criteria

- [ ] Mutation-pressure profiles implemented and documented.
- [ ] Adaptive oversampling logic implemented and reproducible.
- [ ] M3 stratification/preflight contracts preserved and evidenced.
- [ ] Milestone 4 yield target met (or explicit stop report with diagnostics).
- [ ] Patch-ready boundary queue includes non-pass signatures with repro lineage.
- [ ] Milestone 0/1/2/3 regression gates remain green.

## Dependencies

### Prerequisites

- Milestone 3 package outputs:
  - `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone3-single-ofe-stratified-campaign/`
  - `/home/workdir/wepp-forest/generative-inputs-fuzzing/results/milestone3_single_ofe_campaign/`
- Milestone 2 generator infrastructure:
  - `/home/workdir/wepppy/wepppy/wepp/fuzzing/seeded_soil_landuse_generators.py`
  - `/home/workdir/wepppy/wepppy/wepp/fuzzing/single_ofe_stratified_campaign.py`

### Blocks

- Missing runtime dependencies for compose-backed campaign/test execution.
- Insufficient signal variance even under elevated mutation pressure.

## Timeline Estimate

- **Expected duration**: 2-6 days.
- **Complexity**: High.
- **Risk level**: High.

## Security Impact and Review Gate

- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: model-input generation/execution controls only.
- **Security review artifact**: `N/A`

## Deliverables

- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone4-single-ofe-boundary-amplification/tracker.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone4-single-ofe-boundary-amplification/prompts/active/milestone4_single_ofe_boundary_amplification_execplan.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone4-single-ofe-boundary-amplification/artifacts/command_log.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone4-single-ofe-boundary-amplification/artifacts/mutation_pressure_plan.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone4-single-ofe-boundary-amplification/artifacts/yield_targets.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone4-single-ofe-boundary-amplification/notes/review_*.md`

## Follow-up Work

- Milestone 5: single-OFE patch closure and regression consolidation from M4 queue.
- Milestone 6: gated multi-OFE fuzzing pilot (only after M5 exit criteria).

## Closure Notes

To be completed when package is closed.
