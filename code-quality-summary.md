# Code Quality Observability Report

- Mode: `observe-only` (non-blocking)
- Generated (UTC): `2026-07-15T15:50:35Z`
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
- Python runtime: `Python 3.12.3`
- Exception rules source: _none_
- Exception rules configured: `0`
- Exception rules applied: `0`

## Overall Baseline

| Distribution | Count | p50 | p75 | p90 | p95 | p99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `python_prod_file_sloc` | 916 | 125.5 | 304.25 | 670.0 | 964.5 | 1969.8 | 5697.0 |
| `python_prod_max_function_len` | 736 | 60.0 | 109.0 | 175.5 | 226.5 | 344.4 | 2126.0 |
| `python_prod_max_cc` | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `js_source_file_sloc` | 181 | 282.0 | 594.0 | 1238.0 | 1636.0 | 2478.8 | 2835.0 |
| `js_source_max_cc` | 181 | 7.0 | 22.0 | 33.0 | 45.0 | 87.4 | 155.0 |

## Changed Files

- Files analyzed: `45`; highest severity red: `5`, yellow: `18`; worsened metric entries: `38` (exceptions: `0`, actionable: `38`)

| File | Lang | Highest | Key Metric Deltas |
| --- | --- | --- | --- |
| `tests/microservices/test_rq_engine_ag_fields_routes.py` | `python` | `yellow` | python_file_sloc 527->837 (worsened, yellow)<br>python_function_len 80->99 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_ag_fields_backend_contract.py` | `python` | `green` | python_file_sloc 380->380 (unchanged, green)<br>python_function_len 55->55 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_ag_fields_concept1_inputs.py` | `python` | `green` | python_file_sloc n/a->59 (new, green)<br>python_function_len n/a->19 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_ag_fields_concept1_integration.py` | `python` | `green` | python_file_sloc n/a->62 (new, green)<br>python_function_len n/a->27 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_ag_fields_concept1_planner.py` | `python` | `green` | python_file_sloc n/a->90 (new, green)<br>python_function_len n/a->15 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_ag_fields_corpus_execution.py` | `python` | `yellow` | python_file_sloc n/a->132 (new, green)<br>python_function_len n/a->100 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_ag_fields_hybrid_integration.py` | `python` | `green` | python_file_sloc n/a->180 (new, green)<br>python_function_len n/a->43 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_ag_fields_management_corpus.py` | `python` | `yellow` | python_file_sloc n/a->98 (new, green)<br>python_function_len n/a->84 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_ag_fields_routing_schemes.py` | `python` | `green` | python_file_sloc n/a->57 (new, green)<br>python_function_len n/a->9 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_ag_fields_watershed_integration.py` | `python` | `green` | python_file_sloc 259->585 (worsened, green)<br>python_function_len 41->54 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_ash_transport_run_ash.py` | `python` | `green` | python_file_sloc 160->186 (worsened, green)<br>python_function_len 46->46 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_ag_fields_rq.py` | `python` | `green` | python_file_sloc 137->150 (worsened, green)<br>python_function_len 32->32 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/topo/test_watershed_abstraction_slope_file.py` | `python` | `green` | python_file_sloc 257->289 (worsened, green)<br>python_function_len 42->42 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/wepp/interchange/test_hill_interchange_cleanup.py` | `python` | `green` | python_file_sloc 137->179 (worsened, green)<br>python_function_len 59->59 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/wepp/interchange/test_pass_interchange.py` | `python` | `green` | python_file_sloc 115->151 (worsened, green)<br>python_function_len 27->45 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/wepp/interchange/test_totalwatsed3.py` | `python` | `green` | python_file_sloc 392->441 (worsened, green)<br>python_function_len 76->76 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/wepp/interchange/test_wat_interchange.py` | `python` | `green` | python_file_sloc 65->143 (worsened, green)<br>python_function_len 31->51 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/wepp/management/test_multiple_ofe.py` | `python` | `green` | python_file_sloc 319->393 (worsened, green)<br>python_function_len 53->54 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_pure_controls_render.py` | `python` | `yellow` | python_file_sloc 1167->1189 (worsened, yellow)<br>python_function_len 95->95 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/ag_fields_routes.py` | `python` | `yellow` | python_file_sloc 923->1136 (worsened, yellow)<br>python_function_len 61->90 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/ag_fields/ag_fields.py` | `python` | `red` | python_file_sloc 1429->1712 (worsened, red)<br>python_function_len 165->165 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/ag_fields/concept1_inputs.py` | `python` | `yellow` | python_file_sloc n/a->169 (new, green)<br>python_function_len n/a->83 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/ag_fields/concept1_integration.py` | `python` | `yellow` | python_file_sloc n/a->445 (new, green)<br>python_function_len n/a->90 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/ag_fields/concept1_planner.py` | `python` | `red` | python_file_sloc n/a->961 (new, yellow)<br>python_function_len n/a->281 (new, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/ag_fields/corpus_execution.py` | `python` | `yellow` | python_file_sloc n/a->578 (new, green)<br>python_function_len n/a->134 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/ag_fields/hybrid_integration.py` | `python` | `green` | python_file_sloc n/a->641 (new, green)<br>python_function_len n/a->72 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/ag_fields/management_corpus.py` | `python` | `yellow` | python_file_sloc n/a->459 (new, green)<br>python_function_len n/a->97 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/ag_fields/routing_schemes.py` | `python` | `green` | python_file_sloc n/a->69 (new, green)<br>python_function_len n/a->12 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/ag_fields/watershed_integration.py` | `python` | `yellow` | python_file_sloc 1005->1141 (worsened, yellow)<br>python_function_len 96->96 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/ash_transport/ash.py` | `python` | `red` | python_file_sloc 768->780 (worsened, yellow)<br>python_function_len 261->261 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/ag_fields_rq.py` | `python` | `green` | python_file_sloc 257->287 (worsened, green)<br>python_function_len 58->60 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/topo/peridot/peridot_runner.py` | `python` | `red` | python_file_sloc 693->699 (worsened, yellow)<br>python_function_len 204->204 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/topo/watershed_abstraction/slope_file.py` | `python` | `yellow` | python_file_sloc 216->244 (worsened, green)<br>python_function_len 102->102 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/wepp/interchange/concurrency.py` | `python` | `yellow` | python_file_sloc 244->191 (improved, green)<br>python_function_len 163->109 (improved, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/wepp/interchange/hill_ebe_interchange.py` | `python` | `yellow` | python_file_sloc 317->325 (worsened, green)<br>python_function_len 80->80 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/wepp/interchange/hill_element_interchange.py` | `python` | `green` | python_file_sloc 323->331 (worsened, green)<br>python_function_len 66->66 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/wepp/interchange/hill_interchange.py` | `python` | `yellow` | python_file_sloc 213->236 (worsened, green)<br>python_function_len 94->117 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/wepp/interchange/hill_loss_interchange.py` | `python` | `green` | python_file_sloc 141->151 (worsened, green)<br>python_function_len 42->42 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/wepp/interchange/hill_pass_interchange.py` | `python` | `red` | python_file_sloc 388->396 (worsened, green)<br>python_function_len 159->159 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/wepp/interchange/hill_soil_interchange.py` | `python` | `green` | python_file_sloc 325->333 (worsened, green)<br>python_function_len 78->78 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/wepp/interchange/hill_wat_interchange.py` | `python` | `yellow` | python_file_sloc 562->594 (worsened, green)<br>python_function_len 122->122 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/wepp/interchange/totalwatsed3.py` | `python` | `yellow` | python_file_sloc 915->936 (worsened, yellow)<br>python_function_len 146->146 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/wepp/management/utils/multi_ofe.py` | `python` | `yellow` | python_file_sloc 172->335 (worsened, green)<br>python_function_len 125->137 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/controllers_js/__tests__/ag_fields.test.js` | `javascript` | `green` | js_file_sloc 568->738 (worsened, green)<br>js_cc 4->4 (unchanged, green) |
| `wepppy/weppcloud/controllers_js/ag_fields.js` | `javascript` | `yellow` | js_file_sloc 1777->1958 (worsened, yellow)<br>js_cc 18->18 (unchanged, yellow) |

## Hotspots (Current Tree)

### `python_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 5697 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 4232 |
| `tests/nodb/mods/test_roads_controller.py` | 3240 |
| `tests/nodb/mods/test_features_export_service.py` | 3043 |
| `wepppy/nodb/mods/features_export/service.py` | 2998 |
| `tests/nodb/mods/test_omni.py` | 2895 |
| `wepppy/wepp/management/managements.py` | 2548 |
| `wepppy/nodb/core/wepp.py` | 2430 |
| `wepppy/climates/cligen/cligen.py` | 2248 |
| `wepppy/nodb/base.py` | 2213 |

