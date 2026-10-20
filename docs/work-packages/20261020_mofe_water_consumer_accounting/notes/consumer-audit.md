# Consumer Audit: Local Depths, Internal Transfers and Outlet Volumes

Audit date: 2026-10-20 UTC. Scope: repository-owned WEPPpy/wepppyo3 production
consumers of H.wat, their direct downstream reports/models, and relevant R and
audit tools. This is a static call-site audit plus workbook and native-writer
readback, not a claim to have exercised every runtime path. External user SQL,
notebooks and unknown archived executables are outside the searchable surface.

## Source provenance and control volume

Baseline WEPPpy `3a6f79f33`, wepppyo3 `5e4271623`, wepp-forest `375ccc296`.
Full revisions, installed native hash and workbook hash are in the
[receipt](../artifacts/20261020_audit_readback.json).

In `/workdir/wepp-forest/src/`, `watbal_hourly.for:417` transfers upstream
sbrunf using upstream/local area; `watbal.for` has the corresponding daily
logic. `wshpas.f90:145` converts terminal sbrunf to volume using terminal local
length and width, and writes both depth and volume to EVENT/SUBEVENT records.
`hbp_legacy_bridge.f90` preserves them in binary pass output;
`hbp_mode2_bridge.f90` reads them. `wshred.for` reads master-pass volumes,
`wshdrv.f90:797` retains them in tmpsbv, and `wshcqi.f90:348` routes volumes.
These are controls, not evidence that multiplying model sbrunf again is needed.

Current ordinary non-contour `watbal.for:1259` and
`watbal_hourly.for:1406` emit runoff*efflen/totlen as Q and also as QOFE.
The workbook instead has lower Q=119.753300 and QOFE=300.364812 mm/year.
Raw parsers preserve values and do not distinguish these meanings by version.
Terminal Q can represent hillslope depth for the demonstrated constant-width
serial case; general contour/width/version support needs explicit verification.
Use pass volumes for reconciliation. Never infer version from a Q/QOFE ratio.

## Direct consumer findings

Paths without a repository prefix are relative to WEPPpy; native paths are
relative to `/workdir/wepppyo3`.

