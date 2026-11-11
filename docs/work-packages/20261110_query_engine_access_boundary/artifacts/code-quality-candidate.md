# Code Quality Observability Report

- Mode: `observe-only` (non-blocking)
- Generated (UTC): `2026-11-11T02:26:01Z`
- Base ref: `origin/master`

## Threshold Bands

| Metric | Yellow | Red |
| --- | ---: | ---: |
| `python_file_sloc` | 650 | 1200 |
| `python_function_len` | 80 | 150 |
| `python_cc` | 15 | 30 |
| `js_file_sloc` | 1500 | 2500 |
| `js_cc` | 15 | 30 |

## Tooling

- `radon` available: `False`
- `eslint` available: `True`
- Python runtime: `Python 3.14.6`
- Exception rules source: _none_
- Exception rules configured: `0`
- Exception rules applied: `0`

## Overall Baseline

| Distribution | Count | p50 | p75 | p90 | p95 | p99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `python_prod_file_sloc` | 1142 | 131.5 | 302.75 | 673.5 | 961.95 | 2077.52 | 5831.0 |
| `python_prod_max_function_len` | 954 | 57.0 | 104.0 | 173.0 | 226.7 | 391.99 | 2249.0 |
| `python_prod_max_cc` | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `js_source_file_sloc` | 240 | 242.5 | 543.25 | 1070.4 | 1539.45 | 2323.28 | 2840.0 |
| `js_source_max_cc` | 240 | 6.0 | 19.0 | 32.0 | 42.1 | 84.05 | 155.0 |

## Changed Files

- Files analyzed: `19`; highest severity red: `1`, yellow: `7`; worsened metric entries: `22` (exceptions: `0`, actionable: `22`)

| File | Lang | Highest | Key Metric Deltas |
| --- | --- | --- | --- |
| `tests/query_engine/test_http_access_boundary.py` | `python` | `green` | python_file_sloc n/a->595 (new, green)<br>python_function_len n/a->28 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/query_engine/test_mcp_router.py` | `python` | `yellow` | python_file_sloc 1040->1045 (worsened, yellow)<br>python_function_len 121->122 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/query_engine/test_server_routes.py` | `python` | `yellow` | python_file_sloc 464->482 (worsened, green)<br>python_function_len 91->97 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_combined_watershed_viewer_security.py` | `python` | `green` | python_file_sloc 192->195 (worsened, green)<br>python_function_len 30->30 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_run_0_nocfg_auth_bridge.py` | `python` | `green` | python_file_sloc 558->562 (worsened, green)<br>python_function_len 44->44 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/query_engine/access_scope.py` | `python` | `green` | python_file_sloc n/a->91 (new, green)<br>python_function_len n/a->28 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/query_engine/activate.py` | `python` | `yellow` | python_file_sloc 520->534 (worsened, green)<br>python_function_len 107->108 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/query_engine/app/access.py` | `python` | `green` | python_file_sloc n/a->266 (new, green)<br>python_function_len n/a->45 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/query_engine/app/feature_access.py` | `python` | `green` | python_file_sloc 78->94 (worsened, green)<br>python_function_len 35->39 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/query_engine/app/helpers.py` | `python` | `green` | python_file_sloc 41->110 (worsened, green)<br>python_function_len 52->26 (improved, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/query_engine/app/server.py` | `python` | `yellow` | python_file_sloc 903->926 (worsened, yellow)<br>python_function_len 141->145 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/query_engine/catalog_refresh.py` | `python` | `yellow` | python_file_sloc 755->764 (worsened, yellow)<br>python_function_len 75->80 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/query_engine/core.py` | `python` | `yellow` | python_file_sloc 416->422 (worsened, green)<br>python_function_len 140->140 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/app.py` | `python` | `green` | python_file_sloc 483->487 (worsened, green)<br>python_function_len 25->25 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/combined_watershed_viewer.py` | `python` | `green` | python_file_sloc 148->153 (worsened, green)<br>python_function_len 46->46 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | `python` | `red` | python_file_sloc 2415->2417 (worsened, red)<br>python_function_len 401->401 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/utils/browse_cookie.py` | `python` | `green` | python_file_sloc 33->42 (worsened, green)<br>python_function_len 9->9 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/utils/helpers.py` | `python` | `yellow` | python_file_sloc 884->889 (worsened, yellow)<br>python_function_len 125->130 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/utils/query_cookie.py` | `python` | `green` | python_file_sloc n/a->55 (new, green)<br>python_function_len n/a->36 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |

## Hotspots (Current Tree)

### `python_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 5831 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 5349 |
| `tests/weppcloud/routes/test_pure_controls_render.py` | 4695 |
| `tests/nodb/mods/test_roads_controller.py` | 3423 |
| `tests/nodb/mods/test_features_export_service.py` | 3243 |
| `wepppy/nodb/mods/features_export/service.py` | 3139 |
| `tests/nodb/mods/test_omni.py` | 2972 |
| `wepppy/rq/project_rq.py` | 2848 |
| `wepppy/wepp/management/managements.py` | 2660 |
| `wepppy/nodb/base.py` | 2622 |

