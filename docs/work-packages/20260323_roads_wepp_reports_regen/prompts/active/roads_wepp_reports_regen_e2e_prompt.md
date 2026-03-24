# Prompt: Execute Roads WEPP Report Regeneration Package End-to-End

You are executing the active Roads report-resource parity package in `/workdir/wepppy`.

## Mandatory startup

1. Read `/workdir/wepppy/AGENTS.md`.
2. Read `/workdir/wepppy/docs/prompt_templates/codex_exec_plans.md`.
3. Read `/workdir/wepppy/docs/work-packages/20260323_roads_wepp_reports_regen/package.md`.
4. Read `/workdir/wepppy/docs/work-packages/20260323_roads_wepp_reports_regen/tracker.md`.
5. Read `/workdir/wepppy/docs/work-packages/20260323_roads_wepp_reports_regen/prompts/active/roads_wepp_reports_regen_execplan.md`.
6. Read `/workdir/wepppy/wepppy/nodb/mods/roads/specification.md`.
7. Confirm fixture defaults exist before implementation or fixture verification:
   - `/wc1/runs/cl/clogging-starch`
   - `/wc1/runs/cl/clogging-starch/roads/UM1_roads_info.geojson`
   - `/wc1/runs/cl/clogging-starch/dem/wbt/relief.tif`

## Primary references to keep synchronized

- Active ExecPlan: `docs/work-packages/20260323_roads_wepp_reports_regen/prompts/active/roads_wepp_reports_regen_execplan.md`
- Tracker: `docs/work-packages/20260323_roads_wepp_reports_regen/tracker.md`

## Execution contract

- Execute milestone-by-milestone end-to-end without pausing for extra confirmation unless blocked by an external dependency.
- Follow `AGENTS.md` plus all nearest nested `AGENTS.md` files for touched paths.
- Keep ExecPlan living sections current at each milestone boundary:
  - `Progress`
  - `Surprises & Discoveries`
  - `Decision Log`
  - `Outcomes & Retrospective`
- Keep package tracker current as milestones advance.
- If package status changes materially, update `PROJECT_TRACKER.md`.

## Non-negotiable scope and behavior guardrails

- Roads report resources must remain isolated under `wepp/roads/output` and `wepp/roads/output/interchange`.
- Never overwrite baseline `wepp/output/*` artifacts.
- Enforce strict `output_scope` contract: only `baseline|roads`; default remains `baseline`; invalid scopes must fail explicitly (400 path).
- Do not add fallback wrappers that hide missing dependencies or silently fall back to baseline when Roads scope is requested.
- Preserve explicit-failure behavior for missing required Roads artifacts.

## Required rollout sequence and review gates

Execute in this exact order:

1. Milestone 1: Foundation guardrails (`output_scope` contract + scoped cache/path isolation).
2. Milestone 2: `return_periods` rollover.
3. Milestone 3: `streamflow + water balance` rollover.
4. Milestone 4: `gl-dashboard` rollover.
5. Milestone 5: `storm event analyzer` rollover.
6. Milestone 6: Roads post-run report regeneration + Roads Run Results summary.
7. Milestone 7: Regression coverage + fixture-backed e2e verification.
8. Milestone 8: Independent cross-cutting code review.
9. Milestone 9: Independent cross-cutting QA review.
10. Milestone 10: Governance/doc sync + full validation gates.

Review closure rules:

- After each component rollover (Milestones 2-5), run a dedicated `reviewer` regression pass for that component.
- Record each component review in package artifacts before moving forward.
- Resolve all medium/high findings before starting the next rollover component.
- After implementation milestones, run independent cross-cutting code review and QA review passes.
- Resolve all medium/high cross-cutting findings before final handoff.

## Required review artifacts

- `docs/work-packages/20260323_roads_wepp_reports_regen/artifacts/return_periods_regression_review.md`
- `docs/work-packages/20260323_roads_wepp_reports_regen/artifacts/streamflow_watbal_regression_review.md`
- `docs/work-packages/20260323_roads_wepp_reports_regen/artifacts/gl_dashboard_regression_review.md`
- `docs/work-packages/20260323_roads_wepp_reports_regen/artifacts/storm_event_analyzer_regression_review.md`
- `docs/work-packages/20260323_roads_wepp_reports_regen/artifacts/code_review_findings.md`
- `docs/work-packages/20260323_roads_wepp_reports_regen/artifacts/qa_review_findings.md`

## Fixture defaults (unless explicitly justified)

- run id: `clogging-starch`
- wd: `/wc1/runs/cl/clogging-starch`
- config: `disturbed9002-wbt-mofe.cfg`
- roads input: `/wc1/runs/cl/clogging-starch/roads/UM1_roads_info.geojson`
- DEM: `/wc1/runs/cl/clogging-starch/dem/wbt/relief.tif`

## Validation requirements

- Run the exact validation gates defined in the active ExecPlan.
- Use `wctl` wrappers for tests/docs checks.
- At final handoff, include exact commands and pass/fail outcomes.
- Ensure docs checks include package docs and prompt files, including:
  - `wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/package.md`
  - `wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/tracker.md`
  - `wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/prompts/active/roads_wepp_reports_regen_execplan.md`
  - `wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/prompts/active/roads_wepp_reports_regen_e2e_prompt.md`

## Handoff format

Provide:
1. Milestones completed and what remains.
2. Files changed.
3. Test/validation commands run with pass/fail.
4. Code review findings summary and disposition.
5. QA review findings summary and disposition.
6. Blockers, risks, and rollback notes.
