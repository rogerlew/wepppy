# Phase 10 Mod Workflow Rollout Review
Date: 2026-02-18

## Scope
- Treatments, ash transport (`watar`), debris flow, omni scenarios/contrasts, and observed model-fit/report workflow closure for NoDir archive-form compatibility.

## Delivered Changes
- Wave 1:
  - Route-level NoDir preflight + canonical error propagation (`NODIR_MIXED_STATE`, `NODIR_INVALID_ARCHIVE`, `NODIR_LOCKED`) for treatments/ash/debris/omni enqueue and omni dry-run boundaries.
- Wave 2:
  - Projection-aware ash climate CLI read path hardening in `Ash.run_ash`.
  - `run_ash_rq` dependent-root NoDir preflight for read-path callers.
- Wave 3:
  - Omni clone/contrast archive-form normalization for `landuse`/`soils` source roots.
  - `_omni_clone_sibling` `_pups` boundary enforcement and traversal rejection.
- Wave 4:
  - Observed closure coverage with both marker-form and valid zip-archive `.nodir` allowlisted-root variants.

## Validation Snapshot
1. `wctl run-pytest tests/microservices/test_rq_engine_treatments_routes.py tests/microservices/test_rq_engine_ash_routes.py tests/microservices/test_rq_engine_debris_flow_routes.py tests/microservices/test_rq_engine_omni_routes.py`
   - `55 passed, 3 warnings`
2. `wctl run-pytest tests/rq/test_project_rq_debris_flow.py tests/rq/test_project_rq_ash.py`
   - `4 passed, 3 warnings`
3. `wctl run-pytest tests/nodb/mods/test_ash_transport_run_ash.py tests/nodb/mods/test_treatments_build.py tests/nodb/mods/test_omni.py tests/nodb/mods/test_observed_processing.py`
   - `48 passed, 5 warnings`
4. `wctl run-pytest tests/weppcloud/routes/test_treatments_bp.py tests/weppcloud/routes/test_debris_flow_bp.py tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/routes/test_observed_bp.py`
   - `13 passed, 3 warnings`
5. `wctl run-pytest tests --maxfail=1`
   - `1648 passed, 27 skipped, 54 warnings`

## Contract / Dependency Notes
- NoDir allowlist remained unchanged: `landuse`, `soils`, `climate`, `watershed`.
- No canonical error payload contract changes.
- No enqueue dependency-graph changes; `wepppy/rq/job-dependencies-catalog.md` unchanged.

## Residual Risk
- Observed closure now has both marker and valid archive variants; no remaining concrete Phase 10B blockers identified.
