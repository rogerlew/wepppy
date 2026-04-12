# WP-03 Work Package: Convert Endpoint + CRS/Format Pipeline
Status: done
Last Updated: 2026-04-11
Owner: Fresh Agent (unassigned)
Parent Plan: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md`
Primary Spec: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/specification.md`

## Objective
Deliver WP-03 end-to-end by implementing `POST /utils/shape-converter/v1/convert` with CRS-aware conversion and format output behavior (GeoJSON + GeoParquet) using independent upload model.

This package is complete only when all WP-03 gates pass:
- Code gate
- Shape-converter unit-test gate
- QA gate
- Security review gate

## Scope
### In scope
- Implement convert endpoint contract and request validation.
- Reuse ZIP/shapefile validation controls from WP-02 for convert uploads.
- Implement CRS behavior for:
  - `same_as_shapefile`
  - `wgs84`
  - `utm_wepppy_upper_left`
- Implement output serialization for:
  - GeoJSON (RFC 7946 for WGS84, non-RFC projected mode signaling)
  - GeoParquet (with required geospatial metadata)
- Implement convert-specific canonical errors and status mapping.
- Add unit/integration tests and smoke evidence for convert.
- Update orchestration board and this work-package evidence.

### Out of scope
- Relay-mode `response_mode=json_body` final behavior and browser handoff UX (WP-06B).
- UI implementation details (WP-06).
- Cleanup hardening and janitor lifecycle completion (WP-04).
- Abuse-control/rate-limit/backpressure implementation (WP-05).
- Runtime hardening/sandbox enforcement completion (WP-07).
- WEPPcloud route/controller updates (separate scope).

## Constraints and Invariants
- No branch creation unless explicitly requested by human operator.
- Do not modify unrelated dirty files.
- Keep convert/inspect as independent uploads; no cross-request staging.
- Preserve public no-auth access model.
- Maintain canonical error payload with required `error.details`.
- Keep route namespace under `/utils/shape-converter/*`.

## Required API Contract (WP-03)
## Endpoint
- `POST /utils/shape-converter/v1/convert`

## Request
- `multipart/form-data` with:
  - `archive` (ZIP)
  - `output_format=geojson|geoparquet`
  - `target_crs=same_as_shapefile|wgs84|utm_wepppy_upper_left`
  - `response_mode` optional (`download|json_body`)

## Response behavior in WP-03
- Required now:
  - `response_mode=download` success path for `geojson` and `geoparquet`.
- Deferred to WP-06B:
  - `response_mode=json_body` final relay mode behavior.
- If `json_body` is not implemented in WP-03, endpoint must fail explicitly with canonical 4xx error and a clear code/message/details (no silent fallback).

## Error response
Canonical shape:
```json
{
  "error": {
    "message": "...",
    "code": "...",
    "details": "..."
  }
}
```
`error.details` is required.

## Convert error codes to cover
- `invalid_archive`
- `archive_path_traversal`
- `archive_quota_exceeded`
- `missing_required_sidecar`
- `invalid_shapefile`
- `unknown_source_crs`
- `reprojection_failed`
- `utm_not_supported_for_extent`

## CRS and Output Rules (WP-03)
1. `same_as_shapefile`
   - Preserve source CRS when known.
   - If source CRS unknown, do not reproject; preserve coordinates and mark warnings/metadata accordingly.
2. `wgs84`
   - Reproject to EPSG:4326.
   - If source CRS unknown -> fail `unknown_source_crs`.
3. `utm_wepppy_upper_left`
   - Determine UTM zone from upper-left bbox corner in WGS84, matching WEPPpy behavior.
   - Use hemisphere from north latitude sign.
   - If outside UTM domain -> `utm_not_supported_for_extent`.
4. GeoJSON output
   - WGS84 mode: RFC 7946-compatible.
   - Projected mode: non-RFC signaling + explicit warning metadata.
5. GeoParquet output
   - Include required geometry metadata (`geo` metadata key, primary column, CRS metadata when known).

## Target File Plan
Expected new/modified files for WP-03 (adjust only if justified):
- `wepppy/microservices/shape_converter/app.py`
- `wepppy/microservices/shape_converter/convert.py` (recommended)
- `wepppy/microservices/shape_converter/crs.py` (recommended)
- `wepppy/microservices/shape_converter/serialization.py` (recommended)
- `wepppy/microservices/shape_converter/errors.py`
- `wepppy/microservices/shape_converter/inspect.py` (only if shared metadata helpers needed)
- `tests/shape_converter/unit/test_convert_endpoint.py`
- `tests/shape_converter/unit/test_crs_transform.py`
- `tests/shape_converter/unit/test_output_serialization.py`
- `tests/shape_converter/integration/test_convert_api.py`
- `tests/shape_converter/helpers/archive_builder.py` (extend fixtures as needed)

Doc updates required:
- `/workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-03_convert_endpoint_crs_format_pipeline.md` (fill evidence)
- `/workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md` (WP-03 state + gate statuses)

