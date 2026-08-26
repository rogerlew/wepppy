# ADR-0044: Seamless WEPPcloud Session Cookie Namespace Migration

Status: Accepted for Bearhive rehearsal; production activation pending evidence

Date: 2026-08-23

Review Date: Before implementation

## Context

WEPPcloud currently uses Flask's generic default cookie name, `session`. Live
evidence on `wc.bearhive.duckdns.org` shows a browser repeatedly reaching
authenticated routes through its valid remember token while each request
creates a new Redis session containing `_user_id` but no `csrf_token`. The
browser then submits the CSRF token rendered into the page against a different
or absent Flask session and receives HTTP 400 with `The CSRF session token is
missing.`

`wepp.cloud` is the sole production origin for this decision. Bearhive origins,
including `wc.bearhive.duckdns.org` and `wc-prod.bearhive.duckdns.org`, are
development/test deployments used for reproduction and validation only. Their
cookies and sessions do not migrate into `wepp.cloud`.

The server recorded dozens of new sessions for the same authenticated identity
within seconds. A public HTTPS reproduction with one unambiguous cookie
succeeded with HTTP 204, and the corrected recorder Fetch transport is present
in the served bundle. This isolates the remaining failure to ambiguous or
unusable browser session-cookie state, with duplicate generic `session` cookies
across host/domain scopes as the leading explanation.

A direct rename would avoid future collisions but would discard active browser
sessions. Telling users to log out, clear site data, or sign in again is not an
acceptable migration. Some users intentionally opt out of remembered login, so
the remember cookie cannot be the only compatibility path.

## Decision

Change WEPPcloud's production Flask session-cookie name from `session` to
`__Host-weppcloud_session` through a staged, dual-read migration. The prefix
makes browsers reject Domain-scoped, non-root-path, or non-Secure variants.
Production startup MUST fail if those invariants are violated. Explicit local
HTTP configuration may use `weppcloud_session` with the same migration rules.

The new cookie is authoritative whenever its name is present: an invalid or
expired new cookie MUST NOT downgrade to legacy. When the new name is absent, a
migration-aware Redis session interface MUST inspect bounded exact-name legacy
`session` occurrences in wire order before authentication and CSRF hooks run.
Invalid signatures may be skipped. The first correctly signed legacy SID is
authoritative: if its Redis session exists, adopt it; if not, fail closed
without scanning later signed candidates. This preserves explicit logout. The
SID and payload remain unchanged, and the response writes that SID under the
new name automatically.

rq-engine's cookie-authenticated session-token bridge MUST implement the same
new-name authority and bounded legacy rules during the compatibility window.

WEPPcloud MUST NOT delete the legacy generic `session` cookie during ordinary
migration. Its domain/path ownership is ambiguous and it may belong to another
application. Once a valid new cookie exists, all WEPPcloud consumers ignore the
legacy name.

No candidate after the first correctly signed SID may authorize the request.
Later signed, live payloads are inspected only for conflict detection. Adoption
requires one authenticated principal across all live candidates; different
principals, authenticated/anonymous conflict, or multiple live anonymous
sessions fail closed. Logout/reset invalidates all presented signed SIDs and
uses a Redis revocation fence against late writes. No credential or identity
value may be logged.

The compatibility reader remains for at least one rolling Redis-session
lifetime plus deployment skew. Retirement requires evidence that new-cookie
adoption is complete across active deployments and a separate reviewed change.

## Decision Provenance

Decision Venue: Codex operator conversation, 2026-08-23 21:30 UTC

Participants Present: WEPPcloud operator, Codex

Decision Owner(s): WEPPcloud operator approval pending; this ADR is a draft

Implementer(s): Pending

## Change Summary

| Behavior | Current | Proposed |
| --- | --- | --- |
| Flask cookie name | `session` | `__Host-weppcloud_session` in production |
| Existing valid session | Read only through generic name | Adopted automatically and reissued under the new name |
| Duplicate legacy cookies | Flask selects first; rq-engine selects last | Skip bad signatures; first signed SID is authoritative |
| rq-engine bridge | Reads `SESSION_COOKIE_NAME` or `session` | Prefers new name and safely accepts legacy during migration |
| Legacy-cookie deletion | Not applicable | Never deleted by ordinary migration |
| User action | Current failures may require cookie clearing | No logout, site-data clearing, or routine reauthentication required |

