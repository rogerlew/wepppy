# RQ Controller State Setup Discovery

**Status**: Closed (2026-04-10 07:29 UTC)
**Timezone**: UTC (all dates/times in this package documentation use UTC unless explicitly stated otherwise).

## Overview
This package implements the setup-discovery surfaces in rq-engine so agents can discover valid `create` configs and setup operation contracts without relying on out-of-band documentation. It is the first runtime implementation package after the `20260410_rq_controller_state_foundation` contract freeze.

## Objectives
- Implement non-run-scoped setup-discovery endpoints in rq-engine:
  - `GET /api/configs`
  - `GET /api/configs/{config}`
  - `GET /api/endpoints`
  - `GET /api/endpoints/{operation_id}/schema`
  - `GET /api/endpoints/{operation_id}/defaults`
  - `GET /api/endpoints/{operation_id}/errors`
- Ensure `operation_id` values in setup discovery are canonically aligned with OpenAPI IDs.
- Ensure descriptor auth metadata (`accepted_auth` + scope requirements) matches actual route behavior.
- Update frozen endpoint inventory/checklist artifacts and OpenAPI/contract tests for the new agent-facing routes.

## Scope
This package delivers setup-discovery routes, contract-aligned payloads, and required tests/docs/checklist updates.

### Included
- New rq-engine route module(s) for setup discovery.
- OpenAPI metadata updates and route-registration wiring.
- Contract and route-level tests for setup discovery behavior.
- Frozen artifact updates:
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`
- Contract/doc updates:
  - `docs/schemas/rq-controller-state-contract.md`
  - `docs/schemas/rq-engine-agent-api-contract.md`
  - `docs/dev-notes/rq-engine-agent-api.md` (pointer consistency if needed)

### Explicitly Out of Scope
- Run-scoped orchestration surfaces (`/pipeline`, `/readiness`, run-scoped endpoint schema/default/error routes).
- Full `rq:read` auth cutover and optimistic concurrency/idempotency rollout gates tracked by `20260410_rq_controller_state_auth_concurrency`.
- Controller-state read surfaces outside setup discovery.

## Stakeholders
- **Primary**: rq-engine maintainers and agent-interface implementers.
- **Reviewers**: API contract/schema maintainers.
- **Security Reviewer**: independent security subagent review required by package gate.
- **Informed**: downstream package owners for controller-state roadmap rows 3-8.

## Success Criteria
- [x] Setup discovery endpoints are implemented and exposed under rq-engine `/api`.
- [x] Agents can enumerate valid configs and derive `create` call requirements without external docs.
- [x] `operation_id` values in setup discovery payloads match OpenAPI operation IDs.
- [x] Frozen endpoint inventory/checklist artifacts include the six new setup routes.
- [x] Required validation gates pass (code, QA, security, docs) with no unresolved medium/high findings.

## Dependencies

### Prerequisites
- `docs/work-packages/20260410_rq_controller_state_foundation/` (completed foundation freeze).
- Canonical route artifacts:
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

### Blocks
- `20260410_rq_controller_state_orchestration_reads`
- `20260410_rq_controller_state_schema_defaults`
- `20260410_rq_controller_state_auth_concurrency`
- `20260410_rq_controller_state_contract_cutover`

## Related Packages
- **Depends on**: [20260410_rq_controller_state_foundation](../20260410_rq_controller_state_foundation/package.md)
- **Related**: [20260208_rq_engine_agent_usability](../20260208_rq_engine_agent_usability/package.md)
- **Follow-up**:
  - `20260410_rq_controller_state_orchestration_reads`
  - `20260410_rq_controller_state_schema_defaults`
  - `20260410_rq_controller_state_geospatial_uploads`

## Timeline Estimate
- **Expected duration**: 1 focused session
- **Complexity**: Medium
- **Risk level**: Medium

## Security Impact and Review Gate
- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: Adds new agent-facing setup endpoints and publishes auth metadata used for pre-run route selection; requires explicit auth/scope/session/CSRF boundary review.
- **Security review artifact**: `docs/work-packages/20260410_rq_controller_state_setup_discovery/artifacts/2026-04-10_security_review.md`

## Required Validation Gates

### Code Gate
- Add/extend setup-discovery route + contract tests.
- Update OpenAPI metadata/tests for the new setup endpoints.
- Update frozen endpoint inventory/checklist artifacts.
- Required commands:
  - `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1`
  - `wctl run-pytest tests/microservices/test_rq_engine_setup_discovery_routes.py --maxfail=1` (or equivalent changed rq-engine test slice)
  - `python tools/check_endpoint_inventory.py`
  - `python tools/check_route_contract_checklist.py`

### QA Gate
- Run independent reviewer + QA subagent review.
- Capture findings in package tracker and disposition every item.
- No unresolved medium/high QA findings at handoff.

### Security Gate
- Create and complete `artifacts/2026-04-10_security_review.md` using template guidance.
- Explicitly review auth/scope/session/CSRF implications for setup routes.
- No unresolved medium/high security findings at handoff.

### Docs Gate
- Run `wctl doc-lint` across all changed docs (schemas, package docs, tracker, ExecPlan, `PROJECT_TRACKER.md`, and security artifact).

## References
- `docs/schemas/rq-controller-state-contract.md`
- `docs/schemas/rq-engine-agent-api-contract.md`
- `docs/work-packages/README.md`
- `docs/prompt_templates/codex_exec_plans.md`
- `docs/work-packages/20260410_rq_controller_state_foundation/package.md`
- `docs/work-packages/20260410_rq_controller_state_foundation/tracker.md`
- `PROJECT_TRACKER.md`

## Deliverables
- Setup-discovery route implementation in rq-engine.
- Setup-discovery tests and OpenAPI contract updates.
- Updated freeze/checklist artifacts for new agent-facing endpoints.
- Updated schema/docs and package closeout documents.
- Security review artifact and QA/reviewer finding dispositions.

## Closure Notes
- Implemented setup discovery routes and registered them under rq-engine `/api`:
  - `GET /api/configs`
  - `GET /api/configs/{config}`
  - `GET /api/endpoints`
  - `GET /api/endpoints/{operation_id}/schema`
  - `GET /api/endpoints/{operation_id}/defaults`
  - `GET /api/endpoints/{operation_id}/errors`
- Added canonical contract boundaries and regression tests for auth matrix, payload structure, and handled internal-failure `500` payloads.
- Updated freeze/checklist artifacts and contract rules to include the six new setup-discovery routes in the frozen agent-facing baseline.
- Completed independent reviewer, QA, and security subagent passes; all medium/high findings were resolved before closure.
- Archived active ExecPlan to:
  - `docs/work-packages/20260410_rq_controller_state_setup_discovery/prompts/completed/rq_controller_state_setup_discovery_execplan.md`
  - outcome note: `docs/work-packages/20260410_rq_controller_state_setup_discovery/prompts/completed/rq_controller_state_setup_discovery_execplan_outcome.md`
- Security artifact completed:
  - `docs/work-packages/20260410_rq_controller_state_setup_discovery/artifacts/2026-04-10_security_review.md`

## Follow-up Work
- `20260410_rq_controller_state_orchestration_reads`
- `20260410_rq_controller_state_schema_defaults`
- `20260410_rq_controller_state_auth_concurrency`
