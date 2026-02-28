# Phase 6 Validation Log

Start (UTC): 2026-02-27T16:37:25Z

INFO:wctl2:docker compose exec weppcloud bash -lc cd /workdir/wepppy && PYTHONPATH=/workdir/wepppy MYPY_CACHE_DIR=/tmp/mypy_cache /opt/venv/bin/pytest tests --maxfail=1
============================= test session starts ==============================
platform linux -- Python 3.12.12, pytest-8.4.2, pluggy-1.6.0
rootdir: /workdir/wepppy
plugins: reportlog-0.4.0, timeout-2.4.0, cov-7.0.0, libtmux-0.47.0, dash-2.9.3, anyio-4.12.1
collected 2096 items / 2 skipped

tests/all_your_base/geo/test_vrt.py .................                    [  0%]
tests/all_your_base/test_geo_get_utm_zone.py .                           [  0%]
tests/climate/test_climate_scaling.py sssssss                            [  1%]
tests/climates/daymet/test_daymet_singlelocation_client.py ..            [  1%]
tests/climates/noaa/test_atlas14_download.py ssss                        [  1%]
tests/climates/test_cligen_geojson_export.py .                           [  1%]
tests/climates/test_cligen_station_search.py .                           [  1%]
tests/config/test_secrets.py .....                                       [  1%]
tests/culverts/test_culvert_batch_rq.py ....                             [  2%]
tests/culverts/test_culvert_orchestration.py ....                        [  2%]
tests/culverts/test_culverts_runner.py .......                           [  2%]
tests/culverts/test_download_skeletons_script.py ...                     [  2%]
tests/culverts/test_watershed_feature_crs.py ..                          [  2%]
tests/disturbed/test_disturbed_matrix.py ............................... [  4%]
....................                                                     [  5%]
tests/eu/soils/test_esdac_build.py .                                     [  5%]
tests/integration/test_cross_service_auth_lifecycle.py ...F

=================================== FAILURES ===================================
_____ test_lifecycle__mx_l4_grouped_cookie_round_trip_from_issue_to_browse _____

grouped_integration_run = IntegrationRun(runid='upset-reckoning;;omni;;undisturbed', config='disturbed9002', wd=PosixPath('/tmp/pytest-of-unknown/pytest-61/test_lifecycle__mx_l4_grouped_0/grouped-run'))
issue_user_token = <function issue_user_token.<locals>._issue at 0x74624c12ae80>
rq_engine_client = <starlette.testclient.TestClient object at 0x746230650cb0>
browse_client = <starlette.testclient.TestClient object at 0x746168726690>

    def test_lifecycle__mx_l4_grouped_cookie_round_trip_from_issue_to_browse(
        grouped_integration_run,
        issue_user_token,
        rq_engine_client,
        browse_client,
    ) -> None:
        bearer_token = issue_user_token(
            runs=(grouped_integration_run.runid,),
            scopes=("rq:status",),
        )
        grouped_runid_url = quote(grouped_integration_run.runid, safe="")
    
        issue_response = rq_engine_client.post(
            f"/api/runs/{grouped_runid_url}/{grouped_integration_run.config}/session-token",
            headers=_auth_header(bearer_token),
        )
>       assert issue_response.status_code == 200
E       assert 500 == 200
E        +  where 500 = <Response [500 Internal Server Error]>.status_code

tests/integration/test_cross_service_auth_lifecycle.py:218: AssertionError
------------------------------ Captured log call -------------------------------
ERROR    wepppy.microservices.rq_engine.session_routes:session_routes.py:562 rq-engine session token issuance failed
Traceback (most recent call last):
  File "/workdir/wepppy/wepppy/microservices/rq_engine/session_routes.py", line 480, in issue_session_token
    authorize_run_access(claims, runid)
  File "/workdir/wepppy/wepppy/microservices/rq_engine/auth.py", line 244, in authorize_run_access
    _authorize_user_claims(claims, runid)
  File "/workdir/wepppy/wepppy/microservices/rq_engine/auth.py", line 162, in _authorize_user_claims
    wd = get_wd(auth_runid, prefer_active=False)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/workdir/wepppy/tests/integration/conftest.py", line 182, in _get_wd
    raise FileNotFoundError(requested_runid)
FileNotFoundError: upset-reckoning
=============================== warnings summary ===============================
../../opt/venv/lib/python3.12/site-packages/pytz/tzinfo.py:27
  /opt/venv/lib/python3.12/site-packages/pytz/tzinfo.py:27: DeprecationWarning:
  
  datetime.datetime.utcfromtimestamp() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.fromtimestamp(timestamp, datetime.UTC).

../../opt/venv/lib/python3.12/site-packages/pyparsing.py:108
  /opt/venv/lib/python3.12/site-packages/pyparsing.py:108: DeprecationWarning:
  
  module 'sre_constants' is deprecated

../../opt/venv/lib/python3.12/site-packages/passlib/utils/__init__.py:854
  /opt/venv/lib/python3.12/site-packages/passlib/utils/__init__.py:854: DeprecationWarning:
  
  'crypt' is deprecated and slated for removal in Python 3.13

wepppy/profile_recorder/assembler.py:14
  /workdir/wepppy/wepppy/profile_recorder/assembler.py:14: DeprecationWarning:
  
  __package__ != __spec__.parent

../../opt/venv/lib/python3.12/site-packages/flask_security/core.py:1426
  /opt/venv/lib/python3.12/site-packages/flask_security/core.py:1426: DeprecationWarning:
  
  The ConfirmRegisterForm and the confirm_register_form option are deprecated as of version 5.6.0 and will be removed in a future release.

../../opt/venv/lib/python3.12/site-packages/flask_security/core.py:1426
  /opt/venv/lib/python3.12/site-packages/flask_security/core.py:1426: DeprecationWarning:
  
  The RegisterForm is deprecated as of version 5.6.0 and will be removed in a future release. The form RegisterFormV2 should be sub-classed instead.

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/integration/test_cross_service_auth_lifecycle.py::test_lifecycle__mx_l4_grouped_cookie_round_trip_from_issue_to_browse
!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
====== 1 failed, 102 passed, 13 skipped, 6 warnings in 179.18s (0:02:59) =======
INFO:wctl2:docker compose exec weppcloud bash -lc cd /workdir/wepppy && PYTHONPATH=/workdir/wepppy MYPY_CACHE_DIR=/tmp/mypy_cache /opt/venv/bin/pytest tests --maxfail=1
============================= test session starts ==============================
platform linux -- Python 3.12.12, pytest-8.4.2, pluggy-1.6.0
rootdir: /workdir/wepppy
plugins: reportlog-0.4.0, timeout-2.4.0, cov-7.0.0, libtmux-0.47.0, dash-2.9.3, anyio-4.12.1
collected 2096 items / 2 skipped

