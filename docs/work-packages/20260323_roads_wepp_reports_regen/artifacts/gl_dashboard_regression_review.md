# GL Dashboard Regression Review

Date: 2026-03-24 04:49Z  
Reviewer: Codex (dedicated Milestone 4 regression pass)

## Scope Reviewed
- `wepppy/weppcloud/routes/gl_dashboard.py`
- `wepppy/weppcloud/routes/batch_runner/batch_runner_bp.py`
- `wepppy/weppcloud/templates/gl_dashboard.htm`
- `wepppy/weppcloud/static/js/gl-dashboard.js`
- `wepppy/weppcloud/static/js/gl-dashboard/data/wepp-data.js`
- `wepppy/weppcloud/static/js/gl-dashboard/graphs/graph-loaders.js`
- `wepppy/weppcloud/static/js/gl-dashboard/layers/orchestrator.js`
- `wepppy/weppcloud/static/js/gl-dashboard/layers/detector.js`
- `tests/weppcloud/routes/test_gl_dashboard_route.py`
- `tests/weppcloud/routes/test_gl_dashboard_batch_route.py`

## Validation Executed
- `wctl run-pytest tests/weppcloud -k gl_dashboard --maxfail=1` -> pass (27 passed)
- `wctl run-npm test -- gl-dashboard` -> pass (17 suites, 57 tests)

## Findings
1. Resolved (Medium): gl-dashboard frontend query payload builders contained baseline-only `wepp/output/interchange/*` literals, bypassing backend scope control.
   - Disposition: replaced with backend-owned `weppPaths` context map and required-path wiring through orchestrator/data/graph/detector modules.
2. Resolved (Medium): run-scoped gl-dashboard route accepted no strict `output_scope` contract.
   - Disposition: added strict `baseline|roads` validation with explicit `400` on invalid scope, plus route coverage.
3. Open medium/high findings after fix: none.

## Regression Risk Assessment
- Residual low risk: storm-event-analyzer route/module still needs equivalent scope rollout in Milestone 5.
