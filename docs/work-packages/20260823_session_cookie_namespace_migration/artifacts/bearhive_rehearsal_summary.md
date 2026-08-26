# Bearhive Rehearsal Summary

**Environment**: `https://wc.bearhive.duckdns.org` (development/test)
**Production impact**: None; `wepp.cloud` was not changed
**Status**: Mixed-version activation passed; deploy-script rollback rehearsal remains

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
- The operator independently confirmed the same password-login behavior in a
  real Bearhive browser: unchecked remember-me produced no remember cookie,
  while checked remember-me issued one. No credential values were recorded.
- The operator confirmed the OAuth lifecycle behaves as designed: successful
  OAuth login carries remembered-login state and logout clears it before a new
  OAuth login. No credential values were recorded.
- The operator exercised Browser Session Reset on Bearhive. Reset logged the
  browser out and rotated the owned and presented legacy session state; the
  private run returned the expected signed-out 404, and signing in normally
  restored authorized access. No manual site-data clearing was required.
- The operator verified concurrent-tab logout propagation: logging out in one
  tab signed out both tabs and the owned primary session rotated in both. This
  closes the concurrent-tab gate but is not treated as proof of a response
  completing after revocation.
- A controlled Bearhive canary used the live Flask session interface and Redis:
  request A loaded an authenticated SID and paused, request B completed logout
  and wrote the revocation tombstone, then request A resumed and returned HTTP
  200. Its late save did not recreate the Redis session, preserved the
  tombstone, and expired the owned cookie. Temporary canary state was removed.
- The operator replayed a previously valid, unexpired rq-engine session JWT
  after logout. rq-engine rejected it with the canonical unauthorized error and
  the message `Session token has been revoked.`; Redis independently showed the
  SID tombstone with approximately the full four-day TTL. No token or error ID
  was retained in evidence.
- Mixed-version activation passed in a controlled no-remember browser. In the
  reader-first phase, web and rq-engine preferred the owned name while
  WEPPcloud continued writing `session`. After both services were recreated
  with the owned writer, the same browser loaded its authenticated profile,
  completed the CSRF-protected token probe, and received
  `__Host-weppcloud_session` with the identical signed SID and no remember
  cookie (Playwright: 1 passed). Redis and workers were not restarted.
- Post-rehearsal review found and closed two mixed-version edge paths before
  handoff: a reader-first writer now expires a distinct authoritative owned
  cookie during SID rotation, logout, reset, and fail-closed repair; rq-engine
  project creation now uses the shared migration-aware cookie selector and
  applies SID tombstones to session-class tokens.
- The one-time activation browser canary is explicitly opt-in so ordinary
  post-activation smoke runs remain repeatable. Production and HPC Compose
  surfaces expose the same web/rq-engine migration variables as Bearhive.
- A post-activation browser canary authenticated without remember-me and
  directly posted to rq-engine's cookie-authenticated `session-token` endpoint
  for the operator-selected private run. It returned HTTP 200 and issued the
  run-scoped browse JWT cookie (Playwright: 1 passed).
- A production-Dockerfile packaging test built an image from source commit
  `42cf8319625a` and pinned locally as image ID
  `sha256:cad002e6aa36e79bfecb48475abe876eaac8b90cf901bc5796fa1d73950e4b18`.
  Web and rq-engine ran from that image without a source bind mount while
  retaining the activated dual-read/single-write configuration. Health,
  authenticated profile, logout/remember opt-out, and direct rq-engine token
  mint passed (3 Playwright tests). The normal activated Bearhive deployment
  was restored afterwards. This proves packaged-image startup, not the canonical
  production deployment workflow.
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
- Recovery from the pinned migration-aware Git revision through
  `scripts/deploy-production.sh` and the installed `wctl` preset.

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
