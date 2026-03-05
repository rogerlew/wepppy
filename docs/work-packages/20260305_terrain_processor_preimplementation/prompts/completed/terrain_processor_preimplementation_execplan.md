# TerrainProcessor Pre-Implementation Helpers (Phased)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

The future TerrainProcessor implementation is blocked by missing helper-level building blocks. This plan delivers those helpers first, with tests and reviews per phase, so the eventual TerrainProcessor package can focus on orchestration and UI workflow instead of low-level utility construction.

After completion, maintainers can assemble TerrainProcessor behavior from existing, validated primitives with lower implementation risk and faster iteration.

## Progress

- [x] (2026-03-05 04:20Z) Created work-package scaffold and authored active ExecPlan.
- [x] (2026-03-05 04:20Z) Added active execution prompt and tracker wiring.
- [x] (2026-03-05 06:40Z) Phase 1 complete: flow-stack facade helper, tests, review, and concept synchronization landed.
- [x] (2026-03-05 06:48Z) Phase 2 complete: bounded-breach helper set, edge-case tests, review, and concept synchronization landed.
- [x] (2026-03-05 06:58Z) Phase 3 complete: culvert geometry + burn adapter helpers, typed errors, review, and concept synchronization landed.
- [x] (2026-03-05 07:06Z) Phase 4 complete: multi-outlet snap + unnest parser/dataclass helpers, schema-hardening fixes, and concept synchronization landed.
- [x] (2026-03-05 07:13Z) Phase 5 complete: provenance/artifact/invalidation scaffolding with rule and coverage hardening landed.
- [x] (2026-03-05 07:19Z) Final validation, package closeout artifacts, and execution prompt archival completed.

## Surprises & Discoveries

- Observation: Many flow-stack primitives already exist in `WhiteboxToolsTopazEmulator` but are not packaged as reusable TerrainProcessor-oriented helpers.
  Evidence: `wepppy/topo/wbt/wbt_topaz_emulator.py` exposes `_create_relief`, `_create_flow_vector`, `_create_flow_accumulation`, `_extract_streams`, `_identify_stream_junctions`, and `set_outlet`.

- Observation: The concept file already names function-level seams, which can be converted into implementation contracts without introducing speculative abstractions.
  Evidence: `wepppy/topo/wbt/terrain_processor.concept.md` Phase 1-4 function call blocks.

- Observation: `UnnestBasins` hierarchy outputs use `outlet_id` / `parent_outlet_id` and `row` / `column` naming in practice; parser support needed to cover both conceptual and WBT-native schemas.
  Evidence: reviewer finding resolved by widening aliases in `parse_unnest_basins_hierarchy_csv(...)` and adding WBT-schema regression tests.

- Observation: typed helper-error contracts needed stricter boundary wrapping to prevent raw JSON/geometry exceptions from leaking.
  Evidence: maintainability review finding resolved by wrapping GeoJSON file/JSON decode and geometry-intersection errors as `GeometryInputError` / `CulvertSnapError`.

## Decision Log

- Decision: Sequence work as helper-first phases and defer full orchestrator implementation.
  Rationale: Minimizes scope risk and ensures reusable, testable foundations before orchestration complexity.
  Date/Author: 2026-03-05 / Codex.

- Decision: Require concept-document synchronization in every completed phase.
  Rationale: Avoids drift between planning language and shipped helper behavior.
  Date/Author: 2026-03-05 / Codex.

- Decision: Require sub-agent review and test-quality checks phase-by-phase.
  Rationale: Keeps quality control continuous instead of deferring defects to final integration.
  Date/Author: 2026-03-05 / Codex.

- Decision: Harden helper contracts in response to review findings rather than documenting limitations.
  Rationale: The package goal is reusable low-friction primitives; unresolved boundary ambiguity would transfer risk to the full TerrainProcessor implementation package.
  Date/Author: 2026-03-05 / Codex.

