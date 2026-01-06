# weppcloud integration plan for Culvert_web_app
> Implementation plan based on docs/culvert-at-risk-integration/weppcloud-integration.spec.md

## Guiding requirements (spec highlights)
- Endpoint: `POST /rq-engine/api/culverts-wepp-batch/` (multipart, FastAPI rq-engine to avoid 30s Caddy timeout; extend timeout there as needed).
- Storage: `/wc1/culverts/<culvert_batch_uuid>/` with per-culvert runs under `/runs/<Point_ID>/` and `_base/` seeded from `culvert.cfg`.
- Payload ZIP: `topo/hydro-enforced-dem.tif` + `topo/streams.tif` + `culverts/culvert_points.geojson` + `culverts/watersheds.geojson` + `metadata.json` + `model-parameters.json`; all inputs in the same projected CRS (meters).
- DEM handling: new `Ron.symlink_dem()` to symlink the canonical DEM into each run and populate `ron.map`.
- Streams: provided by Culvert_web_app (no mcl/csa parameters needed).
- Watersheds: GeoJSON polygons with `Point_ID` attribute (no raster, no culvert_id_map needed).
- RQ job status: use `/rq-engine/api/jobstatus/{job_id}`; artifacts via browse under `/culverts/<batch_uuid>/.../browse/`.
- Outputs: per-culvert GeoJSON + parquet + WEPP interchange; batch-level `run_metadata.json`.
- Limits: max ZIP 2GB, max 300 culverts; error responses are structured 400s.

## Phase 0 - Contract finalization and fixtures (COMPLETE)
- Scope: finalize `metadata.json` + `model-parameters.json` schema, idempotency rules, retention policy; use the `Santee_10m_no_hydroenforcement` project (local at `/wc1/culvert_app_instance_dir/user_data/`) as the baseline payload for validation.
- Dependencies: Culvert_web_app owners for schema fields and retention expectations; ops for cleanup window and storage constraints; security for initial auth choice.
- Deliverables: JSON schema docs for `metadata.json`/`model-parameters.json`, minimal sample payloads (synthetic + real), updated spec notes on retry/idempotency/retention.
- Risks: schema churn after implementation starts; large real payloads exceeding test budgets; mismatch between culvert outputs and payload contract.
- Verification: validated the baseline payload from `Santee_10m_no_hydroenforcement`; created `tests/culverts/test_payloads/santee_10m_no_hydroenforcement/payload.zip` and `tests/culverts/test_payloads/manifest.md`. The second payload will be added once the user 1 copy completes.

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

## Phase 1 - API ingestion, validation, and job enqueue (rq-engine) (COMPLETE)
- Scope: implement `/rq-engine/api/culverts-wepp-batch/` in rq-engine (FastAPI); accept multipart upload, mint `culvert_batch_uuid`, validate payload inline (payload_validator), extract payload, generate batch-level `topo/flovec.tif` + `topo/netful.tif`, enqueue RQ job, return `{job_id, culvert_batch_uuid, status_url}`. This keeps validation inside the ingestion path and avoids the 30s Caddy timeout applied to weppcloud routes. Long term, migrate `/rq/api/*` to `/rq-engine/api/*`.
- Request parameters (optional): `zip_sha256`, `total_bytes` to capture payload metadata since the ZIP is created client-side.
- Dependencies: Phase 0 schema decisions; RQ queue configuration; open endpoint for POC (auth deferred to Phase 6).
- Deliverables: rq-engine route + request/response contract; `payload_validator` module + error types; RQ job function stub (`run_culvert_batch_rq`); batch-level `topo/flovec.tif` (D8 pointer) and `topo/netful.tif` (stream junctions) generated from the shared DEM + streams; `batch_metadata.json` written at batch root; logging to batch root.
- Risks: upload timeouts for large ZIPs; unbounded disk usage; duplicate POSTs creating multiple batches without idempotency key; CRS parsing differences between raster/GeoJSON libs; `Point_ID` dtype mismatches; DEM/streams extent alignment.
- Verification: tests for rq-engine ingestion/validation (happy + invalid payloads); manual curl with a real payload; verify status via `/rq-engine/api/jobstatus/{job_id}`.

## Phase 2 - Culvert batch runner scaffolding (COMPLETE)
- Scope: create `CulvertsRunner` (or extend `BatchRunner`) to manage batch state/logging; implement `_base` project copy using `culvert.cfg` and `base_runid`; create per-culvert run dirs; add `Ron.symlink_dem()` and symlink `topo/flovec.tif` + `topo/netful.tif` into each run; map `Point_ID` to run IDs; set run_group metadata; add `symlink_channels_map` (WBT-only) to use the shared netful raster instead of `build_channels`.
- Dependencies: Phase 1 job entrypoint; `culvert.cfg` definition; agreement on runid template and run_group name.
- Deliverables: runner class + nodb state; `Ron.symlink_dem()` implementation; `symlink_channels_map` that enforces WBT backend in raster mode and emits `netful.geojson` via `polygonize_netful()` + `json_to_wgs()`; culvert config template; stub updates if `.pyi` exists.
- Risks: filesystem contention when creating many runs; symlink breakage on cleanup; runid collisions for non-unique `Point_ID`.
- Verification: unit tests for `Ron.symlink_dem()` and run directory creation; integration test that `_base` + one run hydrate NoDb singletons without errors.

