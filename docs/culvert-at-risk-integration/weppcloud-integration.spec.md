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
- Canonical DEM path: `/wc1/culverts/<culvert_batch_uuid>/dem/hydro-enforced-dem.tif`.
- Each culvert is a canonical weppcloud project at `/wc1/culverts/<culvert_batch_uuid>/runs/<culvert_id>/`.
  - create a symlink to the canonical DEM path (e.g. `/wc1/culverts/<culvert_batch_uuid>/dem/hydro-enforced-dem.tif` -> `/wc1/culverts/<culvert_batch_uuid>/runs/<culvert_id>/dem/dem.tif`)
- Use an existing culvert `_base` project: `/wc1/culverts/<culvert_batch_uuid>/runs/_base/` used to stage shared parameters and defaults (mirrors BatchRunner pattern).

## End-to-end flow (proposed)
1. User creates a project in Culvert_web_app.
2. User uploads a high-res DEM (optional) and culvert/road inputs.
3. Culvert_web_app runs hydro-enforcement and identifies culvert watersheds.
4. Culvert_web_app packages outputs into a ZIP and POSTs to wepp.cloud API.
5. wepp.cloud validates payload, creates batch root, enqueues an RQ job, returns job id.
6. Culvert_web_app polls job status; on completion, downloads artifacts.

## API surface (wepp.cloud)
### POST /rq/api/culverts-wepp-batch/
Create a batch and enqueue a culvert WEPP job. Must be routed through `blueprint_bp` to avoid the 30s Caddy timeout for weppcloud routes.

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

## Payload ZIP contract (proposed)
Top-level files/directories (required unless noted):
- `topo/hydro-enforced-dem.tif` (GeoTIFF)
- `topo/streams.tif` (GeoTIFF; same projection, extent, and resolution as DEM)
- `topo/watersheds.tif` (GeoTIFF; same projection, extent, and resolution as DEM)
- `culverts/culvert_points.geojson` (WGS84 lat/long)
- `metadata.json` (schema TBD; project level fields for observability)
- `model-parameters.json` (schema TBD; must include everything needed for processing)

Note: avoid ESRI shapefiles and sidecars entirely.

## wepp.cloud job behavior (proposed)
- Validate ZIP structure, verify GeoJSON + GeoTIFF alignment, and confirm coordinate system.
- Extract payload to `/wc1/culverts/<culvert_batch_uuid>/`.
- Ensure `/wc1/culverts/<culvert_batch_uuid>/dem/hydro-enforced-dem.tif` exists (create symlink if needed).
- Create per-culvert runs under `/wc1/culverts/<culvert_batch_uuid>/runs/<culvert_id>/` using the `culvert` config.
- For each culvert id:
  - Use WhiteboxToolsTopazEmulator (parameters from `culvert.cfg`, optionally adjusted by DEM resolution) to delineate subcatchments/channels.
  - Run WEPP using stochastic PRISM revision climates (100-year climate).
  - Collect per-culvert results into Parquet summaries.
- Generate consolidated artifacts at run level.

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
- Optional webhook callbacks for all `rq/api` routes on job-completion.
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
- Payload contract finalization: exact filenames, required metadata schema, CRS rules, optional inputs.
- GeoJSON attributes: canonical culvert id field and any required properties.
- Watershed raster encoding: confirm by inspecting Culvert_web_app pipeline (value semantics, nodata rules).
- Browse service path and expected UI flow for culvert downloads; may require a custom route.
- Retry and idempotency semantics for duplicate POSTs.
- Long-term auth model (JWT issuance, refresh, key rotation) and webhook payload schema/retry policy.
- Data retention policy and cleanup schedule in `/wc1/culverts/` (required).
