# Verify the DEVAL loading and report handoff contract

This ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Keep
`Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes &
Retrospective` current.

## Purpose / Big Picture

An authorized user can request “Deval in the Details,” receive a cached report
or an honest loading screen, observe bounded progress and errors, and reach the
generated report when rendering finishes. Anonymous traffic also passes the CAP
abuse-control challenge. Direct rendering, execution of the real inline script,
route calls, fake RQ state, worker tests, and filesystem reload make the result
observable.

## Progress

- [x] (2026-07-28 UTC) Scaffolded SURF-18 and ratified concise intent.
- [x] (2026-07-28 UTC) Traced access, CAP, RunContext, cache, RedisPrep, enqueue, worker, status,
  artifact, and existing evidence.
- [x] (2026-07-28 UTC) Added direct render and real inline-client coverage.
- [x] (2026-07-28 UTC) Added route/cache/enqueue/reload and worker coverage.
- [x] (2026-07-28 UTC) Repaired only regressions that prove a contradiction of the unchanged
  contract.
- [x] (2026-07-28 UTC) Completed correctness/security reviews, frontend gates,
  and broad Python validation; the known unrelated GridMET fixture failure
  recurred after 2,462 passes and 40 skips.
- [x] (2026-07-28 UTC) Archived this plan and prepared the atomic child commit
  and clean-worktree verification.

## Surprises & Discoveries

- Observation: The loading page currently has no focused render or executable
  polling suite.
  Evidence: repository search finds worker signature tests but no DEVAL client
  or route contract test.

- Observation: CAP was present but canonical run authorization was absent from
  the DEVAL route body.
  Evidence: the authorization-before-interchange regression failed before the
  `authorize(runid, config)` repair.

- Observation: The loading client treated every non-active, non-failure status
  as success and rendered nested error objects as `[object Object]`.
  Evidence: executable Jest regressions failed for unknown/missing states and a
  canonical nested error message before the fail-closed repair.

- Observation: Independent security review found parent/PUP Redis collisions,
  eager filesystem context before CAP, and symlink escape paths not visible in
  the initial ordinary-root fixtures.
  Evidence: two-parent PUP, registered-blueprint, foreign-job, and symlink
  regressions now cover those boundaries.

## Decision Log

- Decision: CAP and run authorization apply cumulatively.
  Rationale: CAP controls automated abuse; it does not establish permission to
  read or enqueue work for a private run.
  Date/Author: 2026-07-28 / Codex applying existing security contracts.

- Decision: Interpret polling statuses exactly as the canonical RQ schema.
  Rationale: treating unknown or malformed values as success can refresh before
  an artifact exists and hide protocol failures.
  Date/Author: 2026-07-28 / Codex applying the RQ response contract.

- Decision: Store DEVAL PUP tracking in the parent run's RedisPrep and encode
  config/PUP components losslessly.
  Rationale: a PUP leaf name is not globally unique; the parent run is the
  authorization and persistence identity.
  Date/Author: 2026-07-28 / Codex after independent security review.

- Decision: Do not attach the shared eager RunContext preprocessor to the
  WEPPcloudR blueprint.
  Rationale: each run-scoped WEPPcloudR route already resolves context after
  its own guards, while preprocessing occurred before decorators.
  Date/Author: 2026-07-28 / Codex after independent security review.

- Decision: Reject symlinked DEVAL export components, artifacts, and logs.
  Rationale: fixed relative names do not confine I/O when an intermediate or
  target path is a symlink.
  Date/Author: 2026-07-28 / Codex after independent security review.

## Outcomes & Retrospective

SURF-18 now provides executable evidence from the rendered loading host through
CAP and run authorization, cache/enqueue selection, owned job polling, worker
execution, confined logs/artifact, and final reload. The initial expectation
was primarily a missing-test audit; execution instead found and repaired the
authorization and polling defects plus three security boundary defects exposed
by independent review. Focused validation passes 157 Python tests and 5 Jest
tests; the full frontend passes 94 suites and 692 tests. Final security
review passed with no unresolved findings. Broad Python reached 2,462 passes
and 40 skips before the known unrelated GridMET `_FakeUnits.degC` fixture
failure. No SURF-18 failure occurred before that unrelated stop.

## Context and Orientation

`wepppy/weppcloud/routes/weppcloudr.py::deval_details` resolves the run, prepares
query-engine interchange data, chooses a cached artifact or RQ job, and renders
`wepppy/weppcloud/templates/reports/deval_loading.htm`. That template contains
the complete browser polling client. `wepppy/rq/weppcloudr_rq.py` invokes the
weppcloudR container and requires
`active_root/export/WEPPcloudR/deval_<runid>.htm`.

## Plan of Work

Render the actual loading host with ordinary and hostile values. Execute its
real inline script in Jest with deterministic DOM, fetch, response, timer, and
location doubles. Build hermetic Flask/route fixtures around temporary active
roots, fake RedisPrep, fake Redis/RQ jobs, and the real helper functions. Extend
worker tests with fake subprocess and status publication. Retain every
conforming path; for each mismatch, preserve the failing regression and apply
the smallest contract-compatible repair.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-pytest tests/weppcloud/routes/test_deval_loading.py tests/weppcloud/routes/test_pure_controls_render.py tests/rq/test_weppcloudr_rq.py --maxfail=1
    wctl run-npm test -- deval_loading_inline
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260728_pure_ui_deval_loading_contract
    wctl doc-lint --path docs/work-packages/20260716_pure_ui_contract_standardization_c
    git diff --check

Run a controller build only if controller source changes. Run
`wctl check-rq-graph` only if enqueue sites or dependency edges change; the
ratified scope does not authorize either.

## Validation and Acceptance

Acceptance requires combined authorization and CAP evidence, correct cache and
no-cache choices, active-job reuse, exact enqueue inputs, safe direct rendering,
canonical status classification, bounded retry/backoff, explicit errors, real
worker command/output/status evidence, and generated report reload. A production
patch requires independent correctness and security reviews with no unresolved
high or medium findings.

## Idempotence and Recovery

Tests use temporary roots and fake Redis, RQ, subprocess, browser, and timer
state. They never enqueue live work or execute Docker/R. Repeated execution is
safe. The child commit is a restore point if a focused or broad gate fails.

## Artifacts and Notes

The evidence matrix is `artifacts/field_matrix.md`. Record a security review in
`artifacts/2026-07-28_security_review.md` if production code changes.

## Interfaces and Dependencies

Retain Flask, `requires_cap`, canonical run authorization, `RunContext`,
RedisPrep, RQ `Queue` and `Job`, the jobstatus response contract,
`render_deval_details_rq`, Docker/Rscript, StatusMessenger, and the fixed
artifact path. Add no dependency, endpoint, payload, queue edge, or schema.

Revision note: created 2026-07-28 for the registered SURF-18 audit.
