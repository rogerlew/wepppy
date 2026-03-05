# Phase 3 Review - Culvert Two-Pass Runtime

## Scope Delivered
- Implemented road-stream crossing extraction and culvert point selection (`auto_intersect` and uploaded-point snap path).
- Implemented `burn_streams_at_roads_adapter` runtime wiring and `relief_burned.tif` artifact registration.
- Implemented mandatory second flow-stack pass and v2 stream artifacts.

## Files Changed
- `wepppy/topo/wbt/terrain_processor.py`
- `tests/topo/test_terrain_processor_runtime.py`

## Validation
- `wctl run-pytest tests/topo -k terrain_processor_phase3 -q` -> `1 passed`.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` -> `PASS`.
- `python3 tools/code_quality_observability.py --base-ref origin/master` -> report generated.
- `wctl doc-lint --path wepppy/topo/wbt/terrain_processor.concept.md` -> clean.

## Review Findings
- Correctness: Resolved by explicit enforcement of two-pass rerun semantics.
- Maintainability: Resolved by keeping culvert extraction/snap logic in helper contracts.
- Test quality: Resolved by branch coverage for uploaded culvert path + rerun assertion.

## Residual Risk
- Only `culvert_method='burn_streams_at_roads'` is runtime-enabled; legacy breakline burn remains intentionally unsupported.
