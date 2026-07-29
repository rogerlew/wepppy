# SURF-15 Security Review

**Date**: 2026-07-28
**Verdict**: PASS / ship
**Unresolved findings**: 0 high, 0 medium, 0 low

## Scope and Threat Model

The review covered the Root user-management GET and POST routes, actual
rendered user data and role state, the actual inline mutation client, global
CSRF enforcement, Flask-Security authorization and persistence, validation
errors, failure rollback, and reload. Relevant threats were an Admin or
anonymous caller crossing the Root boundary, forged client requests, ambiguous
JSON values changing roles, self-lockout, stored markup execution, CSRF, and
user data leaking through browser logs.

## Resolved Findings

- High: `roles_required('Admin', 'Root')` required both roles and contradicted
  the Root-only owner. The GET now requires exactly Root, matching navigation,
  page content, and the POST.
- High: the disabled self-Root checkbox was only client-side protection. The
  POST now rejects removal of the acting user's own Root role.
- High: string or otherwise non-boolean `role_state` values could select the
  truthy grant branch. The route now requires a literal JSON boolean.
- Medium: malformed/non-object JSON and invalid target values lacked bounded
  validation. They now return canonical 400 error envelopes without mutation.
- Medium: browser errors were console-only and could include target identity.
  The client now uses a text-only live status, reverts the control, and emits
  no user data to console.

## Confirmed Controls

- Anonymous and Admin callers cannot render or mutate the surface.
- Global CSRF rejects the POST before role authorization.
- Only PowerUser, Admin, Dev, and Root are accepted.
- User IDs are integers; email lookup remains case-insensitive; missing and
  unknown targets fail without persistence.
- Grant/revoke uses the existing Flask-Security datastore and commits before a
  successful empty JSON response; redundant mutations return 400.
- Jinja escapes hostile names and email addresses, while client error text uses
  `textContent`.
- The browser sends same-origin credentials and CSRF, disables the active
  control in flight, restores it on failure, and preserves the disabled
  self-Root state.

## Residual Risk

A Root operator can intentionally grant or revoke privileged roles for another
account; that is the purpose of this surface. This package does not add an
audit-log system, session revocation, or account lifecycle controls. Those are
explicit exclusions rather than weakened protections.

## Validation Reviewed

- focused Python: 28 passed;
- actual-inline Jest: 4 passed;
- frontend lint: passed;
- full frontend: 97 suites and 699 tests passed;
- broad Python: 5,534 passed and 58 skipped; and
- broad-exception and whitespace checks: passed.
