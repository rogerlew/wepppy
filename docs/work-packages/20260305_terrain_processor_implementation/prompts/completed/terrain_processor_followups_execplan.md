# TerrainProcessor Follow-Up Implementation (Tasks 1-6)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this follow-up package, WEPPcloud maintainers can run TerrainProcessor with full breach-least-cost controls, validate behavior against real WhiteboxTools runs, consume visualization outputs through UI-ready API payloads, and drive execution through watershed API endpoints. This closes the major runtime-to-UI integration gap that remained after the original backend runtime shipment.

## Progress

- [x] (2026-03-05 23:45Z) Re-activated work package with new active ExecPlan and run prompt for Tasks 1-6.
- [x] (2026-03-06 00:20Z) Task 1 complete: implemented BLC pass-through (`blc_max_cost`, `blc_fill`) in runtime/helper/emulator with regression tests.
- [x] (2026-03-06 00:25Z) Task 2 complete: added real WBT integration suite `tests/topo/test_terrain_processor_wbt_integration.py`.
- [x] (2026-03-06 00:30Z) Task 3 complete: added visualization benchmark artifact + raster-size guardrail (`visualization_max_pixels`).
- [x] (2026-03-06 00:35Z) Task 4 complete: added runtime UI payload artifact (`visualization_ui_payload.json`) and URL-ready relative paths.
- [x] (2026-03-06 00:40Z) Task 5 complete: added watershed terrain config/run/result/manifest/resource API surface.
- [x] (2026-03-06 00:45Z) Task 6 complete: synchronized concept/work-package/tracker docs with follow-up behavior.
- [x] (2026-03-06 00:50Z) Targeted and final validation gates completed for topo + weppcloud changes.

## Surprises & Discoveries

- Observation: Real `unnest_basins` WhiteboxTools signatures differ from the prior runtime assumption and do not accept a `hierarchy=` keyword.
  Evidence: Container signature inspection showed `unnest_basins(d8_pntr, pour_pts, output, esri_pntr=False, ...)`.

- Observation: `parse_request_payload` can coerce single-item lists to scalar values, which is risky for terrain config list fields.
  Evidence: `_normalise_payload_value` in `routes/_common.py` returns the sole list element when `len(normalised) == 1`; terrain endpoints now prefer JSON body parsing first.

## Decision Log

- Decision: Re-open the same work-package and track Tasks 1-6 as a follow-up cycle rather than creating a new package id.
  Rationale: The follow-up work directly extends the same runtime module, tests, and concept contract.
  Date/Author: 2026-03-05 / Codex.

- Decision: Implement UI-facing output contracts via backend API payload transformation rather than embedding WEPPcloud URL semantics directly inside `TerrainProcessor` core runtime.
  Rationale: Keeps runtime reusable outside Flask while still providing immediate UI integration.
  Date/Author: 2026-03-05 / Codex.

- Decision: Persist terrain config/result as workspace JSON sidecars rather than introducing a new NoDb controller in this follow-up.
  Rationale: Fastest low-risk path to route-level integration while preserving deterministic state under run workspace.
  Date/Author: 2026-03-06 / Codex.

- Decision: Add compatibility handling for `unnest_basins` runners that do not accept `hierarchy=` and detect sidecar CSV paths heuristically.
  Rationale: Aligns runtime with observed real WBT signatures and avoids false contract failures.
  Date/Author: 2026-03-06 / Codex.

## Outcomes & Retrospective

Completed outcome:
- All Tasks 1-6 were implemented in the active follow-up cycle.
- Runtime now supports full breach-least-cost control surface (`blc_dist_m`, `blc_max_cost`, `blc_fill`) with tested helper/emulator/runtime plumbing.
- Visualization phase now emits benchmark and UI payload artifacts and enforces a configurable pixel guardrail.
- Watershed blueprint now exposes terrain config/run/result/manifest/resource endpoints with route-safe artifact URL generation.
- Real WBT integration tests and new weppcloud route tests were added and pass.

Residual gap:
- Full frontend workflow/UI implementation remains intentionally out of scope; backend contracts are now available for that follow-up.

Lesson learned:
- Keeping runtime payloads filesystem-relative and attaching URLs at route boundaries preserved separation of concerns while still enabling immediate UI integration.

## Context and Orientation

