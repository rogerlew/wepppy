# weppcloud integration plan for Culvert_web_app
> Implementation plan based on docs/culvert-at-risk-integration/weppcloud-integration.spec.md

## Guiding requirements (spec highlights)
- Endpoint: `POST /rq-engine/api/culverts-wepp-batch/` (multipart, FastAPI rq-engine to avoid 30s Caddy timeout; extend timeout there as needed).
- Storage: `/wc1/culverts/<culvert_batch_uuid>/` with per-culvert runs under `/runs/<Point_ID>/` and `_base/` seeded from `culvert.cfg`.
- Payload ZIP: `topo/breached_filled_DEM_UTM.tif` + `topo/streams.tif` + `culverts/culvert_points.geojson` + `culverts/watersheds.geojson` + `metadata.json` + `model-parameters.json`; all inputs in the same projected CRS (meters).
- GeoJSON validation: `culvert_points` must use Point geometries, `watersheds` must use Polygon/MultiPolygon geometries, and each GeoJSON includes a named CRS matching the rasters.
- DEM handling: new `Ron.symlink_dem()` to symlink the canonical DEM into each run and populate `ron.map`.
- Streams: provided by Culvert_web_app (no mcl/csa parameters needed).
- Watersheds: GeoJSON polygons with `Point_ID` attribute (no raster, no culvert_id_map needed).
- RQ job status: use `/rq-engine/api/jobstatus/{job_id}`; artifacts via browse under `/weppcloud/culverts/<batch_uuid>/browse/`.
- Outputs: per-culvert GeoJSON + parquet + WEPP interchange; batch-level `batch_summary.json` plus per-run `run_metadata.json`.
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
- `flow_accum_threshold` (int, optional; preserved for traceability when provided in metadata)
- `hydro_enforcement_select` (string, optional; normalized from `hydroEnforcementSelect` in Culvert_web_app)

Notes:
- `culvert_batch_uuid` is minted by wepp.cloud and returned in the API response (not required in `metadata.json`).
- Payload hash/size are computed by wepp.cloud at upload time and are not required in `metadata.json`.

### `model-parameters.json` schema (v1)
- `schema_version` (string, required; `culvert-model-params-v1`)
- `base_project_runid` (string, optional)
- `nlcd_db` (string, optional; overrides `landuse.nlcd_db`)
- `order_reduction_passes` (integer, optional; overrides `culvert_runner.order_reduction_passes`)
- `flow_accum_threshold` (integer, optional; flow accumulation threshold from Culvert_web_app)

Notes:
- `mcl`/`csa` parameters are NOT included—streams are pre-computed by Culvert_web_app and provided in `topo/streams.tif`.
- Climate duration and soils DB use defaults from `culvert.cfg` (no override keys in v1).

## Phase 1 - API ingestion, validation, and job enqueue (rq-engine) (COMPLETE)
- Scope: implement `/rq-engine/api/culverts-wepp-batch/` in rq-engine (FastAPI); accept multipart upload, mint `culvert_batch_uuid`, validate payload inline (payload_validator), extract payload, enqueue RQ job, return `{job_id, culvert_batch_uuid, status_url}`. Add `/rq-engine/api/culverts-wepp-batch/{batch_uuid}/retry/{point_id}` for flake-checking reruns. This keeps validation inside the ingestion path and avoids the 30s Caddy timeout applied to weppcloud routes. Long term, migrate `/rq/api/*` to `/rq-engine/api/*`.
- Request parameters (optional): `zip_sha256`, `total_bytes` to capture payload metadata since the ZIP is created client-side.
- Dependencies: Phase 0 schema decisions; RQ queue configuration; open endpoint for POC (auth deferred to Phase 6).
- Deliverables: rq-engine route + request/response contract; `payload_validator` module + error types; RQ job function stub (`run_culvert_batch_rq`); `batch_metadata.json` written at batch root; logging to batch root.
- Risks: upload timeouts for large ZIPs; unbounded disk usage; duplicate POSTs creating multiple batches without idempotency key; CRS parsing differences between raster/GeoJSON libs; `Point_ID` dtype mismatches; DEM/streams extent alignment.
- Verification: tests for rq-engine ingestion/validation (happy + invalid payloads); manual curl with a real payload; verify status via `/rq-engine/api/jobstatus/{job_id}`.

## Phase 2 - Culvert batch runner scaffolding (COMPLETE)
- Scope: create `CulvertsRunner` (or extend `BatchRunner`) to manage batch state/logging; implement `_base` project copy using `culvert.cfg` and `base_runid`; create per-culvert run dirs; add `Ron.symlink_dem()` and symlink `topo/flovec.tif` + `topo/netful.tif` into each run; map `Point_ID` to run IDs; set run_group metadata; add `symlink_channels_map` (WBT-only) to use the shared netful raster instead of `build_channels`.
- Dependencies: Phase 1 job entrypoint; `culvert.cfg` definition; agreement on runid template and run_group name.
- Deliverables: runner class + nodb state; `Ron.symlink_dem()` implementation; `symlink_channels_map` that enforces WBT backend in raster mode and emits `netful.geojson` via `polygonize_netful()` + `json_to_wgs()`; culvert config template; stub updates if `.pyi` exists.
- Risks: filesystem contention when creating many runs; symlink breakage on cleanup; runid collisions for non-unique `Point_ID`.
- Verification: unit tests for `Ron.symlink_dem()` and run directory creation; integration test that `_base` + one run hydrate NoDb singletons without errors.

## Phase 1/2 combined handoff summary
- Implemented rq-engine package split (`wepppy/microservices/rq_engine/`) with APIRouter modules; `/rq-engine/api/culverts-wepp-batch/` now accepts multipart `payload.zip`, validates inline, extracts to `/wc1/culverts/<culvert_batch_uuid>/`, writes `batch_metadata.json`, enqueues `run_culvert_batch_rq`, and returns `{job_id, culvert_batch_uuid, status_url}`.
- Validator lives in `wepppy/microservices/culvert_payload_validator.py` (required files, CRS alignment, DEM/streams alignment, `Point_ID` coverage) and returns structured 400s.
- RQ entrypoint stub lives in `wepppy/rq/culvert_rq.py` (StatusMessenger wiring, TIMEOUT=43200).
- CulvertsRunner NoDb added (`wepppy/nodb/culverts_runner.py`) to create per-culvert runs under `/wc1/culverts/<culvert_batch_uuid>/runs/<Point_ID>/`, set run_group `culvert;;<batch_uuid>;;<runid>`, and record completion metadata.
- `Ron.symlink_dem()` + `Watershed.symlink_channels_map()` added to reuse shared DEM/topo rasters (WBT-only) and generate `netful.geojson`/`netful.WGS.geojson`.
- Added `culvert.cfg` with `[culvert_runner] base_runid` and culvert run_group resolution in `get_wd()` (uses `CULVERTS_ROOT`); `CulvertsRunner` now copies the base run into each batch `_base`.
- Tests added in `tests/microservices/test_rq_engine_culverts.py`, `tests/microservices/test_rq_engine_jobinfo.py`, and `tests/culverts/test_culverts_runner.py`; run with `wctl run-pytest tests/microservices/test_rq_engine_culverts.py`, `wctl run-pytest tests/microservices/test_rq_engine_jobinfo.py`, and `wctl run-pytest tests/culverts/test_culverts_runner.py`.
- Verification (2025-01-05): `wctl run-pytest tests/culverts/test_culverts_runner.py tests/microservices/test_rq_engine_culverts.py` (pass).
- Dependency update: add `python-multipart==0.0.12` to `docker/requirements-uv.txt` and rebuild the weppcloud image so multipart parsing works in fresh containers.
- Model-parameters overrides now applied during run setup (`base_project_runid`, `nlcd_db`).

