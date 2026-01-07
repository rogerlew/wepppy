# weppcloud integration spec for Culvert_web_app
> Draft integration spec for connecting Culvert_web_app (culvert-at-risk.org) to wepp.cloud.
> Context source: docs/culvert-at-risk-integration/AGENTS.Culvert_web_app.md

## Context
- Culvert_web_app runs in the same rack as wepp.cloud with 10G connectivity.
- Culvert_web_app currently has a nonfunctional WEPP integration (placeholders only).
- We need a wepp.cloud API that accepts processed culvert inputs, runs WEPP per culvert, and returns artifacts for download.
- Initial focus: working integration with a simple auth model; later: long-lived JWT + webhooks for RQ jobs.

## Goals
- Provide a wepp.cloud API endpoint to accept a culvert project payload (processed DEM + culvert/watershed data).
- Kick off an RQ job that runs delineation for each culvert using WhiteboxToolsTopazEmulator, builds landuse, and soils, stochastic PRISM revision climates, and runs WEPP
- Persist and expose standardized artifacts for download by Culvert_web_app.
- Return an RQ job id for status polling.

## Non-goals
- Implementing Culvert_web_app changes (we provide payload spec and documentation for integration).
- Replacing Culvert_web_app's existing ws_deln pipeline.
- Final auth model (JWT + webhook registration) or full user auth alignment.
- Tracking Culvert_web_app end-user identity inside wepp.cloud (culvert app remains the system of record).

## Assumptions
- Culvert_web_app will do the initial hydro-enforcement, DEM conditioning, road burn/breach, and culvert watershed identification.
- Culvert_web_app will send a single ZIP payload with standardized contents and no shapefile sidecars.
- Inputs are delivered as GeoJSON + GeoTIFF, not ESRI shapefiles.
- wepp.cloud is authoritative for WEPP execution and artifact storage.

## Storage layout and naming
- Batch root: `/wc1/culverts/<culvert_batch_uuid>/`.
- Extract payload to `/wc1/culverts/<culvert_batch_uuid>/`.
- Canonical DEM path: `/wc1/culverts/<culvert_batch_uuid>/topo/hydro-enforced-dem.tif`.
- Each culvert is a canonical weppcloud project at `/wc1/culverts/<culvert_batch_uuid>/runs/<culvert_id>/`.
  - DEM symlink: instead of fetching/copying the DEM for each culvert project, create a symlink from per-run path to canonical DEM (e.g., `/wc1/culverts/<culvert_batch_uuid>/runs/<culvert_id>/dem/dem.tif` → `/wc1/culverts/<culvert_batch_uuid>/topo/hydro-enforced-dem.tif`). This is handled by a new `Ron.symlink_dem()` method that creates the symlink and sets `ron.map` (see DEM symlink manager below).
- `_base` project initialization: `culvert.cfg` specifies a `base_runid` key pointing to a template project that gets copied to `/wc1/culverts/<culvert_batch_uuid>/_base/`. This mirrors the BatchRunner pattern and stages shared parameters and defaults.

## End-to-end flow (proposed)
1. User creates a project in Culvert_web_app.
2. User uploads a high-res DEM (optional) and culvert/road inputs.
3. Culvert_web_app runs hydro-enforcement and identifies culvert watersheds.
4. Culvert_web_app packages outputs into a ZIP and POSTs to wepp.cloud API.
5. wepp.cloud validates payload, creates batch root, enqueues an RQ job, returns job id.
6. Culvert_web_app polls job status; on completion, downloads artifacts.

## API surface (wepp.cloud)
### POST /rq-engine/api/culverts-wepp-batch/
Create a batch and enqueue a culvert WEPP job. Implemented in rq-engine to avoid weppcloud 30s timeout enforcement for blocking workers.
Heavy topo generation (flovec/netful pruning/chnjnt) runs inside the RQ job, not the API handler, so the API stays fast and resilient under load.

Request (multipart/form-data):
- file: `payload.zip` (required)
- fields (JSON or form fields): undetermined; prefer embedding all required metadata inside `payload.zip`.

Response (JSON):
- job_id (standard RQ response payload)
- culvert_batch_uuid (for composing download url)
- status_url: `/rq-engine/api/jobstatus/{job_id}`

