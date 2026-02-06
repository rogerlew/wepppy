# Mini Work Package: Channel Delineation Upload DEM Extent Mode
Status: Completed
Last Updated: 2026-02-06
Primary Areas: `wepppy/microservices/rq_engine/watershed_routes.py`, `wepppy/rq/project_rq.py`, `wepppy/nodb/core/watershed.py`, `wepppy/weppcloud/templates/controls/channel_delineation_pure.htm`, `wepppy/weppcloud/controllers_js/channel_delineation.js`, `wepppy/weppcloud/controllers_js/channel_gl.js`

## Objective
Add a 4th extent mode (“Upload DEM”) for channel delineation that lets users upload a GeoTIFF DEM, validates and prepares it for Ron, and runs channel extraction without the fetch-dem job.

## Scope
- UI: new extent-mode radio + upload control + current filename display.
- Backend: new upload endpoint; DEM validation (CRS, size, square pixels for UTM); optional warp to UTM based on top-left corner.
- Ron: set `map`, `cellsize`, and install `dem/dem.vrt`.
- RQ chain: skip `fetch_dem_rq` when `set_extent_mode == 3`.
- UX: Build button enabled only when a DEM is uploaded; on completion, fly to DEM extent.

## Non-goals
- Previewing or styling uploaded DEMs on the map.
- Supporting non-GeoTIFF formats or DEMs larger than 1024x1024.
- Changing the standard DEM fetch pipeline for other extent modes.

## Implementation Notes
- Upload path: `/rq-engine/api/runs/<runid>/<config>/tasks/upload-dem/`.
- Validation rules: `.tif` only, spatial reference required, Float32/Float64 data type, width/height <= 1024.
- UTM check: if CRS is UTM, enforce square pixels and no rotation; do not reproject.
- Non-UTM: compute UTM zone from top-left corner (WGS) and warp to that UTM; then enforce square pixels.
- Install: write `dem/dem.vrt` pointing to final DEM; set `Ron.cellsize` and `Ron.map` from WGS extent.
- Build: `fetch_dem_and_build_channels_rq` enqueues only `build_channels_rq` for mode 3.

## Considerations / Follow-ups
- Cleanup: decide whether to delete failed uploads (and any intermediate warp outputs).
- UTM boundary runs: confirm top-left corner zone choice is acceptable for large rasters.
- Resampling: confirm `bilinear` is appropriate for DEM warp; consider `cubic` if needed.
- Metadata: consider storing DEM source path + warp info for auditing.
- UI hinting: show server-side validation errors in the upload hint.
- Extent sync: if the user reloads, consider a dedicated endpoint that returns Ron’s map object so the UI can re-fly.

## Validation
- Upload a UTM GeoTIFF with square pixels (<=1024) and ensure Build Channels is enabled.
- Upload a non-UTM GeoTIFF and confirm it is warped to UTM and installs `dem/dem.vrt`.
- Upload a DEM with non-square pixels and confirm the upload fails.
- Upload a DEM with integer data (Int16/Int32) and confirm the upload fails with a float requirement error.
- Build Channels in Upload DEM mode and confirm it skips `fetch_dem_rq`.
- On completion, confirm the map flies to the DEM extent.