Cookie security attributes, Redis DB 11, the `session:` key prefix, the
12-hour rolling inactivity lifetime, session signing secret, remember-token
policy, CSRF policy, and authorization policy remain unchanged.

## Rationale

A WEPPcloud-specific `__Host-` name prevents sibling and parent domains from
planting a colliding owned cookie. Reusing the validated legacy SID preserves
payload, CSRF state, login freshness, CAP state, and run markers without copying
or transforming user data. Dual-read support makes rolling and staggered
deployments safe. Refusing ambiguous cross-identity selection prevents a UX fix
from becoming an account-confusion vulnerability.

## Alternatives Considered

1. Ask users to clear cookies or log in again. Rejected because it externalizes
   deployment cleanup to every user and violates the session contract's UX
   priority.
2. Rename the cookie without compatibility reading. Rejected because users
   without a valid remember token would be logged out and active form state
   could be lost.
3. Rely only on remember-token restoration. Rejected because remembered login
   is optional and restoration does not preserve CSRF, CAP, freshness, or other
   active session state.
4. Delete every legacy `session` cookie variant. Rejected because WEPPcloud
   cannot prove ownership of generic parent-domain or path-scoped cookies.
5. Keep the generic name and retry CSRF failures in JavaScript. Rejected because
   HttpOnly cookie ambiguity cannot be repaired safely from JavaScript and
   retries can create mutation uncertainty.
6. Scan past a correctly signed legacy SID whose Redis record is absent.
   Rejected because it can undo explicit logout and resurrect a later session.
   Skipping values that cannot be signed by WEPPcloud remains safe.
7. Use load-balancer affinity. Rejected because the failure is browser cookie
   ambiguity, not worker-local server state, and affinity would not establish
   cookie ownership.

## Consequences

Active users with a recoverable legacy session migrate on their first response,
including a first POST, without noticing. New cookies become authoritative
immediately. Unrecoverable state fails closed; Flask-Login restoration remains
available when a remember token is valid.
The migration adds temporary complexity to both Flask and rq-engine cookie
loading and requires coordinated configuration across services.

The legacy generic cookie remains in the browser until its owning scope expires
or removes it, but WEPPcloud ignores it after migration. Operators gain bounded,
value-free counters for migration outcomes so adoption and ambiguity can be
measured without collecting credentials.

## Evidence

- Triggering run:
  `https://wc.bearhive.duckdns.org/weppcloud/runs/soft-boiled-copying/disturbed9002_wbt/`.
- Observed response: HTTP 400 `csrf_failed`, detail `The CSRF session token is
  missing.`
- Redis DB 11 inspection on 2026-08-23 found 244 authenticated sessions without
  CSRF state, 11 authenticated sessions with CSRF state, and dozens of new
  sessions for one identity within seconds.
- A controlled Bearhive HTTPS session with one cookie returned HTTP 204 from the
  recorder endpoint.
- Work package:
  `docs/work-packages/20260823_session_cookie_namespace_migration/`.

## Risk and Rollback Notes

Primary risks are cross-account candidate selection, login loops, CSRF/session
desynchronization, rq-engine bridge failures during mixed-version rollout,
unbounded parsing of hostile Cookie headers, and accidental deletion of
unowned cookies. Tests and reviews must close each risk before implementation.

Rollback MUST retain the new-cookie and migration reader; an unmodified old
image is unsafe after new logins occur. The application MUST NOT dual-write the
generic cookie or delete the new cookie. Rollback is triggered by increased authentication
401/403/400 rates, account-identity mismatch evidence, token-bridge failures,
or session creation rates that remain abnormal after deployment.

## Implementation Notes

Implement migration in the session interface before request hooks so the first
request may be a CSRF-protected POST. Preserve duplicate exact-name occurrences
from the raw header. Cap header bytes and candidate count, validate signatures
before Redis access, and avoid broad exception swallowing. Share semantics
between Flask and rq-engine even if framework adapters differ.

Add value-free metrics or structured logs for `new_cookie`, `legacy_adopted`,
`legacy_bad_signature`, and `legacy_signed_sid_missing`. Keep compatibility for
24–48 hours after the last cutover, then retire only in a separate reviewed
release. Do not record credential or identity values.
