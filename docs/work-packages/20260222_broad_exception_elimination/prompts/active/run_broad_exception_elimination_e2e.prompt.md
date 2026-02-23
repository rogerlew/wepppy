# Prompt: Execute Broad Exception Elimination End-to-End

You are executing an existing work-package ExecPlan in `/workdir/wepppy`.

Primary plan to execute:

- `docs/work-packages/20260222_broad_exception_elimination/prompts/active/broad_exception_elimination_execplan.md`

Execution contract:

- Read and follow `docs/prompt_templates/codex_exec_plans.md` before starting.
- Execute milestone by milestone end-to-end without pausing for "next steps" unless blocked by a real external dependency.
- Keep ExecPlan living sections current at each milestone boundary:
  - `Progress`
  - `Surprises & Discoveries`
  - `Decision Log`
  - `Outcomes & Retrospective`
- Keep package tracking docs synchronized during execution:
  - `docs/work-packages/20260222_broad_exception_elimination/tracker.md`
  - `docs/work-packages/20260222_broad_exception_elimination/artifacts/*`

Required subagent workflow per milestone:

1. `explorer` maps and classifies catch blocks in touched files.
2. Domain refactorer performs code changes:
   - `rq_refactorer` for rq-engine and rq worker milestones
   - `nodb_refactorer` for NoDb milestones
   - `weppcloud_refactorer` for WEPPcloud route milestones
   - `query_engine_refactorer` for query-engine milestones
   - `worker` for tools/tail cleanup
3. `reviewer` performs severity-ranked review of diffs and risks.
4. `test_guardian` runs required tests and authors missing regression tests where coverage gaps exist.
5. Integrator resolves findings, reruns gates, and updates plan/tracker.

Scope and quality constraints:

- Do not introduce silent fallback wrappers that hide missing dependencies or broken state.
- Preserve canonical error contracts, especially `docs/schemas/rq-response-contract.md`.
- Keep boundary catches only when they are true boundaries, minimal, logged, and documented.
- Add regression tests for each confirmed failure mode changed by exception handling updates.

Validation gates:

- Run the exact milestone-local validation commands listed in the active ExecPlan.
- Use `wctl` wrappers for pytest and related tooling.
- Run `wctl check-rq-graph` if queue wiring changes.
- Run `wctl run-pytest tests --maxfail=1` before final handoff.

Handoff output requirements:

- Summarize results by milestone.
- List exact commands run with pass/fail outcomes.
- List changed files grouped by purpose (code, tests, docs, tooling).
- Report residual risks, deferred items, and any boundary exceptions that remain with rationale.