### Job status (existing)
Use existing RQ engine endpoints instead of custom status routes:
- `/rq-engine/api/jobstatus/{job_id}`
- `/rq-engine/api/jobinfo/{job_id}` (if richer metadata is needed)

### Artifacts access (existing)
Use the browse service for listing/downloading artifacts instead of a culvert-specific endpoint.

**Browse service URL scheme:**
- Batch root browse: `/culverts/<culvert_batch_uuid>/browse/`
- Per-culvert browse: `/culverts/<culvert_batch_uuid>/runs/<culvert_id>/culvert/browse/`
- Direct file download: `/culverts/<culvert_batch_uuid>/runs/<culvert_id>/culvert/browse/<path>`

This scheme mirrors the existing `/runs/{runid}/{config}/browse/` pattern. The same approach can be adopted for the batch runner (`/batch/{batch_uuid}/browse/`).

### DevOps system-engineering guidance
- Keep rq-engine as a thin API layer (upload, validation, extraction, enqueue, respond).
- Run CPU/IO-heavy work (topo generation, pruning, WEPP runs) inside RQ workers to avoid request timeouts and keep interactive workers responsive.
- Prefer idempotent batch steps in RQ so retries can resume without re-uploading payloads.

## DEM symlink manager
The `Ron` class gains a new method to handle preexisting DEMs without fetching or copying:

```python
def symlink_dem(self, dem_path: str) -> None:
    """
    Create a symlink to an external DEM and populate self.map.
    
    Used by culvert batch processing where the DEM is already available
    at a canonical location. Replaces the fetch_dem() flow.
    
    Args:
        dem_path: Absolute path to the source DEM (e.g., hydro-enforced-dem.tif)
    
    Side effects:
        - Creates <wd>/dem/ directory if needed
        - Creates symlink: <wd>/dem/dem.tif -> dem_path
        - Reads raster metadata and sets self.map (extent, crs, resolution)
    """
```

This method:
1. Creates the `<wd>/dem/` directory if it does not exist
2. Creates a symlink `<wd>/dem/dem.tif` → `dem_path`
3. Opens the target raster and populates `self.map` with extent, CRS, and resolution metadata
4. Does NOT copy the DEM (saves disk I/O and storage for large batches)

## Payload ZIP contract (proposed)
Top-level files/directories (required unless noted):
- `topo/hydro-enforced-dem.tif` (GeoTIFF)
- `topo/streams.tif` (GeoTIFF; binary stream raster, same projection/extent/resolution as DEM)
- `culverts/culvert_points.geojson` (same CRS as rasters—see CRS rules below)
- `culverts/watersheds.geojson` (watershed polygons with `Point_ID` attribute linking to culvert points; watershed rasters are deleted by Culvert_web_app after polygon creation)
- `metadata.json` (schema v1; project-level fields for observability)
- `model-parameters.json` (schema v1; optional processing overrides—excludes `mcl`/`csa` since streams are pre-computed)

Note: avoid ESRI shapefiles and sidecars entirely.

**Stream raster notes:**
- The `streams.tif` from Culvert_web_app (typically `main_stream_raster_UTM.tif`) is used to generate batch-level `topo/netful.tif`.
- Since streams are provided, `mcl` (minimum channel length) and `csa` (critical source area) parameters are NOT included in `model-parameters.json`—these were already applied when Culvert_web_app generated the stream network.
- wepp.cloud further post-processes `topo/netful.tif` at batch ingest: prune short stream segments, reduce stream order, then regenerate `chnjnt.tif` from the final `netful.tif`. This is needed because Culvert_web_app stream rasters can be extremely dense, which explodes hillslope counts and pushes WEPP into regimes outside typical watershed calibrations. Pruning yields a channel network closer to the scale WEPP watershed was tuned for, reducing unrealistic hillslopes and unstable channel erosion behavior.

### `metadata.json` schema (v1)
- `schema_version` (string, required; `culvert-metadata-v1`)
- `source` (object, required: `system` string, `project_id` string, `user_id` string optional)
- `created_at` (ISO 8601 string, required)
- `culvert_count` (int, required)
- `crs` (object, required: `proj4` string, `epsg` int optional)
- `dem` (object, required: `path` string, `resolution_m` number, `width` int, `height` int, `nodata` number)
- `streams` (object, required: `path` string, `nodata` number, `value_semantics` = `binary`)
- `culvert_points` (object, required: `path` string, `point_id_field` = `Point_ID`, `feature_count` int optional)
- `watersheds` (object, required: `path` string, `point_id_field` = `Point_ID`, `feature_count` int optional)

