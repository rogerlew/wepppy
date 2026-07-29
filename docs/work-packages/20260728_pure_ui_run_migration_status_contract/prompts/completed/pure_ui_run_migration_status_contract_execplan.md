# Verify the run migration status lifecycle

This ExecPlan is maintained under `docs/prompt_templates/codex_exec_plans.md`.
Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes &
Retrospective` current.

## Purpose / Big Picture

An authorized owner or administrator can understand required migrations,
optionally archive, enqueue exactly once, observe bounded and authenticated job
progress through every terminal state, and continue or retry safely.

## Progress

- [x] (2026-07-28 UTC) Scaffolded SURF-08 and ratified concise intent.
- [x] (2026-07-28 UTC) Traced Flask gate/host, template state machine,
  rq-engine migration/job routes, worker, persistence, reload, and tests.
- [x] (2026-07-28 UTC) Added permission-aware direct render and seven real
  inline enqueue/poll/backoff/terminal regressions.
- [x] (2026-07-28 UTC) Passed 225 focused render, Flask, route, job, and worker
  tests.
- [x] (2026-07-28 UTC) Repaired JSON-safe bootstrap, authenticated/confined
  polling, owner/admin enforcement, token-class confinement, submit
  serialization, persistence-before-publish identity, and archive/readonly
  failure mismatches.
- [x] (2026-07-28 UTC) Completed broad validation, independent security review,
  records, commit, and clean closeout.

## Surprises & Discoveries

- Observation: Existing coverage renders the template only with benign default
  context and never executes its inline migration lifecycle.
  Evidence: `test_pure_controls_render.py` has no migration-specific field or
  behavior assertions.

- Observation: The page submitted with a session token but polled jobstatus and
  jobinfo through unauthenticated `getJson`, so required poll-auth mode could
  not complete the lifecycle.
  Evidence: The new real inline test failed by falling through to bare `fetch`
  and passed after both reads used `requestWithSessionToken`.

- Observation: `runid` and `config` were embedded in JavaScript as raw quoted
  Jinja values.
  Evidence: The direct-render regression failed until both values used
  `tojson`.

- Observation: Ownership checks cannot safely interpret machine-token subjects
  as human user IDs, and enqueue-before-persistence can publish an
  undiscoverable duplicate-capable job.
  Evidence: Independent security review reproduced both authorization and
  persistence-order gaps; exact token-collision and persistence-failure
  regressions now pass.

## Decision Log

- Decision: Execute the real inline script using the established final-script
  extraction Jest pattern.
  Rationale: Source inspection cannot prove disabled submission, token
  transport, bounded timers, terminal stop, or escaped results.
  Date/Author: 2026-07-28 / Codex with operator authority.

- Decision: Preserve all server migration, archive, readonly, version, queue,
  authorization, and result semantics.
  Rationale: SURF-08 is a conformance audit, not a migration redesign.
  Date/Author: 2026-07-28 / Codex with operator authority.

- Decision: Use the existing shared run-scoped session-token request for both
  status and terminal jobinfo.
  Rationale: It preserves optional/open deployments while conforming to
  configured required poll auth without introducing another token cache.
  Date/Author: 2026-07-28 / Codex with operator authority.

- Decision: Restrict non-admin migration authority to user/session tokens and
  persist a generated RQ job ID before publishing that same ID to the queue.
  Rationale: Human ownership must not transfer to machine identities, and a
  failed persistence write must leave no queued job that a retry cannot find.
  Date/Author: 2026-07-28 / Codex after independent security review.

## Outcomes & Retrospective

SURF-08 closed with JSON-safe bootstrap, authenticated and confined polling,
owner/admin enforcement, token-class confinement, fail-closed capability
rendering, persistence-before-publish submission, and archive/readonly failure
repairs. Seven real inline Jest tests cover native
archive enqueue, bounded rate-limit backoff, all terminal states, hostile URLs,
escaping, retry, and continuation. 225 focused Python tests cover render,
Flask, rq-engine, job, and worker seams. Frontend lint and
the full Jest suite passed. Broad Python reached 2,462 passed and 40 skipped
before the permitted unrelated GridMET `_FakeUnits.degC` fixture failure.
Independent security review passed with no unresolved high or medium findings.

## Context and Orientation

`runs0` redirects gated older runs to the authorized migration page. Its inline
client submits `create_archive` through the run-scoped session-token helper,
polls canonical job status, fetches terminal jobinfo, and renders continuation
or retry. `migration_routes.py` owns authorization, locks, active-job
rejection, readonly transition, enqueue, and persisted job identity.
`migrations_rq.py` owns archive execution, migrations, version update, readonly
restoration, status publication, and the result consumed by the page.

## Plan of Work

Render the real template across owner, readonly, unauthorized, and current
states. Execute the production inline script with mocked transport, timers,
jobstatus, jobinfo, and navigation. Retain Flask, rq-engine, job-route, and
worker tests after inspecting and running them. Patch only a demonstrated
contradiction of the concise and canonical contracts.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1
    wctl run-npm test -- run_migration_status_inline
    wctl run-pytest tests/microservices/test_rq_engine_migration_routes.py tests/microservices/test_rq_engine_jobinfo.py tests/rq/test_migrations_rq.py --maxfail=1
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260728_pure_ui_run_migration_status_contract
    wctl doc-lint --path docs/work-packages/20260716_pure_ui_contract_standardization_c
    git diff --check

Run the controller build only if bundled controller source changes. Run the RQ
graph check only if queue wiring changes.

## Validation and Acceptance

Acceptance requires actual rendering, executable enqueue/poll/backoff/terminal
behavior, and retained server authorization/lock/worker evidence. All focused,
frontend, documentation, and applicable broad gates pass, except a proven
unrelated pre-existing failure may be recorded exactly.

## Idempotence and Recovery

Tests mock timers, transport, tokens, jobs, files, and navigation and are safe
to rerun. Preserve unrelated work and do not rebuild generated assets without a
controller-source change.

## Interfaces and Dependencies

Preserve the migration page path, `create_archive`, canonical job fields,
terminal states, `rq:enqueue`, session/run claims, active-job key, archive and
readonly semantics, migration result, version update, and project reload URL.

## Revision Notes

2026-07-28: Created from explicit operator direction after SURF-07 closed.
