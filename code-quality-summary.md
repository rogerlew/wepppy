# Code Quality Observability Report

- Mode: `observe-only` (non-blocking)
- Generated (UTC): `2026-08-29T11:41:50Z`
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
| `python_prod_file_sloc` | 982 | 130.5 | 334.5 | 698.4 | 1007.05 | 2140.13 | 5697.0 |
| `python_prod_max_function_len` | 799 | 62.0 | 112.5 | 184.0 | 243.5 | 389.04 | 2233.0 |
| `python_prod_max_cc` | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `js_source_file_sloc` | 207 | 255.0 | 577.0 | 1224.8 | 1598.6 | 2433.58 | 2835.0 |
| `js_source_max_cc` | 207 | 6.0 | 20.0 | 33.0 | 43.4 | 85.7 | 155.0 |

## Changed Files

- Files analyzed: `116`; highest severity red: `28`, yellow: `29`; worsened metric entries: `101` (exceptions: `0`, actionable: `101`)

| File | Lang | Highest | Key Metric Deltas |
| --- | --- | --- | --- |
| `tests/climates/test_cligen_station_catalog_isolation.py` | `python` | `green` | python_file_sloc n/a->45 (new, green)<br>python_function_len n/a->34 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/docker/unit/test_project_config_rollout_contract.py` | `python` | `green` | python_file_sloc n/a->27 (new, green)<br>python_function_len n/a->7 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/eu/soils/test_esdac_build.py` | `python` | `green` | python_file_sloc 29->59 (worsened, green)<br>python_function_len 19->32 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/eu/soils/test_esdac_soil_build.py` | `python` | `green` | python_file_sloc 169->342 (worsened, green)<br>python_function_len 41->50 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_creation_idempotency.py` | `python` | `green` | python_file_sloc n/a->105 (new, green)<br>python_function_len n/a->33 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_auth.py` | `python` | `green` | python_file_sloc 287->313 (worsened, green)<br>python_function_len 31->31 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_bootstrap_routes.py` | `python` | `yellow` | python_file_sloc 1014->1015 (worsened, yellow)<br>python_function_len 142->142 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_builder_routes.py` | `python` | `green` | python_file_sloc n/a->393 (new, green)<br>python_function_len n/a->46 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_climate_routes.py` | `python` | `green` | python_file_sloc 284->594 (worsened, green)<br>python_function_len 48->60 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_landuse_routes.py` | `python` | `red` | python_file_sloc 1749->2183 (worsened, red)<br>python_function_len 92->92 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_openapi_contract.py` | `python` | `yellow` | python_file_sloc 209->321 (worsened, green)<br>python_function_len 39->95 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_orchestration_read_routes.py` | `python` | `yellow` | python_file_sloc 477->664 (worsened, yellow)<br>python_function_len 51->51 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_project_config_update_routes.py` | `python` | `yellow` | python_file_sloc n/a->568 (new, green)<br>python_function_len n/a->88 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_project_routes.py` | `python` | `yellow` | python_file_sloc 585->737 (worsened, yellow)<br>python_function_len 50->50 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_schema_defaults_routes.py` | `python` | `red` | python_file_sloc 954->1622 (worsened, red)<br>python_function_len 66->99 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_soils_routes.py` | `python` | `green` | python_file_sloc 183->329 (worsened, green)<br>python_function_len 38->38 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_upload_climate_routes.py` | `python` | `green` | python_file_sloc 229->401 (worsened, green)<br>python_function_len 46->55 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_wepp_routes.py` | `python` | `red` | python_file_sloc 1375->1507 (worsened, red)<br>python_function_len 85->92 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/baer/test_sbs_coverage_mask.py` | `python` | `green` | python_file_sloc 146->88 (improved, green)<br>python_function_len 35->28 (improved, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/baer/test_sbs_rattlesnake_gdal.py` | `python` | `green` | python_file_sloc n/a->21 (new, green)<br>python_function_len n/a->18 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_climate_catalog.py` | `python` | `yellow` | python_file_sloc 178->194 (worsened, green)<br>python_function_len 90->90 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_climate_input_parser_service.py` | `python` | `green` | python_file_sloc 211->236 (worsened, green)<br>python_function_len 20->20 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_climate_station_catalog_service.py` | `python` | `green` | python_file_sloc 102->168 (worsened, green)<br>python_function_len 20->22 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_config_sanitization.py` | `python` | `green` | python_file_sloc n/a->85 (new, green)<br>python_function_len n/a->16 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_defaults_cfg_compatibility.py` | `python` | `green` | python_file_sloc n/a->129 (new, green)<br>python_function_len n/a->22 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_landuse_build_event_contracts.py` | `python` | `green` | python_file_sloc 120->190 (worsened, green)<br>python_function_len 64->76 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_landuse_catalog.py` | `python` | `green` | python_file_sloc 80->86 (worsened, green)<br>python_function_len 48->48 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_locale_capability_authority.py` | `python` | `yellow` | python_file_sloc n/a->996 (new, yellow)<br>python_function_len n/a->60 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_project_config_builder_snapshot.py` | `python` | `green` | python_file_sloc n/a->60 (new, green)<br>python_function_len n/a->19 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_project_config_capabilities.py` | `python` | `green` | python_file_sloc n/a->520 (new, green)<br>python_function_len n/a->60 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_project_config_preset_snapshot.py` | `python` | `green` | python_file_sloc n/a->305 (new, green)<br>python_function_len n/a->33 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_project_config_reader_foundation.py` | `python` | `green` | python_file_sloc n/a->466 (new, green)<br>python_function_len n/a->35 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_project_config_registry_serializer.py` | `python` | `green` | python_file_sloc n/a->496 (new, green)<br>python_function_len n/a->32 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_project_config_serialization.py` | `python` | `green` | python_file_sloc n/a->83 (new, green)<br>python_function_len n/a->12 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_project_config_update.py` | `python` | `red` | python_file_sloc n/a->1345 (new, red)<br>python_function_len n/a->133 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_soils_gridded_root_creation.py` | `python` | `yellow` | python_file_sloc 798->831 (worsened, yellow)<br>python_function_len 138->138 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_tenerife_climate_catalog_service.py` | `python` | `green` | python_file_sloc 59->77 (worsened, green)<br>python_function_len 21->21 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_wepp_run_payload_grouped_updates.py` | `python` | `yellow` | python_file_sloc 736->743 (worsened, yellow)<br>python_function_len 41->41 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/profile_recorder/stubdeps.py` | `python` | `red` | python_file_sloc 208->208 (unchanged, green)<br>python_function_len 188->188 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_project_config_update_rq.py` | `python` | `green` | python_file_sloc n/a->105 (new, green)<br>python_function_len n/a->36 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_project_rq_archive.py` | `python` | `green` | python_file_sloc 226->413 (worsened, green)<br>python_function_len 34->35 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_project_rq_fork.py` | `python` | `red` | python_file_sloc 1959->2012 (worsened, red)<br>python_function_len 168->168 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_climate_bp.py` | `python` | `red` | python_file_sloc 181->864 (worsened, yellow)<br>python_function_len 82->156 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_config_builder_ui.py` | `python` | `green` | python_file_sloc n/a->118 (new, green)<br>python_function_len n/a->33 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_pure_controls_render.py` | `python` | `red` | python_file_sloc 3549->4086 (worsened, red)<br>python_function_len 118->181 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_rq_engine_token_api.py` | `python` | `yellow` | python_file_sloc 985->986 (worsened, yellow)<br>python_function_len 56->56 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_run_0_builder_maturity.py` | `python` | `green` | python_file_sloc n/a->14 (new, green)<br>python_function_len n/a->6 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_run_0_openet_admin_gate.py` | `python` | `red` | python_file_sloc 1051->1212 (worsened, red)<br>python_function_len 100->100 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_soils_bp.py` | `python` | `green` | python_file_sloc 91->124 (worsened, green)<br>python_function_len 59->60 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/test_ui_foundation_css.py` | `python` | `green` | python_file_sloc 25->32 (worsened, green)<br>python_function_len 13->13 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/test_user_preferences_postgres.py` | `python` | `yellow` | python_file_sloc 406->415 (worsened, green)<br>python_function_len 99->99 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/utils/test_helpers_url_for_run.py` | `python` | `green` | python_file_sloc 40->53 (worsened, green)<br>python_function_len 9->15 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tools/check_project_config_secrets.py` | `python` | `green` | python_file_sloc n/a->29 (new, green)<br>python_function_len n/a->19 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tools/normalize_project_config_sources.py` | `python` | `green` | python_file_sloc n/a->37 (new, green)<br>python_function_len n/a->24 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tools/rq_engine_contract_rules.py` | `python` | `green` | python_file_sloc 142->177 (worsened, green)<br>python_function_len 20->22 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/climates/cligen/cligen.py` | `python` | `red` | python_file_sloc 2318->2324 (worsened, red)<br>python_function_len 276->276 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/eu/soils/soil_build.py` | `python` | `red` | python_file_sloc 298->372 (worsened, green)<br>python_function_len 151->157 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/__init__.py` | `python` | `green` | python_file_sloc 178->182 (worsened, green)<br>python_function_len 55->55 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/auth.py` | `python` | `green` | python_file_sloc 320->351 (worsened, green)<br>python_function_len 39->42 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/builder_routes.py` | `python` | `yellow` | python_file_sloc n/a->291 (new, green)<br>python_function_len n/a->127 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/climate_routes.py` | `python` | `red` | python_file_sloc 414->673 (worsened, yellow)<br>python_function_len 95->225 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/creation_idempotency.py` | `python` | `green` | python_file_sloc n/a->133 (new, green)<br>python_function_len n/a->31 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/landuse_routes.py` | `python` | `red` | python_file_sloc 1432->1634 (worsened, red)<br>python_function_len 191->243 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/orchestration_read_routes.py` | `python` | `red` | python_file_sloc 1283->1505 (worsened, red)<br>python_function_len 460->470 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/project_config_update_routes.py` | `python` | `yellow` | python_file_sloc n/a->669 (new, yellow)<br>python_function_len n/a->115 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/project_routes.py` | `python` | `red` | python_file_sloc 412->586 (worsened, green)<br>python_function_len 231->367 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | `python` | `red` | python_file_sloc 4242->5274 (worsened, red)<br>python_function_len 2073->2233 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/soils_routes.py` | `python` | `yellow` | python_file_sloc 146->222 (worsened, green)<br>python_function_len 73->112 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/upload_climate_routes.py` | `python` | `yellow` | python_file_sloc 140->177 (worsened, green)<br>python_function_len 69->101 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/wepp_routes.py` | `python` | `yellow` | python_file_sloc 301->293 (improved, green)<br>python_function_len 97->97 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/wepp_run_payload.py` | `python` | `red` | python_file_sloc 536->598 (worsened, green)<br>python_function_len 233->293 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/base.py` | `python` | `red` | python_file_sloc 2302->2361 (worsened, red)<br>python_function_len 201->201 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/config_builder/__init__.py` | `python` | `green` | python_file_sloc n/a->43 (new, green)<br>python_function_len n/a->n/a (n/a, unknown)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/config_builder/registry.py` | `python` | `red` | python_file_sloc n/a->690 (new, yellow)<br>python_function_len n/a->218 (new, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/config_builder/resolver.py` | `python` | `red` | python_file_sloc n/a->507 (new, green)<br>python_function_len n/a->156 (new, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/config_builder/schema.py` | `python` | `green` | python_file_sloc n/a->154 (new, green)<br>python_function_len n/a->7 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/config_builder/snapshot.py` | `python` | `green` | python_file_sloc n/a->109 (new, green)<br>python_function_len n/a->37 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/climate_input_parser.py` | `python` | `yellow` | python_file_sloc 203->245 (worsened, green)<br>python_function_len 100->117 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/climate_station_catalog_service.py` | `python` | `green` | python_file_sloc 140->211 (worsened, green)<br>python_function_len 25->52 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/landuse.py` | `python` | `red` | python_file_sloc 1899->1956 (worsened, red)<br>python_function_len 362->362 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/soils.py` | `python` | `red` | python_file_sloc 1959->1964 (worsened, red)<br>python_function_len 218->218 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/locales/__init__.py` | `python` | `green` | python_file_sloc 18->83 (worsened, green)<br>python_function_len n/a->n/a (n/a, unknown)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/locales/capability_graph.py` | `python` | `yellow` | python_file_sloc n/a->896 (new, yellow)<br>python_function_len n/a->119 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/locales/climate_catalog.py` | `python` | `green` | python_file_sloc 285->417 (worsened, green)<br>python_function_len 23->28 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/locales/landuse_catalog.py` | `python` | `green` | python_file_sloc 160->316 (worsened, green)<br>python_function_len 42->48 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/locales/locale_profiles.py` | `python` | `green` | python_file_sloc n/a->391 (new, green)<br>python_function_len n/a->49 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/baer/sbs_map.py` | `python` | `yellow` | python_file_sloc 1041->1043 (worsened, yellow)<br>python_function_len 116->116 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/project_config_capabilities.py` | `python` | `yellow` | python_file_sloc n/a->639 (new, green)<br>python_function_len n/a->145 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/project_config_reader.py` | `python` | `yellow` | python_file_sloc n/a->433 (new, green)<br>python_function_len n/a->106 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/project_config_snapshot.py` | `python` | `yellow` | python_file_sloc n/a->428 (new, green)<br>python_function_len n/a->112 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/project_config_update.py` | `python` | `red` | python_file_sloc n/a->1570 (new, red)<br>python_function_len n/a->124 (new, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/project_config_sanitization.py` | `python` | `green` | python_file_sloc n/a->183 (new, green)<br>python_function_len n/a->43 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/project_config_serialization.py` | `python` | `green` | python_file_sloc n/a->267 (new, green)<br>python_function_len n/a->62 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/project_config_update_rq.py` | `python` | `green` | python_file_sloc n/a->61 (new, green)<br>python_function_len n/a->36 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/project_rq.py` | `python` | `red` | python_file_sloc 2785->2796 (worsened, red)<br>python_function_len 205->205 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/project_rq_archive.py` | `python` | `yellow` | python_file_sloc 346->357 (worsened, green)<br>python_function_len 109->110 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/tools/migrations/unroll_root_resources_batch.py` | `python` | `red` | python_file_sloc 1256->1255 (improved, red)<br>python_function_len 309->309 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/controllers_js/__tests__/config_builder.test.js` | `javascript` | `green` | js_file_sloc n/a->686 (new, green)<br>js_cc n/a->5 (new, green) |
| `wepppy/weppcloud/controllers_js/__tests__/control_base.test.js` | `javascript` | `green` | js_file_sloc 259->292 (worsened, green)<br>js_cc 1->1 (unchanged, green) |
| `wepppy/weppcloud/controllers_js/__tests__/http.test.js` | `javascript` | `green` | js_file_sloc 411->434 (worsened, green)<br>js_cc 5->5 (unchanged, green) |
| `wepppy/weppcloud/controllers_js/__tests__/project.test.js` | `javascript` | `green` | js_file_sloc 1238->1266 (worsened, green)<br>js_cc 6->6 (unchanged, green) |
| `wepppy/weppcloud/controllers_js/__tests__/project_config_update.test.js` | `javascript` | `green` | js_file_sloc n/a->487 (new, green)<br>js_cc n/a->3 (new, green) |
| `wepppy/weppcloud/controllers_js/__tests__/table_overflow_accessibility.test.js` | `javascript` | `green` | js_file_sloc n/a->203 (new, green)<br>js_cc n/a->2 (new, green) |
| `wepppy/weppcloud/controllers_js/config_builder.js` | `javascript` | `yellow` | js_file_sloc n/a->584 (new, green)<br>js_cc n/a->19 (new, yellow) |
| `wepppy/weppcloud/controllers_js/http.js` | `javascript` | `yellow` | js_file_sloc 849->859 (worsened, green)<br>js_cc 26->26 (unchanged, yellow) |
| `wepppy/weppcloud/controllers_js/project.js` | `javascript` | `red` | js_file_sloc 2071->2051 (improved, yellow)<br>js_cc 52->52 (unchanged, red) |
| `wepppy/weppcloud/controllers_js/project_config_update.js` | `javascript` | `yellow` | js_file_sloc n/a->407 (new, green)<br>js_cc n/a->16 (new, yellow) |
| `wepppy/weppcloud/routes/nodb_api/climate_bp.py` | `python` | `yellow` | python_file_sloc 518->848 (worsened, yellow)<br>python_function_len 72->87 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/nodb_api/soils_bp.py` | `python` | `green` | python_file_sloc 124->169 (worsened, green)<br>python_function_len 39->77 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | `python` | `red` | python_file_sloc 1999->2349 (worsened, red)<br>python_function_len 336->391 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/weppcloud_site.py` | `python` | `red` | python_file_sloc 984->989 (worsened, yellow)<br>python_function_len 312->312 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/static-src/tests/smoke/a11y/axe-runs0.spec.js` | `javascript` | `yellow` | js_file_sloc 907->932 (worsened, green)<br>js_cc 17->17 (unchanged, yellow) |
| `wepppy/weppcloud/static-src/tests/smoke/table-overflow-accessibility.spec.js` | `javascript` | `green` | js_file_sloc n/a->109 (new, green)<br>js_cc n/a->2 (new, green) |
| `wepppy/weppcloud/user_preferences.py` | `python` | `green` | python_file_sloc 550->553 (worsened, green)<br>python_function_len 76->76 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/utils/helpers.py` | `python` | `yellow` | python_file_sloc 828->843 (worsened, yellow)<br>python_function_len 125->125 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/utils/rq_engine_token.py` | `python` | `green` | python_file_sloc 43->50 (worsened, green)<br>python_function_len 40->47 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |

## Hotspots (Current Tree)

### `python_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 5697 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 5274 |
| `tests/weppcloud/routes/test_pure_controls_render.py` | 4086 |
| `tests/nodb/mods/test_features_export_service.py` | 3251 |
| `tests/nodb/mods/test_roads_controller.py` | 3240 |
| `wepppy/nodb/mods/features_export/service.py` | 3026 |
| `tests/nodb/mods/test_omni.py` | 2929 |
| `wepppy/rq/project_rq.py` | 2796 |
| `wepppy/wepp/management/managements.py` | 2548 |
| `wepppy/nodb/core/wepp.py` | 2430 |

### `python_max_function_len_top20`

| Path | Value |
| --- | ---: |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 2233 |
| `wepppy/nodb/mods/roads/roads.py` | 2126 |
| `tests/nodb/mods/disturbed/live_e2e/runbook.py` | 768 |
| `wepppy/weppcloud/routes/ui_showcase/ui_showcase_bp.py` | 631 |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 613 |
| `wepppy/nodb/mods/path_ce/data_prep.py` | 541 |
| `wepppy/wepp/fuzzing/single_ofe_stratified_campaign.py` | 528 |
| `wepppy/microservices/rq_engine/orchestration_read_routes.py` | 470 |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 391 |
| `wepppy/eu/soils/esdac/esdac.py` | 389 |

### `python_max_cc_top20`

_No entries._

### `js_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/weppcloud/controllers_js/omni.js` | 2835 |
| `wepppy/weppcloud/controllers_js/features_export.js` | 2690 |
| `wepppy/weppcloud/controllers_js/map_gl.js` | 2458 |
| `wepppy/weppcloud/controllers_js/project.js` | 2051 |
| `wepppy/weppcloud/controllers_js/ag_fields.js` | 1997 |
| `wepppy/weppcloud/controllers_js/batch_runner.js` | 1915 |
| `wepppy/weppcloud/controllers_js/channel_gl.js` | 1873 |
| `wepppy/weppcloud/controllers_js/geneva_summary_report.js` | 1747 |
| `wepppy/weppcloud/controllers_js/control_base.js` | 1746 |
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
