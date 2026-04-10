# RQ Controller State Contract Foundation

**Status**: Open (2026-04-10)
**Pre-scope note**: Scaffold authored on 2026-04-09 for planned 2026-04-10 kickoff (date retained to match roadmap package ID and user-requested package name).

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
- Author active ExecPlan for foundation execution and handoff.

### Explicitly Out of Scope
- Implementing new rq-engine routes or payload handlers.
- Adding production code for `/api/configs`, `/pipeline`, `/readiness`, or other proposed endpoints.
- Performing full OpenAPI or test-suite implementation updates beyond planning-level references.

## Stakeholders
- **Primary**: RQ engine maintainers and agent-interface implementers.
- **Reviewers**: Contract/schema maintainers for rq-engine and WEPPcloud docs.
- **Informed**: Teams building downstream work packages in the controller-state roadmap.

## Success Criteria
- [ ] Foundation contract sections are internally consistent and implementation-ready.
- [ ] Canonical identifier and descriptor invariants are explicitly frozen in docs.
- [ ] Downstream package sequence and dependencies are documented with actionable exit criteria.
- [ ] Required verification commands are documented for follow-on package execution.
- [ ] Tracker and ExecPlan are complete enough for stateless agent handoff.

## Dependencies

### Prerequisites
- Existing draft contract:
  - `docs/schemas/rq-controller-state-contract.md`
- Existing agent API contract baseline:
  - `docs/schemas/rq-engine-agent-api-contract.md`
- Existing route freeze artifacts:
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

### Blocks
- `20260410_rq_controller_state_setup_discovery`
- `20260410_rq_controller_state_orchestration_reads`
- `20260410_rq_controller_state_schema_defaults`

## Related Packages
- **Depends on**: none
- **Related**: [20260208_rq_engine_agent_usability](../20260208_rq_engine_agent_usability/package.md)
- **Follow-up**: `20260410_rq_controller_state_setup_discovery`, `20260410_rq_controller_state_orchestration_reads`, `20260410_rq_controller_state_schema_defaults`

## Timeline Estimate
- **Expected duration**: 1-2 focused sessions
- **Complexity**: Medium
- **Risk level**: Medium

## Security Impact and Review Gate
- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: This package is planning/documentation-only and does not change runtime attack surfaces.
- **Security review artifact**: `N/A`

## References
- `docs/schemas/rq-controller-state-contract.md` - proposed contract and roadmap.
- `docs/schemas/rq-engine-agent-api-contract.md` - canonical companion contract.
- `docs/work-packages/README.md` - package process and required artifacts.
- `docs/prompt_templates/codex_exec_plans.md` - ExecPlan requirements.
- `PROJECT_TRACKER.md` - cross-package scheduling and status board.

## Deliverables
- Work-package scaffold:
  - `docs/work-packages/20260410_rq_controller_state_foundation/package.md`
  - `docs/work-packages/20260410_rq_controller_state_foundation/tracker.md`
  - `docs/work-packages/20260410_rq_controller_state_foundation/prompts/active/rq_controller_state_foundation_execplan.md`
- Updated `PROJECT_TRACKER.md` entry for this package.
- Foundation decisions and execution plan for downstream packages.

## Follow-up Work
- Start `20260410_rq_controller_state_setup_discovery` once this package is marked ready.
- Start orchestration read endpoints package after setup discovery alignment.
- Revisit contract freeze after first implementation package to capture discovered deltas.
