# Verify the Pure user profile/session contract

This ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Keep
`Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes &
Retrospective` current.

## Purpose / Big Picture

An authenticated user can inspect safely rendered account/provider metadata,
follow owned password/logout/reset continuations, and, when authorized, mint
and copy a personal API token. The profile surface cannot silently widen role,
session, provider, CSRF, or token authority.

## Progress

- [x] (2026-07-28 UTC) Scaffolded SURF-14 and ratified concise intent.
- [x] (2026-07-28 UTC) Traced template, inline clients, profile/token routes, provider
  disconnect, password/logout/reset, session/cookies, and existing tests.
- [x] (2026-07-28 UTC) Added direct render, hostile-value, and
  real-inline-client evidence.
- [x] (2026-07-28 UTC) Retained focused route, token, OAuth, CSRF, and session
  evidence.
- [x] (2026-07-28 UTC) Removed the misowned Dev role control and repaired
  prefix-aware password navigation.
- [x] (2026-07-28 UTC) Completed independent reviews, focused/broad gates,
  records, commit, and
  clean closeout.

## Surprises & Discoveries

- Observation: The profile template still renders a Dev-only PowerUser
  checkbox that posts to `/tasks/usermod/`, while the owning route requires
  Root and the register assigns role mutation to SURF-15.
  Evidence: `templates/user/profile.html` and `routes/admin.py::task_usermod`.

- Observation: The relative `../change` password link resolves to `/change`
  from `/weppcloud/profile`, escaping the deployed proxy prefix.
  Evidence: ProxyFix regression for `security.change_password`.

- Observation: Review identified missing direct evidence for hostile provider
  and role output, CSRF-before-role ordering, and both clipboard fallback
  outcomes; each gap was closed before broad validation.

## Decision Log

- Decision: Treat profile metadata as read-only and retain role/account
  mutation under the Root-only SURF-15 owner.
  Rationale: A non-Root profile control cannot satisfy the route authority and
  duplicates a separately registered privileged surface.
  Date/Author: 2026-07-28 / Codex applying the registered ownership boundary.

- Decision: Inherit REM-03/REM-04 cookie/session/reset evidence without moving
  browser deletion back into the profile page.
  Rationale: Diagnostics is the ratified browser-reset owner; profile provides
  only a discoverable continuation.
  Date/Author: 2026-07-28 / Codex applying existing remediation ownership.

- Decision: Generate the password continuation from the Flask-Security
  endpoint rather than a browser-relative path.
  Rationale: `url_for` preserves the configured proxy prefix and keeps route
  ownership with Flask-Security.
  Date/Author: 2026-07-28 / Codex after independent security review.

## Outcomes & Retrospective

SURF-14 closed with direct actual-template evidence for ordinary, privileged,
linked-provider, empty, hostile, and proxy-prefixed states; actual inline
token mint/copy/fallback/error execution; and retained OAuth, CSRF, token,
cookie/session, logout, and Diagnostics evidence. Focused Python passed 70
tests. Focused Jest, frontend lint, and the complete 96-suite/695-test
frontend sweep passed.
The repository-wide Python sweep passed 5,522 tests with 58 skips.

Two production repairs were necessary. The profile no longer offers a
Dev-visible role mutation that only the Root-owned SURF-15 route could honor,
and its password continuation now preserves the `/weppcloud` proxy prefix.
Independent correctness and security reviews passed with no unresolved
findings. No token claim, lifetime, provider, cookie, or session behavior
changed.

## Context and Orientation

`templates/user/profile.html` extends the security shell and contains account
metadata, provider disconnect forms, the optional personal-token panel, and
inline scripts. `routes/user.py::profile` selects token visibility and
`mint_profile_token` issues the personal token. Password change/logout are
Flask-Security routes, provider disconnect is OAuth-owned, and browser reset is
owned by the Diagnostics page.

## Plan of Work

Render real profile states with ordinary, privileged, linked-provider, empty,
and hostile users. Execute both actual inline clients under Jest. Retain real
route evidence for profile authorization, token visibility/claims/errors,
provider disconnect, CSRF, cookie/logout, and browser reset. Establish a
failing regression for any confirmed mismatch before the smallest repair.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-pytest tests/weppcloud/routes/test_user_profile_contract.py \
      tests/weppcloud/routes/test_user_profile_token.py \
      tests/weppcloud/routes/test_security_oauth_routes.py \
      tests/weppcloud/routes/test_csrf_rollout.py \
      tests/weppcloud/test_auth_remember_cookie.py --maxfail=1
    wctl run-npm test -- user_profile_inline
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260728_pure_ui_user_profile_session_contract
    wctl doc-lint --path docs/work-packages/20260716_pure_ui_contract_standardization_c
    git diff --check

Run a controller build only if controller source changes. Run
`wctl check-rq-graph` only if queue wiring changes; neither is expected.

## Validation and Acceptance

Acceptance requires direct evidence for every profile state and owned
continuation, execution of the real inline token client, applicable real route
and session evidence, and no unresolved high or medium review finding. A
production patch requires independent correctness and security review.

## Idempotence and Recovery

Tests use local Flask/Jinja applications, temporary databases, mocked fetch and
Clipboard APIs, and deterministic token fixtures. They do not create
production users, send provider requests, or mint production tokens. Repeated
execution is safe. The child commit is the restore point.

## Artifacts and Notes

The evidence matrix is `artifacts/field_matrix.md`. The required high-impact
review is `artifacts/2026-07-28_security_review.md`.

## Interfaces and Dependencies

Retain current Flask-Security routes, OAuth disconnect contract, CSRF/session
guards, token roles/scopes/audiences/lifetime, and response envelopes. Add no
dependency, endpoint, field, role, provider behavior, or account mutation.

Revision note: created 2026-07-28 for the registered SURF-14 audit.
