# Seamless WEPPcloud Session Cookie Namespace Migration

**Status**: Bearhive rehearsal in progress; production deployment prohibited

## Overview

Move `wepp.cloud` from the generic Flask `session` cookie to
`__Host-weppcloud_session` without requiring logout, login, cookie clearing, or
loss of active session state. A bounded dual-read migration will adopt valid legacy
Redis sessions and reissue the same session ID under the new name while
preserving logout authority.

## Trigger and User Experience

The recorder CSRF incident exposed widespread authenticated session churn: the
browser retained remembered identity but did not present a stable Flask session,
causing CSRF failures. The repair is complete only when ordinary users can
continue working across deployment without instructions to clear site data or
authenticate again. Active form state and run-page workflows must survive the
cutover.

## Scope

Included:

- ADR-0044 and amendments to the session and CSRF contracts.
- A bounded duplicate-preserving parser with explicit downgrade and logout
  protections.
- Flask-Session migration adapter that preserves the existing Redis session ID.
- rq-engine session-token bridge dual-read support.
- `SESSION_COOKIE_NAME=__Host-weppcloud_session` for `wepp.cloud`, with an
  explicit unprefixed development/test profile where local HTTP requires it.
- Value-free migration observability, staged rollout, rollback, and retirement
  criteria.
- Unit, integration, browser, mixed-version, security, and live-canary evidence.

Excluded:

- Changing the Flask secret, Redis DB/index, session TTL, remember-token policy,
  CSRF rules, authorization, or cookie security attributes.
- Deleting generic legacy cookies during ordinary migration.
- General browser-cookie cleanup or redesigning Flask-Session.
- Cross-origin continuity between `wepp.cloud` and Bearhive development/test
  deployments.

## Deployment Authority

`wepp.cloud` is the only production origin in scope. Bearhive origins,
including `wc.bearhive.duckdns.org` and `wc-prod.bearhive.duckdns.org`, are
development/test environments used to validate the change. They are not
production rollout targets and require no session continuity with
`wepp.cloud`.

## Contract Authority

- `docs/schemas/weppcloud-session-contract.md`
- `docs/schemas/weppcloud-csrf-contract.md`
- `docs/dev-notes/auth-token.spec.md`
- `docs/dev-notes/weppcloud-session-lifecycle.spec.md`
- `docs/adrs/ADR-0044-seamless-weppcloud-session-cookie-namespace-migration.md`

This is an intended session default and compatibility-policy change. The
contract checkpoint, ADR, independent reviews, and disposition must be accepted
and committed as a standalone ancestor before production implementation edits.

## Security Impact

High. The work parses signed browser credentials, selects authenticated session
state, and changes the cookie consumed by Flask and rq-engine. Dedicated
security, governance/UX, operations, correctness, and QA reviews are mandatory.

## Acceptance Criteria

- A browser with one valid legacy session receives the new cookie carrying
  the same signed SID and remains authenticated with CSRF state intact.
- A browser with one invalid and one valid duplicate legacy cookie adopts the
  valid Redis-backed session without user action.
- A correctly signed candidate is authoritative; later duplicates cannot
  silently select another account or revive an explicitly ended session.
- Presence of the new cookie always wins; legacy values cannot override it.
- rq-engine accepts new and safely selected legacy cookies throughout rollout.
- Users without remember tokens retain valid active sessions during cutover.
- No migration response deletes generic `session` cookies.
- A two-phase reader-first/name-flip deployment and safe rollback are tested.
- Safari, Chromium, and Firefox live canaries show stable session IDs, heartbeat
  success, recorder 204, token-bridge success, and no new login prompt.
- Rollback preserves both old and new browser state and requires no user cleanup.

## Deliverables

- `prompts/active/session_cookie_namespace_migration_execplan.md`
- `artifacts/contract_checkpoint.md`
- `artifacts/regression_risk_register.md`
- `artifacts/review_disposition.md`
- `artifacts/rollout_runbook.md`
- `artifacts/bearhive_rehearsal_summary.md`
- `artifacts/final_validation_summary.md`
