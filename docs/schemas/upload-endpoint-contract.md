# Upload Endpoint Contract
> Authoritative contract for upload-capable API endpoints in rq-engine and adjacent NoDb upload surfaces.
> **See also:** `docs/schemas/rq-response-contract.md` and `docs/schemas/rq-controller-state-contract.md`.

## Scope
- Covers HTTP endpoints that accept multipart file uploads in:
  - `wepppy/microservices/rq_engine/*_routes.py`
  - `wepppy/weppcloud/routes/nodb_api/roads_bp.py`
- Defines canonical per-endpoint caps, extension allowlists, and core validators.
- Documents upload-facing error expectations (canonical error shape; informative user-visible reasons for validation failures).

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

## Raster Content and Driver Boundary

**F6-RU-01 amendment status:** accepted behavior proposal; implementation
conformance pending. The standalone contract checkpoint must be an ancestor of
route, helper, template, controller, test, and user-facing documentation edits.

General raster upload endpoints accept only self-contained files whose content
matches their declared extension:

| Extension | Required GDAL driver |
| --- | --- |
| `.tif`, `.tiff` | `GTiff` |
| `.img` | `HFA` |

Before any route-specific parser, metadata reader, raster stacker, NoDb
validator, or other native consumer receives the file, the upload boundary must
stage the bytes as a regular nonsymlink file in private scratch space, open that
snapshot with only the required driver enabled, verify the reported driver is
exact, and force an actual read of every raster band. The driver-restricted read
must report no dependent files other than the staged primary file. A renamed
raster, malformed/truncated file, external HFA sidecar dependency, or unsupported
driver is a validation failure.

Successful exact-driver full-band decoding plus the recorded byte hash is the
format trust boundary: it materializes a validated immutable upload snapshot
(trusted only for format/driver identity, not scientific semantics). That
snapshot is the only uploaded pathname route-specific native validators may
consume. Its byte hash and filesystem identity must remain unchanged through
those validators. Only those exact validated bytes may be
atomically published as a run-owned artifact. A persisted accepted artifact may
be reused only from server-authoritative state beneath its approved run-owned
upload root; traversal, symlink escape, and a client-selected replacement
pathname are invalid. A legacy absolute-path field may be accepted only as a
non-authoritative reuse signal when the server ignores its value and derives the
sole candidate from run-owned state. Reuse must prove the same byte identity under
the owning mutation/read lock immediately before consumption. These invariants
prove that an unrestricted legacy semantic validator never receives unvalidated
or replaceable bytes. Direct GDAL opens added or touched by this remediation must
use `OpenEx(..., allowed_drivers=[expected])` or equivalent.

All raster parts and persisted raster reuses in one request must pass boundary
validation before any part is published, controller state is mutated, or work
is enqueued. A failure during that request-wide boundary-validation phase must
remove request scratch files and leave accepted destinations and controller
state unchanged. Failures after boundary validation follow the canonical NoDb
composite-operation rules; this upload-format boundary does not add a new
distributed rollback guarantee.

General raster upload endpoints do not accept VRT because their multipart
contracts do not collect and prove a closed referenced-file graph. The narrowly
validated postfire dNBR identity-VRT contract is separate and unchanged. A
previously stored user raster must pass this boundary before reuse; an old VRT or
mismatched file requires re-upload rather than unrestricted native opening.

This contract composes with, without changing, the canonical RQ response/error
contract in `docs/schemas/rq-response-contract.md` and the failed-mutation and
composite-operation rules in
`docs/schemas/nodb-persistence-concurrency-contract.md`.

## Uploaded climate mode

A successfully applied CLI upload records
the user-defined catalog identity and derives its mode from the parsed file.
Use mode 15 for an individual event and mode 12 for continuous climate, including
replacement in either direction. Obsolete batch result references cannot label
the new upload. Existing spatial and authorization constraints still apply.

For legacy stored upload modes 12 and 15, the Climate summary shows the
type of the current active, readable CLI without mutating the run. The advisory
lives in the summary so a successful upload refresh updates it on the same page.
Require a regular active CLI to match the recorded filename and Climate source
directory, with recorded upload station data. The legacy check cannot verify
historical ancestry if a generated file reused the exact same recorded upload
path. The form keeps the existing user-defined catalog selector. The display calculation does not change the stored mode selectors
used by the no-preparation pipeline. WEPP preparation reconciles a verified
mismatch and obsolete batch references before preparing a deck, holding the
climate root operation and the Climate write lock. Reject a missing or malformed
recorded upload at preparation, including an invalid daily calendar date. Generated and batch types are unaffected. Existing no-preparation
paths keep their prepared inputs and existing mode selection. This correction
does not change the publication or retention boundary for overlapping uploads
and failed replacements.