tests/all_your_base/geo/test_vrt.py .................                    [  0%]
tests/all_your_base/test_geo_get_utm_zone.py .                           [  0%]
tests/climate/test_climate_scaling.py sssssss                            [  1%]
tests/climates/daymet/test_daymet_singlelocation_client.py ..            [  1%]
tests/climates/noaa/test_atlas14_download.py ssss                        [  1%]
tests/climates/test_cligen_geojson_export.py .                           [  1%]
tests/climates/test_cligen_station_search.py .                           [  1%]
tests/config/test_secrets.py .....                                       [  1%]
tests/culverts/test_culvert_batch_rq.py ....                             [  2%]
tests/culverts/test_culvert_orchestration.py ....                        [  2%]
tests/culverts/test_culverts_runner.py .......                           [  2%]
tests/culverts/test_download_skeletons_script.py ...                     [  2%]
tests/culverts/test_watershed_feature_crs.py ..                          [  2%]
tests/disturbed/test_disturbed_matrix.py ............................... [  4%]
....................                                                     [  5%]
tests/eu/soils/test_esdac_build.py .                                     [  5%]
tests/integration/test_cross_service_auth_lifecycle.py ....              [  5%]
tests/integration/test_cross_service_auth_portability.py ......          [  5%]
tests/locales/earth/soils/test_isric_crs_workaround.py .........         [  6%]
tests/locales/earth/test_copernicus_retrieve.py .......                  [  6%]
tests/microservices/test_browse_auth_routes.py ......................... [  7%]
............................................................             [ 10%]
tests/microservices/test_browse_dtale.py s.s.s                           [ 10%]
tests/microservices/test_browse_routes.py .......                        [ 11%]
tests/microservices/test_browse_security.py .............                [ 11%]
tests/microservices/test_download.py ...                                 [ 11%]
tests/microservices/test_dss_preview.py .                                [ 11%]
tests/microservices/test_elevationquery.py ....                          [ 12%]
tests/microservices/test_files_routes.py ............................... [ 13%]
.............................................................            [ 16%]
tests/microservices/test_rq_engine_admin_job_routes.py ....              [ 16%]
tests/microservices/test_rq_engine_ash_routes.py .........               [ 17%]
tests/microservices/test_rq_engine_auth.py ............................. [ 18%]
                                                                         [ 18%]