- Decision: Treat flow-stack-driving config deltas (`conditioning`, `csa`, `mcl`, least-cost params) as phase-1 invalidators.
  Rationale: These settings affect phase-1 flow-stack artifacts directly and must invalidate from phase 1 to prevent stale outputs.
  Date/Author: 2026-03-05 / Codex.

## Outcomes & Retrospective

Delivered a complete helper-first TerrainProcessor pre-implementation foundation in `wepppy/topo/wbt/terrain_processor_helpers.py` with 34 dedicated helper tests and phase-by-phase review artifacts.

What was achieved:
- Phase 1-5 helper contracts implemented and validated.
- Concept document synchronized with shipped helper names and behavior.
- Per-phase tests, broad-exception checks, and observe-only quality reports executed.
- Correctness/maintainability/test-quality findings resolved before closeout.
- Package artifacts (`phase1_review.md` through `phase5_review.md`, `final_validation_summary.md`) published.

What remains:
- Full TerrainProcessor orchestrator assembly and UI execution workflow (explicitly out of scope for this package).

Lesson learned:
- Real WBT sidecar schemas and typed error-boundary behavior must be validated early with explicit tests to avoid late integration surprises.

## Context and Orientation

Primary targets:

- `wepppy/topo/wbt/terrain_processor.concept.md`
- `wepppy/topo/wbt/wbt_topaz_emulator.py`
- `wepppy/topo/wbt/` (new helper modules/functions to be added)
- `tests/topo/` (new test suites)

This package does not deliver a complete TerrainProcessor runtime class. It delivers helper-level components and contracts that future orchestration code will consume.

## Plan of Work

### Phase 1: Flow-stack Facade

Deliver a reusable helper that executes the concept flow-stack sequence from a clear input contract and returns typed artifact paths.

Scope:
- Implement helper wrapper around existing relief/flow/accum/stream/junction/polygonize primitives.
- Add unit/integration tests for call order, required preconditions, and artifact outputs.
- Update concept document with shipped helper signature, behavior notes, and status marker.

Sub-agent orchestration:
- `explorer`: map exact primitive reuse points and gaps.
- `worker`: implement helper and tests.
- `reviewer`: correctness review (call sequencing, WBT contract adherence).
- `test_guardian`: test quality review and fixture hygiene.

Acceptance:
- Focused tests pass.
- Reviewer and test-quality findings resolved.
- Concept doc updated for this phase.

### Phase 2: Bounded-Breach Helper

Deliver bounded-breach helper utilities from concept algorithm: fill pass, boundary mask logic, interior breach, and composite DEM selection.

Scope:
- Implement helper API for bounded-breach computation.
- Add tests for collar sizing, mask/composite behavior, and fallback edge cases.
- Update concept document with final helper contract and parameter semantics.

Sub-agent orchestration:
- `worker`: implementation + tests.
- `reviewer`: algorithm and raster semantics review.
- `qa_reviewer`: maintainability/readability review.

Acceptance:
- Focused tests pass.
- Reviewer findings resolved.
- Concept doc phase section updated.

### Phase 3: Culvert Prep + Burn Adapter

Deliver helper set for culvert preparation and burn execution:
- road-stream intersection extraction,
- upload-point loading and snapping to crossings,
- validated `burn_streams_at_roads` adapter wrapper.

Scope:
- Add geometry helper functions and adapter wrappers with explicit typed errors.
- Add tests for geometry filtering/snap behavior and burn-call parameter validation.
- Update concept document to mark helper availability and any contract clarifications.

Sub-agent orchestration:
- `worker`: implementation + tests.
- `reviewer`: geometry and adapter correctness.
- `test_guardian`: regression and fixture quality.

Acceptance:
- Targeted tests pass.
- Review findings resolved.
- Concept phase updated.

### Phase 4: Multi-Outlet and Unnest Parsing

Deliver helper utilities for multi-outlet mode:
- snap-outlet iteration helper,
- unnest-basins output parser,
- typed basin summary dataclasses.