Notes:
- `culvert_batch_uuid` is minted by wepp.cloud and returned in the API response (not required in `metadata.json`).
- Payload hash/size are computed by wepp.cloud at upload time and are not required in `metadata.json`.

### `model-parameters.json` schema (v1)
- `schema_version` (string, required; `culvert-model-params-v1`)
- `base_project_runid` (string, optional)
- `nlcd_db` (string, optional; overrides `landuse.nlcd_db`)

Notes:
- Climate duration and soils DB use defaults from `culvert.cfg` (no override keys in v1).

### Coordinate system rules
- **Rasters must use a projected CRS with meter units** (e.g., UTM). WGS84 is NOT acceptable for rasters because cell size must be in meters for hydrological calculations.
- **GeoJSON must use the same CRS as the rasters.** Since DEMs can have 1m resolution, keeping all assets in the same projected CRS avoids reprojection artifacts and ensures pixel-accurate alignment.
- wepp.cloud will validate that all inputs share a common CRS and reject payloads where rasters and vectors have mismatched projections.

### Culvert ID attribute
The `culverts/culvert_points.geojson` must include a `Point_ID` attribute on each feature:
- **Field name:** `Point_ID` (matches Culvert_web_app convention)
- **Type:** integer or string (unique within the batch)
- **Usage:** Used to create per-culvert run directories (`/runs/<Point_ID>/`) and to join WEPP outputs back to culvert locations

