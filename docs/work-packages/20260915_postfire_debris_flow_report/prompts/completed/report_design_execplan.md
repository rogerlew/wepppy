# Document and review the post-fire debris-flow report


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Keep
Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective
current. This is a documentation delivery plan, not authority to implement UI.

## Purpose / Big Picture


Give the owner an inspectable report design and an actionable implementation
handoff. Users need conditional rainfall likelihood with familiar report controls,
not raw parquet files or an overloaded dashboard. Completion is a reviewed
contract, linked module documentation and future implementation/acceptance plan.

## Progress


- [x] (2026-09-15 21:44 UTC) Read documentation tooling, plan instructions, report precedents and module contracts.
- [x] (2026-09-15 21:44 UTC) Draft contract, package, state/field matrix and future implementation plan.
- [x] (2026-09-15 21:56 UTC) Update module links and project board.
- [x] (2026-09-15 21:56 UTC) Obtain correctness, security and UX reviews; all findings independently confirmed resolved.
- [x] (2026-09-15 21:56 UTC) Lint, spelling-preview, check links/diff and TOML registration; close documentation delivery.

## Surprises & Discoveries


Geneva keeps report payload/selection rules in its module specification and
execution evidence in packages. Storm Event Analyzer combines design and phase
history in a document still labeled draft. Preserve the former separation.
The inverse table intentionally has null `probability`; its `target_probability`
owns the threshold label. Storm event counts must not count duration rows.

## Decision Log


Decision: saved scenario points, fixed existing 50% targets and a paginated event
table are the proposed first release. Rationale: existing artifacts answer the
primary question without scientific recalculation or extra controls.
Date/author: 2026-09-15, root agent; owner ratification pending.

Decision: register `.codex/agents/ux_reviewer.toml` in `.codex/config.toml`,
retain a dedicated UX review prompt and use a separate review agent.
Rationale: the owner explicitly requested intuitive human-facing simplicity,
which is not the same obligation as code correctness or security.
Date/author: 2026-09-15, owner request implemented by root agent.

## Outcomes & Retrospective


The reviewed report proposal, module links, field/state matrix and implementation
handoff are complete. Three independent reviewers confirmed all findings resolved.
The requested reusable UX role is registered; the current session used its
explicit brief without claiming runtime role reload. Documentation/configuration
validation passed. No report code, model runs, artifact schemas, scientific
defaults or production behavior changed. Owner ratification and runtime delivery
remain a separate phase, not an incomplete obligation of this documentation plan.

## Context and Orientation


`wepppy/nodb/mods/postfire_debris_flow/specification.md` owns domain behavior;
`docs/rainfall_results.md` within that module owns saved tables and bounded local
queries. An accepted attempt is the production-selected completed assessment;
it is distinct from a requested model or running job. M1 and M3 are separate
published equations with model-specific predictors. A likelihood is conditional
on a duration's rainfall, not an annual debris-flow probability.

The new durable report proposal is
`docs/ui-docs/contracts/postfire-debris-flow-report-contract.md`. This package's
`artifacts/field_matrix.md` maps visible behavior to data and future evidence;
`artifacts/implementation_plan.md` sequences the future code delivery. The
package tracker records review and validation; closed packages remain history.

## Plan of Work


Milestone 1 writes the report proposal, retaining accepted science and labeling
new presentation as pending. Add report/data-authority links to the module
specification and mark stage 7 design prepared, implementation pending in the
roadmap. Register the package in `PROJECT_TRACKER.md`. A reader can trace every
scientific claim to the existing module contracts and distinguish design status.

Milestone 2 writes the field/state matrix, contract decision and implementation
plan. It must include real-file boundaries, valid legacy/empty/stale states,
generic M1/M3 acceptance beyond one named basin, unitization, authorized reads,
identity races and honest exports. Retain a dedicated UX reviewer brief.

Milestone 3 sends the completed draft to three independent read-only reviewers:
correctness, security and UX. The author records their findings in artifacts,
edits the documents, and obtains confirmation for medium/high fixes. Review
approval means documentation readiness, not owner ratification or shipped UI.

Milestone 4 validates all touched Markdown, checks links and spelling, updates
tracker/outcomes, and moves completed prompts with `wctl doc-mv --force` to
`prompts/completed/`. Close only this documentation scope. Preserve all review
artifacts and unrelated working-tree edits; do not commit or push without authority.

## Concrete Steps


Run from `/home/workdir/wepppy`:

    wctl doc-lint --path docs/ui-docs/contracts/postfire-debris-flow-report-contract.md
    wctl doc-lint --path docs/work-packages/20260915_postfire_debris_flow_report
    wctl doc-lint --path wepppy/nodb/mods/postfire_debris_flow/specification.md
    wctl doc-lint --path wepppy/nodb/mods/postfire_debris_flow/implementation_roadmap.md
    wctl doc-lint --path PROJECT_TRACKER.md
    git diff --check

For each edited Markdown file, preview `diff -u FILE <(uk2us FILE)` and apply
only relevant safe spelling changes. Expect zero lint errors and no whitespace
errors; record exact outcomes rather than inventing runtime evidence.

## Validation and Acceptance


The owner can open the package and find the report proposal, module links,
implementation plan, field/state matrix, three independent reviews and their
disposition without chat history. All medium/high review findings are closed.
Future implementation gates are explicit and unclaimed. No runtime tests are
needed for prose-only changes; their planned commands live in the handoff plan.

## Idempotence and Recovery


All changes are additive documentation and narrow status/link edits. Retry lint
and review safely. Correct only this package's files; preserve unrelated dirty
code-quality files. No external writes, source acquisition, reruns or rollbacks.

## Artifacts and Notes


Retain review findings with reviewer identity, scope and date in `artifacts/`.
The final disposition records each finding and exact amendment. Normal repository
history archives these design records; no credentials or raw run data are needed.

## Interfaces and Dependencies


No new application runtime interfaces or dependencies are created. The requested
reusable UX role follows existing `.codex/config.toml` registrations; parse both
TOML files and verify the referenced role file exists. The future design reuses
`open_results`, `list_events`, `get_event`, Pure report shell, Unitizer and existing
run authorization/artifact browsing. The implementation plan must bind browser
adapters precisely in a ratified checkpoint before any implementation begins.

Revision note: 2026-09-15 — initial documentation-only plan, explicitly separating
delivery of a reviewed proposal from runtime implementation authorization.
Closeout revision: 2026-09-15 21:56 UTC — resolved reviewer findings on axes,
window labels, inline detail, saved-table projection, validator boundaries,
year coverage, response caching and CSV safety; all reviewers confirmed closure.
