# Streamflow + Water Balance Regression Review

Date: 2026-03-24 04:31Z  
Reviewer: Codex (dedicated Milestone 3 regression pass)

## Scope Reviewed
- `wepppy/wepp/reports/hillslope_watbal.py`
- `wepppy/wepp/reports/channel_watbal.py`
- `wepppy/wepp/reports/total_watbal.py`
- `wepppy/nodb/core/wepp.py`
- `wepppy/weppcloud/routes/nodb_api/wepp_bp.py`
- `wepppy/weppcloud/templates/reports/wepp/avg_annual_watbal.htm`
- `wepppy/weppcloud/templates/reports/wepp/yearly_watbal.htm`
- `wepppy/weppcloud/templates/reports/wepp/daily_streamflow_graph.htm`
- `tests/wepp/reports/test_hillslope_watbal.py`
- `tests/wepp/reports/test_channel_watbal.py`
- `tests/wepp/reports/test_total_watbal.py`
- `tests/weppcloud/routes/test_wepp_bp.py`

## Validation Executed
- `wctl run-pytest tests/wepp/reports -k "streamflow or watbal" --maxfail=1` -> pass (12 passed)
- `wctl run-pytest tests/weppcloud/routes/test_wepp_bp.py -k output_scope --maxfail=1` -> pass (4 passed)

## Findings
1. Resolved (Medium): hillslope water-balance cache key was scope-agnostic and could cross-contaminate baseline/roads cache content.
   - Disposition: baseline cache key retained for compatibility; roads uses dedicated cache key suffix (`_roads`).
2. Resolved (Medium): water-balance and streamflow routes lacked explicit invalid-scope regression coverage.
   - Disposition: added route regression tests asserting `400` for invalid `output_scope` across streamflow/watbal/return-period endpoints.
3. Open medium/high findings after fix: none.

## Regression Risk Assessment
- Residual low risk: gl-dashboard and storm-event-analyzer consumers still have baseline-path literals and remain queued for Milestones 4-5.
