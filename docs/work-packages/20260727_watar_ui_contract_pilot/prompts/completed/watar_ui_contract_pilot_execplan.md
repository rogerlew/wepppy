# Test and repair the WATAR/Ash controller contract

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` current in accordance with
`docs/prompt_templates/codex_exec_plans.md`. Update this package's tracker and
the parent tracker at each stopping point.

## Purpose / Big Picture

This package makes WATAR/Ash safer by adding tests against the actual rendered
and downstream contract, then repairing only mismatches those tests prove. It is
the first repeatable controller iteration, not a prototype for a governance
platform.

## Progress

- [x] (2026-07-28 UTC) Reframed DOM-01 around tests-first, minimal repair, and
  measured helper value.
- [x] (2026-07-28 10:30Z) Confirmed the concise GOV-00A test convention.
- [x] (2026-07-28 10:30Z) Recorded intended and observed risk-bearing fields.
- [x] (2026-07-28 10:30Z) Added actual-render evidence and retained the
  historical selector-name regression.
- [x] (2026-07-28 10:30Z) Added only applicable downstream evidence, including
  the dedicated wind-toggle persistence path.
- [x] (2026-07-28 10:30Z) Found no new production mismatch; no patch is needed.
- [x] (2026-07-28 10:45Z) Ran applicable frontend and backend gates and closed
  DOM-01 without a production patch.

## Surprises & Discoveries

- Observation: The controller inventory is a sequential backlog, not evidence
  that a registry or dependency platform is necessary.
- Observation: Hand-authored Jest DOM can agree with controller assumptions
  while the actual Jinja template submits a different field name.
- Observation: The historical selector mismatch was already repaired before
  DOM-01 started, but its actual-template regression was narrow.
  Evidence: `test_ash_template_submits_canonical_model_selector_names` existed
  at the start; DOM-01 expanded it to the rendered WATAR field set and paired
  canonical selector persistence with the existing legacy-alias test.

## Decision Log

- Decision: Shared packages and GOV-01 do not block DOM-01.
  Rationale: tests should reveal which shared behavior matters.
- Decision: Direct assertions precede helper extraction.
  Rationale: tooling must demonstrate reduced repetition and clearer evidence.
- Decision: Close without a production patch if actual rendered and downstream
  behavior conforms.
  Rationale: DOM-01 is a conformance audit; inventing a repair would create
  regression risk without fixing a confirmed defect.

## Context and Orientation

Primary sources are `wepppy/weppcloud/controllers_js/ash.js`,
`wepppy/weppcloud/templates/controls/ash_pure.htm`,
`wepppy/weppcloud/routes/nodb_api/watar_bp.py`, the directly used `Ash` NoDb
state, and ash/WEPP RQ paths. Existing tests include:

- `wepppy/weppcloud/controllers_js/__tests__/ash.test.js`;
- `tests/weppcloud/routes/test_watar_bp.py`;
- `tests/microservices/test_rq_engine_ash_routes.py`;
- `tests/rq/test_project_rq_ash.py`; and
- `tests/nodb/mods/test_ash_transport_run_ash.py`.

The current field matrix is `artifacts/field_matrix.md`. The historical
selector test is in `tests/weppcloud/routes/test_pure_controls_render.py`; it
must continue to assert that DOM ids are not submitted names.

Read the nearest WEPPcloud, controller, NoDb, RQ, microservice, and test
instructions before editing their files.

## Plan of Work

### 1. Establish a small field matrix

For each risk-bearing WATAR field, record intended DOM id, submitted name,
allowed token/default, parser key, persisted attribute, reload value, and
whether it reaches RQ. Omit prose about layers that do not apply.

### 2. Write the cheapest crossing test

Render the actual template and assert field identity/state. Add focused
JavaScript serialization/hydration, route parsing, persistence/reload, or RQ
tests only where that field crosses the boundary. Reintroduce the historical
id/name mismatch and prove the regression test fails.

### 3. Repair one mismatch at a time

For each confirmed mismatch, retain the failing test, make the smallest
backward-compatible repair, and rerun its focused tests before continuing.
Avoid shared changes unless a local correction would be wrong.

### 4. Extract tooling only from repetition

After at least two direct test cases, assess whether a small assertion helper
would remove duplication without hiding the field mapping. Keep it in the
existing test tree, stateless, and smaller than the tests using it. Do not add
manifests, generators, change classifiers, or workflows.

### 5. Validate and close

Run focused checks first, then existing frontend/backend suites applicable to
the files changed. Rebuild generated controllers only through the canonical
builder. Re-triage security before a production patch and obtain one
independent correctness review for that patch.

## Concrete Steps

Run from `/home/workdir/wepppy`:

    rg -n "ash|watar|run_ash" \
      wepppy/weppcloud/controllers_js \
      wepppy/weppcloud/templates/controls \
      wepppy/weppcloud/routes/nodb_api \
      wepppy/nodb wepppy/rq tests

Iterate with the exact focused tests identified by the field matrix. Before
closeout run:

    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py \
      tests/weppcloud/routes/test_watar_bp.py \
      tests/microservices/test_rq_engine_ash_routes.py \
      tests/rq/test_project_rq_ash.py \
      tests/nodb/mods/test_ash_transport_run_ash.py --maxfail=1
    # Only after controller source changes:
    python wepppy/weppcloud/controllers_js/build_controllers_js.py
    git diff --check

Run `wctl check-rq-graph` only if enqueue sites or dependency edges change.

## Validation and Acceptance

The historical mismatch must fail when reintroduced. Actual-render tests must
prove submitted names independently of DOM ids. Downstream tests must prove
parser/persistence/reload behavior for durable values and RQ behavior only for
values that cross that boundary.

A passing source-only test is insufficient. A production patch cannot include
unrelated cleanup, refactoring, parameterization, authorization, upload, or
queue changes.

## Idempotence and Recovery

Use isolated fixtures, never production run data. Keep tests deterministic and
avoid global browser/storage state. If intent is ambiguous, stop rather than
encoding current behavior as desired behavior. If a shared repair lacks direct
consumer coverage, narrow or revert it.

## Interfaces and Dependencies

GOV-00A supplies only the concise test convention. DOM-01 may consume existing
shared helpers but does not wait for shared audits. Its test patterns may inform
a helper after repetition; they do not authorize a maintenance platform.

## Outcomes & Retrospective

Closed 2026-07-28. DOM-01 found no new production mismatch. It added direct
tests, not helpers, for actual rendered WATAR field identity, canonical and
legacy selector persistence, and wind-toggle persistence. No controller source,
route, NoDb, RQ, parameterization, authorization, or upload behavior changed.

Validation passed: 111 affected Python tests; frontend lint; and the full
frontend test suite (88 suites, 662 tests). Both the child and umbrella
documentation trees linted with zero warnings, and `git diff --check` passed.
The generated-controller build was not applicable because no controller source
changed. The audit added zero helper lines and encountered zero false tooling
failures. No correctness or security review was required because there was no
production patch. Select the next controller from the register before starting
another audit.

Post-close review closed two low coverage gaps by exercising both wind boolean
values and both rendered reload states. This DOM-01 revision advances the audit
ledger to `verified`, as required by the parent register.

Revision note (2026-07-28): Closed after final validation; records the field
matrix, already-fixed historical mismatch, no-patch decision, and measured
gate results.
