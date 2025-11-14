# Mini Work Package: HEC-RAS Boundary Condition GMLs from `post_dss_export_rq`

**Status:** Completed  
**Last Updated:** 2025-11-13  
**Primary Areas:** `wepppy/rq/wepp_rq.py`, `wepppy/nodb/core/watershed.py`, `wepppy/wepp/interchange/*`

---

## Objective
Augment the DSS export RQ pipeline so each WEPP channel targeted for export also emits a HEC-RAS-compatible boundary condition GML. Every channel Topo ID should produce a standalone `bc_<chn_topaz_id>.gml` comprised of a single line string (EPSG:4326) that is orthogonal to the downstream end of the channel and intersects the center of the lowest pixel mapped in `Watershed.subwta`.

## Current Flow & Gap
1. `post_dss_export_rq` (`wepppy/rq/wepp_rq.py:1162`) already orchestrates channel GeoJSON, partitioned DSS, chanout DSS, and zip archival. Nothing generates boundary condition artifacts today.
2. HEC-RAS boundary conditions require one geometry per channel boundary, ideally tied to WEPP’s channel IDs so downstream tooling can associate flows with spatial locations.
3. `Watershed.subwta` (ArcGrid or GeoTIFF) encodes the Topo ID of every channel/hillslope cell, but the DSS export pipeline never touches it; therefore we have no easy crosswalk between DSS outputs and spatial boundaries.

## Functional Requirements
- Trigger boundary generation inside `_write_dss_channel_geojson` so GeoJSON creation and boundary derivation share the same channel filter logic and metadata.
- Produce exactly one file per channel Topo ID using the naming convention `export/dss/boundaries/bc_<chn_topaz_id>.gml`.
- Each GML contains one `gml:LineString` expressed in WGS84 (EPSG:4326). The line:
  - Passes through the center of the **third pixel from the top** of the channel footprint (counting upward from the downstream end of the flowpath).
  - Is orthogonal to the channel direction estimated from the **second and third pixels from the bottom** (i.e., the second- and third-lowest elevation/downstream-distance cells).
- Extends a configurable distance on both sides of the center point controlled by a new `boundary_width_m` argument (default: 100 m, interpreted as the full line length so each endpoint is half of that distance from the center).
- Persist metadata (channel ID, Topo ID, optional WEPP ID) as XML attributes so downstream consumers can match files to DSS paths.
- Publish progress to `StatusMessenger` so UI clients see “generating HEC-RAS boundary GMLs…” with per-channel updates.
- Skips generation quietly when `Watershed.subwta` is missing, but surfaces actionable errors when inputs exist yet parsing fails.
- Embed the same boundary line geometries into the DSS channel GeoJSON output so users can visually confirm orientation without opening the GML files (e.g., GeoJSON `LineString` features per channel referencing identical coordinates/IDs).

## Technical Approach

### Inputs & Helpers
- `Watershed.getInstance(wd)` already computed during DSS export; reuse it to fetch:
  - `subwta` path (`Watershed.subwta`, `.ARC` or `.tif`).
- `relief` raster (same grid as `subwta`) to determine ordering by elevation; this smoothed DEM is required for boundary generation (Topaz `RELIEF.ARC` or WBT `relief.tif`).
  - `translator_factory()` to map Topo IDs ⇄ WEPP IDs when embedding metadata.
- Raster IO via `wepppy.all_your_base.geo.read_raster` (returns numpy array, GDAL transform, projection). We need both `subwta` labels and the GDAL transform to compute cell centers.
- CRS conversion: instantiate `GeoTransformer(src_proj4=subwta_proj, dst_epsg=4326)` (see `wepppy/all_your_base/geo/geo_transformer.py`) so we can convert easting/northing cell centers into lon/lat pairs for GML.