Scope:
- Implement parser/helper contracts independent of full orchestrator.
- Add tests for hierarchy parsing, parent linkage, and malformed-output handling.
- Update concept document with concrete helper names and output structures.

Sub-agent orchestration:
- `worker`: implementation + tests.
- `reviewer`: parser correctness and contract safety.
- `qa_reviewer`: readability and maintainability review.

Acceptance:
- Focused tests pass.
- Review findings resolved.
- Concept phase updated.

### Phase 5: Provenance and Invalidation Scaffolding

Deliver shared structures for artifact registry, provenance entries, and phase-invalidation mapping from config deltas.

Scope:
- Implement lightweight dataclasses/helpers for provenance + invalidation rules.
- Add tests validating invalidation decisions and provenance record behavior.
- Update concept document to reflect shipped scaffolding and names.

Sub-agent orchestration:
- `worker`: implementation + tests.
- `reviewer`: correctness and integration risk review.
- `test_guardian`: test quality and coverage review.

Acceptance:
- Targeted tests pass.
- Review findings resolved.
- Concept doc updated.

## Concrete Steps

Run commands from `/workdir/wepppy`.

For each phase:

1. Implement helper code and tests for the phase scope.

    wctl run-pytest tests/topo -k <phase_keyword>

2. Run broad exception guard for changed files.

    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master

3. Run observe-only code-quality report.

    python3 tools/code_quality_observability.py --base-ref origin/master

4. Update concept document and lint docs.

    wctl doc-lint --path wepppy/topo/wbt/terrain_processor.concept.md
    wctl doc-lint --path docs/work-packages/20260305_terrain_processor_preimplementation

Final package validation:

    wctl run-pytest tests/topo --maxfail=1
    wctl doc-lint --path docs/work-packages/20260305_terrain_processor_preimplementation

## Validation and Acceptance

The package is accepted when:

- All five phases are complete with passing tests.
- Each phase has recorded review completion and resolved high/medium findings.
- `terrain_processor.concept.md` has per-phase shipped-function updates.
- Package tracker and ExecPlan living sections are fully synchronized.
- Prompts are archived from `prompts/active/` to `prompts/completed/` at closeout.

## Idempotence and Recovery

- Each phase should be delivered as additive helper modules/functions that do not require full orchestrator state.
- If a phase introduces regressions, revert only that phase’s scoped helper changes and re-run targeted tests.
- Keep per-phase artifacts in `artifacts/` so reviewers can restart from any milestone.

## Artifacts and Notes

Capture phase evidence under:

- `docs/work-packages/20260305_terrain_processor_preimplementation/artifacts/phase1_review.md`
- `docs/work-packages/20260305_terrain_processor_preimplementation/artifacts/phase2_review.md`
- `docs/work-packages/20260305_terrain_processor_preimplementation/artifacts/phase3_review.md`
- `docs/work-packages/20260305_terrain_processor_preimplementation/artifacts/phase4_review.md`
- `docs/work-packages/20260305_terrain_processor_preimplementation/artifacts/phase5_review.md`
- `docs/work-packages/20260305_terrain_processor_preimplementation/artifacts/final_validation_summary.md`

## Interfaces and Dependencies

Normative concept contract source:

- `wepppy/topo/wbt/terrain_processor.concept.md`

Implementation dependency anchors:

- `wepppy/topo/wbt/wbt_topaz_emulator.py`
- `wepppy/topo/watershed_abstraction/support.py`
- `wepppy/topo/wbt/osm_roads_consumer.py`

Avoid adding new external dependencies in this package.

---
Revision Note (2026-03-05, Codex): Initial ExecPlan for phased TerrainProcessor pre-implementation helper delivery with per-phase tests, reviews, and concept synchronization.
Revision Note (2026-03-05, Codex): Completed all five helper phases, resolved review findings, added phase/final validation evidence, synchronized concept/tracker artifacts, and archived the execution prompt.