## Phase 1/2 combined handoff summary
- Implemented rq-engine package split (`wepppy/microservices/rq_engine/`) with APIRouter modules; `/rq-engine/api/culverts-wepp-batch/` now accepts multipart `payload.zip`, validates inline, extracts to `/wc1/culverts/<culvert_batch_uuid>/`, generates `topo/flovec.tif` + `topo/netful.tif`, writes `batch_metadata.json`, enqueues `run_culvert_batch_rq`, and returns `{job_id, culvert_batch_uuid, status_url}`.
- Validator lives in `wepppy/microservices/culvert_payload_validator.py` (required files, CRS alignment, DEM/streams alignment, `Point_ID` coverage) and returns structured 400s.
- RQ entrypoint stub lives in `wepppy/rq/culvert_rq.py` (StatusMessenger wiring, TIMEOUT=43200).
- CulvertsRunner NoDb added (`wepppy/nodb/culverts_runner.py`) to create per-culvert runs under `/wc1/culverts/<culvert_batch_uuid>/runs/<Point_ID>/`, set run_group `culvert;;<batch_uuid>;;<runid>`, and record completion metadata.
- `Ron.symlink_dem()` + `Watershed.symlink_channels_map()` added to reuse shared DEM/topo rasters (WBT-only) and generate `netful.geojson`/`netful.WGS.geojson`.
- Added `culvert.cfg` with `[culvert_runner] base_runid` and culvert run_group resolution in `get_wd()` (uses `CULVERTS_ROOT`); `CulvertsRunner` now copies the base run into each batch `_base`.
- Tests added in `tests/microservices/test_rq_engine_culverts.py`, `tests/microservices/test_rq_engine_jobinfo.py`, and `tests/culverts/test_culverts_runner.py`; run with `wctl run-pytest tests/microservices/test_rq_engine_culverts.py`, `wctl run-pytest tests/microservices/test_rq_engine_jobinfo.py`, and `wctl run-pytest tests/culverts/test_culverts_runner.py`.
- Dependency update: add `python-multipart==0.0.12` to `docker/requirements-uv.txt` and rebuild the weppcloud image so multipart parsing works in fresh containers.
- Model-parameters overrides now applied during run setup (`base_project_runid`, `nlcd_db`).

## Phase 3 - Per-culvert WEPP orchestration
- Scope: orchestrate delineation, landuse, soils, climate, and WEPP per culvert using existing run tasks; incorporate WhiteboxToolsTopazEmulator; use `symlink_channels_map` to avoid `build_channels`; apply model-parameters overrides; record per-run success/failure in `run_metadata.json`.
- Dependencies: Phase 2 scaffolding; availability of WBT, PRISM, soils datasets in container; confirmed model-parameters schema.
- Deliverables: RQ orchestration pipeline; per-run execution logs; per-culvert metadata record (timings, versions, config).
- Risks: long runtimes for 300 culverts; missing datasets for runs; error isolation (one culvert failure should not cancel entire batch).
- Verification: integration test with a tiny payload (1-2 culverts) using mocked heavy tasks; manual run with real payloads in the container, confirming per-culvert outputs.

## Phase 4 - Artifact delivery and browse integration
- Scope: standardize output layout under `/culverts/<uuid>/runs/<id>/culvert/`; generate WGS84 GeoJSON outputs; write `run_metadata.json`; expose browse paths `/culverts/<uuid>/browse/` and `/culverts/<uuid>/runs/<id>/culvert/browse/`.
- Dependencies: Phase 3 outputs; browse service routing rules; decision on which artifacts are mandatory vs optional.
- Deliverables: artifact manifest + layout doc; browse route support for `/culverts/`; packaging helpers (copy/link outputs into `culvert/`).
- Risks: browse service path mapping gaps; missing outputs for failed culverts; large artifact sizes.
- Verification: browse integration test that lists and downloads artifacts; verify `run_metadata.json` and required files for successful culverts.

## Phase 5 - Observability, error handling, retention
- Scope: structured error codes for validation/execution; publish status events to Redis DB 2; update RQ job info with `error_code`/`error_detail`; implement cleanup/retention policy in `/wc1/culverts/` (delete 7 days after job completion, with completion time stored in `CulvertsRunner` state).
- Dependencies: Phase 1 RQ job framework; ops decision on retention window.
- Deliverables: error schema, status event payloads, cleanup job (cron or RQ) that reads `CulvertsRunner.completed_at` + retention window, run/batch log summaries.
- Risks: retention job deleting active batches; missing completion timestamp on failed jobs; missing error propagation in RQ engine.
- Verification: tests for error responses and RQ job metadata; simulated cleanup run with dry-run logging; verify status streaming in Redis.

## Phase 6 - Auth and webhook enhancements (post-POC)
- Scope: JWT issuance/rotation, webhook registration + retries, HMAC signing, opt-in callbacks on completion/failure.
- Dependencies: security decisions on token lifecycle; agreement on webhook payload schema.
- Deliverables: auth middleware, webhook dispatcher, docs for Culvert_web_app.
- Risks: callback storms for large batches; secrets management; backward compatibility with POC auth.
- Verification: auth enforcement tests; webhook retry tests with mock endpoints; manual validation with Culvert_web_app dev instance.

## Cross-phase test strategy (minimum)
**Implemented tests**
- `tests/microservices/test_rq_engine_culverts.py` (rq-engine culvert ingestion).
- `tests/microservices/test_rq_engine_jobinfo.py` (rq-engine jobinfo).
- Payload fixtures: `tests/culverts/test_payloads/`.

**Planned tests**
- Unit: `Ron.symlink_dem()`, culvert ID mapping, error formatting.
- Integration: per-culvert orchestration, browse URLs, RQ job status.
- Smoke/manual: real payloads from `/workdir/culvert_app_instance_dir/user_data/` in container; verify outputs and download.

## Open questions / blockers
- Idempotency/retry rules for duplicate POSTs (keying on payload hash? caller-supplied id?).
- Retention/cleanup window and ownership of `/wc1/culverts/` storage.
- Concurrency/timeouts for 300-culvert batches and RQ worker sizing.
