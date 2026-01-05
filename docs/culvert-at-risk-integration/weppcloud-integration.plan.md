# weppcloud integration plan for Culvert_web_app
> Implementation plan based on docs/culvert-at-risk-integration/weppcloud-integration.spec.md

## Guiding requirements (spec highlights)
- Endpoint: `POST /rq/api/culverts-wepp-batch/` (multipart, routed via `blueprint_bp` to avoid 30s Caddy timeout).
- Storage: `/wc1/culverts/<culvert_batch_uuid>/` with per-culvert runs under `/runs/<Point_ID>/` and `_base/` seeded from `culvert.cfg`.
- Payload ZIP: `topo/hydro-enforced-dem.tif` + `topo/streams.tif` + `culverts/culvert_points.geojson` + `culverts/watersheds.geojson` + `metadata.json` + `model-parameters.json`; all inputs in the same projected CRS (meters).
- DEM handling: new `Ron.link_dem()` to symlink the canonical DEM into each run and populate `ron.map`.
- Streams: provided by Culvert_web_app (no mcl/csa parameters needed).
- Watersheds: GeoJSON polygons with `Point_ID` attribute (no raster, no culvert_id_map needed).
- RQ job status: use `/rq-engine/api/jobstatus/{job_id}`; artifacts via browse under `/culverts/<batch_uuid>/.../browse/`.
- Outputs: per-culvert GeoJSON + parquet + WEPP interchange; batch-level `run_metadata.json`.
- Limits: max ZIP 2GB, max 300 culverts; error responses are structured 400s.

## Phase 0 - Contract finalization and fixtures
- Scope: finalize `metadata.json` + `model-parameters.json` schema, idempotency rules, retention policy; gather real payloads from `/workdir/culvert_app_instance_dir/user_data/` for validation (copy in progress).
- Dependencies: Culvert_web_app owners for schema fields and retention expectations; ops for cleanup window and storage constraints; security for initial auth choice.
- Deliverables: JSON schema docs for `metadata.json`/`model-parameters.json`, minimal sample payloads (synthetic + real), updated spec notes on retry/idempotency/retention.
- Risks: schema churn after implementation starts; large real payloads exceeding test budgets; mismatch between culvert outputs and payload contract.
- Verification: validate at least 2 real culvert projects against draft schema; create tiny synthetic payload fixtures for tests (sub-10MB).

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
- `mcl`/`csa` parameters are NOT included—streams are pre-computed by Culvert_web_app and provided in `topo/streams.tif`.
- Climate duration and soils DB use defaults from `culvert.cfg` (no override keys in v1).

## Phase 1 - Payload ingestion and validation
- Scope: implement ZIP intake, extraction to `/wc1/culverts/<uuid>/`, file presence/size checks, CRS validation (rasters + GeoJSON), `Point_ID` validation in both `culvert_points.geojson` and `watersheds.geojson`, structured 400 errors.
- Dependencies: Phase 0 schema decisions; access to real payload examples.
- Deliverables: `payload_validator` module + error types; validation checklist (filenames, CRS, extents, nodata rules, Point_ID matching); failure payload format.
- Risks: CRS parsing differences between raster/GeoJSON libs; `Point_ID` dtype mismatches; DEM/streams extent alignment.
- Verification: pytest unit tests for validator using synthetic rasters/GeoJSON; manual validation against real payload ZIPs from `/workdir/culvert_app_instance_dir/user_data/`.

## Phase 2 - API endpoint and job enqueue
- Scope: add `/rq/api/culverts-wepp-batch/` in rq blueprint, accept multipart upload, mint `culvert_batch_uuid`, call validator, extract payload, enqueue RQ job, return `{job_id, culvert_batch_uuid, status_url}`.
- Request parameters (optional): `zip_sha256`, `total_bytes` to capture payload metadata since the ZIP is created client-side.
- Dependencies: Phase 1 validator; RQ queue configuration; open endpoint for POC (auth deferred to Phase 7).
- Deliverables: Flask route + request/response contract; RQ job function stub (`run_culvert_batch_rq`); batch-level `topo/flovec.tif` (D8 pointer) and `topo/netful.tif` (stream junctions) generated from the shared DEM + streams; logging to batch root.
- Risks: upload timeouts for large ZIPs; unbounded disk usage; duplicate POSTs creating multiple batches without idempotency key.
- Verification: Flask client tests covering success and validation errors; manual curl with a real payload; verify status via `/rq-engine/api/jobstatus/{job_id}`.

