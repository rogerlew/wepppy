# Landuse Validation and Rollout Stage D (Phase 6)

Scope: executable gates and rollout checks for landuse Phase 6 adoption.

## Required Gates

| Gate | Command | Expected Result | Status |
| --- | --- | --- | --- |
| Landuse route + bp + catalog regression | `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py tests/weppcloud/routes/test_landuse_bp.py tests/nodb/test_landuse_catalog.py` | Exit `0`; route preflight, enqueue, and controller route behavior remain stable | passed |
| Shared mutation/state safety | `wctl run-pytest tests/nodir` | Exit `0`; mutation helper + thaw/freeze/state semantics remain green | passed |
| Docs consistency | `wctl doc-lint --path docs/work-packages/20260214_nodir_archives` | Exit `0`; no markdown-doc violations | passed |

## Rollout Checks

- Archive-form `build-landuse` and UserDefined map writes now run under root mutation orchestration.
- Canonical NoDir errors (`409`, `500`, `503`) are surfaced before enqueue for mixed/invalid/transitional roots.
- Cross-root treatments mutation uses deterministic multi-root lock ordering.

## Rollback Trigger and Action

- Trigger: archive-form landuse writes bypass mutation wrapper, or route preflight stops returning canonical NoDir status/code.
- Action: revert Phase 6 landuse changes in `wepppy/rq/project_rq.py` and `wepppy/microservices/rq_engine/landuse_routes.py`, then re-run Stage D gate commands.
