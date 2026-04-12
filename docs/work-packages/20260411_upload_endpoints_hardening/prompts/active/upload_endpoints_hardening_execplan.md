# Upload Endpoints Hardening and ZIP Ingestion Consolidation

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, non-`shape_converter` upload endpoints in WEPPpy will reject dangerous or oversized uploads before they are written/extracted, and culvert ZIP ingestion will use the same hardened archive controls already validated in `shape_converter`. Operators will get deterministic, contract-compliant validation errors with stable `error.code` + `error_id`, and exception-driven failures will be correlated to server-side traceback logs by the same `error_id`.

Observable behavior changes:
- Culvert ZIP uploads reject traversal/symlink/encrypted/nested/unsupported-compression abuse fixtures before extraction.
- Upload endpoints that currently allow unbounded writes enforce explicit size caps and extension allowlists.
- Upload failures return canonical error payloads with specific `error.message`, populated `error.details`, stable `error.code`, and `error_id` (traceback payloads MAY be present per contract).

## Progress

- [x] (2026-04-12 06:06Z) Created work-package scaffold and activated this ExecPlan.
- [x] (2026-04-12 06:06Z) Captured user directive to reuse validated ZIP controls from `shape_converter` for culvert ingestion.
- [x] (2026-04-12 06:24Z) Implemented reusable archive hardening path for culvert ZIP ingestion based on `shape_converter/archive_validation.py`.
- [x] (2026-04-12 06:27Z) Hardened non-archive upload endpoints with explicit pre-write size/type controls.
- [x] (2026-04-12 06:27Z) Removed traceback leakage from upload-facing error responses while preserving canonical contracts.
- [x] (2026-04-12 06:27Z) Added regression tests for archive abuse fixtures and endpoint-specific upload limits.
- [x] (2026-04-12 06:34Z) Completed security review artifact and closure validation gates.
- [x] (2026-04-12 06:37Z) Completed doc-lint closure gate and final package documentation updates.
- [x] (2026-04-12 18:32Z) Executed follow-up findings A-E closure across rq-engine + roads upload surfaces.
- [x] (2026-04-12 18:35Z) Hardened shared upload response/helpers so upload-facing failures consistently emit `error.message`, `error.details`, `error.code`, and `error_id`.
- [x] (2026-04-12 18:53Z) Added regression checks for `error_id`/code/details envelope fields and traceback/error-id log correlation.
- [x] (2026-04-12 19:01Z) Re-ran full suite gate after helper updates (`3524 passed`, `36 skipped`).
- [x] (2026-04-12 19:06Z) Re-ran docs lint on package/security/schema artifacts after follow-up edits (`6 files validated`, `0 errors`, `0 warnings`).

## Surprises & Discoveries

- Observation: The user-referenced path `wepppy/microservices/shape_converter/src/archive.py` does not exist in the current tree; validated ZIP controls live in `wepppy/microservices/shape_converter/archive_validation.py`.
  Evidence: repository listing and file reads on 2026-04-12.
- Observation: Current culvert ingest still uses `zipfile.extractall` after limited validation.
  Evidence: `wepppy/microservices/rq_engine/culvert_routes.py`.
- Observation: `shape_converter` archive validation includes shapefile-only extension policy and sidecar sanitization, so culvert adoption required parameterized policy hooks while preserving existing shape_converter defaults.
  Evidence: `wepppy/microservices/shape_converter/archive_validation.py` and culvert route integration diff.
- Observation: Roads upload validation helpers returned HTTP 200 by default for validation failures via `error_factory` unless status was explicitly set.
  Evidence: `wepppy/weppcloud/routes/nodb_api/roads_bp.py` upload route behavior before hardening.
- Observation: Enforcing top-level `error_id` in shared rq-engine error helpers exposed one brittle exact-equality test in fork routes that assumed no additional top-level keys.
  Evidence: initial full-suite failure in `tests/microservices/test_rq_engine_fork_archive_routes.py::test_fork_rejects_non_string_target_runid`, then fixed by asserting contract fields explicitly.

## Decision Log

- Decision: Reuse/adapt `shape_converter` archive-validation logic for culvert ZIP ingestion rather than adding a third independent ZIP validator.
  Rationale: Minimizes drift and reuses already validated controls.
  Date/Author: 2026-04-12 / Codex.
