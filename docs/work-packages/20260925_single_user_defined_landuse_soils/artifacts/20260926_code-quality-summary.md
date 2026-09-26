# Code Quality Observability Report

- Mode: `observe-only` (non-blocking)
- Generated (UTC): `2026-09-26T01:57:49Z`
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
| `python_prod_file_sloc` | 1043 | 132.0 | 324.0 | 686.8 | 971.9 | 2092.8 | 5697.0 |
| `python_prod_max_function_len` | 859 | 60.0 | 109.0 | 176.0 | 236.1 | 397.82 | 2243.0 |
| `python_prod_max_cc` | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `js_source_file_sloc` | 214 | 256.0 | 567.0 | 1206.7 | 1592.3 | 2406.48 | 2840.0 |
| `js_source_max_cc` | 214 | 6.0 | 19.75 | 33.0 | 44.35 | 85.35 | 155.0 |

## Changed Files

- Files analyzed: `97`; highest severity red: `29`, yellow: `18`; worsened metric entries: `119` (exceptions: `0`, actionable: `119`)

| File | Lang | Highest | Key Metric Deltas |
| --- | --- | --- | --- |
| `tests/microservices/test_rq_engine_debris_flow_routes.py` | `python` | `green` | python_file_sloc 105->110 (worsened, green)<br>python_function_len 40->40 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_fork_archive_routes.py` | `python` | `red` | python_file_sloc 1331->1336 (worsened, red)<br>python_function_len 125->125 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_omni_routes.py` | `python` | `red` | python_file_sloc 1227->1232 (worsened, red)<br>python_function_len 64->64 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_rusle_routes.py` | `python` | `green` | python_file_sloc 100->105 (worsened, green)<br>python_function_len 44->44 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_soils_routes.py` | `python` | `green` | python_file_sloc 329->338 (worsened, green)<br>python_function_len 38->39 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_treatments_routes.py` | `python` | `green` | python_file_sloc 206->211 (worsened, green)<br>python_function_len 37->37 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_upload_disturbed_routes.py` | `python` | `green` | python_file_sloc 250->255 (worsened, green)<br>python_function_len 47->47 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_single_input_uploads.py` | `python` | `green` | python_file_sloc n/a->73 (new, green)<br>python_function_len n/a->13 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/disturbed/conftest.py` | `python` | `green` | python_file_sloc 57->58 (worsened, green)<br>python_function_len 35->36 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/disturbed/test_sbs_validation.py` | `python` | `green` | python_file_sloc 403->404 (worsened, green)<br>python_function_len 56->56 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/path_ce/test_controller_stages.py` | `python` | `green` | python_file_sloc 186->191 (worsened, green)<br>python_function_len 32->32 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/path_ce/test_report_render_integration.py` | `python` | `green` | python_file_sloc 110->115 (worsened, green)<br>python_function_len 43->43 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_omni.py` | `python` | `red` | python_file_sloc 2929->2933 (worsened, red)<br>python_function_len 153->153 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_omni_build_router_service.py` | `python` | `green` | python_file_sloc 601->602 (worsened, green)<br>python_function_len 51->51 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_omni_facade_contracts.py` | `python` | `green` | python_file_sloc 333->334 (worsened, green)<br>python_function_len 50->50 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_omni_mode_build_services.py` | `python` | `yellow` | python_file_sloc 890->891 (worsened, yellow)<br>python_function_len 81->82 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_landuse_build_event_contracts.py` | `python` | `green` | python_file_sloc 190->193 (worsened, green)<br>python_function_len 76->77 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_landuse_mofe_process_pool.py` | `python` | `yellow` | python_file_sloc 441->442 (worsened, green)<br>python_function_len 119->119 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_landuse_mofe_value_types.py` | `python` | `green` | python_file_sloc 13->14 (worsened, green)<br>python_function_len 12->13 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_mofe_scenario_artifacts.py` | `python` | `yellow` | python_file_sloc 403->405 (worsened, green)<br>python_function_len 79->80 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_project_config_builder_snapshot.py` | `python` | `green` | python_file_sloc 85->115 (worsened, green)<br>python_function_len 25->25 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_project_config_update.py` | `python` | `red` | python_file_sloc 1398->1432 (worsened, red)<br>python_function_len 133->133 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_single_input_artifacts.py` | `python` | `green` | python_file_sloc n/a->94 (new, green)<br>python_function_len n/a->54 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_single_input_policy.py` | `python` | `green` | python_file_sloc n/a->46 (new, green)<br>python_function_len n/a->11 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_single_input_sources.py` | `python` | `green` | python_file_sloc n/a->149 (new, green)<br>python_function_len n/a->15 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/wepp/test_single_input.py` | `python` | `green` | python_file_sloc n/a->228 (new, green)<br>python_function_len n/a->33 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/wepp/test_single_input_references.py` | `python` | `green` | python_file_sloc n/a->166 (new, green)<br>python_function_len n/a->43 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_omni_bp_routes.py` | `python` | `green` | python_file_sloc 178->193 (worsened, green)<br>python_function_len 30->30 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_pure_controls_render.py` | `python` | `red` | python_file_sloc 4423->4458 (worsened, red)<br>python_function_len 181->181 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_run_0_openet_admin_gate.py` | `python` | `red` | python_file_sloc 1234->1254 (worsened, red)<br>python_function_len 100->100 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_soils_bp.py` | `python` | `green` | python_file_sloc 124->139 (worsened, green)<br>python_function_len 60->63 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_treatments_bp.py` | `python` | `green` | python_file_sloc 81->96 (worsened, green)<br>python_function_len 35->38 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_wepp_bp.py` | `python` | `yellow` | python_file_sloc 1084->1098 (worsened, yellow)<br>python_function_len 88->88 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/debris_flow_routes.py` | `python` | `green` | python_file_sloc 127->131 (worsened, green)<br>python_function_len 71->73 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | `python` | `red` | python_file_sloc 1522->1545 (worsened, red)<br>python_function_len 613->631 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/landuse_routes.py` | `python` | `red` | python_file_sloc 1634->1667 (worsened, red)<br>python_function_len 243->261 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/omni_routes.py` | `python` | `yellow` | python_file_sloc 974->984 (worsened, yellow)<br>python_function_len 144->144 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/postfire_debris_flow_routes.py` | `python` | `green` | python_file_sloc 346->349 (worsened, green)<br>python_function_len 65->65 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/rusle_routes.py` | `python` | `green` | python_file_sloc 92->96 (worsened, green)<br>python_function_len 60->62 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | `python` | `red` | python_file_sloc 5272->5282 (worsened, red)<br>python_function_len 2233->2243 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/single_input_uploads.py` | `python` | `green` | python_file_sloc n/a->91 (new, green)<br>python_function_len n/a->27 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/soils_routes.py` | `python` | `yellow` | python_file_sloc 222->241 (worsened, green)<br>python_function_len 112->124 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/treatments_routes.py` | `python` | `yellow` | python_file_sloc 177->181 (worsened, green)<br>python_function_len 112->114 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/upload_disturbed_routes.py` | `python` | `green` | python_file_sloc 164->170 (worsened, green)<br>python_function_len 60->62 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/watershed_routes.py` | `python` | `red` | python_file_sloc 1018->1025 (worsened, yellow)<br>python_function_len 215->221 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/base.py` | `python` | `red` | python_file_sloc 2359->2364 (worsened, red)<br>python_function_len 201->201 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/config_builder/resolver.py` | `python` | `red` | python_file_sloc 507->523 (worsened, green)<br>python_function_len 156->171 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/config_builder/schema.py` | `python` | `green` | python_file_sloc 154->155 (worsened, green)<br>python_function_len 7->7 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/config_builder/snapshot.py` | `python` | `green` | python_file_sloc 109->114 (worsened, green)<br>python_function_len 37->38 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/landuse.py` | `python` | `red` | python_file_sloc 2049->2087 (worsened, red)<br>python_function_len 368->374 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/soils.py` | `python` | `red` | python_file_sloc 1965->2034 (worsened, red)<br>python_function_len 218->218 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/watershed.py` | `python` | `red` | python_file_sloc 1221->1225 (worsened, red)<br>python_function_len 110->110 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/watershed_mixins.py` | `python` | `red` | python_file_sloc 1192->1196 (worsened, yellow)<br>python_function_len 187->188 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/wepp.py` | `python` | `red` | python_file_sloc 2410->2426 (worsened, red)<br>python_function_len 166->168 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/wepp_input_parser.py` | `python` | `yellow` | python_file_sloc 139->144 (worsened, green)<br>python_function_len 139->143 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/wepp_prep_service.py` | `python` | `red` | python_file_sloc 655->659 (worsened, yellow)<br>python_function_len 262->265 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/locales/capability_graph.py` | `python` | `yellow` | python_file_sloc 896->896 (unchanged, yellow)<br>python_function_len 119->119 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/debris_flow/debris_flow.py` | `python` | `yellow` | python_file_sloc 251->253 (worsened, green)<br>python_function_len 134->135 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/disturbed/disturbed.py` | `python` | `red` | python_file_sloc 2355->2359 (worsened, red)<br>python_function_len 382->382 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/omni/omni.py` | `python` | `yellow` | python_file_sloc 1147->1153 (worsened, yellow)<br>python_function_len 80->80 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/path_ce/path_cost_effective.py` | `python` | `yellow` | python_file_sloc 565->570 (worsened, green)<br>python_function_len 109->110 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/postfire_debris_flow.py` | `python` | `green` | python_file_sloc 69->71 (worsened, green)<br>python_function_len 29->29 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/revegetation/revegetation.py` | `python` | `green` | python_file_sloc 107->110 (worsened, green)<br>python_function_len 20->20 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/rusle/rusle.py` | `python` | `red` | python_file_sloc 958->960 (worsened, yellow)<br>python_function_len 192->192 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/treatments/treatments.py` | `python` | `red` | python_file_sloc 693->695 (worsened, yellow)<br>python_function_len 175->176 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/project_config_capabilities.py` | `python` | `yellow` | python_file_sloc 661->661 (unchanged, yellow)<br>python_function_len 147->147 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/project_config_update.py` | `python` | `red` | python_file_sloc 1575->1587 (worsened, red)<br>python_function_len 124->124 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/single_input_artifacts.py` | `python` | `green` | python_file_sloc n/a->34 (new, green)<br>python_function_len n/a->28 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/single_input_policy.py` | `python` | `green` | python_file_sloc n/a->77 (new, green)<br>python_function_len n/a->25 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/single_input_sources.py` | `python` | `green` | python_file_sloc n/a->203 (new, green)<br>python_function_len n/a->69 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/omni_rq.py` | `python` | `red` | python_file_sloc 880->890 (worsened, yellow)<br>python_function_len 285->286 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/path_ce_rq.py` | `python` | `green` | python_file_sloc 90->93 (worsened, green)<br>python_function_len 77->78 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/postfire_debris_flow_rq.py` | `python` | `green` | python_file_sloc 60->63 (worsened, green)<br>python_function_len 33->34 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/project_rq.py` | `python` | `red` | python_file_sloc 2813->2818 (worsened, red)<br>python_function_len 205->205 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/single_input_admission.py` | `python` | `green` | python_file_sloc n/a->66 (new, green)<br>python_function_len n/a->25 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/wepp_rq_stage_prep.py` | `python` | `green` | python_file_sloc 191->192 (worsened, green)<br>python_function_len 58->58 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/wepp/management/managements.py` | `python` | `red` | python_file_sloc 2548->2623 (worsened, red)<br>python_function_len 141->141 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/wepp/management/utils/multi_ofe.py` | `python` | `yellow` | python_file_sloc 335->338 (worsened, green)<br>python_function_len 137->137 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/wepp/single_input.py` | `python` | `green` | python_file_sloc n/a->154 (new, green)<br>python_function_len n/a->44 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/wepp/soils/utils/multi_ofe.py` | `python` | `green` | python_file_sloc 64->64 (unchanged, green)<br>python_function_len 29->29 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/controllers_js/__tests__/config_builder.test.js` | `javascript` | `green` | js_file_sloc 686->698 (worsened, green)<br>js_cc 5->5 (unchanged, green) |
| `wepppy/weppcloud/controllers_js/__tests__/landuse.test.js` | `javascript` | `green` | js_file_sloc 644->674 (worsened, green)<br>js_cc 5->5 (unchanged, green) |
| `wepppy/weppcloud/controllers_js/__tests__/soil.test.js` | `javascript` | `green` | js_file_sloc 174->203 (worsened, green)<br>js_cc 3->3 (unchanged, green) |
| `wepppy/weppcloud/controllers_js/config_builder.js` | `javascript` | `yellow` | js_file_sloc 584->594 (worsened, green)<br>js_cc 19->19 (unchanged, yellow) |
| `wepppy/weppcloud/controllers_js/landuse.js` | `javascript` | `red` | js_file_sloc 921->940 (worsened, green)<br>js_cc 44->44 (unchanged, red) |
| `wepppy/weppcloud/controllers_js/soil.js` | `javascript` | `red` | js_file_sloc 429->447 (worsened, green)<br>js_cc 32->32 (unchanged, red) |
| `wepppy/weppcloud/feature_registry/runtime.py` | `python` | `green` | python_file_sloc 220->221 (worsened, green)<br>python_function_len 68->69 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/nodb_api/debris_flow_bp.py` | `python` | `green` | python_file_sloc 32->34 (worsened, green)<br>python_function_len 22->22 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py` | `python` | `yellow` | python_file_sloc 657->695 (worsened, yellow)<br>python_function_len 127->129 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/nodb_api/landuse_bp.py` | `python` | `green` | python_file_sloc 626->627 (worsened, green)<br>python_function_len 55->55 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/nodb_api/omni_bp.py` | `python` | `yellow` | python_file_sloc 291->302 (worsened, green)<br>python_function_len 113->115 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/nodb_api/path_ce_bp.py` | `python` | `green` | python_file_sloc 226->238 (worsened, green)<br>python_function_len 63->65 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/nodb_api/project_bp.py` | `python` | `green` | python_file_sloc 586->600 (worsened, green)<br>python_function_len 70->70 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/nodb_api/soils_bp.py` | `python` | `yellow` | python_file_sloc 169->185 (worsened, green)<br>python_function_len 77->86 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/nodb_api/treatments_bp.py` | `python` | `green` | python_file_sloc 30->34 (worsened, green)<br>python_function_len 31->33 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | `python` | `red` | python_file_sloc 1342->1345 (worsened, red)<br>python_function_len 113->113 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | `python` | `red` | python_file_sloc 2421->2430 (worsened, red)<br>python_function_len 402->410 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |

## Hotspots (Current Tree)

### `python_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 5697 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 5282 |
| `tests/weppcloud/routes/test_pure_controls_render.py` | 4458 |
| `tests/nodb/mods/test_roads_controller.py` | 3240 |
| `tests/nodb/mods/test_features_export_service.py` | 3209 |
| `wepppy/nodb/mods/features_export/service.py` | 3099 |
| `tests/nodb/mods/test_omni.py` | 2933 |
| `wepppy/rq/project_rq.py` | 2818 |
| `wepppy/wepp/management/managements.py` | 2623 |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 2430 |

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
| `wepppy/microservices/rq_engine/project_routes.py` | 412 |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 410 |

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
