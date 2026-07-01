# Add Cap.js to Local Auth Pages

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document follows `docs/prompt_templates/codex_exec_plans.md` from the repository root.

## Purpose / Big Picture

WEPPcloud already uses Cap.js to protect anonymous create, fork, and route-view flows. The local password login and account registration pages still accept public POSTs without Cap.js verification. After this change, a user visiting `/login` or `/register` will see a Cap.js prompt and the server will require a valid `cap_token` before local password login or account creation can succeed. OAuth links remain ordinary links and are not part of the local password form.

## Progress

- [x] (2026-07-01 15:40 UTC) Read repository, work-package, auth, and Cap.js integration instructions.
- [x] (2026-07-01 15:40 UTC) Created package scaffold, tracker, and security review placeholder.
- [x] (2026-07-01 16:05 UTC) Implemented Flask-Security form validation for login/register `cap_token`.
- [x] (2026-07-01 16:05 UTC) Rendered Cap.js prompt, hidden token, and widget assets on login/register templates.
- [x] (2026-07-01 16:20 UTC) Added focused tests for templates and form validation.
- [x] (2026-07-01 16:30 UTC) Updated docs, security review, tracker, and package closeout.
- [x] (2026-07-01 16:35 UTC) Ran focused tests, npm checks, syntax check, real app render checks, and doc lint.

## Surprises & Discoveries

- Observation: Login and registration POST handling is owned by Flask-Security; WEPPcloud only wraps the login view in `routes/_security/ui.py`.
  Evidence: `wepppy/weppcloud/app.py` initializes `Security(app, user_datastore, register_form=ExtendedRegisterForm, confirm_register_form=ExtendedRegisterForm)`.
- Observation: Flask-Security supports a custom `login_form` argument.
  Evidence: local inspection of `Security.__init__` showed `login_form` alongside existing `register_form` and `confirm_register_form` parameters.
- Observation: WTForms did not collect `cap_token` when the field lived only on a plain mixin, even though the validator method could be inherited.
  Evidence: real `/login` render showed no `cap_token` until `cap_token = StringField(...)` was declared directly on `ExtendedLoginForm` and `ExtendedRegisterForm`; direct form inspection then listed `cap_token` in both field sets.
- Observation: The current dev app renders `/login` as OAuth-only, while `/weppcloud/register` renders the local registration form.
  Evidence: test-client render check showed `/login` omitted `cap_token`/`cap-widget` when local login is disabled, and `/weppcloud/register` included both.

## Decision Log

- Decision: Add a shared form-validation mixin and pass custom login/register form classes to Flask-Security.
  Rationale: This keeps Flask-Security responsible for account lookup, password validation, registration, CSRF, and messages while adding the missing Cap.js gate at the existing form boundary.
  Date/Author: 2026-07-01 / Codex
- Decision: Use the existing shared Cap.js prompt macro and widget asset contract instead of adding a new widget style.
  Rationale: Existing create/fork pages already document and test this integration pattern, and reusing it minimizes UI and service contract drift.
  Date/Author: 2026-07-01 / Codex
- Decision: Declare `cap_token` directly on concrete Flask-Security subclasses and keep the shared validator in `CapTokenFormMixin`.
  Rationale: WTForms field collection did not pick up fields from a plain mixin in this context, while direct declarations preserve testable shared validation behavior.
  Date/Author: 2026-07-01 / Codex
- Decision: Gate login Cap assets behind `local_login_enabled`.
  Rationale: OAuth-only login pages should not load Cap assets or show hidden token wiring when no local password form exists.
  Date/Author: 2026-07-01 / Codex

## Outcomes & Retrospective

Completed. The package adds server-enforced Cap.js validation to local login and registration forms, renders Cap.js UI only where the corresponding local form exists, and keeps OAuth provider links outside the token-gated form. The Playwright smoke helper now solves login-page Cap challenges through the Cap challenge/redeem API before submitting `dev-agent` credentials. Follow-up is limited to a deployed browser smoke with a live Cap service after rollout.

## Context and Orientation

`wepppy/weppcloud/app.py` creates the Flask app, configures Flask-Security, defines SQLAlchemy models, and registers custom forms. A Flask-Security form is the Python object that validates a submitted auth form before login or account creation occurs. `wepppy/weppcloud/templates/security/login_user.html` renders the local password login form and optional OAuth provider links. `wepppy/weppcloud/templates/security/register_user.html` renders the account creation form. `wepppy/weppcloud/templates/shared/cap_macros.htm` renders a Cap.js prompt and `<cap-widget>`. `wepppy/weppcloud/utils/cap_verify.py` posts a token to the Cap service `siteverify` endpoint and returns the verification payload.

Cap.js is a CAPTCHA service. In this repository, the browser receives a public `CAP_SITE_KEY`, solves a challenge, and submits the resulting token as `cap_token`. The server validates the token using `CAP_SECRET`; clients never receive the secret.

## Plan of Work