tests/microservices/test_rq_engine_batch_routes.py ........              [ 18%]
tests/microservices/test_rq_engine_bootstrap_routes.py ................  [ 19%]
tests/microservices/test_rq_engine_climate_routes.py .....               [ 19%]
tests/microservices/test_rq_engine_culverts.py ..................        [ 20%]
tests/microservices/test_rq_engine_debris_flow_routes.py .....           [ 20%]
tests/microservices/test_rq_engine_dss_export_routes.py ..               [ 21%]
tests/microservices/test_rq_engine_export_routes.py .....                [ 21%]
tests/microservices/test_rq_engine_fork_archive_routes.py .............. [ 21%]
....                                                                     [ 22%]
tests/microservices/test_rq_engine_jobinfo.py .......................    [ 23%]
tests/microservices/test_rq_engine_landuse_routes.py .....               [ 23%]
tests/microservices/test_rq_engine_landuse_soils_routes.py ...           [ 23%]
tests/microservices/test_rq_engine_migration_routes.py ....              [ 23%]
tests/microservices/test_rq_engine_nodir_boundary_helpers.py ........... [ 24%]
.........                                                                [ 24%]
tests/microservices/test_rq_engine_omni_routes.py ...................... [ 25%]
.....................                                                    [ 26%]
tests/microservices/test_rq_engine_openapi_contract.py .........         [ 27%]
tests/microservices/test_rq_engine_openet_ts_routes.py ..                [ 27%]
tests/microservices/test_rq_engine_project_routes.py .......             [ 27%]
tests/microservices/test_rq_engine_rap_ts_routes.py ..                   [ 27%]
tests/microservices/test_rq_engine_rhem_routes.py .                      [ 27%]
tests/microservices/test_rq_engine_run_sync_routes.py ...                [ 28%]
tests/microservices/test_rq_engine_session_routes.py ................... [ 28%]
....                                                                     [ 29%]
tests/microservices/test_rq_engine_soils_routes.py ...                   [ 29%]
tests/microservices/test_rq_engine_treatments_routes.py .....            [ 29%]
tests/microservices/test_rq_engine_upload_batch_runner_routes.py ..      [ 29%]
tests/microservices/test_rq_engine_upload_climate_routes.py ...          [ 29%]
tests/microservices/test_rq_engine_upload_disturbed_routes.py ..         [ 29%]
tests/microservices/test_rq_engine_upload_huc_fire_routes.py ...         [ 29%]
tests/microservices/test_rq_engine_watershed_routes.py ................. [ 30%]
..                                                                       [ 30%]
tests/microservices/test_rq_engine_wepp_routes.py .........              [ 31%]
tests/nodb/mods/baer/test_sbs_classify_comprehensive.py ................ [ 32%]
...........                                                              [ 32%]
tests/nodb/mods/baer/test_sbs_map_classify_validation.py ............    [ 33%]
tests/nodb/mods/baer/test_sbs_map_extended.py .......................... [ 34%]
......                                                                   [ 34%]
tests/nodb/mods/openet/test_openet_ts.py ...                             [ 34%]
tests/nodb/mods/test_ash_transport_run_ash.py ...                        [ 34%]
tests/nodb/mods/test_disturbed_uniform_sbs.py ...................        [ 35%]
tests/nodb/mods/test_disturbed_validate_sbs_4class.py .                  [ 35%]
tests/nodb/mods/test_lookup_disturbed_class.py ..............            [ 36%]
tests/nodb/mods/test_observed_processing.py ...                          [ 36%]
tests/nodb/mods/test_omni.py ........................................... [ 38%]
.................                                                        [ 39%]
tests/nodb/mods/test_omni_artifact_export_service.py ........            [ 39%]
tests/nodb/mods/test_omni_build_router_service.py ...................    [ 40%]
tests/nodb/mods/test_omni_contrast_build_service.py .....                [ 41%]
tests/nodb/mods/test_omni_facade_contracts.py ............               [ 41%]
tests/nodb/mods/test_omni_input_parser_service.py ......                 [ 41%]
tests/nodb/mods/test_omni_mode_build_services.py ..............          [ 42%]
tests/nodb/mods/test_omni_run_orchestration_service.py .....             [ 42%]
tests/nodb/mods/test_omni_scaling_service.py .......                     [ 43%]
tests/nodb/mods/test_omni_state_contrast_mixin.py ....                   [ 43%]
tests/nodb/mods/test_omni_station_catalog_service.py ..........          [ 43%]
tests/nodb/mods/test_path_ce_model.py .....                              [ 44%]
tests/nodb/mods/test_path_ce_solver.py ....                              [ 44%]
tests/nodb/mods/test_path_cost_effective.py .....                        [ 44%]
tests/nodb/mods/test_swat_interchange.py ........                        [ 44%]
tests/nodb/mods/test_treatments_build.py ...                             [ 45%]
tests/nodb/test_base_boundary_characterization.py ......                 [ 45%]
tests/nodb/test_base_file_handler_cleanup.py ............                [ 45%]
tests/nodb/test_base_misc.py ...............................             [ 47%]
tests/nodb/test_base_unit.py ...........                                 [ 47%]
tests/nodb/test_batch_runner.py ....                                     [ 48%]
tests/nodb/test_build_climate_race_conditions.py .......                 [ 48%]
tests/nodb/test_climate_artifact_export_service.py .......               [ 48%]
tests/nodb/test_climate_build_helpers.py ..........                      [ 49%]
tests/nodb/test_climate_build_router_services.py .........               [ 49%]
tests/nodb/test_climate_catalog.py .....                                 [ 49%]
tests/nodb/test_climate_facade_collaborators.py .........                [ 50%]
tests/nodb/test_climate_gridmet_multiple_build_service.py ...            [ 50%]
tests/nodb/test_climate_input_parser_service.py .....                    [ 50%]
tests/nodb/test_climate_scaling_service.py ..........                    [ 51%]
tests/nodb/test_climate_station_catalog_service.py ....                  [ 51%]
tests/nodb/test_climate_type_hints.py ....                               [ 51%]
tests/nodb/test_climate_user_defined_station_meta_service.py ...         [ 51%]
tests/nodb/test_disturbed_management_overrides.py ..                     [ 51%]
tests/nodb/test_iter_nodb_mods_subclasses.py .                           [ 51%]
tests/nodb/test_landuse_catalog.py ...                                   [ 52%]
tests/nodb/test_landuse_mofe_value_types.py .                            [ 52%]
tests/nodb/test_landuse_raster_wait.py ..                                [ 52%]
tests/nodb/test_lock_race_conditions.py .................                [ 53%]
tests/nodb/test_locked.py ......                                         [ 53%]
tests/nodb/test_path_ce_data_loader.py .........                         [ 53%]
tests/nodb/test_rap_report.py .                                          [ 53%]
tests/nodb/test_ron_fetch_dem_copernicus.py ......                       [ 54%]
tests/nodb/test_ron_fetch_dem_rate_limit.py ......                       [ 54%]
tests/nodb/test_ron_map.py .ss.s                                         [ 54%]
tests/nodb/test_root_dir_materialization.py ......                       [ 54%]
tests/nodb/test_soils_gridded_root_creation.py .....                     [ 55%]
tests/nodb/test_type_hints.py .....                                      [ 55%]
tests/nodb/test_unitizer_preferences.py ....                             [ 55%]
tests/nodb/test_user_defined_cli_parquet.py ...                          [ 55%]
tests/nodb/test_watershed_lookup_loaders.py ....                         [ 55%]
tests/nodb/test_wepp_bootstrap_tokens.py ..                              [ 55%]
tests/nodb/test_wepp_has_run_interchange.py ..                           [ 56%]
tests/nodb/test_wepp_input_parser.py ...........                         [ 56%]
tests/profile_recorder/test_assembler.py ..                              [ 56%]
tests/profile_recorder/test_expectations.py ....                         [ 56%]
tests/profile_recorder/test_playback_session.py ......                   [ 57%]
tests/profile_recorder/test_profile_recorder.py ....                     [ 57%]
tests/query_engine/test_activate.py ..........                           [ 57%]
tests/query_engine/test_benchmarks.py ..                                 [ 57%]
tests/query_engine/test_context.py ........                              [ 58%]
tests/query_engine/test_core.py ..................                       [ 59%]
tests/query_engine/test_formatter.py .                                   [ 59%]
tests/query_engine/test_mcp_auth.py .........                            [ 59%]
tests/query_engine/test_mcp_openapi_contract.py ..                       [ 59%]
tests/query_engine/test_mcp_router.py ..............................     [ 61%]
tests/query_engine/test_server_routes.py ......                          [ 61%]
tests/query_engine/test_storm_event_analyzer.py ........                 [ 61%]
tests/rq/test_batch_rq_delete_batch.py ...                               [ 61%]
tests/rq/test_bootstrap_autocommit_rq.py ........                        [ 62%]
tests/rq/test_bootstrap_enable_rq.py ..                                  [ 62%]
tests/rq/test_culvert_rq_helpers.py ....                                 [ 62%]
tests/rq/test_culvert_rq_manifest.py ..                                  [ 62%]
tests/rq/test_culvert_rq_nodir_guards.py ...                             [ 62%]
tests/rq/test_culvert_rq_pipeline.py ..                                  [ 62%]
tests/rq/test_dependency_graph_tools.py ................                 [ 63%]
tests/rq/test_exception_logging.py ..                                    [ 63%]
tests/rq/test_job_info.py ...                                            [ 63%]
tests/rq/test_jobinfo_payloads.py ............                           [ 64%]
tests/rq/test_land_and_soil_rq_guards.py ....                            [ 64%]
tests/rq/test_omni_rq.py ..........                                      [ 65%]
tests/rq/test_path_ce_rq.py ...                                          [ 65%]
tests/rq/test_project_rq_archive.py ........                             [ 65%]
tests/rq/test_project_rq_archive_helpers.py ...                          [ 65%]
tests/rq/test_project_rq_ash.py ...                                      [ 66%]
tests/rq/test_project_rq_debris_flow.py ....                             [ 66%]
tests/rq/test_project_rq_delete_run.py ...                               [ 66%]
tests/rq/test_project_rq_fork.py ......                                  [ 66%]
tests/rq/test_project_rq_mutation_guards.py ...........                  [ 67%]
tests/rq/test_project_rq_readonly.py ....                                [ 67%]
tests/rq/test_run_sync_rq.py .                                           [ 67%]
tests/rq/test_wepp_rq_dss_helpers.py ....                                [ 67%]
tests/rq/test_wepp_rq_pipeline.py ...                                    [ 67%]
tests/rq/test_wepp_rq_stage_post.py ....                                 [ 67%]
tests/rq/test_weppcloudr_rq.py ...                                       [ 68%]
tests/sbs_map/test_sbs_map.py .....                                      [ 68%]
tests/services/test_wmesque_retrieve.py ..s                              [ 68%]
tests/soils/test_ssurgo.py sssss...                                      [ 68%]
tests/soils/test_wepppyo3_nodata_guard.py .                              [ 68%]
tests/test_0_imports.py .......s....                                     [ 69%]
tests/test_2_validate_managements.py ..........                          [ 69%]
tests/test_all_your_base.py ...........                                  [ 70%]
tests/test_all_your_base_dateutils.py ...............                    [ 71%]
tests/test_all_your_base_hydro.py .....                                  [ 71%]
tests/test_all_your_base_objective_functions.py ..........               [ 71%]
tests/test_all_your_base_stats.py ...                                    [ 72%]
tests/test_imports.py .                                                  [ 72%]
tests/test_managements_module.py ..........                              [ 72%]
tests/test_observability_correlation.py ...............                  [ 73%]
tests/test_redis_settings.py .................                           [ 74%]
tests/test_webclients_elevation.py .....s                                [ 74%]
tests/test_wepp_top_translator.py ............                           [ 74%]
tests/tools/test_check_broad_exceptions.py .............                 [ 75%]
tests/tools/test_check_test_isolation.py .......                         [ 75%]
tests/tools/test_code_quality_observability.py ......                    [ 76%]
tests/tools/test_endpoint_inventory_guard.py .                           [ 76%]
tests/tools/test_migrations_parquet_backfill.py .............            [ 76%]
tests/tools/test_migrations_runner.py .                                  [ 76%]
tests/tools/test_route_contract_checklist_guard.py .                     [ 76%]
tests/topo/test_peridot_runner_wait.py ..                                [ 77%]
tests/topo/test_topaz_subprocess_guards.py ...                           [ 77%]
tests/topo/test_topaz_vrt_read.py .                                      [ 77%]
tests/topo/test_watershed_feature_save_geojson.py ..                     [ 77%]
tests/wepp/interchange/test_calendar_utils.py .                          [ 77%]
tests/wepp/interchange/test_catalog_scan_rust.py .                       [ 77%]
tests/wepp/interchange/test_ebe_interchange.py ...                       [ 77%]
tests/wepp/interchange/test_element_interchange.py ...                   [ 77%]
tests/wepp/interchange/test_hec_ras_boundary.py .                        [ 77%]
tests/wepp/interchange/test_loss_interchange.py ..                       [ 77%]
tests/wepp/interchange/test_pass_cli_hint.py .                           [ 77%]
tests/wepp/interchange/test_pass_interchange.py .....                    [ 78%]
tests/wepp/interchange/test_soil_interchange.py .......                  [ 78%]
tests/wepp/interchange/test_totalwatsed3.py .                            [ 78%]
tests/wepp/interchange/test_versioning.py ....                           [ 78%]
tests/wepp/interchange/test_wat_interchange.py ..                        [ 78%]
tests/wepp/interchange/test_watershed_chan_interchange.py .              [ 78%]
tests/wepp/interchange/test_watershed_chan_peak_interchange.py .         [ 78%]
tests/wepp/interchange/test_watershed_chanwb_interchange.py .            [ 78%]
tests/wepp/interchange/test_watershed_ebe_interchange.py ...             [ 79%]
tests/wepp/interchange/test_watershed_loss_interchange.py .              [ 79%]
tests/wepp/interchange/test_watershed_pass_interchange.py s              [ 79%]
tests/wepp/interchange/test_watershed_pass_interchange_parser.py ..      [ 79%]
tests/wepp/interchange/test_watershed_soil_interchange.py s....          [ 79%]
tests/wepp/interchange/test_watershed_totalwatsed_export.py ..           [ 79%]
tests/wepp/management/test_multiple_ofe.py .                             [ 79%]
tests/wepp/management/test_rotation_stack.py ....                        [ 79%]
tests/wepp/reports/test_average_annuals_by_landuse.py .                  [ 79%]
tests/wepp/reports/test_channel_watbal.py .                              [ 79%]
tests/wepp/reports/test_frq_flood.py .                                   [ 80%]
tests/wepp/reports/test_harness_stub.py .                                [ 80%]
tests/wepp/reports/test_hillslope_watbal.py ..                           [ 80%]
tests/wepp/reports/test_loss_reports.py ......                           [ 80%]
tests/wepp/reports/test_return_periods_dataset.py ...                    [ 80%]
tests/wepp/reports/test_sediment_characteristics.py .                    [ 80%]
tests/wepp/reports/test_total_watbal.py ..                               [ 80%]
tests/wepp/soils/utils/test_wepp_soil_util.py ........                   [ 81%]
tests/wepp/test_wepp_facade_collaborators.py ........                    [ 81%]
tests/wepp/test_wepp_frost_opts.py .......                               [ 81%]
tests/wepp/test_wepp_prep_managements_rap_ts.py .                        [ 81%]
tests/wepp/test_wepp_regressions.py ..                                   [ 81%]
tests/wepp/test_wepp_run_watershed_interchange_options.py .              [ 82%]
tests/wepp/test_wepp_runner_outputs.py .                                 [ 82%]
tests/wepp_runner/test_run_hillslope_retries.py ..                       [ 82%]
tests/weppcloud/bootstrap/test_enable_jobs.py .....                      [ 82%]
tests/weppcloud/bootstrap/test_pre_receive.py ..........                 [ 82%]
tests/weppcloud/controllers_js/test_status_stream_js.py .                [ 82%]
tests/weppcloud/controllers_js/test_unitizer_client_js.py ..             [ 83%]
tests/weppcloud/controllers_js/test_unitizer_map_builder.py ........     [ 83%]
tests/weppcloud/routes/test_archive_dashboard_route.py ...               [ 83%]
tests/weppcloud/routes/test_batch_runner_create_route.py ..              [ 83%]
tests/weppcloud/routes/test_batch_runner_snapshot.py .                   [ 83%]
tests/weppcloud/routes/test_blueprint_registration.py .                  [ 83%]
tests/weppcloud/routes/test_bootstrap_auth_integration.py .....          [ 83%]
tests/weppcloud/routes/test_bootstrap_bp.py ................             [ 84%]
tests/weppcloud/routes/test_cap_verify.py .                              [ 84%]
tests/weppcloud/routes/test_climate_bp.py ........                       [ 85%]
tests/weppcloud/routes/test_command_bar_mcp_token.py .                   [ 85%]
tests/weppcloud/routes/test_csrf_rollout.py ......                       [ 85%]
tests/weppcloud/routes/test_debris_flow_bp.py .                          [ 85%]
tests/weppcloud/routes/test_disturbed_bp.py ...............              [ 86%]
tests/weppcloud/routes/test_exception_logging_routes.py .                [ 86%]
tests/weppcloud/routes/test_gl_dashboard_batch_route.py ...              [ 86%]
tests/weppcloud/routes/test_gl_dashboard_route.py ................       [ 87%]
tests/weppcloud/routes/test_interchange_bp.py ...                        [ 87%]
tests/weppcloud/routes/test_landing_template.py .                        [ 87%]
tests/weppcloud/routes/test_landuse_bp.py ........                       [ 87%]
tests/weppcloud/routes/test_observed_bp.py .....                         [ 88%]
tests/weppcloud/routes/test_omni_bp.py ...                               [ 88%]
tests/weppcloud/routes/test_omni_bp_routes.py ....                       [ 88%]
tests/weppcloud/routes/test_path_ce_bp.py .......                        [ 88%]
tests/weppcloud/routes/test_project_bp.py ...............                [ 89%]
tests/weppcloud/routes/test_pure_controls_render.py .......              [ 89%]
tests/weppcloud/routes/test_rangeland_cover_bp.py .......                [ 90%]
tests/weppcloud/routes/test_rhem_bp.py ......                            [ 90%]
tests/weppcloud/routes/test_rq_engine_token_api.py ....................  [ 91%]
tests/weppcloud/routes/test_run_0_nocfg_auth_bridge.py ................. [ 92%]
........                                                                 [ 92%]
tests/weppcloud/routes/test_run_0_openet_admin_gate.py ....              [ 92%]
tests/weppcloud/routes/test_run_context.py ...                           [ 92%]
tests/weppcloud/routes/test_security_logging_role_cache.py ..            [ 92%]
tests/weppcloud/routes/test_soils_bp.py ...                              [ 93%]
tests/weppcloud/routes/test_team_bp.py .........                         [ 93%]
tests/weppcloud/routes/test_test_bp.py ...                               [ 93%]
tests/weppcloud/routes/test_treatments_bp.py ....                        [ 93%]
tests/weppcloud/routes/test_unitizer_bp.py ..                            [ 93%]
tests/weppcloud/routes/test_user_meta_boundaries.py .                    [ 93%]
tests/weppcloud/routes/test_user_profile_token.py ........               [ 94%]
tests/weppcloud/routes/test_user_runs_admin_scope.py .........           [ 94%]
tests/weppcloud/routes/test_watar_bp.py ..                               [ 94%]
tests/weppcloud/routes/test_wepp_bp.py .............                     [ 95%]
tests/weppcloud/test_auth_tokens.py ............                         [ 96%]
tests/weppcloud/test_batch_runner_endpoints.py ........                  [ 96%]
tests/weppcloud/test_compile_dot_logs.py ..                              [ 96%]
tests/weppcloud/test_config_logging.py ...                               [ 96%]
tests/weppcloud/test_configuration.py .............                      [ 97%]
tests/weppcloud/test_controllers_gl_build_id_global.py .                 [ 97%]
tests/weppcloud/test_gl_dashboard_template.py .                          [ 97%]
tests/weppcloud/test_omni_report_templates.py ...                        [ 97%]
tests/weppcloud/test_registration_name_validation.py ....                [ 97%]
tests/weppcloud/test_security_email_templates.py .                       [ 97%]
tests/weppcloud/test_stale_controllers_gl_template_wiring.py .......     [ 98%]
tests/weppcloud/test_watershed_sub_intersection.py .                     [ 98%]
tests/weppcloud/utils/test_assets_controllers_gl_build_id.py ..          [ 98%]
tests/weppcloud/utils/test_helpers_authorize.py ........                 [ 98%]
tests/weppcloud/utils/test_helpers_paths.py ...............              [ 99%]
tests/weppcloud/utils/test_helpers_url_for_run.py ....                   [ 99%]
tests/weppcloud/utils/test_runid.py ...                                  [ 99%]
tests/weppcloud/utils/test_uploads.py ......                             [100%]

