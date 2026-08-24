# Bearhive Rehearsal Summary

**Environment**: `https://wc.bearhive.duckdns.org` (development/test)
**Production impact**: None; `wepp.cloud` was not changed
**Status**: Partial pass; authenticated browser and recovery gates remain

## Deployment

The WEPPcloud and rq-engine services were recreated/restarted with migration
support. Redis and RQ workers were not restarted or flushed. Effective runtime
configuration was inspected in both services:

- primary cookie: `__Host-weppcloud_session`
- legacy cookie: `session`
- migration: enabled
- primary attributes: Secure, HttpOnly, Path `/`, no Domain
- Flask interface: `MigratingRedisSessionInterface`

Both the WEPPcloud page and rq-engine health endpoint returned HTTP 200 after
restart.

## Passing Evidence

- A controlled HTTPS request presented an unrelated invalid `session` cookie
  before a correctly signed, Redis-backed legacy cookie. The response was HTTP
  200 and issued `__Host-weppcloud_session` with the exact existing SID.
- The issued cookie was Secure, root-path scoped, and had no Domain attribute.
- A credentialed browser login explicitly disabled remember-me, retained only
  the signed legacy `session` cookie, and waited while WEPPcloud restarted. The
  next authenticated profile load adopted the legacy state, issued
  `__Host-weppcloud_session` with the identical signed SID, retained valid CSRF
  state for the rq-engine-token POST, showed no login prompt, and issued no
  remember cookie (Playwright: 1 passed).
- Operator-observed heartbeat on the supplied Bearhive run passed in the
  migrated browser session: `POST /weppcloud/api/session/heartbeat` returned
  HTTP 204, carried `__Host-weppcloud_session` and `X-CSRFToken`, did not
  redirect to login, and did not issue a remember cookie.
- Operator-observed recorder requests on the same migrated run returned HTTP
  204, closing the triggering CSRF failure. An SBS upload also completed
  through rq-engine from that browser session, demonstrating the authenticated
  mutation path without a login prompt or browser-state reset.
- Operator-observed job polling remained functional through both the run page
  and the job dashboard, confirming rq-engine token/status continuity for both
  browser consumers.
- The operator reported no console authentication or CSRF errors. Two transient
  WebSocket hiccups were observed; polling and the tested workflows remained
  functional, so they are retained as a restart-era observation rather than
  classified as a session-migration failure.
- Operator inspection confirmed that `__Host-weppcloud_session` rotates across
  logout and subsequent login. Legacy generic cookies remained present as
  designed, and no cookie values were retained in rehearsal evidence.
- A live browser lifecycle canary verified remembered login issues the remember
  cookie, logout removes it before any subsequent login and rotates the primary
  SID, and an explicit remember-me opt-out login does not reissue it
  (Playwright: 1 passed). The canary's CAP solver was also corrected to handle
  the accepted one-hex-character difficulty target.
- Focused migration/configuration/rq-engine regression suite: 118 passed.
- Repository-wide Python regression suite: 6,684 passed, 63 skipped.
- Full frontend suite: 105 suites and 773 tests passed; frontend lint passed.
- Test-stub and changed-file broad-exception gates passed.
- Independent security review required and verified central four-day SID
  tombstones for all `token_class=session` authorization paths, bounded parsing,
  fail-closed signer configuration, and atomic anonymous-to-authenticated SID
  rotation.
- Independent QA verified over-bound reads suppress remembered-login recovery
  and logout/reset revokes all signed candidates within the raw-header bounds.

## Not Yet Proven

- Authenticated browser continuity with remember disabled across Chromium,
  Firefox, Safari, and Edge.
- Real browser first-request form/CSRF, heartbeat, recorder, and rq-engine token
  mint on an operator-controlled run.
- Logout/reset and concurrent late-response behavior through the live routes.
- Mixed-version activation and migration-aware rescue-image recovery.

Local password login was temporarily enabled for the controlled Bearhive
rehearsal. The smoke harness's post-login probe was corrected to use a
credentialed same-origin browser Fetch rather than Playwright's API client,
which lacked browser Origin/Fetch Metadata and was correctly rejected by the
same-origin guard. The authenticated profile and runs-dashboard Playwright
tests then passed (2 passed); the profile scan reported zero accessibility
violations and the existing dashboard scan reported three.

A recorder POST to the supplied private run reached private-run authorization
rather than the recorder success response. It is intentionally not counted as
a passing recorder canary. No user should be asked to log out, sign in again,
clear cookies, or clear site data during any remaining rehearsal.

## Production Gate

This rehearsal does not authorize deployment to `wepp.cloud`. Complete every
unchecked Phase 0 gate in `artifacts/rollout_runbook.md`, pin and test the rescue
image, capture the production inventory/baselines, and obtain final independent
review sign-off before Phase 1.
