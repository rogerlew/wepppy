# RQ Controller State Errors, Progress, and Outputs

**Status**: Complete (closed 2026-04-10 22:00 UTC)
**Timezone**: UTC (all dates/times in this package documentation use UTC unless explicitly stated otherwise).

## Overview
This package implements operation error catalogs, async progress signaling, and outputs/artifact discovery so agents can recover from failures, poll intelligently, and fetch results without inferring hidden runtime behavior. It adds/finishes operation-scoped `/errors` surfaces where required, exposes canonical progress semantics for long-running operations, and implements `/outputs` with trust/provenance metadata.

## Objectives
- Implement/complete operation error catalog surfaces:
  - `GET /api/runs/{runid}/{config}/endpoints/{operation_id}/errors`
- Implement/complete progress signaling semantics for async operations consumed by orchestration and polling surfaces.
- Implement `GET /api/runs/{runid}/{config}/outputs` with contract-aligned artifact/export metadata.
- Ensure outputs and error catalogs are machine-actionable for autonomous recovery and artifact retrieval.
- Add/extend OpenAPI and route-level tests plus frozen artifact/checklist guards for all new/updated surfaces.

## Scope
This package delivers error catalog route implementation, progress metadata integration, outputs route implementation, and required tests/docs/checklist updates.

### Included
- New/extended rq-engine route module(s) for operation error catalogs and outputs.
- Progress metadata propagation for async run-scoped operations (as defined by contract profile and existing job surfaces).
- Router registration and OpenAPI metadata updates.
- Contract and route tests for auth, payload shape, error taxonomy joins, progress semantics, and artifact retrieval metadata.
- Frozen artifact updates:
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

### Explicitly Out of Scope
- Auth-concurrency/idempotency rollout enforcement (`20260410_rq_controller_state_auth_concurrency`).
- Final contract freeze/cutover reconciliation (`20260410_rq_controller_state_contract_cutover`).

## Stakeholders
- **Primary**: rq-engine maintainers and agent-interface implementers.
- **Reviewers**: API contract/schema maintainers.
- **Security Reviewer**: independent security subagent review required by package gate.
- **Informed**: downstream owners for roadmap packages 7-8.

## Success Criteria
- [x] Run-scoped endpoint error catalogs are implemented/complete with stable `error_code` semantics and recovery mappings.
- [x] Async progress metadata is exposed in a machine-actionable form consistent with contract expectations.
- [x] `/api/runs/{runid}/{config}/outputs` is implemented with artifact trust/provenance metadata and concrete retrieval handles.
- [x] Frozen endpoint inventory/checklist artifacts include all new/updated errors/progress/outputs rows.
- [x] Required validation gates pass (code, QA, security, docs) with no unresolved medium/high findings.

## Dependencies

### Prerequisites
- `docs/work-packages/20260410_rq_controller_state_orchestration_reads/` (complete)
- `docs/work-packages/20260410_rq_controller_state_schema_defaults/` (complete)
- `docs/work-packages/20260410_rq_controller_state_geospatial_uploads/` (complete)
- Canonical route artifacts:
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

### Blocks
- `20260410_rq_controller_state_auth_concurrency`
- `20260410_rq_controller_state_contract_cutover`

## Related Packages
- **Depends on**:
  - [20260410_rq_controller_state_orchestration_reads](../20260410_rq_controller_state_orchestration_reads/package.md)
  - [20260410_rq_controller_state_schema_defaults](../20260410_rq_controller_state_schema_defaults/package.md)
  - [20260410_rq_controller_state_geospatial_uploads](../20260410_rq_controller_state_geospatial_uploads/package.md)
- **Related**: [20260208_rq_engine_agent_usability](../20260208_rq_engine_agent_usability/package.md)
- **Follow-up**:
  - `20260410_rq_controller_state_auth_concurrency`
  - `20260410_rq_controller_state_contract_cutover`

## Timeline Estimate
- **Expected duration**: 1-2 focused sessions
- **Complexity**: High
- **Risk level**: High

## Security Impact and Review Gate
- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: Error catalogs and outputs metadata can disclose operational state and retrieval handles; progress and artifact metadata must not leak sensitive internals and must preserve run-scope boundaries.
- **Security review artifact**: `docs/work-packages/20260410_rq_controller_state_errors_progress_outputs/artifacts/2026-04-10_security_review.md`

## Required Validation Gates

### Code Gate
- Implement/extend errors/progress/outputs routes and contract tests.
- Update OpenAPI metadata/tests for errors/progress/outputs endpoints.
- Update frozen endpoint inventory/checklist artifacts and contract-rule guards.
- Required commands:
  - `wctl run-pytest tests/microservices/test_rq_engine_errors_progress_outputs_routes.py --maxfail=1`
  - `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1`
  - `python tools/check_endpoint_inventory.py`
  - `python tools/check_route_contract_checklist.py`
  - `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1`

### QA Gate
- Run independent `reviewer` and `qa_reviewer` subagent passes.
- Capture findings and dispositions in package tracker.
- No unresolved medium/high QA findings at handoff.

### Security Gate
- Complete `artifacts/2026-04-10_security_review.md` using template guidance.
- Run independent `security_reviewer` subagent pass.
- Explicitly review auth/scope/session, error-taxonomy disclosure, progress disclosure, and output/artifact retrieval metadata implications.
- No unresolved medium/high security findings at handoff.

### Docs Gate
- Run `wctl doc-lint` on changed schema/package/tracker/prompt/security docs and `PROJECT_TRACKER.md`.

## References
- `docs/schemas/rq-controller-state-contract.md`
- `docs/schemas/rq-engine-agent-api-contract.md`
- `docs/work-packages/README.md`
- `docs/prompt_templates/codex_exec_plans.md`
- `docs/prompt_templates/security_review_template.md`
- `wepppy/microservices/rq_engine/AGENTS.md`
- `PROJECT_TRACKER.md`

## Deliverables
- Error catalog surfaces and tests for run-scoped operation endpoints.
- Progress metadata integration and validation coverage.
- Outputs route implementation with artifact trust/provenance metadata and retrieval handles.
- Updated frozen inventory/checklist artifacts for new/updated agent-facing routes.
- Updated package lifecycle docs and archived ExecPlan on closure.
- Completed security review artifact and reviewer/QA/security finding dispositions.

## Kickoff Prompt
- Archived ExecPlan: `docs/work-packages/20260410_rq_controller_state_errors_progress_outputs/prompts/completed/rq_controller_state_errors_progress_outputs_execplan.md`
