# Tracker - Seamless Session Cookie Namespace Migration

## Quick Status

**Started**: 2026-08-23 21:45Z
**Current phase**: Bearhive rehearsal implementation
**Last updated**: 2026-08-24 18:25Z
**Next milestone**: Complete remaining browser/state gates and publish the production rescue digest.

## Task Board

### In Progress

- [ ] Complete production inventory, thresholds, and executable commands in
  `artifacts/rollout_runbook.md`.
- [ ] Complete authenticated browser, logout/reset, mixed-version, and rollback
  rehearsal evidence.

### Ready

- [ ] Execute focused, broad, browser, and live-canary validation.
- [ ] Complete final operations and UX reviews after remaining live evidence.

### Done

- [x] Confirmed the repaired recorder transport is served by Bearhive.
- [x] Confirmed a controlled single-cookie HTTPS recorder request returns 204.
- [x] Captured Redis evidence of authenticated session churn without CSRF state.
- [x] Drafted ADR-0044 with a no-logout/no-cookie-clearing product requirement.
- [x] Scaffolded package, tracker, active ExecPlan, checkpoint, and risk register.
- [x] Completed independent correctness, security, operations, and UX reviews.
- [x] Recorded severity-ranked findings and proposed dispositions.
- [x] Scaffolded the phase-gated `wepp.cloud` production execution ledger.
- [x] Ratified the three blocking contracts for Bearhive rehearsal.
- [x] Committed the contract checkpoint as `9f52eb879`.
- [x] Implemented shared bounded cookie selection and Flask/rq-engine adapters.
- [x] Implemented cross-principal fail-closed recovery, logout/reset fencing,
  four-day session-token revocation, and anonymous-to-authenticated SID rotation.
- [x] Configured and restarted only Bearhive web and rq-engine services.
- [x] Passed live health and duplicate legacy-cookie adoption probes.
- [x] Passed 6,684 repository Python tests (63 skipped), 773 frontend tests,
  lint, stub, broad-exception, and documentation gates.
- [x] Closed independent security and QA code gates for Bearhive rehearsal.
- [x] Temporarily enabled Bearhive local login and passed authenticated profile
  and runs-dashboard Playwright probes (2 passed).
- [x] Passed authenticated no-remember legacy-session continuity across an
  actual WEPPcloud restart with identical SID and valid CSRF state.
- [x] Captured operator verification of the migrated session heartbeat: HTTP
  204 with owned cookie and CSRF header, no login redirect or remember cookie.
- [x] Captured operator verification that recorder events return HTTP 204 and
  an SBS upload completes through rq-engine on the migrated session.
- [x] Captured operator verification that job polling works through both the
  run page and job dashboard.
- [x] Captured clean authentication/CSRF console evidence; two transient
  WebSocket hiccups did not interrupt polling or tested workflows.
- [x] Confirmed the owned primary session cookie rotates across logout/login;
  no credential values were recorded.
- [x] Passed live remembered-login -> logout -> opt-out-login lifecycle: logout
  clears remember before re-login and opt-out does not reissue it.
- [x] Captured independent operator confirmation that password-login remember
  opt-in issues the cookie and opt-out leaves it absent.
- [x] Captured operator confirmation of the OAuth remembered-login and logout
  lifecycle on Bearhive.
- [x] Passed Browser Session Reset: logout/session rotation, signed-out private
  run denial, and authorized access restored after normal login.
- [x] Passed concurrent-tab logout propagation: both tabs signed out and the
  owned primary session rotated.
- [x] Passed controlled late-response fencing against live Bearhive Redis: the
  old SID was not recreated, its tombstone persisted, and the late response
  expired the owned cookie.
- [x] Passed derivative credential revocation: rq-engine rejected an unexpired
  session JWT after logout based on the live four-day SID tombstone.
- [x] Passed reader-first mixed-version activation: web/rq-engine read priority
  stayed owned while the writer changed from legacy to owned, preserving SID,
  authentication, CSRF state, and remember opt-out.
- [x] Closed mixed-version review findings: distinct owned-cookie retirement on
  reader-first invalidation/rotation, migration-aware project creation,
  session-token SID revocation, opt-in activation smoke, and production/HPC
  Compose parity.
- [x] Passed a direct post-activation rq-engine session-token mint through
  same-origin browser cookie authentication on the private rehearsal run.
- [x] Built and exercised a source-independent rescue image on Bearhive, fixed
  two image packaging defects found by the rehearsal, passed authenticated and
  rq-engine canaries, and restored the normal deployment without dependency
  recreation.

## Decisions Pending Acceptance

- `wepp.cloud` is the sole production rollout origin; Bearhive is dev/test.
- Production cookie name becomes `__Host-weppcloud_session`.
- Valid legacy sessions migrate automatically while preserving the same SID.
- New cookie presence blocks downgrade; legacy lookup is bounded and preserves
  logout authority.
- Ordinary migration never deletes the generic legacy cookie.
- rq-engine dual-reads throughout the compatibility window.
- Invalid signatures may be skipped, but lookup never scans past a signed SID.
