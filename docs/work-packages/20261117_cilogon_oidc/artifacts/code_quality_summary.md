# Code Quality Observability Report

- Mode: `observe-only` (non-blocking)
- Generated (UTC): `2026-11-17T20:35:51Z`
- Base ref: `874de621c`

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
| `python_prod_file_sloc` | 1175 | 132.0 | 306.0 | 676.2 | 982.7 | 2070.5 | 5907.0 |
| `python_prod_max_function_len` | 987 | 57.0 | 104.0 | 173.8 | 228.0 | 388.1 | 2249.0 |
| `python_prod_max_cc` | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `js_source_file_sloc` | 243 | 239.0 | 536.0 | 1056.4 | 1534.9 | 2319.22 | 2867.0 |
| `js_source_max_cc` | 243 | 6.0 | 19.0 | 31.8 | 41.8 | 83.9 | 155.0 |

## Changed Files

- Files analyzed: `26`; highest severity red: `3`, yellow: `2`; worsened metric entries: `18` (exceptions: `0`, actionable: `18`)

| File | Lang | Highest | Key Metric Deltas |
| --- | --- | --- | --- |
| `tests/microservices/test_rq_engine_auth.py` | `python` | `green` | python_file_sloc 354->365 (worsened, green)<br>python_function_len 31->31 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_wepp_bootstrap_tokens.py` | `python` | `green` | python_file_sloc 118->118 (unchanged, green)<br>python_function_len 32->32 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/bootstrap/test_account_identity.py` | `python` | `green` | python_file_sloc n/a->60 (new, green)<br>python_function_len n/a->11 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_account_security.py` | `python` | `green` | python_file_sloc n/a->283 (new, green)<br>python_function_len n/a->32 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_bootstrap_bp.py` | `python` | `green` | python_file_sloc 379->379 (unchanged, green)<br>python_function_len 33->33 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_security_auth_forms.py` | `python` | `green` | python_file_sloc 296->294 (improved, green)<br>python_function_len 65->65 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_security_oauth_callback.py` | `python` | `green` | python_file_sloc 39->42 (worsened, green)<br>python_function_len 42->45 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_security_oauth_routes.py` | `python` | `green` | python_file_sloc 462->530 (worsened, green)<br>python_function_len 38->45 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_user_profile_contract.py` | `python` | `green` | python_file_sloc 169->178 (worsened, green)<br>python_function_len 33->38 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_user_profile_token.py` | `python` | `yellow` | python_file_sloc 601->618 (worsened, green)<br>python_function_len 93->93 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/test_account_identity_migration.py` | `python` | `green` | python_file_sloc n/a->36 (new, green)<br>python_function_len n/a->20 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/test_configuration.py` | `python` | `green` | python_file_sloc 287->302 (worsened, green)<br>python_function_len 36->36 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/auth.py` | `python` | `green` | python_file_sloc 375->375 (unchanged, green)<br>python_function_len 47->47 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/bootstrap_routes.py` | `python` | `green` | python_file_sloc 577->577 (unchanged, green)<br>python_function_len 71->71 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/wepp_bootstrap_service.py` | `python` | `green` | python_file_sloc 228->230 (worsened, green)<br>python_function_len 37->37 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/observability/secret_profiles.py` | `python` | `green` | python_file_sloc 55->55 (unchanged, green)<br>python_function_len 9->9 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/account_security.py` | `python` | `green` | python_file_sloc n/a->301 (new, green)<br>python_function_len n/a->54 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/app.py` | `python` | `green` | python_file_sloc 493->506 (worsened, green)<br>python_function_len 25->25 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/bootstrap/api_shared.py` | `python` | `green` | python_file_sloc 259->283 (worsened, green)<br>python_function_len 34->37 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/configuration.py` | `python` | `red` | python_file_sloc 366->383 (worsened, green)<br>python_function_len 161->161 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/migrations/versions/a7c1106e42b9_account_identity.py` | `python` | `green` | python_file_sloc n/a->36 (new, green)<br>python_function_len n/a->19 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/_security/oauth.py` | `python` | `red` | python_file_sloc 466->535 (worsened, green)<br>python_function_len 116->154 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/bootstrap.py` | `python` | `green` | python_file_sloc 163->165 (worsened, green)<br>python_function_len 29->31 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/user.py` | `python` | `yellow` | python_file_sloc 894->890 (improved, yellow)<br>python_function_len 90->90 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/weppcloudr.py` | `python` | `red` | python_file_sloc 775->775 (unchanged, yellow)<br>python_function_len 160->160 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/run_catalog/reader.py` | `python` | `green` | python_file_sloc 69->69 (unchanged, green)<br>python_function_len 27->27 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |

## Hotspots (Current Tree)

### `python_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 5907 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 5349 |
| `tests/weppcloud/routes/test_pure_controls_render.py` | 4702 |
| `tests/nodb/mods/test_roads_controller.py` | 3543 |
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
| `wepppy/nodb/mods/roads/roads.py` | 2069 |
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
