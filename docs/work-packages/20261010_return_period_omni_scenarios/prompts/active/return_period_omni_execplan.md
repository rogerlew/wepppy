# Add Omni comparisons to simple return-period reports


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.
Execute this package only; keep Progress, Surprises & Discoveries, Decision Log,
and Outcomes & Retrospective current.

## Purpose / Big Picture


Users select completed Omni child scenarios in the return-period Configuration
card and see the current project and scenario-specific event dates/values in
each simple metric table. Download CSV exports the concatenated metric rows.
No selections means the established single-project report.

## Progress


- [x] (2026-10-10 17:26 UTC) Inspect route, template, CSV helper, and Omni discovery.
- [x] (2026-10-10 17:26 UTC) Prepare canonical contract and decision checkpoint.
- [x] (2026-10-10 UTC) Complete two independent contract reviews and disposition; both approved after fixes.
- [x] (2026-10-10 UTC) Operator authorized commit/proceed; checkpoint `c5358daa7` and reviewed path clarification `946ec76fb` committed before corresponding source edits.
- [x] (2026-10-10 UTC) Implement discovery, independent reports, template, URL round trips, and CSV.
- [x] (2026-10-10 UTC) Validate source-to-HTML/CSV semantics, 285 focused tests, 931 frontend tests, Chromium smoke; correctness/security reviews approved after fixes.
- [ ] Record full Python sanity outcome and final handoff.

## Surprises & Discoveries


The active renderer uses `simple_table` in `return_periods.htm`, not the older
`_return_period_simple_table.htm` partial. The route builds CSV separately.
`Omni.ran_scenarios` checks an output file, while dashboard discovery checks
only child directories and `wepp.nodb`. Neither alone proves report readiness.
Omni finalization can log a return-period refresh failure and continue.
Report memoization omits method/recurrence intervals from validation and can
write child JSON even when readonly. Comparison calls must bypass it with
`meoization=False`; keep the no-selection path unchanged.
Current completed runs place loss Parquet under `output/interchange`; the
older root output path remains supported. Report CSV dates and global intervals
were insufficient for comparisons; honor explicit event years and metric-local
interval keys. Empty filtered groups require preserving request metadata so
the next navigation does not discard year selections.

## Decision Log


2026-10-10, Codex: concatenate rows and add Scenario only when selected, because
independent recurrence dates cannot be joined. Preserve extraneous behavior
and carry selections back to simple mode. Document durable behavior in
`docs/ui-docs/contracts/return-period-omni-scenarios-contract.md`.

## Outcomes & Retrospective


Implemented and locally validated, with independent correctness/security review
approved. Browser smoke uses the real report/CSV workflow with isolated auth,
NoDb loading, and shell. Full Python sanity remains in progress. Not deployed.
Frontend lint has an unchanged climate-test error; broad-exception enforcement
has line-allowlist drift despite unchanged broad-handler count. Details and
remaining evidence are in `artifacts/20261010_validation.md`.

## Context and Orientation


Work from `/home/workdir/wepppy`. The authorized GET route is
`report_wepp_return_periods` in `wepppy/weppcloud/routes/nodb_api/wepp_bp.py`.
It loads `Wepp.report_return_periods` for one working directory and calls
`_build_return_period_simple_dataframe` for CSV. The template
`wepppy/weppcloud/templates/reports/wepp/return_periods.htm` owns Configuration,
the `simple_table` macro, CSV URLs, and inline navigation JavaScript. Omni child
directories are `_pups/omni/scenarios/<name>` inside a project. Consult current
Omni definitions/completion evidence without changing its state or execution.

## Plan of Work


Milestone 1 establishes the contract checkpoint. Read the package decision,
obtain two independent read-only reviews, resolve findings, and request only
the missing commit authority. Commit the contract/package/reviews together
before editing implementation. Record the ancestor revision in tracker.md.

Milestone 2 implements the finite report extension. Read tests/AGENTS.md before
test changes. Add regressions in `tests/weppcloud/routes/test_wepp_bp.py` and
`test_pure_controls_render.py`, plus an appropriate browser/JS test for multi-value
query preservation. Implement read-only completed-child discovery and validate
names/paths before loading child reports. Keep absent Omni harmless. Use the
same arguments and parent unit preferences for each independently evaluated
report, with memoization disabled for comparison calls. Apply the canonical
modern/legacy completion predicates and project-anchored containment rules.
Extend simple HTML and CSV with ordered scenario rows and no-events
messages. Use a native Details control with labeled checkboxes and Run report.
Keep applied query selections across every navigation and CSV action.

Milestone 3 validates and documents delivery. Render actual templates and parse
CSV output from the real serializer. Test filesystem containment without mocking
it. Exercise a restored fixture and differing child dates/start years. Update
report user/developer documentation and retain independent correctness/security
reviews. Close only after all applicable evidence passes; distinguish local
validation from deployment, which is outside this request.

## Concrete Steps


From the repository root, run scoped documentation lint for the new contract
and package using `wctl doc-lint --path <file>`. After implementation run
`wctl run-pytest tests/weppcloud/routes/test_wepp_bp.py tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`,
`wctl run-npm lint`, `wctl run-npm test`, then
`wctl run-pytest tests --maxfail=1`. Record failures and exact commands; do not
claim missing environment checks passed. Use the wepppy-tester skill for gates.

## Validation and Acceptance


With two selected scenarios whose events differ, every populated simple table
has Scenario, recurrence interval, date, and value. Parsed CSV rows agree with
each report, including units and independent dates. Current project rows remain
first; duplicates do not duplicate rows. No-selection headers remain unchanged.
Check absent/empty/legacy/completed/incomplete/missing-input/restored/hostile
states and the query combinations in the canonical contract. Selection of
unknown or escaping paths fails explicitly without opening external files.
Browser evidence must show checkbox application, reload preservation, CSV,
year/month/method changes, and toggling extraneous parameters.

## Idempotence and Recovery


This is a report-only extension. Do not mutate source run data, queue work,
or repair unavailable scenario outputs. Retry reads through the existing report
path after normal project recovery. Revert only this package's changes if needed;
preserve unrelated dirty files, especially generated docs_index.json.

## Artifacts and Notes


Retain contract decisions, reviews, test output summaries, and HTML/CSV semantic
comparisons under this package's artifacts directory. Update tracker.md before
handoff. The checkpoint starts at revision
`8b32a5c8c7d7eba52e947c8619b1dff2d8435e77`.

## Interfaces and Dependencies


Use repeated `omni_scenario` query values and the existing GET report endpoint.
Reuse `Wepp.report_return_periods`, unitizer presentation, and CSV serialization.
No new external dependencies or model formulas. Read existing artifact-backed
Omni completion metadata while validating both modern and legacy valid states.

Revision note: created 2026-10-10 to make the user-requested report extension
reviewable before the required contract ancestor and implementation.
Updated 2026-10-10 after implementation and reviews to record concrete fixes,
validation, authorized checkpoint ancestry, and remaining full-suite evidence.

Correction after live-project feedback: READONLY was an invalid completion
assumption. Operator rejected it; independently reviewed amendment `d89ace269`
permits artifact-backed discovery with empty metadata and established staging
from existing outputs on selection. Validate actual unstaged output copies and
optional Outlet form guard before final handoff.
