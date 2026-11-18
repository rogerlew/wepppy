# Final code review: vector upload normalization

Date: 2026-11-17
Reviewed revision: `9ac7cb8f69cf5189cc80f5493e01c08c393da204`
Scope: M3-M5 receiving integration, retained-upload access, publication safety,
provenance, reload/downstream behavior, and focused tests.
Reviewer verdict: **HOLD**. One High and four Medium findings require closure.

The review was source-only except for a direct hostile-coordinate probe. It did
not modify runtime code. Line numbers below refer to the reviewed revision.

## Findings

### VUN-CODE-01 — High — Batch sensitive evidence authorization is bypassable through a symlink alias

**Locations:**

- `wepppy/microservices/browse/_download.py:476-513`
  (`download_culvert_with_subpath`)
- `wepppy/microservices/browse/_download.py:516-551`
  (`download_batch_with_subpath`)

The resolved-path sensitive check was inserted in the Culvert handler instead
of the Batch handler. The Culvert function calls
`can_access_batch_sensitive_vector(auth_context, batch_name)` at lines 506-508,
but `batch_name` is undefined there. A matching Culvert subpath therefore raises
`NameError` and returns a 500 even though Culvert is explicitly outside this
work package.

Conversely, the Batch handler authorizes only the caller-supplied `subpath`,
then resolves the filesystem target at lines 545-547 without reclassifying that
resolved target. Batch permits the established public-read path at line 527. An
innocently named in-root symlink whose target is under
`resources/vector_upload_attempts/` can therefore pass raw-path authorization
and return a retained original or receipt to a caller who is not authorized for
sensitive evidence. `download_response_file` marks a resolved `.upload` as an
attachment, but attachment headers are not authorization.

This violates the contract that aliases cannot expose retained hostile bytes
and that authorization must occur before byte or metadata disclosure.

**Required closure:** Remove the Batch-only predicate from Culvert. In
`download_batch_with_subpath`, compute the relative resolved path after the
allowed-root check and require `can_access_batch_sensitive_vector` when it is
sensitive. Add endpoint tests for direct and symlink-aliased Batch evidence for
anonymous/public, ordinary authenticated, authorized member, and root callers,
plus a Culvert download regression test proving no vector-specific Batch logic
executes there.

### VUN-CODE-02 — Medium — Deep GeoJSON nesting escapes the error contract and terminal retention cleanup

**Locations:**

- `wepppy/microservices/vector_upload_normalization.py:518-553`
  (`validate_feature_collection_geometries`)
- `wepppy/microservices/vector_upload_normalization.py:889-896,916-953`
  (`prepare_vector_upload`)

Coordinate validation recursively calls `coordinates()` with no nesting bound.
Both strict JSON decoding and coordinate traversal can raise `RecursionError`,
but the validation translation and outer cleanup boundaries catch only
`OSError`, `TypeError`, and `ValueError` (plus the explicit
`VectorUploadError`). A direct probe with a 1,200-level Polygon coordinate list
raised `RecursionError: maximum recursion depth exceeded`.

At the endpoint this becomes an uncontracted 500 rather than stable
`invalid_vector`. When it occurs after the original and working receipt are
written, it also bypasses the quarantined terminal receipt, exact ledger commit,
and lease release paths. This is a hostile-input resource/accounting defect, not
only an error-message discrepancy.

**Required closure:** Use an iterative traversal with an explicit nesting bound,
or translate `RecursionError` at the smallest parsing/validation boundary while
still enforcing a documented depth cap. Test deeply nested direct GeoJSON and
assert a stable 400 error, terminal quarantined receipt, released lease/final
accounting, and unchanged prior accepted resource.

### VUN-CODE-03 — Medium — Roads and AgFields do not roll back accepted files after publication-stage failure

**Locations:**

- `wepppy/weppcloud/routes/nodb_api/roads_bp.py:355-400`
- `wepppy/nodb/mods/roads/roads.py:1156-1197`
- `wepppy/nodb/mods/ag_fields/ag_fields.py:269-309`
- `wepppy/microservices/vector_upload_normalization.py:703-743`
  (`PreparedVectorUpload.publish`)

Roads copies the new candidate over `roads.uploaded.geojson` at line 1159 before
building the attribute catalog, acquiring the NoDb lock, updating state, or
writing the completion log. Any later exception leaves new canonical bytes at
the old state path while durable state and its digest can still describe the
previous upload.

AgFields stages both outputs, but inside the lock it replaces
`fields.WGS.geojson` and then `rotation_schedule.parquet` at lines 292-293. If
the second replace or subsequent state persistence fails, publication is
partial. NoDb state recovery cannot restore either overwritten file.

