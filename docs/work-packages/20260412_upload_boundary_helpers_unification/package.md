# Upload Boundary Helpers Unification

**Status**: Complete (2026-04-12 16:39 UTC)
**Timezone**: UTC (all timestamps in this package use UTC)

## Overview
This package standardizes upload boundary handling across rq-engine and WEPPcloud upload surfaces by consolidating duplicated non-ZIP helper logic into shared canonical helpers. The goal is consistent size/type enforcement, filename normalization, and error semantics across routes while preserving current endpoint contracts.

## Objectives
- Define a single canonical non-ZIP upload boundary helper layer for route-level file ingestion.
- Migrate duplicated helper implementations in upload-capable routes to the canonical layer.
- Preserve current endpoint-specific caps, extension allowlists, and canonical response contracts.
- Keep ZIP archive handling canonical in `wepppy/microservices/shape_converter/archive_validation.py`.
- Expand regression coverage for helper-level and route-level parity across migrated endpoints.

## Scope
This package is focused on implementation and adoption of shared upload boundary helpers for non-ZIP uploads and consistency hardening across currently divergent route implementations.

### Included
- Inventory and classification of upload endpoints in:
  - `wepppy/microservices/rq_engine/*_routes.py`
  - `wepppy/weppcloud/routes/nodb_api/roads_bp.py`
- Canonical helper design and implementation for non-ZIP file uploads (filename, extension, size, save semantics, status mapping).
- Route migrations for currently duplicated helper paths, including:
  - `wepppy/microservices/rq_engine/ash_routes.py`
  - `wepppy/microservices/rq_engine/omni_routes.py`
  - `wepppy/weppcloud/routes/nodb_api/roads_bp.py`
- Parity updates in existing helper consumers where needed for consistency:
  - `wepppy/microservices/rq_engine/upload_helpers.py`
  - `wepppy/microservices/rq_engine/upload_*_routes.py` and mixed upload routes as applicable.
- Tests for helper behavior and endpoint regression parity.
- Documentation updates for upload contracts and helper usage.

### Explicitly Out of Scope
- Changes to `shape_converter` endpoint behavior.
- New upload capabilities or new accepted file types.
- Contract-breaking changes to endpoint payload shapes or auth requirements.
- Queue wiring, run orchestration, and non-upload business semantics.

## Stakeholders
- **Primary**: rq-engine and WEPPcloud maintainers for upload routes.
- **Reviewers**: maintainers of ash/omni/roads and upload contract docs.
- **Security Reviewer**: required (untrusted upload boundary changes).
- **Informed**: operators and automation agents consuming upload endpoints.

## Success Criteria
- [x] Canonical non-ZIP upload boundary helper(s) are implemented and documented.
- [x] `ash_routes.py`, `omni_routes.py`, and `roads_bp.py` no longer carry duplicated ad-hoc upload boundary implementations.
- [x] Endpoint caps/allowlists in `docs/schemas/upload-endpoint-contract.md` remain accurate and enforced after migration.
- [x] ZIP handling remains canonical in `wepppy/microservices/shape_converter/archive_validation.py` and culvert semantic validation stays in `wepppy/microservices/culvert_payload_validator.py`.
- [x] Route-level regression tests pass for migrated endpoints plus targeted helper tests.
- [x] Full gate `wctl run-pytest tests --maxfail=1` passes before closure.
- [x] Dedicated security review artifact has no unresolved medium/high findings at closeout.

## Dependencies

### Prerequisites
- Completed hardening baseline from `20260411_upload_endpoints_hardening`.
- Current upload contract inventory in `docs/schemas/upload-endpoint-contract.md`.

### Blocks
- Follow-on upload endpoint additions that depend on canonical helper adoption guidance.

## Related Packages
- **Depends on**: [20260411_upload_endpoints_hardening](../20260411_upload_endpoints_hardening/package.md)
- **Related**: [20260411_rq_operator_experience_hardening](../20260411_rq_operator_experience_hardening/package.md)
- **Follow-up**: optional package for broader Flask/FastAPI shared stream abstractions if needed after this migration.

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions.
- **Complexity**: Medium.
- **Risk level**: High.

## Security Impact and Review Gate
- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: modifies untrusted file ingestion boundaries and shared validation logic used by multiple upload endpoints.
- **Security review artifact**: `docs/work-packages/20260412_upload_boundary_helpers_unification/artifacts/2026-04-12_security_review.md`

## Required Validation Gates

### Upload Helper Consistency Gate
- Add helper-level tests for filename sanitization, extension allowlists, byte-cap enforcement, overwrite behavior, and cleanup-on-failure semantics.
- Verify consistent 400 vs 413 status behavior where size limits are exceeded.

### Route Migration Gate
- Run targeted suites for migrated routes (`ash`, `omni`, `roads`, and affected rq-engine upload routes).
- Confirm no endpoint contract drift in success/error payload structure.

### Maintainer Gate
- `wctl run-pytest` on touched route modules.
- `wctl run-pytest tests --maxfail=1` before closure.
- `wctl doc-lint` on changed docs (`package`, `tracker`, active ExecPlan, security artifact, `PROJECT_TRACKER.md`, and any contract docs).

### Security Gate
- Complete dedicated security artifact using `docs/prompt_templates/security_review_template.md`.
- Resolve all medium/high findings before package closure.

## References
- `docs/schemas/upload-endpoint-contract.md`
- `wepppy/microservices/rq_engine/upload_helpers.py`
- `wepppy/microservices/rq_engine/ash_routes.py`
- `wepppy/microservices/rq_engine/omni_routes.py`
- `wepppy/weppcloud/routes/nodb_api/roads_bp.py`
- `wepppy/microservices/shape_converter/archive_validation.py`
- `wepppy/microservices/culvert_payload_validator.py`
- `docs/prompt_templates/codex_exec_plans.md`

## Deliverables
- Unified non-ZIP upload boundary helper implementation.
- Migrated route implementations using canonical helper APIs.
- Expanded helper + route regression tests.
- Updated upload contract and package documentation.

## Closure Summary
- 2026-04-12 16:35 UTC: Implemented shared non-ZIP upload boundary helpers in `wepppy/microservices/upload_boundary.py` and migrated `ash_routes.py`, `omni_routes.py`, `upload_helpers.py`, and `roads_bp.py` to use canonical helper paths.
- 2026-04-12 16:35 UTC: Validation gates passed:
  - Targeted upload suites: `137 passed`.
  - Full suite: `3511 passed`, `36 skipped`.
- 2026-04-12 16:39 UTC: Docs gate passed (`wctl doc-lint` on package/tracker/ExecPlan/security artifact/upload contract/PROJECT_TRACKER).
- 2026-04-12 16:35 UTC: Dedicated security review gate closed with no unresolved medium/high findings.

## Kickoff Prompt
- Active ExecPlan: `docs/work-packages/20260412_upload_boundary_helpers_unification/prompts/active/upload_boundary_helpers_unification_execplan.md`
