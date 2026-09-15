# Code Quality Observability Report

- Mode: `observe-only` (non-blocking)
- Generated (UTC): `2026-09-15T01:37:16Z`
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
| `python_prod_file_sloc` | 1025 | 129.0 | 326.0 | 686.6 | 973.8 | 2079.96 | 5697.0 |
| `python_prod_max_function_len` | 841 | 61.0 | 110.0 | 176.0 | 236.0 | 396.8 | 2233.0 |
| `python_prod_max_cc` | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `js_source_file_sloc` | 212 | 254.0 | 568.25 | 1212.9 | 1594.1 | 2414.67 | 2835.0 |
| `js_source_max_cc` | 212 | 6.0 | 20.25 | 33.0 | 44.45 | 85.45 | 155.0 |

## Changed Files

- Files analyzed: `34`; highest severity red: `0`, yellow: `9`; worsened metric entries: `17` (exceptions: `0`, actionable: `17`)

| File | Lang | Highest | Key Metric Deltas |
| --- | --- | --- | --- |
| `tests/microservices/test_rq_engine_postfire_debris_flow.py` | `python` | `green` | python_file_sloc 267->279 (worsened, green)<br>python_function_len 27->27 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_postfire_debris_flow_integration.py` | `python` | `green` | python_file_sloc 281->347 (worsened, green)<br>python_function_len 26->66 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_postfire_debris_flow_m3_integration.py` | `python` | `yellow` | python_file_sloc n/a->145 (new, green)<br>python_function_len n/a->91 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_postfire_debris_flow_m3_terrain.py` | `python` | `green` | python_file_sloc n/a->72 (new, green)<br>python_function_len n/a->14 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_postfire_debris_flow_production.py` | `python` | `green` | python_file_sloc 454->477 (worsened, green)<br>python_function_len 64->64 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_postfire_debris_flow_production_soils.py` | `python` | `green` | python_file_sloc n/a->336 (new, green)<br>python_function_len n/a->51 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_postfire_debris_flow_publication.py` | `python` | `green` | python_file_sloc 140->158 (worsened, green)<br>python_function_len 29->29 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_postfire_debris_flow_results.py` | `python` | `green` | python_file_sloc 278->291 (worsened, green)<br>python_function_len 33->33 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_postfire_debris_flow_runtime_m3.py` | `python` | `green` | python_file_sloc n/a->173 (new, green)<br>python_function_len n/a->45 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_postfire_debris_flow_source_acquisition.py` | `python` | `green` | python_file_sloc n/a->153 (new, green)<br>python_function_len n/a->58 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_postfire_debris_flow_source_preparation.py` | `python` | `green` | python_file_sloc n/a->213 (new, green)<br>python_function_len n/a->27 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_postfire_debris_flow_source_transport.py` | `python` | `green` | python_file_sloc n/a->96 (new, green)<br>python_function_len n/a->17 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/postfire_debris_flow_routes.py` | `python` | `green` | python_file_sloc 326->326 (unchanged, green)<br>python_function_len 65->65 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/analysis_support.py` | `python` | `green` | python_file_sloc n/a->21 (new, green)<br>python_function_len n/a->16 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/integration.py` | `python` | `yellow` | python_file_sloc 339->370 (worsened, green)<br>python_function_len 82->113 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/m1_inputs.py` | `python` | `green` | python_file_sloc 206->207 (worsened, green)<br>python_function_len 62->63 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/m3_integration.py` | `python` | `yellow` | python_file_sloc n/a->138 (new, green)<br>python_function_len n/a->90 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/m3_terrain.py` | `python` | `yellow` | python_file_sloc n/a->105 (new, green)<br>python_function_len n/a->98 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/predictor_v2.py` | `python` | `green` | python_file_sloc n/a->218 (new, green)<br>python_function_len n/a->71 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/production.py` | `python` | `yellow` | python_file_sloc 481->559 (worsened, green)<br>python_function_len 86->92 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/production_soils.py` | `python` | `green` | python_file_sloc n/a->59 (new, green)<br>python_function_len n/a->29 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/publication.py` | `python` | `green` | python_file_sloc 68->68 (unchanged, green)<br>python_function_len 66->66 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/rainfall_io.py` | `python` | `green` | python_file_sloc 266->304 (worsened, green)<br>python_function_len 62->66 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/result_support.py` | `python` | `green` | python_file_sloc n/a->33 (new, green)<br>python_function_len n/a->22 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/results.py` | `python` | `yellow` | python_file_sloc 298->319 (worsened, green)<br>python_function_len 96->96 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/soil_inputs.py` | `python` | `yellow` | python_file_sloc n/a->225 (new, green)<br>python_function_len n/a->109 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/soil_policy.py` | `python` | `green` | python_file_sloc n/a->104 (new, green)<br>python_function_len n/a->53 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/soil_snapshot.py` | `python` | `green` | python_file_sloc n/a->152 (new, green)<br>python_function_len n/a->40 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/soil_thickness.py` | `python` | `yellow` | python_file_sloc 296->309 (worsened, green)<br>python_function_len 98->98 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/source_acquisition.py` | `python` | `green` | python_file_sloc n/a->210 (new, green)<br>python_function_len n/a->57 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/source_preparation.py` | `python` | `yellow` | python_file_sloc n/a->300 (new, green)<br>python_function_len n/a->107 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/source_replay.py` | `python` | `green` | python_file_sloc n/a->127 (new, green)<br>python_function_len n/a->41 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/source_transport.py` | `python` | `green` | python_file_sloc n/a->197 (new, green)<br>python_function_len n/a->72 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/controllers_js/__tests__/postfire_debris_flow.test.js` | `javascript` | `green` | js_file_sloc 232->256 (worsened, green)<br>js_cc 3->3 (unchanged, green) |

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

_No entries._

### `js_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/weppcloud/controllers_js/omni.js` | 2835 |
| `wepppy/weppcloud/controllers_js/features_export.js` | 2690 |
| `wepppy/weppcloud/controllers_js/map_gl.js` | 2459 |
| `wepppy/weppcloud/controllers_js/project.js` | 2056 |
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
