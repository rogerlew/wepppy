# Prompt: Execute TerrainProcessor Follow-Up Tasks 1-6 End-to-End

You are implementing TerrainProcessor follow-up work for Tasks 1-6.

## Mandatory startup
1. Read `/workdir/wepppy/AGENTS.md`.
2. Read `/workdir/wepppy/docs/work-packages/20260305_terrain_processor_implementation/package.md`.
3. Read `/workdir/wepppy/docs/work-packages/20260305_terrain_processor_implementation/tracker.md`.
4. Read `/workdir/wepppy/docs/work-packages/20260305_terrain_processor_implementation/prompts/active/terrain_processor_followups_execplan.md`.
5. Read `/workdir/wepppy/wepppy/topo/wbt/terrain_processor.concept.md`.
6. Read `/workdir/wepppy/wepppy/topo/wbt/terrain_processor.py`.

## Execution rule
Follow the active ExecPlan milestone-by-milestone. Keep plan `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` synchronized while implementing.

## Required scope
1. BLC knob implementation (`blc_max_cost`, `blc_fill`) in runtime/helper/emulator contracts.
2. Real WBT integration test coverage for TerrainProcessor behavior.
3. Visualization benchmark + guardrail implementation.
4. UI-consumable visualization payload wiring.
5. Watershed controller/API surface for terrain config/run/artifact access.
6. Concept/work-package synchronization and validation evidence.

## Required outputs
- Updated runtime/helper/emulator implementations in `wepppy/topo/wbt/`.
- New/updated tests under `tests/topo/` and `tests/weppcloud/`.
- Updated route/API surface in `wepppy/weppcloud/routes/nodb_api/watershed_bp.py`.
- Updated concept + package docs and follow-up validation artifacts.

## Required gates
- `wctl run-pytest tests/topo/test_terrain_processor_helpers.py tests/topo/test_terrain_processor_runtime.py -q`
- `wctl run-pytest tests/topo/test_terrain_processor_wbt_integration.py -q`
- `wctl run-pytest tests/weppcloud/test_watershed_sub_intersection.py tests/weppcloud/test_watershed_terrain_processor_api.py -q`
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- `python3 tools/code_quality_observability.py --base-ref origin/master`
- `wctl doc-lint --path wepppy/topo/wbt/terrain_processor.concept.md`
- `wctl doc-lint --path docs/work-packages/20260305_terrain_processor_implementation`

## Final sweep
- `wctl run-pytest tests/topo --maxfail=1 -q`
- `wctl run-pytest tests/weppcloud --maxfail=1 -q`

## Handoff format
Provide:
1. Task-by-task summary (1-6) of delivered behavior.
2. Files changed grouped by runtime/tests/routes/docs.
3. Commands run and key outcomes.
4. Review findings and fixes.
5. Remaining risks and recommended next steps.
