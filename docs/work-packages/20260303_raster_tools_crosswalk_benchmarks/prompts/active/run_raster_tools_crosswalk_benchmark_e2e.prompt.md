# Prompt: Execute Raster Tools Cross-Walk and Benchmark Package End-to-End

You are executing an existing work-package ExecPlan in `/workdir/wepppy`.

Primary plan to execute:
- `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/prompts/active/raster_tools_crosswalk_benchmark_execplan.md`

Execution contract:
- Read and follow `docs/prompt_templates/codex_exec_plans.md` before starting.
- Execute milestone by milestone end-to-end without pausing for "next steps" unless blocked by a real external dependency.
- Keep the ExecPlan living sections current at each milestone boundary:
  - `Progress`
  - `Surprises & Discoveries`
  - `Decision Log`
  - `Outcomes & Retrospective`
- Keep package tracking docs synchronized during execution:
  - `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/tracker.md`
  - `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/artifacts/*`
  - `PROJECT_TRACKER.md` when status changes

Required subagent workflow per milestone:

1. `explorer` performs repository discovery and produces source-grounded capability/workflow inventories.
2. Domain worker(s) execute milestone-specific implementation:
   - `worker` for artifact authoring and benchmark harness scripting
   - `nodb_refactorer` for WEPPpy NoDb/raster workflow mapping under `wepppy/nodb/**`
   - `weppcloud_refactorer` for WEPPcloud geospatial call-path mapping under `wepppy/weppcloud/**`
3. `reviewer` performs severity-ranked review focused on correctness, evidence traceability, and scope control.
4. `test_guardian` validates commands/artifacts and adds missing regression/verification checks for benchmark parity where needed.
5. Integrator resolves findings, reruns required gates, and updates ExecPlan/tracker/artifacts before marking milestone complete.

Scope and quality constraints:
- Do not start benchmark execution until the cross-walk matrix is complete and benchmark shortlist is explicitly justified from overlap rows.
- Anchor every matrix and recommendation claim to concrete source evidence (file paths and/or command outputs).
- Do not add speculative wrappers or abstractions; this package is evaluation-only.
- Fail explicitly when dependencies or operations are missing; record findings instead of masking failures.
- Keep benchmark comparisons semantically equivalent; non-equivalent operations must be marked non-comparable.

Execution order:
1. Milestone 1: publish capability inventory and WEPPpy geospatial usage map.
2. Milestone 2: publish capability cross-walk matrix and benchmark shortlist.
3. Milestone 3: publish benchmark plan and harness implementation notes.
4. Milestone 4: execute benchmarks and publish benchmark results with parity outcomes.
5. Milestone 5: publish adoption recommendation memo and close package docs.

Validation gates:
- Run the exact validation commands listed in the active ExecPlan.
- Use `wctl` wrappers where applicable.
- Required documentation checks:
  - `wctl doc-lint --path docs/work-packages/20260303_raster_tools_crosswalk_benchmarks`
  - `wctl doc-lint --path PROJECT_TRACKER.md`
- Do not mark a milestone complete until required validations pass or failures are explicitly recorded in tracker/artifacts.

Handoff output requirements:
- Summarize completion by milestone with artifact paths.
- List exact commands run with pass/fail outcomes.
- List changed files grouped by purpose (artifacts, docs, scripts/harness).
- Call out residual risks, deferred items, and recommendation rationale (`defer`, `selective adoption`, or `broad adoption candidate`).
