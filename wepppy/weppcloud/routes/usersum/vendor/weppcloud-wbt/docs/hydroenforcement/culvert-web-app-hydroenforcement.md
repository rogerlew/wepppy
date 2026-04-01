# Culvert_web_app Hydro-enforcement Routine

## Purpose
This document describes the current hydro-enforcement implementation in `Culvert_web_app`, with emphasis on:

- input files and form parameters,
- preprocessing before hydro-enforcement,
- hydro-enforcement processing steps and parameter values,
- produced output files.

The goal is to provide a concrete implementation reference for evaluating whether (and how) this workflow should be implemented in `weppcloud-wbt`.

## Primary Code Paths
The watershed delineation + hydro-enforcement flow is orchestrated through:

- `culvert_app/app.py` (`/ws_deln/ws_deln_results/<user_id>/<project_name>` POST route)
- `culvert_app/tasks/watershed_delineation_task.py` (`run_watershed_delineation_task`)
- `culvert_app/utils/subroutine_nested_watershed_delineation.py`

Main execution functions in `subroutine_nested_watershed_delineation.py`:

- `watershed_delineation_point_both(...)` for `pourPointDataSelect in ['both', 'culvert']`
- `watershed_delineation_point_NA(...)` for `pourPointDataSelect == 'pour_pt_NA'`
- `watershed_delineation_point_only_gauging_st(...)` for `pourPointDataSelect == 'gauging'`

## Runtime Directories and File Layout
Per project, the route/task uses:

- Inputs: `DATA_FOLDER/{user_id}_inputs/{project_name}/`
- Outputs: `DATA_FOLDER/{user_id}_outputs/{project_name}/WS_deln/`
- Temp: `DATA_FOLDER/{user_id}_temp/{project_name}/`

`DATA_FOLDER` is `app.instance_path/user_data`.

## Input Files

### User-supplied geospatial files
These are expected in `.../{user_id}_inputs/{project_name}/`:

| Logical input | Stored filename | Required when |
| --- | --- | --- |
| Boundary polygon | `boundary.zip` | Always |
| DEM raster | `dem.tif` | Always |
| Pour points | `pour_point.zip` | `both`, `culvert`, `gauging` modes |
| Road network (optional upload) | `road_data.zip` | Optional; if absent, roads are downloaded from OSM |

### Form parameters used by this routine
UI fields from `templates/ws_deln.html` are parsed in `app.py` and mapped into `hydro_params`.

| UI field | Parsed key | Default |
| --- | --- | --- |
| `hydroEnforcementSelect` | `hydro_enforcement_selection` | required user choice |
| `flowAccumThreshold` / `flowAccumThreshold_nohydro` | `flow_accumulation_threshold` | `100` |
| `pourPointSnapDistanceM` / `pourPointSnapDistanceM_nohydro` | `pour_point_snap_distance` | `20` m |
| `filterWatershedMinAreaHa` / `filterWatershedMinAreaHa_nohydro` | `minimum_watershed_area` | `2` ha |
| `flagWatershedAreaOutsideBoundaryHa` / `_nohydro` | `flag_ws_threshold` | `0.5` ha |
| `roadFillDemByM` | `road_fill_DEM_adjustment` | `5` m |
| `roadFillDemBufferM` | `road_fill_DEM_buffer` | `2` m |
| `breaklineOffsetM` | `breakline_offset_length` | `10` m |
| `breaklineBurnDemByM` | `breakline_burn_DEM_adjustment` | `10` m |
| `breaklineBurnDemBufferM` | `breakline_burn_DEM_buffer` | `1` m |

## Preprocessing Before Hydro-enforcement

### Common geospatial preprocessing
Across branches, preprocessing is:

1. Determine UTM CRS from boundary centroid (`get_utm_crs_from_wgs84`).
2. Reproject vectors to UTM (`project_vector_data_to_utm`):
- boundary always,
- pour points when present,
- user road layer when uploaded.
3. Reproject DEM to UTM (`reproject_raster_from_path`, nearest-neighbor).
4. Clip DEM to boundary with 150 m offset (`clip_raster_with_offset(..., offset_distance_m=150)`).
5. Clip pour points to boundary when pour points exist (`clip_vector_data_to_polygon`).
6. Acquire road layer:
- use uploaded roads if present, else
- download OSM drive network over boundary bbox padded by `0.025` degrees.
7. Snap pour points to nearest road polyline within 20 m (`snap_points_to_polyline(..., snap_distance_m=20)`), in modes with pour points.

### Important preprocessing behavior

