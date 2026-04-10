# RQ Controller State Geospatial and Upload Metadata

**Status**: Complete (closed 2026-04-10 21:06 UTC)
**Timezone**: UTC (all dates/times in this package documentation use UTC unless explicitly stated otherwise).

## Overview
This package implements run-scoped geospatial metadata and upload-file contract metadata so agents can choose valid first-step watershed parameters and validate upload payloads before submit. It adds `/geospatial-metadata` and hardens upload operation metadata semantics for format, CRS, extent, resolution, value-class constraints, and upload size limits.

## Objectives
- Implement `GET /api/runs/{runid}/{config}/geospatial-metadata` with run-resolved coverage/default/context fields.
- Implement upload metadata contract fields for:
  - `rq_engine_upload_dem`
  - `rq_engine_upload_cli`
  - `rq_engine_upload_sbs`
  - `rq_engine_upload_cover_transform`
- Enforce contract-aligned file metadata semantics (content type, extension, size, CRS, extent coverage, resolution, and value semantics).
- Add/extend OpenAPI and route-level tests plus frozen artifact/checklist guards for all new/updated surfaces.

## Scope
This package delivers geospatial metadata route implementation, upload metadata payload hardening, and required tests/docs/checklist updates.

### Included
- Geospatial metadata route implementation under rq-engine:
  - `GET /api/runs/{runid}/{config}/geospatial-metadata`
- Upload operation descriptor/schema/default payload hardening for DEM/CLI/SBS/cover-transform operations.
- Live upload handler size-limit enforcement (`max_bytes`) and regression tests.
- Contract and route tests for auth, payload shape, parity across metadata surfaces, and geospatial/upload metadata semantics.
- Frozen artifact updates:
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

### Explicitly Out of Scope
- Operation error catalog, async progress, and `outputs` surfaces (`20260410_rq_controller_state_errors_progress_outputs`).
- Auth-concurrency/idempotency rollout enforcement (`20260410_rq_controller_state_auth_concurrency`).

## Stakeholders
- **Primary**: rq-engine maintainers and agent-interface implementers.
- **Reviewers**: API contract/schema maintainers.
- **Security Reviewer**: independent security subagent review required by package gate.
- **Informed**: downstream owners for roadmap packages 6-8.

## Success Criteria
- [x] `/api/runs/{runid}/{config}/geospatial-metadata` is implemented and exposed with contract-aligned fields.
- [x] Upload operation metadata for DEM/CLI/SBS/cover-transform includes machine-checkable file constraints.
- [x] Geospatial/upload metadata payloads are deterministic for equivalent run state.
- [x] Frozen endpoint inventory/checklist artifacts include new/updated geospatial/upload contract rows.
- [x] Required validation gates pass (code, QA, security, docs) with no unresolved medium/high findings.

## Dependencies

### Prerequisites
- `docs/work-packages/20260410_rq_controller_state_setup_discovery/` (complete)
- `docs/work-packages/20260410_rq_controller_state_schema_defaults/` (complete)
- Canonical route artifacts:
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

### Blocks
- `20260410_rq_controller_state_errors_progress_outputs`
- `20260410_rq_controller_state_contract_cutover`

## Related Packages
- **Depends on**:
  - [20260410_rq_controller_state_setup_discovery](../20260410_rq_controller_state_setup_discovery/package.md)
  - [20260410_rq_controller_state_schema_defaults](../20260410_rq_controller_state_schema_defaults/package.md)
- **Related**:
  - [20260410_rq_controller_state_orchestration_reads](../20260410_rq_controller_state_orchestration_reads/package.md)
  - [20260208_rq_engine_agent_usability](../20260208_rq_engine_agent_usability/package.md)
- **Follow-up**:
  - `20260410_rq_controller_state_errors_progress_outputs`
  - `20260410_rq_controller_state_auth_concurrency`

## Timeline Estimate
- **Expected duration**: 1-2 focused sessions
- **Complexity**: High
- **Risk level**: High

## Security Impact and Review Gate
- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: Upload metadata semantics and geospatial defaults influence file validation and route selection; disclosure and validation-contract boundaries must be reviewed explicitly.
- **Security review artifact**: `docs/work-packages/20260410_rq_controller_state_geospatial_uploads/artifacts/2026-04-10_security_review.md`

## Required Validation Gates

### Code Gate
- `wctl run-pytest tests/microservices/test_rq_engine_geospatial_upload_metadata_routes.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1`
- `python tools/check_endpoint_inventory.py`
- `python tools/check_route_contract_checklist.py`
- `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1`

### QA Gate
- Independent `reviewer` and `qa_reviewer` passes completed.
- Findings dispositioned in package tracker.
- No unresolved medium/high QA findings at handoff.

### Security Gate
- Security artifact completed and reviewed by `security_reviewer`.
- Auth/scope/session, upload metadata disclosure, and validation-contract implications reviewed.
- No unresolved medium/high security findings at handoff.

### Docs Gate
- `wctl doc-lint` run on changed schema/package/tracker/prompt/security docs and `PROJECT_TRACKER.md`.

## References
- `docs/schemas/rq-controller-state-contract.md`
- `docs/schemas/rq-engine-agent-api-contract.md`
- `docs/work-packages/README.md`
- `docs/prompt_templates/codex_exec_plans.md`
- `docs/prompt_templates/security_review_template.md`
- `wepppy/microservices/rq_engine/AGENTS.md`
- `PROJECT_TRACKER.md`

## Deliverables
- Geospatial metadata route implementation in rq-engine.
- Upload metadata schema/default contract hardening for core upload operations.
- Geospatial/upload tests and OpenAPI contract updates.
- Updated frozen inventory/checklist artifacts for new/updated agent-facing routes.
- Updated package lifecycle docs and archived ExecPlan outcome.
- Completed security review artifact and reviewer/QA/security finding dispositions.

## Closure Notes
- Implemented `GET /api/runs/{runid}/{config}/geospatial-metadata` with canonical auth/error boundaries and deterministic fallbacks.
- Hardened upload descriptor/schema/default metadata for:
  - `rq_engine_upload_dem`
  - `rq_engine_upload_cli`
  - `rq_engine_upload_sbs`
  - `rq_engine_upload_cover_transform`
- Added and enforced live upload `max_bytes` limits for DEM/CLI/SBS/cover-transform routes.
- Added parity helpers/tests for climate mode, soils mode, and watershed defaults across metadata surfaces.
- Updated endpoint inventory and route-contract checklist freeze artifacts plus guard rule coverage.
- Completed independent `reviewer`, `qa_reviewer`, and `security_reviewer` re-reviews; no unresolved medium/high findings.
- Archived active ExecPlan to:
  - `docs/work-packages/20260410_rq_controller_state_geospatial_uploads/prompts/completed/rq_controller_state_geospatial_uploads_execplan.md`
  - outcome note: `docs/work-packages/20260410_rq_controller_state_geospatial_uploads/prompts/completed/rq_controller_state_geospatial_uploads_execplan_outcome.md`

## Follow-up Work
- `20260410_rq_controller_state_errors_progress_outputs`
- `20260410_rq_controller_state_auth_concurrency`
