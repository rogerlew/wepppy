# Phase 6 All-Roots Review

Review date: 2026-02-17
Scope: final cross-root conformance review for NoDir Phase 6 mutation adoption (`watershed`, `soils`, `landuse`, `climate`).

## Implementation Summary

### Shared foundation
- Added shared mutation orchestration in `wepppy/nodir/mutations.py` (`preflight_root_forms`, `mutate_root`, `mutate_roots`).
- Added lock-scoped thaw/freeze helpers in `wepppy/nodir/thaw_freeze.py` (`thaw_locked`, `freeze_locked`).
- Wired shared exports in `wepppy/nodir/__init__.py`.

### Root mutation owners
- `watershed`: `build_channels_rq`, `set_outlet_rq`, `build_subcatchments_rq`, `abstract_watershed_rq` now run through `mutate_root(..., "watershed", ...)`.
- `soils`: `build_soils_rq` now runs through `mutate_root(..., "soils", ...)`.
- `landuse`: `build_landuse_rq` now runs through `mutate_root(..., "landuse", ...)`; `build_treatments_rq` uses `mutate_roots(..., ("landuse", "soils"), ...)`.
- `climate`: `build_climate_rq` and `upload_cli_rq` now run through `mutate_root(..., "climate", ...)`.

### Route boundaries
- Added canonical preflight (`nodir_resolve(..., view="effective")`) and `NoDirError` propagation to mutation routes in:
  - `wepppy/microservices/rq_engine/watershed_routes.py`
  - `wepppy/microservices/rq_engine/soils_routes.py`
  - `wepppy/microservices/rq_engine/landuse_routes.py`
  - `wepppy/microservices/rq_engine/climate_routes.py`
- Upload route write path moved under root mutation ownership:
  - `wepppy/microservices/rq_engine/upload_climate_routes.py` (`mutate_root(..., "climate", ...)`).
- Landuse UserDefined raster-stack write path moved under root mutation ownership:
  - `wepppy/microservices/rq_engine/landuse_routes.py` (`mutate_root(..., "landuse", ...)`).

### Constructor and serialized-path cleanup
- Removed eager root directory creation in:
  - `wepppy/nodb/core/watershed.py`
  - `wepppy/nodb/core/soils.py`
  - `wepppy/nodb/core/landuse.py`
  - `wepppy/nodb/core/climate.py`
- Removed watershed `_structure` path-string persistence hazard by keeping structure data in-memory while still writing `structure.json`:
  - `wepppy/nodb/core/watershed.py`.

## Behavior-Matrix Conformance Snapshot

| Behavior Matrix Row | Expected Archive-Form Behavior | Status | Evidence |
| --- | --- | --- | --- |
| RQ-engine watershed group | `materialize(root)+freeze` | pass | `project_rq.py` mutation wrappers + watershed route preflight + watershed gate runs |
| RQ-engine build-soils | `materialize(root)+freeze` | pass | `build_soils_rq` wrapper + soils route preflight + soils gate run |
| RQ-engine build-landuse | `materialize(root)+freeze` | pass | `build_landuse_rq` wrapper + landuse route preflight/user-defined write wrapper + landuse gate run |
| RQ-engine build-climate | `materialize(root)+freeze` | pass | `build_climate_rq` wrapper + climate route preflight + climate gate run |
| RQ-engine upload CLI | `materialize(root)+freeze` | pass | `upload_cli_rq` wrapper + upload route write wrapper + upload route gate run |
| Treatments/landuse+soils mod writes | `materialize(root)+freeze` for affected roots | pass | `build_treatments_rq` uses `mutate_roots` with deterministic lock ordering |
| Mixed/invalid/transitional preflight on mutation routes | `409`/`500`/`503` canonical errors | pass | Added `nodir_resolve(..., view="effective")` + `NoDirError` propagation tests across root routes |

## Stage Artifact Completion

- Watershed Stage A-D: present and validated (`watershed_*_stage_*.md`).
- Soils Stage A-D: present (`soils_*_stage_*.md`).
- Landuse Stage A-D: present (`landuse_*_stage_*.md`).
- Climate Stage A-D: present (`climate_*_stage_*.md`).

## Validation Evidence

| Command | Result |
| --- | --- |
| `wctl run-pytest tests/nodir` | `90 passed` |
| `wctl run-pytest tests/microservices/test_rq_engine_watershed_routes.py tests/topo/test_peridot_runner_wait.py tests/topo/test_topaz_vrt_read.py tests/test_wepp_top_translator.py` | `34 passed` |
| `wctl run-pytest tests/nodir/test_materialize.py tests/microservices/test_rq_engine_export_routes.py tests/nodb/mods/test_swat_interchange.py` | `28 passed` |
| `wctl run-pytest tests/microservices/test_rq_engine_soils_routes.py tests/weppcloud/routes/test_soils_bp.py tests/soils/test_ssurgo.py` | `9 passed, 5 skipped` |
| `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py tests/weppcloud/routes/test_landuse_bp.py tests/nodb/test_landuse_catalog.py` | `16 passed` |
| `wctl run-pytest tests/microservices/test_rq_engine_climate_routes.py tests/microservices/test_rq_engine_upload_climate_routes.py tests/weppcloud/routes/test_climate_bp.py tests/nodb/test_climate_catalog.py` | `18 passed` |
| `wctl run-pytest tests --maxfail=1` | `1531 passed, 27 skipped` |
| `wctl doc-lint --path docs/work-packages/20260214_nodir_archives` | `30 files validated, 0 errors, 0 warnings` |

## Residual Risks

- No open Phase 6 blockers remain for mutation-surface conformance.
- Existing deprecation warnings observed in full-suite output are preexisting platform/dependency warnings and were not introduced by this phase.