=============================== warnings summary ===============================
../../opt/venv/lib/python3.12/site-packages/pytz/tzinfo.py:27
  /opt/venv/lib/python3.12/site-packages/pytz/tzinfo.py:27: DeprecationWarning:
  
  datetime.datetime.utcfromtimestamp() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.fromtimestamp(timestamp, datetime.UTC).

../../opt/venv/lib/python3.12/site-packages/pyparsing.py:108
  /opt/venv/lib/python3.12/site-packages/pyparsing.py:108: DeprecationWarning:
  
  module 'sre_constants' is deprecated

../../opt/venv/lib/python3.12/site-packages/passlib/utils/__init__.py:854
  /opt/venv/lib/python3.12/site-packages/passlib/utils/__init__.py:854: DeprecationWarning:
  
  'crypt' is deprecated and slated for removal in Python 3.13

wepppy/profile_recorder/assembler.py:14
  /workdir/wepppy/wepppy/profile_recorder/assembler.py:14: DeprecationWarning:
  
  __package__ != __spec__.parent

../../opt/venv/lib/python3.12/site-packages/flask_security/core.py:1426
  /opt/venv/lib/python3.12/site-packages/flask_security/core.py:1426: DeprecationWarning:
  
  The ConfirmRegisterForm and the confirm_register_form option are deprecated as of version 5.6.0 and will be removed in a future release.

