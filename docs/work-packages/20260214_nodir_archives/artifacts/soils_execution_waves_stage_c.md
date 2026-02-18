# Soils Execution Waves Stage C (Phase 6)

Scope: execution waves used to deliver soils archive-form mutation behavior.

## Wave Summary

| Wave | Objective | In-Scope Work | Status |
| --- | --- | --- | --- |
| Wave 1 | Remove bootstrap mixed-state hazards | Remove eager `WD/soils` constructor creation in `Soils.__init__`; preserve on-demand directory creation for real writes | complete |
| Wave 2 | Cut over canonical mutation owner | Wrap `build_soils_rq` with `mutate_root(..., "soils", ...)` in `wepppy/rq/project_rq.py` | complete |
| Wave 3 | Enforce route preflight and canonical errors | Add `nodir_resolve(..., "soils", view="effective")` + `NoDirError` propagation in `wepppy/microservices/rq_engine/soils_routes.py` | complete |
| Wave 4 | Validate root and consumer regressions | Execute soils gate suite and shared NoDir regressions | complete |

## Execution Evidence (2026-02-17)

- `wctl run-pytest tests/microservices/test_rq_engine_soils_routes.py tests/weppcloud/routes/test_soils_bp.py tests/soils/test_ssurgo.py`
  - Result: `9 passed, 5 skipped`.
- `wctl run-pytest tests/nodir`
  - Result: `90 passed`.

## Wave Exit Verdict

- `soils` mutation behavior now matches behavior-matrix expectations:
  - Dir form: `native` root mutation path.
  - Archive form: `materialize(root)+freeze` via shared orchestration.
  - Mixed/invalid/transitional states: canonical `409`/`500`/`503` behavior before enqueue.