Baseline runtime implementation already exists in `wepppy/topo/wbt/terrain_processor.py` with six phases, artifact tracking, and visualization manifest generation. Helper contracts and bounded-breach utilities live in `wepppy/topo/wbt/terrain_processor_helpers.py`. WhiteboxTools conditioning primitives are exposed through `wepppy/topo/wbt/wbt_topaz_emulator.py`. Existing runtime tests are concentrated in `tests/topo/test_terrain_processor_runtime.py`, and helper tests are in `tests/topo/test_terrain_processor_helpers.py`.

This follow-up added route/API integration in `wepppy/weppcloud/routes/nodb_api/watershed_bp.py`, plus UI-payload and artifact URL wiring that clients can consume directly.

## Plan of Work

1. Extend WhiteboxTools relief plumbing so breach-least-cost controls are first-class: add `blc_max_cost` and `blc_fill` pass-through support in emulator and helper flow-stack facade, then consume it in runtime phase 2/3 calls.
2. Replace runtime validation blockers that reject those controls, and add regression tests that assert proper pass-through behavior.
3. Add visualization workload telemetry and guardrails in phase 5: benchmark JSON output and maximum-raster-size checks to prevent unbounded expensive processing.
4. Add a UI-facing visualization payload contract generated from phase-5 manifest entries, including stable relative artifact paths for route serving.
5. Extend watershed blueprint with TerrainProcessor endpoints for reading/updating config, running terrain processing, reading latest results/manifest payloads, and streaming generated artifacts safely.
6. Add dedicated tests for new route/API behavior and add at least one real WBT integration test path for TerrainProcessor runtime.
7. Synchronize concept + package docs and run the required validation gates.

## Concrete Steps

From `/workdir/wepppy`:

1. Implement runtime/helper/emulator changes and unit tests:

    wctl run-pytest tests/topo/test_terrain_processor_helpers.py tests/topo/test_terrain_processor_runtime.py -q

2. Add and run real WBT integration tests:

    wctl run-pytest tests/topo/test_terrain_processor_wbt_integration.py -q

3. Add and run watershed route tests:

    wctl run-pytest tests/weppcloud/test_watershed_sub_intersection.py tests/weppcloud/test_watershed_terrain_processor_api.py -q

4. Run quality gates for changed files:

    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master

5. Run docs lint for affected concept and package docs:

    wctl doc-lint --path wepppy/topo/wbt/terrain_processor.concept.md
    wctl doc-lint --path docs/work-packages/20260305_terrain_processor_implementation

6. Final focused regression sweeps:

    wctl run-pytest tests/topo --maxfail=1 -q
    wctl run-pytest tests/weppcloud --maxfail=1 -q

## Validation and Acceptance

Acceptance is met when:

- `blc_max_cost` and `blc_fill` are accepted by runtime config and demonstrably passed to breach-least-cost execution paths.
- Visualization phase emits benchmark + UI-consumable manifest payload artifacts and rejects oversize rasters with a typed runtime error.
- Watershed API can persist TerrainProcessor config, execute runs, and return artifact payloads with route-served URLs.
- New topo and route tests pass, including real WBT integration coverage.
- Concept/work-package docs describe shipped behavior (no stale "unsupported" runtime notes).

## Idempotence and Recovery

- TerrainProcessor route execution writes into a deterministic workspace under the run directory and can be re-run safely.
- Config persistence is file-backed and overwritten atomically through JSON writes.
- If an API run fails, previous successful result payload remains available for inspection.

## Artifacts and Notes

Follow-up implementation evidence will be captured in:

- `docs/work-packages/20260305_terrain_processor_implementation/artifacts/phase1_6_followup_review.md`
- `docs/work-packages/20260305_terrain_processor_implementation/artifacts/followup_validation_summary.md`

## Interfaces and Dependencies

- Runtime core: `wepppy.topo.wbt.terrain_processor::TerrainProcessor`
- Flow helper facade: `wepppy.topo.wbt.terrain_processor_helpers::derive_flow_stack`
- WBT relief adapter: `wepppy.topo.wbt.wbt_topaz_emulator::WhiteboxToolsTopazEmulator._create_relief`
- API surface: `wepppy.weppcloud.routes.nodb_api.watershed_bp`
- No new external dependencies.

---
Revision Note (2026-03-06, Codex): Completed the Tasks 1-6 follow-up implementation and updated this ExecPlan with delivered outcomes, validation evidence, and final decisions.