### `python_max_function_len_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 2126 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 2063 |
| `tests/nodb/mods/disturbed/live_e2e/runbook.py` | 768 |
| `wepppy/weppcloud/routes/ui_showcase/ui_showcase_bp.py` | 631 |
| `wepppy/wepp/fuzzing/single_ofe_stratified_campaign.py` | 528 |
| `wepppy/microservices/rq_engine/orchestration_read_routes.py` | 460 |
| `wepppy/nodb/mods/ash_transport/neris_ash_model.py` | 381 |
| `wepppy/rq/wepp_rq_pipeline.py` | 352 |
| `wepppy/nodb/core/landuse.py` | 350 |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 334 |

### `python_max_cc_top20`

_No entries._

### `js_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/weppcloud/controllers_js/omni.js` | 2835 |
| `wepppy/weppcloud/controllers_js/features_export.js` | 2690 |
| `wepppy/weppcloud/controllers_js/map_gl.js` | 2426 |
| `wepppy/weppcloud/controllers_js/project.js` | 2040 |
| `wepppy/weppcloud/controllers_js/ag_fields.js` | 1958 |
| `wepppy/weppcloud/controllers_js/batch_runner.js` | 1911 |
| `wepppy/weppcloud/controllers_js/channel_gl.js` | 1782 |
| `wepppy/weppcloud/controllers_js/geneva_summary_report.js` | 1747 |
| `wepppy/weppcloud/controllers_js/control_base.js` | 1659 |
| `wepppy/weppcloud/controllers_js/subcatchment_delineation.js` | 1636 |

### `js_max_cc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/weppcloud/static/js/gl-dashboard/map/layers.js` | 155 |
| `wepppy/weppcloud/controllers_js/wepp.js` | 93 |
| `wepppy/weppcloud/static/js/gl-dashboard/layers/renderer.js` | 86 |
| `wepppy/weppcloud/static-src/tests/smoke/map-gl.spec.js` | 81 |
| `wepppy/weppcloud/controllers_js/dss_export.js` | 58 |
| `wepppy/weppcloud/controllers_js/control_base.js` | 57 |
| `wepppy/weppcloud/controllers_js/project.js` | 52 |
| `wepppy/weppcloud/static/js/gl-dashboard/graphs/timeseries-graph.js` | 47 |
| `wepppy/weppcloud/controllers_js/features_export.js` | 46 |
| `wepppy/weppcloud/controllers_js/utils.js` | 45 |

## Review Guidance

- This report is observe-only: it does not block merges.
- Use changed-file deltas to spot opportunistic cleanup candidates.
- Prefer incremental reductions when touching hotspot files.
