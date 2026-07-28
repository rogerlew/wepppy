# Test and repair Pure UI controllers one at a time

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` current in accordance with
`docs/prompt_templates/codex_exec_plans.md`. Keep the umbrella tracker,
controller register, child-package register, and active child tracker current.

## Purpose / Big Picture

Work through the Pure UI inventory one controller at a time. Each controller
package establishes intent, tests actual rendered and downstream behavior,
reproduces contract mismatches, patches them minimally, and retains regression
coverage before the next controller begins.

The initiative's output is safer controller behavior and executable tests. It
is not a contract registry or enforcement platform.

## Progress

- [x] (2026-07-17) Created and independently reviewed the controller inventory
  and bounded package register.
- [x] (2026-07-17 through 2026-07-28) Recorded contract-first governance and
  completed bounded-remediation milestones REM-01 through REM-05 as documented
  in their trackers.
- [x] (2026-07-28) Scaffolded a registry/enforcement dependency platform.
- [x] (2026-07-28) Operator rejected that platform-first direction and required
  a low-regression, controller-by-controller tests-and-repair loop.
- [x] (2026-07-28) Removed seven speculative shared/enforcement scaffolds,
  retained DOM-01 as the first controller, and deferred GOV-01.
- [x] (2026-07-28 10:20Z) Closed the simplified GOV-00A test convention after
  proportional independent review.
- [x] (2026-07-28) Executed and closed DOM-01 WATAR/Ash with direct regression
  tests and no production mismatch.
- [ ] Continue with one controller package at a time.
- [ ] Review measured value after five controllers.
- [ ] Close the initiative when the registered inventory has executable
  regression coverage or explicit operator-approved exclusions.

## Surprises & Discoveries

- Observation: WATAR and channel depression smoothing both failed because tests
  did not cross actual rendered name/value into downstream parsing and reload.

- Observation: The controller count created planning anxiety and caused an
  architecture with two registries, a generated index, a manifest, change-aware
  enforcement, consumer fan-out, attestations, and prerequisite shared audits.

- Observation: That trajectory matched the negative-value TESTGATE assessment:
  control-plane assurance was being built before a thin product slice proved
  benefit.

- Observation: The useful loop is independent of controller count and can be
  applied sequentially with existing Jinja, Jest/jsdom, pytest, controller
  build, and stale-bundle checks.

## Decision Log

### 2026-07-28: Controller count is inventory

**Decision**: Do not use the number of controllers to justify orchestration,
schemas, dependency gates, or broad up-front audits.

### 2026-07-28: One-controller tests-first execution

**Decision**: One controller is active at a time. Actual-render and focused
downstream tests precede minimal compatible repair when practical.

### 2026-07-28: Shared behavior is encountered, not prerequisite

**Decision**: Shared packages do not block controller tests. If a controller
exposes a shared mismatch, test the controller and direct consumers before a
shared patch. Narrow or defer the shared patch when coverage is unavailable.

### 2026-07-28: Tooling must earn its existence

**Decision**: Direct assertions first. Extract a stateless test helper after at
least two repeated tests. Defer GOV-01 until five controllers show a measured
miss or repeated burden and the operator explicitly approves a proposal.

## Context and Orientation

The reviewed inventory remains in:

- `artifacts/controller_audit_register.md`;
- `artifacts/child_package_register.md`; and
- `artifacts/controller_contract_test_roadmap.md`.

The execution protocol is:

`prompts/active/controller_contract_audit_iteration_prompt.md`.

GOV-00A publishes the concise convention. DOM-01 at
`docs/work-packages/20260727_watar_ui_contract_pilot/` is first.

## Plan of Work

### Milestone 1: Close the concise convention

Remove current-authority requirements for obligation registries, generated
indexes, manifests, diff engines, consumer graphs, attestations, and new CI.
Publish the exact one-controller test seam and simplicity/stop-loss rules.

Acceptance: DOM-01 can begin without SHR or GOV-01 prerequisites.

### Milestone 2: Execute one controller

For the selected controller:

1. record concise intended fields/actions;
2. inspect actual template/controller/parser/state/RQ/reload paths;
3. write actual-render and applicable focused downstream tests;
4. reproduce confirmed mismatches;
5. patch one mismatch at a time;
6. run cheap focused checks before existing broad gates;
7. review actual production patches proportionally; and
8. close the package with runtime, mismatch, helper, and remaining-gap results.

If no mismatch exists, retain the tests and close the covered behavior.

### Milestone 3: Continue sequentially

Choose the next register entry after the current controller closes. Incidents or
operator priorities may reorder the backlog. Do not activate multiple controller
packages merely to accelerate the inventory.

### Milestone 4: Five-controller value review

After five controllers, measure:

- mismatches found;
- regressions sensitive to reintroduced defects;
- focused/broad runtime;
- helper lines versus controller-test lines;
- false tooling failures; and
- operator effort.

Continue the loop if it provides positive value. Tooling expansion requires a
specific measured miss or repeated burden, two simpler alternatives, and
explicit operator approval.

## Concrete Steps

For each controller, begin with repository search and focused tests. The WATAR
package contains its exact first command set. Common closeout gates are:

    wctl run-npm lint
    wctl run-npm test
    python wepppy/weppcloud/controllers_js/build_controllers_js.py
    wctl run-pytest <exact-affected-tests>
    wctl doc-lint --path <changed-doc>
    git diff --check

Run the controller build only after controller source changes. Run
`wctl check-rq-graph` only after enqueue/dependency changes. Cheap render, lint,
and focused tests always precede broad execution.

## Validation and Acceptance

A controller is verified only when actual-render tests cover risk-bearing field
identity/state and applicable downstream tests cover serialization, parsing,
persistence/reload, and RQ. Inapplicable layers need no artificial N/A artifact.

Production patches must be limited to confirmed mismatches, preserve
compatibility by default, and carry required correctness/security review based
on actual changed behavior.

## Idempotence and Recovery

Use isolated fixtures and preserve unrelated worktree changes. Never edit
generated bundles directly. If intent is ambiguous, stop. If shared changes lack
direct-consumer coverage, narrow or defer them. If tooling triggers a stop-loss,
remove or simplify it before continuing.

## Interfaces and Dependencies

GOV-00A produces the test convention. The register supplies backlog identity.
Each controller package produces tests, minimal repairs, measured runtime, and
evidence about whether a small helper is useful.

No controller depends on GOV-01. Shared package references describe code context,
not completion gates.

## Outcomes & Retrospective

DOM-01 closed with actual-render, controller, route, persistence, and RQ
coverage; its historical selector mismatch was already fixed, so it needed no
production repair. The affected Python set (111 tests), frontend lint, and full
frontend suite (88 suites, 662 tests) passed. It introduced no test helper or
false tooling failure. Preserve the initial scaffold as superseded history in
git rather than current authority. At each five-controller review, record
whether the loop remains net-positive and whether any tooling proposal passes
the simplicity budget.
