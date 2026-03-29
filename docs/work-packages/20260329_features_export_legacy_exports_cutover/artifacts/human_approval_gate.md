# Human Approval Gate - Legacy Module Deletion

Date prepared: 2026-03-29
Prepared by: Codex
Gate status: **GO approved and executed**

## Decision Requested
Approve or reject Phase 8 destructive cleanup:
- delete `wepppy/export/gpkg_export.py`
- delete `wepppy/export/prep_details.py`
- remove remaining dead callsites and legacy imports

## Evidence Package
- Code review: `artifacts/code_review.md`
- QA review: `artifacts/qa_review.md`
- E2E validation: `artifacts/e2e_validation_summary.md`
- Active plan: `prompts/active/features_export_legacy_exports_cutover_execplan.md`

## Cutover State at Gate
- Legacy rq-engine endpoints now execute via features-export profile requests:
  - `/export/geopackage` -> `prep-wepp`
  - `/export/geodatabase` -> `prep-wepp` with format override `geodatabase`
  - `/export/prep_details` -> `prep-details`
- Post-run hooks now execute/publish features-export profile requests:
  - `_post_gpkg_export_rq` -> `prep-wepp`
  - `_post_prep_details_rq` -> `prep-details`
- Published download endpoint implemented:
  - `GET /api/runs/{runid}/{config}/export/features/published/{profile}/download`
- Publication registry implemented and validated:
  - `export/features/published/index.json`
- Artifact packaging simplified to payload members + `manifest.json` only.

## Known Residual Risks
- Legacy modules still exist; until deletion, accidental non-cutover imports are still technically possible.
- Geopackage generation emits GDAL geometry-type warnings (non-fatal in observed runs).

## Maintainer Decision
- [X] **GO** - approve Phase 8 legacy module deletion.
- [ ] **NO-GO** - do not delete legacy modules yet.

Approver name: Roger Lew

Decision date (UTC): March 29, 2026

Notes:

## Post-GO Execution Evidence
- Deleted legacy modules:
  - `wepppy/export/gpkg_export.py`
  - `wepppy/export/gpkg_export.pyi`
  - `wepppy/export/prep_details.py`
  - `wepppy/export/prep_details.pyi`
- Removed dead imports/callsites:
  - `wepppy/export/__init__.py`
  - `wepppy/export/__init__.pyi`
  - `wepppy/rq/wepp_rq.py`
  - `wepppy/nodb/mods/ag_fields/ag_fields.py`
- Final regression validation (pass):
  - `wctl run-pytest tests/nodb/mods/test_features_export_planner.py tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_exporters.py tests/microservices/test_rq_engine_features_export_routes.py tests/microservices/test_rq_engine_export_routes.py tests/rq/test_wepp_rq_pipeline.py tests/rq/test_wepp_rq_stage_post.py --maxfail=1` (`141 passed`)
  - `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1` (`4 passed`)
  - `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1` (`11 passed`)
  - `wctl run-npm test -- features_export` (`22 passed`)
