# RQ Controller State Contract Cutover

**Status**: Complete (closed 2026-04-11 00:18 UTC)
**Timezone**: UTC (all dates/times in this package documentation use UTC unless explicitly stated otherwise).

## Overview
This package closes the controller-state rollout by freezing contract + implementation alignment after packages 1-7. It reconciles remaining cutover decisions, finalizes inventory/checklist artifacts and OpenAPI contract guards, and ensures route/descriptor/docs behavior is auditable and internally consistent for agent-first execution.

## Objectives
- Complete contract-freeze reconciliation across schema docs, route contract checklist, endpoint inventory freeze, and OpenAPI guard tests.
- Resolve the explicit cutover policy decision for the least-privilege auth bridge (`rq:status` bearer -> broader minted session scopes).
- Disposition row 6-7 watch-list items with explicit outcomes (resolved change or accepted risk with ownership).
- Ensure package 1-7 verification evidence is complete, normalized, and discoverable for audit.
- Close package 8 with required code, QA, and security review gates and no unresolved medium/high findings.

## Scope
This package delivers final cutover reconciliation and evidence hardening only; it is not a broad new feature package.

### Included
- Contract cutover updates in:
  - `docs/schemas/rq-controller-state-contract.md`
  - `docs/schemas/rq-engine-agent-api-contract.md`
  - `docs/dev-notes/rq-engine-agent-api.md` (pointer/handoff parity as needed)
- Freeze/checklist and guard reconciliation in:
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`
  - `tools/rq_engine_contract_rules.py`
  - `tests/microservices/test_rq_engine_openapi_contract.py`
- Final lifecycle normalization for row 8 cutover evidence in package/tracker docs and `PROJECT_TRACKER.md`.

### Explicitly Out of Scope
- New controller-state endpoint feature expansion beyond finalized contract surfaces.
- Broad refactors unrelated to contract freeze/cutover parity.
- Post-cutover roadmap work not required to satisfy row-8 exit criteria.

## Stakeholders
- **Primary**: rq-engine maintainers and agent-interface implementers.
- **Reviewers**: API contract/schema maintainers.
- **Security Reviewer**: independent security subagent review required by package gate.
- **Informed**: package owners for rows 1-7 and downstream agents consuming the frozen contract.

## Success Criteria
- [x] Row-8 cutover exit criteria in `rq-controller-state-contract.md` are fully satisfied and evidenced in tracker notes.
- [x] OpenAPI contract test + freeze/checklist guard commands pass after cutover edits.
- [x] Auth least-privilege bridge cutover decision is explicit, documented, and reflected consistently across contract/docs/metadata.
- [x] Row 6-7 watch-list items are dispositioned (resolved or accepted risk) with rationale and ownership.
- [x] Required validation and independent review phases complete with no unresolved medium/high findings.

## Dependencies

### Prerequisites
- `docs/work-packages/20260410_rq_controller_state_setup_discovery/` (complete)
- `docs/work-packages/20260410_rq_controller_state_orchestration_reads/` (complete)
- `docs/work-packages/20260410_rq_controller_state_schema_defaults/` (complete)
- `docs/work-packages/20260410_rq_controller_state_geospatial_uploads/` (complete)
- `docs/work-packages/20260410_rq_controller_state_errors_progress_outputs/` (complete)
- `docs/work-packages/20260410_rq_controller_state_auth_concurrency/` (complete)
- Canonical route artifacts:
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

### Blocks
- Contract freeze publication and downstream “cutover complete” declaration for controller-state agent surfaces.

## Related Packages
- **Depends on**:
  - [20260410_rq_controller_state_setup_discovery](../20260410_rq_controller_state_setup_discovery/package.md)
  - [20260410_rq_controller_state_orchestration_reads](../20260410_rq_controller_state_orchestration_reads/package.md)
  - [20260410_rq_controller_state_schema_defaults](../20260410_rq_controller_state_schema_defaults/package.md)
  - [20260410_rq_controller_state_geospatial_uploads](../20260410_rq_controller_state_geospatial_uploads/package.md)
  - [20260410_rq_controller_state_errors_progress_outputs](../20260410_rq_controller_state_errors_progress_outputs/package.md)
  - [20260410_rq_controller_state_auth_concurrency](../20260410_rq_controller_state_auth_concurrency/package.md)
- **Related**: [20260208_rq_engine_agent_usability](../20260208_rq_engine_agent_usability/package.md)
- **Follow-up**:
  - Any post-cutover optimization package(s) explicitly spawned from accepted residual risks.

## Timeline Estimate
- **Expected duration**: 1 focused session
- **Complexity**: Medium
- **Risk level**: High

## Security Impact and Review Gate
- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: Cutover includes auth-scope policy decisions and publication of final agent-facing contract boundaries.
- **Security review artifact**: `docs/work-packages/20260410_rq_controller_state_contract_cutover/artifacts/2026-04-10_security_review.md`

## Required Validation Gates

### Code Gate
- Reconcile cutover contract/docs/guard artifacts and update affected tests/checks.
- Required commands:
  - `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1`
  - `python tools/check_endpoint_inventory.py`
  - `python tools/check_route_contract_checklist.py`
  - `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1`

### Review Phases
- **Phase 1 - Contract Review (`reviewer`)**
  - Validate contract/roadmap/cutover semantics and package evidence alignment.
  - No unresolved medium/high reviewer findings.
- **Phase 2 - QA Review (`qa_reviewer`)**
  - Validate reproducibility and gate evidence sufficiency.
  - No unresolved medium/high QA findings.
- **Phase 3 - Security Review (`security_reviewer`)**
  - Validate auth-scope cutover decision, residual-risk handling, and disclosure boundaries.
  - No unresolved medium/high security findings.

### Security Gate
- Complete `artifacts/2026-04-10_security_review.md` using template guidance.
- Record all security findings and dispositions; unresolved medium/high must block closeout.

### Docs Gate
- Run `wctl doc-lint` on changed schema/package/tracker/prompt/security docs and `PROJECT_TRACKER.md`.

## References
- `docs/schemas/rq-controller-state-contract.md`
- `docs/schemas/rq-engine-agent-api-contract.md`
- `docs/dev-notes/rq-engine-agent-api.md`
- `docs/work-packages/README.md`
- `docs/prompt_templates/codex_exec_plans.md`
- `docs/prompt_templates/security_review_template.md`
- `PROJECT_TRACKER.md`

## Deliverables
- Finalized contract-cutover doc updates with explicit policy decisions and watch-list dispositions.
- Updated freeze/checklist artifacts and guard/test parity for cutover state.
- Updated package lifecycle docs and archived ExecPlan on closure.
- Completed security review artifact and phased review dispositions.

## Kickoff Prompt
- Archived ExecPlan: `docs/work-packages/20260410_rq_controller_state_contract_cutover/prompts/completed/rq_controller_state_contract_cutover_execplan.md`
