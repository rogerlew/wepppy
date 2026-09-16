# Code Quality Observability Report

- Mode: `observe-only` (non-blocking)
- Generated (UTC): `2026-09-16T23:28:48Z`
- Base ref: `9395f4722`

## Threshold Bands

| Metric | Yellow | Red |
| --- | ---: | ---: |
| `python_file_sloc` | 650 | 1200 |
| `python_function_len` | 80 | 150 |
| `python_cc` | 15 | 30 |
| `js_file_sloc` | 1500 | 2500 |
| `js_cc` | 15 | 30 |

## Tooling

- `radon` available: `True`
- `eslint` available: `True`
- Python runtime: `Python 3.14.6`
- Exception rules source: _none_
- Exception rules configured: `0`
- Exception rules applied: `0`

## Overall Baseline

| Distribution | Count | p50 | p75 | p90 | p95 | p99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `python_prod_file_sloc` | 1030 | 129.5 | 324.5 | 686.1 | 973.55 | 2076.41 | 5697.0 |
| `python_prod_max_function_len` | 846 | 60.5 | 109.75 | 175.5 | 234.75 | 396.15 | 2233.0 |
| `python_prod_max_cc` | 858 | 12.0 | 21.75 | 35.0 | 44.15 | 79.72 | 171.0 |
| `js_source_file_sloc` | 214 | 255.5 | 567.0 | 1206.7 | 1592.3 | 2406.48 | 2835.0 |
| `js_source_max_cc` | 214 | 6.0 | 19.75 | 33.0 | 44.35 | 85.35 | 155.0 |

## Changed Files

- Files analyzed: `19`; highest severity red: `9`, yellow: `4`; worsened metric entries: `23` (exceptions: `0`, actionable: `23`)

| File | Lang | Highest | Key Metric Deltas |
| --- | --- | --- | --- |
| `tests/nodb/mods/test_postfire_debris_flow_kf.py` | `python` | `green` | python_file_sloc n/a->101 (new, green)<br>python_function_len n/a->18 (new, green)<br>python_cc n/a->8 (new, green) |
| `tests/nodb/mods/test_postfire_debris_flow_production.py` | `python` | `yellow` | python_file_sloc 481->513 (worsened, green)<br>python_function_len 64->92 (worsened, yellow)<br>python_cc 14->17 (worsened, yellow) |
| `tests/rq/test_project_rq_archive.py` | `python` | `green` | python_file_sloc 470->475 (worsened, green)<br>python_function_len 42->47 (worsened, green)<br>python_cc 9->9 (unchanged, green) |
| `tests/weppcloud/routes/test_postfire_report_bp.py` | `python` | `green` | python_file_sloc 164->164 (unchanged, green)<br>python_function_len 26->26 (unchanged, green)<br>python_cc 14->14 (unchanged, green) |
| `wepppy/nodb/mods/postfire_debris_flow/integration.py` | `python` | `red` | python_file_sloc 370->396 (worsened, green)<br>python_function_len 113->129 (worsened, yellow)<br>python_cc 48->53 (worsened, red) |
| `wepppy/nodb/mods/postfire_debris_flow/kf_source.py` | `python` | `red` | python_file_sloc n/a->168 (new, green)<br>python_function_len n/a->64 (new, green)<br>python_cc n/a->46 (new, red) |
| `wepppy/nodb/mods/postfire_debris_flow/predictor_v2.py` | `python` | `red` | python_file_sloc 218->240 (worsened, green)<br>python_function_len 71->83 (worsened, yellow)<br>python_cc 76->86 (worsened, red) |
| `wepppy/nodb/mods/postfire_debris_flow/preflight.py` | `python` | `green` | python_file_sloc 32->37 (worsened, green)<br>python_function_len 28->33 (worsened, green)<br>python_cc 10->12 (worsened, green) |
| `wepppy/nodb/mods/postfire_debris_flow/production.py` | `python` | `red` | python_file_sloc 563->598 (worsened, green)<br>python_function_len 92->100 (worsened, yellow)<br>python_cc 62->69 (worsened, red) |
| `wepppy/nodb/mods/postfire_debris_flow/rainfall_io.py` | `python` | `red` | python_file_sloc 304->304 (unchanged, green)<br>python_function_len 66->66 (unchanged, green)<br>python_cc 64->64 (unchanged, red) |
| `wepppy/nodb/mods/postfire_debris_flow/report.py` | `python` | `yellow` | python_file_sloc 170->175 (worsened, green)<br>python_function_len 42->42 (unchanged, green)<br>python_cc 20->20 (unchanged, yellow) |
| `wepppy/nodb/mods/postfire_debris_flow/response_curve.py` | `python` | `yellow` | python_file_sloc n/a->52 (new, green)<br>python_function_len n/a->40 (new, green)<br>python_cc n/a->22 (new, yellow) |
| `wepppy/nodb/mods/postfire_debris_flow/results.py` | `python` | `red` | python_file_sloc 320->325 (worsened, green)<br>python_function_len 96->96 (unchanged, yellow)<br>python_cc 84->84 (unchanged, red) |
| `wepppy/nodb/mods/postfire_debris_flow/source_transport.py` | `python` | `red` | python_file_sloc 197->201 (worsened, green)<br>python_function_len 72->72 (unchanged, green)<br>python_cc 31->31 (unchanged, red) |
| `wepppy/rq/postfire_debris_flow_rq.py` | `python` | `green` | python_file_sloc 60->60 (unchanged, green)<br>python_function_len 33->33 (unchanged, green)<br>python_cc 13->13 (unchanged, green) |
| `wepppy/weppcloud/controllers_js/__tests__/postfire_report.test.js` | `javascript` | `green` | js_file_sloc 316->331 (worsened, green)<br>js_cc 2->2 (unchanged, green) |
| `wepppy/weppcloud/controllers_js/postfire_debris_flow.js` | `javascript` | `red` | js_file_sloc 230->230 (unchanged, green)<br>js_cc 75->75 (unchanged, red) |
| `wepppy/weppcloud/controllers_js/postfire_report.js` | `javascript` | `yellow` | js_file_sloc 427->464 (worsened, green)<br>js_cc 16->18 (worsened, yellow) |
| `wepppy/weppcloud/controllers_js/project.js` | `javascript` | `red` | js_file_sloc 2056->2055 (improved, yellow)<br>js_cc 52->52 (unchanged, red) |

