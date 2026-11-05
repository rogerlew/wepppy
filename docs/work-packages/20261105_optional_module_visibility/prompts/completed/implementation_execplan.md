# Repair optional module visibility

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Maintain Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective throughout execution.

## Purpose / Big Picture

A project without Observed enabled currently displays an empty Observed Data Model Fit heading. Its initialized observed.nodb is not evidence that the feature is enabled or has results. Make ordinary page rendering, navigation and bootstrap agree on whether Observed has meaningful own state. Audit the other optional modules for the same mistake and repair confirmed peers.

## Progress

- [x] (2026-11-05 17:10 UTC) Diagnose the reported project and scaffold the package.
- [x] (2026-11-05 UTC) Audit source consumers and classify discrepancies; only Observed has confirmed server activation defect.
- [x] (2026-11-05 UTC) Repair Observed context, fallback, missing-state serialization, bootstrap selection and form remounting after failing regressions.
- [x] (2026-11-05 17:24 UTC) Validate focused suites, resolve both low review findings, pass independent review and close local scope.

## Surprises & Discoveries

Ron creates Observed for every initialized project. The reported project's Ron mods are disturbed/roads, while observed.nodb has results None and no observed artifacts. JavaScript hides the form only, leaving the surrounding shell visible. The anonymous URL returns a CAP verification page, so that HTTP response cannot prove the run DOM.

## Decision Log

2026-11-05 17:10 UTC: Preserve default initialization and retained results; correct presentation rather than mutate project data. Authority is the registry specification's own-state and inspection requirements plus the shared controller contract's absent-section behavior. This is a conformance repair, so no normative checkpoint ancestor is needed. The user requests scoped checks only; do not run the full suite. No branch, commit, deployment or project mutation is required.

## Outcomes & Retrospective

Implemented and locally validated: 537 scoped Python and 90 distinct scoped JavaScript tests pass; scoped ESLint and docs lint pass. Independent review passes with no unresolved findings. Only Observed had the confirmed activation defect. Its indirect missing-state, bootstrap, remount and status-handle consumers are repaired. User and developer guidance updated; bundle rebuilt. No full suite, deployment or project mutation. Authenticated live acceptance remains the deployment follow-up.

## Context and Orientation

Work from `/home/workdir/wepppy`. `wepppy/weppcloud/routes/run_0/run_0_bp.py` builds the page context and dynamic section responses. `routes/run_0/templates/runs0_pure.htm` renders hidden placeholders and conditionally includes actual controls. `run_page_bootstrap.js.j2` serializes controller state and selects controller bootstraps. `controllers_js/observed.js` manages the Observed form. `feature_registry/specification.md` requires each feature's own state and preserves readable results. `tests/weppcloud/routes/test_run_0_openet_admin_gate.py` and `test_pure_controls_render.py` provide nearby test fixtures.

## Plan of Work

First inspect all optional controller loads, visibility predicates, template fallbacks, bootstrap flags and dynamic-module dispatch. Record a bounded consumer matrix in artifacts, distinguishing verified unaffected paths from unresolved ones. Preserve enabled states and retained results while suppressing empty off-feature state. Before editing production files, add regression coverage for absent, initialized-empty, populated and legacy state, independently varying mod selection and preview flags.

Then apply the smallest correction at the actual visibility decision and any confirmed indirect consumers. Reuse existing hidden placeholders, navigation and Pure shell. Do not change scientific logic, loaders, saved schemas, authorization or queue wiring. Update supporting developer/operator guidance without changing normative intent.

Finally run focused Python render/route tests and only affected JavaScript checks if controller code changes. Obtain the repository-required independent correctness review; disposition every medium/high issue. Update package/tracker/root tracker, archive this plan to completed once local work is finished, and identify any live validation limit.

## Concrete Steps

Use `rg` to trace optional state through `run_0_bp.py`, `runs0_pure.htm`, `run_page_bootstrap.js.j2`, `project.js` and the affected controllers. Run `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py tests/weppcloud/routes/test_pure_controls_render.py tests/weppcloud/routes/test_feature_registry_runtime.py` with narrower node selections during iteration. If Observed JavaScript changes, run `wctl run-npm test -- observed` and scoped lint, then rebuild with `python3 wepppy/weppcloud/controllers_js/build_controllers_js.py`. Lint each modified Markdown document with `wctl doc-lint --path <file>`. Record actual commands and counts in the tracker.

## Validation and Acceptance

Off plus absent/empty Observed must yield no observed form/title and hidden navigation/placeholder. Enabled plus empty state must retain its section; populated legacy results remain inspectable without enabling or executing a feature. Preview continues to render. Missing Observed serializes hasResults false and does not spuriously report results. Exercise actual Jinja output and executable bootstrap selection rather than asserting only source strings. Confirm the reported project's durable state without writing it. Review other module states in the bounded audit; do not claim whole-system exhaustiveness.

## Idempotence and Recovery

Source/test/doc edits are reversible. No project repair, migration, data deletion or deployment occurs. Repeat scoped tests safely. Revert only this package's hunks if required; preserve unrelated dirty files and ignore generated usersum docs_index.json.

## Artifacts and Notes

Retain the consumer matrix, regression outcome and independent correctness review under artifacts. Never retain authentication tokens or raw private page dumps.

## Interfaces and Dependencies

Keep existing public interfaces. No new dependency or infrastructure. Reuse Flask/Jinja and existing pytest/Jest harnesses. The optional feature visibility decision consumes persisted mods, optional controller results and the authorized preview flag; it never initializes state or enqueues work.

Revision note: initial plan authored before implementation, 2026-11-05 17:10 UTC. Updated after focused validation and independent review to record indirect Observed defects, real status-handle lifecycle evidence and final outcomes; no peer activation defect or scope escalation found. Archived on local closure.