### Channel Endpoint Detection
1. Build a mask per channel by locating cells where `subwta == chn_topaz_id`. Skip when no pixels found (channel filtered out upstream).
2. Sample the matching cells in the smoothed DEM raster to rank them from lowest (downstream) to highest (upstream) value. Use `RELIEF.ARC` for Topaz runs and `WhiteboxToolsTopazEmulator.relief` for WhiteboxTools runs—these files are required inputs for boundary generation. “Lowest” means minimum elevation.
3. Extract the *second* and *third* lowest unique cells; these define the local flow direction vector used to compute the orthogonal boundary. If fewer than three unique pixels exist, fall back to the available ones but log a warning.
4. Use the *third-from-bottom* pixel (same one used as the upstream point for the direction vector) and place the boundary through its centroid so the cut line sits near the downstream outlet.
5. Convert raster indices `(col, row)` for the chosen pixels into projected coordinates using the GDAL transform:
   ```
   x = a + (col + 0.5) * b + (row + 0.5) * c
   y = d + (col + 0.5) * e + (row + 0.5) * f
   ```
6. Form the downstream direction vector `v = third_lowest - second_lowest`. Normalize it; the orthogonal vector is `n = (-v_y, v_x)` (rotate 90°).

### Boundary Line Construction
1. Determine a physical step size. Proposal: `line_half_length = max(cellsize, 5.0)` meters so the cut line spans ≥ one cell. Make this configurable constant near the generator.
2. Normalize `n`; compute endpoints in projected CRS: `p1 = center - n_unit * line_half_length`, `p2 = center + n_unit * line_half_length`.
3. Transform both endpoints to WGS84 using the `GeoTransformer`.
4. Write a minimal GML file. Suggested structure:
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <gml:FeatureCollection xmlns:gml="http://www.opengis.net/gml" xmlns:bc="https://weppcloud.org/hec-ras/boundary">
     <gml:featureMember>
       <bc:BoundaryCondition topazId="1234" weppId="89" channelName="chn_1234">
         <gml:LineString srsName="EPSG:4326">
           <gml:posList>-116.12345 45.67890 -116.12310 45.67920</gml:posList>
         </gml:LineString>
       </bc:BoundaryCondition>
     </gml:featureMember>
   </gml:FeatureCollection>
   ```
5. Use `xml.etree.ElementTree` to avoid extra dependencies; pretty-print for readability.

### Wiring into `post_dss_export_rq`
1. Implement a helper (e.g., `wepppy/wepp/interchange/hec_ras_boundary.py`) exposing `generate_boundary_gmls(wd, channel_ids=None, status_channel=None)`.
2. Call the helper near the end of `post_dss_export_rq` after DSS artifacts exist but before the final completion message, passing the `channel_filter` already computed.
3. `_write_dss_channel_geojson` already has direct access to the filtered channel list and GeoJSON metadata; extend it to:
   - Accept `boundary_width_m: float = 100.0`.
   - Load raster data / build boundary lines.
   - Inject each boundary line as a `Feature` inside the GeoJSON (possibly with a `geometry` type `LineString` and a property flag `boundary_condition=True`).
   - Persist corresponding GML using the shared helper (or inline logic) so data stays consistent.
4. `post_dss_export_rq` status sequence should add a new message before GeoJSON creation (“writing DSS channel geojson + boundary GMLs…”) but no longer needs a separate post-step trigger.

### Telemetry & Cleanup
- Ensure the target directory (`export/dss/boundaries/`) is cleared before regeneration to avoid stale files from previous runs.
- Record `prep.timestamp(TaskEnum.dss_export)` only once (existing behavior). No task enum change needed, but consider emitting a distinct status event `DSS_BOUNDARY_READY` in case UI wants to react later.

## Implementation Tasks
1. **Utility Module**
   - Create `wepppy/wepp/interchange/hec_ras_boundary.py` encapsulating raster loading, channel vector math, CRS transforms, and XML writing.
   - Provide unit-testable pure functions: `find_channel_lowest_cells`, `orthogonal_line`, `write_gml`.

2. **RQ Integration**
   - Import the helper inside `post_dss_export_rq`.
   - Add logging/status messages and directory management under `export/dss/boundaries`.

3. **Tests**
   - Add synthetic raster fixtures (tiny numpy arrays + dummy transforms) under `tests/wepp/interchange/test_hec_ras_boundary.py`.
   - Validate:
     - Channel mask selection by Topo ID.
     - Orthogonal computation matches expectations.
     - GML serialization includes metadata and WGS84 coordinates.
   - Add regression test ensuring `post_dss_export_rq` calls the helper (use monkeypatch to capture arguments).

4. **Docs & Readme**
   - Update `wepppy/wepp/interchange/README.md` (or create a short note) describing the new boundary artifacts and where they live.

## Acceptance Criteria
- Running `post_dss_export_rq` on a project with `subwta` present yields `export/dss/boundaries/bc_<topaz>.gml` files for each exported channel.
- Each GML’s `posList` contains two coordinate pairs expressed in lon/lat degrees and visually matches an orthogonal cutline through the downstream-most channel pixel when plotted.
- Status topic `<runid>:dss_export` shows the new boundary generation messages.
- Unit tests covering raster math and serialization pass (`wctl run-pytest tests/wepp/interchange/test_hec_ras_boundary.py`).

## Open Questions / Follow-Ups
1. **Line Length Tuning:** Is one cell-width sufficient for HEC-RAS, or do we need a longer lever arm (e.g., 20 m) so cross-section extraction grabs enough DEM samples?
2. **Multi-pixel Lowest Tie:** When several pixels share the same lowest elevation, should we average their centers before deriving orientation?
3. **Output Packaging:** Do the boundary GMLs need to be zipped alongside DSS outputs or referenced in metadata for download bundles?
4. **Channel Naming:** Should filenames reflect WEPP IDs (`bc_wepp_12.gml`) or stay Topo-based as requested?
5. **Coordinate Precision:** Default double precision may be overkill; confirm whether HEC-RAS expects 6 decimal places or more.

## Implementation Summary (2025-11-13)
- Added `wepppy/wepp/interchange/hec_ras_boundary.py`, which loads `subwta` + smoothed `relief` rasters, derives downstream flow vectors from the second/third-lowest pixels, and emits both GeoJSON `LineString` features and per-channel `bc_<topaz>.gml` artifacts in EPSG:4326. Boundary centers now align with the third-from-bottom pixel so they cut across the channel outlet, and fallbacks/warnings are logged when insufficient pixels exist.
- `_write_dss_channel_geojson` now calls the helper, appending boundary features to the DSS GeoJSON and persisting GML files in `export/dss/boundaries/`. `boundary_width_m` remains configurable (default 100 m), and the status feed announces the combined GeoJSON + boundary step.
- Relief rasters (`RELIEF.ARC` for Topaz, `relief.tif` for WBT) are enforced as mandatory inputs; missing files abort boundary generation with actionable log messages.
- Added `tests/wepp/interchange/test_hec_ras_boundary.py` to exercise the raster math, orthogonal vector computation, GeoJSON metadata, and GML serialization. The test verifies coordinates/centroid placement and guards against regressions in future geometry changes.

## Validation
- `wctl run-pytest tests/wepp/interchange/test_hec_ras_boundary.py`
- Manual spot checks on channels 644 (east) and 275 (north) confirmed orthogonal boundaries that intersect the downstream-most channel pixels, with matching GeoJSON + GML outputs.

## Remaining Questions / Follow-Ups
1. **Line Length Tuning:** Boundary width is configurable (default 100 m), but we still need hydrologist feedback on ideal span for sampling HEC-RAS cross sections.
2. **Tie Handling Enhancements:** Current logic skips duplicate pixel coordinates when ordering. If more sophisticated tie-breaking (averaging centroids) is required, document the desired behavior.
3. **Output Packaging & Discovery:** GMLs live under `export/dss/boundaries/` and are referenced inside the DSS GeoJSON, but we have not yet added them to download bundles or UI panels. Define how users should retrieve/preview them.
4. **Filename Convention:** We currently use Topaz IDs (`bc_<topaz>.gml`). Update the spec if WEPP IDs or composite naming (`bc_<topaz>_wepp_<id>.gml`) would help downstream tooling.
