# Prompt: Execute TerrainProcessor Runtime + Visualization Artifact Package End-to-End

You are implementing the full TerrainProcessor backend runtime package.

## Mandatory startup
1. Read `/workdir/wepppy/AGENTS.md`.
2. Read `/workdir/wepppy/docs/work-packages/20260305_terrain_processor_implementation/package.md`.
3. Read `/workdir/wepppy/docs/work-packages/20260305_terrain_processor_implementation/tracker.md`.
4. Read `/workdir/wepppy/docs/work-packages/20260305_terrain_processor_implementation/prompts/completed/terrain_processor_implementation_execplan.md`.
5. Read `/workdir/wepppy/wepppy/topo/wbt/terrain_processor.concept.md`.
6. Read `/workdir/wepppy/wepppy/topo/wbt/terrain_processor_helpers.py`.

## Execution rule
Follow the ExecPlan phase-by-phase. Do not skip tests, reviews, concept synchronization, or visualization artifact requirements.

## Scope guardrail
Implement backend runtime + visualization artifact generation only.

UI design and implementation are explicitly out of scope for this package and must not be implemented here.

## Required outputs
- Runtime TerrainProcessor implementation in `wepppy/topo/wbt/`.
- Visualization artifact generation + manifest contracts for all applicable phases.
- New/updated targeted tests under `tests/topo/`.
- `terrain_processor.concept.md` updates reflecting shipped runtime behavior.
- Per-phase review and validation artifacts in package `artifacts/`.

## Required per-phase gates
- Targeted phase pytest suite(s) pass.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` passes.
- `python3 tools/code_quality_observability.py --base-ref origin/master` report generated and reviewed.
- Correctness, maintainability, and test-quality findings resolved.
- `wctl doc-lint --path wepppy/topo/wbt/terrain_processor.concept.md` passes.

## Final gates
- `wctl run-pytest tests/topo --maxfail=1`
- `wctl doc-lint --path docs/work-packages/20260305_terrain_processor_implementation`

## Handoff format
Provide:
1. Phase-by-phase summary of runtime and visualization functionality delivered.
2. Files changed per phase.
3. Commands run and key outputs.
4. Review findings and resolutions.
5. Remaining risks and follow-up recommendations (including independent UI package dependencies).
