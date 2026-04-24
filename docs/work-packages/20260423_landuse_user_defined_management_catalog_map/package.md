# Landuse User-Defined Management Catalog + Mapping Editor

**Status**: Complete (2026-04-24)
**Timezone**: UTC

## Overview
This package adds a run-scoped user-defined management catalog and a companion landuse mapping editor so users can upload `.man` files (single or zipped), manage descriptions, and assign management files to landuse keys/disturbed classes from dedicated PowerUser pages. The resulting mapping must persist inside the run `landuse/` tree, be preferred by the `Landuse` NoDb controller, and drive both single-OFE and multi-OFE prep paths with robust multi-year management expansion.

## Investigation Summary
Feasibility is confirmed with existing repository surfaces:
- `wepppy/weppcloud/templates/controls/poweruser_panel.htm` already hosts the PowerUser Actions list and can add links for two new pages.
- `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py` + `wepppy/weppcloud/templates/controls/edit_csv.htm` provide a proven editable-table pattern with snapshot endpoints and optimistic concurrency (`X-If-Match-Sha256`).
- `wepppy/microservices/shape_converter/archive_validation.py` provides hardened ZIP validation/extraction suitable for `.zip` ingestion with a custom `.man` member policy.
- `wepppy/microservices/upload_boundary.py` and `wepppy/microservices/rq_engine/upload_helpers.py` provide canonical non-archive upload guardrails.
- `wepppy/nodb/core/landuse.py` and `wepppy/wepp/management/managements.py` already support `ManagementDir`/`SoilFile` metadata on management map entries and are the right integration seam for run-local mapping preference.
- Multi-year repetition is already canonical in both single and multi-OFE prep via `Management.build_multiple_year_man(...)` in `wepppy/nodb/core/wepp_prep_service.py` and `wepppy/nodb/core/wepp.py`.

## Objectives
- Add a secured, run-scoped “Landuse User-Defined” catalog page for management files and metadata.
- Add a secured, run-scoped “Landuse Map” page for key/disturbed-class mapping edits.
- Support upload of individual `.man` files and `.zip` archives containing `.man` files only.
- Persist catalog assets under `landuse/user-defined/` and persist mapping overrides under `landuse/`.
- Ensure `Landuse` NoDb prefers the run-scoped mapping override over static built-in mapping when configured.
- Ensure management-to-soil association follows mapping changes deterministically.
- Preserve robust multi-year management behavior across single-OFE and multi-OFE execution paths.
- Keep UI consistent with Pure controls/tokens and theme accessibility expectations.

## Scope
This package covers end-to-end run-scoped management cataloging and mapping override workflows across WEPPcloud UI, Flask routes, rq-engine upload/mutation APIs, NoDb mapping resolution, and regression tests.

### Included
- New PowerUser links for:
  - `Landuse User-Defined` catalog page.
  - `Landuse Map` mapping editor page.
- New run-scoped route surfaces for listing/uploading/deleting/updating user-defined management catalog entries.
- ZIP + MAN validation contracts and hardened error handling aligned to canonical response schema.
- Run-scoped mapping override persistence in `landuse/` and NoDb preference logic.
- Mapping editor UX with readonly key/disturbedclass/description and editable `ManagementFile` selection.
- Soil association automation (`SoilFile`) tied to selected management metadata.
- Targeted tests across frontend/controller, Flask/rq-engine, and NoDb/RQ mutation paths.
- Documentation and package artifacts (tracker, ExecPlan, security review).

### Explicitly Out of Scope
- Global management catalog shared across runs.
- New WEPP management file format support beyond `.man`.
- Broad redesign of existing landuse build modes beyond this catalog/mapping workflow.
- Unrelated queue orchestration changes outside catalog/mapping operations.

## Stakeholders
- **Primary**: Landuse power users and modelers needing custom management files per run.
- **Reviewers**: WEPPcloud route/controller maintainers, NoDb/landuse maintainers, rq-engine maintainers.
- **Security Reviewer**: Required (upload + archive + file/path + mutation surfaces).
- **Informed**: Operators and QA maintainers.

## Success Criteria
- [x] PowerUser Actions include links to “Landuse User-Defined” and “Landuse Map”.
- [x] Users can upload one `.man` file or one `.zip` archive of `.man` files to `landuse/user-defined/` with strict validation.
- [x] Catalog page supports list/add/delete/description-edit with deterministic conflict behavior.
- [x] Mapping page supports editing ManagementFile assignments for each key/disturbed class and saving once.
- [x] Revised mapping persists in run `landuse/` and is preferred by `Landuse` NoDb for subsequent builds/prep.
- [x] Soil associations follow updated management mappings without manual soil remap steps.
- [x] Single-OFE and multi-OFE prep both honor custom management mappings and preserve multi-year management expansion.
- [x] New/updated tests pass and security review closes with no unresolved medium/high findings.

## Dependencies