## Phase 3 - Per-culvert WEPP orchestration (COMPLETE)
- Scope: orchestrate delineation, landuse, soils, climate, and WEPP per culvert using existing run tasks; incorporate WhiteboxToolsTopazEmulator; use `symlink_channels_map` to avoid `build_channels`; apply model-parameters overrides; record per-run success/failure in `run_metadata.json`.
- Dependencies: Phase 2 scaffolding; availability of WBT, PRISM, soils datasets in container; confirmed model-parameters schema.
- Deliverables: RQ orchestration pipeline; per-run execution logs; per-culvert metadata record (timings, versions, config).
- Risks: long runtimes for 300 culverts; missing datasets for runs; error isolation (one culvert failure should not cancel entire batch).
- Verification: integration test with a tiny payload (1-2 culverts) using mocked heavy tasks; manual run with the `santee_mini_4culverts` payload in the container, confirming per-culvert outputs.

## Phase 3 handoff summary
- Orchestration updated in `wepppy/rq/culvert_rq.py` to create runs, load watershed features, and execute the per-culvert pipeline sequentially: `find_outlet` (watershed polygon), `build_subcatchments`, `abstract_watershed`, `build_landuse`, `build_soils`, `build_climate`, `run_wepp_hillslopes`, `run_wepp_watershed`.
- Per-culvert failures are isolated (caught/logged) and do not stop later runs; completion/retention timestamps are set only after all runs finish.
- `run_metadata.json` is written per run with `runid`, `point_id`, `culvert_batch_uuid`, `config`, `status`, `started_at`, `completed_at`, `duration_seconds`, optional `wepppy_version`, and `error` details when failed.
- `CulvertsRunner.load_watershed_features()` added to reuse Point_ID validation and construct `WatershedFeature` objects; stubs updated.
- Integration test added in `tests/culverts/test_culvert_orchestration.py` (monkeypatched heavy methods) to validate metadata creation, failure isolation, and `completed_at` set after processing.
- Verification: `wctl run-pytest tests/culverts/test_culvert_orchestration.py` (pass; warnings only).
- Manual run: `santee_mini_4culverts` payload completed end-to-end after fixes to WBT outlet access, shared topo generation (flovec/netful/chnjnt), and WBT symlink handling.
- BatchRunner WEPP post-processing now explicitly ensures hillslope interchange outputs, `totalwatsed3.parquet`, watershed interchange outputs, and query-engine activation when missing (mirrors `_build_hillslope_interchange_rq`, `_build_totalwatsed3_rq`, `_post_watershed_interchange_rq` behavior).
- Consolidated WEPP post-processing helpers into `wepppy/nodb/wepp_nodb_post_utils.py` (and `.pyi`) and refactored `wepppy/nodb/batch_runner.py` + `wepppy/rq/culvert_rq.py` to use the shared utilities.

## Phase 3b - Parallelized culvert/batch execution (RQ batch queue)
- Status: complete.
- Scope: enqueue one RQ job per culvert run (mirrors `batch_rq` pattern) so culvert batches execute in parallel without blocking interactive workloads; use a dedicated `rq-worker-batch` service and queue for both batch + culvert jobs.
- Dependencies: Phase 3 orchestration complete; RQ queue routing decisions; agreement on per-job runid format so logging attaches to `rq.log`.
- Deliverables:
  - New RQ queue (e.g., `batch`) for culvert + batch work; culvert orchestrator enqueues per-run jobs into this queue and uses a finalizer job with `depends_on`.
  - New `rq-worker-batch` service in dev/prod compose (4 workers) listening to `batch` only; increase `rq-worker` (default queue) to 6 workers for interactive traffic.
  - Concurrency clamps for batch workers:
    - Set `WEPPPY_NCPU=6` in the `rq-worker-batch` service (caps NCPU-driven pools in climate/watershed/etc).
- Risks: nested pools (ProcessPool + ThreadPool) inside a single culvert run can oversubscribe CPU if batch worker count is too high; misrouted jobs could starve interactive queues.
- Verification: enqueue a small payload (1–2 culverts) and confirm parallel job fan-out + finalizer; validate worker isolation by running an interactive job on the default queue while batch queue executes.

## Phase 3b handoff summary
- Status: complete.
- Routed culvert ingestion and batch fan-out to the `batch` RQ queue in `wepppy/microservices/rq_engine/culvert_routes.py` and `wepppy/rq/batch_rq.py`.
- Split culvert orchestration in `wepppy/rq/culvert_rq.py` into `run_culvert_batch_rq` (orchestrator), `run_culvert_run_rq` (per-run worker, runid first arg for `rq.log`), and `_final_culvert_batch_complete_rq` (finalizer); per-run jobs are enqueued in `Queue("batch")` with `depends_on` for the finalizer.
- Orchestrator records per-run job IDs in both `job.meta` and `CulvertsRunner._runs[run_id]["job_id"]`; finalizer reads per-run `run_metadata.json` to compute totals and writes `batch_summary.json` while updating `CulvertsRunner._completed_at` and `_retention_days`.
- `WEPPPY_NCPU` caps added for flowpath pools, soil prep, hillslope runs, fixed climate pools, and watershed interchange task fan-out in `wepppy/nodb/core/wepp.py`, `wepppy/nodb/core/climate.py`, and `wepppy/wepp/interchange/watershed_interchange.py` (no behavior change when unset).
- Stubs updated in `wepppy/rq/culvert_rq.pyi` and `stubs/wepppy/rq/culvert_rq.pyi`.
- Tests updated in `tests/culverts/test_culvert_orchestration.py` to call `run_culvert_run_rq` + finalizer; verification: `wctl run-pytest tests/culverts/test_culvert_orchestration.py tests/microservices/test_rq_engine_culverts.py` (pass; warnings only).

## Phase 3c - Per-run creation (batch_rq parity + parallel run setup)
- Status: complete.
- Scope: move culvert run creation into per-run RQ jobs to match the `batch_rq`/`BatchRunner.run_batch_project` pattern, avoiding a serial `create_runs()` step in the orchestrator.
- Dependencies: Phase 3b fan-out in place; `_base` creation is reliable; runid format and run_group metadata finalized.
- Deliverables:
  - `CulvertsRunner.create_run_if_missing()` (idempotent) that creates a single run directory, rewrites `.nodb` metadata, clears caches/locks, and symlinks DEM + topo rasters.
  - `run_culvert_batch_rq` updated to only compute `run_ids`, ensure `_base`, and enqueue per-run jobs + finalizer (no full `create_runs()`).
  - `run_culvert_run_rq` updated to call `create_run_if_missing()` before executing the per-run pipeline.
  - Optional: helper to load a single watershed feature by `Point_ID` to avoid re-parsing the full GeoJSON on every run.
