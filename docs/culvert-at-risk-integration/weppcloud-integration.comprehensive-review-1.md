# Culvert-at-Risk Integration Comprehensive Review (v1)

## Documentation Consistency
- Plan schema omits `ssurgo_db` and `flow_accum_threshold` even though the spec and builder include them, so plan guidance is out of sync with current contract. (spec: `docs/culvert-at-risk-integration/weppcloud-integration.spec.md:178`, plan: `docs/culvert-at-risk-integration/weppcloud-integration.plan.md:37`, builder: `docs/culvert-at-risk-integration/dev-package/scripts/build_payload.py:701`)
- Scripts README examples use `schema_version: "1.0"` and `source.project_name`, which contradicts the spec/validator (`culvert-*-v1`, `source.project_id`) and will fail validation as written. (scripts README: `docs/culvert-at-risk-integration/dev-package/scripts/README.md:110`, spec: `docs/culvert-at-risk-integration/weppcloud-integration.spec.md:163`, validator: `wepppy/microservices/culvert_payload_validator.py:12`)
- Scripts README lists `Pour_Point_UTM.shp` for culvert points, but dev-package README and the builder use RSCS-snapped pour points (`pour_points_snapped_to_RSCS_UTM.shp`). (scripts README: `docs/culvert-at-risk-integration/dev-package/scripts/README.md:61`, dev-package README: `docs/culvert-at-risk-integration/dev-package/README.md:31`, builder: `docs/culvert-at-risk-integration/dev-package/scripts/build_payload.py:544`)
- Short-stream pruning is documented as using `watershed.wbt.mcl` but implementation uses `min_length = 2 * cellsize`; the pruning semantics differ from the plan/spec. (spec: `docs/culvert-at-risk-integration/weppcloud-integration.spec.md:236`, plan: `docs/culvert-at-risk-integration/weppcloud-integration.plan.md:135`, code: `wepppy/rq/culvert_rq.py:157`)
- Plan status blocks are internally inconsistent (sections marked COMPLETE but labeled “Status: in progress”). (plan: `docs/culvert-at-risk-integration/weppcloud-integration.plan.md:443`, `docs/culvert-at-risk-integration/weppcloud-integration.plan.md:535`)
- Plan calls out `order_reduction_passes` default 1, but `culvert.cfg` defaults to 3, and map-mode logic can ignore the configured default; docs should clarify intended defaults. (plan: `docs/culvert-at-risk-integration/weppcloud-integration.plan.md:139`, config: `wepppy/nodb/configs/culvert.cfg:29`, code: `wepppy/rq/culvert_rq.py:176`)

## API Contract Validation
- Validation errors return `{success: false, errors: [...]}` but server errors return `{Success: False, Error: ..., StackTrace: [...]}`, and the spec does not document this schema split or error_code/error_detail in job status. (responses: `wepppy/microservices/rq_engine/responses.py:9`, `wepppy/microservices/rq_engine/responses.py:19`, spec: `docs/culvert-at-risk-integration/weppcloud-integration.spec.md:323`)
- Payload validator does not enforce many spec-required metadata fields (e.g., `source`, `created_at`, `dem.width/height/resolution_m/nodata`, `streams.value_semantics`, `watersheds.feature_count`), so contract enforcement is partial. (validator: `wepppy/microservices/culvert_payload_validator.py:137`)
- Model-parameters validation only checks `schema_version`; there is no type validation for `base_project_runid`, `nlcd_db`, `ssurgo_db`, or `flow_accum_threshold`. (validator: `wepppy/microservices/culvert_payload_validator.py:228`)
- GeoJSON geometry type checks (Point vs Polygon) are deferred to runtime in `CulvertsRunner` rather than enforced at ingest, so API validation is incomplete. (validator: `wepppy/microservices/culvert_payload_validator.py:317`, runtime: `wepppy/nodb/culverts_runner.py:674`)
- CRS validation enforces “projected in meters” but not “UTM required,” so spec’s UTM-only requirement is only partially enforced. (spec: `docs/culvert-at-risk-integration/weppcloud-integration.spec.md:190`, validator: `wepppy/microservices/culvert_payload_validator.py:162`)
- `/culverts-wepp-batch/{batch_uuid}/retry/{point_id}` is implemented but undocumented; upload field aliases (`payload`, `file`) are also undocumented. (routes: `wepppy/microservices/rq_engine/culvert_routes.py:39`, `wepppy/microservices/rq_engine/culvert_routes.py:126`)