## Hotspots (Current Tree)

### `python_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 5697 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 5274 |
| `tests/weppcloud/routes/test_pure_controls_render.py` | 4392 |
| `tests/nodb/mods/test_features_export_service.py` | 3251 |
| `tests/nodb/mods/test_roads_controller.py` | 3240 |
| `wepppy/nodb/mods/features_export/service.py` | 3026 |
| `tests/nodb/mods/test_omni.py` | 2929 |
| `wepppy/rq/project_rq.py` | 2809 |
| `wepppy/wepp/management/managements.py` | 2548 |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 2421 |

### `python_max_function_len_top20`

| Path | Value |
| --- | ---: |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 2233 |
| `wepppy/nodb/mods/roads/roads.py` | 2126 |
| `tests/nodb/mods/disturbed/live_e2e/runbook.py` | 768 |
| `wepppy/weppcloud/routes/ui_showcase/ui_showcase_bp.py` | 641 |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 613 |
| `wepppy/nodb/mods/path_ce/data_prep.py` | 541 |
| `wepppy/wepp/fuzzing/single_ofe_stratified_campaign.py` | 528 |
| `wepppy/microservices/rq_engine/orchestration_read_routes.py` | 470 |
| `wepppy/microservices/rq_engine/project_routes.py` | 412 |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 402 |

### `python_max_cc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 171 |
| `wepppy/nodb/mods/roads/roads.py` | 148 |
| `wepppy/wepp/fuzzing/single_ofe_stratified_campaign.py` | 98 |
| `wepppy/nodb/mods/path_ce/path_ce_solver.py` | 95 |
| `wepppy/nodb/mods/postfire_debris_flow/predictor_v2.py` | 86 |
| `wepppy/nodb/mods/path_ce/data_prep.py` | 85 |
| `wepppy/nodb/mods/postfire_debris_flow/results.py` | 84 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 82 |
| `wepppy/rq/project_rq_fork.py` | 82 |
| `wepppy/microservices/rq_engine/orchestration_read_routes.py` | 78 |

### `js_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/weppcloud/controllers_js/omni.js` | 2835 |
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
| `wepppy/weppcloud/controllers_js/postfire_debris_flow.js` | 75 |
| `wepppy/weppcloud/controllers_js/dss_export.js` | 58 |
| `wepppy/weppcloud/controllers_js/control_base.js` | 57 |
| `wepppy/weppcloud/controllers_js/project.js` | 52 |
| `wepppy/weppcloud/static/js/gl-dashboard/graphs/timeseries-graph.js` | 47 |
| `wepppy/weppcloud/controllers_js/features_export.js` | 46 |

## Review Guidance

- This report is observe-only: it does not block merges.
- Use changed-file deltas to spot opportunistic cleanup candidates.
- Prefer incremental reductions when touching hotspot files.
