# Autonomously complete remaining run-domain Pure UI contracts

This ExecPlan is a living document. Maintain Progress, Surprises & Discoveries,
Decision Log, and Outcomes & Retrospective as work proceeds. It operates with
the umbrella `pure_ui_contract_standardization_execplan.md` and controls the
serial remaining run-domain queue.

## Purpose / Big Picture

Give every remaining run-page Pure UI controller direct regression evidence from
rendered fields/actions through browser requests, route parsing, saved state,
queued work, and reload when applicable. Every closed child package is its own
commit restore point. This is a tests-and-repair sequence, not a registry,
generator, manifest, or new CI system.

## Progress

- [x] (2026-07-28 UTC) Closed DOM-01, DOM-04A/B, DOM-05, DOM-06, DOM-07, and
  DOM-08A before this sequence.
- [x] (2026-07-28 UTC) Created the autonomous serial plan and per-package
  commit rule.
- [x] (2026-07-28 UTC) Scaffolded and executed DOM-08B; actual catalog/map
  rendering and existing browser/RQ-engine persistence evidence passed without
  a production repair.
- [x] (2026-07-28 UTC) Executed DOM-09; actual modifier rendering and existing
  exact-payload/synchronous-mutation evidence passed without a production
  repair.
- [x] (2026-07-28 UTC) Executed DOM-10; actual Soil rendering and existing
  state/queue/worker evidence passed without a production repair.
- [x] (2026-07-28 UTC) Executed DOM-11A; actual climate catalog/station/build
  rendering and existing state/parser/enqueue evidence passed without repair.
- [x] (2026-07-28 UTC) Executed DOM-11B; actual upload/scaling rendering and
  existing route/state/worker evidence passed without repair.
- [x] (2026-07-28 UTC) Executed DOM-12; repaired a saved model-source selected
  state mismatch with direct render/browser/route evidence.
- [x] (2026-07-28 UTC) Executed DOM-02; actual project header rendering and
  existing auth/state/module-gate evidence passed without repair.
- [x] (2026-07-28 UTC) Executed DOM-03; actual invite rendering and existing
  collaboration authorization evidence passed without repair.
- [x] (2026-07-28 UTC) Executed DOM-13A; actual boundary/schema/sub-field
  rendering and existing browser/RQ-engine state and enqueue evidence passed
  without repair.
- [x] (2026-07-28 UTC) Executed DOM-13B; actual plant archive/mapping rendering
  and existing browser/RQ-engine inventory and persistence evidence passed
  without repair.
- [x] (2026-07-28 UTC) Executed DOM-14A; actual core run/executable/lifecycle
  rendering and existing browser/Flask/RQ-engine evidence passed without repair.
- [ ] Execute all remaining run-domain packages in the dependency-aware order.
- [ ] Resolve each encountered hold through its owning package or a bounded
  operator decision.

## Surprises & Discoveries

- Observation: Regressions arose where a rendered name/value did not cross a
  parser or reload seam. Direct Jinja/Jest/pytest tests found those defects
  without shared infrastructure.
  Evidence: DOM-05 retained the depression-smoothing seam, DOM-07 added the
  build-before-abstraction edge, and DOM-08A added multipart normalization.

## Decision Log

- Decision: Execute one child package at a time even though packages are
  independently closable.
  Rationale: They share run state, route families, templates, and broad gates;
  one active package keeps regression risk, evidence, and repairs attributable.
  Date/Author: 2026-07-28 / Codex with operator authority.

- Decision: Commit every closed package; push only on separate operator request.
  Rationale: Commits are explicit recovery and review boundaries.
  Date/Author: 2026-07-28 / Codex with operator authority.

- Decision: Resolve holds at the nearest owner, never with speculative tooling.
  Rationale: The concise convention requires direct consumer evidence and the
  five-domain value review found no need for a helper or registry.
  Date/Author: 2026-07-28 / Codex.

## Outcomes & Retrospective

Append every closeout here: package ID, mismatch disposition, validation,
production-patch status, commit, and any hold resolution. On final closure,
compare value/runtime with the existing five-controller checkpoint and do not
propose tooling without a measured unresolved burden and operator approval.

DOM-08B: no mismatch and no production patch. Added actual-render endpoint,
upload/control, and snapshot-precondition evidence; 169 focused Python tests,
frontend lint, 4 focused Jest tests, the full 88-suite/663-test frontend sweep,
and package documentation lint passed. No hold or helper was introduced.

DOM-09: no mismatch and no production patch. Added actual-render selection,
value, action, and lifecycle evidence; 138 focused Python tests, lint, 3 focused
Jest tests, and package documentation lint passed. The preceding full frontend
sweep remained applicable because no frontend source changed.

DOM-10: no mismatch and no production patch. Expanded actual-render mode,
selection, option, and lifecycle evidence; 204 focused Python tests, lint, 7
focused Jest tests, and docs lint passed. No helper was introduced.

