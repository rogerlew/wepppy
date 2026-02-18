# Climate Validation and Rollout Stage D (Phase 6)

Scope: executable gates and rollout checks for climate Phase 6 adoption.

## Required Gates

| Gate | Command | Expected Result | Status |
| --- | --- | --- | --- |
| Climate build/upload routes + bp + catalog regression | `wctl run-pytest tests/microservices/test_rq_engine_climate_routes.py tests/microservices/test_rq_engine_upload_climate_routes.py tests/weppcloud/routes/test_climate_bp.py tests/nodb/test_climate_catalog.py` | Exit `0`; climate route preflight/upload/build behavior is stable | passed |
| Shared mutation/state safety | `wctl run-pytest tests/nodir` | Exit `0`; lock/thaw/freeze/mutation helper invariants remain green | passed |
| Docs consistency | `wctl doc-lint --path docs/work-packages/20260214_nodir_archives` | Exit `0`; no markdown-doc violations | passed |

## Rollout Checks

- Archive-form `build-climate` and `upload-cli` root writes are executed through shared mutation orchestration.
- Mixed/invalid/transitional roots fail at route preflight with canonical `409`/`500`/`503` semantics.
- Upload route no longer performs direct archive-form filesystem writes outside a NoDir root lock/state boundary.

## Rollback Trigger and Action

- Trigger: climate build/upload paths bypass root mutation wrapper or stop returning canonical NoDir preflight errors.
- Action: revert Phase 6 climate changes in `wepppy/rq/project_rq.py`, `wepppy/microservices/rq_engine/climate_routes.py`, and `wepppy/microservices/rq_engine/upload_climate_routes.py`, then re-run Stage D gate commands.
