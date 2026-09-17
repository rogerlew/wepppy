# Code Quality Observability Report

- Mode: `observe-only` (non-blocking)
- Generated (UTC): `2026-09-17T07:28:45Z`
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
| `python_prod_file_sloc` | 1037 | 133.0 | 328.0 | 686.4 | 973.2 | 2069.28 | 5697.0 |
| `python_prod_max_function_len` | 853 | 60.0 | 109.0 | 175.8 | 236.4 | 395.24 | 2233.0 |
| `python_prod_max_cc` | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `js_source_file_sloc` | 214 | 255.5 | 567.0 | 1206.7 | 1592.3 | 2406.48 | 2835.0 |
| `js_source_max_cc` | 214 | 6.0 | 19.75 | 33.0 | 44.35 | 85.35 | 155.0 |

## Changed Files

- Files analyzed: `76`; highest severity red: `12`, yellow: `17`; worsened metric entries: `59` (exceptions: `0`, actionable: `59`)

| File | Lang | Highest | Key Metric Deltas |
| --- | --- | --- | --- |
| `tests/all_your_base/test_file_digest.py` | `python` | `green` | python_file_sloc n/a->141 (new, green)<br>python_function_len n/a->48 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_browse_dtale.py` | `python` | `green` | python_file_sloc 442->437 (improved, green)<br>python_function_len 75->74 (improved, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_dtale_freshness.py` | `python` | `green` | python_file_sloc n/a->244 (new, green)<br>python_function_len n/a->27 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_errors_progress_outputs_routes.py` | `python` | `green` | python_file_sloc 402->430 (worsened, green)<br>python_function_len 71->71 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_postfire_debris_flow.py` | `python` | `green` | python_file_sloc 279->362 (worsened, green)<br>python_function_len 27->27 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/baer/test_sbs_native_required.py` | `python` | `green` | python_file_sloc 82->84 (worsened, green)<br>python_function_len 24->24 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/geneva/test_geneva_cache_freshness.py` | `python` | `green` | python_file_sloc n/a->233 (new, green)<br>python_function_len n/a->31 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/geneva/test_geneva_collaborators.py` | `python` | `yellow` | python_file_sloc 851->854 (worsened, yellow)<br>python_function_len 109->109 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/geneva/test_geneva_hru_map_geometry_service.py` | `python` | `green` | python_file_sloc 112->103 (improved, green)<br>python_function_len 43->45 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_features_export_dependency_tracker.py` | `python` | `yellow` | python_file_sloc 477->503 (worsened, green)<br>python_function_len 117->117 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_features_export_freshness.py` | `python` | `green` | python_file_sloc n/a->198 (new, green)<br>python_function_len n/a->35 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_features_export_openfilegdb.py` | `python` | `green` | python_file_sloc 192->192 (unchanged, green)<br>python_function_len 50->50 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_features_export_service.py` | `python` | `red` | python_file_sloc 3251->3209 (improved, red)<br>python_function_len 116->116 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_omni_run_orchestration_service.py` | `python` | `yellow` | python_file_sloc 441->443 (worsened, green)<br>python_function_len 146->147 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_omni_sbs_freshness.py` | `python` | `green` | python_file_sloc n/a->139 (new, green)<br>python_function_len n/a->20 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_postfire_debris_flow_freshness.py` | `python` | `green` | python_file_sloc n/a->205 (new, green)<br>python_function_len n/a->28 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_postfire_debris_flow_production.py` | `python` | `yellow` | python_file_sloc 513->532 (worsened, green)<br>python_function_len 92->111 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_postfire_debris_flow_runtime_m3.py` | `python` | `green` | python_file_sloc 279->299 (worsened, green)<br>python_function_len 44->47 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_base_boundary_characterization.py` | `python` | `yellow` | python_file_sloc 952->987 (worsened, yellow)<br>python_function_len 78->78 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_batch_climate_rap_contention.py` | `python` | `green` | python_file_sloc 522->566 (worsened, green)<br>python_function_len 47->47 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_cli_parquet_lineage.py` | `python` | `green` | python_file_sloc n/a->349 (new, green)<br>python_function_len n/a->42 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_climate_artifact_export_service.py` | `python` | `green` | python_file_sloc 405->409 (worsened, green)<br>python_function_len 55->55 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_derived_file_signature.py` | `python` | `green` | python_file_sloc n/a->100 (new, green)<br>python_function_len n/a->45 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_hydration_snapshot.py` | `python` | `green` | python_file_sloc n/a->127 (new, green)<br>python_function_len n/a->43 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_landuse_coverage_area_source.py` | `python` | `yellow` | python_file_sloc 446->450 (worsened, green)<br>python_function_len 95->95 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_landuse_mofe_freshness.py` | `python` | `green` | python_file_sloc n/a->151 (new, green)<br>python_function_len n/a->42 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_project_config_registry_serializer.py` | `python` | `green` | python_file_sloc 496->535 (worsened, green)<br>python_function_len 32->32 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/profile_recorder/conftest.py` | `python` | `green` | python_file_sloc 9->10 (worsened, green)<br>python_function_len 6->6 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/profile_recorder/test_sbs_seed.py` | `python` | `green` | python_file_sloc n/a->136 (new, green)<br>python_function_len n/a->26 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_project_rq_archive.py` | `python` | `green` | python_file_sloc 475->549 (worsened, green)<br>python_function_len 47->47 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/test_raster_freshness.py` | `python` | `green` | python_file_sloc n/a->256 (new, green)<br>python_function_len n/a->22 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/wepp/reports/test_average_annuals_by_landuse.py` | `python` | `yellow` | python_file_sloc 104->74 (improved, green)<br>python_function_len 81->81 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/wepp/reports/test_report_cache_freshness.py` | `python` | `green` | python_file_sloc n/a->605 (new, green)<br>python_function_len n/a->40 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/test_context_processors_static_url.py` | `python` | `green` | python_file_sloc 69->90 (worsened, green)<br>python_function_len 34->34 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/utils/test_assets_controllers_gl_build_id.py` | `python` | `green` | python_file_sloc 26->60 (worsened, green)<br>python_function_len 18->18 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/all_your_base/file_digest.py` | `python` | `green` | python_file_sloc n/a->56 (new, green)<br>python_function_len n/a->23 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/all_your_base/raster_freshness.py` | `python` | `green` | python_file_sloc n/a->203 (new, green)<br>python_function_len n/a->51 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/climates/cli_parquet.py` | `python` | `green` | python_file_sloc n/a->187 (new, green)<br>python_function_len n/a->33 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/postfire_debris_flow_routes.py` | `python` | `green` | python_file_sloc 326->346 (worsened, green)<br>python_function_len 65->65 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | `python` | `red` | python_file_sloc 5274->5272 (improved, red)<br>python_function_len 2233->2233 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/_derived_build.py` | `python` | `green` | python_file_sloc 125->150 (worsened, green)<br>python_function_len 68->68 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/_read_retry.py` | `python` | `green` | python_file_sloc 84->96 (worsened, green)<br>python_function_len 46->46 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/base.py` | `python` | `red` | python_file_sloc 2379->2359 (improved, red)<br>python_function_len 201->201 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/config_builder/registry.py` | `python` | `red` | python_file_sloc 700->687 (improved, yellow)<br>python_function_len 228->228 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/climate_artifact_export_service.py` | `python` | `red` | python_file_sloc 441->448 (worsened, green)<br>python_function_len 218->218 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/climate_observed_build.py` | `python` | `green` | python_file_sloc 112->112 (unchanged, green)<br>python_function_len 36->36 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/landuse.py` | `python` | `red` | python_file_sloc 2026->2020 (improved, red)<br>python_function_len 362->362 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/baer/sbs_map.py` | `python` | `yellow` | python_file_sloc 789->795 (worsened, yellow)<br>python_function_len 116->116 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/features_export/dependency_tracker.py` | `python` | `green` | python_file_sloc 506->520 (worsened, green)<br>python_function_len 66->66 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/features_export/exporters/geodatabase.py` | `python` | `yellow` | python_file_sloc 204->198 (improved, green)<br>python_function_len 85->81 (improved, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/features_export/readme_builder.py` | `python` | `yellow` | python_file_sloc 427->430 (worsened, green)<br>python_function_len 80->83 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/features_export/service.py` | `python` | `red` | python_file_sloc 3026->3099 (worsened, red)<br>python_function_len 290->290 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/geneva/collaborators/_cache_freshness.py` | `python` | `green` | python_file_sloc n/a->208 (new, green)<br>python_function_len n/a->35 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/geneva/collaborators/hru_map_geometry_service.py` | `python` | `yellow` | python_file_sloc 302->335 (worsened, green)<br>python_function_len 82->97 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/geneva/collaborators/hsg_assignment_service.py` | `python` | `green` | python_file_sloc 179->210 (worsened, green)<br>python_function_len 52->70 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/omni/omni.py` | `python` | `yellow` | python_file_sloc 1141->1147 (worsened, yellow)<br>python_function_len 80->80 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/omni/omni_clone_contrast_service.py` | `python` | `red` | python_file_sloc 402->404 (worsened, green)<br>python_function_len 204->204 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/omni/omni_mode_build_services.py` | `python` | `red` | python_file_sloc 539->542 (worsened, green)<br>python_function_len 320->323 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/omni/omni_run_orchestration_service.py` | `python` | `red` | python_file_sloc 487->551 (worsened, green)<br>python_function_len 217->265 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/omni/omni_sbs_freshness.py` | `python` | `green` | python_file_sloc n/a->252 (new, green)<br>python_function_len n/a->40 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/omni/omni_station_catalog_service.py` | `python` | `green` | python_file_sloc 223->217 (improved, green)<br>python_function_len 60->60 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/production.py` | `python` | `yellow` | python_file_sloc 598->732 (worsened, yellow)<br>python_function_len 100->110 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/rainfall_io.py` | `python` | `green` | python_file_sloc 304->330 (worsened, green)<br>python_function_len 66->66 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/rap/rap_ts_build.py` | `python` | `green` | python_file_sloc 163->163 (unchanged, green)<br>python_function_len 51->51 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/skeletonize.py` | `python` | `green` | python_file_sloc 129->130 (worsened, green)<br>python_function_len 39->39 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/profile_recorder/assembler.py` | `python` | `green` | python_file_sloc 480->495 (worsened, green)<br>python_function_len 65->72 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/profile_recorder/playback.py` | `python` | `yellow` | python_file_sloc 1030->1055 (worsened, yellow)<br>python_function_len 95->100 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/profile_recorder/sbs_seed.py` | `python` | `green` | python_file_sloc n/a->168 (new, green)<br>python_function_len n/a->52 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/omni_rq.py` | `python` | `red` | python_file_sloc 840->880 (worsened, yellow)<br>python_function_len 261->285 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/project_rq_archive.py` | `python` | `yellow` | python_file_sloc 357->381 (worsened, green)<br>python_function_len 110->120 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/webservices/dtale/dtale.py` | `python` | `red` | python_file_sloc 1013->1135 (worsened, yellow)<br>python_function_len 156->177 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/wepp/interchange/_utils.py` | `python` | `yellow` | python_file_sloc 234->238 (worsened, green)<br>python_function_len 111->104 (improved, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/wepp/reports/_cache_freshness.py` | `python` | `green` | python_file_sloc n/a->175 (new, green)<br>python_function_len n/a->34 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/wepp/reports/average_annuals_by_landuse.py` | `python` | `yellow` | python_file_sloc 118->239 (worsened, green)<br>python_function_len 80->81 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/wepp/reports/hillslope_watbal.py` | `python` | `green` | python_file_sloc 262->353 (worsened, green)<br>python_function_len 65->78 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/utils/assets.py` | `python` | `green` | python_file_sloc 57->47 (improved, green)<br>python_function_len 37->25 (improved, green)<br>python_cc n/a->n/a (n/a, unknown) |

## Hotspots (Current Tree)

### `python_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 5697 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 5272 |
| `tests/weppcloud/routes/test_pure_controls_render.py` | 4392 |
| `tests/nodb/mods/test_roads_controller.py` | 3240 |
| `tests/nodb/mods/test_features_export_service.py` | 3209 |
| `wepppy/nodb/mods/features_export/service.py` | 3099 |
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