../../opt/venv/lib/python3.12/site-packages/flask_security/core.py:1426
  /opt/venv/lib/python3.12/site-packages/flask_security/core.py:1426: DeprecationWarning:
  
  The RegisterForm is deprecated as of version 5.6.0 and will be removed in a future release. The form RegisterFormV2 should be sub-classed instead.

tests/microservices/test_files_routes.py::test_files_pattern_literal_underscore_percent
tests/microservices/test_files_routes.py::test_files_sort_stability_matches_manifest
tests/microservices/test_files_routes.py::test_files_manifest_cached_flag
tests/microservices/test_files_routes.py::test_files_meta_skips_cached_flag
tests/microservices/test_files_routes.py::test_files_manifest_pattern_filtering
tests/microservices/test_files_routes.py::test_files_dotfiles_hidden_by_default
  /workdir/wepppy/wepppy/microservices/browse/listing.py:249: DeprecationWarning:
  
  datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).

tests/microservices/test_rq_engine_bootstrap_routes.py::test_bootstrap_checkout_invalid_json_payload_falls_back_to_missing_sha
tests/microservices/test_rq_engine_jobinfo.py::test_jobinfo_batch_uses_query_args_when_payload_invalid
tests/microservices/test_rq_engine_omni_routes.py::test_run_omni_invalid_json_returns_400
tests/microservices/test_rq_engine_omni_routes.py::test_run_omni_contrasts_invalid_json_returns_400
tests/microservices/test_rq_engine_omni_routes.py::test_run_omni_contrasts_dry_run_invalid_json_returns_400
tests/query_engine/test_mcp_router.py::test_validate_query_invalid_json
  /opt/venv/lib/python3.12/site-packages/httpx/_content.py:204: DeprecationWarning:
  
  Use 'content=<...>' to upload raw bytes/text content.

