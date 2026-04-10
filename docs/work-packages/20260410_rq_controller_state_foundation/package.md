# RQ Controller State Contract Foundation

**Status**: Closed (2026-04-10 04:23 UTC)
**Timezone**: UTC (all dates/times in this package documentation use UTC unless explicitly stated otherwise).
**Pre-scope note**: Scaffold authored at 2026-04-10 03:54 UTC for planned 2026-04-10 kickoff (date retained to match roadmap package ID and user-requested package name).

## Overview
This package establishes the implementation foundation for the RQ controller state contract before any endpoint build-out begins. It freezes canonical identifiers, descriptor invariants, and rollout assumptions so follow-on packages can implement APIs without drift between docs, OpenAPI, and route-level behavior.

## Objectives
- Freeze the canonical join-key model for `operation_id` and `step_id` across discovery, pipeline, readiness, and OpenAPI.
- Convert draft-level contract requirements into an implementation-ready baseline with explicit MUST/SHOULD boundaries.
- Produce a dependency-ordered implementation checklist for downstream work packages.
- Define verification gates that downstream packages must run to preserve contract alignment.

## Scope
This package covers contract-level design hardening, roadmap sequencing, and implementation guardrails only.

### Included
- Review and finalize foundation sections in `docs/schemas/rq-controller-state-contract.md`.
- Cross-check contract identifier vocabulary against frozen rq-engine route inventory artifacts.
- Record explicit implementation assumptions and unresolved decisions in work-package docs.
- Author and maintain ExecPlan for foundation execution and handoff.

### Explicitly Out of Scope
- Implementing new rq-engine routes or payload handlers.
- Adding production code for `/api/configs`, `/pipeline`, `/readiness`, or other proposed endpoints.
- Performing full OpenAPI or test-suite implementation updates beyond planning-level references.

## Stakeholders
- **Primary**: RQ engine maintainers and agent-interface implementers.
- **Reviewers**: Contract/schema maintainers for rq-engine and WEPPcloud docs.
- **Informed**: Teams building downstream work packages in the controller-state roadmap.

## Success Criteria
- [x] Foundation contract sections are internally consistent and implementation-ready.
- [x] Canonical identifier and descriptor invariants are explicitly frozen in docs.
- [x] Downstream package sequence and dependencies are documented with actionable exit criteria.
- [x] Required verification commands are documented for follow-on package execution.
- [x] Tracker and ExecPlan are complete enough for stateless agent handoff.

## Dependencies

### Prerequisites
- Existing draft contract:
  - `docs/schemas/rq-controller-state-contract.md`
- Existing agent API contract baseline:
  - `docs/schemas/rq-engine-agent-api-contract.md`
- Existing route freeze artifacts:
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

### Blocks (Direct)
- `20260410_rq_controller_state_setup_discovery`
- `20260410_rq_controller_state_orchestration_reads`
- `20260410_rq_controller_state_schema_defaults`

### Downstream Dependents (Transitive)
- `20260410_rq_controller_state_geospatial_uploads`
- `20260410_rq_controller_state_errors_progress_outputs`
- `20260410_rq_controller_state_auth_concurrency`
- `20260410_rq_controller_state_contract_cutover`

## Related Packages
- **Depends on**: none
- **Related**: [20260208_rq_engine_agent_usability](../20260208_rq_engine_agent_usability/package.md)
- **Follow-up**: `20260410_rq_controller_state_setup_discovery`, `20260410_rq_controller_state_orchestration_reads`, `20260410_rq_controller_state_schema_defaults`
- **Roadmap source of truth**: `docs/schemas/rq-controller-state-contract.md` (`ExecPlan Work-Package Roadmap` table)

## Timeline Estimate
- **Expected duration**: 1-2 focused sessions
- **Complexity**: Medium
- **Risk level**: Medium

## Security Impact and Review Gate
- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: Package changes include security-sensitive auth/scope contract semantics (`rq:read`/`rq:status` rollout behavior and create auth descriptor constraints) that guide downstream implementation.
- **Security review artifact**: `docs/work-packages/20260410_rq_controller_state_foundation/artifacts/2026-04-10_security_review.md`

## References
- `docs/schemas/rq-controller-state-contract.md` - proposed contract and roadmap.
- `docs/schemas/rq-engine-agent-api-contract.md` - canonical companion contract.
- `docs/work-packages/README.md` - package process and required artifacts.
- `docs/prompt_templates/codex_exec_plans.md` - ExecPlan requirements.
- `PROJECT_TRACKER.md` - cross-package scheduling and status board.

## Deliverables
- Work-package scaffold and lifecycle docs:
  - `docs/work-packages/20260410_rq_controller_state_foundation/package.md`
  - `docs/work-packages/20260410_rq_controller_state_foundation/tracker.md`
  - `docs/work-packages/20260410_rq_controller_state_foundation/prompts/completed/rq_controller_state_foundation_execplan.md`
  - `docs/work-packages/20260410_rq_controller_state_foundation/prompts/completed/rq_controller_state_foundation_execplan_outcome.md`
- Updated contract docs closing confirmed foundation ambiguities:
  - `docs/schemas/rq-controller-state-contract.md`
  - `docs/schemas/rq-engine-agent-api-contract.md`
- Security review artifact:
  - `docs/work-packages/20260410_rq_controller_state_foundation/artifacts/2026-04-10_security_review.md`
- Updated `PROJECT_TRACKER.md` lifecycle entry for this package.
- Independent reviewer subagent findings with disposition captured in tracker notes.

## Closure Notes
- Reconciled identifier model language with frozen artifacts by freezing `operation_id` alignment semantics and path-exception handling.
- Clarified descriptor invariants by defining catalog vs schema/default descriptor shapes and checklist parity boundaries.
- Clarified roadmap dependency notation and direct vs transitive package dependencies for handoff.
- Completed required validation gate:
  - `wctl doc-lint --path docs/schemas/rq-controller-state-contract.md --path docs/schemas/rq-engine-agent-api-contract.md --path docs/work-packages/20260410_rq_controller_state_foundation/package.md --path docs/work-packages/20260410_rq_controller_state_foundation/tracker.md --path docs/work-packages/20260410_rq_controller_state_foundation/prompts/completed/rq_controller_state_foundation_execplan.md --path docs/work-packages/20260410_rq_controller_state_foundation/prompts/completed/rq_controller_state_foundation_execplan_outcome.md --path docs/work-packages/20260410_rq_controller_state_foundation/artifacts/2026-04-10_security_review.md --path PROJECT_TRACKER.md` (`8 files validated, 0 errors, 0 warnings`).
- Root `PROJECT_TRACKER.md` entry moved from Backlog to Done.

## Follow-up Work
- Start `20260410_rq_controller_state_setup_discovery` once this package is marked closed.
- Start orchestration read endpoints package after setup discovery alignment.
- Revisit contract freeze after first implementation package to capture discovered deltas.
