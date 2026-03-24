# Cross-Cutting QA Review Findings

Date: 2026-03-24  
Reviewer: Codex (Milestone 9)

## QA Scope
- Regression tests for scoped report rollovers (Milestones 2-5).
- Roads controller/runtime validation for post-run resource regeneration.
- Roads route/template render behavior and summary link correctness.
- Fixture-backed e2e verification on `clogging-starch`.

## Findings
1. Resolved (Medium): No dedicated route assertion existed for Roads Run Results scoped link payloads and artifact link list.
   - Disposition: added `test_report_roads_summary_includes_scoped_links_and_artifacts` in `tests/weppcloud/routes/test_roads_bp.py`.
2. Resolved (Medium): Optional interchange-source absence in fixture run (`soil_pw0.txt`, `chan.out`, `chnwb.txt`) caused QA e2e failures despite required-resource readiness.
   - Disposition: added explicit optional-source gating in Roads regeneration helper; fixture e2e now passes with required resources present.
3. Resolved (High, follow-up): gl-dashboard route tests asserted only a subset of `weppPaths`, missing contract regressions on required keys.
   - Disposition: upgraded route tests (run + batch) to assert the full backend `wepp_paths` map for both baseline and roads scopes.
4. Resolved (High, follow-up): storm-event-analyzer route tests asserted only a subset of `weppPaths`.
   - Disposition: upgraded tests to assert full backend path maps for baseline and roads scopes.
5. Resolved (Medium, follow-up): missing positive roads-scope route tests for WEPP summary/water-balance report handlers.
   - Disposition: added roads-scope acceptance tests for `report_wepp_loss` and `report_wepp_avg_annual_watbal`, including scope propagation assertions.
6. Resolved (Medium, follow-up): missing negative test for segment-summary generation failures in Roads resource regeneration.
   - Disposition: added explicit failure regression test asserting `_regenerate_roads_report_resources()` surfaces segment-summary build exceptions.
7. Resolved (Medium, follow-up): missing pure template render regression for `controls/roads_reports.htm`.
   - Disposition: added dedicated render test in `tests/weppcloud/routes/test_pure_controls_render.py`.
8. Resolved (High, follow-up): missing positive roads-scope forwarding coverage for yearly water balance, streamflow, and return-period routes.
   - Disposition: added dedicated roads-scope acceptance tests in `tests/weppcloud/routes/test_wepp_bp.py` that assert downstream `output_scope` propagation and roads dataset path usage.
9. Resolved (Medium, follow-up): segment-loss summary branch coverage was insufficient for fallback/missing/contract paths.
   - Disposition: added tests for `segment_run_id` fallback matching, `loss_row_missing=True`, and non-list manifest JSON rejection in `tests/nodb/mods/test_roads_controller.py`.
10. Resolved (Medium, follow-up): roads controller Jest task-flow assertions did not enforce ordered/counted HTTP calls.
   - Disposition: strengthened `roads.test.js` with ordered `toHaveBeenNthCalledWith` assertions and explicit request call count.
11. Resolved (Medium, follow-up): gl-dashboard path wiring changes lacked direct payload assertions.
   - Disposition: expanded `wepp-data.test.js` to assert configured roads-scoped paths are used in hillslope/channel/yearly-channel/event query payloads.
12. Open medium/high findings: none.

## Validation Evidence
- `wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1` -> pass
- `wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1` -> pass
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1` -> pass
- Fixture e2e command (ExecPlan step 12) -> pass (`run_status=completed`, `missing=[]`)
- `wctl run-pytest tests/wepp/reports/test_loss_reports.py --maxfail=1` -> pass
- `wctl run-pytest tests/weppcloud/routes/test_wepp_bp.py tests/weppcloud/routes/test_gl_dashboard_route.py tests/weppcloud/routes/test_gl_dashboard_batch_route.py tests/weppcloud/routes/test_storm_event_analyzer_route.py tests/weppcloud/routes/test_pure_controls_render.py tests/weppcloud/routes/test_roads_bp.py --maxfail=1` -> pass
- `wctl run-pytest tests/wepp/reports/test_hillslope_watbal.py --maxfail=1` -> pass
- `wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1` -> pass
- `wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1` -> pass
- `wctl run-pytest tests/weppcloud/routes/test_wepp_bp.py --maxfail=1` -> pass
- `wctl run-npm test -- roads.test.js wepp-data.test.js` -> pass

## Conclusion
- Milestone 9 closure criteria met: no unresolved medium/high QA findings.
