# RQ Operator Experience Hardening

**Status**: Complete (2026-04-11 07:37 UTC)
**Timezone**: UTC (all timestamps in this package use UTC)

## Overview
This package hardens rq-engine for API operators running end-to-end automation without developer-only tooling. It addresses observed acceptance friction in auth bootstrap, cross-endpoint revision coherence, snapshot freshness semantics, and smoke-runbook reliability so autonomous agents can execute deterministic workflows with lower operational overhead.

## Objectives
- Deliver a machine-safe token bootstrap path for API operators that does not require `wctl` or HTML scraping.
- Make run-state consistency machine-joinable across endpoint families by implementing explicit revision-domain metadata.
- Eliminate ambiguous freshness signals by enforcing strict `updated_at`/materialization semantics.
- Replace brittle smoke-runbook assertions with deterministic gate checks based on exit status and contract shape.
- Add test and guard coverage that prevents regression in operator UX-critical contract guarantees.

## Scope
This package spans contract docs, route/descriptors/OpenAPI metadata, and API smoke/guard validation so the operator experience is both documented and enforced.

### Included
- Machine-first operator token bootstrap contract and implementation alignment.
- Controller-state response metadata hardening:
  - `run_state_domain`
  - `run_state_vector`
  - strict `updated_at` semantics
  - explicit `data_state` / `data_updated_at`
- Endpoint-family consistency enforcement tests for revision/freshness semantics.
- Smoke runbook and automation updates to remove hard-coded pass-count gates.
- Documentation updates across canonical schema docs and package artifacts.

### Explicitly Out of Scope
- Replacing browser-focused session renewal flows used by WEPPcloud UI.
- Broad auth system redesign outside rq-engine/weppcloud token bootstrap surfaces.
- Non-rq-engine service contracts unrelated to operator orchestration.

## Stakeholders
- **Primary**: rq-engine API operators and agent-interface maintainers.
- **Reviewers**: rq-engine contract/schema maintainers, WEPPcloud auth maintainers.
- **Security Reviewer**: required (auth/token and access-scope surfaces are in scope).
- **Informed**: downstream work-package owners using rq controller-state smoke workflows.

## Success Criteria
- [x] API operators can mint or acquire required JWTs via a documented machine-safe flow without `wctl` or HTML parsing.
- [x] Run-scoped controller-state responses expose deterministic revision-domain metadata that supports reliable multi-endpoint consistency checks.
- [x] Snapshot endpoints no longer emit `null`/epoch freshness sentinels and instead expose explicit materialization semantics.
- [x] Contract/openapi/route tests cover the new semantics and fail on regression.
- [x] Smoke runbook pass/fail criteria are deterministic and count-agnostic.
- [x] Security review artifact is complete with no unresolved medium/high findings.

## Dependencies

### Prerequisites
- [20260410_rq_controller_state_contract_cutover](../20260410_rq_controller_state_contract_cutover/package.md) (completed baseline freeze).
- Canonical contracts:
  - `docs/schemas/rq-engine-agent-api-contract.md`
  - `docs/schemas/rq-controller-state-contract.md`
  - `docs/dev-notes/auth-token.spec.md`

### Blocks
- Broader autonomous operator smoke rollout across additional configs/mods.

## Related Packages
- **Depends on**: [20260410_rq_controller_state_contract_cutover](../20260410_rq_controller_state_contract_cutover/package.md)
- **Related**:
  - [20260410_rq_controller_state_auth_concurrency](../20260410_rq_controller_state_auth_concurrency/package.md)
  - [20260410_rq_controller_state_errors_progress_outputs](../20260410_rq_controller_state_errors_progress_outputs/package.md)
- **Follow-up**: To be determined based on residual findings after implementation.

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions
- **Complexity**: High
- **Risk level**: High

## Security Impact and Review Gate
- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: token bootstrap and scope semantics directly affect authorization boundaries for automation clients.
- **Security review artifact**: `docs/work-packages/20260411_rq_operator_experience_hardening/artifacts/2026-04-11_security_review.md`

## Required Validation Gates

### Maintainer Preflight Gate (Contract/Route)
Maintainer-only gate for contract/route parity checks; these commands may rely
on `wctl`.
- Execute Phase A command set from:
  `docs/work-packages/20260410_rq_controller_state_contract_cutover/artifacts/2026-04-11_rq_controller_state_e2e_smoke_runbook.md`.

### Operator Acceptance Gate
- Run API-only operator smoke (auth bootstrap + discovery + orchestration reads + one mutation + polling + parity checks) using `curl`/`python` only (no `wctl`).
- Capture UTC method/path/status evidence and redacted payload snippets.
- Use canonical operator smoke sequence from:
  `docs/work-packages/20260410_rq_controller_state_contract_cutover/artifacts/2026-04-11_rq_controller_state_e2e_smoke_runbook.md`.

### QA/Security/Docs Gate
- Independent `reviewer`, `qa_reviewer`, and `security_reviewer` passes with dispositioned findings.
- `wctl doc-lint` across changed schema/work-package docs.

## References
- `docs/schemas/rq-engine-agent-api-contract.md`
- `docs/schemas/rq-controller-state-contract.md`
- `docs/work-packages/20260410_rq_controller_state_contract_cutover/artifacts/2026-04-11_rq_controller_state_e2e_smoke_runbook.md`
- `docs/work-packages/20260410_rq_controller_state_contract_cutover/artifacts/2026-04-11_clueless-aftertaste_replication_acceptance_report.md`
- `docs/prompt_templates/codex_exec_plans.md`
- `docs/work-packages/README.md`

## Deliverables
- Updated canonical contracts with operator UX hardening requirements.
- Implemented route/descriptor/openapi updates for operator token bootstrap and state/freshness metadata semantics.
- Regression tests and guard coverage for contract invariants.
- Updated smoke runbook + API-only acceptance evidence artifact.
- Security review artifact with final disposition.

## Kickoff Prompt
- Active ExecPlan: `docs/work-packages/20260411_rq_operator_experience_hardening/prompts/active/rq_operator_experience_hardening_execplan.md`
