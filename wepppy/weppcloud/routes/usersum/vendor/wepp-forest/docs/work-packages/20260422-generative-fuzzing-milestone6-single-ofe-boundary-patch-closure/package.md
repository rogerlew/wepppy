# Generative Inputs Fuzzing Milestone 6: Single-OFE Boundary Patch Closure

**Status**: Open (2026-04-22 UTC)
**Timezone**: UTC

## Overview

Milestone 5 established calibrated campaign sensitivity (`5/5` controls detected)
and produced composite non-pass yield (`140` oracle-flagged cases out of
`1008` executed). Milestone 6 converts that queue into patch-ready boundary
closure by separating true numeric instability from oracle noise, minimizing
reproducers, and landing targeted single-OFE fixes.

## Objectives

- Triage `ORACLE_TOKEN_ANOMALY` cases into patchable numeric instability vs
  benign/low-signal contexts.
- Build deterministic minimized reproducer sets for highest-yield slices.
- Implement and validate single-OFE boundary fixes in prioritized routines.
- Re-run calibrated campaign and measure post-patch reduction with sensitivity
  gate preserved.

## Scope

### Included

- Oracle-noise triage taxonomy and evidence-backed case labeling.
- Reproducer minimization workflow and stable repro manifests.
- Targeted single-OFE patch lanes in WEPP input boundary surfaces.
- Before/after campaign comparison for composite non-pass rates.
- Updated queue disposition with patched/remaining/unknown statuses.

### Explicitly Out of Scope

- Multi-OFE campaign execution.
- Broad multi-year scientific parity certification.
- Non-fuzzing product feature work.

## Normative Constraints

1. Single-OFE hard scope
- Execute only single-OFE campaign cases.
- Keep multi-OFE seeds quarantined.

2. Rosetta contract is mandatory
- Host and container runtime must provide `from rosetta import Rosetta3`.
- Campaign execution must fail fast if Rosetta is unavailable.

3. Preserve calibration contract
- Positive-control sensitivity gate remains required for every run.
- Secondary oracle outputs remain persisted and included in composite disposition.

4. Priority focus order
- Prioritize highest-yield bins from Milestone 5:
  - `wet/moderate`, `wet/steep`, `dry/steep`.
- Prioritize highest-yield mutation profiles:
  - `P5_SLOPE_RESPONSE_AMPLIFICATION`, `P2_EVENT_EDGE`,
    `P4_TEXTURE_DENSITY_DISCONTINUITY`.

5. Evidence-backed closure only
- Each claimed closure must map to:
  - repro case(s),
  - patch commit path,
  - post-patch rerun evidence.

## Success Criteria

- [ ] Oracle triage plan completed with labeled `140`-case queue and rationale.
- [ ] Minimized reproducible subset generated for top-priority slices.
- [ ] Targeted boundary fixes implemented with regression coverage.
- [ ] Post-patch calibrated rerun executed with sensitivity gate pass.
- [ ] Composite non-pass reduction demonstrated or explicitly blocked with analysis.
- [ ] Milestone 0/1/2/3/4/5 required gates remain green.

## Dependencies

### Prerequisites

- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone5-single-ofe-sensitivity-calibration/`
- `/home/workdir/wepp-forest/generative-inputs-fuzzing/results/milestone5_single_ofe_campaign/`
- `/home/workdir/wepppy/wepppy/wepp/fuzzing/single_ofe_stratified_campaign.py`
- `/home/workdir/wepppy/wepppy/wepp/soils/utils/wepp_soil_util.py`

### Blocks

- Inability to reproduce queued anomalies deterministically.
- Runtime dependency drift (especially Rosetta host/container mismatch).

## Timeline Estimate

- **Expected duration**: 3-8 days.
- **Complexity**: High.
- **Risk level**: High.

## Security Impact and Review Gate

- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: fuzzing and numeric-stability boundary hardening only.
- **Security review artifact**: `N/A`

## Deliverables

- `/home/workdir/wepp-forest/docs/work-packages/20260422-generative-fuzzing-milestone6-single-ofe-boundary-patch-closure/tracker.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260422-generative-fuzzing-milestone6-single-ofe-boundary-patch-closure/prompts/active/milestone6_single_ofe_boundary_patch_closure_execplan.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260422-generative-fuzzing-milestone6-single-ofe-boundary-patch-closure/artifacts/command_log.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260422-generative-fuzzing-milestone6-single-ofe-boundary-patch-closure/artifacts/oracle_noise_triage_plan.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260422-generative-fuzzing-milestone6-single-ofe-boundary-patch-closure/artifacts/repro_minimization_plan.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260422-generative-fuzzing-milestone6-single-ofe-boundary-patch-closure/artifacts/patch_closure_criteria.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260422-generative-fuzzing-milestone6-single-ofe-boundary-patch-closure/notes/review_*.md`

## Follow-up Work

- Milestone 7: single-OFE confidence consolidation and closure memo.
- Milestone 8: gated multi-OFE pilot after single-OFE closure criteria pass.

## Closure Notes

To be completed when package is closed.
