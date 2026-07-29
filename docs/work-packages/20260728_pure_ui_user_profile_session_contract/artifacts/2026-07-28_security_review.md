# SURF-14 Security Review

**Date**: 2026-07-28
**Verdict**: PASS / ship
**Unresolved findings**: 0 high, 0 medium, 0 low

## Scope

The review covered authenticated profile rendering, hostile identity/provider
output, password/logout/Diagnostics continuations, provider disconnect,
personal-token visibility/mint/copy, CSRF ordering, session cookies, and the
removal of the profile role-mutation control.

## Resolved During Review

- Medium: added application-level evidence that missing CSRF fails with 400
  before token role authorization, while valid CSRF reaches the 403 role gate.
- Low: replaced prefix-breaking `../change` with
  `url_for('security.change_password')`; ProxyFix evidence proves
  `/weppcloud/change`.
- Low: added hostile role, provider, and provider-email escaping evidence.

## Confirmed Controls

- `/tasks/usermod/` remains Root-only and the Dev-visible profile mutation UI
  is absent.
- Token mint remains authenticated, role-gated, CSRF-protected, same-origin,
  and `Cache-Control: no-store`.
- The readonly token output uses text content without logging or web-storage
  persistence; Clipboard and bounded fallback paths are covered.
- Provider disconnect remains POST-only, authenticated, owner-filtered,
  CSRF-protected, and prevents removal of the sole sign-in method.
- Logout/session-cookie deletion and Diagnostics ownership remain unchanged.

## Residual Risk

Minted JWTs remain 90-day bearer credentials, and clipboard copies can outlive
the page. These inherited lifetime, scope, and session policies are unchanged
by SURF-14 and disclosed to the user.

## Validation Reviewed

- focused Python profile/security surface: passing;
- actual inline profile Jest: passing;
- frontend lint: passing; and
- `git diff --check`: passing.