tests/microservices/test_rq_engine_session_routes.py::test_session_token_issues_with_cookie
tests/microservices/test_rq_engine_session_routes.py::test_session_token_private_run_requires_authenticated_cookie_session
tests/microservices/test_rq_engine_session_routes.py::test_session_token_stale_remember_cookie_includes_relogin_guidance
  /opt/venv/lib/python3.12/site-packages/httpx/_client.py:822: DeprecationWarning:
  
  Setting per-request cookies=<...> is being deprecated, because the expected behaviour on cookie persistence is ambiguous. Set cookies directly on the client instance instead.

tests/nodb/mods/test_swat_interchange.py::test_run_swat_persists_interchange_summary
  /workdir/wepppy/wepppy/nodb/mods/swat/swat.py:585: DeprecationWarning:
  
  datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).

tests/nodb/mods/test_swat_interchange.py::test_run_swat_persists_interchange_summary
  /workdir/wepppy/wepppy/nodb/mods/swat/swat.py:592: DeprecationWarning:
  
  datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).

tests/nodb/mods/test_swat_interchange.py::test_run_swat_persists_interchange_summary
tests/nodb/mods/test_swat_interchange.py::test_interchange_status_partial_from_skipped
tests/nodb/mods/test_swat_interchange.py::test_interchange_error_clears_summary
tests/nodb/mods/test_swat_interchange.py::test_interchange_failed_status_from_version_manifest
tests/nodb/mods/test_swat_interchange.py::test_interchange_manifest_fallback
tests/nodb/mods/test_swat_interchange.py::test_interchange_manifest_fallback_skips_historical_run
  /workdir/wepppy/wepppy/nodb/mods/swat/swat.py:748: DeprecationWarning:
  
  datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).

tests/nodb/test_climate_artifact_export_service.py::test_export_cli_precip_frequency_csv_writes_recurrence_limited_by_years
  /workdir/wepppy/wepppy/nodb/core/climate_artifact_export_service.py:242: DeprecationWarning:
  
  datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).

tests/nodb/test_user_defined_cli_parquet.py::test_set_user_defined_cli_refreshes_cli_parquet
tests/nodb/test_user_defined_cli_parquet.py::test_set_user_defined_cli_refreshes_cli_parquet
tests/nodb/test_user_defined_cli_parquet.py::test_set_user_defined_cli_refreshes_cli_parquet
tests/nodb/test_user_defined_cli_parquet.py::test_set_user_defined_cli_refreshes_cli_parquet
tests/nodb/test_user_defined_cli_parquet.py::test_set_user_defined_cli_delegates_station_meta_builder
tests/nodb/test_user_defined_cli_parquet.py::test_set_user_defined_cli_delegates_station_meta_builder
tests/nodb/test_user_defined_cli_parquet.py::test_set_user_defined_cli_delegates_station_meta_builder
tests/nodb/test_user_defined_cli_parquet.py::test_set_user_defined_cli_delegates_station_meta_builder
  /workdir/wepppy/wepppy/climates/cligen/cligen.py:1227: DeprecationWarning:
  
  In future, it will be an error for 'np.bool_' scalars to be interpreted as an index

tests/nodb/test_watershed_lookup_loaders.py::test_hillslope_width_falls_back_when_lookup_missing_topaz_id
  /workdir/wepppy/wepppy/nodb/core/watershed_mixins.py:917: DeprecationWarning:
  
  Call to deprecated method _deprecated_width_of.

tests/query_engine/test_mcp_openapi_contract.py: 1 warning
tests/query_engine/test_mcp_router.py: 57 warnings
tests/query_engine/test_server_routes.py: 6 warnings
  /opt/venv/lib/python3.12/site-packages/starlette/applications.py:239: DeprecationWarning:
  
  The `middleware` decorator is deprecated, and will be removed in version 1.0.0. Refer to https://starlette.dev/middleware/#using-middleware for recommended approach.

tests/query_engine/test_server_routes.py::test_query_endpoint_accepts_trailing_slash
tests/query_engine/test_server_routes.py::test_query_endpoint_accepts_trailing_slash
  /opt/venv/lib/python3.12/site-packages/starlette/templating.py:162: DeprecationWarning:
  
  The `name` is not the first parameter anymore. The first parameter should be the `Request` instance.
  Replace `TemplateResponse(name, {"request": request})` by `TemplateResponse(request, name)`.

tests/rq/test_exception_logging.py: 2 warnings
tests/rq/test_land_and_soil_rq_guards.py: 2 warnings
tests/rq/test_omni_rq.py: 2 warnings
tests/rq/test_path_ce_rq.py: 2 warnings
tests/rq/test_project_rq_archive.py: 5 warnings
tests/rq/test_project_rq_ash.py: 2 warnings
tests/rq/test_project_rq_debris_flow.py: 2 warnings
tests/rq/test_project_rq_mutation_guards.py: 9 warnings
tests/rq/test_project_rq_readonly.py: 1 warning
  /workdir/wepppy/wepppy/rq/exception_logging.py:35: DeprecationWarning:
  
  datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).

tests/rq/test_project_rq_archive.py::test_archive_rq_preserves_nodir_cache_entries
  /workdir/wepppy/wepppy/rq/project_rq_archive.py:193: DeprecationWarning:
  
  datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).

tests/rq/test_wepp_rq_dss_helpers.py::test_write_dss_channel_geojson_writes_filtered_channels_with_metadata
  /workdir/wepppy/wepppy/rq/wepp_rq_dss.py:208: DeprecationWarning:
  
  datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).

tests/test_imports.py::test_imports_in_directory
  <frozen importlib._bootstrap>:488: RuntimeWarning:
  
  numpy.ndarray size changed, may indicate binary incompatibility. Expected 16 from C header, got 96 from PyObject

tests/test_imports.py::test_imports_in_directory
  /usr/local/lib/python3.12/importlib/__init__.py:90: DeprecationWarning:
  
  wepppy.webservices.wmesque is deprecated; use wepppy.webservices.wmesque2 instead.

