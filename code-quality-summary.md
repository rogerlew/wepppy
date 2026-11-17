# Code Quality Observability Report

- Mode: `observe-only` (non-blocking)
- Generated (UTC): `2026-11-17T09:37:06Z`
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
| `python_prod_file_sloc` | 1172 | 132.0 | 305.0 | 676.8 | 984.05 | 2071.25 | 5888.0 |
| `python_prod_max_function_len` | 984 | 57.0 | 104.0 | 174.4 | 228.0 | 388.55 | 2249.0 |
| `python_prod_max_cc` | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `js_source_file_sloc` | 243 | 239.0 | 536.0 | 1056.4 | 1534.9 | 2319.22 | 2867.0 |
| `js_source_max_cc` | 243 | 6.0 | 19.0 | 31.8 | 41.8 | 83.9 | 155.0 |

## Changed Files

- Files analyzed: `82`; highest severity red: `30`, yellow: `22`; worsened metric entries: `84` (exceptions: `0`, actionable: `84`)

| File | Lang | Highest | Key Metric Deltas |
| --- | --- | --- | --- |
| `services/profile_playback/app.py` | `python` | `yellow` | python_file_sloc 829->852 (worsened, yellow)<br>python_function_len 116->116 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_files_routes.py` | `python` | `red` | python_file_sloc 1612->1633 (worsened, red)<br>python_function_len 57->57 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_ag_fields_routes.py` | `python` | `red` | python_file_sloc 1055->1319 (worsened, red)<br>python_function_len 102->102 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_auth.py` | `python` | `green` | python_file_sloc 346->354 (worsened, green)<br>python_function_len 31->31 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_fork_archive_routes.py` | `python` | `red` | python_file_sloc 1322->1584 (worsened, red)<br>python_function_len 142->153 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_omni_routes.py` | `python` | `red` | python_file_sloc 1520->1861 (worsened, red)<br>python_function_len 64->103 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_upload_batch_runner_routes.py` | `python` | `yellow` | python_file_sloc 341->681 (worsened, yellow)<br>python_function_len 55->68 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_sensitive_vector_artifacts.py` | `python` | `green` | python_file_sloc n/a->146 (new, green)<br>python_function_len n/a->28 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_vector_retention_lifecycle.py` | `python` | `green` | python_file_sloc n/a->284 (new, green)<br>python_function_len n/a->35 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_vector_upload_exact_converter.py` | `python` | `green` | python_file_sloc n/a->133 (new, green)<br>python_function_len n/a->52 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_vector_upload_exact_downstream.py` | `python` | `yellow` | python_file_sloc n/a->374 (new, green)<br>python_function_len n/a->91 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_vector_upload_normalization.py` | `python` | `yellow` | python_file_sloc n/a->911 (new, yellow)<br>python_function_len n/a->123 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_vector_upload_session_provenance.py` | `python` | `yellow` | python_file_sloc n/a->268 (new, green)<br>python_function_len n/a->86 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_ag_fields_backend_contract.py` | `python` | `yellow` | python_file_sloc 507->694 (worsened, yellow)<br>python_function_len 74->74 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_omni.py` | `python` | `red` | python_file_sloc 2972->2973 (worsened, red)<br>python_function_len 153->153 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_omni_contrast_build_service.py` | `python` | `green` | python_file_sloc 575->589 (worsened, green)<br>python_function_len 79->79 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_omni_state_contrast_mixin.py` | `python` | `green` | python_file_sloc 129->164 (worsened, green)<br>python_function_len 27->37 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_roads_controller.py` | `python` | `red` | python_file_sloc 3429->3478 (worsened, red)<br>python_function_len 256->256 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_vector_retention_copy_consumers.py` | `python` | `green` | python_file_sloc n/a->357 (new, green)<br>python_function_len n/a->55 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/profile_recorder/test_retained_profile_lifecycle.py` | `python` | `green` | python_file_sloc n/a->293 (new, green)<br>python_function_len n/a->36 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_project_rq_archive.py` | `python` | `yellow` | python_file_sloc 829->1058 (worsened, yellow)<br>python_function_len 47->94 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_project_rq_delete_run.py` | `python` | `yellow` | python_file_sloc 494->581 (worsened, green)<br>python_function_len 119->119 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_vector_archive_recovery.py` | `python` | `green` | python_file_sloc n/a->339 (new, green)<br>python_function_len n/a->61 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_vector_fork_retention.py` | `python` | `green` | python_file_sloc n/a->343 (new, green)<br>python_function_len n/a->41 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_vector_retention_deletion.py` | `python` | `green` | python_file_sloc n/a->323 (new, green)<br>python_function_len n/a->66 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/shape_converter/unit/test_geoparquet_input.py` | `python` | `green` | python_file_sloc n/a->285 (new, green)<br>python_function_len n/a->41 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/tools/test_check_vector_upload_readiness.py` | `python` | `green` | python_file_sloc n/a->126 (new, green)<br>python_function_len n/a->14 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/topo/test_watershed_collection_upload_geometry.py` | `python` | `green` | python_file_sloc n/a->34 (new, green)<br>python_function_len n/a->5 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_archive_dashboard_route.py` | `python` | `green` | python_file_sloc 67->94 (worsened, green)<br>python_function_len 18->18 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_pure_controls_render.py` | `python` | `red` | python_file_sloc 4695->4702 (worsened, red)<br>python_function_len 181->181 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_roads_bp.py` | `python` | `yellow` | python_file_sloc 854->1016 (worsened, yellow)<br>python_function_len 103->139 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/test_batch_runner_endpoints.py` | `python` | `green` | python_file_sloc 210->277 (worsened, green)<br>python_function_len 35->68 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tools/check_vector_upload_readiness.py` | `python` | `green` | python_file_sloc n/a->85 (new, green)<br>python_function_len n/a->77 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tools/reconcile_vector_upload_retention.py` | `python` | `green` | python_file_sloc n/a->31 (new, green)<br>python_function_len n/a->23 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/_gdalinfo.py` | `python` | `green` | python_file_sloc 300->319 (worsened, green)<br>python_function_len 55->56 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/browse/_download.py` | `python` | `yellow` | python_file_sloc 681->727 (worsened, yellow)<br>python_function_len 120->125 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/browse/auth.py` | `python` | `yellow` | python_file_sloc 490->513 (worsened, green)<br>python_function_len 96->106 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/browse/browse.py` | `python` | `red` | python_file_sloc 1364->1421 (worsened, red)<br>python_function_len 109->109 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/browse/dtale.py` | `python` | `red` | python_file_sloc 310->334 (worsened, green)<br>python_function_len 244->264 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/browse/files_api.py` | `python` | `red` | python_file_sloc 969->1006 (worsened, yellow)<br>python_function_len 205->213 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/browse/flow.py` | `python` | `yellow` | python_file_sloc 972->980 (worsened, yellow)<br>python_function_len 148->148 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/browse/listing.py` | `python` | `red` | python_file_sloc 849->858 (worsened, yellow)<br>python_function_len 205->207 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/browse/sensitive_vectors.py` | `python` | `green` | python_file_sloc n/a->98 (new, green)<br>python_function_len n/a->20 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/ag_fields_routes.py` | `python` | `red` | python_file_sloc 1270->1326 (worsened, red)<br>python_function_len 97->97 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/auth.py` | `python` | `green` | python_file_sloc 370->375 (worsened, green)<br>python_function_len 42->47 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | `python` | `red` | python_file_sloc 1578->1827 (worsened, red)<br>python_function_len 647->653 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/omni_routes.py` | `python` | `red` | python_file_sloc 1133->1353 (worsened, red)<br>python_function_len 144->171 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/upload_batch_runner_routes.py` | `python` | `yellow` | python_file_sloc 290->343 (worsened, green)<br>python_function_len 106->135 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/shape_converter/app.py` | `python` | `red` | python_file_sloc 985->1042 (worsened, yellow)<br>python_function_len 213->219 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/shape_converter/convert.py` | `python` | `red` | python_file_sloc 913->1497 (worsened, red)<br>python_function_len 99->128 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/shape_converter/crs.py` | `python` | `yellow` | python_file_sloc 237->244 (worsened, green)<br>python_function_len 80->80 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/shape_converter/parser_provenance.py` | `python` | `green` | python_file_sloc 107->129 (worsened, green)<br>python_function_len 62->62 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/vector_retention_lifecycle.py` | `python` | `yellow` | python_file_sloc n/a->368 (new, green)<br>python_function_len n/a->89 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/vector_upload_normalization.py` | `python` | `red` | python_file_sloc n/a->1848 (new, red)<br>python_function_len n/a->384 (new, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/batch_runner.py` | `python` | `red` | python_file_sloc 1468->1590 (worsened, red)<br>python_function_len 210->228 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/ag_fields/ag_fields.py` | `python` | `red` | python_file_sloc 1759->1839 (worsened, red)<br>python_function_len 165->165 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/omni/omni.py` | `python` | `yellow` | python_file_sloc 1138->1185 (worsened, yellow)<br>python_function_len 82->82 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/omni/omni_clone_contrast_service.py` | `python` | `red` | python_file_sloc 408->429 (worsened, green)<br>python_function_len 204->207 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/omni/omni_contrast_build_service.py` | `python` | `red` | python_file_sloc 1268->1287 (worsened, red)<br>python_function_len 187->187 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/omni/omni_state_contrast_mixin.py` | `python` | `yellow` | python_file_sloc 969->993 (worsened, yellow)<br>python_function_len 54->54 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/roads/roads.py` | `python` | `red` | python_file_sloc 5834->5888 (worsened, red)<br>python_function_len 2052->2052 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/profile_recorder/assembler.py` | `python` | `green` | python_file_sloc 498->511 (worsened, green)<br>python_function_len 72->72 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/profile_recorder/playback.py` | `python` | `yellow` | python_file_sloc 1063->1072 (worsened, yellow)<br>python_function_len 104->104 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/batch_rq.py` | `python` | `red` | python_file_sloc 914->991 (worsened, yellow)<br>python_function_len 208->208 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/project_rq.py` | `python` | `red` | python_file_sloc 2848->2875 (worsened, red)<br>python_function_len 207->214 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/project_rq_archive.py` | `python` | `red` | python_file_sloc 467->747 (worsened, yellow)<br>python_function_len 196->300 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/project_rq_delete.py` | `python` | `red` | python_file_sloc 461->554 (worsened, green)<br>python_function_len 148->210 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/project_rq_fork.py` | `python` | `red` | python_file_sloc 1475->1488 (worsened, red)<br>python_function_len 303->303 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/topo/watershed_collection/__init__.py` | `python` | `green` | python_file_sloc 1->10 (worsened, green)<br>python_function_len n/a->n/a (n/a, unknown)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/topo/watershed_collection/watershed_collection.py` | `python` | `yellow` | python_file_sloc 783->807 (worsened, yellow)<br>python_function_len 99->99 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/wepp/interchange/_roads_lifecycle.py` | `python` | `green` | python_file_sloc 434->459 (worsened, green)<br>python_function_len 57->57 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/configuration.py` | `python` | `red` | python_file_sloc 363->366 (worsened, green)<br>python_function_len 158->161 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/controllers_js/__tests__/ag_fields.test.js` | `javascript` | `green` | js_file_sloc 951->954 (worsened, green)<br>js_cc 4->4 (unchanged, green) |
| `wepppy/weppcloud/controllers_js/__tests__/batch_runner.test.js` | `javascript` | `green` | js_file_sloc 408->410 (worsened, green)<br>js_cc 5->5 (unchanged, green) |
| `wepppy/weppcloud/controllers_js/__tests__/omni.test.js` | `javascript` | `green` | js_file_sloc 458->464 (worsened, green)<br>js_cc 3->3 (unchanged, green) |
| `wepppy/weppcloud/controllers_js/__tests__/roads.test.js` | `javascript` | `green` | js_file_sloc 414->427 (worsened, green)<br>js_cc 4->4 (unchanged, green) |
| `wepppy/weppcloud/controllers_js/ag_fields.js` | `javascript` | `yellow` | js_file_sloc 1997->1997 (unchanged, yellow)<br>js_cc 18->18 (unchanged, yellow) |
| `wepppy/weppcloud/controllers_js/batch_runner.js` | `javascript` | `red` | js_file_sloc 1915->1915 (unchanged, yellow)<br>js_cc 30->30 (unchanged, red) |
| `wepppy/weppcloud/controllers_js/omni.js` | `javascript` | `red` | js_file_sloc 2867->2867 (unchanged, red)<br>js_cc 42->42 (unchanged, red) |
| `wepppy/weppcloud/controllers_js/roads.js` | `javascript` | `yellow` | js_file_sloc 1266->1266 (unchanged, green)<br>js_cc 25->25 (unchanged, yellow) |
| `wepppy/weppcloud/routes/archive_dashboard/archive_dashboard.py` | `python` | `green` | python_file_sloc 100->111 (worsened, green)<br>python_function_len 51->53 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/nodb_api/roads_bp.py` | `python` | `yellow` | python_file_sloc 650->649 (improved, green)<br>python_function_len 138->138 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |

## Hotspots (Current Tree)

### `python_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 5888 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 5349 |
| `tests/weppcloud/routes/test_pure_controls_render.py` | 4702 |
| `tests/nodb/mods/test_roads_controller.py` | 3478 |
| `tests/nodb/mods/test_features_export_service.py` | 3243 |
| `wepppy/nodb/mods/features_export/service.py` | 3139 |
| `tests/nodb/mods/test_omni.py` | 2973 |
| `wepppy/rq/project_rq.py` | 2875 |
| `wepppy/wepp/management/managements.py` | 2660 |
| `wepppy/nodb/base.py` | 2627 |

### `python_max_function_len_top20`

| Path | Value |
| --- | ---: |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 2249 |
| `wepppy/nodb/mods/roads/roads.py` | 2052 |
| `tests/nodb/mods/disturbed/live_e2e/runbook.py` | 768 |
| `tests/scripts/test_deploy_production_execution.py` | 688 |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 653 |
| `wepppy/weppcloud/routes/ui_showcase/ui_showcase_bp.py` | 641 |
| `wepppy/nodb/mods/path_ce/data_prep.py` | 541 |
| `wepppy/wepp/fuzzing/single_ofe_stratified_campaign.py` | 528 |
| `wepppy/microservices/rq_engine/orchestration_read_routes.py` | 470 |
| `wepppy/eu/soils/esdac/esdac.py` | 418 |

### `python_max_cc_top20`

_No entries._

### `js_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/weppcloud/controllers_js/omni.js` | 2867 |
| `wepppy/weppcloud/controllers_js/features_export.js` | 2690 |
| `wepppy/weppcloud/controllers_js/map_gl.js` | 2470 |
| `wepppy/weppcloud/controllers_js/project.js` | 2111 |
| `wepppy/weppcloud/controllers_js/ag_fields.js` | 1997 |
| `wepppy/weppcloud/controllers_js/batch_runner.js` | 1915 |
| `wepppy/weppcloud/controllers_js/channel_gl.js` | 1873 |
| `wepppy/weppcloud/controllers_js/control_base.js` | 1753 |
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