## Route Prefix Notes
- FastAPI routes below are served under the rq-engine API prefix (`/rq-engine/api/...`).
- Flask Roads routes are listed as defined in the blueprint and are mounted by WEPPcloud route registration.

## Upload Endpoint Matrix

| Endpoint | Handler module | Upload field(s) | Allowed extensions/types | Max size | Additional validation |
| --- | --- | --- | --- | --- | --- |
| `/api/runs/{runid}/{config}/tasks/upload-cli/` | `wepppy/microservices/rq_engine/upload_climate_routes.py` | `input_upload_cli` | `.cli` | `25 * 1024 * 1024` (25 MB) | Saved via `save_upload_file`; enqueue `upload_cli_rq` |
| `/api/runs/{runid}/{config}/tasks/upload-sbs/` | `wepppy/microservices/rq_engine/upload_disturbed_routes.py` | `input_upload_sbs` | `.tif`, `.tiff`, `.img` | `100 * 1024 * 1024` (100 MB) | Restricted format/driver validation, then `sbs_map_sanity_check`, `baer.validate(...)` |
| `/api/runs/{runid}/{config}/tasks/upload-cover-transform` | `wepppy/microservices/rq_engine/upload_disturbed_routes.py` | `input_upload_cover_transform` | `.csv` | `10 * 1024 * 1024` (10 MB) | `Revegetation.validate_user_defined_cover_transform(...)` |
| `/api/runs/{runid}/{config}/tasks/upload-dem/` | `wepppy/microservices/rq_engine/watershed_routes.py` | `input_upload_dem` | `.tif`, `.tiff`, `.img` | `100 * 1024 * 1024` (100 MB) | Restricted format/driver validation before DEM install/metadata validation in `_install_uploaded_dem(...)` |
| `/api/huc-fire/tasks/upload-sbs/` | `wepppy/microservices/rq_engine/upload_huc_fire_routes.py` | `input_upload_sbs` | `.tif`, `.tiff`, `.img` | `100 * 1024 * 1024` (100 MB) | Restricted format/driver validation, then `Disturbed.validate(...)` |
| `/api/batch/_/{batch_name}/upload-geojson` | `wepppy/microservices/rq_engine/upload_batch_runner_routes.py` | `geojson_file` or `file` | `.geojson`, `.json`, single-dataset Shapefile `.zip`, `.parquet`, `.geoparquet` | default `30 * 1024 * 1024` (30 MiB); override via Flask `BATCH_GEOJSON_MAX_MB` | Binary formats normalize through shape-converter; receiving validation requires only Polygon/MultiPolygon before replacement/registration; existing saved projects are not migrated |
| `/api/batch/_/{batch_name}/upload-sbs-map` | `wepppy/microservices/rq_engine/upload_batch_runner_routes.py` | `sbs_map` or `file` | `.tif`, `.tiff`, `.img` | `100 * 1024 * 1024` (100 MB) | Restricted format/driver validation, then `sbs_map_sanity_check(...)`; optional burn-class summary |
| `/api/runs/{runid}/{config}/agfields/boundaries` | `wepppy/microservices/rq_engine/ag_fields_routes.py` | `field_boundaries` | `.geojson`, `.json`, single-dataset Shapefile `.zip`, `.parquet`, `.geoparquet` | `10 * 1024 * 1024` (10 MB) | Binary formats normalize through shape-converter; receiving validation requires Polygon/MultiPolygon and literal `field_id` before canonical GeoJSON/attribute replacement |
| `/api/runs/{runid}/{config}/agfields/plant-database` | `wepppy/microservices/rq_engine/ag_fields_routes.py` | `plant_database` | ZIP containing `.man` members only | compressed `100 * 1024 * 1024` (100 MB); uncompressed 600 MB; 200 members | `read_upload_bytes_with_limit(...)` + `validate_and_extract_zip_archive(...)`; unique server filename; RQ processing removes the staged archive |
| `/api/culverts-wepp-batch/` | `wepppy/microservices/rq_engine/culvert_routes.py` | `payload.zip` or `payload` or `file` | ZIP archive | compressed payload cap `2 * 1024 * 1024 * 1024` (2 GiB) | **Must** use `read_upload_bytes_with_limit(...)` + `validate_and_extract_zip_archive(...)`; `ArchiveLimits(max_compressed_bytes=2 GiB, max_uncompressed_bytes=6 GiB, max_member_count=1200)`; semantic checks via `validate_payload_root(...)` |
| `/runs/<string:runid>/<config>/tasks/roads/upload_geojson` (and trailing slash variant) | `wepppy/weppcloud/routes/nodb_api/roads_bp.py` | `file` | `.geojson`, `.json`, single-dataset Shapefile `.zip`, `.parquet`, `.geoparquet` | `10 * 1024 * 1024` (10 MB) | Binary formats normalize through shape-converter; controller revalidates canonical LineString/MultiLineString via `Roads.set_uploaded_geojson(...)` |

