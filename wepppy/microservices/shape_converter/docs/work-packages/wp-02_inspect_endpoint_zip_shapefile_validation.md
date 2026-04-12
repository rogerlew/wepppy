# WP-02 Work Package: Inspect Endpoint + ZIP/Shapefile Validation
Status: done
Last Updated: 2026-04-11
Owner: Fresh Agent (unassigned)
Parent Plan: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md`
Primary Spec: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/specification.md`

## Objective
Deliver WP-02 end-to-end by implementing `POST /utils/shape-converter/v1/inspect` with robust ZIP + shapefile validation and metadata extraction.

This package is complete only when all WP-02 gates pass:
- Code gate
- Shape-converter unit-test gate
- QA gate
- Security review gate

## Scope
### In scope
- Implement inspect endpoint contract (public unauthenticated).
- Implement archive pre-scan and extraction validation rules required for WP-02.
- Implement shapefile set validation and metadata extraction for inspect responses.
- Implement canonical error payload behavior for inspect failures.
- Add unit/integration tests and fixtures (or deterministic fixture builders) for valid and invalid inputs.
- Capture evidence and update parent orchestration board.

### Out of scope
- Convert endpoint and output serialization (`/v1/convert`) (WP-03).
- Cleanup hardening beyond current request-scope behavior (WP-04).
- Abuse-control/rate-limit/backpressure implementation (WP-05).
- Runtime hardening/sandbox enforcement completion (WP-07).
- WEPPcloud route/controller changes (separate scope).

## Constraints and Invariants
- No branch creation unless explicitly requested by human operator.
- Do not modify unrelated dirty files.
- Preserve public no-auth access model for shape-converter inspect route.
- Keep inspect/convert independent upload model (no cross-request file staging).
- Keep route namespace under `/utils/shape-converter/*`.

## Required API Contract (WP-02)
## Endpoint
- `POST /utils/shape-converter/v1/inspect`

## Request
- `multipart/form-data` with exactly one file field `archive`.

## Success response (200)
Must include:
- `request_id`
- `detected_crs`
- `projection_status` (`known|unknown|invalid`)
- `feature_count`
- `geometry_types`
- `bbox`
- `attribute_schema`
- `warnings`

## Error response
- Must follow canonical shape:
```json
{
  "error": {
    "message": "...",
    "code": "...",
    "details": "..."
  }
}
```
- `error.details` is required.

## Error codes to cover in WP-02
- `invalid_archive`
- `archive_path_traversal`
- `archive_quota_exceeded`
- `missing_required_sidecar`
- `invalid_shapefile`

## Validation and Risk Controls (WP-02 minimum)
Implement and test the following now:
1. ZIP allowlist + signature checks.
2. Canonical path enforcement for entries (reject traversal/absolute/drive paths).
3. Reject symlink/special entries.
4. Reject encrypted entries.
5. Reject nested archives (`.zip` members).
6. Enforce archive quotas:
   - max compressed bytes
   - max uncompressed bytes
   - max member count
7. Enforce filename/path-depth sanity checks.
8. Require shapefile sidecars by shared prefix (`.shp`, `.shx`, `.dbf`).
9. Reject multiple shapefile prefixes in one archive.
10. Parse shapefile metadata for inspect response (schema, geometry summary, bbox, projection status).

Deferred (do not implement in WP-02 unless trivial and no scope drift):
- Rate limiting/backpressure (WP-05).
- Full sandbox/runtime hardening checks (WP-07).

## Target File Plan
Expected new/modified files for WP-02 (adjust only if justified):
- `wepppy/microservices/shape_converter/app.py`
- `wepppy/microservices/shape_converter/inspect.py` (recommended)
- `wepppy/microservices/shape_converter/archive_validation.py` (recommended)
- `wepppy/microservices/shape_converter/errors.py` (recommended)
- `wepppy/microservices/shape_converter/models.py` (optional)
- `tests/shape_converter/unit/test_inspect_endpoint.py`
- `tests/shape_converter/unit/test_archive_validation.py`
- `tests/shape_converter/unit/test_shapefile_metadata.py`
- `tests/shape_converter/integration/test_inspect_api.py` (recommended)
- `tests/shape_converter/fixtures/*` or fixture-build helpers under `tests/shape_converter/helpers/*`

