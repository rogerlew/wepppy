# Phase 2 Findings Resolution

## Resolution Ledger

- finding_id: P2-H1
  source: reviewer/test_guardian run 1
  severity: high
  scope: `upload_climate_routes.py` + `landuse_routes.py` mutation wrappers were no-op in review evidence
  disposition: resolved
  status: resolved
  resolution:
  - restored real lock-backed wrappers with preflight + post-lock recheck (`maintenance_lock`) in both routes.
  validation:
  - `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py tests/microservices/test_rq_engine_upload_climate_routes.py`

- finding_id: P2-H2
  source: reviewer run 1
  severity: high
  scope: omni concurrent lock contention (`NODIR_LOCKED`) risk in scenario helper
  disposition: resolved
  status: resolved
  resolution:
  - introduced bounded retry/wait lock acquisition in `wepppy/nodb/mods/omni/omni_mode_build_services.py` for single-root and multi-root lock helpers.
  validation:
  - `wctl run-pytest tests/nodb/mods/test_omni_mode_build_services.py`

- finding_id: P2-M1
  source: reviewer run 1
  severity: medium
  scope: unlocked watershed mutation path in `upload_dem`
  disposition: resolved
  status: resolved
  resolution:
  - wrapped `upload_dem` mutation block in watershed maintenance lock with directory preflight before and after lock.
  validation:
  - `wctl run-pytest tests/microservices/test_rq_engine_watershed_routes.py`

- finding_id: P2-M2
  source: reviewer run 2
  severity: medium
  scope: `_maybe_nodir_error_response` duck-typing risk across rq-engine routes
  disposition: resolved
  status: resolved
  resolution:
  - switched all Phase 2 route helpers to strict `isinstance(exc, NoDirError)` mapping.
  - added cross-route helper tests in `tests/microservices/test_rq_engine_nodir_boundary_helpers.py` for positive NoDir mapping and attr-shaped non-NoDir negative behavior.
  validation:
  - `wctl run-pytest tests/microservices/test_rq_engine_nodir_boundary_helpers.py tests/microservices/test_rq_engine_export_routes.py`

- finding_id: P2-M3
  source: reviewer run 2
  severity: medium
  scope: non-canonical multi-root lock ordering in worker helpers
  disposition: resolved
  status: resolved
  resolution:
  - canonicalized all relevant multi-root lock root sets to deterministic sorted order in:
    - `wepppy/rq/project_rq.py`
    - `wepppy/rq/culvert_rq.py`
    - `wepppy/nodb/mods/omni/omni_mode_build_services.py`
  - added helper-level order assertions in tests (`project_rq_mutation_guards.py`, `test_omni_mode_build_services.py`).
  validation:
  - `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py tests/nodb/mods/test_omni_mode_build_services.py tests/rq/test_project_rq_ash.py tests/rq/test_project_rq_debris_flow.py`

- finding_id: P2-M4
  source: test_guardian run 1
  severity: medium
  scope: missing success-path helper tests in new RQ guard suites
  disposition: resolved
  status: resolved
  resolution:
  - added directory-form success-path tests for lock helpers in:
    - `tests/rq/test_project_rq_mutation_guards.py`
    - `tests/rq/test_culvert_rq_nodir_guards.py`
    - `tests/rq/test_land_and_soil_rq_guards.py`
  validation:
  - `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py tests/rq/test_culvert_rq_nodir_guards.py tests/rq/test_land_and_soil_rq_guards.py`

- finding_id: P2-M5
  source: test_guardian run 1
  severity: medium
  scope: export contract assertions lacked full message checks
  disposition: resolved
  status: resolved
  resolution:
  - strengthened export route tests to assert status + error code + error message for NoDir paths and generic attr-shaped runtime boundary behavior.
  validation:
  - `wctl run-pytest tests/microservices/test_rq_engine_export_routes.py`

## Deferred Low Findings

- finding_id: P2-L1
  source: reviewer run 2
  severity: low
  scope: local `nodir_resolve` wrapper return annotations use `-> None` while returning resolver value.
  disposition: deferred
  status: deferred
  phase_assignment: Phase 3
  rationale:
  - non-functional typing/stub hygiene item with no runtime regression evidence; keep Phase 2 scope focused on behavior containment.

## Closure Check

- high unresolved: none
- medium unresolved: none
- escalated blockers from Phase 2 findings: none
