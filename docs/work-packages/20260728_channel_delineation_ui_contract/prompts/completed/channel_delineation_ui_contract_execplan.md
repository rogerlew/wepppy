# Audit the Channel Delineation controller contract

This ExecPlan is a living document. Maintain `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` under
`docs/prompt_templates/codex_exec_plans.md`. Update this tracker and the parent
tracker at each stopping point.

## Purpose / Big Picture

After DOM-05, Channel Delineation has executable evidence that a user's selected
configuration is rendered correctly, reaches the browser request, persists
through the Watershed/RQ path, and reloads. The work is a bounded audit using
existing tests; it is not a new contract platform.

## Progress

- [x] (2026-07-28 UTC) Created DOM-05 package, tracker, and initial field
  matrix.
- [x] (2026-07-28 UTC) Traced current rendered and downstream behavior.
- [x] (2026-07-28 UTC) Added direct actual-render, payload, and persistence
  order evidence for the remaining scoped fields.
- [x] (2026-07-28 UTC) Found no new production conformance mismatch.
- [x] (2026-07-28 UTC) Passed applicable gates and closed without a production
  patch.

## Surprises & Discoveries

- Observation: REM-05 already repaired the depression-smoothing id/name
  mismatch and provides direct regression evidence for that one field.
- Observation: MCL and CSA retain `input_*` rendered names; both controllers
  deliberately normalize them to canonical JSON keys before RQ submission.
  Evidence: `channel_delineation.js` and `channel_gl.js` use `coalesceNumeric`
  with `mcl`/`input_mcl` and `csa`/`input_csa`.
- Observation: WBT least-cost distance remains present in the payload while its
  visibility follows the depression-smoothing selection.
  Evidence: both controllers parse `wbt_blc_dist` unconditionally and the
  worker persists a non-null value before build.

## Decision Log

- Decision: Direct assertions precede any helper extraction.
  Rationale: DOM-01 did not reveal enough repetition to justify shared test
  infrastructure.
- Decision: Treat REM-05 as inherited evidence, not an unfinished prerequisite.
  Rationale: DOM-05 must audit the rest of the controller without reopening a
  closed finite repair.
- Decision: Close with test/documentation changes only.
  Rationale: actual rendered state, both payload paths, and worker persistence
  order conform; a production edit would add regression risk without correcting
  an observed defect.

## Context and Orientation

`wepppy/weppcloud/templates/controls/channel_delineation_pure.htm` is the
actual rendered form. `channel_delineation.js` and `channel_gl.js` are the
legacy and current GL controllers. They submit a JSON payload to the existing
channel route and RQ path. `wepppy/rq/project_rq.py` persists build settings on
`Watershed` before invoking channel construction. REM-05 documents the existing
depression-smoothing repair at
`docs/work-packages/20260728_channel_depression_smoothing_fix/`.

## Plan of Work

First render the actual template with representative Watershed state and compare
its submitted fields and selected states against `artifacts/field_matrix.md`.
Then exercise the existing legacy and GL controller fixtures with representative
settings. Follow each durable field into `project_rq.py` and add only the
focused RQ characterization that proves it persists before build. If a test
finds a mismatch, retain the failing case and make the smallest compatible
repair. Do not alter algorithms, defaults, queue wiring, authorization, or
schema without a separately authorized contract decision.

## Concrete Steps

Run from `/home/workdir/wepppy`:

    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py \
      tests/rq/test_project_rq_mutation_guards.py --maxfail=1
    wctl run-npm test -- channel_delineation channel_gl
    wctl run-npm lint
    wctl run-npm test
    wctl doc-lint --path docs/work-packages/20260728_channel_delineation_ui_contract
    git diff --check

Build generated controllers only after controller source changes. Run
`wctl check-rq-graph` only after queue wiring changes.

## Validation and Acceptance

The rendered form must independently prove submitted names and selected state.
Both controllers must submit the canonical payload. Durable values require
persistence/RQ evidence only where they cross that boundary. A production patch
needs proportional independent review; test/documentation-only work does not.

## Idempotence and Recovery

Use isolated fixtures and do not use production run data. Preserve REM-05
coverage. If a shared repair lacks direct consumer evidence, keep the change
local or defer it. Leave generated bundles untouched unless rebuilt through the
canonical builder.

## Interfaces and Dependencies

DOM-05 consumes the completed GOV-00A convention and REM-05 evidence. DOM-04A
is map context, not a prerequisite for the direct form-to-worker audit. No new
dependency or shared test helper is authorized.

## Outcomes & Retrospective

Closed 2026-07-28. DOM-05 added direct tests, not a helper, for actual rendered
Channel configuration, non-default legacy/GL payloads, and worker persistence
order. No production source changed and no mismatch was found. Validation
passed: 124 focused Python tests, frontend lint, and the full frontend suite
(88 suites, 662 tests). Documentation lint and `git diff --check` passed.
Generated-controller build, RQ graph validation, and production correctness or
security review were not applicable. The audit added zero helper lines and
encountered zero false tooling failures. Select the next controller before
starting another audit.

Revision note (2026-07-28): Closed after focused and full frontend validation;
records the no-patch decision and measured results.

Revision note (2026-07-28): Created for the operator-authorized sequential
DOM-05 audit after DOM-01.
