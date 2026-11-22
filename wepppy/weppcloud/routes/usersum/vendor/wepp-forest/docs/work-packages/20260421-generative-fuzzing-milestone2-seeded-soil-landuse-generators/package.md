# Generative Inputs Fuzzing Milestone 2: Seeded Soil/Landuse Generators

**Status**: Open (2026-04-21 UTC)
**Timezone**: UTC

## Overview

Milestone 1 delivered wrapper property contracts. Milestone 2 builds the first
seeded generator system for WEPP inputs with emphasis on:

- using existing `wepppy` soil and management tooling,
- seeding from real project run artifacts,
- keeping physical/contract invariants intentionally loose so `wepp-forest`
  can encounter boundary behavior instead of being over-sanitized.

## Objectives

- Implement constrained-but-loose generators for soil and landuse inputs.
- Use real run artifacts (`*.sol`, `*.man`, `*.slp`, `*.cli`) as seed corpus.
- Reuse `wepppy` tooling rather than building parallel parsers:
  - `wepppy.wepp.soils.utils.WeppSoilUtil`
  - `wepppy.wepp.soils.utils.SoilMultipleOfeSynth`
  - `wepppy.wepp.management.managements` and `data/*` catalogs.
- Define soft invariants (warn/classify), not strict reject filters, for
  physical plausibility boundaries.
- Produce generator outputs compatible with Milestone 0 signature-classification
  and Milestone 3 campaign scaling.

## Scope

### Included

- Seed-corpus curation plan from `/wc1/runs/**/wepp/runs/`.
- Generator implementation for:
  - `soil` (`.sol`) mutation/synthesis,
  - `landuse/management` (`.man`) mutation/synthesis,
  - slope/climate borrowing strategy (`.slp`, `.cli`) from existing runs.
- Soft invariant taxonomy and severity levels (`info`, `warn`, `hard-fail`).
- Pilot generation run (small batch) with artifacted outputs and metadata.

### Explicitly Out of Scope

- Full high-volume fuzz campaign execution (Milestone 3).
- Fortran guard changes.
- Tight scientific validity filters that block boundary exploration.

## Key Design Decisions (Normative)

1. Seed-first generation
- Start from real production-like run inputs from `/wc1/runs/**/wepp/runs/`.
- Mutation and recombination happen on top of real seed files, not synthetic
  files from scratch as default mode.

2. Loose invariants by policy
- Physical plausibility checks should be mostly advisory (`warn`) in Milestone 2.
- Only parser/format violations and impossible structural contracts are
  `hard-fail`.

3. Tolerance preference for `wepp-forest`
- Do not pre-filter aggressively to avoid SGFPE boundaries.
- Prefer generating plausible-but-pathological inputs and let trap-enabled WEPP
  classify behavior.

4. Slope/climate integration
- For Milestone 2, slope/climate are borrowed from seed runs and treated as
  stable context files.
- Soil/landuse variation is primary in this milestone.

## Data Sources

- Run artifact seeds:
  - `/wc1/runs/**/wepp/runs/*.sol`
  - `/wc1/runs/**/wepp/runs/*.man`
  - `/wc1/runs/**/wepp/runs/*.slp`
  - `/wc1/runs/**/wepp/runs/*.cli`
- Management catalogs:
  - `/home/workdir/wepppy/wepppy/wepp/management/data/`
  - `/home/workdir/wepppy/wepppy/wepp/management/managements.py`
- Soil tooling:
  - `/home/workdir/wepppy/wepppy/wepp/soils/utils/wepp_soil_util.py`
  - `/home/workdir/wepppy/wepppy/wepp/soils/utils/multi_ofe.py`

## Success Criteria

- [x] Seed corpus inventory created with provenance and sampling strategy.
- [x] Soil/landuse generators implemented using existing `wepppy` tooling.
- [x] Soft-invariant policy documented and enforced in generator metadata.
- [x] Pilot batch generated with reproducible seed IDs and mutation metadata.
- [x] Generated cases are consumable by Milestone 0 classifier workflow.
- [x] Package evidence (`tracker`, command log, inventory/review notes) complete.

## Dependencies

### Prerequisites

- Milestone 1 package completion:
  - `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone1-wrapper-properties/`
- Milestone 0 classifier and schema:
  - `/home/workdir/wepp-forest/generative-inputs-fuzzing/scripts/classify_signatures.py`
  - `/home/workdir/wepp-forest/generative-inputs-fuzzing/specs/canonical_result_schema.md`

### Blocks

- Access issues to `/wc1/runs` seed corpus.
- Missing compose-backed dependencies for `wepppy` gated tests.

## Timeline Estimate

- **Expected duration**: 2-5 days.
- **Complexity**: High.
- **Risk level**: Medium-high.

## Security Impact and Review Gate

- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: generator/test tooling and seed-corpus operations only.
- **Security review artifact**: `N/A`

## Deliverables

- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone2-seeded-soil-landuse-generators/tracker.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone2-seeded-soil-landuse-generators/prompts/active/milestone2_seeded_generator_execplan.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone2-seeded-soil-landuse-generators/artifacts/command_log.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone2-seeded-soil-landuse-generators/artifacts/seed_inventory.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone2-seeded-soil-landuse-generators/notes/review_*.md`

## Follow-up Work

- Milestone 3: scale campaigns, sharding, clustering, and minimization.
- Milestone 4: routine-by-routine closure and regression conversion.

## Closure Notes

Milestone 2 implementation completed on 2026-04-21 UTC with generator code in
`wepppy`, pilot outputs in `generative-inputs-fuzzing/results/`, and required
Milestone 0/Milestone 1 compatibility gates passing. One sampled seed case is
explicitly classified as structural `hard_fail` due parser-invalid source
management input (`invalid literal for int() with base 10: '2.0'`), consistent
with Milestone 2 hard-fail policy.