- Decision: Keep culvert semantic payload validation (`required files`, metadata consistency) in `culvert_payload_validator.py`; use shared ZIP logic strictly for archive safety controls.
  Rationale: Separation keeps archive hardening generic while preserving culvert business validation behavior.
  Date/Author: 2026-04-12 / Codex.
- Decision: Parameterize `shape_converter` archive validation with optional member-policy and sidecar-sanitization controls rather than duplicating ZIP-safety code into rq-engine.
  Rationale: Reuses validated safety path directly and avoids a divergent third archive validator.
  Date/Author: 2026-04-12 / Codex.
- Decision: Return explicit `413` for size/quota violations and `400` for type/validation failures across hardened upload endpoints.
  Rationale: Preserves canonical response shape while improving error-class clarity for clients and operators.
  Date/Author: 2026-04-12 / Codex.
- Decision: Implement upload error envelope + traceback correlation at shared helper boundaries (`responses.py`, `upload_helpers.py`, `weppcloud/utils/helpers.py`) and patch only route outliers.
  Rationale: Ensures consistency across upload surfaces while minimizing route-by-route drift.
  Date/Author: 2026-04-12 / Codex.

## Outcomes & Retrospective

- Completed all scoped hardening milestones and security findings closure.
- Culvert ZIP ingestion now uses shared validated archive controls (read with limit, safe member validation, controlled extraction) and no longer calls `extractall`.
- Scoped non-shape_converter upload endpoints now enforce explicit pre-write max-byte controls and extension/type allowlists.
- Upload-facing error payloads for scoped endpoints now return canonical envelopes with required upload contract fields (`error.message`, `error.details`, `error.code`, `error_id`).
- Exception-driven upload failures now emit server-side traceback logs correlated to API responses via matching `error_id`.
- Regression coverage now includes culvert ZIP abuse fixtures (traversal, encrypted, nested, unsupported compression, duplicate path, quota) plus per-endpoint size/type validations.
- Validation gates completed:
  - Targeted scoped suites: `120 passed`
  - Full closure suite: `3524 passed`, `36 skipped`
  - Docs lint closure gate: `6 files validated`, `0 errors`, `0 warnings`

## Context and Orientation

Primary upload surfaces in scope:
- ZIP archive ingestion:
  - `wepppy/microservices/rq_engine/culvert_routes.py`
  - `wepppy/microservices/culvert_payload_validator.py`
- File uploads with identified hardening gaps:
  - `wepppy/microservices/rq_engine/upload_huc_fire_routes.py`
  - `wepppy/microservices/rq_engine/upload_batch_runner_routes.py`
  - `wepppy/microservices/rq_engine/landuse_routes.py`
  - `wepppy/microservices/rq_engine/treatments_routes.py`
  - `wepppy/microservices/rq_engine/upload_disturbed_routes.py`
  - `wepppy/weppcloud/routes/nodb_api/roads_bp.py`
- Upload error response boundary:
  - `wepppy/microservices/rq_engine/responses.py`

Validated ZIP implementation to reuse:
- `wepppy/microservices/shape_converter/archive_validation.py`
  - `read_upload_bytes_with_limit`
  - `validate_and_extract_zip_archive`
  - member path/safety validation helpers.

Key finding classes to close:
- Archive abuse and extraction safety gaps.
- Unbounded upload write paths.
- Missing/empty extension allowlists.
- Inconsistent upload error envelope fields (`error.code`, `error.details`, `error_id`) and missing traceback/error-id observability correlation.

## Plan of Work

Milestone 1 (Archive hardening reuse for culvert ZIP):
- Introduce a reusable ZIP safety module for rq-engine culvert ingest by adapting `shape_converter` archive controls.
- Replace culvert route ZIP extraction path so it no longer uses unguarded `extractall` and enforces archive quotas/member policy before extraction.
- Preserve existing `validate_payload_root` semantics for culvert-required content.

Milestone 2 (Non-archive upload boundary hardening):
- Add explicit max-byte enforcement before write for `upload_huc_fire`, batch SBS upload, landuse/treatments user-defined uploads, and Roads upload path.
- Add explicit type/extension allowlists for endpoints currently accepting arbitrary files (including disturbed SBS route policy).

