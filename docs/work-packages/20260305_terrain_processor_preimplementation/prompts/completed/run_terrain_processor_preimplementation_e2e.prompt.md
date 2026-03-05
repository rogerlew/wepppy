# Prompt: Execute TerrainProcessor Pre-Implementation Package End-to-End

You are implementing the phased pre-implementation package for TerrainProcessor helper functions.

## Mandatory startup
1. Read `/workdir/wepppy/AGENTS.md`.
2. Read `/workdir/wepppy/docs/work-packages/20260305_terrain_processor_preimplementation/package.md`.
3. Read `/workdir/wepppy/docs/work-packages/20260305_terrain_processor_preimplementation/tracker.md`.
4. Read `/workdir/wepppy/docs/work-packages/20260305_terrain_processor_preimplementation/prompts/active/terrain_processor_preimplementation_execplan.md`.
5. Read `/workdir/wepppy/wepppy/topo/wbt/terrain_processor.concept.md`.

## Execution rule
Follow the active ExecPlan phase-by-phase. Do not skip tests, reviews, or concept-document updates for any phase.

## Goal
Reduce friction for future TerrainProcessor implementation by delivering reusable helper functions now, with:
- phase-scoped implementation,
- phase-scoped tests,
- phase-scoped reviews,
- phase-scoped concept synchronization.

## Required outputs
- Helper implementations in `wepppy/topo/wbt/` aligned to concept phases.
- New/updated targeted tests under `tests/topo/`.
- `terrain_processor.concept.md` updates reflecting shipped helper behavior after each phase.
- Work-package artifacts documenting review findings and validation evidence.

## Required per-phase gates
- Targeted phase pytest suite(s) pass.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` passes.
- `python3 tools/code_quality_observability.py --base-ref origin/master` report generated and reviewed.
- Reviewer and test-quality findings resolved.
- `wctl doc-lint --path wepppy/topo/wbt/terrain_processor.concept.md` passes after concept update.

## Final gates
- `wctl run-pytest tests/topo --maxfail=1`
- `wctl doc-lint --path docs/work-packages/20260305_terrain_processor_preimplementation`

## Review requirements
Before handoff, perform:
1. Correctness review for each phase’s helper contracts.
2. Maintainability review for helper boundaries and error contracts.
3. Test quality review for fixtures, coverage, and failure clarity.

## Handoff format
Provide:
1. Phase-by-phase summary of completed helper functionality.
2. Files changed per phase.
3. Commands run and key outputs.
4. Review findings and how they were resolved.
5. Remaining risks and follow-up recommendations for full TerrainProcessor implementation.