## Mixed-Payload Endpoints With Upload Fields

These routes combine non-file params with optional/conditional upload parts.

| Endpoint | Handler module | Upload field(s) | Allowed extensions/types | Max size | Upload condition |
| --- | --- | --- | --- | --- | --- |
| `/api/runs/{runid}/{config}/build-landuse` | `wepppy/microservices/rq_engine/landuse_routes.py` | `input_upload_landuse` | `.tif`, `.tiff`, `.img` | `500 * 1024 * 1024` (500 MB) | Restricted format/driver validation in UserDefined mode and [applied input preservation and map checks](european-landuse-mapping-contract.md#uploaded-raster-compatibility) (implementation pending) |
| `/api/runs/{runid}/{config}/build-treatments` | `wepppy/microservices/rq_engine/treatments_routes.py` | `input_upload_landuse` | `.tif`, `.tiff`, `.img` | `500 * 1024 * 1024` (500 MB) | Restricted format/driver validation; used when `treatments.mode == UserDefinedMap` |
| `/api/runs/{runid}/{config}/run-ash` | `wepppy/microservices/rq_engine/ash_routes.py` | `input_upload_ash_load` (required), `input_upload_ash_type_map` (optional) | `.tif`, `.tiff`, `.img` | `100 * 1024 * 1024` (100 MB) | Restricted format/driver validation; used when `ash_depth_mode == 2` |
| `/api/runs/{runid}/{config}/run-omni` | `wepppy/microservices/rq_engine/omni_routes.py` | `scenarios[{idx}][sbs_file]` | `.tif`, `.tiff`, `.img` | `100 * 1024 * 1024` (100 MB) | Restricted format/driver validation per uploaded SBS scenario |
| `/api/runs/{runid}/{config}/run-omni-contrasts` | `wepppy/microservices/rq_engine/omni_routes.py` | `omni_contrast_geojson` (optional/required by mode) | `.geojson`, `.json`, single-dataset Shapefile `.zip`, `.parquet`, `.geoparquet` | `100 * 1024 * 1024` (100 MB) | Binary formats normalize through shape-converter; user-defined areas require Polygon/MultiPolygon validation before saved input mutation/build |
| `/api/runs/{runid}/{config}/run-omni-contrasts-dry-run` | `wepppy/microservices/rq_engine/omni_routes.py` | `omni_contrast_geojson` (optional/required by mode) | `.geojson`, `.json`, single-dataset Shapefile `.zip`, `.parquet`, `.geoparquet` | `100 * 1024 * 1024` (100 MB) | Same normalization and pre-mutation receiving validation as `run-omni-contrasts`; no run enqueue |

## Vector normalization amendment (VUN-01)

Accepted contract intent 2026-11-16; implementation conformance pending. The
four rows above compose with the canonical
[vector-upload normalization contract](vector-upload-normalization-contract.md)
and [GeoParquet resource ADR](../adrs/ADR-0145-geoparquet-upload-resource-bounds.md).
Extensions and MIME are hints; content identity, hostile-input structural limits,
canonical WGS84 output, receiving semantic validation, failed-replacement safety,
stable error translation and observable normalization receipts are mandatory.
The converter cannot authorize persistence, mutate workflow state or bypass
authentication, CSRF, run scope, locks, existing byte policies or response
envelopes. Each complete within-limit original is retained under the owning
project attempt tree with SHA-256 provenance. Rejected originals use the
download-only quarantine contract; public-run access does not expose attempt
artifacts. A generic authenticated public-run reader is not the owner: retained
evidence requires explicit run owner/root or existing Batch project/group
authority. Filesystem-wide atomic admission composes the ADR aggregate,
principal, in-flight and free-space limits before source bytes. Culvert and
D-Tale paths are excluded. No queue edge is added.

RQ-WH-01 accepted amendment (2026-10-28 19:56 UTC; implementation pending):
`/api/culverts-wepp-batch/` accepts an optional multipart `webhook_url` text field
and, when present, requires the Idempotency-Key header under the
[webhook admission contract](rq-webhook-contract.md#Admission-and-recovery-matrix).
Validate callback syntax before extraction; bind the computed upload digest for
recovery. Existing archive limits, upload aliases and semantic validation remain
mandatory. Do not retain the raw callback in project uploads or archives.
## Omni saved-input staging (OSR-01)

Accepted intent 2026-11-16; candidate implemented with scoped validation. Omni SBS uploads
adopt the [user-file staging lifecycle](user-file-staging-contract.md).
The [Omni SBS control contract](../ui-docs/contracts/omni-sbs-control-contract.md)
defines saved-reference resolution, replacement isolation, and restoration from
the corresponding scenario project. Existing extension, size, restricted-decoder,
containment, authentication, and error rules remain mandatory. No other upload
consumer is enrolled by this amendment.

## Error Contract Requirements
- Upload validation failures must return canonical 4xx responses with `error.message`, `error.details`, `error.code`, and top-level `error_id` consistent with `docs/schemas/rq-response-contract.md`.
- MUST return specific user-visible failure reasons (`error.message`) for validation/business failures.
- MUST include stable `error.code` + `error_id` in API responses.
- MUST log full traceback server-side with that `error_id` for exception-driven failures.
- Upload validation failures **MUST** include a specific, user-visible reason in `error.message` (for example: unsupported extension/type, missing required upload field, or size limit exceeded). Generic-only messages like `Invalid upload` are not acceptable.
- Server faults must return canonical 5xx responses.
- API payloads MAY include traceback details; response/log correlation through `error_id` is required.
- Size-limit failures should return `413` where implemented (for example, culvert ZIP and explicit max-size checks).

## New Upload Route Requirements
- Define explicit upload field names, allowed extensions/types, and max-size caps in route code.
- Use canonical helper ownership rules:
  - Non-ZIP routes use `wepppy/microservices/upload_boundary.py` (rq-engine routes use `wepppy/microservices/rq_engine/upload_helpers.py` as compatibility wrapper).
  - ZIP routes reuse `wepppy/microservices/shape_converter/archive_validation.py`; do not introduce ad-hoc ZIP validators.
- Preserve canonical error payload shape.
- Do not blind users on validation errors: route-level `error.message` values must state exactly why the upload was rejected.
- Preserve explicit status behavior: use `413` for enforced size-limit failures and `400` for validation/type failures.
- Preserve `post_save` boundary semantics: if `post_save` raises, the destination file is cleaned up and the exception `status_code` (when present) propagates through route error mapping.
- Add regression tests for each new upload route:
  - accepted upload path,
  - rejected extension/type path,
  - oversize upload path.
- Update this contract in the same change when adding or modifying upload routes.

## Maintenance Rules
- If any upload cap, extension allowlist, or upload field name changes in code, update this contract in the same change.
- If a new upload endpoint is added, add it to this document before merge.
- For culvert ZIP handling changes, preserve reuse of `archive_validation.py` controls and keep semantic payload rules in `culvert_payload_validator.py`.

## SBS palette admission

Shared SBS sanity validation follows the SBS raster contract's Unknown palette
colors section: structurally valid rasters with readable but unrecognized
palette colors are accepted for explicit class assignment. A palette need not
contain a recognized low/moderate/high color. This does not relax upload size,
extension, authorization, containment, projection, integer/class-count or native
error requirements. Implemented and regression-checked 2026-10-13.

Schema discovery reports `color_table_mode: optional_unknown_colors_unassigned`;
the existing key is retained, and its value describes this admission behavior.

### Climate upload admission isolation

The upload endpoint keeps the existing authorization, multipart field,
extension, size limit, response and Climate job family. Each admitted upload gets a run-owned staging directory outside
the active Climate outputs. The HTTP request stages the candidate and records
the run, RQ job identifier and CLI basename only after the tracked submission
conflict check. It may not change the active climate files, Climate NoDb
metadata or completed Climate timestamp. An active job can reject a second
upload of the same filename without changing either its bytes or the previously
applied file.

New jobs receive the exact server-generated attempt identifier and the sanitized
CLI basename. The worker verifies their binding to the owning run and job and
requires a regular input under the contained, nonsymlink attempt directory.
Reject a retry once a later Climate job has superseded its receipt.
An already applied upload can be retried without republishing its bytes.
The existing two-argument worker form remains valid for already-enqueued jobs.
Workers capable of both forms must serve the queue before the new route admits
jobs. The worker validates and classifies a private snapshot matching the
admitted checksum. It publishes those exact bytes. Preserve the active basename
and path in Climate metadata and retain Single and Multiple spatial modes. The
worker verifies the active Climate directory and legacy source stay within the
run and replaces the destination without following an existing symlink.

Expose the attempt and its status under `climate_artifacts/climate_upload/attempts/`
through ordinary authorized run browsing and project archive/restore.
Only the current applied file appears in the Climate summary. A successful
application records completion and removes the consumed candidate. Failure
retains inspectable evidence for that attempt. Cleanup errors after a successful
application are secondary to its result. A proven enqueue follows the existing
tracked submission recovery. A conclusively absent enqueue uses the existing
tracked receipt restoration where available. If preallocation, lease
verification or enqueue fails with an uncertain outcome, leave the candidate
and receipt available and never overwrite a potentially newer tracked job reference. The
Climate panel's existing verified-job rule handles unconfirmed status.
Rollback after an upload passes file validation and generated-build retention
remain separate publication obligations.
