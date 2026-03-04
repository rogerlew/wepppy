# Outcome (Completed 2026-03-04)

- Status: Completed end-to-end and archived from `prompts/active/` to `prompts/completed/`.
- Accomplished: Milestones 1-5 were implemented across browse preview, parquet download, CSV export, D-Tale load, and filter-builder UI.
- Validation: Required test and docs gates were executed; detailed evidence is in `docs/work-packages/20260304_browse_parquet_quicklook_filters/artifacts/20260304_e2e_validation_results.md`.
- Deviation: `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` failed due pre-existing broad-catch deltas in touched files; follow-up is explicitly recorded in package tracker/artifacts.

## Prompt: Execute Browse Parquet Quick-Look Filter Builder End-to-End

You are executing an existing work-package ExecPlan in `/workdir/wepppy`.

Primary plan to execute:
- `docs/work-packages/20260304_browse_parquet_quicklook_filters/prompts/active/browse_parquet_quicklook_filters_execplan.md`

Execution contract:
- Read and follow `docs/prompt_templates/codex_exec_plans.md` before starting.
- Execute milestone by milestone end-to-end without pausing for extra confirmation unless blocked by a real external dependency.
- Keep the ExecPlan living sections current at each milestone boundary:
  - `Progress`
  - `Surprises & Discoveries`
  - `Decision Log`
  - `Outcomes & Retrospective`
- Keep package tracking docs synchronized during execution:
  - `docs/work-packages/20260304_browse_parquet_quicklook_filters/tracker.md`
  - `docs/work-packages/20260304_browse_parquet_quicklook_filters/artifacts/*`
  - `PROJECT_TRACKER.md` when status changes

Requester-confirmed behavior requirements (must not be changed):
- When filter state is active, `download` returns filtered parquet.
- `Contains` is case-insensitive.
- `GreaterThan` and `LessThan` are numeric-only and gracefully exclude missing/`NaN` rows.
- UI operator must be a select control.

Required subagent workflow per milestone:

1. `explorer` performs repository discovery and confirms touched call paths before edits.
2. Domain worker(s) execute milestone-specific implementation:
   - `worker` for browse microservice + template + test changes.
   - `weppcloud_refactorer` for UI/template integration and static JS behavior.
   - `query_engine_refactorer` only if query-engine internals are needed for safe parquet pushdown reuse.
3. `reviewer` performs severity-ranked review focused on correctness, security contracts, and regression risk.
4. `test_guardian` validates test coverage, failure-mode tests, and command execution discipline.
5. Integrator resolves findings, reruns required gates, and updates ExecPlan/tracker before marking milestone complete.

Scope and quality constraints:
- Preserve existing auth/path security behavior in browse/download/dtale routes.
- Preserve no-filter behavior when no filter payload is provided.
- No broad `except Exception` additions in production paths.
- Use explicit failures for invalid filters and unsupported comparisons.
- Avoid adding new dependencies unless justified via `docs/standards/dependency-evaluation-standard.md`.
- Keep implementation bounded to parquet quick-look surfaces (HTML preview, parquet download, CSV export, D-Tale).

Execution order:
1. Milestone 1: Implement shared filter contract parser/validator + compile/execution core.
2. Milestone 2: Integrate filtered parquet HTML preview in browse flow.
3. Milestone 3: Integrate filtered parquet download/CSV export/D-Tale load paths.
4. Milestone 4: Implement `Parquet Filter Builder` UI and filter-state propagation in parquet links.
5. Milestone 5: Finalize regression tests, docs updates, and rollout flag behavior.

Validation gates:
- Run exact validation commands listed in the active ExecPlan.
- Use `wctl` wrappers for tests and docs checks.
- Required route-level test suites at minimum:
  - `wctl run-pytest tests/microservices/test_browse_routes.py`
  - `wctl run-pytest tests/microservices/test_download.py`
  - `wctl run-pytest tests/microservices/test_browse_dtale.py`
  - `wctl run-pytest tests/microservices/test_files_routes.py`
  - `wctl run-pytest tests/microservices/test_browse_auth_routes.py`
- Required hygiene checks:
  - `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
  - `wctl doc-lint --path docs/work-packages/20260304_browse_parquet_quicklook_filters`
  - `wctl doc-lint --path PROJECT_TRACKER.md`
- Do not mark milestone complete until validations pass or failures are explicitly recorded in tracker/artifacts.

Handoff output requirements:
- Summarize completion by milestone with changed file paths.
- List exact commands run with pass/fail outcomes.
- List tests added/updated and the behavior each test protects.
- Call out any deferred items and residual risks.
- Confirm requester-required semantics are implemented exactly as specified.