## Core Implementation Review
- Short-stream pruning uses `min_length = 2 * cellsize` rather than the configured `watershed.wbt.mcl`, which changes network simplification behavior vs docs. (config: `wepppy/nodb/configs/culvert.cfg:8`, code: `wepppy/rq/culvert_rq.py:157`)
- `CulvertsRunner._resolve_run_config` only encodes `nlcd_db` overrides, so `ssurgo_db` overrides are applied at runtime but not reflected in `run_metadata.config`. (runner: `wepppy/nodb/culverts_runner.py:584`, run: `wepppy/rq/culvert_rq.py:467`)
- Representative flowpath mode is forced on for culvert batches, which changes hillslope geometry vs standard WEPP runs and is not described in the spec. (code: `wepppy/rq/culvert_rq.py:1344`, plan note: `docs/culvert-at-risk-integration/weppcloud-integration.plan.md:345`)
- Batch landuse/soils retrieval uses native-CRS extents for WMesque v2 (good), but the server-side `bbox_crs` behavior is external and not verified here. (client: `wepppy/all_your_base/geo/webclients/wmesque.py:79`, caller: `wepppy/rq/culvert_rq.py:1218`)
- Stream coverage check reads full rasters into memory per run (`_sum_masked_raster`), which may be a performance hotspot for large 1m DEMs. (runner: `wepppy/nodb/culverts_runner.py:29`)

## Test Coverage Analysis
- Ingestion tests do not cover size/hash mismatches, invalid `schema_version`, invalid `total_bytes`, invalid ZIP member paths, or raster transform/size mismatches. (tests: `tests/microservices/test_rq_engine_culverts.py:55`, validator: `wepppy/microservices/culvert_payload_validator.py:241`)
- Orchestration tests don’t exercise `NoOutletFoundError` seeding, `CulvertPointOutsideWatershedError`, or minimum watershed area filtering. (tests: `tests/culverts/test_culvert_orchestration.py:32`, code: `wepppy/rq/culvert_rq.py:1310`)
- CulvertsRunner tests skip VRT cropping, stream fallback selection (`streams.tif`/`chnjnt.streams.tif`), and map-mode order reduction behavior. (tests: `tests/culverts/test_culverts_runner.py:200`, code: `wepppy/nodb/culverts_runner.py:235`)
- No tests cover the retry endpoint or browse/download routes for culvert batches. (routes: `wepppy/microservices/rq_engine/culvert_routes.py:126`, `wepppy/microservices/browse.py:1909`, `wepppy/microservices/_download.py:214`)
- No tests validate native-CRS WMesque retrieval or the nodata guard behavior noted in Phase 5d. (code: `wepppy/rq/culvert_rq.py:1218`, plan: `docs/culvert-at-risk-integration/weppcloud-integration.plan.md:552`)