## Phase 3 - Culvert batch runner scaffolding
- Scope: create `CulvertsRunner` (or extend `BatchRunner`) to manage batch state/logging; implement `_base` project copy using `culvert.cfg` and `base_runid`; create per-culvert run dirs; add `Ron.link_dem()` and symlink `topo/flovec.tif` + `topo/netful.tif` into each run; map `Point_ID` to run IDs; set run_group metadata; add `symlink_channels_map` (WBT-only) to use the shared netful raster instead of `build_channels`.
- Dependencies: Phase 2 job entrypoint; `culvert.cfg` definition; agreement on runid template and run_group name.
- Deliverables: runner class + nodb state; `Ron.link_dem()` implementation; `symlink_channels_map` that enforces WBT backend in raster mode and emits `netful.geojson` via `polygonize_netful()` + `json_to_wgs()`; culvert config template; stub updates if `.pyi` exists.
- Risks: filesystem contention when creating many runs; symlink breakage on cleanup; runid collisions for non-unique `Point_ID`.
- Verification: unit tests for `Ron.link_dem()` and run directory creation; integration test that `_base` + one run hydrate NoDb singletons without errors.

## Phase 4 - Per-culvert WEPP orchestration
- Scope: orchestrate delineation, landuse, soils, climate, and WEPP per culvert using existing run tasks; incorporate WhiteboxToolsTopazEmulator; use `symlink_channels_map` to avoid `build_channels`; apply model-parameters overrides; record per-run success/failure in `run_metadata.json`.
- Dependencies: Phase 3 scaffolding; availability of WBT, PRISM, soils datasets in container; confirmed model-parameters schema.
- Deliverables: RQ orchestration pipeline; per-run execution logs; per-culvert metadata record (timings, versions, config).
- Risks: long runtimes for 300 culverts; missing datasets for runs; error isolation (one culvert failure should not cancel entire batch).
- Verification: integration test with a tiny payload (1-2 culverts) using mocked heavy tasks; manual run with real payloads in the container, confirming per-culvert outputs.

## Phase 5 - Artifact delivery and browse integration
- Scope: standardize output layout under `/culverts/<uuid>/runs/<id>/culvert/`; generate WGS84 GeoJSON outputs; write `run_metadata.json`; expose browse paths `/culverts/<uuid>/browse/` and `/culverts/<uuid>/runs/<id>/culvert/browse/`.
- Dependencies: Phase 4 outputs; browse service routing rules; decision on which artifacts are mandatory vs optional.
- Deliverables: artifact manifest + layout doc; browse route support for `/culverts/`; packaging helpers (copy/link outputs into `culvert/`).
- Risks: browse service path mapping gaps; missing outputs for failed culverts; large artifact sizes.
- Verification: browse integration test that lists and downloads artifacts; verify `run_metadata.json` and required files for successful culverts.

## Phase 6 - Observability, error handling, retention
- Scope: structured error codes for validation/execution; publish status events to Redis DB 2; update RQ job info with `error_code`/`error_detail`; implement cleanup/retention policy in `/wc1/culverts/` (delete 7 days after job completion, with completion time stored in `CulvertsRunner` state).
- Dependencies: Phase 2 RQ job framework; ops decision on retention window.
- Deliverables: error schema, status event payloads, cleanup job (cron or RQ) that reads `CulvertsRunner.completed_at` + retention window, run/batch log summaries.
- Risks: retention job deleting active batches; missing completion timestamp on failed jobs; missing error propagation in RQ engine.
- Verification: tests for error responses and RQ job metadata; simulated cleanup run with dry-run logging; verify status streaming in Redis.

## Phase 7 - Auth and webhook enhancements (post-POC)
- Scope: JWT issuance/rotation, webhook registration + retries, HMAC signing, opt-in callbacks on completion/failure.
- Dependencies: security decisions on token lifecycle; agreement on webhook payload schema.
- Deliverables: auth middleware, webhook dispatcher, docs for Culvert_web_app.
- Risks: callback storms for large batches; secrets management; backward compatibility with POC auth.
- Verification: auth enforcement tests; webhook retry tests with mock endpoints; manual validation with Culvert_web_app dev instance.

## Cross-phase test strategy (minimum)
- Unit: payload validator, `Ron.link_dem()`, culvert ID mapping, error formatting.
- Integration: `/rq/api/culverts-wepp-batch/` happy/invalid paths; RQ job status; browse URLs.
- Smoke/manual: real payloads from `/workdir/culvert_app_instance_dir/user_data/` in container; verify outputs and download.
- Commands (containerized): `wctl run-pytest tests/weppcloud/routes/test_culvert_batch_api.py`, `wctl run-pytest tests/weppcloud/culvert/test_payload_validator.py`.

## Open questions / blockers (carry into Phase 0)
- Idempotency/retry rules for duplicate POSTs (keying on payload hash? caller-supplied id?).
- Retention/cleanup window and ownership of `/wc1/culverts/` storage.
- Concurrency/timeouts for 300-culvert batches and RQ worker sizing.
