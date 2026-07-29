# SURF-13 Pure UI Security/Auth Forms Contract

**Status**: Verified 2026-07-28
**Package ID**: SURF-13
**Security impact**: `high`
**Dedicated security review**: required and passed

## Purpose

Verify the inherited Pure security-form family from direct rendering through
Flask-Security submission, CSRF/CAP enforcement, session and remember-cookie
behavior, safe errors, email-driven continuation, and authenticated account
mutation.

## Concise Intent Contract

Public login, registration, confirmation resend, forgotten-password, password
reset, and magic-login request forms render the canonical Flask-Security field
names and actions. Login and registration additionally enforce the configured
CAP challenge without bypassing CSRF or Flask-Security validation. User-entered
values and errors remain escaped; passwords, tokens, CAPTCHA values, OAuth
codes, and session identifiers are never reflected or logged.

Authenticated password changes require the canonical current/new password
fields and preserve Flask-Security session invalidation behavior. Logout and
account-exit continuations clear the scoped session and remember cookies
according to the canonical session contract. Email confirmation, reset, and
login links remain server-generated token URLs; templates do not invent,
transform, or expose token contents.

All forms retain their configured Flask-Security endpoint, method, CSRF token,
validation errors, navigation, autofill purpose, and disabled/absent semantics.
The package adds no authentication method, identity field, role, token format,
password rule, cookie lifetime, OAuth behavior, or account-deletion operation.

## Scope

- `wepppy/weppcloud/templates/security/_layout.html`, `_macros.html`,
  `_messages.html`, `_menu.html`, and `_cap_form_script.html`;
- login, registration, confirmation, forgotten/reset/change-password,
  magic-login, welcome, goodbye, and security email templates;
- Flask-Security configuration and WEPPcloud security hooks that directly
  govern these forms;
- existing CSRF, CAP, remember-cookie, OAuth-boundary, email, and session
  regressions; and
- direct render, real route, validation/error, continuation, and security
  evidence.

## Exclusions

No authentication redesign, new route, OAuth provider change, user-profile
editing, root-admin user mutation, role change, password-policy/default change,
token lifetime/format change, deployment proxy change, or account-deletion
workflow is authorized. SURF-14 owns profile/session UI and SURF-15 owns root
user modification.

## Acceptance

Actual rendering proves exact field/action/CSRF/CAP identity, safe values and
errors, autofill hints, navigation, and email links across every form family.
Route tests prove CSRF and CAP composition on public login/registration and
retain existing access, redirect/continuation, cookie/session, OAuth-boundary,
and credential-safe logging evidence. Existing downstream evidence is retained
only after inspection and execution. Focused, frontend, documentation,
security, and broad Python gates are recorded before closeout.

## Outcome

The inherited form, email, CAP, cookie/session, OAuth-boundary, CSRF, and
security-logging implementation conformed without a production repair. Eleven
new Python tests comprise nine direct renders across all material form
families and two real Flask-Security route submissions. They cover escaped
hostile values/errors, welcome/goodbye continuations, every HTML security
email, and CSRF-before-CAP enforcement. The real CAP and password-toggle
scripts are executed under Jest. Focused Python, frontend, independent review,
documentation, and broad-suite results are recorded in the tracker and
completed ExecPlan.
