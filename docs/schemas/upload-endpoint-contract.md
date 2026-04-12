# Upload Endpoint Contract
> Authoritative contract for upload-capable API endpoints in rq-engine and adjacent NoDb upload surfaces.
> **See also:** `docs/schemas/rq-response-contract.md` and `docs/schemas/rq-controller-state-contract.md`.

## Scope
- Covers HTTP endpoints that accept multipart file uploads in:
  - `wepppy/microservices/rq_engine/*_routes.py`
  - `wepppy/weppcloud/routes/nodb_api/roads_bp.py`
- Defines canonical per-endpoint caps, extension allowlists, and core validators.
- Documents upload-facing error expectations (canonical error shape; no traceback leakage in client payloads).

## Explicit Exclusions
- `shape_converter` endpoint behavior is out of scope for this contract.
- Culvert ZIP ingestion is in scope, but it must continue to reuse shared ZIP controls from:
  - `wepppy/microservices/shape_converter/archive_validation.py`
- Culvert semantic payload validation remains in:
  - `wepppy/microservices/culvert_payload_validator.py`

## Canonical Helper Ownership
- Canonical non-ZIP upload boundary helpers live in:
  - `wepppy/microservices/upload_boundary.py`
- rq-engine route call sites should consume the compatibility wrapper:
  - `wepppy/microservices/rq_engine/upload_helpers.py`
- Canonical ZIP helper authority remains in:
  - `wepppy/microservices/shape_converter/archive_validation.py`

## Route Prefix Notes
- FastAPI routes below are served under the rq-engine API prefix (`/rq-engine/api/...`).
- Flask Roads routes are listed as defined in the blueprint and are mounted by WEPPcloud route registration.

## Upload Endpoint Matrix

| Endpoint | Handler module | Upload field(s) | Allowed extensions/types | Max size | Additional validation |
| --- | --- | --- | --- | --- | --- |
| `/api/runs/{runid}/{config}/tasks/upload-cli/` | `wepppy/microservices/rq_engine/upload_climate_routes.py` | `input_upload_cli` | `.cli` | `25 * 1024 * 1024` (25 MB) | Saved via `save_upload_file`; enqueue `upload_cli_rq` |
| `/api/runs/{runid}/{config}/tasks/upload-sbs/` | `wepppy/microservices/rq_engine/upload_disturbed_routes.py` | `input_upload_sbs` | `.tif`, `.tiff`, `.img`, `.vrt` | `100 * 1024 * 1024` (100 MB) | `sbs_map_sanity_check`, `baer.validate(...)` |
| `/api/runs/{runid}/{config}/tasks/upload-cover-transform` | `wepppy/microservices/rq_engine/upload_disturbed_routes.py` | `input_upload_cover_transform` | `.csv` | `10 * 1024 * 1024` (10 MB) | `Revegetation.validate_user_defined_cover_transform(...)` |
| `/api/runs/{runid}/{config}/tasks/upload-dem/` | `wepppy/microservices/rq_engine/watershed_routes.py` | `input_upload_dem` | `.tif` | `100 * 1024 * 1024` (100 MB) | DEM install/metadata validation in `_install_uploaded_dem(...)` |
| `/api/huc-fire/tasks/upload-sbs/` | `wepppy/microservices/rq_engine/upload_huc_fire_routes.py` | `input_upload_sbs` | `.tif`, `.tiff`, `.img`, `.vrt` | `100 * 1024 * 1024` (100 MB) | `Disturbed.validate(...)` after save |
| `/api/batch/_/{batch_name}/upload-geojson` | `wepppy/microservices/rq_engine/upload_batch_runner_routes.py` | `geojson_file` or `file` | `.geojson`, `.json` | default `10 * 1024 * 1024` (10 MB); override via Flask `BATCH_GEOJSON_MAX_MB` | `WatershedCollection(...)` parse + feature-count checks |
| `/api/batch/_/{batch_name}/upload-sbs-map` | `wepppy/microservices/rq_engine/upload_batch_runner_routes.py` | `sbs_map` or `file` | `.tif`, `.tiff`, `.img`, `.vrt` | `100 * 1024 * 1024` (100 MB) | `sbs_map_sanity_check(...)`; optional burn-class summary |
| `/api/culverts-wepp-batch/` | `wepppy/microservices/rq_engine/culvert_routes.py` | `payload.zip` or `payload` or `file` | ZIP archive | compressed payload cap `2 * 1024 * 1024 * 1024` (2 GiB) | **Must** use `read_upload_bytes_with_limit(...)` + `validate_and_extract_zip_archive(...)`; `ArchiveLimits(max_compressed_bytes=2 GiB, max_uncompressed_bytes=6 GiB, max_member_count=1200)`; semantic checks via `validate_payload_root(...)` |
| `/runs/<string:runid>/<config>/tasks/roads/upload_geojson` (and trailing slash variant) | `wepppy/weppcloud/routes/nodb_api/roads_bp.py` | `file` | `.geojson` | `10 * 1024 * 1024` (10 MB) | Controller validation via `Roads.set_uploaded_geojson(...)` |