| ID | Touch points | Observed behavior | Disposition for execution |
| --- | --- | --- | --- |
| WCA-01 | `wepp_interchange/src/hillslope_watbal.rs::produce`; `wepppy/wepp/reports/hillslope_watbal.py` | Annual P/QOFE/latqcc are summed across OFEs; ET/Dp now daily area weighted | Confirmed report defect. Replace each field's reducer, bump semantic cache, retain compact native pipeline |
| WCA-02 | `wepppy/weppcloud/static/js/gl-dashboard/data/wepp-data.js::refreshWeppEventData`, `loadBaseWeppEventData`; `map/layers.js` display/difference | Both branches use SUM(P) or SUM(Q); ET uses weighted SQL | Confirmed for MOFE. Correct selected/base queries and unavailable values, test actual generated SQL and displayed differences |
| WCA-03 | `wepppy/wepp/interchange/hill_wat_interchange.py::load_hill_wat_dataframe`, `DAILY_MM_COLUMNS` | All listed depth columns use SUM(depth*Area)/SUM(Area), including Q, QOFE, UpStrmQ, SubRIn, latqcc | Local ET/Dp/P/stocks have spatial weights; cumulative runoff and lateral outlet semantics are wrong for a whole-hill flow. Separate outlet, local, transfer fields; retain raw mode |
| WCA-04 | `wepppy/nodb/mods/features_export/temporal_wide_materializer.py::_collapse_terminal_ofe_rows`; carrier/duckdb materializers, service, layer catalog | Local ET/Dp have independent source-aware daily weighting; other fields use terminal row; yearly numeric reduction sums | Lateral remains terminal local depth, P is only a terminal sample, optional stock/geometry fields have inconsistent spatial/temporal interpretation. Define per-field contract before expanding reducers |
| WCA-05 | `wepp_interchange/src/ashpost.rs::` runoff accumulation/correction; `wepppy/nodb/mods/ash_transport/ashpost.py` | Sums QOFE*Area over all OFEs of selected ash hills, subtracts from hydrologic runoff volume, clips negative nonash contribution to zero | Confirmed structural internal-transfer double counting for workbook QOFE; current duplicate-Q convention is also not an outlet-volume sum. Use verified per-hill outlet volume, preserve modeled ash replacement semantics and NaN policy |
| WCA-06 | `wepp_interchange/src/totalwatsed.rs::aggregate_hill` and output assembly; `totalwatsed_schema.rs`; Python `totalwatsed3.py` | P/ET/Dp are area volumes; lateral retains maximum OFE per native hill; named Runoff uses H.pass runvol. Raw Q/QOFE still sum depth*local Area over all OFEs | Named hydrology is the control. Raw Q/QOFE are not outlet flow. Audit advertised descriptions and readers, choose explicit diagnostic or corrected semantics without silent renames. Missing-OFE legacy behavior and global-vs-day terminal selection need sparse-day coverage |
| WCA-07 | `weppcloudR/templates/scripts/report.Rmd::calc_watbal`; `users/chinmay/weppcloudr_report_functions.R::calc_watbal` | Reads raw rows, computes P-Q-ET-Dp-latqcc plus ungrouped storage lag; omits runon and area basis | Confirmed unsuitable for MOFE closure; older report still calls it. Default new_report no longer does. Disposition supported legacy behavior explicitly; do not describe all raw calculations as deprecated or delete shared helpers silently |
| WCA-08 | `tools/hillslope_daily_closure_audit.py`, `hillslope_mofe_daily_closure_audit.py`, `totalwatsed3_daily_closure_audit.py` | Daily/total tools mirror TotalWatSed lateral and pass runoff; MOFE tool deliberately sums transfers and subtracts inflows for local budgets, also compares terminal QOFE*Area to pass | Preserve legitimate internal-transfer diagnostics. Mark/version QOFE-based reconciliation assumptions so current duplicate-Q outputs do not falsely diagnose physical leakage |

## Indirect and supporting touch points