- Grouped pour points: if a `Grp_ID` column exists, `clip_vector_data_to_polygon` keeps one representative record per non-empty `Grp_ID`.
- OSM road widths are inferred by highway class (`motorway=25`, `trunk=15`, `primary=12`, `secondary=10`, `tertiary=8`, `residential=6`, `unclassified=5`).
- User-uploaded roads use `road_width` if present; otherwise breakline generation falls back to width `10.0`.

## Hydro-enforcement Operations

### Core terrain modification helper
`adjust_dem_along_polyline(...)` performs both road-fill and breakline-burn:

- Buffer polyline by `buffer_width` (meters in UTM CRS),
- Rasterize buffer (`all_touched=True`),
- Apply `dem + dy` for fill (`burn=False`) or `dem - dy` for burn (`burn=True`),
- Keep nodata unchanged.

### WhiteboxTools calls and parameters
Hydrologic conditioning and flow products use:

- `wbt.breach_depressions(..., max_depth=None, max_length=None, flat_increment=None, fill_pits=True)`
- `wbt.d8_pointer(..., esri_pntr=False)`
- `wbt.d8_flow_accumulation(..., out_type="cells", log=False, clip=False, pntr=True, esri_pntr=False)`
- `wbt.extract_streams(..., threshold=flow_accum_threshold, zero_background=False)`
- `wbt.raster_to_vector_lines(...)` for stream vectorization

## Branch-specific Processing

### 1) `both` / `culvert` branch (`watershed_delineation_point_both`)
Hydro-enforcement sequence when `hydroEnforcementSelect == 'hydroenf_required'`:

1. Create breaklines from pour points snapped to roads (`create_breaklines`, `offset=breakline_offset_m`).
2. Elevate DEM along roads:
- input DEM: `DEM_UTM.tif`
- output DEM: `road_elevated_DEM_UTM.tif`
- `dy=road_fill_dem_by_m`, `buffer_width=road_fill_Dem_buffer_m`, `burn=False`
3. Burn DEM along breaklines:
- input DEM: road-elevated DEM
- output DEM: `breaklines_burned_DEM_UTM.tif`
- `dy=breakline_burn_Dem_by_m`, `buffer_width=breakline_burn_dem_buffer_m`, `burn=True`
4. Breach/fill conditioned DEM from breakline-burned raster.
5. Compute D8 pointer, D8 flow accumulation, extract streams.

If hydro-enforcement is not required:

- breakline/DEM adjustments are skipped,
- `breach_depressions` runs directly on clipped DEM.

Then for both hydro and no-hydro:

- find road-stream intersections,
- snap snapped-road pour points to nearest intersection within `pour_point_snap_distance_m`,
- delineate nested watersheds from final pour points,
- calculate watershed metrics and filtering/flagging outputs.

### 2) `pour_pt_NA` branch (`watershed_delineation_point_NA`)
This branch is two-phase when hydro-enforcement is required.

Phase A (always):

1. Run baseline DEM conditioning from clipped DEM (breach/fill, D8, flow accumulation, streams).
2. Vectorize streams and compute road-stream intersection points.

Phase B (only if hydro-enforcement required):

1. Create breaklines at road-stream intersection points.
2. Elevate DEM along roads (`road_fill_dem_by_m`, `road_fill_Dem_buffer_m`).
3. Burn DEM along breaklines (`breakline_burn_Dem_by_m`, `breakline_burn_dem_buffer_m`).
4. Re-run breach/fill.
5. Re-run D8 pointer and D8 flow accumulation.

If hydro-enforcement is not required, Phase B is skipped; delineation uses Phase A products.

### 3) `gauging` branch (`watershed_delineation_point_only_gauging_st`)
Hydro-enforcement differs from the `both/culvert` branch:

- It creates breaklines from pour points snapped to roads,
- Burns DEM along breaklines,
- Does **not** include road-elevation/fill in this function,
- Then runs breach/fill, D8, flow accumulation, stream extraction.

Road-stream intersections are then generated, and gauging points are snapped into/onto those intersections inside `find_intersections_of_polylines(...)` using `pour_point_snap_distance_m`.

## Derived Vector Processing (post-flow products)
After flow and streams are available, watershed delineation uses:

- Road-stream intersection generation (`find_intersections_of_polylines`)
- Nested watershed delineation (`nested_basin_delineation`)
- Mean slope, longest channel path, max overland flow path, time of concentration
- Area filtering (`filter_watersheds_by_drainage_area`, min area `filter_Watershed_min_area_ha`)
- Outside-boundary flagging (`flag_watersheds_with_drainage_area_outside_region_boundary`)

