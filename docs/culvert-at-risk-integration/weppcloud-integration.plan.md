# weppcloud integration plan for Culvert_web_app
> Implementation plan based on docs/culvert-at-risk-integration/weppcloud-integration.spec.md

## Guiding requirements (spec highlights)
- Endpoint: `POST /rq-engine/api/culverts-wepp-batch/` (multipart, FastAPI rq-engine to avoid 30s Caddy timeout; extend timeout there as needed).
- Storage: `/wc1/culverts/<culvert_batch_uuid>/` with per-culvert runs under `/runs/<Point_ID>/` and `_base/` seeded from `culvert.cfg`.
- Payload ZIP: `topo/hydro-enforced-dem.tif` + `topo/streams.tif` + `culverts/culvert_points.geojson` + `culverts/watersheds.geojson` + `metadata.json` + `model-parameters.json`; all inputs in the same projected CRS (meters).
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
- Scope: implement `/rq-engine/api/culverts-wepp-batch/` in rq-engine (FastAPI); accept multipart upload, mint `culvert_batch_uuid`, validate payload inline (payload_validator), extract payload, enqueue RQ job, return `{job_id, culvert_batch_uuid, status_url}`. This keeps validation inside the ingestion path and avoids the 30s Caddy timeout applied to weppcloud routes. Long term, migrate `/rq/api/*` to `/rq-engine/api/*`.
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
- Scope: add `order_reduction_passes` to `CulvertsRunner` and post-process `topo/netful.tif` once per batch before per-run jobs are enqueued: prune short streams (WBT `remove_short_streams`, using `watershed.wbt.mcl`), compute a Strahler order raster from the pruned stream mask, run `PruneStrahlerStreamOrder` `N` times (binary output on the final pass), then generate `chnjnt.tif` from the final `netful.tif`.
- Sanity check: applying the prune once at the batch root keeps the per-run symlink flow intact and avoids redundant work in each culvert job; overwriting `netful.tif` is acceptable because the payload is per-batch and isolated.
- Dependencies: `whitebox_tools` from the weppcloud fork (`/workdir/weppcloud-wbt`) must expose `StrahlerStreamOrder` and `PruneStrahlerStreamOrder` (with `--binary_output`); payload provides `topo/streams.tif`.
- Deliverables:
  - `CulvertsRunner.order_reduction_passes` NoDb property, read from `[culvert_runner] order_reduction_passes` (default 1; allow 0 to disable).
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
- Overrides: `model_parameters.nlcd_db` and `model_parameters.ssurgo_db` are respected to select the 30m sources; defaults fall back to the base project settings.
- Skeletonization: run-level symlinks are removed by skeletonization; batch rasters remain at the batch root.

## Phase 4c - Cropped VRT symlinks for large DEMs (IN PROGRESS)
- Scope: generate windowed VRTs (single SimpleSource + srcWin) for DEM + shared topo rasters using watershed feature bounds + pixel padding to reduce WBT/Peridot memory footprint.
- Touch points:
  - `wepppy/all_your_base/geo/vrt.py` centralizes VRT creation (`build_windowed_vrt`, `build_windowed_vrt_from_window`, CRS-aware bbox handling).
  - `Ron.symlink_dem` accepts `as_cropped_vrt` (default true), persists `_dem_is_vrt` + crop window metadata, and writes `dem.vrt` when cropping.
  - `Watershed.symlink_channels_map` uses the Ron crop window to build `flovec/netful/relief/chnjnt` VRTs and persists `_flovec_netful_relief_chnjnt_are_vrt`.
  - `WatershedFeature.get_padded_bbox` now requires an explicit `output_crs` to avoid ambiguous coordinate systems.
  - `CulvertsRunner` sources crop padding from `culvert.cfg` (`crop_pad_px`).
- Runtime behavior:
  - `Ron.dem_fn` composes `dem.vrt` vs `dem.tif` from `_dem_is_vrt`; call sites now resolve DEMs via Ron.
  - `WhiteboxToolsTopazEmulator` composes `relief/flovec/netful/chnjnt` paths from `_flovec_netful_relief_chnjnt_are_vrt`; WBT builds reset this flag to `.tif`.
  - `elevationquery` accepts `dem.vrt`; `_compute_ruggedness_from_dem` uses `ron.dem_fn`.
- Assumptions: culvert payloads are UTM; run raster grids are aligned so a shared crop window is valid across DEM/flovec/netful/relief/chnjnt.

## Phase 4c handoff summary
- VRT helper: `wepppy/all_your_base/geo/vrt.py` provides CRS-aware window computation and VRT creation (single SimpleSource + srcWin).
- DEM selection: `Ron` now persists `_dem_is_vrt` and owns `dem_fn`, eliminating file-system guessing in downstream modules.
- Channel raster selection: `Watershed` persists `_flovec_netful_relief_chnjnt_are_vrt` and keeps the WBT emulator in sync; VRTs use `.vrt` extensions for WBT compatibility.
- Culvert config: `culvert.cfg` carries `crop_pad_px` for DEM/topo crop padding; culvert runs call the new VRT-enabled symlink methods.

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
