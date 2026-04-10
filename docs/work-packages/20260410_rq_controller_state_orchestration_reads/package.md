# RQ Controller State Orchestration Reads

**Status**: Closed (2026-04-10 18:08 UTC)
**Timezone**: UTC (all dates/times in this package documentation use UTC unless explicitly stated otherwise).

## Overview
This package implemented the run-scoped orchestration read surfaces that let agents drive WEPPcloud workflows deterministically without UI scraping. It delivered `/pipeline` and `/readiness` for existing `runid/config` contexts with canonical step identity, state transitions, invalidation lineage, and next-action semantics.

## Objectives
- Implement run-scoped orchestration read endpoints in rq-engine:
  - `GET /api/runs/{runid}/{config}/pipeline`
  - `GET /api/runs/{runid}/{config}/readiness`
- Enforce contract-aligned step/state semantics (`step_id`, `operation_id`, status/state machine, `can_run_now`, invalidation lineage).
- Ensure payloads are deterministic and config/mod-aware for baseline and disturbed runs.
- Add/extend OpenAPI and route-level tests plus frozen artifact/checklist guards for the new endpoints.

## Scope
This package delivered orchestration-read route implementation, contract-aligned payload builders, and required tests/docs/checklist updates.

### Included
- New rq-engine orchestration-read routes for pipeline/readiness.
- Router-registration and OpenAPI metadata updates.
- Pipeline/readiness payload assembly from run state with contract-required fields.
- Contract and route tests for auth, payload shape, state transitions, deterministic next-action selection, and review-identified regressions.
- Frozen artifact updates:
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

### Explicitly Out of Scope
- Endpoint schema/default surfaces for core operations (`20260410_rq_controller_state_schema_defaults`).
- Geospatial/upload metadata contracts (`20260410_rq_controller_state_geospatial_uploads`).
- Error catalog/progress/outputs surfaces (`20260410_rq_controller_state_errors_progress_outputs`).
- Auth-concurrency/idempotency rollout enforcement (`20260410_rq_controller_state_auth_concurrency`).

## Stakeholders
- **Primary**: rq-engine maintainers and agent-interface implementers.
- **Reviewers**: API contract/schema maintainers.
- **Security Reviewer**: independent security subagent review required by package gate.
- **Informed**: downstream owners for roadmap packages 4-8.

## Success Criteria
- [x] `/pipeline` and `/readiness` are implemented and exposed under rq-engine `/api/runs/{runid}/{config}`.
- [x] Step identity and status fields align with the contract core vocabulary and state-machine semantics.
- [x] `next_actionable_steps` is deterministic for baseline and disturbed configs given equivalent state.
- [x] Frozen endpoint inventory/checklist artifacts include the orchestration read routes.
- [x] Required validation gates pass (code, QA, security, docs) with no unresolved medium/high findings.

## Dependencies

### Prerequisites
- `docs/work-packages/20260410_rq_controller_state_foundation/` (complete)
- `docs/work-packages/20260410_rq_controller_state_setup_discovery/` (complete)
- Canonical route artifacts:
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

### Blocks
- `20260410_rq_controller_state_schema_defaults`
- `20260410_rq_controller_state_geospatial_uploads`
- `20260410_rq_controller_state_errors_progress_outputs`
- `20260410_rq_controller_state_auth_concurrency`
- `20260410_rq_controller_state_contract_cutover`

## Related Packages
- **Depends on**:
  - [20260410_rq_controller_state_foundation](../20260410_rq_controller_state_foundation/package.md)
  - [20260410_rq_controller_state_setup_discovery](../20260410_rq_controller_state_setup_discovery/package.md)
- **Related**: [20260208_rq_engine_agent_usability](../20260208_rq_engine_agent_usability/package.md)
- **Follow-up**:
  - `20260410_rq_controller_state_schema_defaults`
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
- **Triage rationale**: Adds new agent-facing run-scoped endpoints that expose orchestration state and readiness decisions; requires explicit review of run-access boundaries, auth/scope parity, and state disclosure constraints.
- **Security review artifact**: `docs/work-packages/20260410_rq_controller_state_orchestration_reads/artifacts/2026-04-10_security_review.md`

## Required Validation Gates

### Code Gate
- Implement/extend orchestration-read route and contract tests.
- Update OpenAPI metadata/tests for orchestration-read endpoints.
- Update frozen endpoint inventory/checklist artifacts and contract-rule guards.
- Required commands:
  - `wctl run-pytest tests/microservices/test_rq_engine_orchestration_read_routes.py --maxfail=1`
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
- Explicitly review auth/scope/session/CSRF and run-state disclosure implications.
- No unresolved medium/high security findings at handoff.

### Docs Gate
- Run `wctl doc-lint` on changed package/tracker/prompt/security docs, frozen artifacts, and `PROJECT_TRACKER.md`.

## References
- `docs/schemas/rq-controller-state-contract.md`
- `docs/schemas/rq-engine-agent-api-contract.md`
- `docs/work-packages/README.md`
- `docs/prompt_templates/codex_exec_plans.md`
- `docs/prompt_templates/security_review_template.md`
- `wepppy/microservices/rq_engine/AGENTS.md`
- `PROJECT_TRACKER.md`

## Deliverables
- Orchestration-read route implementation in rq-engine (`/pipeline`, `/readiness`).
- Orchestration-read tests and OpenAPI contract updates.
- Updated frozen inventory/checklist artifacts for new agent-facing routes.
- Updated package lifecycle docs and archived ExecPlan.
- Completed security review artifact and reviewer/QA/security finding dispositions.

## Closure Notes
- Implemented run-scoped orchestration reads:
  - `GET /api/runs/{runid}/{config}/pipeline`
  - `GET /api/runs/{runid}/{config}/readiness`
- Added deterministic payload synthesis with stable issue joins, invalidation lineage, and next-action prioritization.
- Hardened review-driven edge handling:
  - dedicated `RunConfigMismatchError` (`404` only for config mismatch)
  - canonical `500` for non-not-found value failures
  - UTC normalization for naive timestamps
  - deterministic empty-timeline `updated_at`
  - recursive child-job status/ended-at folding for fan-out queue trees
- Expanded orchestration route tests to cover auth denial, malformed paths, completion fallback, revision sensitivity, redaction, baseline/disturbed determinism, roads/swat completion semantics, and child-tree status precedence.
- Completed independent `reviewer`, `qa_reviewer`, and `security_reviewer` passes; no unresolved medium/high QA or security findings remain.
- Archived active ExecPlan to:
  - `docs/work-packages/20260410_rq_controller_state_orchestration_reads/prompts/completed/rq_controller_state_orchestration_reads_execplan.md`
  - outcome note: `docs/work-packages/20260410_rq_controller_state_orchestration_reads/prompts/completed/rq_controller_state_orchestration_reads_execplan_outcome.md`

## Follow-up Work
- `20260410_rq_controller_state_schema_defaults`
- `20260410_rq_controller_state_geospatial_uploads`
- `20260410_rq_controller_state_errors_progress_outputs`
- `20260410_rq_controller_state_auth_concurrency`
