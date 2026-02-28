# Phase 1 Subsystem Summary

## Snapshot

- Generated at: 2026-02-27 03:27Z
- Inventory source: `artifacts/nodir_reference_files.txt` (130 files)
- Classification source: `artifacts/phase1_classification_matrix.csv`
- Action totals: `replace=84`, `remove=31`, `guard=15`
- Target-phase totals: `phase2=19`, `phase3=18`, `phase4=40`, `phase5=53`

## Per-Subsystem Action Totals

| Subsystem | Total | Remove | Replace | Guard |
|---|---:|---:|---:|---:|
| `tests/microservices` | 14 | 1 | 13 | 0 |
| `tests/nodb` | 6 | 1 | 5 | 0 |
| `tests/nodir` | 15 | 15 | 0 | 0 |
| `tests/query_engine` | 1 | 0 | 1 | 0 |
| `tests/rq` | 10 | 1 | 9 | 0 |
| `tests/tools` | 1 | 1 | 0 | 0 |
| `tests/weppcloud` | 4 | 0 | 4 | 0 |
| `wepppy/climates` | 1 | 0 | 1 | 0 |
| `wepppy/export` | 3 | 0 | 3 | 0 |
| `wepppy/microservices` | 19 | 0 | 12 | 7 |
| `wepppy/nodb` | 21 | 1 | 19 | 1 |
| `wepppy/nodir` | 11 | 11 | 0 | 0 |
| `wepppy/query_engine` | 1 | 0 | 1 | 0 |
| `wepppy/rq` | 12 | 0 | 7 | 5 |
| `wepppy/tools` | 5 | 0 | 4 | 1 |
| `wepppy/wepp` | 1 | 0 | 1 | 0 |
| `wepppy/weppcloud` | 5 | 0 | 4 | 1 |

## Highest-Risk Files

- `wepppy/microservices/browse/files_api.py`: broad archive/effective view handling and mixed-state checks; likely to regress file browser semantics if changed out of order.
- `wepppy/microservices/browse/flow.py`: central browse dispatch path with NoDir alias logic and mixed-state redirect behavior.
- `wepppy/rq/wepp_rq.py`: mixed-state recovery wiring in core queue execution path; impacts long-running job restart behavior.
- `wepppy/rq/wepp_rq_stage_helpers.py`: shared recovery helpers used by multiple RQ entry points; tight coupling with `.nodir` recovery semantics.
- `wepppy/rq/project_rq.py`: high fan-out mutation entrypoint for root materialization and job staging.
- `wepppy/nodb/batch_runner.py`: mutates roots before batch execution; part of Phase 2 stop-the-bleeding boundary.
- `wepppy/nodir/projections.py`: projection and mutation orchestration across `.nodir` lower/upper/work trees; high-risk removal target in Phase 4.
- `wepppy/tools/migrations/nodir_bulk.py`: only explicit bulk rollback CLI; sequencing must align with data migration policy decisions.

## Recommended Edit Sequence

### Phase 2 (Stop New NoDir Creation)

1. `wepppy/weppcloud/routes/test_bp.py`
2. `wepppy/weppcloud/utils/helpers.py`
3. `wepppy/microservices/rq_engine/project_routes.py`
4. `wepppy/microservices/rq_engine/upload_huc_fire_routes.py`
5. `wepppy/microservices/rq_engine/upload_climate_routes.py`
6. `wepppy/microservices/rq_engine/landuse_routes.py`
7. `wepppy/rq/project_rq.py`
8. `wepppy/rq/culvert_rq.py`
9. `wepppy/rq/land_and_soil_rq.py`
10. `wepppy/nodb/batch_runner.py`
11. `wepppy/nodb/mods/omni/omni_mode_build_services.py`

### Phase 4 (Runtime Reversal)

1. Remove `wepppy/nodir/*` package surface after Phase 3 data rollback closure.
2. Convert `wepppy/nodb/core/*` and `wepppy/nodb/mods/*` NoDir helper usage to directory-only equivalents.
3. Replace NoDir browse/diff boundaries in `wepppy/microservices/browse/*`, `wepppy/microservices/_gdalinfo.py`, and `wepppy/weppcloud/routes/diff/diff.py`.
4. Remove sidecar and materialization dependencies in `wepppy/export/*`, `wepppy/query_engine/activate.py`, `wepppy/climates/climatena_ca/__init__.py`, and `wepppy/wepp/interchange/hec_ras_buffer.py`.
5. Retire NoDir-specific tests/docs in Phase 5.

## Archival Prompt Ownership Note

Superseded package prompts remain under `docs/work-packages/20260214_nodir_archives/prompts/active/` and must be treated as archival context only. Current count: 9 active prompt files. Phase 2+ execution ownership remains with this package (`20260227_nodir_full_reversal`).
