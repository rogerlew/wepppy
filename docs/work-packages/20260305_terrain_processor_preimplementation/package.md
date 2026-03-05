# TerrainProcessor Pre-Implementation Foundations

**Status**: Closed 2026-03-05

## Overview
This package reduces implementation friction for the future TerrainProcessor by pre-implementing high-value helper functions and contracts in `wepppy/topo/wbt` before the full orchestrator is built. The focus is to ship stable, test-covered primitives that match the current concept document and can be reused directly when the TerrainProcessor work-package starts.

## Objectives
- Pre-implement reusable flow, conditioning, culvert, and multi-outlet helpers described in `terrain_processor.concept.md`.
- Add targeted tests and review gates per phase so each helper lands with behavior guarantees.
- Keep `terrain_processor.concept.md` synchronized with shipped capabilities and function-level status.
- Produce implementation artifacts that future TerrainProcessor planning can reference directly.

## Scope

### Included
- Flow-stack facade helper around existing WBT emulator primitives.
- Bounded-breach helper and mask/composite utilities.
- Culvert-prep geometry helpers and `burn_streams_at_roads` adapter wrapper.
- Multi-outlet snap/unnest parsing helpers and basin summary dataclasses.
- Artifact/provenance and phase-invalidation support scaffolding.
- Per-phase tests, reviews, and concept-doc updates.

### Explicitly Out of Scope
- Full `TerrainProcessor` orchestrator class implementation.
- Frontend workflow implementation for phase-by-phase map review.
- End-to-end WEPP run launch orchestration from TerrainProcessor outputs.

## Stakeholders
- **Primary**: maintainers implementing TerrainProcessor execution logic.
- **Reviewers**: `wepppy/topo/wbt` maintainers and testing maintainers.
- **Informed**: WEPPcloud terrain preprocessing and watershed delineation maintainers.

## Success Criteria
- [x] Multi-phase pre-implementation ExecPlan is active and fully scoped.
- [x] Each planned helper phase lands with dedicated tests and passes required gates.
- [x] Each completed phase updates `wepppy/topo/wbt/terrain_processor.concept.md` with shipped functionality notes.
- [x] Reviewer + test-quality findings are resolved per phase before progressing.
- [x] The package leaves a clear low-friction handoff for full TerrainProcessor implementation.

## Dependencies

### Prerequisites
- Existing concept source: `wepppy/topo/wbt/terrain_processor.concept.md`.
- Existing WBT primitives in `wepppy/topo/wbt/wbt_topaz_emulator.py`.
- OSM roads module from `docs/work-packages/20260304_osm_roads_client_cache/`.

### Blocks
- Full TerrainProcessor implementation work-package.

## Related Packages
- **Depends on**: [20260304_osm_roads_client_cache](../20260304_osm_roads_client_cache/package.md)
- **Follow-up**: Full TerrainProcessor implementation package (to be created after this package closes)

## Timeline Estimate
- **Expected duration**: 1-2 weeks
- **Complexity**: High
- **Risk level**: Medium

## References
- `wepppy/topo/wbt/terrain_processor.concept.md` - source concept and function targets
- `wepppy/topo/wbt/wbt_topaz_emulator.py` - existing WBT-backed primitives
- `wepppy/topo/watershed_abstraction/support.py` - shared polygonization/projection helpers
- `docs/prompt_templates/codex_exec_plans.md` - ExecPlan standard
- `AGENTS.md` - repository guardrails and active ExecPlan policy

## Deliverables
- Pre-implementation helper modules/functions in `wepppy/topo/wbt/`.
- New targeted test suites for each helper phase.
- Updated `terrain_processor.concept.md` status notes per delivered phase.
- Package artifacts capturing phase reviews and validation results.

## Follow-up Work
- Build the full TerrainProcessor orchestrator using these helpers.
- Wire UI and run-launch flows to the finalized orchestrator.