tests/wepp/interchange/test_pass_interchange.py::test_write_parquet_with_pool_concurrent
tests/wepp/interchange/test_pass_interchange.py::test_write_parquet_with_pool_concurrent
tests/wepp/interchange/test_pass_interchange.py::test_write_parquet_with_pool_falls_back_when_tmp_invalid
tests/weppcloud/bootstrap/test_pre_receive.py::test_pre_receive_logs_push_for_multi_ofe_slp
tests/weppcloud/bootstrap/test_pre_receive.py::test_pre_receive_new_ref_logs_only_introduced_commits
  /usr/local/lib/python3.12/multiprocessing/popen_fork.py:66: DeprecationWarning:
  
  This process (pid=45004) is multi-threaded, use of fork() may lead to deadlocks in the child.

tests/weppcloud/routes/test_exception_logging_routes.py::test_logged_blueprint_logs_route_exception
  /workdir/wepppy/wepppy/weppcloud/routes/_common.py:109: DeprecationWarning:
  
  datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).

tests/weppcloud/routes/test_user_runs_admin_scope.py::test_runs_users_requires_admin_role
tests/weppcloud/routes/test_user_runs_admin_scope.py::test_runs_users_returns_user_table_for_admin
tests/weppcloud/routes/test_user_runs_admin_scope.py::test_runs_catalog_ignores_alias_for_non_admin
tests/weppcloud/routes/test_user_runs_admin_scope.py::test_runs_catalog_applies_alias_for_admin
tests/weppcloud/routes/test_user_runs_admin_scope.py::test_runs_map_data_applies_alias_for_admin
tests/weppcloud/routes/test_user_runs_admin_scope.py::test_runs_catalog_skips_missing_run_metadata_and_logs_boundary
tests/weppcloud/routes/test_user_runs_admin_scope.py::test_runs_map_data_skips_missing_run_metadata_and_logs_boundary
tests/weppcloud/routes/test_user_runs_admin_scope.py::test_runs_catalog_skips_run_metadata_load_errors_and_logs_warning_boundary
tests/weppcloud/routes/test_user_runs_admin_scope.py::test_runs_map_data_skips_run_metadata_load_errors_and_logs_warning_boundary
  /workdir/wepppy/tests/weppcloud/routes/test_user_runs_admin_scope.py:118: DeprecationWarning:
  
  datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
========== 2069 passed, 29 skipped, 151 warnings in 348.77s (0:05:48) ==========
Broad exception handler changed-file enforcement

Repo root: /home/workdir/wepppy
Base ref: origin/master
Merge base: a073eb2b94792bf8a41ff38caa2f9388deef06fb
Path filter: wepppy, services
Allowlist source: /home/workdir/wepppy/docs/standards/broad-exception-boundary-allowlist.md
Changed Python files scanned: 62

Files:
  M wepppy/climates/climatena_ca/__init__.py
  M wepppy/export/ermit_input.py
  M wepppy/export/gpkg_export.py
  M wepppy/export/prep_details.py
  M wepppy/microservices/_gdalinfo.py
  M wepppy/microservices/browse/_download.py
  M wepppy/microservices/browse/browse.py
  M wepppy/microservices/browse/dtale.py
  M wepppy/microservices/browse/files_api.py
  M wepppy/microservices/browse/listing.py
  M wepppy/microservices/rq_engine/ash_routes.py
  M wepppy/microservices/rq_engine/climate_routes.py
  M wepppy/microservices/rq_engine/debris_flow_routes.py
  M wepppy/microservices/rq_engine/export_routes.py
  M wepppy/microservices/rq_engine/landuse_routes.py
  M wepppy/microservices/rq_engine/omni_routes.py
  M wepppy/microservices/rq_engine/project_routes.py
  M wepppy/microservices/rq_engine/soils_routes.py
  M wepppy/microservices/rq_engine/treatments_routes.py
  M wepppy/microservices/rq_engine/upload_climate_routes.py
  M wepppy/microservices/rq_engine/upload_huc_fire_routes.py
  M wepppy/microservices/rq_engine/watershed_routes.py
  M wepppy/nodb/batch_runner.py
  M wepppy/nodb/core/landuse.py
  M wepppy/nodb/core/ron.py
  M wepppy/nodb/core/soils.py
  M wepppy/nodb/core/watershed.py
  M wepppy/nodb/core/watershed_mixins.py
  M wepppy/nodb/core/wepp.py
  M wepppy/nodb/duckdb_agents.py
  M wepppy/nodb/mods/ash_transport/ash.py
  M wepppy/nodb/mods/disturbed/disturbed.py
  M wepppy/nodb/mods/omni/omni.py
  M wepppy/nodb/mods/omni/omni_clone_contrast_service.py
  M wepppy/nodb/mods/omni/omni_mode_build_services.py
  M wepppy/nodb/mods/omni/omni_station_catalog_service.py
  M wepppy/nodb/mods/path_ce/data_loader.py
  M wepppy/nodb/mods/swat/swat.py
  M wepppy/nodb/mods/swat/swat_connectivity_mixin.py
  M wepppy/nodb/mods/swat/swat_recall_mixin.py
  M wepppy/nodb/mods/swat/swat_txtinout_mixin.py
  M wepppy/query_engine/activate.py
  M wepppy/rq/culvert_rq.py
  M wepppy/rq/culvert_rq_manifest.py
  M wepppy/rq/land_and_soil_rq.py
  M wepppy/rq/omni_rq.py
  M wepppy/rq/path_ce_rq.py
  M wepppy/rq/project_rq.py
  M wepppy/rq/project_rq_archive.py
  M wepppy/rq/project_rq_fork.py
  M wepppy/rq/wepp_rq.py
  M wepppy/rq/wepp_rq_stage_helpers.py
  M wepppy/tools/migrations/landuse.py
  M wepppy/tools/migrations/nodir_bulk.py
  M wepppy/tools/migrations/soils.py
  M wepppy/tools/migrations/watershed.py
  M wepppy/wepp/interchange/hec_ras_buffer.py
  M wepppy/weppcloud/routes/diff/diff.py
  M wepppy/weppcloud/routes/nodb_api/watar_bp.py
  M wepppy/weppcloud/routes/run_0/run_0_bp.py
  M wepppy/weppcloud/routes/test_bp.py
  M wepppy/weppcloud/utils/helpers.py