- Risks: race conditions if multiple jobs attempt the same run_id; partial run directories if a job crashes mid-copy; repeated GeoJSON parsing overhead.
- Verification: run a small payload (1–2 culverts) and confirm per-run creation happens inside worker jobs; verify `_base` remains unchanged, per-run logs are scoped correctly, and reruns are idempotent.

## Phase 3c handoff summary
- Status: complete.
- Added `CulvertsRunner.create_run_if_missing()` to copy `_base` into `runs/<run_id>`, rewrite `.nodb` state (`wd`, `_run_group`, `_group_name`), clear Redis cache/locks, and symlink DEM + WBT topo rasters (`flovec`, `netful`, `relief`, `chnjnt`) in `wepppy/nodb/culverts_runner.py`.
- `run_culvert_batch_rq` now loads `run_ids`, ensures `_base`, and enqueues per-run jobs without serial `create_runs()`; per-run jobs create runs on demand in `wepppy/rq/culvert_rq.py`.
- `run_culvert_run_rq` now instantiates `CulvertsRunner` when missing and calls `create_run_if_missing()` before executing the pipeline, preserving run_group semantics (`culvert;;<batch_uuid>;;<run_id>`).
- Orchestrator still records job IDs in `CulvertsRunner._runs` while `create_run_if_missing()` preserves existing entries to avoid clobbering `job_id`.
- Stubs updated in `wepppy/nodb/culverts_runner.pyi` and `stubs/wepppy/nodb/culverts_runner.pyi`.
- Tests updated to assert per-run job creates the run directory and is idempotent; run with `wctl run-pytest tests/culverts/test_culvert_orchestration.py`.

## Phase 3e - Stream pruning + order reduction (culvert batches)
- Status: complete.
- Scope: add `order_reduction_passes` to `CulvertsRunner` and post-process `topo/netful.tif` once per batch before per-run jobs are enqueued: prune short streams (WBT `remove_short_streams`, `min_length = 2 * cellsize_m`), compute a Strahler order raster from the pruned stream mask, run `PruneStrahlerStreamOrder` `N` times (binary output on the final pass), then generate `chnjnt.tif` from the final `netful.tif`.
- Sanity check: applying the prune once at the batch root keeps the per-run symlink flow intact and avoids redundant work in each culvert job; overwriting `netful.tif` is acceptable because the payload is per-batch and isolated.
- Dependencies: `whitebox_tools` from the weppcloud fork (`/workdir/weppcloud-wbt`) must expose `StrahlerStreamOrder` and `PruneStrahlerStreamOrder` (with `--binary_output`); payload provides `topo/streams.tif`.
- Deliverables:
  - `CulvertsRunner.order_reduction_passes` NoDb property, read from `[culvert_runner] order_reduction_passes` (default `culvert.cfg` value; allow 0 to disable).
  - `run_culvert_batch_rq` prunes short streams (`remove_short_streams`), builds a Strahler order raster from the pruned stream mask, then prunes stream order (`PruneStrahlerStreamOrder`) with binary output on the final pass, then generates `topo/chnjnt.tif` from the final `topo/netful.tif` before enqueuing culvert runs.
  - Logs emitted showing pass count and inputs/outputs; failure raises early before jobs are enqueued.
- Risks: pruning changes the number of channels/hillslopes; ensure the weppcloud-wbt fork with `--binary_output` is deployed so downstream binary stream masks stay compatible with `polygonize_netful`.
- Verification: run `santee_mini_4culverts` with `order_reduction_passes=1` and compare hillslope counts/logs before/after; confirm pruned `netful.tif` is used in `dem/wbt/netful.tif` symlinks, `chnjnt.tif` is regenerated from the pruned netful raster, and the batch completes.

## Phase 3f - Stream coverage validation + per-run fallback
- Status: complete.
- Scope: ensure each run has stream pixels inside the watershed boundary before outlet detection. If the pruned `topo/netful.tif` has zero stream pixels within the watershed mask, fall back to the full `topo/streams.tif` for that run only and use the batch-generated `topo/chnjnt.streams.tif` so junctions align with the fallback stream map. Allow `Watershed.find_outlet()` to run with a pre-built `target_watershed.tif` (no feature argument) so culvert orchestration can reuse cached masks.
- Deliverables:
  - `CulvertsRunner` stream-source selection helper that rasterizes the watershed polygon into `dem/target_watershed.tif`, checks stream coverage, and selects either `netful.tif` + `chnjnt.tif` or `streams.tif` + `chnjnt.streams.tif`.
  - `run_culvert_batch_rq` generates `topo/chnjnt.streams.tif` once per batch (alongside `topo/chnjnt.tif`) for per-run symlinking.
  - `Watershed.find_outlet()` accepts an optional `WatershedFeature` and uses the cached `target_watershed.tif` when present.
  - Stubs/tests updated to cover the new optional signature and payload fixtures include `topo/streams.tif`.
- Risks: fallback stream maps can increase channel density for specific culverts; ensure junction maps always match the chosen stream raster.
- Verification: run a batch where a culvert polygon does not intersect pruned `netful.tif` and confirm the run uses `streams.tif` + `chnjnt.streams.tif` while other runs keep `netful.tif`.

## Phase 3g - LPT queue ordering (area proxy)
- Status: complete.
- Scope: compute per-feature area inside `WatershedFeature` (geodesic for lat/long, planar for projected CRS) and enqueue runs in descending area to reduce stragglers for large batches/culvert collections.
- Deliverables:
  - `WatershedFeature.area_m2` cached property with geodesic fallback for geographic CRS.
  - `run_culvert_batch_rq` orders `run_ids` by descending `area_m2`.
  - `run_batch_rq` orders watershed jobs by descending `area_m2` (LPT).
- Risks: area is a proxy for hillslopes/runtime; MultiPolygon holes/invalid geometries may skew ranking.
- Verification: confirmed enqueue order is largest → smallest in RQ metadata/logs for mixed-size payloads.

## Phase 4 - Artifact delivery and browse integration (COMPLETE)
- Scope: expose browse access for culvert + batch roots; skeletonize per-run folders after `run_metadata.json` is written; package the skeletonized runs into a batch artifact (`weppcloud_run_skeletons.zip`). Do not copy artifacts into a `culvert/` subfolder in this phase.
- Dependencies: Phase 3 outputs; browse service routing for `/weppcloud/culverts/` and `/weppcloud/batch/`; agreement on skeletonization allowlist + denylist; shared `skeletonize_run` helper in `wepppy/nodb`.
- Required per-run artifact (MVP, stored in run root):
  - `run_metadata.json` (written during Phase 3; not copied or renamed).
- Batch-level artifact (MVP):
  - `weppcloud_run_skeletons.zip` at `/culverts/<uuid>/weppcloud_run_skeletons.zip` containing the skeletonized `runs/` tree.
  - `runs_manifest.md` at `/culverts/<uuid>/runs_manifest.md` listing run IDs, watershed labels (when present), job metadata, and available counts. Job fields (`job_status`, `job_created`) are best-effort from the worker; they may show `-` if a worker fails before updating NoDb, and no finalizer backfill runs yet.
  - `culverts_runner.nodb` at `/culverts/<uuid>/culverts_runner.nodb` with batch summary and per-run metadata (includes `job_status`/`job_created` when available).