### Watershed GeoJSON structure
The `culverts/watersheds.geojson` contains one polygon feature per culvert watershed:
- **Geometry:** Polygon (or MultiPolygon) representing the drainage area for each culvert
- **Required attribute:** `Point_ID` (integer or string) — must match the corresponding culvert in `culvert_points.geojson`
- **Nested watersheds:** Watersheds may overlap (downstream culverts contain upstream culverts' watersheds). Each polygon represents the **total contributing area** to that culvert, not the incremental area.
- **CRS:** Must match the DEM projection (UTM or other meter-based projected CRS)

Note: Culvert_web_app deletes watershed rasters after polygon creation, so the GeoJSON polygons are the source of truth for watershed geometry in the payload.

Example feature:
```json
{
  "type": "Feature",
  "properties": {
    "Point_ID": 42,
    "area_ha": 125.3
  },
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[...], ...]]
  }
}
```

**Important:** The watershed geometry is used by `Watershed.find_outlet()` to locate the outlet pixel on the DEM (see Per-culvert processing below).

## wepp.cloud job behavior (proposed)

### Batch initialization
Payload validation/extraction happens in the rq-engine API handler; batch topo generation and run orchestration happen inside the RQ job (`run_culvert_batch_rq`).
- Place hydro-enforced DEM at `/wc1/culverts/<culvert_batch_uuid>/topo/hydro-enforced-dem.tif`.
- Generate batch-level topo rasters from the shared DEM + streams:
  - `wbt.d8_pointer(dem=relief_fn, output=flovec_fn, esri_pntr=False)` → `topo/flovec.tif`
  - Copy `topo/streams.tif` → `topo/netful.tif` (no pruning yet)
  - Prune short streams (uses `watershed.wbt.mcl` from `culvert.cfg`):
    - `wbt.remove_short_streams(d8_pntr=flovec_fn, streams=topo/netful.tif, output=topo/netful.tif, min_length=mcl)`
  - Build a Strahler order raster from the pruned binary stream map:
    - `wbt.strahler_stream_order(d8_pntr=flovec_fn, streams=topo/netful.tif, output=topo/netful.strahler.tif)`
  - Reduce stream order `N` times (uses `culvert_runner.order_reduction_passes` from `culvert.cfg`, final pass emits a binary stream mask):
    - `wbt.prune_strahler_stream_order(streams=topo/netful.strahler.tif, output=topo/netful.tif, binary_output=true)`
  - `wbt.stream_junction_identifier(d8_pntr=flovec_fn, streams=topo/netful.tif, output=chnjnt_fn)` → `topo/chnjnt.tif`
- Create per-culvert runs under `/wc1/culverts/<culvert_batch_uuid>/runs/<Point_ID>/` using the `culvert` config.

### Per-culvert processing
For each culvert (identified by `Point_ID`):

1. **Link DEM and topo rasters:** Use `Ron.symlink_dem()` to symlink to the shared hydro-enforced DEM. Similarly link the shared `flovec.tif` and `netful.tif` into each run.

2. **Find outlet from watershed geometry:**
   ```python
   # Load the watershed polygon for this culvert from watersheds.geojson
   watershed_geom = get_watershed_geometry(Point_ID)

   # Use Watershed.find_outlet() to locate the outlet pixel
   # This finds the lowest elevation point on the watershed boundary
   # that intersects the stream network (from netful.tif)
   outlet_col, outlet_row = Watershed.find_outlet(watershed_geom)
   ```
   The `find_outlet()` method analyzes the watershed polygon against the DEM and stream network raster to determine the pour point pixel coordinates. This is more robust than using the culvert point directly, as it ensures the outlet is on the actual flow path.

3. **Delineate subcatchments/channels:** Use the WBT Topaz emulator with the identified outlet and the shared `flovec.tif`/`netful.tif`. Since streams are pre-computed by Culvert_web_app, no `mcl`/`csa` parameters are needed—the stream network is used as-is. Use a WBT-only `symlink_channels_map` flow (raster mode) instead of `build_channels`, then generate `netful.geojson` via:
   - `polygonize_netful(self.netful, self.netful_json)`
   - `json_to_wgs(self.netful_json)`

4. **Build inputs:** Generate landuse, soils, and climate inputs.

5. **Run WEPP:** Execute using stochastic PRISM revision climates (100-year simulation).

6. **Collect results:** Store per-culvert outputs and compile into Parquet summaries.

### Batch finalization
- Generate consolidated artifacts at batch level.
- Create `run_metadata.json` with success/failure status per culvert.

## Output artifacts (required)
- `run_metadata.json` (inputs, versions, timings, culvert run success or failure)
- Proof of concept: package existing outputs without new analysis or cross-culvert aggregation.
- For each culvert pack:
  - `subcatchments.wgs.geojson`
  - `channels.wgs.geojson`
  - `landuse.parquet`
  - `soils.parquet`
  - `hillslopes.parquet`
  - `channels.parquet`
  - wepp/output/interchange


## Observability
- RQ job status exposed via existing RQ engine endpoints (polling).
- Optional: emit status events into Redis DB 2 so Culvert_web_app can subscribe later.
- Follow BatchRunner conventions; add a `CulvertsRunner` NoDbBase for culvert batch logs/status.

## Auth and access (after proof of concept)
- JWT tokens
- Optional webhook callbacks for all `rq-engine/api` routes on job-completion.
- Treat the culvert app as the authenticated client (no per-end-user identity).

## Error handling
- Validation errors return HTTP 400 with structured error list.
- Execution failures return job status `failed` with `error_code` and `error_detail` in the RQ engine status endpoint.
- Artifacts access relies on the browse service; missing outputs should be surfaced there.

## Performance and limits
- Max ZIP size (2Gb)
- Max culvert count per batch (300).
- Max DEM size/resolution  (tbd).
- RQ worker concurrency and job timeouts (similar to batch).
- Run culvert watersheds in parallel (similar to batch).

## Missing details / open questions
- ~~Payload contract finalization: exact filenames, required metadata schema, CRS rules, optional inputs.~~ (CRS rules documented above)
- ~~GeoJSON attributes: canonical culvert id field and any required properties.~~ (Point_ID documented above)
- ~~Watershed raster encoding: confirm by inspecting Culvert_web_app pipeline.~~ (Changed to GeoJSON polygons; raster not needed)
- ~~Browse service path and expected UI flow for culvert downloads; may require a custom route.~~ (URL scheme documented above)
- ~~Stream raster in payload.~~ (streams.tif provided by Culvert_web_app; used for batch `netful.tif` generation; mcl/csa not needed)
- Retry and idempotency semantics for duplicate POSTs.
- Long-term auth model (JWT issuance, refresh, key rotation) and webhook payload schema/retry policy.
- Data retention policy and cleanup schedule in `/wc1/culverts/` (required).
- `Watershed.find_outlet()` implementation details: confirm method signature, handling of edge cases (multiple outlet candidates, watersheds that don't intersect flow network).
