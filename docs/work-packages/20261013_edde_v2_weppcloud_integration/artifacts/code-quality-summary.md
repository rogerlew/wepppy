# Code Quality Observability Report

- Mode: `observe-only` (non-blocking)
- Generated (UTC): `2026-10-14T04:52:27Z`
- Base ref: `85f6ae9f8`

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
| `python_prod_file_sloc` | 1089 | 130.0 | 306.0 | 679.2 | 966.8 | 2088.2 | 5706.0 |
| `python_prod_max_function_len` | 904 | 58.0 | 106.0 | 172.0 | 228.85 | 388.79 | 2249.0 |
| `python_prod_max_cc` | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `js_source_file_sloc` | 231 | 241.0 | 554.0 | 1119.0 | 1561.5 | 2337.8 | 2840.0 |
| `js_source_max_cc` | 231 | 6.0 | 19.0 | 32.0 | 43.0 | 84.5 | 155.0 |

## Changed Files

- Files analyzed: `19`; highest severity red: `5`, yellow: `6`; worsened metric entries: `15` (exceptions: `0`, actionable: `15`)

| File | Lang | Highest | Key Metric Deltas |
| --- | --- | --- | --- |
| `tests/microservices/test_rq_engine_climate_routes.py` | `python` | `green` | python_file_sloc 620->634 (worsened, green)<br>python_function_len 60->60 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_schema_defaults_routes.py` | `python` | `red` | python_file_sloc 1665->1675 (worsened, red)<br>python_function_len 99->99 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_climate_edde_build.py` | `python` | `green` | python_file_sloc n/a->192 (new, green)<br>python_function_len n/a->42 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_locale_capability_authority.py` | `python` | `yellow` | python_file_sloc 1057->1057 (unchanged, yellow)<br>python_function_len 60->60 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_pure_controls_render.py` | `python` | `red` | python_file_sloc 4541->4546 (worsened, red)<br>python_function_len 181->181 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/climates/edde/cligen.py` | `python` | `green` | python_file_sloc 170->170 (unchanged, green)<br>python_function_len 69->69 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/climate_routes.py` | `python` | `red` | python_file_sloc 683->686 (worsened, yellow)<br>python_function_len 225->225 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | `python` | `red` | python_file_sloc 5329->5349 (worsened, red)<br>python_function_len 2243->2249 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/climate.py` | `python` | `red` | python_file_sloc 1362->1373 (worsened, red)<br>python_function_len 118->118 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/climate_build_router.py` | `python` | `yellow` | python_file_sloc 141->142 (worsened, green)<br>python_function_len 80->81 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/climate_edde_build.py` | `python` | `yellow` | python_file_sloc n/a->224 (new, green)<br>python_function_len n/a->105 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/climate_edde_inputs.py` | `python` | `green` | python_file_sloc n/a->36 (new, green)<br>python_function_len n/a->17 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/climate_input_parser.py` | `python` | `yellow` | python_file_sloc 268->289 (worsened, green)<br>python_function_len 117->124 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/climate_mode_build_services.py` | `python` | `green` | python_file_sloc 72->75 (worsened, green)<br>python_function_len 61->65 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/locales/capability_graph.py` | `python` | `yellow` | python_file_sloc 901->901 (unchanged, yellow)<br>python_function_len 119->119 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/locales/climate_catalog.py` | `python` | `green` | python_file_sloc 429->445 (worsened, green)<br>python_function_len 28->28 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/locales/locale_profiles.py` | `python` | `green` | python_file_sloc 391->391 (unchanged, green)<br>python_function_len 49->49 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/controllers_js/__tests__/climate.test.js` | `javascript` | `green` | js_file_sloc 526->524 (improved, green)<br>js_cc 6->6 (unchanged, green) |
| `wepppy/weppcloud/routes/nodb_api/climate_bp.py` | `python` | `yellow` | python_file_sloc 848->855 (worsened, yellow)<br>python_function_len 87->87 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |

## Hotspots (Current Tree)

### `python_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 5706 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 5349 |
| `tests/weppcloud/routes/test_pure_controls_render.py` | 4546 |
| `tests/nodb/mods/test_roads_controller.py` | 3256 |
| `tests/nodb/mods/test_features_export_service.py` | 3209 |
| `wepppy/nodb/mods/features_export/service.py` | 3099 |
| `tests/nodb/mods/test_omni.py` | 2972 |
| `wepppy/rq/project_rq.py` | 2818 |
| `wepppy/wepp/management/managements.py` | 2623 |
| `wepppy/nodb/core/wepp.py` | 2423 |

### `python_max_function_len_top20`

| Path | Value |
| --- | ---: |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 2249 |
| `wepppy/nodb/mods/roads/roads.py` | 2126 |
| `tests/nodb/mods/disturbed/live_e2e/runbook.py` | 768 |
| `wepppy/weppcloud/routes/ui_showcase/ui_showcase_bp.py` | 641 |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 631 |
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
