# AGENTS.Culvert_web_app.md
> AI Coding Agent Guide for Culvert_web_app (https://github.com/SouravDSGit/Culvert_web_app)
> Authorship: Maintained by GitHub Copilot / Codex (per AGENTS policy).

## Quick Map
- `culvert_app/app.py`: Flask app, routing, auth/session, upload endpoints, SocketIO progress, Redis/RQ setup.
- `culvert_app/tasks/*.py`: background jobs (watershed delineation, hydrologic vuln, hydrogeo vuln, stream generation, reports, downloads).
- `culvert_app/utils/*.py`: geospatial subroutines, R integration, WEPP processing, data fetch, file prep.
- `culvert_app/static/visualization/*.py`: Folium map building and layer overlays.
- `culvert_app/static/js/*.js`: UI orchestration, form validation, SocketIO listeners, upload workflows.
- `culvert_app/templates/*.html`: Jinja pages for dashboards, analysis, maps.
- `culvert_app/models/*.py`: SQLAlchemy models.
- `culvert_app/redis_helpers.py`: Redis pools and task state/cancel helpers.

## Data Layout
- Instance root: `app.instance_path`.
- User data root: `user_data/`.
  - Inputs: `user_data/<user_id>_inputs/<project>/`
  - Outputs: `user_data/<user_id>_outputs/<project>/`
  - Logs: `user_data/<user_id>_logs/<project>/execution_logs.json`
  - Temp: `user_data/<user_id>_temp/<project>/`
- Core datasets: `core_data/` under instance path.
  - Examples: US boundary zip, PRISM, NLCD, GSSURGO, Atlas14, NDVI, WEPP binaries.

## Runtime/Queue
- Redis usage (see `culvert_app/redis_helpers.py`):
  - DB 0: RQ jobs.
  - DB 1: Flask sessions.
  - DB 2: SocketIO pub/sub.
  - DB 3: cancellation flags.
  - DB 4: task state (progress, status).
  - DB 5: map storage (unused).
- Progress:
  - `emit_progress_update` + `emit_progress_update_background` -> SocketIO room `user_<id>_project_<project>`.
  - `active_tasks` is in-process; Redis task state is the cross-process source of truth.
- Cancellation:
  - `/cancel_task/...` writes Redis flag, `check_cancellation` raises `TaskCancelledError`.

## Geospatial Pipelines
- Watershed delineation (ws_deln):
  - Inputs: boundary polygon (upload/draw), DEM (upload or USGS 3DEP VRT), roads (upload or OSM), pour points (culvert/gauge or derived).
  - Flow: reproject to UTM, hydro-enforcement (optional road fill + breakline burn), D8 flow/accum, stream extraction, road-stream intersections, snap pour points, delineate and filter watersheds, flag outside-boundary polygons.
  - Outputs: shapefiles + `final_watershed_html_map.html`.
  - Key code: `culvert_app/tasks/watershed_delineation_task.py`, `culvert_app/utils/subroutine_nested_watershed_delineation.py`, `culvert_app/static/visualization/subroutine_basemap_generator.py`.
- Hydrologic vulnerability:
  - Uses ws_deln outputs + user streamflow/precip inputs, regional frequency analysis, rational method, GPDM peak discharge, culvert capacity checks.
  - Outputs: vulnerability maps and tables.
  - Key code: `culvert_app/tasks/hydro_vuln_analysis_task.py`, `culvert_app/utils/subroutine_determine_WS_characteristics.py`, `culvert_app/utils/subroutine_regional_freq_analysis.py`, `culvert_app/utils/subroutine_rational_method.py`, `culvert_app/utils/subroutine_graphical_peak_discharge_Est.py`, `culvert_app/utils/subroutine_culvert_discharge_capacity.py`.
- Hydrogeo vulnerability:
  - Streams + erosion risk via SBEVA, RUSLE, WDFM; WEPP optional.
  - Uses PRISM, NLCD, GSSURGO, Atlas14, geology, NDVI from `core_data`.
  - Key code: `culvert_app/tasks/hydrogeo_vuln_analysis_task.py`, `culvert_app/tasks/stream_generation_task.py`, `culvert_app/utils/subroutine_sbeva_analysis.py`, `culvert_app/utils/subroutine_rusle_analysis.py`, `culvert_app/utils/subroutine_wdfm_analysis.py`, `culvert_app/utils/subroutine_run_WEPP_model.py`.
- WEPP:
  - Builds hillslope/stream inputs, climate/soil/management files, runs WEPP binary, merges results into watershed outputs.
  - NOTE: WEPP is not functional in this app; treat WEPP paths/outputs as disabled placeholders.
  - Details: `WEPP_steps.md` (contains some naive assumptions).

## Culvert/Watershed ID bookkeeping
Understanding the ID chain is critical for wepp.cloud integration:

### ID flow through the pipeline
1. **Pour point upload** → User uploads points with arbitrary attributes; code uses `Point_ID` as the canonical ID column (hardcoded in `watershed_delineation_task.py` via `pour_ID='Point_ID'`).
2. **FID assignment** → GeoPandas assigns a 0-indexed `FID` to each row when reading the shapefile.
3. **WhiteboxTools watershed** → `wbt.watershed()` creates a raster where each cell's value equals the `FID` of the associated pour point.
4. **Raster to vector** → `wbt.raster_to_vector_polygons()` creates polygons with a `VALUE` attribute matching the raster cell value (i.e., the pour point `FID`).
5. **ID merge** → Code joins `VALUE` back to `FID` and transfers `Point_ID`:
   ```python
   # From subroutine_nested_watershed_delineation.py:
   watershed_poly_gdf['VALUE'] = watershed_poly_gdf['VALUE'].astype(int)
   watershed_poly_gdf_merged = pd.merge(
       watershed_poly_gdf, 
       point_gdf[['FID', ID_column]],  # ID_column = 'Point_ID'
       left_on='VALUE', 
       right_on='FID', 
       how='left'
   )
   ```

### Key files with IDs
| File | ID columns | Notes |
|------|------------|-------|
| `pour_point_filtered_UTM.shp` | `FID`, `Point_ID` | Final pour points after filtering |
| `ws_raster_UTM.tif` | Cell values = `FID` | Temporary watershed raster |
| `ws_polygon_filtered_by_area_UTM.shp` | `VALUE`, `FID`, `Point_ID` | Vectorized watersheds with merged IDs |

### wepp.cloud payload requirements
When building the payload ZIP for wepp.cloud:
1. **culvert_points.geojson** must include `Point_ID` on each feature
2. **watersheds.geojson** must include `Point_ID` on each polygon feature, matching the corresponding culvert point

The `Point_ID` attribute in the watershed GeoJSON directly links each watershed polygon to its culvert—no separate ID mapping file is needed.

### Relevant source locations
- `culvert_app/tasks/watershed_delineation_task.py` → sets `pour_ID='Point_ID'`
- `culvert_app/utils/subroutine_nested_watershed_delineation.py`:
  - Lines 1189-1210: `delineate_watershed_and_convert_to_polygon()` with VALUE/FID merge
  - Lines 838-888: Nested delineation loop adding `ID_column` and `watershed_id` to each polygon
- `culvert_app/tasks/hydro_vuln_analysis_task.py` → uses `pour_ID="Point_ID"` throughout

## Watershed delineation file map (ws_deln)
- Inputs (uploads or fetch):
  - `boundary_path` -> `boundary.zip` (AOI polygon zip; upload/draw routes in `culvert_app/app.py`).
  - `dem_path` -> `dem.tif` (DEM raster; upload or USGS fetch in `culvert_app/app.py` + `culvert_app/utils/fetch_USGS_dem.py`).
  - `pour_point_path` -> `pour_point.zip` (culvert/gauge pour points; optional).
  - `user_uploaded_road_path` -> `road_data.zip` (road shapefile; optional).
- Outputs (WS_deln folder in `culvert_app/tasks/watershed_delineation_task.py`):
  - `boundary_UTM_path` -> `Boundary_UTM.shp` (boundary reprojected to UTM).
  - `pour_UTM_path_reporj` -> `Pour_Point_UTM.shp` (pour points reprojected to UTM).
  - `pour_UTM_path_clipped` -> `Pour_Point_UTM_clipped.shp` (pour points clipped to boundary).
  - `dem_UTM_path` -> `DEM_UTM.tif` (DEM reprojected + clipped).
  - `road_UTM_path` -> `road_UTM.shp` (roads in UTM).
  - `pour_points_snapped_to_roads_UTM_path` -> `pour_points_snapped_to_roads_UTM.shp`.
  - `breaklines_UTM_path` -> `breaklines_UTM.shp`.
  - `Road_elevated_DEM_UTM_path` -> `road_elevated_DEM_UTM.tif`.
  - `breaklines_burned_DEM_UTM_path` -> `breaklines_burned_DEM_UTM.tif`.
  - `breached_filled_DEM_UTM_path` -> `breached_filled_DEM_UTM.tif`.
  - `D8flow_dir_UTM_path` -> `D8flow_dir_UTM.tif`.
  - `D8Flow_accum_UTM_path` -> `bD8Flow_accum_UTM.tif`.
  - `stream_vector_UTM_path` -> `stream_vector_UTM.shp`.
  - `road_stream_intersect_vector_UTM_path` -> `road_stream_intersect_vector_UTM.shp`.
  - `pour_points_snapped_to_RSCS_UTM_path` -> `pour_points_snapped_to_RSCS_UTM.shp`.
  - `all_ws_polygon_UTM_path` -> `all_ws_polygon_UTM.shp`.
  - `ws_polygon_filtered_by_area_UTM_path` -> `ws_polygon_filtered_by_area_UTM.shp`.
  - `pour_point_filtered_UTM_path` -> `pour_point_filtered_UTM.shp`.
  - `final_flagged_ws_polygon_filtered_by_area_UTM_path` -> `final_flagged_ws_polygon_filtered_by_area_UTM.shp`.
  - `final_ws_polygon_flag_ID_path` -> `ws_polygon_flag_ID.csv`.
  - `final_flag_removed_ws_polygon_filtered_by_area_UTM_path` -> `final_flag_removed_ws_polygon_filtered_by_area_UTM.shp`.
  - `final_flag_removed_pour_point_filtered_by_area_UTM_path` -> `final_flag_removed_pour_point_UTM.shp`.
  - `final_watershed_html_map_path` -> `final_watershed_html_map.html`.
- Temp intermediates:
  - `dem_temp_path` -> `dem_reprojected1.tif`.
  - `stream_raster_temp_path` -> `stream_raster_UTM.tif`.
  - `ws_raster_temporary_path` -> `ws_raster_UTM.tif`.
  - `ws_polygon_temp_path` -> `ws_polygon_UTM.shp`.
  - `user_dir_error_log_ws_deln_path` -> `error_log.json`.
  - `task_complete_flag_path` -> `ws_deln_completed.json`.
- Form persistence:
  - `ws_deln_form_responses_path` -> `user_ws_deln_responses.txt` (saved in WS_deln output dir).
  - `filepath` -> `watershed_delineation_form_data.txt` (in `save_ws_deln_form_data_to_file`).

## Hydro-enforcement pipeline (ws_deln)
- Trigger: `hydro_enforcement_select` from form key `hydroEnforcementSelect`.
- Breaklines: `create_breaklines(...)` writes `user_output_breaklines_file_path` (`breaklines_UTM.shp`) using `user_output_road_file_path` + `user_output_pour_points_snapped_to_roads_file_path`.
- Road fill: `adjust_dem_along_polyline(..., burn=False)` writes `user_output_Road_elevated_DEM_file_path` (`road_elevated_DEM_UTM.tif`) with `road_fill_dem_by_m` and `road_fill_Dem_buffer_m`.
- Breakline burn: `adjust_dem_along_polyline(..., burn=True)` writes `user_output_breaklines_burned_DEM_file_path` (`breaklines_burned_DEM_UTM.tif`) with `breakline_burn_Dem_by_m` and `breakline_burn_dem_buffer_m`.
- Conditioning: `wbt.breach_depressions(...)` runs on `user_output_breaklines_burned_DEM_file_path` (hydro-enf) or `user_output_dem_raster_file_path` (no hydro-enf), outputting `user_output_breached_filled_DEM_file_path`.
- Downstream flow products (same for both branches): `wbt.d8_pointer` -> `user_output_D8flow_dir_file_path`, `wbt.d8_flow_accumulation` -> `user_output_D8Flow_accum_file_path`, `wbt.extract_streams` -> `stream_raster_temporary_file_path`, `wbt.raster_to_vector_lines` -> `user_output_stream_vector_file_path`.

## Hydrologic vulnerability file map (hydro_vuln)
- Inputs:
  - `user_dir_inputs` -> `.../<user_id>_outputs/<project>/WS_deln` (uses ws_deln outputs).
  - `user_dir_uploads` -> `.../<user_id>_inputs/<project>` (user time series uploads).
  - `parsed_data` -> `user_hydro_vuln_responses.txt` in `user_dir_outputs`.
  - `ws_deln_param` -> `user_ws_deln_responses.txt` in `user_dir_inputs` (flagged watershed selection).
  - `boundary_polygon_UTM_path` -> `Boundary_UTM.shp`.
  - `dem_UTM_reprojected_path` -> `DEM_UTM.tif`.
  - `flow_accumulation_path` -> `bD8Flow_accum_UTM.tif`.
  - `pour_points_path` -> `pour_point_filtered_UTM.shp` or `final_flag_removed_pour_point_UTM.shp` (based on `flag_keep_option`).
  - `input_watersheds_path` -> `ws_polygon_filtered_by_area_UTM.shp` or `final_flag_removed_ws_polygon_filtered_by_area_UTM.shp`.
  - `flow_ts_dir_path` -> `.../Inst_Streamflow` and `pi_ts_dir_path` -> `.../PI` (time series CSV uploads).
- Core data:
  - `runoff_table_path` -> `Coeff_Runoff_table.csv`.
  - `prism_30yr_ppt_normals_path` -> `PRISM_CONUS_30yr_precip_Avg_UTM.tif`.
  - `cn_table_csv_path` -> `CNtable.csv`.
  - `rainfall_type_path` -> `GPDM/rainfall_types_USA.csv`.
  - `usa_states_shapefile_path` -> `US States and Territories Shapefile_20250216.zip`.
  - `gssurgo_base_raster_path` -> `Soil_GSSURGO`.
  - `NLCD_2024_CONUS_raster_path` -> `Annual_NLCD_LndCov_2024_CU_C1V1/Annual_NLCD_LndCov_2024_CU_C1V1.tif`.
  - `base_wetland_polygon_path` -> `Wetland_data`.
- Outputs:
  - `wschar_output_folder` -> `WSchar_and_ROI/`.
  - `save_reprojected_CN_raster_path` -> `CN_data_UTM_reprojected.tif`.
  - `save_ws_char_path` -> `ws_char_polygon_UTM.shp`.
  - `clipped_nlcd_raster_path` -> `nlcd_2024.tif`.
  - `aoi_gSSURGO_hydgrpdcd_data_path` -> `aoi_gSSURGO_hydgrpdcd.shp`.
  - `roi_file_path` -> `roi_index.csv`.
  - `RM_results_folder` -> `RM_results/` with `RM_output_ws_path` -> `RM_Qp_results.shp` and `RM_save_vuln_results_path` -> `RM_vuln_results.shp`.
  - `RF_results_folder` -> `RFA_results/` with `RF_save_vuln_results_path` -> `RF_vuln_results.shp`.
  - `GPDM_results_folder` -> `GPDM_results/` with `GPDM_save_vuln_results_path` -> `GPDM_vuln_results.shp`.
  - `save_pi_freq_output_dir_path` -> `PI_Freq_analysis_output/`.
  - `save_Q_freq_output_dir_path` -> `Q_Freq_analysis_output/`.
  - `save_hydro_vuln_map_path` -> `Vuln_Result_Final_Map.html`.
- Optional overlay inputs (hydrogeo results):
  - `sbeva_output_watershed_path` -> `hydrogeo_vuln/sbeva/sbeva_final_output_watershed_polygon.shp`.
  - `rusle_output_watershed_path` -> `hydrogeo_vuln/rusle/rusle_watersheds_with_erosion.shp`.
  - `wdfm_output_watershed_path` -> `hydrogeo_vuln/wdfm/wdfm_final_output_watershed_polygon.shp`.
  - `ehvi_results_path` -> `hydrogeo_vuln/ehvi/ehvi_final_output_watershed_polygon.shp`.

## Hydrogeo vulnerability file map (hydrogeo_vuln)
- Inputs:
  - `user_dir_inputs` -> `.../<user_id>_outputs/<project>/WS_deln`.
  - `response_file_path` -> `user_ws_deln_responses.txt` (flag selection).
  - `ws_shapefile_path` -> `ws_polygon_filtered_by_area_UTM.shp` or `final_flag_removed_ws_polygon_filtered_by_area_UTM.shp`.
  - `pour_points_path` -> `pour_point_filtered_UTM.shp` or `final_flag_removed_pour_point_UTM.shp`.
  - `stream_polyline_path` -> `hydrogeo_stream_vector_UTM.shp` (from `culvert_app/tasks/stream_generation_task.py`).
  - `dem_UTM_path` -> `DEM_UTM.tif`.
  - `flow_acc_path` -> `bD8Flow_accum_UTM.tif`.
  - `road_polyline_path` -> `road_UTM.shp` (for WDFM).
  - Hydro vuln overlays: `RF_save_vuln_results_path`, `RM_save_vuln_results_path`, `GPDM_save_vuln_results_path`.
- Outputs (top-level):
  - `sbeva_results_path` -> `hydrogeo_vuln/sbeva/` with `sbeva_output_watershed_path` -> `sbeva_final_output_watershed_polygon.shp`.
  - `rusle_results_path` -> `hydrogeo_vuln/rusle/` with `rusle_output_watershed_path` -> `rusle_watersheds_with_erosion.shp`.
  - `wdfm_results_path` -> `hydrogeo_vuln/wdfm/` with `wdfm_output_watershed_path` -> `wdfm_final_output_watershed_polygon.shp`.
  - `wepp_results_path` -> `hydrogeo_vuln/wepp/` with `wepp_output_watershed_path` -> `wepp_watersheds_with_erosion.shp` (disabled; WEPP not functional).
  - `ehvi_folder_path` -> `hydrogeo_vuln/ehvi/` with `ehvi_results_path` -> `ehvi_final_output_watershed_polygon.shp`.
  - `vuln_map_path` -> `Vuln_Result_Final_Map.html`.
- SBEVA intermediates (in `sbeva_results_path`):
  - `AOI_PIDF_24hr_100yr_output_raster_path` -> `AOI_PIDF_24hr_100yr_UTM.tif`.
  - `AOI_PIDF_24hr_100yr_output_categorized_raster_path` -> `AOI_PIDF_24hr_100yr_UTM_categorized.tif`.
  - `PRISM_AOI_30yr_precip_Normal_resampled_UTM_path` -> `PRISM_AOI_30yr_precip_Normal_resampled_UTM.tif`.
  - `PRISM_AOI_categorized_30yr_precip_Normal_resampled_UTM_path` -> `SBEVA_Categorized_PRISM_AOI_30yr_precip_Normal_resampled_UTM.tif`.
  - `PRISM_AOI_30yr_tmean_Normal_resampled_UTM_path` -> `PRISM_AOI_30yr_tmean_Normal_resampled_UTM.tif`.
  - `PRISM_AOI_30yr_categorized_tmean_Normal_resampled_UTM_path` -> `SBEVA_Categorized_PRISM_AOI_30yr_tmean_Normal_resampled_UTM.tif`.
  - `PRISM_AOI_30yr_solclear_Normal_resampled_UTM_path` -> `PRISM_AOI_30yr_solclear_Normal_resampled_UTM.tif`.
  - `PRISM_AOI_30yr_categorized_solclear_Normal_resampled_UTM_path` -> `SBEVA_Categorized_PRISM_AOI_30yr_solclear_Normal_resampled_UTM.tif`.
  - `GSSURGO_soil_data_output_dir` -> `Gssurgo_soil_data/`.
  - `output_slope_percentage_AOI_raster_path` -> `slope_percentage_AOI_raster_UTM.tif`.
  - `categorized_output_slope_percentage_AOI_raster_path` -> `categorized_output_slope_percentage_AOI_raster_UTM.tif`.
  - `output_aoi_nlcd_raster_path` -> `aoi_nlcd_raster_UTM.tif`.
  - `output_aoi_categorized_nlcd_raster_path` -> `aoi_categorized_nlcd_raster_UTM.tif`.
  - `sbeva_output_weighted_raster_path` -> `sbeva_output_weighted_raster_UTM.tif`.
  - `output_stream_buffer_path` -> `stream_buffer.shp`.
- RUSLE intermediates (in `rusle_results_path`):
  - `output_100yr_30min_raster_path` -> `NOAA_Atlas14_100yr_30min_UTM.tif`.
  - `Rfactor_output_raster_path` -> `Rfactor_UTM.tif`.
  - `kffactor_raster_output_path` -> `Kffactor_UTM.tif`.
  - `ls_factor_raster_output_path` -> `LSfactor_UTM.tif`.
  - `aoi_NDVI_raster_output_path` -> `NDVI_AOI_UTM.tif`.
  - `cfactor_raster_output_path` -> `Cfactor_AOI_UTM.tif`.
  - `rusle_erosion_rate_raster_output_path` -> `rusle_Erosion_rates_t_h_y.tif`.
- WDFM intermediates (in `wdfm_results_path`):
  - `AOI_PIDF_24hr_100yr_output_raster_path` -> `AOI_PIDF_24hr_100yr_UTM.tif`.
  - `AOI_PIDF_24hr_100yr_output_categorized_raster_path` -> `AOI_PIDF_24hr_100yr_UTM_categorized.tif`.
  - `GSSURGO_soil_data_output_dir` -> `Gssurgo_soil_data/`.
  - `output_slope_percentage_AOI_raster_path` -> `slope_percentage_AOI_raster_UTM.tif`.
  - `categorized_output_slope_percentage_AOI_raster_path` -> `categorized_output_slope_percentage_AOI_raster_UTM.tif`.
  - `categorized_geology_path` -> `categorized_geology_UTM.tif`.
  - `categorized_ndvi_path` -> `categorized_ndvi_UTM.tif`.
  - `categorized_stream_buffer_path` -> `categorized_stream_buffer_UTM.tif`.
  - `categorized_road_buffer_path` -> `categorized_road_buffer_UTM.tif`.
  - `wdfm_output_weighted_raster_path` -> `wdfm_output_weighted_raster_UTM.tif`.

## Report generation file map (Reports)
- Entrypoint:
  - `report_generate` route in `culvert_app/app.py` queues `run_report_generation_task` with `user_outputs_dir = DATA_FOLDER/<user_id>_outputs/<project>`.
- Inputs (response files):
  - `ws_deln_response_file_path` -> `WS_deln/user_ws_deln_responses.txt`.
  - `hydro_vuln_response_file_path` -> `hydro_vuln/user_hydro_vuln_responses.txt`.
  - `hydro_geo_response_file_path` -> `hydrogeo_vuln/user_hydrogeo_vuln_responses.txt`.
- Plot generation outputs (`culvert_app/static/visualization/subroutine_plot_generator_for_report.py`):
  - Output directory: `Reports/Generated_Images/` (under `.../<user_id>_outputs/<project>/Reports/Generated_Images`).
  - `study-area` -> `{user_id}_study_area_map.png`.
  - `watershed-analysis` -> `{user_id}_watershed_analysis.png`.
  - `hydro-risk` -> `{user_id}_hydrologic_risk.png`.
  - `hydrogeo-risk` -> `{user_id}_hydrogeo_risk.png`.
- Report document output (`culvert_app/utils/subroutine_generate_CULVERT_Report.py`):
  - `report_filename` -> `CULVERT_{project_name}_report.docx`.
  - `report_path` -> `Reports/CULVERT_{project_name}_report.docx`.
  - Supporting data dependencies used by plot generator:
  - WS_deln outputs: `Boundary_UTM.shp`, `DEM_UTM.tif`, `road_UTM.shp`, `pour_point_filtered_UTM.shp` or `final_flag_removed_pour_point_UTM.shp`.
  - Hydro/hydrogeo outputs for maps: `Vuln_Result_Final_Map.html` and method-specific shapefiles under `hydro_vuln/` and `hydrogeo_vuln/`.

## Download packaging file map (downloads)
- Entrypoints:
  - `prepare_download` in `culvert_app/app.py` queues `run_download_task` (task_type `download_files`).
  - `get_download` in `culvert_app/app.py` serves the prepared file from Redis metadata.
  - `cleanup_downloads` in `culvert_app/app.py` removes old files (>1 hour) in download cache.
- Inputs:
  - `selected_files` (from POST `/prepare-download` JSON) -> relative paths under `base_path`.
  - `base_path` -> `DATA_FOLDER/<user_id>_outputs/<project_name>`.
- Outputs:
  - `download_dir` -> `DATA_FOLDER/downloads/<user_id>_<project_name>/`.
  - Single file:
    - `download_filename` -> `download_{user_id}_{project_name}_{source_file['filename'].replace('/', '_')}`.
    - `download_path` -> `download_dir/download_filename` (copied via `shutil.copy2`).
  - Multi-file:
    - `download_filename` -> `download_{user_id}_{project_name}_files.zip`.
    - `download_path` -> `download_dir/download_filename` (ZIP via `zipfile.ZipFile`).
- Redis metadata (download handoff):
  - `download_key` -> `download_{user_id}_{project_name}_{task_type}`.
  - `download_info` -> dict with `filename`, `path`, `file_count`, `total_size`, `created_at`.
  - Stored in `redis_map_storage_client` with `setex(download_key, 3600, str(download_info))`.

## Stream generation file map (generate_streams)
- Entrypoints:
  - `generate_streams` route in `culvert_app/app.py` queues `run_stream_generation_task` with `flow_accum_thresh`.
  - `check_streams_exist` route in `culvert_app/app.py` verifies stream shapefile components.
- Inputs:
  - `user_dir_inputs` -> `.../<user_id>_outputs/<project>/WS_deln`.
  - `input_watersheds_path` -> `ws_polygon_filtered_by_area_UTM.shp` or `final_flag_removed_ws_polygon_filtered_by_area_UTM.shp` (based on `FlagKeepOptionSelect` in `user_ws_deln_responses.txt`).
  - `input_point_path` -> `pour_point_filtered_UTM.shp` or `final_flag_removed_pour_point_UTM.shp`.
  - Required rasters: `bD8Flow_accum_UTM.tif`, `D8flow_dir_UTM.tif` (from ws_deln outputs).
  - `rp_file_path` -> `hydro_vuln/user_hydro_vuln_responses.txt` (for return period list).
- Outputs (hydrogeo_vuln):
  - `stream_vector_output_path` -> `hydrogeo_stream_vector_UTM.shp`.
  - `stream_raster_output_path` -> `main_stream_raster_UTM.tif`.
  - `vuln_map_path` -> `Vuln_Result_Final_Map.html` (map after stream overlay).
- Hillslope/WEPP placeholders (hydrogeo_vuln/wepp):
  - `hillslope_polygon_path` -> `wepp/hillslopes_UTM.shp`.
  - `hillslope_streams_path` -> `wepp/wepp_stream_vector_UTM.shp`.
  - `wepp_output_watershed_path` -> `wepp/wepp_watersheds_with_erosion.shp` (WEPP not functional).
- Map overlays (used by `add_layers_to_basemaps`):
  - Hydrologic: `RF_vuln_results.shp`, `RM_vuln_results.shp`, `GPDM_vuln_results.shp`.
  - Hydrogeo: `sbeva_final_output_watershed_polygon.shp`, `rusle_watersheds_with_erosion.shp`, `wdfm_final_output_watershed_polygon.shp`, `ehvi_final_output_watershed_polygon.shp`.
  - Stream layer: `hydrogeo_stream_vector_UTM.shp`.

## User Interaction/Flows
- Home -> login/registration -> project dashboard (create/select project).
- ws_deln page: upload/draw boundary, DEM, road data, pour points; run watershed delineation; map and progress via SocketIO.
- hydrologic_vuln page: streamflow/precip uploads + analysis; results map.
- hydrogeo_vuln page: choose methods (SBEVA/RUSLE/WDFM/WEPP), run analysis; results map + downloads.
- analysis_dashboard/explore_files: view outputs, download artifacts.
- support email: sends request and attaches project execution logs.

## Local Dev Notes
- Docker compose: `docker-compose.yml` or `docker-compose.nocaddy.yml`.
- R packages: `R_packages_installation_docker.py` / `culvert_app/R_packages_installation_local.py`.
- Python deps: `requirements.txt` and `culvert_app/requirements.txt`.

## Tests
- No formal test suite or runner configuration detected (no `tests/` directory; no `pytest`/`unittest` usage).
- `test_dash_startup.py` is a standalone debug script for Dash/Plotly startup checks.
- `culvert_app/gevent_test_app.py` is a manual app stub, not an automated test.
- Notebook and junk artifacts under `culvert_app/utils/notebooks/` and `culvert_app/utils/junk/` are exploratory, not CI tests.
