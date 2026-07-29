# Tracker - SURF-14 Pure UI User Profile/Session Contract

## Status

Verified 2026-07-28 UTC.

## Progress

- [x] Registered SURF-14 after verified SURF-13.
- [x] Ratified the read-only metadata, owned-continuation, privileged token,
  session, and role-mutation ownership contract.
- [x] Inventoried and directly rendered every profile state.
- [x] Executed the actual token client and retained route/session evidence.
- [x] Removed the misowned Dev role-mutation control and repaired prefix-aware
  password navigation.
- [x] Completed reviews, focused/broad validation, parent reconciliation,
  commit, and clean closeout.

## Decisions

- Profile account metadata is read-only; no profile-edit mutation exists.
- Root-only role/account mutation remains solely owned by SURF-15.
- Browser reset remains a Diagnostics continuation and inherits REM-04 evidence.
- Token mint claims, lifetime, roles, and scopes remain unchanged.

## Conformance Classification

The package applies the concise intent in `package.md`, the canonical CSRF and
session contracts, and existing route authorization. Direct regressions
confirmed and closed the Dev/Root role-mutation mismatch and the proxy-prefix
password-link mismatch. No token, provider, session, or role authority was
widened.
