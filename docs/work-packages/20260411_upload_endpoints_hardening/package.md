# Upload Endpoints Hardening

**Status**: Complete (2026-04-12 19:06 UTC)
**Timezone**: UTC (all timestamps in this package use UTC)

## Overview
This package hardens non-`shape_converter` upload endpoints in WEPPpy so archive and file uploads are validated before storage/extraction and enforce explicit resource/safety limits. The package disposes the vulnerability findings from the upload review and standardizes upload boundary behavior across rq-engine and WEPPcloud Roads upload surfaces.

## Objectives
- Reuse the validated ZIP validation/extraction implementation from `wepppy/microservices/shape_converter/archive_validation.py` for culvert ZIP ingestion.
- Eliminate unbounded upload writes in non-archive endpoints by enforcing explicit size caps before disk write.
- Enforce extension/type allowlists consistently across upload endpoints.
- Enforce canonical upload error envelopes (`error.message`, `error.details`, `error.code`, `error_id`) with specific user-visible reasons.
- Correlate exception-driven traceback logging to API responses via shared `error_id`, while keeping traceback payload behavior contract-compliant (`MAY` include traceback).
- Add regression coverage for traversal, archive abuse cases, and per-endpoint upload limits.

## Scope
This package covers upload boundary hardening for rq-engine and WEPPcloud upload routes, with explicit priority on ZIP ingestion safety and size/type validation parity.

### Included
- `wepppy/microservices/rq_engine/culvert_routes.py` ZIP ingest hardening.
- Extraction/reuse of archive validation logic from `wepppy/microservices/shape_converter/archive_validation.py` and `read_upload_bytes_with_limit` semantics.
- Endpoint hardening for:
  - `wepppy/microservices/rq_engine/upload_climate_routes.py`
  - `wepppy/microservices/rq_engine/upload_huc_fire_routes.py`
  - `wepppy/microservices/rq_engine/upload_batch_runner_routes.py`
  - `wepppy/microservices/rq_engine/landuse_routes.py`
  - `wepppy/microservices/rq_engine/treatments_routes.py`
  - `wepppy/microservices/rq_engine/upload_disturbed_routes.py`
  - `wepppy/microservices/rq_engine/watershed_routes.py` (`upload-dem`)
  - `wepppy/weppcloud/routes/nodb_api/roads_bp.py`
- Upload error contract hardening in `wepppy/microservices/rq_engine/responses.py`, `wepppy/microservices/rq_engine/upload_helpers.py`, and `wepppy/weppcloud/utils/helpers.py`.
- Targeted and suite-level tests under `tests/microservices/` and `tests/weppcloud/routes/`.
- Documentation updates for upload limits and validation behavior where contracts are user-visible.

### Explicitly Out of Scope
- Behavior changes inside `wepppy/microservices/shape_converter/` endpoint contracts themselves.
- New upload formats or functional features unrelated to hardening.
- Frontend UX redesign outside minimal messaging needed to reflect hardened validation errors.

## Stakeholders
- **Primary**: rq-engine and WEPPcloud maintainers responsible for upload route reliability and security.
- **Reviewers**: maintainers of culvert batch ingestion and run-scoped upload routes.
- **Security Reviewer**: required (public route upload and archive handling attack surfaces).
- **Informed**: operators and agent workflows relying on upload endpoints.

## Success Criteria
- [x] Culvert ZIP ingestion uses the hardened validation/extraction pipeline derived from `shape_converter` validated code.
- [x] ZIP traversal, encrypted-entry, nested-archive, unsupported-compression, duplicate-path, and quota abuse fixtures are rejected with explicit contract-compliant errors.
- [x] `upload_huc_fire`, batch SBS upload, landuse/treatments user-defined uploads, and Roads upload enforce explicit pre-write max-byte controls.
- [x] Disturbed SBS upload no longer allows arbitrary file extensions.
- [x] Upload-facing error payloads include specific `error.message`, populated `error.details`, stable `error.code`, and `error_id`.
- [x] Exception-driven upload failures log full traceback server-side with the same `error_id` returned to callers.
- [x] Targeted microservice/web route tests and `wctl run-pytest tests --maxfail=1` pass for merged changes.
- [x] Dedicated security review artifact is complete with no unresolved medium/high findings.

## Dependencies

### Prerequisites
- Findings inventory from the upload vulnerability review (2026-04-12).
- Validated ZIP hardening implementation in `wepppy/microservices/shape_converter/archive_validation.py`.

### Blocks
- Follow-on endpoint contract freeze work that assumes hardened upload behavior.

## Related Packages
- **Depends on**: none.
- **Related**: [20260411_rq_operator_experience_hardening](../20260411_rq_operator_experience_hardening/package.md) (adjacent API hardening effort).
- **Follow-up**: potential package for unified upload-boundary helper extraction if additional endpoints are discovered.

## Timeline Estimate
- **Expected duration**: 2-5 focused sessions.
- **Complexity**: High.
- **Risk level**: High.

## Security Impact and Review Gate
- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: includes archive extraction logic, untrusted upload boundary validation, and error leakage controls.
- **Security review artifact**: `docs/work-packages/20260411_upload_endpoints_hardening/artifacts/2026-04-12_security_review.md`

## Required Validation Gates

### Upload Hardening Gate
- Add/extend upload abuse tests for ZIP/member path safety and file-size rejection behavior.
- Verify per-endpoint extension allowlists and max-byte constraints are enforced before write/extract.

### Contract/Error Gate
- Verify upload rejection responses remain canonical (`error.message`, `error.details`, `error.code`, `error_id`) with specific reasons.
- Verify exception-driven upload failures emit traceback logs correlated by `error_id`.
- Verify status codes are explicit for validation/quota errors.

### Maintainer Gate
- `wctl run-pytest` on touched microservice and route test modules.
- `wctl run-pytest tests --maxfail=1` before closure.
- `wctl doc-lint` on changed docs.

### Security Gate
- Complete dedicated security artifact using `docs/prompt_templates/security_review_template.md`.
- Close all medium/high findings before package closure.

## References
- `wepppy/microservices/shape_converter/archive_validation.py`
- `wepppy/microservices/shape_converter/convert.py`
- `wepppy/microservices/rq_engine/culvert_routes.py`
- `wepppy/microservices/culvert_payload_validator.py`
- `wepppy/microservices/rq_engine/upload_huc_fire_routes.py`
- `wepppy/microservices/rq_engine/upload_batch_runner_routes.py`
- `wepppy/microservices/rq_engine/landuse_routes.py`
- `wepppy/microservices/rq_engine/treatments_routes.py`
- `wepppy/microservices/rq_engine/upload_disturbed_routes.py`
- `wepppy/weppcloud/routes/nodb_api/roads_bp.py`
- `wepppy/microservices/rq_engine/responses.py`
- `docs/prompt_templates/codex_exec_plans.md`

## Deliverables
- Hardened culvert ZIP ingestion implementation reusing shape_converter validated archive controls.
- Consistent size/type pre-write enforcement across scoped upload endpoints.
- Upload regression tests for abuse cases and endpoint-specific validation limits.
- Updated package docs, tracker evidence, and security review artifact.

## Kickoff Prompt
- Active ExecPlan: `docs/work-packages/20260411_upload_endpoints_hardening/prompts/active/upload_endpoints_hardening_execplan.md`
