# Phase 1-6 Follow-Up Review

## Scope

Follow-up Tasks 1-6 for TerrainProcessor runtime/UI-integration closure:

1. BLC knob pass-through (`blc_max_cost`, `blc_fill`)
2. Real WBT integration coverage
3. Visualization benchmark + guardrails
4. UI-consumable runtime payloads
5. Watershed API/controller surface
6. Concept/work-package synchronization

## Findings and Resolutions

- Runtime fidelity gap: `blc_max_cost`/`blc_fill` were blocked by runtime validation and not passed to WBT.
  Resolution: Added helper/emulator/runtime pass-through with validation + regression tests.

- WBT signature drift: `unnest_basins` may not accept `hierarchy=`.
  Resolution: Added callable-signature compatibility and sidecar hierarchy discovery.

- Visualization observability gap: no timing evidence or workload guardrails.
  Resolution: Added `visualization_benchmarks.json`, per-artifact `generation_ms`, and `visualization_max_pixels` guardrail.

- UI integration gap: manifest paths were filesystem-local only.
  Resolution: Added `visualization_ui_payload.json`, relative-path derivation, watershed resource URL serving, and manifest URL decoration.

- API surface gap: no route-level terrain config/run/result endpoints.
  Resolution: Added watershed terrain routes for config set/query, run, result/manifest query, and artifact streaming.

## Changed Modules

- `wepppy/topo/wbt/terrain_processor_helpers.py`
- `wepppy/topo/wbt/wbt_topaz_emulator.py`
- `wepppy/topo/wbt/terrain_processor.py`
- `wepppy/weppcloud/routes/nodb_api/watershed_bp.py`
- `tests/topo/test_terrain_processor_helpers.py`
- `tests/topo/test_terrain_processor_runtime.py`
- `tests/topo/test_terrain_processor_wbt_integration.py`
- `tests/weppcloud/test_watershed_terrain_processor_api.py`
- `wepppy/topo/wbt/terrain_processor.concept.md`
