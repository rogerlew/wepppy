# Verify the Pure security and authentication form contract

This ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Keep
`Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes &
Retrospective` current.

## Purpose / Big Picture

A visitor or authenticated user can complete each supported Flask-Security
form through the Pure shell with honest fields, layered CSRF/CAP controls, safe
errors, and correct continuation behavior. Direct rendering and hermetic route
tests make the contract observable without sending email or using external
identity providers.

## Progress

- [x] (2026-07-28 UTC) Scaffolded SURF-13 and ratified concise intent.
- [x] (2026-07-28 UTC) Traced templates, Flask-Security configuration/hooks, routes, forms,
  tokens, email, session/cookies, logging, and existing tests.
- [x] (2026-07-28 UTC) Added direct render and hostile-value evidence for every form/email family.
- [x] (2026-07-28 UTC) Retained route, CAP, CSRF, OAuth, logging, and session evidence.
- [x] (2026-07-28 UTC) Confirmed conformance; no production repair was required.
- [x] (2026-07-28 UTC) Completed reviews, focused/broad gates, records, commit, and clean closeout.

## Surprises & Discoveries

- Observation: SURF-13 inherits substantial REM-03/REM-04 authentication and
  origin-hardening evidence, but the register still lacks a finite direct
  rendered-template matrix.
  Evidence: existing tests emphasize hooks, cookies, CAPTCHA, OAuth, and emails
  rather than the complete security template family.

- Observation: WEPPcloud's passwordless request template posts to `/login`,
  which initially looked anomalous but exactly matches the installed
  Flask-Security canonical template.
  Evidence: local installed package template comparison and direct-render
  assertion.

- Observation: Independent review identified evidence weaknesses in the first
  test draft, not production defects: login/registration were absent from the
  finite matrix, and email escaping could pass if identity output vanished.
  Evidence: both cases are now positive-presence regressions.

## Decision Log

- Decision: Treat Flask-Security endpoint/form behavior and the canonical CSRF
  and session contracts as simultaneous authority.
  Rationale: templates customize presentation but must not redefine
  authentication semantics.
  Date/Author: 2026-07-28 / Codex applying existing security contracts.

- Decision: Test shared helpers only as encountered by concrete SURF-13 forms.
  Rationale: SHR-01 and SHR-02 are deferred producer audits; the roadmap permits
  finite consumer evidence without advancing those owners.
  Date/Author: 2026-07-28 / Codex applying the one-controller roadmap.

- Decision: Retain Flask-Security as the route/token behavior authority and
  prove WEPPcloud-owned presentation and extensions directly.
  Rationale: duplicating the framework's internal route suite would create a
  synthetic second implementation; configuration, exact actions, custom CAP,
  cookies, logging, OAuth boundaries, and escaping are the local seams.
  Date/Author: 2026-07-28 / Codex after implementation trace.

## Outcomes & Retrospective

SURF-13 closed as a test-and-documentation-only conformance package. Eleven
new Python tests comprise nine direct renders for all material form families
and hostile output plus two actual login/register submissions proving
CSRF-before-CAP enforcement. Two Jest tests execute the actual CAP and
password-toggle scripts. The focused auth boundary passed 85 tests and
configuration passed 16. Independent review strengthened login/registration,
route composition, and email positive-presence evidence, and the dedicated
security gate passed with no unresolved findings. No production repair, queue
change, dependency, or controller build was required. Frontend lint and all 95
suites/694 tests passed; final broad Python passed 5,517 tests with 58 skips.

## Context and Orientation

`wepppy/weppcloud/templates/security/` overrides Flask-Security templates while
retaining its forms and endpoints. `wepppy/weppcloud/routes/_security/` and
application configuration add WEPPcloud CAP, OAuth, cookie/session, logging, and
redirect behavior. The canonical CSRF and session contracts govern browser
requests and persistent authentication.

## Plan of Work

Inventory the actual template inheritance, macros, fields, actions, messages,
scripts, and email links. Render every material form with realistic and hostile
form doubles. Inspect Flask-Security configuration and WEPPcloud request/
response hooks, then run and extend existing real-app tests for CAP, CSRF,
remember cookies, OAuth boundaries, email templates, and token continuations.
For each mismatch, retain the failing regression and apply the smallest
contract-compatible repair.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-pytest tests/weppcloud/test_auth_cap_captcha.py \
      tests/weppcloud/test_auth_remember_cookie.py \
      tests/weppcloud/test_security_email_templates.py \
      tests/weppcloud/routes/test_security_oauth_routes.py \
      tests/weppcloud/routes/test_security_oauth_callback.py \
      --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_security_auth_forms.py \
      tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260728_pure_ui_security_auth_forms_contract
    wctl doc-lint --path docs/work-packages/20260716_pure_ui_contract_standardization_c
    git diff --check

Run a controller build only if controller source changes. Run
`wctl check-rq-graph` only if queue wiring changes; neither is expected.

## Validation and Acceptance

Acceptance requires rendered evidence for every form and email family; exact
action, method, field, CSRF, CAP, error, and navigation behavior; real route
evidence for CSRF-before-CAP login/registration rejection; cookie/session and
non-disclosure evidence; and no unresolved high or medium review finding. A
production patch requires independent correctness and security review.

## Idempotence and Recovery

Tests use local Flask applications, temporary databases/sessions, fake mail,
and deterministic form/token doubles. They do not create production users,
send email, or call OAuth providers. Repeated execution is safe. The child
commit is the restore point for closeout.

## Artifacts and Notes

The evidence matrix is `artifacts/field_matrix.md`. The required high-impact
review is `artifacts/2026-07-28_security_review.md`.

## Interfaces and Dependencies

Retain Flask-Security forms/endpoints, Jinja autoescaping, WEPPcloud CSRF and
CAP guards, configured session/remember-cookie hooks, mail templates, and token
continuations. Add no dependency, endpoint, identity field, role, token format,
password policy, cookie default, or account mutation.

Revision note: created 2026-07-28 for the registered SURF-13 audit.