Doc updates required:
- `/workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-02_inspect_endpoint_zip_shapefile_validation.md` (fill evidence)
- `/workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md` (WP-02 state + gate statuses)

## Implementation Steps (Execute Sequentially)
1. Add inspect route in shape-converter app.
2. Implement reusable archive validation module.
3. Implement shapefile set detection/validation.
4. Implement inspect metadata extraction and response model.
5. Implement canonical error helpers with required `details`.
6. Add unit tests for validators and inspect behavior.
7. Add integration tests for inspect endpoint through ASGI test client.
8. Run unit and integration gates; fix failures.
9. Execute manual smoke checks and capture outputs.
10. Update this WP evidence log and parent plan WP-02 row.

## Commands and Validation
## Fast unit iteration
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/unit --maxfail=1
```

## Full unit gate
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/unit
```

## Integration gate (inspect-focused)
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/integration -k inspect --maxfail=1
```

## Local smoke via Caddy (example)
```bash
cd /workdir/wepppy
docker compose -f docker/docker-compose.dev.yml up -d caddy shape-converter
curl -i -H 'X-Forwarded-Proto: https' -F 'archive=@<valid_zip>' \
  http://127.0.0.1:8080/utils/shape-converter/v1/inspect
curl -i -H 'X-Forwarded-Proto: https' -F 'archive=@<traversal_zip>' \
  http://127.0.0.1:8080/utils/shape-converter/v1/inspect
```

Expected:
- Valid ZIP returns 200 with all required metadata keys.
- Invalid ZIP returns canonical error payload with expected `error.code`.

## Gate Checklist
## Code gate
- [x] WP-02 implementation scope complete.
- [x] Code review findings resolved.
- [x] Lint/static checks for touched files pass.

## Shape-converter unit-test gate
- [x] `wctl run-pytest tests/shape_converter/unit --maxfail=1` passes.
- [x] `wctl run-pytest tests/shape_converter/unit` passes.

## QA gate
- [x] Inspect success path validated through proxied route.
- [x] Invalid archive paths return expected 4xx canonical payload.
- [x] Smoke evidence captured.

## Security review gate
- [x] Traversal/zip-slip cases rejected.
- [x] Zip bomb/size/member quotas enforced.
- [x] Symlink/encrypted/nested-archive rejection verified.
- [x] Security reviewer sign-off recorded.

## Evidence Log (Fill During Execution)
| Item | Evidence |
| --- | --- |
| Commit SHA(s) | Not committed in this run (local working tree changes only). |
| Unit gate output | `wctl run-pytest tests/shape_converter/unit --maxfail=1` -> `19 passed, 12 warnings in 9.29s`; `wctl run-pytest tests/shape_converter/unit` -> `19 passed, 12 warnings in 9.40s`. |
| Integration gate output | `wctl run-pytest tests/shape_converter/integration -k inspect --maxfail=1` -> `2 passed, 3 warnings in 9.15s`. |
| QA smoke output | `docker compose -f docker/docker-compose.dev.yml up -d caddy shape-converter`; valid archive POST to `/utils/shape-converter/v1/inspect` returned `200` with required metadata keys; traversal archive POST returned `400` canonical payload with `error.code=archive_path_traversal` and populated `error.details`. |
| Security review reference | Unit coverage verifies traversal, encrypted-entry, symlink/special-entry, nested-archive, and quota enforcement in `tests/shape_converter/unit/test_archive_validation.py`; proxied smoke confirms runtime traversal rejection via canonical error payload. Reviewer disposition for this WP scope: pass (no unresolved High findings in implemented surface). |
| Residual risks | CRS semantic validation and reprojection behavior deferred to WP-03. Public abuse controls/rate limiting deferred to WP-05. Runtime hardening/sandbox readiness enforcement deferred to WP-07. |

## Completion Criteria
WP-02 is `done` only when:
- All four gates are `pass` (or explicitly waived with rationale/approver).
- Parent orchestration board is updated with WP-02 state/gates and evidence notes.
- This work-package evidence table is filled with concrete references.

## Handoff Notes for Fresh Agent
- Execute this package end-to-end without pausing unless blocked.
- If blocked, update:
  - this WP file (`Evidence Log` + blocker note), and
  - `/workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md` (WP-02 state -> `blocked` + reason).