First, add `wepppy/weppcloud/auth_forms.py` with a shared validator mixin and concrete `ExtendedLoginForm` and `ExtendedRegisterForm` classes. Each concrete class declares a `StringField` named `cap_token` and validates it by calling `verify_cap_token`. The validator emits a generic validation error when the token is missing, verification raises `CapVerificationError`, or the returned payload does not include `success: true`. It does not log or expose raw token values. `wepppy/weppcloud/app.py` imports these classes and passes `login_form=ExtendedLoginForm`, `register_form=ExtendedRegisterForm`, and `confirm_register_form=ExtendedRegisterForm` to `Security(...)`.

Second, update `login_user.html` and `register_user.html` to import the shared Cap macro, render a prompt and hidden form field inside each local form, and load `widget.js` plus `floating.js` in the page script block. The templates should use defaults compatible with the existing Cap pages: `cap_base_url` defaults to `/cap`, `cap_asset_base_url` defaults to `${cap_base_url}/assets`, and `cap_site_key` defaults to an empty string if not configured. The OAuth provider links stay outside the local login form.

Third, add tests under `tests/weppcloud/`. Template tests render the auth pages with minimal fake forms and assert the prompt, hidden field, widget endpoint, scripts, and OAuth-only suppression are present. Form tests monkeypatch the Cap verification helper and assert missing, rejected, exception, and accepted token paths without hitting the network.

Fourth, update `docs/ui-docs/cap-js-captcha-auth.md`, complete the security review artifact, update the tracker/package closeout, and run focused validation.

## Concrete Steps

Run commands from `/home/workdir/wepppy`.

1. Edit implementation and tests:
       apply_patch ...
2. Run focused tests:
       wctl run-pytest tests/weppcloud/test_auth_cap_captcha.py --maxfail=1
   Result: 8 passed.
3. Run JavaScript syntax and frontend checks:
       node --check wepppy/weppcloud/static-src/tests/smoke/a11y/axe-runs0.spec.js
       wctl run-npm lint
       wctl run-npm test
   Result: syntax check passed; lint passed; Jest reported 84 suites and 607 tests passed.
4. Run real app render checks:
       wctl exec weppcloud python - <<'PY'
       from wepppy.weppcloud.app import app
       with app.test_client() as client:
           for path in ('/login', '/weppcloud/register'):
               response = client.get(path)
               text = response.get_data(as_text=True)
               print(path, response.status_code, 'cap_token=' + str('cap_token' in text), 'cap_widget=' + str('cap-widget' in text))
       PY
   Result: `/login` was OAuth-only and omitted Cap assets; `/weppcloud/register` rendered `cap_token` and `cap-widget`.
5. Lint changed docs:
       wctl doc-lint --path docs/work-packages/20260701_auth_cap_captcha/package.md
       wctl doc-lint --path docs/work-packages/20260701_auth_cap_captcha/tracker.md
       wctl doc-lint --path docs/work-packages/20260701_auth_cap_captcha/artifacts/2026-07-01_security_review.md
       wctl doc-lint --path docs/work-packages/20260701_auth_cap_captcha/prompts/completed/implementation_exec_plan.md
       wctl doc-lint --path docs/ui-docs/cap-js-captcha-auth.md
       wctl doc-lint --path wepppy/weppcloud/README.md

Expected focused pytest outcome is all selected tests passed. Expected doc lint outcome is no errors.

## Validation and Acceptance

Acceptance is met. Tests prove that the login and register templates render the Cap.js prompt and scripts when local forms are present, that OAuth-only login suppresses Cap assets, and that form-validation tests require and validate `cap_token`. A human can also start WEPPcloud, visit `/login` when local login is enabled or `/weppcloud/register`, solve the Cap.js prompt, and submit the forms; missing or failed verification keeps the form from succeeding.

## Idempotence and Recovery

The edits are additive. Re-running tests is safe. If the Cap service is misconfigured in a deployed environment, local login/register fail explicitly rather than silently accepting submissions without CAPTCHA. Roll back by reverting `wepppy/weppcloud/auth_forms.py`, the `app.py` form wiring, auth template/CSS changes, and the smoke helper/docs updates, then redeploying the previous auth templates.

## Artifacts and Notes

Focused validation:

    tests/weppcloud/test_auth_cap_captcha.py ........ [100%]
    Test Suites: 84 passed, 84 total
    Tests: 607 passed, 607 total
    /login 200 cap_token=False cap_widget=False
    /weppcloud/register 200 cap_token=True cap_widget=True

## Interfaces and Dependencies

Use existing dependencies only:

- `flask_security.forms.LoginForm` and `RegisterForm` remain the base classes.
- `wtforms.StringField` stores submitted `cap_token`; templates render it as `type="hidden"` to avoid `hidden_tag()` duplication.
- `wepppy.weppcloud.utils.cap_verify.verify_cap_token(token: str) -> dict` performs server verification.
- `wepppy.weppcloud.templates.shared.cap_macros.cap_prompt(...)` renders the widget.

Revision note 2026-07-01 15:40 UTC: Initial self-contained execution plan created from local code discovery and user request.
Revision note 2026-07-01 16:35 UTC: Plan updated with implementation details, validation evidence, and closure outcome.