Milestone 3 (Error contract hardening):
- Enforce canonical upload error envelope requirements (`error.message`, `error.details`, `error.code`, `error_id`) while preserving specific user-visible reasons.
- Ensure exception-driven upload failures log full traceback server-side with matching `error_id`; payload traceback inclusion remains optional (`MAY include traceback`) per contract.
- Add/adjust tests to verify envelope fields and traceback/error-id log correlation.

Milestone 4 (Validation and security closure):
- Add archive abuse regression fixtures and endpoint-specific size/extension tests.
- Run targeted suites then full `tests --maxfail=1`.
- Complete `artifacts/2026-04-12_security_review.md` and close medium/high findings.

## Concrete Steps

Run commands from `/workdir/wepppy`.

1. Implement culvert ZIP hardening reuse and tests:
   - `wctl run-pytest tests/microservices/test_rq_engine_culverts.py --maxfail=1`

2. Implement endpoint hardening for file upload routes and tests:
   - `wctl run-pytest tests/microservices/test_rq_engine_upload_huc_fire_routes.py tests/microservices/test_rq_engine_upload_batch_runner_routes.py tests/microservices/test_rq_engine_landuse_routes.py tests/microservices/test_rq_engine_treatments_routes.py tests/microservices/test_rq_engine_upload_disturbed_routes.py --maxfail=1`
   - `wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1`

3. Validate error-contract behavior and non-leakage:
   - `wctl run-pytest tests/microservices/test_rq_engine_*upload*.py tests/microservices/test_rq_engine_culverts.py --maxfail=1`

4. Full closure gate:
   - `wctl run-pytest tests --maxfail=1`
   - `wctl doc-lint --path docs/work-packages/20260411_upload_endpoints_hardening/package.md --path docs/work-packages/20260411_upload_endpoints_hardening/tracker.md --path docs/work-packages/20260411_upload_endpoints_hardening/prompts/active/upload_endpoints_hardening_execplan.md --path PROJECT_TRACKER.md`

## Validation and Acceptance

Acceptance is satisfied when:
- Culvert ZIP ingestion rejects traversal, encrypted, nested archive, unsupported compression, symlink/special entry, duplicate-path, and archive quota abuse fixtures.
- No scoped endpoint writes unbounded upload payloads.
- Extension/type policy is explicit and test-covered for each scoped route.
- Upload-facing error payloads are canonical and include required contract fields (`error.message`, `error.details`, `error.code`, `error_id`).
- Exception-driven upload failures emit traceback logs with a matching response `error_id`.
- Targeted tests and `wctl run-pytest tests --maxfail=1` pass.
- Security artifact reports no unresolved medium/high findings.

## Idempotence and Recovery

- Changes are additive and route-local; test commands are safe to rerun.
- If a milestone fails mid-way, revert only local incomplete edits in that route/module and rerun targeted tests before proceeding.
- Keep archive-policy extraction modular so individual routes can adopt/revert with minimal blast radius.

## Artifacts and Notes

- Security review output: `docs/work-packages/20260411_upload_endpoints_hardening/artifacts/2026-04-12_security_review.md`.
- Validation evidence and any residual-risk acceptance notes will be logged in `tracker.md` before closure.

## Interfaces and Dependencies

Interfaces expected after implementation:
- Culvert ZIP ingest path calls a hardened archive validator/extractor derived from `shape_converter` controls.
- Upload routes expose explicit max-byte and extension validation behavior with canonical error responses.
- Error response boundary preserves canonical upload contract shape and emits traceback/error-id correlation for exception-driven failures.

Dependencies:
- Existing tests under `tests/microservices/` and `tests/weppcloud/routes/`.
- Existing culvert semantic validation in `wepppy/microservices/culvert_payload_validator.py`.

---
Revision Note (2026-04-12 / Codex): Initial active ExecPlan authored at package kickoff, explicitly aligned to upload vulnerability findings and the directive to reuse validated `shape_converter` ZIP controls.
Revision Note (2026-04-12 19:02Z / Codex): Updated the living plan for follow-up findings A-E closure, including helper-level envelope/correlation hardening, new regression evidence, and updated validation counts.
Revision Note (2026-04-12 19:06Z / Codex): Recorded final follow-up docs-lint evidence for package + schema artifacts.