### `python_max_function_len_top20`

| Path | Value |
| --- | ---: |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 2249 |
| `wepppy/nodb/mods/roads/roads.py` | 2052 |
| `tests/nodb/mods/disturbed/live_e2e/runbook.py` | 768 |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 647 |
| `wepppy/weppcloud/routes/ui_showcase/ui_showcase_bp.py` | 641 |
| `wepppy/nodb/mods/path_ce/data_prep.py` | 541 |
| `wepppy/wepp/fuzzing/single_ofe_stratified_campaign.py` | 528 |
| `wepppy/microservices/rq_engine/orchestration_read_routes.py` | 470 |
| `wepppy/eu/soils/esdac/esdac.py` | 418 |
| `wepppy/microservices/rq_engine/project_routes.py` | 414 |

### `python_max_cc_top20`

_No entries._

### `js_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/weppcloud/controllers_js/omni.js` | 2840 |
| `wepppy/weppcloud/controllers_js/features_export.js` | 2690 |
| `wepppy/weppcloud/controllers_js/map_gl.js` | 2459 |
| `wepppy/weppcloud/controllers_js/project.js` | 2111 |
| `wepppy/weppcloud/controllers_js/ag_fields.js` | 1997 |
| `wepppy/weppcloud/controllers_js/batch_runner.js` | 1915 |
| `wepppy/weppcloud/controllers_js/channel_gl.js` | 1873 |
| `wepppy/weppcloud/controllers_js/control_base.js` | 1751 |
| `wepppy/weppcloud/controllers_js/geneva_summary_report.js` | 1747 |
| `wepppy/weppcloud/controllers_js/subcatchment_delineation.js` | 1636 |

### `js_max_cc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/weppcloud/static/js/gl-dashboard/map/layers.js` | 155 |
| `wepppy/weppcloud/controllers_js/wepp.js` | 93 |
| `wepppy/weppcloud/static/js/gl-dashboard/layers/renderer.js` | 86 |
| `wepppy/weppcloud/static-src/tests/smoke/map-gl.spec.js` | 81 |
| `wepppy/weppcloud/controllers_js/postfire_debris_flow.js` | 74 |
| `wepppy/weppcloud/controllers_js/dss_export.js` | 58 |
| `wepppy/weppcloud/controllers_js/control_base.js` | 57 |
| `wepppy/weppcloud/controllers_js/project.js` | 52 |
| `wepppy/weppcloud/static/js/gl-dashboard/graphs/timeseries-graph.js` | 48 |
| `wepppy/weppcloud/controllers_js/features_export.js` | 46 |

## Review Guidance

- This report is observe-only: it does not block merges.
- Use changed-file deltas to spot opportunistic cleanup candidates.
- Prefer incremental reductions when touching hotspot files.
