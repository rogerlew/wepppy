# Verify the Pure Root user-modification contract

This ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Keep
`Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes &
Retrospective` current.

## Purpose / Big Picture

A Root operator can inspect user metadata and safely grant or revoke the four
existing operational roles. The page, browser client, route validation,
database mutation, and re-rendered state agree, while Admin and malformed or
forged requests cannot cross the Root authority boundary.

## Progress

- [x] (2026-07-28 UTC) Scaffolded SURF-15 and ratified concise intent.
- [x] (2026-07-28 UTC) Traced the template, context producer, GET/POST routes,
  datastore persistence, navigation consumers, and existing CSRF evidence.
- [x] (2026-07-28 UTC) Added actual render and real-inline-client evidence.
- [x] (2026-07-28 UTC) Added real route/CSRF/validation/persistence/reload
  evidence.
- [x] (2026-07-28 UTC) Repaired Root authority, strict request validation,
  self-Root protection, error status, and visible safe client feedback.
- [x] (2026-07-28 UTC) Completed security review, focused/broad gates, records,
  commit, and clean
  closeout.

## Surprises & Discoveries

- Observation: The page body and navigation expose user management only to
  Root, while the GET route decorator also admits Admin.
  Evidence: `templates/user/usermod.html`, header consumers, and
  `routes/admin.py::usermod`.

- Observation: The disabled self-Root checkbox has no matching server check,
  so a forged POST can remove the acting user's Root role.
  Evidence: `routes/admin.py::task_usermod`.

- Observation: The POST reads `request.json` directly and does not require a
  literal boolean `role_state`.
  Evidence: malformed input can raise before a contract response, while a
  truthy string can select the grant branch.

- Observation: The inline client reported success and failure only through
  browser console calls, including server error content that can name a user.
  Evidence: actual inline execution of the original template script.

## Decision Log

- Decision: Treat both GET and POST as Root-only.
  Rationale: The registered SURF-15 owner, page body, navigation, and mutation
  authority all identify a privileged Root surface; there is no ratified Admin
  read-only workflow.
  Date/Author: 2026-07-28 / Codex applying existing ownership evidence.

- Decision: Enforce self-Root protection at the server boundary.
  Rationale: A disabled checkbox is not an authorization control, and the
  current UI already communicates that the action is unavailable.
  Date/Author: 2026-07-28 / Codex applying the existing UI invariant.

- Decision: Require a JSON object and literal boolean role state.
  Rationale: Role mutation must not reinterpret strings or malformed bodies as
  authorization-bearing commands.
  Date/Author: 2026-07-28 / Codex applying strict boundary validation.

- Decision: Return invalid mutation requests as canonical HTTP 400 envelopes
  and expose browser results in a text-only live status.
  Rationale: Privileged mutation failure must be machine-visible, accessible,
  safely escaped, and must not rely on developer-console disclosure.
  Date/Author: 2026-07-28 / Codex applying the existing error and UI contracts.

## Outcomes & Retrospective

SURF-15 closed with actual Root/Admin, inventory, empty, hostile, selected,
self-disabled, mutation, and reload evidence; four actual-inline client tests;
and real CSRF, Flask-Security datastore, and SQLite persistence. Focused Python
passed 28 tests, frontend lint and all 97 suites/699 tests passed, and broad
Python passed 5,534 tests with 58 skips.

The GET authority now matches its Root-only owner. Strict JSON/target/role/
boolean validation prevents ambiguous grants, the server prevents self-Root
removal, invalid requests return HTTP 400, and the browser reports success or
failure through escaped live text while rolling back failed controls. The
dedicated security review passed with no unresolved findings. No new role,
account lifecycle operation, session behavior, or dependency was introduced.

## Context and Orientation

`wepppy/weppcloud/templates/user/usermod.html` renders the user table and owns
an inline module that posts checkbox changes.
`wepppy/weppcloud/routes/admin.py::usermod` renders the page, while
`task_usermod` grants or revokes roles through the Flask-Security datastore.
`wepppy/weppcloud/_context_processors.py::_get_all_users` supplies the table.
The global CSRF extension protects the POST before its role decorator runs.

## Plan of Work

Render the actual template for Root, empty, selected, self, and hostile states.
Execute its actual inline module under Jest for grant, revoke, response error,
invalid response, and transport failure. Exercise a real Flask application
with an in-memory database to prove GET/POST authority, CSRF ordering, strict
validation, datastore commit, self-Root protection, and reload. Write failing
regressions before the smallest conformance repairs.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-pytest tests/weppcloud/routes/test_admin_usermod_contract.py \
      tests/weppcloud/routes/test_csrf_rollout.py --maxfail=1
    wctl run-npm test -- usermod_inline
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260728_pure_ui_root_usermod_contract
    wctl doc-lint --path docs/work-packages/20260716_pure_ui_contract_standardization_c
    git diff --check

No controller build or RQ graph check is expected because this package owns an
inline template client and no queue wiring.

## Validation and Acceptance

Acceptance requires exact rendered names, state, authority, endpoint, payload,
CSRF, rollback, persistence, and reload evidence. Admin receives 403 for both
routes. Missing CSRF fails before role authorization. Malformed or ambiguous
input cannot mutate roles. The acting Root cannot remove their own Root role.

## Idempotence and Recovery

Tests use local Jinja/jsdom applications and an in-memory SQLite database.
They do not contact production services or mutate production users. Repeated
execution is safe. The child commit is the restore point.

## Artifacts and Notes

The evidence matrix is `artifacts/field_matrix.md`. The required security
review is `artifacts/2026-07-28_security_review.md`.

## Interfaces and Dependencies

Retain the `admin.usermod` and `admin.task_usermod` endpoints, existing
PowerUser/Admin/Dev/Root role names, Flask-Security datastore, global CSRF
extension, and canonical success/error envelopes. Add no dependency, role,
account operation, session behavior, or queue work.

Revision note: created 2026-07-28 for the registered SURF-15 audit.
