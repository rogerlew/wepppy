# Prompt: Execute Cross-Service Auth Token Campaign End-to-End

You are executing an existing work-package ExecPlan in `/workdir/wepppy`.

Primary plan to execute:
- `docs/work-packages/20260219_cross_service_auth_tokens/prompts/active/integrated_auth_token_campaign_execplan.md`

Execution contract:
- Read and follow `docs/prompt_templates/codex_exec_plans.md` before starting.
- Execute the plan end-to-end without pausing for "next steps" between milestones unless blocked by a real external dependency.
- Keep the ExecPlan living sections current at each milestone boundary:
  - `Progress`
  - `Surprises & Discoveries`
  - `Decision Log`
  - `Outcomes & Retrospective`
- Keep package tracking docs synchronized during execution:
  - `docs/work-packages/20260219_cross_service_auth_tokens/tracker.md`
  - `docs/work-packages/20260219_cross_service_auth_tokens/artifacts/token_compatibility_matrix.md`
  - `docs/work-packages/20260219_cross_service_auth_tokens/artifacts/lifecycle_validation_results.md` (create/update)

Scope and quality constraints:
- Preserve current auth contracts unless the plan explicitly calls for a change.
- If behavior differs from the matrix/spec, resolve explicitly (code fix or documented contract update), then update plan + tracker + artifacts in the same change.
- Do not add speculative abstractions or fallback wrappers that mask missing dependencies.
- Add regression tests for each confirmed failure mode.

Execution order:
1. Milestone 0: create/land shared `tests/integration/` harness and fixtures.
2. Milestone 1: land matrix-driven cross-service token portability tests.
3. Milestone 2: land lifecycle tests (renewal fallback, revocation propagation, rotation overlap/retirement).
4. Milestone 3: close auth primitive unit-test gaps.
5. Milestone 4: run full validation gates and close out package docs.

Validation gates:
- Run the exact validation commands listed in the active ExecPlan.
- Use `wctl` wrappers for pytest/npm/doc tools.
- Do not mark milestone complete until required validations pass or failures are explicitly documented in plan/tracker.

Handoff output requirements:
- Summarize what shipped by milestone.
- List exact commands run and pass/fail outcomes.
- List changed files by purpose (tests, docs, contracts, code).
- Call out residual risks, deferred items, and any decisions requiring human policy input.