- Browse paths:
  - `/weppcloud/culverts/<uuid>/browse/` for batch root browsing (includes `runs/<id>/...`).
  - `/weppcloud/batch/<batch_name>/browse/` for BatchRunner outputs.
- Skeletonization (per run, run after `run_metadata.json` is written and before zipping):
  - Keep list (allowlist; remove everything else):
    - `*.log`
    - `climate.nodb`
    - `disturbed.nodb`
    - `landuse.nodb`
    - `nodb.version`
    - `soils.nodb`
    - `redisprep.dump`
    - `ron.nodb`
    - `run_metadata.json`
    - `unitizer.nodb`
    - `watershed.nodb`
    - `wepp.nodb`
    - `climate/`
    - `dem/wbt/*.geojson`
    - `disturbed/disturbed_land_soil_lookup.csv`
    - `landuse/landuse.parquet`
    - `soils/soils.parquet`
    - `watershed/channels.parquet`
    - `watershed/hillslopes.parquet`
    - `watershed/network.txt`
    - `watershed/structure.pkl`
    - `wepp/output/interchange/`
  - Exclude list (denylist; override allowlist):
    - `wepp/output/interchange/H.pass.parquet`
  - Note: `_logs/` directories are not retained; profile recorder logs are intentionally dropped.
- Failure representation:
  - Always write `run_metadata.json`; for failed runs it must include `status=failed` and the `error` block already written in Phase 3.
  - Do not create placeholder files in Phase 4.
- Deferred (post-MVP):
  - Artifact manifests that enumerate required outputs and mark missing files for failed runs.
  - Explicit `culvert/` packaging or copied outputs (if clients need a curated directory later).
- Deliverables: browse route support for `/weppcloud/culverts/` + `/weppcloud/batch/`; reusable `skeletonize_run` helper in `wepppy/nodb` + hook in `_process_culvert_run` (or equivalent); `weppcloud_run_skeletons.zip` batch artifact (MVP).
- Risks: browse service path mapping gaps; missing outputs for failed culverts; large artifact sizes; skeletonization removing debug inputs needed for re-runs.
- Verification: browse integration test that lists the batch root and `runs/` tree; confirm `run_metadata.json` is present in skeletonized runs; confirm `weppcloud_run_skeletons.zip` contains only the allowlist minus denylist; verify `runs_manifest.md` has one row per run.

## Phase 4 handoff summary
- Skeletonization: added reusable `skeletonize_run` (git clean allowlist/denylist) and invoked it after `run_metadata.json` is written; `_logs/` are intentionally dropped; `wepp/output/interchange/H.pass.parquet` is explicitly excluded.
- Batch artifacts: finalizer writes `batch_summary.json`, `runs_manifest.md` (Source + Batch Summary + runs table), and `weppcloud_run_skeletons.zip` (includes skeletonized `runs/`, `runs_manifest.md`, and `culverts_runner.nodb`).
- NoDb state: `culverts_runner.nodb` now carries per-run job metadata (`job_status`, `job_created`) plus a persisted batch summary.
- Browse/DTale/download/gdalinfo: added `/weppcloud/culverts/...` and `/weppcloud/batch/...` routes in browse, download, gdalinfo, and D-Tale services; Caddy routes updated to proxy these paths; path traversal checks hardened while allowing symlinked assets.
- Tests: added browse route tests and extended culvert orchestration test to validate manifest + NoDb summary.

## Phase 4b - Batch landuse/soils downscale (COMPLETE)
- Scope: for culvert batches, fetch NLCD + SSURGO once at 30m for the payload DEM extent, then downscale locally to the DEM grid (matches subwta); run this in `run_culvert_batch_rq` before enqueuing child jobs, store canonical rasters at the batch root, and symlink into runs.
- Shared batch outputs (kept outside `runs/`):
  - `landuse/nlcd_30m.tif`, `landuse/nlcd.tif`
  - `soils/ssurgo_30m.tif`, `soils/ssurgo.tif`
- Run behavior:
  - Require `landuse/nlcd.tif` + `soils/ssurgo.tif` to exist at the batch root, then symlink them before `Landuse.build()`/`Soils.build()`.
  - Call `Landuse.build(retrieve_nlcd=False)` and `Soils.build(retrieve_gridded_ssurgo=False)` to skip cleanup and remote retrieval.
- Assumptions: all runs in a culvert batch share the same DEM grid/extent; subwta grid matches the DEM grid.
- Notes: skeletonization removes run-local symlinks; canonical rasters live at the batch root.

## Phase 4b handoff summary
- Batch rasters: `landuse/nlcd_30m.tif`, `landuse/nlcd.tif`, `soils/ssurgo_30m.tif`, `soils/ssurgo.tif` generated once per batch from the payload DEM extent before jobs are queued and shared by runs.
- Per-run wiring: landuse/soils directories are cleaned, then symlinked to the batch rasters before `Landuse.build(retrieve_nlcd=False)` and `Soils.build(retrieve_gridded_ssurgo=False)`.
- Overrides: `model_parameters.nlcd_db` is respected to select the 30m sources; defaults fall back to the base project settings.
- Skeletonization: run-level symlinks are removed by skeletonization; batch rasters remain at the batch root.

## Phase 4c - Cropped VRT symlinks for large DEMs (COMPLETE)
- Scope: generate windowed VRTs (single SimpleSource + srcWin) for DEM + shared topo rasters using watershed feature bounds + pixel padding to reduce WBT/Peridot memory footprint.
- Touch points:
  - `wepppy/all_your_base/geo/vrt.py` centralizes VRT creation (`build_windowed_vrt`, `build_windowed_vrt_from_window`, CRS-aware bbox handling).
  - `Ron.symlink_dem` accepts `as_cropped_vrt` (default false) + `crop_window`, persists `_dem_is_vrt` + crop window metadata, and writes `dem.vrt` when cropping.
  - `Watershed.symlink_channels_map` uses the Ron crop window to build `flovec/netful/relief/chnjnt` VRTs and persists `_flovec_netful_relief_chnjnt_are_vrt`.
  - `Landuse.symlink_landuse_map` and `Soils.symlink_soils_map` accept `as_cropped_vrt` (default false), persist `_landuse_is_vrt`/`_soils_is_vrt`, and create `nlcd.vrt`/`ssurgo.vrt` when cropping.
  - `NoDbBase` no longer exposes `lc_dir`/`soils_dir`/`lc_fn`/`ssurgo_fn`; callers must use `Landuse`/`Soils` instances directly.
  - `WatershedFeature.get_padded_bbox` now requires an explicit `output_crs` to avoid ambiguous coordinate systems.
  - `CulvertsRunner` sources crop padding from `culvert.cfg` (`crop_pad_px`).
- Runtime behavior:
  - `Ron.dem_fn` composes `dem.vrt` vs `dem.tif` from `_dem_is_vrt`; VRT creation requires a crop window; call sites now resolve DEMs via Ron.
  - `WhiteboxToolsTopazEmulator` composes `relief/flovec/netful/chnjnt` paths from `_flovec_netful_relief_chnjnt_are_vrt`; WBT builds reset this flag to `.tif`.
  - `Landuse.lc_fn` and `Soils.ssurgo_fn` resolve `.vrt` vs `.tif` based on `_landuse_is_vrt`/`_soils_is_vrt`; retrieval workflows reset these flags to `.tif`.
  - `elevationquery` accepts `dem.vrt`; `_compute_ruggedness_from_dem` uses `ron.dem_fn`.
