# QA Review - Features Export Legacy Cutover

Date: 2026-03-29
Reviewer: Codex (QA pass)

## Test Matrix

### Microservices
- `wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py tests/microservices/test_rq_engine_export_routes.py --maxfail=1`
  - Result: `21 passed`

### Features Export Service
- `wctl run-pytest tests/nodb/mods/test_features_export_service.py --maxfail=1`
  - Result: `56 passed`

### RQ Integration
- `wctl run-pytest tests/rq/test_features_export_rq.py tests/rq/test_wepp_rq_pipeline.py --maxfail=1`
  - Result: `8 passed`
- `wctl run-pytest tests/rq/test_wepp_rq_stage_post.py --maxfail=1`
  - Result: `9 passed`

### WEPPcloud Route Integration
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1`
  - Result: `4 passed`
- `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1`
  - Result: `10 passed`

### Frontend Controller JS
- `wctl run-npm test -- features_export`
  - Result: `22 passed`

## QA Conclusion
- All targeted suites for cutover behavior are passing.
- Publication registry behavior is covered by new service tests and route tests.
- Legacy endpoint boundary error behavior (`NoDirError` propagation) remains preserved.
