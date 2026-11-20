# Generative Inputs Fuzzing Milestone 3: Single-OFE Stratified Campaign

**Status**: Open (2026-04-21 UTC)
**Timezone**: UTC

## Overview

Milestone 2 established seeded soil/landuse generation with lineage metadata and
soft-invariant telemetry. Milestone 3 scales campaign execution with explicit
stratification requirements across climate and slope regimes while keeping scope
strictly limited to **single-OFE** runs.

This package prioritizes broad boundary discovery under controlled complexity:
- large seed pool across dry/wet climates,
- large seed pool across gradual/steep slopes,
- no multi-OFE fuzzing until single-OFE protocol is proven and single-OFE
  boundary patches are closed.

## Objectives

- Execute stratified single-OFE fuzzing campaigns at scale.
- Ensure coverage across climate moisture and slope steepness strata.
- Preserve seed lineage, mutation metadata, and invariant telemetry contracts.
- Integrate classifier-based signature clustering into campaign outputs.
- Produce prioritized single-OFE boundary findings for patch workflow.

## Scope

### Included

- Single-OFE seed preflight and quarantine for structurally invalid artifacts.
- Climate and slope stratification framework for seed sampling.
- Sharded campaign execution and aggregation.
- Signature clustering/deduplication using Milestone 0 classifier contracts.
- Evidence capture (coverage matrix, finding inventory, command transcripts).

### Explicitly Out of Scope

- Multi-OFE fuzzing generation/execution.
- Multi-OFE boundary triage and patching.
- Broad scientific parity adjudication.

## Normative Constraints

1. Single-OFE-only campaign
- Milestone 3 must only execute single-OFE cases.
- Multi-OFE seeds may be inventoried but must not be executed in campaign lanes.

2. Stratification is mandatory
- Sampling must cover both climate extremes and slope extremes.
- Minimum required dimensions:
  - climate bins: `dry`, `mesic`, `wet`
  - slope bins: `gradual`, `moderate`, `steep`
- Campaign evidence must include per-bin counts and executed-case counts.

3. Deferred multi-OFE expansion
- Multi-OFE fuzzing is explicitly deferred until:
  - single-OFE protocol and telemetry are stable,
  - significant single-OFE boundaries are patched and regression-covered.

## Success Criteria

- [x] Single-OFE preflight quarantine implemented and reported.
- [x] Stratified seed coverage matrix generated for climate/slope bins.
- [x] Campaign executes at target scale with reproducible shards.
- [x] Signature clustering report produced with deduplicated keys.
- [x] Top single-OFE failure boundaries triaged into patch-ready queue artifact.
- [x] Milestone 0/1/2 regression gates remain green.

## Dependencies

### Prerequisites

- Milestone 2 package outputs:
  - `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone2-seeded-soil-landuse-generators/`
  - `/home/workdir/wepp-forest/generative-inputs-fuzzing/results/milestone2_seeded_pilot/`
- Milestone 0 classifier contract:
  - `/home/workdir/wepp-forest/generative-inputs-fuzzing/scripts/classify_signatures.py`
  - `/home/workdir/wepp-forest/generative-inputs-fuzzing/specs/canonical_result_schema.md`

### Blocks

- Missing or low-diversity climate/slope signals in seed corpus metadata.
- Compose/runtime dependency failures in campaign execution environment.

## Timeline Estimate

- **Expected duration**: 3-7 days.
- **Complexity**: High.
- **Risk level**: High.

## Security Impact and Review Gate

- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: model-input generation/execution and evidence collection only.
- **Security review artifact**: `N/A`

## References

- `/home/workdir/wepp-forest/generative-inputs-fuzzing/README.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone2-seeded-soil-landuse-generators/package.md`
- `/home/workdir/wepppy/wepppy/wepp/fuzzing/seeded_soil_landuse_generators.py`
- `/home/workdir/wepppy/wepppy/wepp/soils/utils/wepp_soil_util.py`
- `/home/workdir/wepppy/wepppy/wepp/management/managements.py`

## Deliverables

- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone3-single-ofe-stratified-campaign/tracker.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone3-single-ofe-stratified-campaign/prompts/active/milestone3_single_ofe_stratified_execplan.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone3-single-ofe-stratified-campaign/artifacts/command_log.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone3-single-ofe-stratified-campaign/artifacts/stratification_plan.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone3-single-ofe-stratified-campaign/artifacts/coverage_matrix.csv`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone3-single-ofe-stratified-campaign/notes/review_*.md`

## Follow-up Work

- Milestone 4: single-OFE boundary patch closure and regression consolidation.
- Milestone 5: multi-OFE fuzzing expansion (only after Milestone 4 exit criteria).

## Closure Notes

To be completed when package is closed.
