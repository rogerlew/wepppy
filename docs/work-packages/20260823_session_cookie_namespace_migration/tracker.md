# Tracker - Seamless Session Cookie Namespace Migration

## Quick Status

**Started**: 2026-08-23 21:45Z
**Current phase**: Production owned-cookie writer observation
**Last updated**: 2026-08-25 02:29Z
**Next milestone**: Review production telemetry and legacy-reader evidence at
2026-08-26 02:20Z; do not retire the legacy reader before that checkpoint.

## Scheduled Follow-up

- [ ] **2026-08-26 02:20Z (24 hours after activation):** Pull aggregate CSRF,
  authentication, session-token, migration rejection/adoption, Redis-session,
  and 5xx signals. Record denominators and explicitly identify telemetry gaps.
- [ ] Review whether legacy-cookie usage is measurable and sufficiently low.
  If it is not measurable, improve aggregate, credential-free telemetry and
  continue dual-reading; do not infer retirement readiness from silence.
- [ ] Open a separate reviewed retirement change before removing the legacy
  `session` reader. No retirement change is part of the writer activation.

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
- [x] Boot-tested a source-independent packaged image on Bearhive, fixed two
  packaging defects, and passed authenticated/rq-engine canaries. This does not
  close the canonical deploy-script rollback gate.
- [x] Added and rehearsed targeted web deployment on forest1. Only `weppcloud`
  and `rq-engine` rotated; workers, Redis, PostgreSQL, Caddy, and scheduler kept
  their exact container IDs, and both public health endpoints passed.
- [x] Deployed reader-first revision `c4f509634` to wepp1 with targeted mode.
  Only web/rq-engine rotated; active worker jobs continued on unchanged worker
  containers, all other recorded container IDs were unchanged, and both public
  health endpoints passed.
- [x] Activated `__Host-weppcloud_session` as the production writer on wepp1
  using targeted mode. Both session consumers retain the legacy reader, only
  web/rq-engine rotated, all non-target container IDs remained unchanged, and
  both public health endpoints passed after the bounded rq-engine startup
  delay.
- [x] Passed the production existing-session browser canary after activation:
  authentication survived hard refresh, heartbeat returned 204, recorder and
  rq-engine paths worked, the owned cookie was issued, and logout propagated
  across tabs without user remediation.
- [x] Confirmed fresh production local and OAuth login remain functional under
  the owned-cookie writer.

## Decisions Pending Acceptance

- `wepp.cloud` is the sole production rollout origin; Bearhive is dev/test.
- Production cookie name becomes `__Host-weppcloud_session`.
- Valid legacy sessions migrate automatically while preserving the same SID.
- New cookie presence blocks downgrade; legacy lookup is bounded and preserves
  logout authority.
- Ordinary migration never deletes the generic legacy cookie.
- rq-engine dual-reads throughout the compatibility window.
- Invalid signatures may be skipped, but lookup never scans past a signed SID.
