# RQ Controller State Schema and Defaults

**Status**: Complete (closed 2026-04-10 19:52 UTC)
**Timezone**: UTC (all dates/times in this package documentation use UTC unless explicitly stated otherwise).

## Overview
This package implements the schema/default read surfaces that let agents discover controller and operation constraints directly from rq-engine for an existing `runid/config`. It covers controller schema/hints/templates plus run-scoped endpoint schema/defaults with run-resolved constraints and defaults.

## Objectives
- Implement run-scoped controller metadata surfaces:
  - `GET /api/runs/{runid}/{config}/controllers`
  - `GET /api/runs/{runid}/{config}/controllers/{controller}/schema`
  - `GET /api/runs/{runid}/{config}/controllers/{controller}/hints`
  - `GET /api/runs/{runid}/{config}/controllers/{controller}/templates`
- Implement run-scoped endpoint schema/default surfaces:
  - `GET /api/runs/{runid}/{config}/endpoints`
  - `GET /api/runs/{runid}/{config}/endpoints/{operation_id}/schema`
  - `GET /api/runs/{runid}/{config}/endpoints/{operation_id}/defaults`
- Enforce contract-aligned metadata semantics including `constraint_mode`, predicate grammar fields (`required_if`, `available_if`), and run-resolved defaults context.
- Add/extend OpenAPI and route-level tests plus frozen artifact/checklist guards for the new endpoints.

## Scope
This package delivers schema/default route implementation, contract-aligned payload builders, and required tests/docs/checklist updates.

### Included
- New rq-engine schema/default route module(s) for controller and endpoint metadata reads.
- Router registration and OpenAPI metadata updates.
- Deterministic metadata payload assembly for baseline and disturbed configs.
- Contract and route tests for auth, payload shape, predicate grammar fields, and run-resolved constraint/default behavior.
- Frozen artifact updates:
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

### Explicitly Out of Scope
- Geospatial/upload metadata contracts (`20260410_rq_controller_state_geospatial_uploads`).
- Operation error catalogs/progress/outputs surfaces (`20260410_rq_controller_state_errors_progress_outputs`).
- Auth-concurrency/idempotency rollout enforcement (`20260410_rq_controller_state_auth_concurrency`).

## Stakeholders
- **Primary**: rq-engine maintainers and agent-interface implementers.
- **Reviewers**: API contract/schema maintainers.
- **Security Reviewer**: independent security subagent review required by package gate.
- **Informed**: downstream owners for roadmap packages 5-8.

## Success Criteria
- [x] Controller and endpoint schema/default surfaces are implemented and exposed under rq-engine `/api/runs/{runid}/{config}`.
- [x] Core metadata fields align with contract expectations (`constraint_mode`, `required_if`, `available_if`, run-resolved defaults context).
- [x] Schema/default payloads are deterministic for equivalent baseline and disturbed run states.
- [x] Frozen endpoint inventory/checklist artifacts include all new schema/default routes.
- [x] Required validation gates pass (code, QA, security, docs) with no unresolved medium/high findings.

## Dependencies

### Prerequisites
- `docs/work-packages/20260410_rq_controller_state_foundation/` (complete)
- `docs/work-packages/20260410_rq_controller_state_orchestration_reads/` (complete)
- Canonical route artifacts:
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

### Blocks
- `20260410_rq_controller_state_geospatial_uploads`
- `20260410_rq_controller_state_errors_progress_outputs`
- `20260410_rq_controller_state_auth_concurrency`
- `20260410_rq_controller_state_contract_cutover`

## Related Packages
- **Depends on**:
  - [20260410_rq_controller_state_foundation](../20260410_rq_controller_state_foundation/package.md)
  - [20260410_rq_controller_state_orchestration_reads](../20260410_rq_controller_state_orchestration_reads/package.md)
- **Related**:
  - [20260410_rq_controller_state_setup_discovery](../20260410_rq_controller_state_setup_discovery/package.md)
  - [20260208_rq_engine_agent_usability](../20260208_rq_engine_agent_usability/package.md)
- **Follow-up**:
  - `20260410_rq_controller_state_geospatial_uploads`
  - `20260410_rq_controller_state_errors_progress_outputs`
  - `20260410_rq_controller_state_auth_concurrency`

## Timeline Estimate
- **Expected duration**: 1-2 focused sessions
- **Complexity**: High
- **Risk level**: High

## Security Impact and Review Gate
- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: New run-scoped metadata surfaces expose controller and operation constraints/defaults used for autonomous execution planning; requires explicit run-access and data-disclosure review.
- **Security review artifact**: `docs/work-packages/20260410_rq_controller_state_schema_defaults/artifacts/2026-04-10_security_review.md`

## Required Validation Gates

### Code Gate
- Implement/extend schema/default routes and contract tests.
- Update OpenAPI metadata/tests for schema/default endpoints.
- Update frozen endpoint inventory/checklist artifacts and contract-rule guards.
- Required commands:
  - `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1`
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
- Explicitly review auth/scope/session/CSRF and sensitive-field disclosure implications.
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
- Schema/default route implementation in rq-engine for controller and endpoint metadata reads.
- Schema/default tests and OpenAPI contract updates.
- Updated frozen inventory/checklist artifacts for new agent-facing routes.
- Updated package lifecycle docs and archived ExecPlan on closure.
- Completed security review artifact and reviewer/QA/security finding dispositions.

## Closure Notes
- Implemented run-scoped schema/default routes:
  - `GET /api/runs/{runid}/{config}/controllers`
  - `GET /api/runs/{runid}/{config}/controllers/{controller}/schema`
  - `GET /api/runs/{runid}/{config}/controllers/{controller}/hints`
  - `GET /api/runs/{runid}/{config}/controllers/{controller}/templates`
  - `GET /api/runs/{runid}/{config}/endpoints`
  - `GET /api/runs/{runid}/{config}/endpoints/{operation_id}/schema`
  - `GET /api/runs/{runid}/{config}/endpoints/{operation_id}/defaults`
- Registered schema/default router in `wepppy/microservices/rq_engine/__init__.py` and added deterministic payload builders in `wepppy/microservices/rq_engine/schema_defaults_routes.py`.
- Updated and extended coverage:
  - `tests/microservices/test_rq_engine_schema_defaults_routes.py`
  - `tests/microservices/test_rq_engine_openapi_contract.py`
  - `tools/rq_engine_contract_rules.py`
  - frozen artifacts in `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/`
- Resolved reviewer-discovered parity defects between metadata and actual handlers (climate default integer typing, upload-SBS disturbed-mod gating, operation schema/default parity for soils/wepp/session-token surfaces).
- Completed independent `reviewer`, `qa_reviewer`, and `security_reviewer` gates with no unresolved medium/high findings.
- Archived active ExecPlan to:
  - `docs/work-packages/20260410_rq_controller_state_schema_defaults/prompts/completed/rq_controller_state_schema_defaults_execplan.md`
  - outcome note: `docs/work-packages/20260410_rq_controller_state_schema_defaults/prompts/completed/rq_controller_state_schema_defaults_execplan_outcome.md`

## Kickoff Prompt (Archived)
- `docs/work-packages/20260410_rq_controller_state_schema_defaults/prompts/completed/rq_controller_state_schema_defaults_execplan.md`
