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
- [ ] Confirm the concise GOV-00A test convention.
- [ ] Record intended and observed risk-bearing fields.
- [ ] Add actual-render tests and reproduce the historical mismatch.
- [ ] Add only the downstream tests applicable to each field.
- [ ] Patch confirmed mismatches one at a time.
- [ ] Run existing gates, review production patches, and close.

## Surprises & Discoveries

- Observation: The controller inventory is a sequential backlog, not evidence
  that a registry or dependency platform is necessary.
- Observation: Hand-authored Jest DOM can agree with controller assumptions
  while the actual Jinja template submits a different field name.

## Decision Log

- Decision: Shared packages and GOV-01 do not block DOM-01.
  Rationale: tests should reveal which shared behavior matters.
- Decision: Direct assertions precede helper extraction.
  Rationale: tooling must demonstrate reduced repetition and clearer evidence.

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
    wctl run-pytest tests/weppcloud/routes/test_watar_bp.py \
      tests/microservices/test_rq_engine_ash_routes.py \
      tests/rq/test_project_rq_ash.py \
      tests/nodb/mods/test_ash_transport_run_ash.py --maxfail=1
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

At closeout record:

- mismatches found and fixed;
- tests that fail when defects are reintroduced;
- focused and broad runtime;
- helper lines versus controller-test lines;
- tooling-caused false failures;
- remaining uncovered WATAR behavior; and
- the next single controller recommended for execution.
