# Broad Exception Elimination and Boundary Contract Hardening

**Status**: Closed (2026-02-23)

## Overview

Production code currently includes a large number of broad exception handlers (`except Exception`, bare `except`) across route, queue, and NoDb subsystems. Some of these catches are valid boundary protections, but many silently mask failures or flatten contract-specific errors into generic behavior.

This package executes a phased, test-driven cleanup that narrows broad catches while preserving existing API and workflow contracts.

## Objectives

- Remove or narrow over-broad exception handlers in high-risk production paths.
- Preserve canonical error contracts and status semantics in API boundaries.
- Replace silent swallow paths with explicit logging + re-raise or contract-compliant responses.
- Establish a sustainable changed-file guard that prevents new undocumented broad catches.

## Scope

### Included

- Production Python under:
  - `wepppy/microservices/rq_engine/`
  - `wepppy/rq/`
  - `wepppy/nodb/`
  - `wepppy/weppcloud/routes/`
  - `wepppy/query_engine/`
  - `services/cao/` (targeted boundary cleanup)
- Regression test updates/additions for exception contracts and error-shape behavior.
- Work-package artifacts documenting baseline inventory, phase outcomes, and residual approved boundaries.
- Tooling/guardrails for changed-file broad-exception drift.

### Explicitly Out of Scope

- Full repo-wide elimination of every historical broad catch in one pass.
- Contract redesign of rq-engine, weppcloud auth/session, or NoDb persistence semantics.
- Queue topology redesign unrelated to exception-hardening.
- New abstraction layers not required to remove a confirmed broad-exception risk.

## Stakeholders

- **Primary**: WEPPpy maintainers; agent contributors touching runtime/error flows.
- **Reviewers**: Roger.
- **Informed**: Teams using rq-engine APIs, WEPPcloud routes, and NoDb workflows.

## Success Criteria

- [x] Broad-catch cleanup completed for targeted high-risk files in rq-engine, rq workers, NoDb core/base, and WEPPcloud routes.
- [ ] No silent broad-exception swallow behavior remains in touched production paths. (Deferred hotspots are documented in `artifacts/boundary_allowlist.md`.)
- [x] Canonical error contracts remain intact (notably `docs/schemas/rq-response-contract.md`).
- [x] New/updated regression tests lock intended exception translation behavior.
- [x] A changed-file guard exists and prevents introducing undocumented broad catches.
- [x] Required validation gates pass (`wctl run-pytest` targeted suites + `tests --maxfail=1`).

## Dependencies

### Prerequisites

- Root policy in `AGENTS.md` and subsystem playbooks (`wepppy/nodb/AGENTS.md`, `wepppy/microservices/rq_engine/AGENTS.md`, `tests/AGENTS.md`).
- Canonical RQ response/error contract in `docs/schemas/rq-response-contract.md`.
- Existing route/worker/NoDb regression suites under `tests/`.

### Blocks

- Future hardening initiatives that require deterministic exception boundaries.
- Automation efforts depending on stable cross-service error behavior.

## Related Packages

- **Related**: [20260208_rq_engine_agent_usability](../20260208_rq_engine_agent_usability/package.md)
- **Related**: [20260219_cross_service_auth_tokens](../20260219_cross_service_auth_tokens/package.md)
- **Related (mini, completed)**: [20260221_browse_code_quality_closure_execplan](../../mini-work-packages/completed/20260221_browse_code_quality_closure_execplan.md)
- **Related (mini, completed)**: [20260221_nodb_omni_final_hotspot_elimination_execplan](../../mini-work-packages/completed/20260221_nodb_omni_final_hotspot_elimination_execplan.md)

## Timeline Estimate

- **Expected duration**: 1-3 weeks (phased rollout).
- **Complexity**: High.
- **Risk level**: High (contract regression risk if done without characterization tests).

## References

- `AGENTS.md` - global exception policy and ExecPlan requirements.
- `docs/prompt_templates/codex_exec_plans.md` - ExecPlan standard.
- `docs/schemas/rq-response-contract.md` - canonical rq-engine error payload contract.
- `docs/dev-notes/code-quality-observability.md` - observability policy and exception annotations.
- `docs/standards/nodb-facade-collaborator-pattern.md` - NoDb exception/logging constraints.

## Deliverables

- Active ExecPlan:
  - `docs/work-packages/20260222_broad_exception_elimination/prompts/active/broad_exception_elimination_execplan.md`
- End-to-end kickoff prompt:
  - `docs/work-packages/20260222_broad_exception_elimination/prompts/active/run_broad_exception_elimination_e2e.prompt.md`
- Living tracker and phase log:
  - `docs/work-packages/20260222_broad_exception_elimination/tracker.md`
- Baseline and phase artifacts under:
  - `docs/work-packages/20260222_broad_exception_elimination/artifacts/`

## Follow-up Work

- Promote broad-exception guard from changed-file scope to broader enforcement if rollout succeeds.
- Revisit legacy low-risk utility modules after high-risk runtime surfaces are closed.

## Closure Notes

**Closed**: 2026-02-23

**Summary**: Milestones 0-7 were executed end-to-end with phased broad-catch reduction (`1120 -> 1103`), changed-file enforcement (`--enforce-changed`) activation, boundary allowlist population, and final full-suite validation (`2048 passed, 29 skipped`).

**Lessons Learned**: characterization-first narrowing and required subagent review/testing loops prevented contract drift, while Milestone 7 showed that enforcement tooling needs explicit `TryStar` support and precise policy wording.

**Archive Status**: Closed. Follow-up package recommended for deferred swallow-style boundaries listed in `artifacts/boundary_allowlist.md`.
