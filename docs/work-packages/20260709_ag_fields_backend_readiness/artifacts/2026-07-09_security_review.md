# Security Review - AgFields Backend Readiness

## Metadata

- **Package**: `docs/work-packages/20260709_ag_fields_backend_readiness/`
- **Reviewer**: Codex
- **Date**: 2026-07-09
- **Scope reviewed**: AgFields controller, RQ worker tasks, authenticated rq-engine routes, uploads, artifact serving, single-flight queue admission, and queue registration
- **Commit/branch context**: `master` working tree
- **Related decision**: `docs/adrs/ADR-0015-agfields-upload-archive-guardrails.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: The package adds upload/file-processing endpoints and queue wiring, both high-impact surfaces under the work-package policy.
- **Threat model assumptions**:
  - Every route is run-scoped and authorizes the bearer token against the requested run.
  - Uploaded GeoJSON and ZIP content is untrusted and must remain inside `<wd>/ag_fields/`.
  - RQ workers receive validated run identifiers, bounded numeric options, and server-created upload filenames.
  - Callers with legitimate access to one run must not mutate another run or overlap incompatible AgFields jobs within their run.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Medium | Boundary upload | Renaming before extension enforcement allowed a `.txt` upload to acquire a `.geojson` destination name. | Route regression initially returned 200 for `.txt`. | Preserve the sanitized raw suffix through shared extension enforcement. | Resolved |
| SEC-02 | Medium | Boundary persistence | Invalid re-upload could replace canonical GeoJSON before validation failed, leaving prior NoDb state inconsistent with disk. | `test_invalid_boundary_reupload_preserves_canonical_artifacts_and_state`. | Stage GeoJSON and Parquet; replace both under the NoDb lock only after validation. | Resolved |
| SEC-03 | Medium | Queue/data integrity | Concurrent AgFields jobs or synchronous mutations could overlap filesystem phases outside the NoDb lock. | Single-flight and sync-conflict route tests. | Add run-scoped submit lock, live RQ status checks, and HTTP 409 for conflicting mutations. | Resolved |
| SEC-04 | Low | Worker error logging | `filename`/`message` in `LogRecord.extra` masked the original task exception. | Initial RQ failure tests raised `KeyError`. | Use non-reserved log-context keys while preserving terminal JSON field names. | Resolved |
| SEC-05 | Low | Plant ZIP processing | `archive.read()` loaded each expanded member into memory at once. | Diff review of controller extraction loop. | Stream members in 64 KiB chunks after shared archive quota validation. | Resolved |
| SEC-06 | Low | Staged uploads | Unique server-staged plant ZIPs could accumulate after workers completed or failed. | RQ task cleanup path and upload contract. | Remove the staged archive in the worker `finally` block with path containment. | Resolved |
| SEC-07 | Low | API contract | The 13-route surface exceeded the canonical OpenAPI size budget. | Full-suite failure: `129,217 > 118,500`. | Retain route discoverability and document a narrow 130,000-byte ceiling in the canonical contract and ADR-0015. | Resolved |

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Release recommendation**: ship

## Surface Checks

### Auth, Input, and Run Boundaries

- [x] All 13 route shapes call `require_jwt` and `authorize_run_access`; mutations require `rq:enqueue`, reads require `rq:status`.
- [x] Boundary uploads use the shared non-ZIP helper with raw extension enforcement and a 10 MB limit.
- [x] Plant ZIPs use shared signature/path/compression/quota validation: 100 MB compressed, 600 MB uncompressed, 200 members, `.man` only.
- [x] Controller extraction retains zip-slip guards and streams members; mapping/delete inputs accept basenames only.
- [x] Overlay serving resolves one fixed controller-owned path; no user path is joined into the response path.
- [x] Canonical errors include code/details/error id; terminal worker failures name only workflow identifiers and messages.

### Queue, Locking, and Data Integrity

- [x] RQ inputs are validated before filesystem/WEPP execution and each worker clears only `ag_fields.nodb` immediately before mutable hydration.
- [x] A 30-second run-scoped submit lock closes enqueue races; active queued/started/deferred/scheduled jobs block other jobs and synchronous mutations.
- [x] Boundary/schema/mapping/plant inventory mutations preserve NoDb lock/dump behavior and atomic replacement where required.
- [x] Queue graph artifacts and analyst-maintained job catalog entries describe all three job families.
- [x] Worker exceptions are logged, published as `EXCEPTION_JSON`, and re-raised; no error is swallowed.

### Other Surfaces

- [x] No secrets, token values, new outbound calls, shell interpolation, unsafe deserialization, third-party dependencies, CI permissions, or service mounts were added.
- [x] No frontend/session/CSRF surface changed; the successor browser client will use existing rq-engine session bearer tokens.
- [x] No agent/MCP permission or network-egress surface changed.

## Validation Evidence

- `wctl run-pytest tests/nodb/mods/` -> `748 passed, 23 skipped`.
- Final targeted controller/RQ/route set -> `52 passed`.
- `wctl run-stubtest wepppy.rq.ag_fields_rq` -> success.
- `wctl check-test-stubs` -> all stubs complete.
- `python tools/check_broad_exceptions.py --enforce-changed` with new production files included -> pass, net delta `-4`.
- `wctl check-rq-graph` -> graph artifacts up to date after regeneration.
- Live Redis job-tree check: each new RQ entrypoint resolved as one queued root with `runid=agfields-tree-check`; temporary jobs were deleted afterward.
- Full `wctl run-pytest tests --maxfail=1` -> stopped at the unrelated `tests/nodb/test_batch_runner.py::test_run_batch_project_does_not_delete_workspace_when_rmtree_disabled` baseline failure after `2070 passed, 41 skipped, 35 warnings in 300.01s`; the failure reproduced alone and no implicated file is changed by this package.

## Residual Risk

- Authenticated users can submit repeated sequential heavy jobs; single-flight prevents overlap but is not a general rate limiter. This matches existing rq-engine policy and remains observable through job metadata/status channels.
- Canonical upload limits may reject unusually large legitimate datasets. ADR-0015 defines the review signals and change process.
- No generated-output run against a real WEPP binary was executed; regression coverage proves configured-binary propagation through the `run_hillslope` boundary with generated `.run/.man/.slp` artifacts.

## Sign-off

- **Security reviewer**: Codex, 2026-07-09
- **Package implementer/owner**: Codex, 2026-07-09