DOM-11A: no mismatch and no production patch. Added catalog/station/spatial/
build actual-render evidence; 79 render tests, 15 Climate Jest tests, 41
Flask/RQ-engine/parser/catalog tests, lint, and docs lint passed.

DOM-11B: no mismatch and no production patch. Added upload/scaling actual-render
evidence; 80 render tests, 15 Climate Jest tests, 71 upload/scaling/worker tests,
21 upload-schema tests, lint, and docs lint passed.

DOM-12: fixed `checked` versus `selected` macro input so saved SWAT state
renders selected. Focused render/route (86), Observed Jest (4), lint, and docs
lint passed; no authorization, payload, or queue behavior changed.

DOM-02: no mismatch and no production patch. Added actual project header
rendering; 123 render/route tests, 28 Project Jest tests, lint, and docs lint
passed.

DOM-03: no mismatch and no production patch. Added actual invite rendering; 92
render/route tests, 4 Team Jest tests, lint, and docs lint passed.

DOM-13A: no mismatch and no production patch. Added actual multipart boundary,
schema, and sub-field render evidence; 129 render/RQ-engine tests, 21 AgFields
Jest tests, lint, and docs lint passed.

DOM-13B: no mismatch and no production patch. Added actual plant archive/modal
mapping render evidence; 130 render/RQ-engine tests, 21 AgFields Jest tests,
lint, and docs lint passed.

DOM-14A: no mismatch and no production patch. Added actual core WEPP run,
executable, watershed action, and lifecycle render evidence; 194 focused Python
tests, the full 88-suite/663-test frontend sweep, lint, and docs lint passed.

## Context and Orientation

The authoritative backlog is `artifacts/child_package_register.md`; detailed
controller seams are in `artifacts/controller_audit_register.md`; the reusable
protocol is `controller_contract_audit_iteration_prompt.md`. An actual-render
test renders the Jinja template and asserts browser-visible id/name/value/state.
RQ is the Redis-backed job queue; test it only when a controller value crosses
enqueue/dependency/lifecycle behavior.

Remaining boundaries are DOM-02, DOM-03, DOM-08B, DOM-09, DOM-10, DOM-11A/B,
DOM-12, DOM-13A-D, DOM-14A-C, DOM-15 through DOM-29, including DOM-20A/B and
DOM-25A/B. DOM-08B owns the Landuse catalog/editor/map, distinct from DOM-08A's
already-verified build form.

## Plan of Work

For each selected package, create a dated directory with `package.md`,
`tracker.md`, field matrix, and active child ExecPlan; mark only that child in
progress. Read nearest instructions, canonical contracts, real template,
controller, parser, state, RQ path, reload path, and existing tests. Add the
smallest actual-render and downstream tests for risk-bearing values.

If behavior conforms, retain tests and close without production edits. If code
contradicts unchanged intent, add a regression and apply the smallest compatible
conformance fix. If intent is absent or ambiguous, stop that package and follow
`docs/standards/contract-first-change-standard.md`; do not infer intent. Test
direct consumers before any shared patch.

Use this dependency-aware serial order: DOM-08B, DOM-09, DOM-10, DOM-11A,
DOM-11B, DOM-12; DOM-02, DOM-03; DOM-13A, DOM-13B, DOM-14A, DOM-14B, DOM-14C,
DOM-15, DOM-16, DOM-17; DOM-18, DOM-19, DOM-21, DOM-22, DOM-23, DOM-24;
DOM-13C, DOM-13D, DOM-20A, DOM-20B, DOM-25A, DOM-25B, DOM-26, DOM-27, DOM-28,
DOM-29. This honors hard dependencies while treating register "context" as
non-blocking.

## Concrete Steps

From `/home/workdir/wepppy`, repeat:

    rg -n '<controller>|<endpoint>|<task>' wepppy tests
    wctl run-pytest <focused tests> --maxfail=1
    wctl run-npm test -- <controller selector>
    wctl run-npm lint
    wctl run-npm test
    wctl doc-lint --path <child package>
    git diff --check
    wctl doc-mv --force <active child plan> <completed child plan>
    git add <only that child, parent records, tests, and any repair>
    git commit -m 'test(<controller>): audit <contract>'

Run controller build only after controller source changes, `wctl check-rq-graph`
only after queue wiring changes, and proportional correctness/security review
only after production patches. If the full Python sweep hits the known unrelated
GridMET `_FakeUnits.degC` fixture failure, record it and use the focused set.

## Validation and Acceptance

Close only when actual-render evidence and every applicable serialization,
parser/state, RQ, and reload seam pass. Inapplicable layers require a concise
field-matrix reason. The sequence completes when every remaining row is
verified, documented with a bounded follow-up, or operator-excluded, and every
closeout has its own commit.

## Idempotence and Recovery

Require a clean worktree before every scaffold. Never reset/discard unrelated
work. Resume an interrupted package from its active plan and tracker. Re-running
tests and lint is safe; a failing test narrows the next repair, never broadens
scope.

## Revision Notes

2026-07-28: Created under explicit operator authority for autonomous serial
completion with per-package commits.
