# Code Quality Observability Report

- Mode: `observe-only` (non-blocking)
- Generated (UTC): `2026-10-27T00:57:59Z`
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
| `python_prod_file_sloc` | 1101 | 131.0 | 308.0 | 679.0 | 962.0 | 2087.0 | 5406.0 |
| `python_prod_max_function_len` | 916 | 58.0 | 107.0 | 172.5 | 228.25 | 387.95 | 2249.0 |
| `python_prod_max_cc` | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `js_source_file_sloc` | 236 | 241.0 | 547.25 | 1092.0 | 1549.25 | 2317.6 | 2840.0 |
| `js_source_max_cc` | 236 | 6.0 | 19.0 | 32.0 | 42.5 | 84.25 | 155.0 |

## Changed Files

- Files analyzed: `16`; highest severity red: `9`, yellow: `1`; worsened metric entries: `8` (exceptions: `0`, actionable: `8`)

| File | Lang | Highest | Key Metric Deltas |
| --- | --- | --- | --- |
| `tests/microservices/test_browse_auth_routes.py` | `python` | `red` | python_file_sloc 1972->2013 (worsened, red)<br>python_function_len 76->76 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_dtale_freshness.py` | `python` | `green` | python_file_sloc 432->452 (worsened, green)<br>python_function_len 63->63 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_files_routes.py` | `python` | `red` | python_file_sloc 1582->1570 (improved, red)<br>python_function_len 57->57 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_roads_controller.py` | `python` | `red` | python_file_sloc 3056->3065 (worsened, red)<br>python_function_len 256->256 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/roads/test_roads_publication.py` | `python` | `green` | python_file_sloc 43->62 (worsened, green)<br>python_function_len 13->31 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/wepp/interchange/test_roads_lifecycle.py` | `python` | `green` | python_file_sloc 330->306 (improved, green)<br>python_function_len 45->45 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_diff_bp.py` | `python` | `green` | python_file_sloc 83->83 (unchanged, green)<br>python_function_len 31->31 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/browse/_download.py` | `python` | `yellow` | python_file_sloc 681->678 (improved, yellow)<br>python_function_len 118->120 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/browse/_roads.py` | `python` | `unknown` | python_file_sloc 47->n/a (removed, unknown)<br>python_function_len 23->n/a (removed, unknown)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/browse/browse.py` | `python` | `red` | python_file_sloc 1347->1342 (improved, red)<br>python_function_len 109->109 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/browse/dtale.py` | `python` | `red` | python_file_sloc 309->306 (improved, green)<br>python_function_len 249->247 (improved, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/browse/files_api.py` | `python` | `red` | python_file_sloc 963->960 (improved, yellow)<br>python_function_len 201->199 (improved, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/browse/listing.py` | `python` | `red` | python_file_sloc 843->836 (improved, yellow)<br>python_function_len 195->195 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/roads/roads.py` | `python` | `red` | python_file_sloc 5405->5406 (worsened, red)<br>python_function_len 2030->2031 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/runtime_paths/paths.py` | `python` | `green` | python_file_sloc 63->55 (improved, green)<br>python_function_len 27->23 (improved, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/webservices/dtale/dtale.py` | `python` | `red` | python_file_sloc 1581->1546 (improved, red)<br>python_function_len 221->221 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |

## Hotspots (Current Tree)

### `python_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 5406 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 5349 |
| `tests/weppcloud/routes/test_pure_controls_render.py` | 4579 |
| `tests/nodb/mods/test_features_export_service.py` | 3243 |
| `wepppy/nodb/mods/features_export/service.py` | 3139 |
| `tests/nodb/mods/test_roads_controller.py` | 3065 |
| `tests/nodb/mods/test_omni.py` | 2972 |
| `wepppy/rq/project_rq.py` | 2837 |
| `wepppy/wepp/management/managements.py` | 2623 |
| `wepppy/nodb/core/wepp.py` | 2423 |

### `python_max_function_len_top20`

| Path | Value |
| --- | ---: |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 2249 |
| `wepppy/nodb/mods/roads/roads.py` | 2031 |
| `tests/nodb/mods/disturbed/live_e2e/runbook.py` | 768 |
| `wepppy/weppcloud/routes/ui_showcase/ui_showcase_bp.py` | 641 |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 634 |
| `wepppy/nodb/mods/path_ce/data_prep.py` | 541 |
| `wepppy/wepp/fuzzing/single_ofe_stratified_campaign.py` | 528 |
| `wepppy/microservices/rq_engine/orchestration_read_routes.py` | 470 |
| `wepppy/microservices/rq_engine/project_routes.py` | 412 |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 396 |

### `python_max_cc_top20`

_No entries._

### `js_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/weppcloud/controllers_js/omni.js` | 2840 |
| `wepppy/weppcloud/controllers_js/features_export.js` | 2690 |
| `wepppy/weppcloud/controllers_js/map_gl.js` | 2459 |
| `wepppy/weppcloud/controllers_js/project.js` | 2055 |
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