- Assumptions: culvert payloads are UTM; run raster grids are aligned so a shared crop window is valid across DEM/flovec/netful/relief/chnjnt.

## Phase 4c handoff summary
- VRT helper: `wepppy/all_your_base/geo/vrt.py` provides CRS-aware window computation and VRT creation (single SimpleSource + srcWin).
- DEM selection: `Ron` now persists `_dem_is_vrt` and owns `dem_fn`, eliminating file-system guessing in downstream modules.
- Channel raster selection: `Watershed` persists `_flovec_netful_relief_chnjnt_are_vrt` and keeps the WBT emulator in sync; VRTs use `.vrt` extensions for WBT compatibility.
- Landuse/soils selection: `Landuse`/`Soils` now persist `_landuse_is_vrt`/`_soils_is_vrt` and own `lc_fn`/`ssurgo_fn`; call sites use the instances directly (no `NoDbBase` helpers).
- Culvert config: `culvert.cfg` carries `crop_pad_px` for DEM/topo crop padding; culvert runs call the new VRT-enabled symlink methods.

## Phase 4e - wbt_abstract_watershed memory optimization (COMPLETE)
- Scope: reduce memory footprint of `wbt_abstract_watershed` (Peridot) to prevent memory-watchdog kills during parallel culvert batch processing; integrate `--skip-flowpaths` flag to eliminate unnecessary flowpath output generation.
- Problem: initial Hubbard Brook batch (7 watersheds) with 4 concurrent workers peaked at 101GB used / 24GB available, triggering the memory-watchdog kill threshold (25GB available). Per-process memory was 15-21GB each.
- Dependencies: optimized Peridot binary with reduced raster footprint and `--skip-flowpaths` CLI flag.

### Peridot optimizations (Rust binary)
- Raster footprint reduced: `f32` for relief/fvslop/taspec (was `f64`).
- `flovec` uses `u8` with in-place remap (was `i8` with separate allocation).
- Precomputed `indices_map` avoids redundant cell iteration.
- `--skip-flowpaths` flag skips `flowpaths.csv` and `slope_files/flowpaths/` output (not needed for culvert runs).

### Code changes
- Binary: copied optimized `wbt_abstract_watershed` to `wepppy/topo/peridot/bin/`.
- `wepppy/topo/peridot/peridot_runner.py`: added `skip_flowpaths` parameter to `run_peridot_wbt_abstract_watershed()`; updated `post_abstract_watershed()` to handle missing `flowpaths.csv`.
- `wepppy/nodb/core/watershed.py`: added `skip_flowpaths` property with getter/setter; passed to runner in `abstract_watershed()`.
- `wepppy/rq/culvert_rq.py`: set `watershed.skip_flowpaths = True` before `abstract_watershed()` for batch processing.

### Validation metrics (Hubbard Brook batch, 7 watersheds)
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Peak memory used | 101GB | 51GB | -50% |
| Memory available | 24GB | 73-82GB | +200% |
| Per-process (large watershed) | 15-21GB | 7-10GB | -50% |
| Per-process (small watershed) | 8-12GB | 3-5GB | -60% |
| Watchdog kills | 1 | 0 | eliminated |

### Per-run memory profile (from `_peridot.log`)
| Run | Raster Cells | Hillslopes | Memory (optimized) |
|-----|-------------|------------|-------------------|
| 200 | 3.98M | 87 | ~10GB |
| 174 | 3.31M | 78 | ~7GB |
| 59 | 4.18M | 78 | ~10GB |
| 184 | 3.55M | 78 | ~7GB |
| 210 | 1.51M | 43 | ~3GB |
| 1 | 1.64M | 28 | ~3GB |

### Memory-heavy phases (from log analysis)
1. **Raster loading**: ~50-70MB combined for subwta/relief/flovec/fvslop/taspec per run.
2. **Indices map construction**: ~5-18MB depending on hillslope count.
3. **Hillslope abstraction**: dominant memory consumer; scales with cell count × hillslope count; produces flowpath indices arrays (~15-17MB for large watersheds).

### Notes
- Memory pressure depends on concurrent process overlap, not individual watershed size; 4 large watersheds overlapping caused peak usage.
- `--skip-flowpaths` eliminates flowpath CSV/slope file I/O overhead but primary savings come from reduced raster footprint.
- Memory watchdog thresholds: warn at 30GB available, kill at 25GB available (`/home/workdir/wepppy/scripts/memory-watchdog.sh`).

## Phase 4f - Per-run stream junction generation + job staggering (COMPLETE)
- Scope: optimize per-run stream junction (chnjnt.tif) generation and reduce VRT file contention during parallel batch processing.
- Problem: culvert runs use VRT files that reference shared source TIFs; when multiple workers start simultaneously, file contention can cause transient failures.

### Stream junction generation
- **Original approach**: clip `netful.vrt` → `netful.masked.tif` using `target_watershed.tif` (not `bound.tif`), then run `stream_junction_identifier(flovec, netful.masked.tif)` → `chnjnt.tif`.
- **Attempted optimization**: clip pre-computed `chnjnt.vrt` directly to watershed mask → `chnjnt.tif` (skip `stream_junction_identifier`).
- **Result**: optimization failed—stream junctions must be recalculated for the masked stream network because junction topology changes at watershed boundaries.
- **Final implementation**: kept original approach with `_generate_masked_stream_junctions()` in `wepppy/rq/culvert_rq.py` (mask source is `target_watershed.tif`, not `bound.tif`):
  1. Clip `netful.vrt` to `target_watershed.tif` mask → `netful.masked.tif`
  2. Run `wbt.stream_junction_identifier(d8_pntr=flovec.vrt, streams=netful.masked.tif)` → `chnjnt.tif`

### Job staggering for VRT contention
- **Problem**: transient "bound file was not created" failures when multiple workers read the same source TIF through VRT references simultaneously.
- **Solution**: added 1-second delay between job submissions in `run_culvert_batch_rq()` to stagger worker starts.
- **Code change**: `time.sleep(1)` after each `q.enqueue_call()` in `wepppy/rq/culvert_rq.py`.

### Notes
- `chnjnt.vrt` is created per-run as a cropped view of the batch's `topo/chnjnt.tif`, but it cannot be used directly because masking to the watershed boundary changes which stream segments exist, which changes junction locations.
- The 1s delay adds ~N seconds to batch submission time (where N = number of runs) but prevents file contention failures.
- Use `bound.tif` for masking (not `target_watershed.tif`): clipping channels to the target watershed can misidentify headwater pixels and cause mismatch with `netw0.tif`.

## Phase 4g - Representative flowpath optimization (COMPLETE)
- Status: complete.
- Scope: replace the O(pixels) per-hillslope flowpath walking in `wbt_abstract_watershed` with a single representative flowpath per hillslope, dramatically reducing abstraction time for 1.0m DEM culvert batches.
- Problem: `wbt_abstract_watershed` was the bottleneck for high-resolution (1.0m) culvert batches. Run 184 (78 hillslopes, 3.5M cells) took **4409 seconds** (~73 minutes) for abstraction alone, walking 2.4M flowpath indices.