## Mixed-Payload Endpoints With Upload Fields

These routes combine non-file params with optional/conditional upload parts.

| Endpoint | Handler module | Upload field(s) | Allowed extensions/types | Max size | Upload condition |
| --- | --- | --- | --- | --- | --- |
| `/api/runs/{runid}/{config}/build-landuse` | `wepppy/microservices/rq_engine/landuse_routes.py` | `input_upload_landuse` | `.tif`, `.tiff`, `.img`, `.vrt` | `500 * 1024 * 1024` (500 MB) | Used when `landuse.mode == UserDefined` |
| `/api/runs/{runid}/{config}/build-treatments` | `wepppy/microservices/rq_engine/treatments_routes.py` | `input_upload_landuse` | `.tif`, `.tiff`, `.img`, `.vrt` | `500 * 1024 * 1024` (500 MB) | Used when `treatments.mode == UserDefinedMap` |
| `/api/runs/{runid}/{config}/run-ash` | `wepppy/microservices/rq_engine/ash_routes.py` | `input_upload_ash_load` (required), `input_upload_ash_type_map` (optional) | `.tif`, `.tiff`, `.img` | `100 * 1024 * 1024` (100 MB) | Used when `ash_depth_mode == 2` |
| `/api/runs/{runid}/{config}/run-omni` | `wepppy/microservices/rq_engine/omni_routes.py` | `scenarios[{idx}][sbs_file]` | `.tif`, `.tiff`, `.img` | `100 * 1024 * 1024` (100 MB) | Per-scenario upload when scenario type requires SBS map |
| `/api/runs/{runid}/{config}/run-omni-contrasts` | `wepppy/microservices/rq_engine/omni_routes.py` | `omni_contrast_geojson` (optional/required by mode) | `.geojson`, `.json` | `100 * 1024 * 1024` (100 MB) | Required for `user_defined_areas` when no path provided |
| `/api/runs/{runid}/{config}/run-omni-contrasts-dry-run` | `wepppy/microservices/rq_engine/omni_routes.py` | `omni_contrast_geojson` (optional/required by mode) | `.geojson`, `.json` | `100 * 1024 * 1024` (100 MB) | Same upload rules as `run-omni-contrasts` |

## Error Contract Requirements
- Upload validation failures must return canonical 4xx responses (`error.message`, optional `error.code`, `error.details`) consistent with `docs/schemas/rq-response-contract.md`.
- Server faults must return canonical 5xx responses without exposing traceback text to upload-facing clients.
- Size-limit failures should return `413` where implemented (for example, culvert ZIP and explicit max-size checks).

## Maintenance Rules
- If any upload cap, extension allowlist, or upload field name changes in code, update this contract in the same change.
- If a new upload endpoint is added, add it to this document before merge.
- For culvert ZIP handling changes, preserve reuse of `archive_validation.py` controls and keep semantic payload rules in `culvert_payload_validator.py`.