## Known Issues and Open Items
- Retention cleanup is not implemented; `_retention_days` is set but no job removes stale batches. (plan: `docs/culvert-at-risk-integration/weppcloud-integration.plan.md:455`, code: `wepppy/rq/culvert_rq.py:626`)
- Idempotency/deduping for duplicate POSTs remains unresolved, and there is no idempotency key support in the route. (plan: `docs/culvert-at-risk-integration/weppcloud-integration.plan.md:598`, route: `wepppy/microservices/rq_engine/culvert_routes.py:39`)
- Error propagation into RQ job status (error_code/error_detail) is not implemented; job status returns only aggregated state. (spec: `docs/culvert-at-risk-integration/weppcloud-integration.spec.md:327`, code: `wepppy/rq/job_info.py:104`)
- Redis DB 2 status events for culvert runs are not emitted; logging relies on standard handlers only. (spec: `docs/culvert-at-risk-integration/weppcloud-integration.spec.md:312`, code: `wepppy/rq/culvert_rq.py:80`)
- Phase 5d wepppyo3 nodata guard is not present in this repo; landuse/soils still assume complete keys from `identify_mode_single_raster_key`. (plan: `docs/culvert-at-risk-integration/weppcloud-integration.plan.md:552`, code: `wepppy/nodb/core/landuse.py:538`)
- Watershed simplification issue remains a Culvert_web_app upstream dependency; validator does not enforce unsimplified polygons. (plan: `docs/culvert-at-risk-integration/weppcloud-integration.plan.md:468`, builder: `docs/culvert-at-risk-integration/dev-package/scripts/build_payload.py:688`)

## Integration Points
- WMesque2 native CRS retrieval is wired through `extent_crs` and `bbox_crs` in the client and culvert batch landuse/soils fetch path. (client: `wepppy/all_your_base/geo/webclients/wmesque.py:79`, caller: `wepppy/rq/culvert_rq.py:1218`)
- Browse and download routes exist for culvert batch artifacts under `/weppcloud/culverts/{uuid}/browse/` and `/weppcloud/culverts/{uuid}/download/`. (browse: `wepppy/microservices/browse.py:1909`, download: `wepppy/microservices/_download.py:214`)
- RQ job metadata is set for culvert batch/run jobs, and job status aggregation works, but errors are not surfaced in job status payloads. (culvert jobs: `wepppy/rq/culvert_rq.py:253`, job info: `wepppy/rq/job_info.py:104`)
- Run path resolution supports culvert run groups via `CULVERTS_ROOT`, aligning browse/download to `/wc1/culverts/<uuid>/runs/<Point_ID>/`. (helpers: `wepppy/weppcloud/utils/helpers.py:144`)

## Prioritized Remaining Work
1. Align docs and examples with the implemented contract (schema_version values, Point_ID source file, `project_id`, model-parameters keys, pruning semantics, and extra artifacts like `batch_summary.json`).
2. Implement structured error propagation in RQ job status (`error_code`, `error_detail`) and normalize error response schemas across rq-engine endpoints.
3. Add a retention/cleanup job that enforces `culvert_runner.DEFAULT_RETENTION_DAYS`, and document retention in the plan/spec.
4. Confirm or implement wmesque2 server-side `bbox_crs` support and landuse/soils nodata guard in wepppyo3; add regression tests using the provided fixtures.
5. Decide whether pruning should use `watershed.wbt.mcl` or the cellsize-based heuristic, and update code/docs/tests accordingly.
6. Expand tests for validation edge cases (schema_version, size/hash mismatches, raster transform mismatches), run-level validation errors, and the retry endpoint.
7. Evaluate performance of `_sum_masked_raster` for large 1m DEMs; consider windowed or masked statistics to avoid full-raster reads.

## Resolution Summary (Post-Review Updates)
- Documentation alignment: updated spec/plan/dev-package docs for cellsize-based pruning, optional `flow_accum_threshold`, `order_reduction_passes` mapping, GeoJSON CRS/geometry validation, and the retry endpoint; removed `ssurgo_db` override from docs; added Phase 6a for error schema standardization; marked Phase 5d complete with updated wepppyo3.
- Validator updates: added `flow_accum_threshold` checks, model-parameter type validation, and GeoJSON geometry type enforcement at ingest.
- Runtime changes: removed `ssurgo_db` override in the culvert RQ pipeline so metadata reflects only `nlcd_db` overrides; retained cellsize-based pruning per decision.
- Test coverage: added ingestion mismatch cases, orchestration validation (NoOutletFoundError seeding, point-outside-watershed, minimum area), runner VRT/stream fallback, order-reduction map mode, and a wepppyo3 nodata guard regression test.
- Deferred work: error schema normalization and job error propagation moved to Phase 6a; retention and idempotency items remain open per the Prioritized Remaining Work list.