## Implementation Steps (Execute Sequentially)
1. Add convert route and request parsing in app.
2. Reuse archive validation and shapefile loading from WP-02 where possible.
3. Implement CRS selection and transform pipeline.
4. Implement GeoJSON and GeoParquet serializers.
5. Implement download response path with metadata sidecar behavior.
6. Handle `response_mode=json_body` explicitly (implemented or explicit deferred error path).
7. Implement canonical convert error mapping and status codes.
8. Add/extend unit tests for CRS and serialization logic.
9. Add integration tests for convert happy paths and error paths.
10. Run gates, collect smoke evidence, update docs.

## Commands and Validation
## Fast unit iteration
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/unit -k "convert or crs or serialization" --maxfail=1
```

## Full unit gate
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/unit
```

## Integration gate (convert-focused)
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/integration -k convert --maxfail=1
```

## Local smoke via Caddy (example)
```bash
cd /workdir/wepppy
docker compose -f docker/docker-compose.dev.yml up -d caddy shape-converter
curl -i -H 'X-Forwarded-Proto: https' \
  -F 'archive=@<valid_zip>' \
  -F 'output_format=geojson' \
  -F 'target_crs=wgs84' \
  http://127.0.0.1:8080/utils/shape-converter/v1/convert
curl -i -H 'X-Forwarded-Proto: https' \
  -F 'archive=@<valid_zip_missing_prj>' \
  -F 'output_format=geojson' \
  -F 'target_crs=wgs84' \
  http://127.0.0.1:8080/utils/shape-converter/v1/convert
```

Expected:
- Valid request returns artifact response for download mode.
- Missing source CRS with target reprojection returns canonical `unknown_source_crs`.

## Gate Checklist
## Code gate
- [x] WP-03 implementation scope complete.
- [x] Code review findings resolved.
- [x] Lint/static checks for touched files pass.

## Shape-converter unit-test gate
- [x] `wctl run-pytest tests/shape_converter/unit --maxfail=1` passes.
- [x] `wctl run-pytest tests/shape_converter/unit` passes.

## QA gate
- [x] Convert success path validated through proxied route.
- [x] Convert error paths validated with canonical payloads.
- [x] Smoke evidence captured.

## Security review gate
- [x] Convert path reuses archive validation controls from WP-02.
- [x] CRS error paths are explicit (no silent fallback transforms).
- [x] Projected GeoJSON compatibility warnings present.
- [x] Security reviewer sign-off recorded.

## Evidence Log (Fill During Execution)
| Item | Evidence |
| --- | --- |
| Commit SHA(s) | Not committed in this run (local working tree changes only). |
| Unit gate output | `wctl run-pytest tests/shape_converter/unit -k "convert or crs or serialization" --maxfail=1` -> `50 passed, 32 warnings in 9.30s`; `wctl run-pytest tests/shape_converter/unit --maxfail=1` -> `50 passed, 32 warnings in 9.57s`; `wctl run-pytest tests/shape_converter/unit` -> `50 passed, 32 warnings in 9.69s`. |
| Integration gate output | `wctl run-pytest tests/shape_converter/integration -k convert --maxfail=1` -> `9 passed, 3 warnings in 9.17s`. |
| QA smoke output | `docker compose -f docker/docker-compose.dev.yml up -d caddy shape-converter`; proxied convert success (`output_format=geojson,target_crs=wgs84`) returned `200`, `Content-Type=application/geo+json`, metadata sidecar path under `/utils/shape-converter/v1/convert/metadata/<id>`; proxied error (`missing .prj` + `target_crs=wgs84`) returned canonical `400` with `error.code=unknown_source_crs` and non-empty `error.details`; proxied deferred relay mode (`response_mode=json_body`) returned canonical `400` with `error.code=response_mode_not_supported`. |
| Security review reference | Subagent security/code/QA review findings (high/medium) were addressed in this pass: upload reads now enforce streaming byte caps before buffering, convert metadata sidecar cache now uses bounded TTL+max-entry eviction, `.prj` size cap added to prevent inspect response amplification, CRS parsing now falls back from invalid WKT to valid mapping, GeoParquet serialization now guards Arrow exceptions across the full path, and additional API-boundary tests cover traversal/quota/sidecar/invalid-shapefile/reprojection/same-as-unknown/proxied-metadata behaviors; changed-file broad-catch enforcement passed via `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` (`Result: PASS`). |
| Residual risks | WP-04: request-lifecycle cleanup hardening/abnormal-termination janitor behavior still pending. WP-05: public abuse controls (rate limits/concurrency/backpressure/trusted-proxy identity enforcement) still pending. WP-06B: `response_mode=json_body` relay mode intentionally deferred (explicit 400 guard in WP-03). WP-07: runtime hardening/sandbox enforcement and readiness guarantees still pending. |

## Completion Criteria
WP-03 is `done` only when:
- All four gates are `pass` (or explicitly waived with rationale/approver).
- Parent orchestration board is updated with WP-03 state/gates and evidence notes.
- This work-package evidence table is filled with concrete references.

## Handoff Notes for Fresh Agent
- Execute this package end-to-end without pausing unless blocked.
- If blocked, update:
  - this WP file (`Evidence Log` + blocker note), and
  - `/workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md` (WP-03 state -> `blocked` + reason).
