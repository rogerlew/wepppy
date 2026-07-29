# SURF-14 Pure UI User Profile/Session Contract

**Status**: Verified
**Package ID**: SURF-14
**Security impact**: `high`
**Dedicated security review**: required

## Purpose

Verify the authenticated user-profile surface from actual rendering through
role-gated token minting, linked-provider presentation/disconnect submission,
password/logout/diagnostics navigation, session boundaries, and safe output.

## Concise Intent Contract

The profile page presents the authenticated user's name, email, roles, and
linked providers as escaped read-only account metadata. It offers canonical
password-change, logout, Diagnostics browser-reset, and provider-disconnect
continuations without redefining their owning route contracts.

Only users with the existing Admin, PowerUser, Dev, or Root role can see and
use the personal API-token panel. Mint requests remain same-origin,
CSRF-protected, authenticated, role-gated, no-store responses. The token is
shown only after a successful explicit mint and can be copied without storage
or logging by the profile client.

The profile page does not grant or revoke roles. Root-only account and role
mutation belongs to SURF-15 and `/tasks/usermod/`; controls that cannot satisfy
that authority boundary are absent. Browser-state deletion remains owned by
the Diagnostics page and REM-04. SURF-14 adds no profile-editing field, role,
token scope/lifetime, provider operation, cookie/session default, or account
deletion behavior.

## Scope

- `wepppy/weppcloud/templates/user/profile.html`;
- `wepppy/weppcloud/routes/user.py::{profile,mint_profile_token}`;
- the inherited provider-disconnect, password-change, logout, and Diagnostics
  destinations as consumed by the profile page;
- profile token inline client behavior and existing authentication,
  authorization, CSRF, token-claim, cookie/session, and browser-reset tests; and
- direct rendered-template, hostile-value, route, client, and security evidence.

## Exclusions

SURF-15 owns root user lookup and role/account mutation. OAuth provider
protocol behavior remains under its existing owner. Password rules, token
claims/lifetime, browser-reset implementation, cookie/session defaults, user
schema, runs catalog, and account deletion are unchanged.

## Acceptance

Actual rendering proves escaped account/provider data, role-selected token
controls, exact action/endpoint identity, CSRF fields, readonly token output,
copy/mint states, and canonical navigation. Inline tests execute the real
profile scripts. Existing route tests are retained only after inspection and
execution. Any ownership mismatch receives a failing regression before the
smallest contract-compatible repair. Independent correctness/security review,
focused and broad validation, documentation lint, a child commit, and a clean
worktree are required.

## Outcome

SURF-14 verified the profile contract and required two narrow production
repairs. The Dev-visible PowerUser checkbox and its client were removed because
they targeted the Root-only SURF-15 mutation boundary. The password link now
uses `url_for('security.change_password')`, preserving the `/weppcloud` proxy
prefix.

Direct rendering covers ordinary, privileged, linked-provider, empty, hostile,
and proxy-prefixed states. The actual inline token client covers mint, copy,
fallback, and error behavior. Focused Python passed 70 tests; focused Jest,
frontend lint, and the complete frontend suite passed. Independent correctness
and security reviews passed with no unresolved findings. The repository-wide
Python sweep passed 5,522 tests with 58 skips.