### Peridot optimizations (Rust binary)
- New `--representative-flowpath` flag for `wbt_abstract_watershed` (WBT-only).
- Forces `--skip-flowpaths` when enabled (no flowpaths.csv or slope_files/flowpaths output).
- Loads `dem/wbt/discha.tif` (distance-to-channel raster) to select seed cells.
- Seed selection: picks a median-distance source cell (no upstream neighbor per D8) with deterministic tie-breaks (higher relief, then row-major).
- Walks one downstream flowpath to the channel with a fallback candidate sweep.
- Builds hillslope summary from that single path while preserving existing length/width logic (source hillslopes use path length; left/right use channel length for width and area/width for length).
- Deprecated `get_edge_flowpaths` in favor of faster `get_edge_flowpaths2` (O(N) per hillslope mask vs. O(F^2 * L)).

### Code changes
- Binary: updated `wbt_abstract_watershed` in `wepppy/topo/peridot/bin/`.
- `wepppy/topo/peridot/peridot_runner.py`: added `representative_flowpath` parameter to `run_peridot_wbt_abstract_watershed()`.
- `wepppy/nodb/core/watershed.py`: added `representative_flowpath` property with getter/setter; passed to runner in `abstract_watershed()`.
- `wepppy/rq/culvert_rq.py`: set `watershed.representative_flowpath = True` before `abstract_watershed()` for batch processing.

### Performance comparison (Run 184: 78 hillslopes, 3.5M cells)

| Metric | Before (full flowpath) | After (representative) | Improvement |
|--------|------------------------|------------------------|-------------|
| **Abstraction time** | 4409.51s (~73 min) | 0.17s | **25,938x faster** |
| Indices walked | 2,374,966 | 3,740 | 635x fewer |
| Points output | 27,405 | 3,740 | 7.3x fewer |
| Memory (flowpaths) | ~19.16 MiB | ~0.17 MiB | 113x less |
| **Total run time** | 4711.5s (~78 min) | 292.5s (~4.9 min) | **16x faster** |

### Batch-level performance (Hubbard Brook, 40 culverts)

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Status | Failed (all runs) | Success (all runs) | Fixed |
| Avg run duration | N/A (failed at ~2.6h) | 110.8s | Viable |
| Min run | N/A | 43.5s | - |
| Max run | N/A | 322.4s | - |

### Hillslope geometry comparison (Run 184: 78 hillslopes)

| Metric | Old (full flowpath) | New (representative) | Difference |
|--------|---------------------|----------------------|------------|
| Mean length | 121.8m | 88.0m | -33.8m (-10.7%) |
| Min length | 1.8m | 1.0m | - |
| Max length | 626.4m | 909.0m | - |
| Correlation | - | - | 0.55 |

Note: Representative flowpath mode produces different hillslope geometries because it walks a single flowpath per hillslope rather than aggregating all flowpaths. Large differences occur for hillslopes where the representative path is much shorter/longer than the weighted average of all paths.

### WEPP output comparison (Run 184)

| Metric | Old | New | Diff (%) |
|--------|-----|-----|----------|
| Contributing area (ha) | 237.94 | 237.89 | -0.0% |
| Avg. Ann. Precipitation (m³) | 3,650,763 | 3,649,976 | -0.0% |
| Avg. Ann. Water discharge (m³) | 2,164,516 | 2,167,289 | +0.1% |
| **Avg. Ann. Hillslope soil loss (t)** | 2.70 | 1.40 | **-48.1%** |
| Avg. Ann. Channel soil loss (t) | 67.20 | 67.10 | -0.1% |
| Avg. Ann. Sediment discharge (t) | 19.00 | 17.80 | -6.3% |
| Sediment Delivery Ratio | 0.271 | 0.261 | -3.7% |

Key observation: Hillslope soil loss is **48% lower** with representative flowpath mode. This is expected because representative flowpaths tend to be shorter on average, and soil loss is sensitive to hillslope length. Channel processes remain nearly identical since channel geometry is unchanged. The watershed-level sediment discharge difference (6.3%) is much smaller than the hillslope-level difference due to the dominance of channel erosion in this watershed.

### Known limitations
- `discha.tif` fallback: many hillslopes show "no discha candidates" warnings, falling back to first pixel index instead of median distance selection. This affects seed quality but doesn't break the abstraction. Future work: investigate discha raster generation to ensure valid values within hillslope boundaries.
- This mode is WBT-only and intentionally diverges from TOPAZ behavior.
- Hillslope lengths can differ significantly from full-flowpath mode; this affects soil loss predictions but provides acceptable approximations for culvert risk screening.
- WBT junction detection limitation: small or simple watersheds with minimal stream networks may fail during subcatchment delineation with "Current cell is not recognized as a junction" (WhiteboxAppError). This occurs when the outlet cell doesn't land on a recognized stream junction in WBT's `stream_link_identifier` topology. This is a preexisting WBT limitation, not specific to representative flowpath mode.

### Verification
- Manual batch: Hubbard Brook payload (40 culverts, 1.0m DEM) completed successfully with 100% success rate.
- Peridot logs confirm representative flowpath mode active and abstraction completing in sub-second times.

## Phase 4h - Minimal stream seeding for edge-case watersheds (COMPLETE)
- Status: complete.
- Scope: handle watersheds where `find_outlet` candidates fall outside the watershed mask by extending the mask and seeding a minimal stream/junction.
- Problem: WBT `find_outlet` reports candidate row/col at the VRT edge for culvert watersheds where the flow path exits the raster outside the polygon mask.

### Root cause analysis
- `find_outlet` returns candidates on the raster edge that are outside `target_watershed.tif`, so the tool never sees a stream cell inside the mask.
- Walking upstream from the candidate is ambiguous because multiple cells can drain into the same downstream pixel, so the fix uses the candidate location directly.

### Solution: extend watershed mask + seed outlet
1. Parse `find_outlet` error candidates; only proceed if all candidates converge.
2. Ensure `dem/target_watershed.tif` exists (rebuild from the watershed feature if missing).
3. Extend the watershed mask to include the candidate pixel.
4. Seed `netful` at the candidate (plus upstream neighbor when available) and ensure `chnjnt` contains a junction at the outlet.
5. Retry `find_outlet` with the cached mask.

### Code changes
- `wepppy/rq/culvert_rq.py`:
  - Added `_extend_watershed_mask_to_candidate()`
  - `find_outlet` fallback now rebuilds the mask if missing, extends the mask to include the candidate, seeds `netful`/`chnjnt`, and retries `find_outlet`
  - Uses `_parse_outlet_candidates_from_error()`, `_seed_outlet_pixel()`, `_ensure_outlet_junction()`
- `wepppy/nodb/core/watershed.py`:
  - Minimal structure handling when `network.txt` is missing (1 hillslope, 1 channel)
- `wepppy/nodb/core/wepp.py`:
  - Minimal `pw0.str` generation for 1 hillslope/1 channel

### Test payload
- `tests/culverts/test_payloads/Hubbard_Brook_subset_11/payload.zip` (11 edge-case watersheds)