Per-file delta (unsuppressed broad catches):
  M wepppy/climates/climatena_ca/__init__.py (base=0 current=0 delta=+0)
  M wepppy/export/ermit_input.py (base=0 current=0 delta=+0)
  M wepppy/export/gpkg_export.py (base=0 current=0 delta=+0)
  M wepppy/export/prep_details.py (base=0 current=0 delta=+0)
  M wepppy/microservices/_gdalinfo.py (base=0 current=0 delta=+0)
  M wepppy/microservices/browse/_download.py (base=0 current=0 delta=+0)
  M wepppy/microservices/browse/browse.py (base=5 current=0 delta=-5)
  M wepppy/microservices/browse/dtale.py (base=0 current=0 delta=+0)
  M wepppy/microservices/browse/files_api.py (base=0 current=0 delta=+0)
  M wepppy/microservices/browse/listing.py (base=0 current=0 delta=+0)
  M wepppy/microservices/rq_engine/ash_routes.py (base=0 current=0 delta=+0)
  M wepppy/microservices/rq_engine/climate_routes.py (base=0 current=0 delta=+0)
  M wepppy/microservices/rq_engine/debris_flow_routes.py (base=0 current=0 delta=+0)
  M wepppy/microservices/rq_engine/export_routes.py (base=0 current=0 delta=+0)
  M wepppy/microservices/rq_engine/landuse_routes.py (base=0 current=0 delta=+0)
  M wepppy/microservices/rq_engine/omni_routes.py (base=12 current=0 delta=-12)
  M wepppy/microservices/rq_engine/project_routes.py (base=4 current=0 delta=-4)
  M wepppy/microservices/rq_engine/soils_routes.py (base=0 current=0 delta=+0)
  M wepppy/microservices/rq_engine/treatments_routes.py (base=0 current=0 delta=+0)
  M wepppy/microservices/rq_engine/upload_climate_routes.py (base=0 current=0 delta=+0)
  M wepppy/microservices/rq_engine/upload_huc_fire_routes.py (base=3 current=0 delta=-3)
  M wepppy/microservices/rq_engine/watershed_routes.py (base=0 current=0 delta=+0)
  M wepppy/nodb/batch_runner.py (base=0 current=0 delta=+0)
  M wepppy/nodb/core/landuse.py (base=0 current=0 delta=+0)
  M wepppy/nodb/core/ron.py (base=0 current=0 delta=+0)
  M wepppy/nodb/core/soils.py (base=1 current=1 delta=+0)
  M wepppy/nodb/core/watershed.py (base=0 current=0 delta=+0)
  M wepppy/nodb/core/watershed_mixins.py (base=0 current=0 delta=+0)
  M wepppy/nodb/core/wepp.py (base=0 current=0 delta=+0)
  M wepppy/nodb/duckdb_agents.py (base=0 current=0 delta=+0)
  M wepppy/nodb/mods/ash_transport/ash.py (base=0 current=0 delta=+0)
  M wepppy/nodb/mods/disturbed/disturbed.py (base=1 current=1 delta=+0)
  M wepppy/nodb/mods/omni/omni.py (base=0 current=0 delta=+0)
  M wepppy/nodb/mods/omni/omni_clone_contrast_service.py (base=0 current=0 delta=+0)
  M wepppy/nodb/mods/omni/omni_mode_build_services.py (base=0 current=0 delta=+0)
  M wepppy/nodb/mods/omni/omni_station_catalog_service.py (base=0 current=0 delta=+0)
  M wepppy/nodb/mods/path_ce/data_loader.py (base=0 current=0 delta=+0)
  M wepppy/nodb/mods/swat/swat.py (base=0 current=0 delta=+0)
  M wepppy/nodb/mods/swat/swat_connectivity_mixin.py (base=0 current=0 delta=+0)
  M wepppy/nodb/mods/swat/swat_recall_mixin.py (base=0 current=0 delta=+0)
  M wepppy/nodb/mods/swat/swat_txtinout_mixin.py (base=0 current=0 delta=+0)
  M wepppy/query_engine/activate.py (base=0 current=0 delta=+0)
  M wepppy/rq/culvert_rq.py (base=13 current=13 delta=+0)
  M wepppy/rq/culvert_rq_manifest.py (base=0 current=0 delta=+0)
  M wepppy/rq/land_and_soil_rq.py (base=1 current=1 delta=+0)
  M wepppy/rq/omni_rq.py (base=8 current=8 delta=+0)
  M wepppy/rq/path_ce_rq.py (base=0 current=0 delta=+0)
  M wepppy/rq/project_rq.py (base=27 current=27 delta=+0)
  M wepppy/rq/project_rq_archive.py (base=0 current=0 delta=+0)
  M wepppy/rq/project_rq_fork.py (base=1 current=1 delta=+0)
  M wepppy/rq/wepp_rq.py (base=0 current=0 delta=+0)
  M wepppy/rq/wepp_rq_stage_helpers.py (base=0 current=0 delta=+0)
  M wepppy/tools/migrations/landuse.py (base=0 current=0 delta=+0)
  M wepppy/tools/migrations/nodir_bulk.py (base=0 current=0 delta=+0)
  M wepppy/tools/migrations/soils.py (base=0 current=0 delta=+0)
  M wepppy/tools/migrations/watershed.py (base=0 current=0 delta=+0)
  M wepppy/wepp/interchange/hec_ras_buffer.py (base=0 current=0 delta=+0)
  M wepppy/weppcloud/routes/diff/diff.py (base=0 current=0 delta=+0)
  M wepppy/weppcloud/routes/nodb_api/watar_bp.py (base=0 current=0 delta=+0)
  M wepppy/weppcloud/routes/run_0/run_0_bp.py (base=10 current=10 delta=+0)
  M wepppy/weppcloud/routes/test_bp.py (base=0 current=0 delta=+0)
  M wepppy/weppcloud/utils/helpers.py (base=3 current=0 delta=-3)

Net delta (all changed files): -27
Result: PASS
Wrote JSON report to code-quality-report.json
Wrote Markdown summary to code-quality-summary.md
Observe-only mode: no threshold-based failure.
INFO:wctl2:docker compose exec weppcloud bash -lc cd /workdir/wepppy && /opt/venv/bin/python tools/check_rq_dependency_graph.py
RQ dependency graph artifacts are up to date
✅ 24 files validated, 0 errors, 0 warnings
✅ 52 files validated, 0 errors, 0 warnings
✅ 8 files validated, 0 errors, 0 warnings
✅ 1 files validated, 0 errors, 0 warnings
✅ 27 files validated, 0 errors, 0 warnings
✅ 1 files validated, 0 errors, 0 warnings

## Regression Fix Rerun Notes

- Root cause fix: widened grouped integration fixture runid alias acceptance in `tests/integration/conftest.py` for parent-run ACL lookup compatibility.
- `wctl run-pytest tests/integration/test_cross_service_auth_lifecycle.py::test_lifecycle__mx_l4_grouped_cookie_round_trip_from_issue_to_browse` -> `1 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_auth.py` -> `29 passed`.
✅ 27 files validated, 0 errors, 0 warnings
✅ 1 files validated, 0 errors, 0 warnings
