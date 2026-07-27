# ADR-0028: Rolling 90-Day Remembered Login

Status: Accepted

Date: 2026-07-27

Review Date: 2026-10-25

## Context

Users reported that WEPPcloud required password login too frequently. Production
inspection found that server-side Redis sessions use a rolling 12-hour
inactivity lifetime and browser session cookies are nonpermanent. Although
`SECURITY_DEFAULT_REMEMBER_ME` was true, the production login checkbox rendered
unchecked. Users who did not select it therefore lost authentication when the
browser session ended or the Redis session expired.

The configured remember-cookie lifetime was 30 days and did not refresh with
activity.

## Decision

Render "Remember me on this device" selected by default on password-login GET
requests while preserving the user's ability to clear it before submission.
Use a rolling 90-day browser inactivity lifetime for opted-in users. Keep the
rolling 12-hour Redis
session inactivity window, Secure and HttpOnly cookie attributes, SameSite=Lax,
and explicit logout clearing behavior.

## Decision Provenance

Decision Venue: Codex operator conversation, 2026-07-27 19:09 UTC

Participants Present: WEPPcloud operator, Codex

Decision Owner(s): WEPPcloud operator

Implementer(s): Codex

## Change Summary

| Parameter | Previous | Accepted |
| --- | --- | --- |
| Login checkbox | Configured true but rendered unchecked | Rendered checked on GET |
| Remember lifetime | 30 days | 90 days |
| Remember refresh | Disabled | Opt-in-aware refresh |
| Redis session inactivity | 12 hours rolling | 12 hours rolling, unchanged |

## Rationale

A selected-by-default checkbox makes the configured intent visible and gives
users a clear opt-out on shared devices. A rolling 90-day remembered login
reduces repeated credential entry for active users while preserving explicit
logout and shared-device opt-out.

## Alternatives Considered

1. Keep the existing 30-day absolute lifetime - rejected because users reported
   excessive reauthentication and the default checkbox was ineffective.
2. Make Redis sessions permanent - rejected because it conflates active browser
   sessions with remembered identity and increases server-side session
   retention.
3. Remember every login without an opt-out - rejected because shared-device
   users need an explicit way to avoid persistence.
4. Use Flask-Login's global refresh setting - rejected because version 0.6.3
   creates a remember cookie even after `remember=False`, defeating opt-out.
   Refresh must be conditional on a valid remember cookie already being present.

## Consequences

Active users who accept the default remain remembered while they use WEPPcloud
at least once per 90 days. Theft of a copied token can therefore remain
replayable until the user's `fs_uniquifier` changes. Secure,
HttpOnly, SameSite=Lax, signed-token, user-validation, and logout controls remain
required.

## Evidence

- Production inspection on `wepp1`, 2026-07-27 19:09-19:12 UTC.
- 405 Redis session keys all had TTLs within the rolling 12-hour window.
- Production login HTML rendered the remember checkbox without `checked`.
- `docs/work-packages/20260727_auth_session_persistence_hardening/`.

## Risk and Rollback Notes

Monitor unexpected remembered-session use, logout failures, and authentication
complaints through 2026-10-25. A policy rollback restores the 30-day,
nonrefreshing default, reverts the checked-by-default form behavior, marks this
ADR superseded, and amends the session contract. It does not shorten cookies
already issued by browsers. Immediate containment requires rotating an affected user's
`fs_uniquifier`, which invalidates all of that user's remember tokens. Keep the
independent logging/redaction repair in place. Do not weaken Secure, HttpOnly,
SameSite, signature, or logout controls.

## Implementation Notes

Flask-Security assigns the field default after WTForms has processed the field,
so configuration alone does not make the rendered checkbox checked. The custom
login form must set field data only when no POST form data exists; submitted
opt-out values must remain authoritative.

`REMEMBER_COOKIE_REFRESH_EACH_REQUEST` remains disabled because its global
behavior violates explicit opt-out in the pinned Flask-Login version.
WEPPcloud must implement opt-in-aware refresh only when a valid remember cookie
is already present.
