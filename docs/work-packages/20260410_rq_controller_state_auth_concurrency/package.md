# RQ Controller State Auth and Concurrency

**Status**: Complete (closed 2026-04-10 22:52 UTC)
**Timezone**: UTC (all dates/times in this package documentation use UTC unless explicitly stated otherwise).

## Overview
This package enforces the auth and write-safety contract for controller-state surfaces so autonomous agents can execute safely under concurrent mutation. It hardens read-scope rollout (`rq:read`), accepted-auth parity, optimistic concurrency preconditions, and idempotency behavior alignment across descriptors, OpenAPI, and live routes.

## Objectives
- Enforce `rq:read` rollout semantics and planned `rq:status` alias sunset behavior for read-only controller-state surfaces.
- Align `accepted_auth` and `auth_requirements` metadata with actual route behavior.
- Implement/finish optimistic concurrency preconditions (`X-Run-State-Match` / expected run-state revision semantics where contract requires).
- Implement/finish idempotency behavior and descriptor parity for mutating operations that declare idempotency support.
- Add/extend OpenAPI and route-level tests plus frozen artifact/checklist guards for all auth/concurrency changes.

## Scope
This package delivers auth rollout enforcement, concurrency/idempotency behavior alignment, and required tests/docs/checklist updates.

### Included
- Route-level auth scope enforcement updates for controller-state surfaces.
- Descriptor/auth metadata parity updates for setup/run-scoped endpoint catalogs and schema payloads.
- Optimistic concurrency precondition enforcement and canonical conflict responses.
- Idempotency policy behavior alignment where declared supported.
- OpenAPI metadata and tests for auth/concurrency/idempotency semantics.
- Frozen artifact updates:
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

### Explicitly Out of Scope
- Final contract freeze/cutover reconciliation (`20260410_rq_controller_state_contract_cutover`).

## Stakeholders
- **Primary**: rq-engine maintainers and agent-interface implementers.
- **Reviewers**: API contract/schema maintainers.
- **Security Reviewer**: independent security subagent review required by package gate.
- **Informed**: downstream owners for final cutover package.

## Success Criteria
- [x] Auth scope behavior for controller-state surfaces matches contract rollout rules (`rq:read` with explicit compatibility boundaries).
- [x] Descriptor `accepted_auth` / `auth_requirements` matches live route behavior and OpenAPI metadata.
- [x] Concurrency precondition behavior (including conflict responses) is enforced where required.
- [x] Idempotency behavior matches declared policy metadata where supported.
- [x] Required validation gates pass (code, QA, security, docs) with no unresolved medium/high findings.

## Dependencies

### Prerequisites
- `docs/work-packages/20260410_rq_controller_state_setup_discovery/` (complete)
- `docs/work-packages/20260410_rq_controller_state_orchestration_reads/` (complete)
- `docs/work-packages/20260410_rq_controller_state_schema_defaults/` (complete)
- `docs/work-packages/20260410_rq_controller_state_errors_progress_outputs/` (complete)
- Canonical route artifacts:
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

### Blocks
- `20260410_rq_controller_state_contract_cutover`

## Related Packages
- **Depends on**:
  - [20260410_rq_controller_state_setup_discovery](../20260410_rq_controller_state_setup_discovery/package.md)
  - [20260410_rq_controller_state_orchestration_reads](../20260410_rq_controller_state_orchestration_reads/package.md)
  - [20260410_rq_controller_state_schema_defaults](../20260410_rq_controller_state_schema_defaults/package.md)
  - [20260410_rq_controller_state_errors_progress_outputs](../20260410_rq_controller_state_errors_progress_outputs/package.md)
- **Related**: [20260208_rq_engine_agent_usability](../20260208_rq_engine_agent_usability/package.md)
- **Follow-up**:
  - `20260410_rq_controller_state_contract_cutover`

## Timeline Estimate
- **Expected duration**: 1-2 focused sessions
- **Complexity**: High
- **Risk level**: High

## Security Impact and Review Gate
- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: This package changes auth/scope and mutation-safety semantics; it directly affects authorization boundaries and concurrent write safety.
- **Security review artifact**: `docs/work-packages/20260410_rq_controller_state_auth_concurrency/artifacts/2026-04-10_security_review.md`

## Required Validation Gates

### Code Gate
- Implement/extend auth-concurrency/idempotency route and contract tests.
- Update OpenAPI metadata/tests for auth/scope/concurrency/idempotency semantics.
- Update frozen endpoint inventory/checklist artifacts and contract-rule guards.
- Required commands:
  - `wctl run-pytest tests/microservices/test_rq_engine_auth_concurrency_routes.py --maxfail=1`
  - `wctl run-pytest tests/microservices/test_rq_engine_auth.py tests/microservices/test_rq_engine_session_routes.py --maxfail=1`
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
- Explicitly review auth/scope/session, concurrency-conflict behavior, and idempotency replay semantics.
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
- Auth scope rollout enforcement and metadata parity updates.
- Concurrency precondition enforcement and conflict contract coverage.
- Idempotency behavior alignment where declared supported.
- Updated OpenAPI/frozen inventory/checklist artifacts and guard tests.
- Updated package lifecycle docs and archived ExecPlan on closure.
- Completed security review artifact and reviewer/QA/security finding dispositions.

## Kickoff Prompt
- Archived ExecPlan: `docs/work-packages/20260410_rq_controller_state_auth_concurrency/prompts/completed/rq_controller_state_auth_concurrency_execplan.md`