| Boundary | Files / functions | Dependency and required check |
| --- | --- | --- |
| Active average annual UI | `wepppy/nodb/core/wepp.py::report_hill_watbal`, report prebuild; `routes/nodb_api/wepp_bp.py::report_wepp_avg_annual_watbal`; `templates/controls/wepp_reports.htm`; `templates/reports/wepp/avg_annual_watbal.htm`; CSV adapter | Uses WCA-01 today, including watershed rollup of per-hill rows; verify HTML/CSV and no additional area multiplication |
| Yearly water UI | `wepppy/wepp/reports/total_watbal.py`; `wepp_bp.py::report_wepp_yearly_watbal` | Uses TotalWatSed named measures, not the native hillslope summary. Different existing year-selection policies must not masquerade as spatial discrepancies |
| Ash models | `ash_transport/ash.py::_run_hillslope_work/load_work`; `ash_multi_year_model.py::_run_ash_model_until_gone`; `ash_multi_year_model_alex.py::_run_ash_model_until_gone`; `weppcloud/routes/nodb_api/watar_bp.py` | Daily loader supplies Q/P/RM/soil/snow; Q correction changes ash runoff/transport and persisted results. Verify native ash bridge/recurrence and AshPost together, including output version freshness |
| Neris | `ash_transport/neris_ash_model.py::run_model` | Reads daily-loader Es; already area weighted. Preserve as control |
| Observed hydrology | `wepppy/nodb/mods/observed/observed.py::_load_hillslope_simulation` and channel loading | Generates/reads TotalWatSed, labels raw QOFE as volume; fitting uses named Streamflow. Confirm diagnostic column exposure versus hydrologic use |
| Frequency, return periods, DSS | `wepppy/wepp/reports/frq_flood.py`, `return_periods.py`; `wepppy/wepp/interchange/watershed_totalwatsed_export.py`; `routes/gl_dashboard_flow_duration.py`; `routes/nodb_api/return_period_scenarios.py` | Named Streamflow/Runoff/baseflow propagate; preserve pass-volume and corrected ET/Dp controls, audit export labels |
| Current R reports | `weppcloudR/plumber.R` default new_report; current report helper TotalWatSed inputs | Uses corrected named watershed hydrology; deleted inactive raw block must stay absent |
| Parser/schema | `wepp_interchange/src/hill_wat.rs`, `schema.rs`; `wepppy/wepp/interchange/hill_wat_interchange.py`, `ag_fields_interchange.py`, `hill_interchange.py`; `wepppy/tools/migrations/interchange.py`, `migrate_interchange.py` | Raw OFE rows/aliases are not aggregation defects. QOFE description alone cannot prove its version-specific basis |
| Export source binding | `features_export/carrier_layer_materializer.py`, `duckdb_materializer.py`, `service.py`, `layer_catalog.yaml` | Keep exact joined-source column identity, hidden area/date availability and correct WEPP/Topaz geometry association; both normal and AgFields H.wat declarations |
| Storm-event analyzer | `wepppy/query_engine/storm_event_analyzer.py`; `static/js/storm-event-analyzer/data/event-data.js` | H.wat snow coverage/SWE are area weighted; precipitation comes from hill event output weighted by hill area, hydrology from outlet output. No confirmed WAT-flow defect here; soil saturation AVG is a separate soil-domain question |
| Scope/wiring | `nodb/core/wepp.py`, `nodb/wepp_nodb_post_utils.py`, `rq/wepp_rq_stage_post.py`, `rq/wepp_rq.py`, `rq/wepp_rq_pipeline.py`, `rq/interchange_rq.py`, `rq/project_rq.py`, `rq/culvert_rq.py`, `nodb/core/wepp_run_service.py`, `nodb/batch_runner.py`, `routes/batch_runner/batch_runner_bp.py`, `routes/gl_dashboard.py`, `routes/nodb_api/roads_bp.py` | Producers and source paths, not separate reducers. Preserve cache freshness, Roads link/output_scope and batch behavior |
| Roads / AgFields | `nodb/mods/roads/roads.py`; `nodb/mods/ag_fields/watershed_integration.py`; interchange source mapping | Per-native-hill outlet selection must precede merging IDs to a target hill. Do not take one max OFE across independent contributing hills; preserve admitted AgFields cardinality rules |

The audit searched H.wat/hill_wat, latqcc/QOFE and loader call sites in Python,
Rust, JavaScript, YAML, R/Rmd and tools, then followed direct aggregation and
named-output consumers. This inventory does not certify untested external SQL or
all optional source layouts. Execution must repeat the search against its base
revision and add any newly reached formulas to this ledger.

## Workbook findings and reproducible evidence

`Two_OFE` has 11,323 unique daily records per OFE. `Last_OFE ` has 11,322 and
ends on 2025 day 364. Its missing day affects Es and Dp; do not mix that sheet's
annual values with the complete source sheet. Actual printed areas sum to
2811.38 m2; the summary's rounded single length produces 2817.5 m2 instead.
Use actual per-row Area, not the 0.6/0.4 filename or rounded length.

Summary I13 hard-codes 0.4; M13/N13 correctly use weighted areas; F12 uses a
rounded inverse 2.5; S13 still averages OFE outflows. The lower local budget
requires UpStrmQ+SubRIn. P=Dp/baseflow assumptions and O-column storage changes
are not independently validated. Daily records do not prove the producing
executable used hourly rather than daily internal stepping.

Run `artifacts/audit_readback.py` with the supplied workbook, explicit native
library and output receipt. It reads both cached values and formula text,
computes complete-sheet annual controls, and calls the actual native writer on
a temporary two-OFE parquet fixture. Expected corrected P/Q/lateral/ET/Dp are
10/8/4.5/5/7; pre-fix native output is 20/12.6666667/10/5/7. Other consumer
findings are static formula/call-site evidence, not claimed service executions.
