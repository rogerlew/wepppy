# Contract Decision - Authentication Session Persistence Hardening

## Checkpoint Metadata

- **Starting implementation revision**: `4a748774f`
- **Operator authorization**: 2026-07-27 19:09 UTC, "make the fixes in a
  work-package and dispatch dual agent review to verify fixes"
- **Classification**: Intended behavior change plus incident remediation.
- **Bounded authority**: GOV-00A-M1C / REM-03, borrowing SURF-13, SHR-02,
  and SHR-04A.
- **Applicable contracts**:
  `docs/schemas/weppcloud-session-contract.md`,
  `docs/schemas/weppcloud-csrf-contract.md`.
- **Operator UX decision**: 2026-07-27 19:45 UTC. Authentication architecture
  is UX-led; conventional rolling remember cookies and their documented copied-
  token residual risk are accepted to reduce user friction.

## Normative Delta

- Password login renders remembered login selected by default with user opt-out.
- Remembered identity uses a rolling 90-day browser inactivity lifetime with
  refresh restricted to opted-in browsers already carrying a valid token.
- Redis sessions retain the rolling 12-hour inactivity lifetime.
- Authentication logs exclude all credential and token values.
- Safe remember-action telemetry is allowed without cookie values.
- Production security logs persist at `/wc1/logs/weppcloud/security.log`.

## Rationale

Production evidence showed that the existing configured remember default was not
rendered, so most users received only a browser-session cookie backed by a
12-hour Redis session. The existing security file log was disabled by
permissions and container logs included CAPTCHA tokens.

## Compatibility Impact

Authenticated API, OAuth, CSRF, Redis session, cookie name/path, and explicit
logout contracts remain unchanged. Users on shared devices can uncheck remember.
Existing remember cookies remain valid under Flask-Login signing rules.
`REMEMBER_COOKIE_DAYS` remains an explicit operator override. Flask-Login's
unsafe global refresh setting remains disabled.

## Security Impact

The rolling browser lifetime increases exposure if a remember cookie is stolen.
The operator accepts that Flask-Login does not server-expire a copied raw token;
suspected theft is contained by rotating the user's `fs_uniquifier`. Existing
Secure, HttpOnly, SameSite=Lax, signed-token, user-validation, and logout
controls remain mandatory. Improved redaction removes confirmed token disclosure
from logs.

## Alternatives Rejected

- Permanent Redis sessions: excessive server retention and mixed semantics.
- Forced remember with no opt-out: unsafe on shared devices.
- Unbounded remember lifetime: unacceptable credential persistence.
- Global per-request refresh: Flask-Login 0.6.3 recreates remember cookies for
  users who opted out. Opt-in-aware refresh is required instead.
- Server-side per-device token state: rejected absent evidence of a material
  threat because it adds architecture and recovery complexity without improving
  the user-reported friction objective.
- Cookie-value logging: unnecessary secret exposure.
- Logging under `/workdir` or `/var/log`: not writable by production uid 1002.

## Regression Evidence Plan

- Rendered GET checkbox contains `checked`.
- Successful login route tests prove omitted `remember` emits no remember
  cookie, opted-in login emits a 90-day Secure/HttpOnly/SameSite=Lax cookie,
  later opted-in requests roll its expiry, ordinary sessions do not create one,
  and logout expires both cookies with
  matching scope.
- Configuration asserts 90 days, disabled global refresh, and unchanged 12-hour
  Redis lifetime.
- Final-log sentinel tests cover password, CSRF, CAPTCHA, session/remember
  cookies, OAuth/bearer/authorization tokens, case and separator variants,
  nested signal extras, `next`, and referrer inputs.
- Remember-action tests assert only `set`/`clear` metadata.
- File logger tests cover default path, `0700`/`0600` permissions, handler
  deduplication, append-only multi-worker behavior, and visible setup/write
  failures. A production-container check writes and reopens the canonical path.
- Production-compatible Compose config, route non-exposure check, and
  documentation lint pass.

## Rollback

Remember-policy rollback is separate from the log-redaction repair. Restore the
30-day nonrefreshing default, restore unchecked GET behavior, supersede ADR-0028,
and amend the session contract together. Already-issued cookies retain their
browser expiry. Rotate an affected user's `fs_uniquifier` if immediate
invalidation is required. Do not revert token redaction or durable logging.

## Conformance State

Contract amendment and ADR are drafted. Implementation conformance is pending
until the standalone checkpoint ancestor is reviewed and committed.
