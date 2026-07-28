# Ratify the concise Pure UI controller test convention

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` current in accordance with
`docs/prompt_templates/codex_exec_plans.md`. Update the GOV-00A and umbrella
trackers at each stopping point.

## Purpose / Big Picture

GOV-00A now has one job: publish the smallest convention needed to test and
repair one controller at a time. It distinguishes intended behavior from
observed behavior, requires actual-render and applicable downstream tests, and
defines when a small test helper may be extracted.

GOV-00A does not build an obligation registry, generated index, validator,
manifest, change classifier, dependency engine, attestation system, or CI
workflow.

## Progress

- [x] (2026-07-17) Recorded contract-first precedence and bounded-remediation
  history.
- [x] (2026-07-20 through 2026-07-28) Recorded and reviewed REM-01 through
  REM-05 governance milestones without advancing borrowed controllers.
- [x] (2026-07-28) Operator replaced the platform-first architecture with a
  controller-by-controller tests-first loop.
- [x] (2026-07-28 10:20Z) Published the concise controller test convention.
- [x] (2026-07-28 10:20Z) Reconciled umbrella, reusable prompt, register, and
  developer guidance.
- [x] (2026-07-28 10:20Z) Passed documentation validation and one proportional
  independent review with no remaining high/medium findings.
- [x] (2026-07-28 10:20Z) Closed GOV-00A and unblocked DOM-01 WATAR/Ash.

## Surprises & Discoveries

- Observation: The controller count caused planning to expand into two
  registries, a derived index, a change-aware gate, fan-out mappings, and eight
  prerequisite scaffolds before the first controller test.
  Evidence: the superseded 2026-07-28 registry/enforcement scaffold.

- Observation: This repeats the TESTGATE failure pattern documented in
  `/workdir/openWEPP/docs/work-packages/20260723-testgate-incompatible-recovery-receipt-001/artifacts/testgate-trajectory-and-value-assessment.md`:
  infrastructure was allowed to precede demonstrated product value.

- Observation: The useful seam is simple: actual rendered name/value through
  serialization, parsing, persistence, and reload.

## Decision Log

### 2026-07-28: Controller tests are the execution unit

**Decision**: Execute one controller at a time. Write actual-render and focused
downstream tests, patch confirmed mismatches minimally, retain regressions, and
move to the next controller.

**Rationale**: Inventory size does not require a control plane.

### 2026-07-28: Tooling follows repetition

**Decision**: Begin with direct assertions. Extract a stateless test helper only
after at least two tests repeat the same logic and the helper makes assertions
clearer.

**Rejected**: obligation registries, generated indexes, manifests, diff engines,
consumer graphs, attestations, machine ancestry checks, and new CI workflows.

### 2026-07-28: Review actual risk

**Decision**: Test/documentation-only work starts with security impact `none`.
One independent correctness review covers a production patch. Dedicated
security and second reviews are triggered by the actual patch, not the
controller's hypothetical maximum surface.

## Context and Orientation

The reviewed controller and surface registers remain inventory. The active
execution model is:

`docs/work-packages/20260716_pure_ui_contract_standardization_c/artifacts/controller_contract_test_roadmap.md`.

The reusable loop is:

`docs/work-packages/20260716_pure_ui_contract_standardization_c/prompts/active/controller_contract_audit_iteration_prompt.md`.

The first controller package is:

`docs/work-packages/20260727_watar_ui_contract_pilot/`.

Existing shared contracts remain authoritative where applicable. Source and
tests demonstrate observed behavior; they do not invent intent.

## Plan of Work

### Milestone 1: Publish the concise convention

Update `docs/ui-docs/controller-contract.md` or one small linked document to
require:

- distinct DOM id, submitted name, option token, parser key, persisted
  attribute, and reload value;
- actual-render evidence for template/macro output;
- focused serialization, parser, persistence/reload, and RQ evidence only where
  applicable;
- tests before production repair when practical;
- one mismatch and minimal compatible patch at a time; and
- direct assertions before helper extraction.

Do not create a schema or generated index.

Milestone acceptance: a maintainer can start DOM-01 without interpreting a
registry or producing governance artifacts unrelated to its tests.

### Milestone 2: Reconcile current guidance

Update the umbrella package, tracker, register, reusable prompt, active plan,
and `PROJECT_TRACKER.md`. Remove the rejected prerequisite spine and make
GOV-01 a deferred value evaluation after five controllers.

Preserve historical remediation artifacts as history; do not rewrite their
then-applicable decisions.

### Milestone 3: Validate and close

Run scoped documentation lint, spelling preview, reference checks, and
`git diff --check`. Obtain one independent review of whether the convention is
clear, executable, low-regression-risk, and free of platform requirements.
Disposition findings proportionally and close GOV-00A.

## Concrete Steps

Run from `/home/workdir/wepppy`:

    wctl doc-lint --path \
      docs/work-packages/20260716_pure_ui_contract_ratification
    wctl doc-lint --path \
      docs/work-packages/20260716_pure_ui_contract_standardization_c
    wctl doc-lint --path docs/ui-docs/controller-contract.md
    rg -n "contract-obligations|change-aware|no-impact attestation|manifest" \
      docs/work-packages/20260716_pure_ui_contract_ratification \
      docs/work-packages/20260716_pure_ui_contract_standardization_c \
      PROJECT_TRACKER.md
    git diff --check

Search results in preserved historical review artifacts are not current
authority and do not require rewriting.

## Validation and Acceptance

GOV-00A is accepted when:

- DOM-01 has no shared-package or GOV-01 prerequisite;
- the one-controller loop begins with actual-render tests;
- tooling extraction requires demonstrated repetition;
- test/documentation work has no hypothetical security artifact;
- production patches remain small and compatible;
- cheap focused checks precede broad suites;
- stop-loss and five-controller value review are explicit; and
- current authoritative docs contain no requirement to build the rejected
  registry/enforcement platform.

## Idempotence and Recovery

All changes are documentation and process guidance. Preserve unrelated worktree
changes and historical review evidence. If the convention grows into a schema or
orchestration system, stop and reduce it before closing GOV-00A.

## Interfaces and Dependencies

GOV-00A produces only the concise test convention consumed by each controller
package. The umbrella register supplies backlog identity. Controller packages
produce tests, minimal repairs, runtime measurements, and evidence for whether
small helpers are useful.

GOV-01 consumes nothing automatically. It may be proposed only after five
controller packages demonstrate a measured miss or repeated burden and the
operator explicitly approves the proposed component.

## Outcomes & Retrospective

GOV-00A closed with `docs/ui-docs/controller-contract.md` as the current concise
convention. It requires actual rendered evidence, defines the finite
risk-bearing inclusion/exclusion rule, limits downstream tests to seams a value
reaches, and requires tests-first minimal compatible repair.

No obligation registry, generated index, manifest, change classifier, consumer
graph, attestation, or new CI workflow was created. Scoped documentation lint,
spelling preview, reference checks, the root AGENTS size gate, and
`git diff --check` passed. Independent review initially found one medium
definition gap and one low scope ambiguity; both were fixed, and the final
verdict was PASS with no remaining high/medium findings.

DOM-01 can start immediately. It has no SHR or GOV-01 prerequisite.

Revision note (2026-07-28): Closed the plan after publishing and reviewing the
operator-directed concise convention; recorded the outcome and DOM-01 start
condition so the completed plan is self-contained.
