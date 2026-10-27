# Code Quality Observability Report

- Mode: `observe-only` (non-blocking)
- Generated (UTC): `2026-10-27T19:46:06Z`
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
| `python_prod_file_sloc` | 1106 | 131.5 | 308.75 | 680.0 | 967.25 | 2084.35 | 5415.0 |
| `python_prod_max_function_len` | 921 | 58.0 | 107.0 | 173.0 | 228.0 | 387.6 | 2249.0 |
| `python_prod_max_cc` | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `js_source_file_sloc` | 236 | 241.0 | 547.25 | 1092.0 | 1549.25 | 2317.6 | 2840.0 |
| `js_source_max_cc` | 236 | 6.0 | 19.0 | 32.0 | 42.5 | 84.25 | 155.0 |

## Changed Files

- Files analyzed: `37`; highest severity red: `8`, yellow: `9`; worsened metric entries: `30` (exceptions: `0`, actionable: `30`)

| File | Lang | Highest | Key Metric Deltas |
| --- | --- | --- | --- |
| `tests/microservices/test_rq_engine_ag_fields_routes.py` | `python` | `yellow` | python_file_sloc 1045->1053 (worsened, yellow)<br>python_function_len 102->102 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_run_sync_routes.py` | `python` | `yellow` | python_file_sloc 182->195 (worsened, green)<br>python_function_len 87->87 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/rq212_tasks.py` | `python` | `green` | python_file_sloc n/a->86 (new, green)<br>python_function_len n/a->55 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_ag_fields_rq.py` | `python` | `yellow` | python_file_sloc 500->501 (worsened, green)<br>python_function_len 145->145 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_batch_rq_delete_batch.py` | `python` | `green` | python_file_sloc 113->127 (worsened, green)<br>python_function_len 51->51 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_batch_task_boundary.py` | `python` | `green` | python_file_sloc 478->479 (worsened, green)<br>python_function_len 76->76 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_culvert_rq_manifest.py` | `python` | `green` | python_file_sloc 74->86 (worsened, green)<br>python_function_len 56->56 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_dependency_graph_tools.py` | `python` | `green` | python_file_sloc 549->549 (unchanged, green)<br>python_function_len 56->56 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_job_dependencies.py` | `python` | `green` | python_file_sloc 93->150 (worsened, green)<br>python_function_len 24->32 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_job_info.py` | `python` | `green` | python_file_sloc 336->358 (worsened, green)<br>python_function_len 64->65 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_job_listings.py` | `python` | `green` | python_file_sloc 67->113 (worsened, green)<br>python_function_len 72->77 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_query_catalog_pilot.py` | `python` | `green` | python_file_sloc 381->407 (worsened, green)<br>python_function_len 51->51 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_roads_rq.py` | `python` | `green` | python_file_sloc 125->137 (worsened, green)<br>python_function_len 23->23 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_rq212_historical.py` | `python` | `green` | python_file_sloc n/a->112 (new, green)<br>python_function_len n/a->32 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_rq212_lifecycle.py` | `python` | `yellow` | python_file_sloc n/a->315 (new, green)<br>python_function_len n/a->84 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_rq212_metadata.py` | `python` | `green` | python_file_sloc n/a->164 (new, green)<br>python_function_len n/a->45 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_run_catalog_rq.py` | `python` | `green` | python_file_sloc 247->257 (worsened, green)<br>python_function_len 50->50 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_wbt_controlled_failure_integration.py` | `python` | `red` | python_file_sloc 1884->1884 (unchanged, red)<br>python_function_len 106->106 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/tools/test_query_catalog_pilot_cli.py` | `python` | `green` | python_file_sloc 316->336 (worsened, green)<br>python_function_len 20->21 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_deval_loading.py` | `python` | `green` | python_file_sloc 546->569 (worsened, green)<br>python_function_len 79->79 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tools/query_catalog_pilot.py` | `python` | `yellow` | python_file_sloc 509->509 (unchanged, green)<br>python_function_len 84->84 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tools/wctl2/commands/rq.py` | `python` | `green` | python_file_sloc 173->174 (worsened, green)<br>python_function_len 48->48 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/ag_fields_routes.py` | `python` | `red` | python_file_sloc 1234->1236 (worsened, red)<br>python_function_len 97->97 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/run_sync_routes.py` | `python` | `red` | python_file_sloc 337->339 (worsened, green)<br>python_function_len 184->184 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/profile_coverage/runtime.py` | `python` | `green` | python_file_sloc 75->54 (improved, green)<br>python_function_len 47->29 (improved, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/ag_fields_rq.py` | `python` | `yellow` | python_file_sloc 516->517 (worsened, green)<br>python_function_len 147->147 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/auth_actor.py` | `python` | `green` | python_file_sloc 185->167 (improved, green)<br>python_function_len 88->70 (improved, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/batch_rq.py` | `python` | `red` | python_file_sloc 885->886 (worsened, yellow)<br>python_function_len 185->185 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/culvert_rq_manifest.py` | `python` | `yellow` | python_file_sloc 348->348 (unchanged, green)<br>python_function_len 146->146 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/job_dependencies.py` | `python` | `red` | python_file_sloc 409->425 (worsened, green)<br>python_function_len 213->213 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/job_info.py` | `python` | `red` | python_file_sloc 537->541 (worsened, green)<br>python_function_len 179->179 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/job_listings.py` | `python` | `yellow` | python_file_sloc 209->215 (worsened, green)<br>python_function_len 76->81 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/project_rq.py` | `python` | `red` | python_file_sloc 2837->2837 (unchanged, red)<br>python_function_len 205->205 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/roads_rq.py` | `python` | `green` | python_file_sloc 224->225 (worsened, green)<br>python_function_len 51->51 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/rq_worker.py` | `python` | `yellow` | python_file_sloc 387->415 (worsened, green)<br>python_function_len 64->82 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/run_catalog_rq.py` | `python` | `green` | python_file_sloc 135->135 (unchanged, green)<br>python_function_len 33->33 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/weppcloudr.py` | `python` | `red` | python_file_sloc 776->776 (unchanged, yellow)<br>python_function_len 160->160 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |

## Hotspots (Current Tree)

### `python_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 5415 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 5349 |
| `tests/weppcloud/routes/test_pure_controls_render.py` | 4614 |
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