Flagging uses:

- fixed boundary buffer distance of `10` m internally,
- user threshold `flag_wastershed_area_outside_boundary_ha` on outside-drainage area.

## Outputs Produced
Primary outputs in `.../{user_id}_outputs/{project_name}/WS_deln/`:

| Output file | Produced in |
| --- | --- |
| `Boundary_UTM.shp` | all branches |
| `DEM_UTM.tif` | all branches |
| `road_UTM.shp` | all branches |
| `breaklines_UTM.shp` | hydro-required paths |
| `road_elevated_DEM_UTM.tif` | hydro-required `both/culvert` and `pour_pt_NA` |
| `breaklines_burned_DEM_UTM.tif` | hydro-required paths |
| `breached_filled_DEM_UTM.tif` | all branches |
| `D8flow_dir_UTM.tif` | all branches |
| `bD8Flow_accum_UTM.tif` | all branches |
| `stream_vector_UTM.shp` | all branches |
| `road_stream_intersect_vector_UTM.shp` | all branches |
| `pour_points_snapped_to_roads_UTM.shp` | branches with pour points |
| `pour_points_snapped_to_RSCS_UTM.shp` | `both/culvert` branch |
| `all_ws_polygon_UTM.shp` | all branches |
| `ws_polygon_filtered_by_area_UTM.shp` | all branches |
| `pour_point_filtered_UTM.shp` | all branches |
| `final_flagged_ws_polygon_filtered_by_area_UTM.shp` | all branches |
| `ws_polygon_flag_ID.csv` | all branches |
| `final_flag_removed_ws_polygon_filtered_by_area_UTM.shp` | all branches |
| `final_flag_removed_pour_point_UTM.shp` | all branches |
| `final_watershed_html_map.html` | all branches |
| `watershed_delineation_form_data.txt` | all branches |
| `user_ws_deln_responses.txt` | all branches |

Notes:

- Shapefile outputs imply sidecars (`.dbf`, `.shx`, `.prj`, etc.).
- Temp files are created in the temp directory (`dem_reprojected1.tif`, `stream_raster_UTM.tif`, per-pour temporary watershed files) and mostly cleaned.

## Packaging-relevant Outputs
`tasks/build_payload.py` later expects:

- `WS_deln/breached_filled_DEM_UTM.tif`
- `WS_deln/pour_points_snapped_to_RSCS_UTM.shp`
- `WS_deln/all_ws_polygon_UTM.shp`
- `hydrogeo_vuln/main_stream_raster_UTM.tif` (from downstream analysis stage, not from WS_deln)

It also records `hydroEnforcementSelect` and flow accumulation threshold in payload metadata/model-parameters.

## Implementation Notes for Porting Assessment

- `pour_pt_NA` with hydro-enforcement performs one full pre-hydro flow stack, then repeats conditioning/flow stack after DEM modification.
- Raster operations are full-grid and sequential (road fill, breakline burn, breach/fill, D8, accumulation).
- Snap and breakline creation are Python/GeoPandas loops over points and road geometry, not vectorized.
- Current code path for `gauging` uses a branch-specific routine where road fill is absent in the called function implementation.

## `UnnestBasins` Replacement Notes (`weppcloud-wbt`)

As of 2026-02-16, the forked `UnnestBasins` implementation in `weppcloud-wbt` is the primary candidate to replace the Python pair:

- `nested_basin_delineation(...)`
- `establish_nesting_hierarchy(...)`

Current `UnnestBasins` behavior in this fork:

- Produces one raster per nesting order (`<output>_1.tif`, `<output>_2.tif`, ...).
- Produces a hierarchy sidecar CSV at `<output_stem>_hierarchy.csv`.
- Sidecar schema:
  - `outlet_id,parent_outlet_id,child_count,child_ids,nesting_order,hierarchy_level,is_root,row,column`

Optimization and validation status:

- Internal per-order processing now uses a one-pass full-grid assignment plus per-order ancestor remap (avoids retracing every flowpath for each order).
- Regression tests were added in `whitebox-tools-app/src/tools/hydro_analysis/unnest_basins.rs` to verify optimized order mapping matches legacy tracing behavior.
- Benchmarks recorded during implementation:
  - `Santee_10m_no_hydroenforcement`: Python nested workflow `58.876s`, Rust `UnnestBasins` `2.883s` (~20.4x faster for this component).
  - `Tallulah River Demo`: Rust `UnnestBasins` `886.748s` (~14m47s).
