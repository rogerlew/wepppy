# Code Quality Observability Report

- Mode: `observe-only` (non-blocking)
- Generated (UTC): `2026-10-08T23:41:27Z`
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
| `python_prod_file_sloc` | 1075 | 131.0 | 315.5 | 681.8 | 970.9 | 2089.6 | 5697.0 |
| `python_prod_max_function_len` | 891 | 58.0 | 107.0 | 172.0 | 229.5 | 391.3 | 2243.0 |
| `python_prod_max_cc` | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `js_source_file_sloc` | 216 | 254.0 | 567.0 | 1211.5 | 1590.5 | 2398.4 | 2840.0 |
| `js_source_max_cc` | 216 | 6.0 | 19.25 | 33.0 | 44.25 | 85.25 | 155.0 |

## Changed Files

- Files analyzed: `31`; highest severity red: `9`, yellow: `6`; worsened metric entries: `26` (exceptions: `0`, actionable: `26`)

| File | Lang | Highest | Key Metric Deltas |
| --- | --- | --- | --- |
| `tests/climates/prism/test_wepp_adapter.py` | `python` | `green` | python_file_sloc n/a->50 (new, green)<br>python_function_len n/a->25 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_climate_routes.py` | `python` | `green` | python_file_sloc 619->620 (worsened, green)<br>python_function_len 60->60 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_schema_defaults_routes.py` | `python` | `red` | python_file_sloc 1626->1626 (unchanged, red)<br>python_function_len 99->99 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_batch_climate_rap_contention.py` | `python` | `green` | python_file_sloc 570->619 (worsened, green)<br>python_function_len 47->47 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_climate_prism_build.py` | `python` | `green` | python_file_sloc n/a->118 (new, green)<br>python_function_len n/a->34 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_locale_capability_authority.py` | `python` | `yellow` | python_file_sloc 1024->1029 (worsened, yellow)<br>python_function_len 60->60 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_project_config_builder_snapshot.py` | `python` | `green` | python_file_sloc 115->118 (worsened, green)<br>python_function_len 25->25 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_project_config_capabilities.py` | `python` | `green` | python_file_sloc 560->561 (worsened, green)<br>python_function_len 60->60 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_project_config_registry_serializer.py` | `python` | `green` | python_file_sloc 535->537 (worsened, green)<br>python_function_len 32->33 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_project_config_update.py` | `python` | `red` | python_file_sloc 1432->1434 (worsened, red)<br>python_function_len 133->133 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_project_rq_archive.py` | `python` | `green` | python_file_sloc 606->626 (worsened, green)<br>python_function_len 47->47 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/climates/prism/bulk_client.py` | `python` | `green` | python_file_sloc 116->120 (worsened, green)<br>python_function_len 38->39 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/climates/prism/wepp_adapter.py` | `python` | `green` | python_file_sloc n/a->80 (new, green)<br>python_function_len n/a->42 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/climate_routes.py` | `python` | `red` | python_file_sloc 682->683 (worsened, yellow)<br>python_function_len 225->225 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | `python` | `red` | python_file_sloc 5291->5291 (unchanged, red)<br>python_function_len 2243->2243 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/climate.py` | `python` | `red` | python_file_sloc 1348->1362 (worsened, red)<br>python_function_len 118->118 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/climate_build_helpers.py` | `python` | `red` | python_file_sloc 1348->1348 (unchanged, red)<br>python_function_len 89->89 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/climate_build_router.py` | `python` | `yellow` | python_file_sloc 129->141 (worsened, green)<br>python_function_len 80->80 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/climate_input_parser.py` | `python` | `yellow` | python_file_sloc 267->268 (worsened, green)<br>python_function_len 117->117 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/climate_mode_build_services.py` | `python` | `green` | python_file_sloc 68->72 (worsened, green)<br>python_function_len 56->61 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/climate_observed_build.py` | `python` | `green` | python_file_sloc 211->230 (worsened, green)<br>python_function_len 59->74 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/climate_prism_build.py` | `python` | `yellow` | python_file_sloc n/a->121 (new, green)<br>python_function_len n/a->101 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/locales/capability_graph.py` | `python` | `yellow` | python_file_sloc 896->896 (unchanged, yellow)<br>python_function_len 119->119 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/locales/climate_catalog.py` | `python` | `green` | python_file_sloc 417->429 (worsened, green)<br>python_function_len 28->28 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/locales/locale_profiles.py` | `python` | `green` | python_file_sloc 391->391 (unchanged, green)<br>python_function_len 49->49 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/batch_rq.py` | `python` | `red` | python_file_sloc 880->883 (worsened, yellow)<br>python_function_len 185->185 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/omni_rq.py` | `python` | `red` | python_file_sloc 902->906 (worsened, yellow)<br>python_function_len 290->290 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/wepp_rq.py` | `python` | `yellow` | python_file_sloc 1038->1041 (worsened, yellow)<br>python_function_len 102->102 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/wepp_rq_stage_finalize.py` | `python` | `green` | python_file_sloc 142->145 (worsened, green)<br>python_function_len 58->58 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/controllers_js/__tests__/climate.test.js` | `javascript` | `green` | js_file_sloc 521->526 (worsened, green)<br>js_cc 6->6 (unchanged, green) |
| `wepppy/weppcloud/controllers_js/climate.js` | `javascript` | `red` | js_file_sloc 1352->1366 (worsened, green)<br>js_cc 40->40 (unchanged, red) |

## Hotspots (Current Tree)

### `python_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 5697 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 5291 |
| `tests/weppcloud/routes/test_pure_controls_render.py` | 4495 |
| `tests/nodb/mods/test_roads_controller.py` | 3240 |
| `tests/nodb/mods/test_features_export_service.py` | 3209 |
| `wepppy/nodb/mods/features_export/service.py` | 3099 |
| `tests/nodb/mods/test_omni.py` | 2972 |
| `wepppy/rq/project_rq.py` | 2818 |
| `wepppy/wepp/management/managements.py` | 2623 |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 2451 |

### `python_max_function_len_top20`

| Path | Value |
| --- | ---: |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 2243 |
| `wepppy/nodb/mods/roads/roads.py` | 2126 |
| `tests/nodb/mods/disturbed/live_e2e/runbook.py` | 768 |
| `wepppy/weppcloud/routes/ui_showcase/ui_showcase_bp.py` | 641 |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 631 |
| `wepppy/nodb/mods/path_ce/data_prep.py` | 541 |
| `wepppy/wepp/fuzzing/single_ofe_stratified_campaign.py` | 528 |
| `wepppy/microservices/rq_engine/orchestration_read_routes.py` | 470 |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 415 |
| `wepppy/microservices/rq_engine/project_routes.py` | 412 |

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
| `wepppy/weppcloud/static/js/gl-dashboard/graphs/timeseries-graph.js` | 47 |
| `wepppy/weppcloud/controllers_js/features_export.js` | 46 |

## Review Guidance

- This report is observe-only: it does not block merges.
- Use changed-file deltas to spot opportunistic cleanup candidates.
- Prefer incremental reductions when touching hotspot files.