### Results
- Batch UUID: `ceed1b38-1ef4-4c19-83d8-7edd625c1d6c`
- Summary (pre-fix batch): total 11, succeeded 9, failed 2, skipped_no_outlet 0
- Resolved: Point_ID 9 `ZeroDivisionError` fixed by guarding disturbed soil `pct_coverage` when `total_area <= 0.0`; run 9 now completes.
- Remaining failure: Point_ID 207 WBT junction error ("Current cell is not recognized as a junction")

### Remaining work
- [x] Point_ID 207 follow-up: the issue was malformed inputs (culvert point outside watershed), not WBT. Added a guard that validates point-in-watershed and raises `NoOutletFoundError` early.

## Phase 5 - Observability, error handling, retention (COMPLETE)
- Status: complete; remaining work moved to Phase 6a and cleanup follow-ups.
- Scope: run-level validation + error propagation, structured error codes for validation/execution, publish status events to Redis DB 2, update RQ job info with `error_code`/`error_detail`, add validation metrics, and implement cleanup/retention policy in `/wc1/culverts/` (delete 7 days after job completion, with completion time stored in `CulvertsRunner` state).
- Dependencies: Phase 1 RQ job framework; ops decision on retention window.
- Deliverables:
  - Culvert point-in-watershed validation (`WatershedFeature.contains_point`) before modeling; supports `culvert_runner.contains_point_buffer_m` (meters) to tolerate small alignment offsets; failures recorded as `CulvertPointOutsideWatershedError`.
  - Run-level errors from `run_metadata.json` merged into `culverts_runner.nodb` + `runs_manifest.md`.
  - Finalizer computes validation metrics (culvert/outlet coords, distance, target area, bounds area) and stores them in `culverts_runner.nodb` + `runs_manifest.md`.
  - NoDb contention retry for `CulvertsRunner` writes when batch workers overlap.
  - Retry/backoff for flaky `bound.tif` creation (WBT watershed step) to reduce VRT -> TIF contention failures.
  - Batch-scoped logging: `culvert_rq` logger now routes into the `CulvertsRunner` file handler under the batch UUID.
  - Outlet seeding log includes D8 neighbor mask sum from `target_watershed.tif` for diagnostics.
  - Remaining: status event payloads, cleanup job (cron or RQ) that reads `CulvertsRunner.completed_at` + retention window, run/batch log summaries.
- Risks: retention job deleting active batches; missing completion timestamp on failed jobs; missing error propagation in RQ engine.
- Verification: Hubbard Brook edge-case payload confirms outside-watershed failures appear in `run_metadata.json`, `culverts_runner.nodb`, and `runs_manifest.md`; run-level metrics populated when outputs exist.

## Phase 5a - Minimum watershed area filtering (COMPLETE)
- Scope: filter micro-watersheds using `culvert_runner.minimum_watershed_area_m2` (configured in `culvert.cfg`) when the watershed GeoJSON provides `area_sqm`; reject runs below the threshold with a structured validation error.
- Deliverables:
  - `CulvertsRunner.minimum_watershed_area_m2` config hook.
  - Run-level guard after point-in-watershed validation and after `target_watershed_path` creation (NoOutletFoundError fallback path).
  - Failure surfaced as `WatershedAreaBelowMinimumError` in `run_metadata.json`, `culverts_runner.nodb`, and `runs_manifest.md`.
- Risks: inconsistent `area_sqm` values in payloads; missing `area_sqm` means no filtering (intentional).
- Verification: Hubbard Brook payload analysis shows 100 m^2 threshold eliminates micro-watersheds without blocking valid small catchments.

## Phase 5b - Watershed simplification issue documentation (COMPLETE)
- Scope: Document critical issue where Culvert_web_app's 1.0m watershed simplification causes weppcloud to skip culverts.
- Problem: weppcloud validates that each culvert's pour point is inside its associated watershed polygon. Simplified watersheds often fail this check.

### Impact analysis (Hubbard Brook dataset)
| Metric | Unsimplified | Simplified (1.0m) |
|--------|-------------:|------------------:|
| Pour points inside watershed | 208 / 210 | **116 / 210** |
| Culverts skipped by weppcloud | 2 | **94** |

**45% of culverts will be skipped** due to simplification moving polygon boundaries.

### Vertex reduction from simplification
| Point_ID | Unsimplified | Simplified | Ratio |
|---------:|-------------:|-----------:|------:|
| 130 | 3,958 | 62 | 64x |
| 162 | 5,608 | 49 | 114x |
| 112 | 1,575 | 5 | 315x |

### Culvert_web_app deleted resources
The following files are created but deleted after processing:
1. **`ws_raster_UTM.tif`** - Watershed raster (cell values = pour point FID)
2. **`ws_polygon_UTM.shp`** - Unsimplified polygons before simplification

Source code location: `subroutine_nested_watershed_delineation.py`:
```python
# Line ~1198: Creates unsimplified polygons (temporary)
wbt.raster_to_vector_polygons(i=output_watershed_raster_path, output=watershed_polygon_path)

# Line ~1213: Simplifies with 1.0m tolerance BEFORE saving
watershed_poly_gdf_merged = simplify_geometry(watershed_poly_gdf_merged, tolerance=1.0)
```

### Recommended fix for Culvert_web_app
```python
# Preserve unsimplified polygons before calling simplify_geometry():
ws_polygon_unsimplified_path = os.path.join(user_output_WS_deln_path, "ws_polygon_unsimplified_UTM.shp")
watershed_poly_gdf_merged.to_file(ws_polygon_unsimplified_path)

# Then apply simplification for the standard output
watershed_poly_gdf_merged = simplify_geometry(watershed_poly_gdf_merged, tolerance=1.0)
```

### Deliverables
- Updated `docs/culvert-at-risk-integration/dev-package/README.md` with "CRITICAL: Watershed Simplification Issue" section.
- `build_payload.py` uses simplified watersheds as-is (no reconstruction attempted).
- Culvert_web_app team informed: to run all culverts, provide unsimplified `watersheds.geojson`.

## Phase 5c - Stream network scaling (COMPLETE)
- Context: `flow_accum_threshold` in Culvert_web_app is cell-count based (default 100). For high-resolution DEMs (1.0m), that yields a much denser stream network than a 9–10m DEM using the same threshold, exploding hillslopes and runtime.
- Baseline reference: weppcloud assumes `flow_accum_threshold=100` plus one stream-order reduction pass, but the real calibration target is the 30m DEM workflow where channel initiation is driven by critical source area (typically 5–10 ha).
- Scaling guidance:
  - Target area: `A_target_m2 = flow_accum_threshold * (cellsize_m^2)`
  - If re-running `extract_streams` to match the 30m/100-cell baseline (~90,000 m²), reasonable targets are:
    - 10m DEM: `flow_accum_threshold ≈ 900`
    - 1m DEM: `flow_accum_threshold ≈ 90,000`
  - Order-reduction mapping (when `culvert_runner.order_reduction_mode = "map"`):
    - Compute an effective cellsize: `cellsize_m * sqrt(flow_accum_threshold / 100)` (default `flow_accum_threshold=100` when missing).
    - <= 1m → 3 passes; <= 4m → 2 passes; <= 10m → 1 pass (default for coarser DEMs)
