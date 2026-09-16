# Implement the saved post-fire likelihood report


This is the active living ExecPlan for the report implementation, maintained
under `docs/prompt_templates/codex_exec_plans.md`. Update Progress, Surprises &
Discoveries, Decision Log and Outcomes & Retrospective at every milestone.

## Purpose / Big Picture


A user can open View likelihood report in the existing postfire control, compare
saved rainfall scenarios, see the three 50% rainfall thresholds and find a saved
storm without rerunning a model. It looks like existing Pure reports and clearly
distinguishes conditional likelihood from annual chance or downstream hazard.
The owner authorized implementation and local commits, not pushing/deployment
or live model reruns. The closed design package is immutable history.

## Progress


- [x] (2026-09-15 UTC) Read design handoff and repository contract-first process.
- [x] (2026-09-15 UTC) Owner granted checkpoint and implementation commit authority.
- [x] (2026-09-15 UTC) Prepared exact interface and compatibility/security record.
- [ ] Obtain independent contract/security/UX reviews and commit ancestor.
- [ ] Implement validated saved-table reader and bounded read routes with tests.
- [ ] Write controller tests, implement Pure report and wire existing control link.
- [ ] Validate saved M1/M3, browser tasks, no-write boundaries and broad gates.
- [ ] Resolve final independent reviews, commit implementation, close or name gaps.

## Surprises & Discoveries


There is no existing Flask postfire blueprint: its control uses rq-engine.
ResultCatalog validates but discards design/inverse, so retaining those tables
is smaller than creating another decoder. get_state requires reconcile=False
to avoid job-state reconciliation. M1 assessment identity is the upload ID.
The existing bearer-only artifact route lacks explicit no-store, so the report
needs a small fixed-name session-authenticated attachment route.

## Decision Log


2026-09-15 / root: execute a successor, preserving closed history. Owner approved
the planned design and required local commits. Use browser CSV from coherent
displayed rows; no separate CSV endpoint. No new data/queue/services. Preserve
existing freshness, including code-identity staleness; never rerun to hide it.

## Outcomes & Retrospective


Preparation underway. No runtime changes or implementation validation yet.

## Context and Orientation


Work in `/home/workdir/wepppy`, current branch. The durable contract is
`docs/ui-docs/contracts/postfire-debris-flow-report-contract.md`, including exact
HTTP paths, JSON fields, empty/error states and browser tasks. A bundle is an
immutable accepted attempt's manifest and three parquet tables, plus v2 mask.
`wepppy/nodb/mods/postfire_debris_flow/production.py` reads the accepted NoDb
record and currentness. `results.py` validates the saved bundle and queries
events. The report must use those readers, not compute scenarios or decode
original rasters. Existing scalar/saved-mask validation remains enabled.

Read nearest AGENTS before edits. Routes belong under
`wepppy/weppcloud/routes/nodb_api/postfire_report_bp.py`, registered in routes
`__init__.py` and `_blueprints_context.py`. Report template belongs under
`templates/reports/postfire_debris_flow/`; controller and Jest tests belong
under `controllers_js/` and `controllers_js/__tests__/`. Reuse Geneva's Pure
report shell and Unitizer patterns, not its scientific logic. Existing control
template gets one link; do not modify the model-running controller behavior.

## Plan of Work


Milestone 0 finalizes the current contract and review disposition, committing
only scope-owned documentation/agent registration as a standalone ancestor.
Record its hash in tracker before code. Independent reviewers assess the exact
routes/data/access/state matrix, not merely the visual outline.

Milestone 1 adds optional design/inverse Arrow fields to ResultCatalog and
returns all validated tables from open_results. Add a small report reader and
Flask adapter with page/query/detail/fixed attachments. Only accepted NoDb
records may select an attempt. Pin manifest from its saved artifact signature,
validate model/assessment association and recheck acceptance. Surface absent,
stale, unknown-currentness and invalid-bundle states separately. Real temporary
bundles test errors and no-write behavior; route tests exercise real authorization.

Milestone 2 starts with Jest tests of scenario selection, duration/filter/reset,
pagination, event details and response races. Implement one JSON bootstrap and
initializer, accessible saved-point chart/four-row table, three-row inverse
table, paginated events with inline detail, methods/downloads. Unitizer changes
all dimensions without changing selection or probability. Browser CSV handles
formula-safe text and full-precision displayed-unit numbers. Rebuild the bundle.

Milestone 3 reads existing accepted development M1 and M3 bundles, including
overpriced-sprawl and a second suitable basin. Do not run models. Record safe
identity/hash/value/timing evidence; compare report values and downloads, verify
unchanged run artifacts and no enqueues. Use copied fixtures for hostile/error/
archive states. Browser tasks cover desktop/narrow, keyboard and supported
themes; dedicated UX advocate challenges complexity. Missing external evidence
must be named, not fabricated or silently waived.

Milestone 4 runs focused and full gates, independent correctness/security/UX
reviews and post-fix confirmation. Update module/user/operator docs, tracker
and current contract conformance honestly. Commit scoped implementation; leave
unrelated code-quality outputs untouched. No push or deployment.

## Concrete Steps and Validation


From the workspace run `wctl run-pytest tests/nodb/mods --maxfail=1` and
`wctl run-pytest tests/weppcloud --maxfail=1`, narrowing first to newly created
test modules and existing postfire fixtures. Run `wctl run-npm lint`,
`wctl run-npm test`, and rebuild using
`python3 wepppy/weppcloud/controllers_js/build_controllers_js.py`.
Run `wctl run-pytest tests --maxfail=1` before final delivery. For public Python
surface changes run `wctl check-test-stubs`; record any independent failures.
Lint changed docs with `wctl doc-lint --path <path>`, preview uk2us and run
`git diff --check`. Record exact suite counts only after commands finish.

Acceptance is observable: no assessment gives a helpful empty page, valid
assessment shows exact saved values with explicit model/source/currentness,
filters/page counts represent unique events, keyboard selection exposes inline
details, units update together, and replaced acceptance requires reload. Every
unauthorized route denies access and every invalid artifact fails safely.
Do not seed all events or recalculate a probability curve.

## Idempotence and Recovery


Edits are additive and tests use temporary files. Report requests are read-only;
do not create optional NoDb state or reconcile jobs. Rollback removes the added
link/blueprint/UI and optional table projection, never accepted artifacts or
preferences. Preserve unrelated dirty work and never change branch. Re-run
failed checks after a scoped repair; capture remaining failures accurately.

## Artifacts and Interfaces


Retain checkpoint, review findings/dispositions and validation under artifacts.
Use exact read-interface contract for server/client shapes and state policies.
No new external dependency, service, scientific threshold or schema. Browser
payloads exclude raw source paths; normal artifact browsing/archive remains.

Revision note (2026-09-15 UTC): created active successor from owner-authorized
handoff, with exact transport and commit gate rather than reopening closed docs.
