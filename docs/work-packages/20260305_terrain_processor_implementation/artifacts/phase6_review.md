# Phase 6 Review - Invalidation/Re-entry + Integration Validation

## Scope Delivered
- Implemented config-delta comparison and runtime invalidation mapping.
- Implemented selective phase invalidation with artifact cleanup and registry rebuild.
- Implemented `rerun_with_config(...)` and phase-6 invalidation report artifact.

## Files Changed
- `wepppy/topo/wbt/terrain_processor.py`
- `tests/topo/test_terrain_processor_runtime.py`

## Validation
- `wctl run-pytest tests/topo -k terrain_processor_phase6 -q` -> `2 passed`.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` -> `PASS`.
- `python3 tools/code_quality_observability.py --base-ref origin/master` -> report generated.
- `wctl doc-lint --path wepppy/topo/wbt/terrain_processor.concept.md` -> clean.

## Review Findings
- Correctness: Resolved by start-phase selection based on runtime invalidation rules.
- Maintainability: Resolved by separating helper invalidation mapping from runtime invalidation mapping.
- Test quality: Resolved by asserting preserved phase-1 artifacts and expected rerun phase set.

## Residual Risk
- Runtime invalidation rules should be revisited whenever new `TerrainConfig` fields are introduced.