### Prerequisites
- Existing staged mapping submit package closure:
  - [20260423_landuse_batched_mapping_submit](../20260423_landuse_batched_mapping_submit/package.md)
- Existing upload hardening patterns and archive validation utilities.

### Blocks
- Future landuse UX packages that depend on run-scoped custom mapping/catalog behavior.

## Related Packages
- **Related**: [20260423_landuse_batched_mapping_submit](../20260423_landuse_batched_mapping_submit/package.md)
- **Related**: [20260411_upload_endpoints_hardening](../20260411_upload_endpoints_hardening/package.md)
- **Follow-up**: optional package for cross-run reusable management libraries.

## Timeline Estimate
- **Expected duration**: 5-10 focused sessions.
- **Complexity**: High.
- **Risk level**: High.

## Security Impact and Review Gate
- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: introduces/extends untrusted file upload and archive ingestion surfaces, run-tree file writes, and mutation endpoints.
- **Security review artifact**: `docs/work-packages/20260423_landuse_user_defined_management_catalog_map/artifacts/2026-04-24_security_review.md`

## Implemented Contract Decisions
- **Upload payload shape and limits**:
  - Catalog upload route accepts either one `.man` or one `.zip` per request, not both.
  - Proposed caps: single `.man` <= 5 MiB; `.zip` compressed <= 50 MiB; extracted <= 250 MiB; member count <= 500.
- **ZIP member semantics**:
  - Accept `.man` entries only.
  - Reject encrypted/unsupported/traversal/absolute/duplicate members via shared archive validator.
  - All-or-nothing extraction/apply for archive imports.
- **Duplicate file semantics**:
  - Default reject on filename collision unless explicit replace flag is set.
  - Description updates are independent metadata mutations and must not rewrite file bytes.
- **Mapping save semantics**:
  - Full-table validation before write; reject on first invalid reference with no partial apply.
  - Optimistic concurrency via snapshot SHA.
- **NoDb preference semantics**:
  - If a run-scoped custom mapping file is configured, it is authoritative.
  - If configured mapping is missing/invalid, fail explicitly with a typed validation error (no silent fallback).
- **Backward compatibility**:
  - Existing built-in mapping selection flow remains unchanged when no run-scoped override is configured.

## Validation Summary
- `.venv/bin/pytest tests/wepp/management/test_management_map_loading.py tests/nodb/test_landuse_custom_mapping.py tests/microservices/test_rq_engine_landuse_routes.py tests/weppcloud/routes/test_landuse_bp.py tests/weppcloud/routes/test_pure_controls_render.py -q` (`86 passed`)
- `wctl doc-lint --path docs/work-packages/20260423_landuse_user_defined_management_catalog_map` (`5 files validated, 0 errors, 0 warnings`)
- `wctl check-rq-graph` (`RQ dependency graph artifacts are up to date`)
- `wctl run-pytest tests --maxfail=1` (environment blocked in this workspace; container run exited `137` shortly after startup)
- `.venv/bin/pytest tests --maxfail=1` (environment blocked in this workspace; collection failed because `SECRET_KEY`/`SECRET_KEY_FILE` is not configured)

## Required Validation Gates
- Frontend/controller tests for new pages and mapping editor interactions.
- Flask/rq-engine tests for auth, upload validation, archive policy, and catalog/mapping mutation contracts.
- NoDb/RQ tests for mapping preference, lock semantics, and multi-year prep behavior.
- `wctl check-rq-graph` if enqueue wiring changes.
- `wctl doc-lint --path docs/work-packages/20260423_landuse_user_defined_management_catalog_map`.

## References
- `wepppy/weppcloud/templates/controls/poweruser_panel.htm`
- `wepppy/weppcloud/routes/nodb_api/landuse_bp.py`
- `wepppy/weppcloud/routes/run_0/run_0_bp.py`
- `wepppy/weppcloud/templates/controls/edit_csv.htm`
- `wepppy/microservices/rq_engine/landuse_routes.py`
- `wepppy/microservices/upload_boundary.py`
- `wepppy/microservices/shape_converter/archive_validation.py`
- `wepppy/nodb/core/landuse.py`
- `wepppy/wepp/management/managements.py`
- `wepppy/nodb/core/wepp_prep_service.py`
- `wepppy/nodb/core/wepp.py`
- `docs/ui-docs/control-ui-styling/control-components.md`
- `docs/schemas/rq-response-contract.md`
- `docs/schemas/weppcloud-csrf-contract.md`

## Deliverables
- New package docs + ExecPlan + security artifact.
- Implemented run-scoped catalog and mapping pages (PowerUser-linked).
- Hardened upload/mapping endpoints with explicit contracts.
- Landuse NoDb custom mapping preference implementation.
- Regression tests for upload validation, mapping persistence, and prep behavior.

## Kickoff Prompt
- Completed ExecPlan: `docs/work-packages/20260423_landuse_user_defined_management_catalog_map/prompts/completed/landuse_user_defined_management_catalog_map_execplan.md`
