# Cross-Cutting Code Review Findings

Date: 2026-03-24  
Reviewer: Codex (Milestone 8)

## Scope Reviewed
- Roads execution/regeneration flow:
  - `wepppy/nodb/mods/roads/roads.py`
- Roads Run Results route/template/control integration:
  - `wepppy/weppcloud/routes/nodb_api/roads_bp.py`
  - `wepppy/weppcloud/templates/reports/roads/summary.htm`
  - `wepppy/weppcloud/templates/controls/roads_pure.htm`
  - `wepppy/weppcloud/controllers_js/roads.js`
- Storm event analyzer rollover:
  - `wepppy/weppcloud/routes/storm_event_analyzer.py`
  - `wepppy/weppcloud/templates/reports/storm_event_analyzer.htm`
  - `wepppy/weppcloud/static/js/storm-event-analyzer/main.js`
  - `wepppy/weppcloud/static/js/storm-event-analyzer/data/event-data.js`

## Findings
1. Resolved (Medium): Roads Run Results links initially bypassed `url_for_run` and would not reliably respect site-prefix routing.
   - Disposition: switched to backend `url_for_run(...)` endpoint resolution for report and artifact links in `roads_bp`.
2. Resolved (Medium): Roads report-resource regeneration forced optional watershed/hillslope conversions (`soil`, `chan.out`, `chnwb`) even when source files were absent, causing avoidable run failures.
   - Disposition: added explicit source-availability gating with run-log visibility while preserving strict failure on required resources.
3. Resolved (High, follow-up): `report_wepp_loss` ignored `output_scope`, so Roads "Watershed Loss Summary" links rendered baseline data.
   - Disposition: added strict scope resolution to `report_wepp_loss`, plumbed `output_scope` through `OutletSummaryReport` / `HillSummaryReport` / `ChannelSummaryReport`, and preserved scope in `reports/wepp/summary.htm` navigation + CSV URLs.
4. Resolved (High, follow-up): Roads segment-loss summary joined manifest rows on `segment_run_id`, which did not match real `loss_pw0.hill.parquet` keys in fixture runs.
   - Disposition: changed join strategy to prefer `target_hillslope_wepp_id` and only fallback to `segment_run_id` when needed; added `loss_match_key` diagnostics and regression coverage that verifies target-key precedence.
5. Resolved (Medium, follow-up): GL dashboard used a single channel dataset path for both summary and yearly-channel flows, causing path semantics drift.
   - Disposition: split channel path wiring (`lossChannel` for summary/cumulative channel metrics, `lossAllYearsChannel` for yearly-channel overlays and yearly refresh queries).
6. Resolved (Medium, follow-up): invalid-scope contract tests did not include `/report/wepp/summary`.
   - Disposition: extended `tests/weppcloud/routes/test_wepp_bp.py` invalid-scope matrix to include the summary route.
7. Resolved (Medium, follow-up): `HillslopeWatbalReport` had a bare `raise` outside `except KeyError`, which triggered `RuntimeError: No active exception to reraise` on baseline unmapped IDs.
   - Disposition: converted the translator miss path to explicit `except KeyError as exc` handling that re-raises the original exception for baseline scope and applies roads-only fallback logic.
8. Resolved (Medium, follow-up): Roads Run Results showed non-single-storm report links whenever resources were marked ready, even when required non-single-storm datasets were absent.
   - Disposition: `_roads_run_results_report_links` now gates route links by required Roads resource relpaths, and route tests cover the single-storm-style reduced-resource case.
9. Open medium/high findings: none.

## Conclusion
- Milestone 8 closure criteria met: no unresolved medium/high code-review findings.