- Mitigations available today:
  - Re-run `extract_streams` in Culvert_web_app with a scaled threshold (best fidelity).
  - Adjust `culvert_runner.order_reduction_passes` as a heuristic simplifier when re-running streams is not feasible (less direct than thresholding).
- Current action: test `order_reduction_passes` values (start with 2, then 3) on 1.0m DEM batches to measure hillslope and runtime reduction.
- Deliverables:
  - Document target-area scaling approach and recommended thresholds by DEM resolution.
  - Decide whether to re-run stream extraction for high-resolution projects or rely on order-reduction passes.

## Phase 5d - Native CRS retrieval for landuse/soils + wepppyo3 nodata guard (COMPLETE)
- Scope: avoid WGS84 round-trip clipping by requesting NLCD/SSURGO with native UTM extents; extend wmesque2 + client to accept native CRS bounding boxes; guard `identify_mode_single_raster_key` against 100% nodata hillslopes.

### Problem analysis (batch `55b28bb9-2d61-43f3-9f45-10779e93c501`, run 7)
- Run 7 failed with `KeyError: '1441'` in `wepp.run_hillslopes()` when looking up landcover.
- Root cause: 6 hillslopes (1441, 1541, 1592, 1601, 1602, 1603) had 100% nodata in the NLCD raster.
- NLCD retrieval used WGS84 bbox which, when transformed back to UTM, produced a smaller extent than the DEM:
  - DEM extent: 261900–273608 (11.7km width)
  - NLCD 30m extent: 262478–273068 (10.6km width, ~1km missing on edges)
- `identify_mode_single_raster_key` (wepppyo3) correctly skipped hillslopes with all-nodata pixels, but downstream code expected all hillslope IDs to be present in `domlc_d`.

### Deliverables
1. **wmesque2 native CRS support** (complete):
   - wmesque2 accepts optional `bbox_crs` (EPSG/proj4) for projected extent requests.
   - wmesque client (`wmesque_retrieve`) accepts `extent_crs` parameter, appends `bbox_crs` for v2 only.
   - Culvert batch landuse/soils retrieval uses native UTM extent to avoid WGS84 round-trip clipping.

2. **wepppyo3 nodata guard** (complete; updated wepppyo3 mounted in container):
   - `identify_mode_single_raster_key` and `identify_mode_intersecting_raster_keys` must return entries for all keys in the key raster.
   - When a hillslope has 100% nodata in the parameter raster, return the nodata value (or a sentinel) instead of silently skipping.
   - Test fixture created: `/workdir/wepppyo3/tests/raster_characteristics/fixtures/` with `subwta_nodata_edge.tif` (4 hillslopes) and `nlcd_nodata_edge.tif` (68% nodata coverage).

### Test fixture details
- Source: cropped from batch `55b28bb9-2d61-43f3-9f45-10779e93c501` run 7
- `subwta_nodata_edge.tif`: 500x200 px, hillslopes [1312, 1323, 1442, 1443], channel [1444]
- `nlcd_nodata_edge.tif`: 500x200 px, 32% valid / 68% nodata (right edge nodata)
- Expected: all 4 hillslopes must appear in `identify_mode_single_raster_key` result; 1442/1443 may have nodata as value

### Risks
- Incorrect CRS strings or non-projected CRS inputs to wmesque2.
- Downstream code must handle nodata values returned for hillslopes with no valid landcover data.

### Verification
- wepppyo3 test using fixture confirms all keys are returned.
- Run 7 retry succeeds after wmesque2 native CRS fix is deployed.

## Phase 5 handoff summary
- Validation now checks culvert points against watershed polygons; outside points fail fast with `CulvertPointOutsideWatershedError`.
- Minimum watershed area filter rejects micro-watersheds when `area_sqm` is present, using `WatershedAreaBelowMinimumError`.
- Finalizer merges `run_metadata.json` status/errors into `culverts_runner.nodb` and `runs_manifest.md` for consistent reporting.
- Runs manifest includes validation metrics and culvert/outlet distance for downstream QA.
- NoDb contention retry pattern applied to `CulvertsRunner` updates in batch jobs.

## Phase 6 - Auth and webhook enhancements (post-POC)
- Scope: JWT issuance/rotation, webhook registration + retries, HMAC signing, opt-in callbacks on completion/failure.
- Dependencies: security decisions on token lifecycle; agreement on webhook payload schema.
- Deliverables: auth middleware, webhook dispatcher, docs for Culvert_web_app.
- Risks: callback storms for large batches; secrets management; backward compatibility with POC auth.
- Verification: auth enforcement tests; webhook retry tests with mock endpoints; manual validation with Culvert_web_app dev instance.

## Phase 6a - Error schema standardization (COMPLETE)
- Scope: standardize `success`/`error` payloads across rq-engine routes and add `error_code`/`error_detail` to job status/job info outputs.
- Dependencies: agreement on error taxonomy and client expectations for job status polling.
- Deliverables: updated response helpers, job status payload extensions, updated spec/dev-package docs.
- Risks: client-side parsing changes; backward compatibility for existing integrations.
- Verification: regression tests for error responses and job status schema; manual checks against culvert payload uploads.

## Phase 6b - Payload naming + ws_deln metadata alignment (READY FOR REVIEW)
- Scope: rename the DEM payload path to `topo/breached_filled_DEM_UTM.tif` (no misleading "hydro-enforced" filename) and capture `hydroEnforcementSelect` as `hydro_enforcement_select` in `metadata.json`.
- Dependencies: Culvert_web_app form values and `user_ws_deln_responses.txt` output; payload builder updates in the dev package.
- Deliverables:
  - Payload validator + runner use the new DEM filename.
  - `build_payload.py` copies the DEM to `topo/breached_filled_DEM_UTM.tif` and emits `hydro_enforcement_select` in `metadata.json`.
  - Docs/specs updated to reference the new DEM filename and metadata field.
- Compatibility: this is a breaking rename as we move from dev to production; older payloads using `topo/hydro-enforced-dem.tif` are intentionally unsupported and must be reexported.
- Risks: culvert docs drifting out of sync.
- Verification: update culvert tests/fixtures to use `topo/breached_filled_DEM_UTM.tif`; validate a real payload from `/wc1/culvert_app_instance_dir/user_data/`.

## Cross-phase test strategy (minimum)
**Implemented tests**
- `tests/microservices/test_rq_engine_culverts.py` (rq-engine culvert ingestion).
- `tests/microservices/test_rq_engine_jobinfo.py` (rq-engine jobinfo).
- `tests/culverts/test_culverts_runner.py` (run scaffolding + symlinks).
- `tests/culverts/test_culvert_orchestration.py` (per-culvert orchestration + metadata).
- Payload fixtures: `tests/culverts/test_payloads/`.

**Planned tests**
- Unit: `Ron.symlink_dem()`, culvert ID mapping, error formatting.
- Integration: per-culvert orchestration, browse URLs, RQ job status.
- Smoke/manual: real payloads from `/workdir/culvert_app_instance_dir/user_data/` in container; verify outputs and download.

## Open questions / blockers
- Idempotency/retry rules for duplicate POSTs (keying on payload hash? caller-supplied id?).
- Retention/cleanup window and ownership of `/wc1/culverts/` storage.
- Concurrency/timeouts for 300-culvert batches and RQ worker sizing.
