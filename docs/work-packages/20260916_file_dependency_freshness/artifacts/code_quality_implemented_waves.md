# Code Quality Observability Report

- Mode: `observe-only` (non-blocking)
- Generated (UTC): `2026-09-17T02:41:59Z`
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
| `python_prod_file_sloc` | 1031 | 130.0 | 324.0 | 687.0 | 973.5 | 2075.7 | 5697.0 |
| `python_prod_max_function_len` | 847 | 60.0 | 109.5 | 175.4 | 234.5 | 396.02 | 2233.0 |
| `python_prod_max_cc` | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `js_source_file_sloc` | 214 | 255.5 | 567.0 | 1206.7 | 1592.3 | 2406.48 | 2835.0 |
| `js_source_max_cc` | 214 | 6.0 | 19.75 | 33.0 | 44.35 | 85.35 | 155.0 |

## Changed Files

- Files analyzed: `24`; highest severity red: `3`, yellow: `3`; worsened metric entries: `15` (exceptions: `0`, actionable: `15`)

| File | Lang | Highest | Key Metric Deltas |
| --- | --- | --- | --- |
| `tests/all_your_base/test_file_digest.py` | `python` | `green` | python_file_sloc n/a->141 (new, green)<br>python_function_len n/a->48 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_errors_progress_outputs_routes.py` | `python` | `green` | python_file_sloc 402->430 (worsened, green)<br>python_function_len 71->71 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_postfire_debris_flow.py` | `python` | `green` | python_file_sloc 279->362 (worsened, green)<br>python_function_len 27->27 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_postfire_debris_flow_freshness.py` | `python` | `green` | python_file_sloc n/a->179 (new, green)<br>python_function_len n/a->28 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_postfire_debris_flow_production.py` | `python` | `yellow` | python_file_sloc 513->530 (worsened, green)<br>python_function_len 92->111 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_postfire_debris_flow_runtime_m3.py` | `python` | `green` | python_file_sloc 279->285 (worsened, green)<br>python_function_len 44->44 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_base_boundary_characterization.py` | `python` | `yellow` | python_file_sloc 952->987 (worsened, yellow)<br>python_function_len 78->78 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_batch_climate_rap_contention.py` | `python` | `green` | python_file_sloc 522->566 (worsened, green)<br>python_function_len 47->47 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_derived_file_signature.py` | `python` | `green` | python_file_sloc n/a->100 (new, green)<br>python_function_len n/a->45 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_hydration_snapshot.py` | `python` | `green` | python_file_sloc n/a->127 (new, green)<br>python_function_len n/a->43 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_project_config_registry_serializer.py` | `python` | `green` | python_file_sloc 496->535 (worsened, green)<br>python_function_len 32->32 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/test_context_processors_static_url.py` | `python` | `green` | python_file_sloc 69->90 (worsened, green)<br>python_function_len 34->34 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/utils/test_assets_controllers_gl_build_id.py` | `python` | `green` | python_file_sloc 26->60 (worsened, green)<br>python_function_len 18->18 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/all_your_base/file_digest.py` | `python` | `green` | python_file_sloc n/a->56 (new, green)<br>python_function_len n/a->23 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/postfire_debris_flow_routes.py` | `python` | `green` | python_file_sloc 326->346 (worsened, green)<br>python_function_len 65->65 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | `python` | `red` | python_file_sloc 5274->5272 (improved, red)<br>python_function_len 2233->2233 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/_derived_build.py` | `python` | `green` | python_file_sloc 125->150 (worsened, green)<br>python_function_len 68->68 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/_read_retry.py` | `python` | `green` | python_file_sloc 84->96 (worsened, green)<br>python_function_len 46->46 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/base.py` | `python` | `red` | python_file_sloc 2379->2359 (improved, red)<br>python_function_len 201->201 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/config_builder/registry.py` | `python` | `red` | python_file_sloc 700->687 (improved, yellow)<br>python_function_len 228->228 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/climate_observed_build.py` | `python` | `green` | python_file_sloc 112->112 (unchanged, green)<br>python_function_len 36->36 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/production.py` | `python` | `yellow` | python_file_sloc 598->701 (worsened, yellow)<br>python_function_len 100->109 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/rap/rap_ts_build.py` | `python` | `green` | python_file_sloc 163->163 (unchanged, green)<br>python_function_len 51->51 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/utils/assets.py` | `python` | `green` | python_file_sloc 57->47 (improved, green)<br>python_function_len 37->25 (improved, green)<br>python_cc n/a->n/a (n/a, unknown) |

## Hotspots (Current Tree)

### `python_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 5697 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 5272 |
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