`PreparedVectorUpload.publish` makes the attempt terminal on mutation failure,
but it has no workflow-specific rollback callback. Batch implements an explicit
backup/restore path and Omni publishes into a new UUID path; Roads and AgFields
do not have equivalent failed-replacement safety. This contradicts the explicit
acceptance rule that failed attempts never replace a prior accepted resource.

**Required closure:** Add reversible publication for Roads and grouped rollback
for the AgFields GeoJSON/Parquet pair, coordinated with the mutation lock and
state persistence. Inject failures after the first filesystem replacement and
during persistence/logging; assert prior file hashes, state, reload behavior,
and downstream reads all remain on the previously accepted resource.

### VUN-CODE-04 — Medium — Browser-session uploads lose verified human provenance

**Locations:**

- `wepppy/microservices/rq_engine/session_routes.py:1038-1047,1088-1105`
- `wepppy/microservices/rq_engine/auth.py:128-152`
- `wepppy/microservices/rq_engine/ag_fields_routes.py:173-187`
- `wepppy/microservices/rq_engine/omni_routes.py:209-223`
- `wepppy/microservices/rq_engine/upload_batch_runner_routes.py:131-144`

Session tokens are issued with a verified `feature_access_principal` and, for an
authenticated human, `user_id`. `_sanitize_auth_actor` discards both for
`token_class == "session"` and retains only `session_id`. AgFields and Omni then
map that sanitized session actor to `unattributed`; Batch reads raw claims but
also has no session/principal branch and reaches the same result.

Consequently the common browser workflow records hostile upload receipts and
security events without the verified account ID and charges actor-scoped
retention to the unattributed bucket. That defeats the approved investigation
and potential account-enforcement use case even though a stable verified human
principal was available. The session identifier itself must not be persisted,
but that does not require discarding the verified human account ID.

**Required closure:** Derive `RetentionActor("human", id)` from a signed,
positive human `feature_access_principal` (or the verified session `user_id`)
without copying the session ID, roles, or raw claims into evidence. Add actual
session-token tests for AgFields, Omni run/dry-run, and Batch and assert that
receipts/events contain only the permitted stable actor fields.

### VUN-CODE-05 — Medium — Required format-equivalence and artifact-readback coverage is incomplete

**Locations:**

- `tests/weppcloud/routes/test_roads_bp.py:404-471`
- `tests/microservices/test_rq_engine_ag_fields_routes.py:267-381`
- `tests/microservices/test_rq_engine_omni_routes.py:1240-1370`
- `tests/microservices/test_rq_engine_upload_batch_runner_routes.py:150-415`
- `docs/schemas/vector-upload-normalization-contract.md`, “Acceptance gate”

The focused route tests prove direct GeoJSON in several workflows and one
mocked binary branch in some workflows (Roads/AgFields GeoParquet and Batch ZIP).
Omni has no binary-format receiving test. Roads and AgFields do not exercise ZIP,
Batch does not exercise GeoParquet, and `.geoparquet` alias coverage is absent at
these receiving boundaries. The converter responses are mocked, so these tests
also do not prove format-equivalent canonical geometry or actual downstream
artifact readback.

The governing acceptance gate requires every supported format through each
actual receiving boundary, state reload, and parsed downstream artifacts; it
explicitly says mocks and file existence are insufficient. The current tests
therefore cannot detect workflow-specific field-name, CRS, geometry, parser
selection, or reload divergence across formats.

**Required closure:** Run a shared semantic fixture as direct GeoJSON,
Shapefile ZIP, `.parquet`, and `.geoparquet` through Roads, AgFields, Omni run
and dry-run, and Batch. Use the qualified converter rather than a fabricated
response, reload the workflow controller, and parse/compare the workflow's next
artifact (not merely its existence or successful job status). Retain failed
replacement checks for every workflow.

## Reviewed areas without a finding

- AgFields, Omni, and Batch move synchronous normalization work off the async
  event loop in the reviewed route paths; Roads remains a synchronous Flask
  route. No additional async-blocking defect was found in those integrations.
- Batch has an explicit accepted-file backup/restore path, and Omni stages new
  accepted uploads beneath a new UUID directory before selecting them.
- Original uploads use exclusive, no-follow, mode-`0600` creation and verified
  SHA-256 readback before the receipt advances to `source_stored`.

## Residual risk

This review did not qualify the container image, exercise Redis/NoDb under real
service identities, or run the complete test suite. Those are separate M2/M5
evidence gates. Even after the source findings close, exact-image integration,
production-equivalent mount/identity behavior, and parsed downstream artifact
evidence remain required before acceptance. Publication and deployment remain
outside this work package's execution authority.
