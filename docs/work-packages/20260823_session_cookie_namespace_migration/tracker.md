# Tracker - Seamless Session Cookie Namespace Migration

## Quick Status

**Started**: 2026-08-23 21:45Z
**Current phase**: Bearhive rehearsal implementation
**Last updated**: 2026-08-24 00:45Z
**Next milestone**: Complete authenticated browser and rollback rehearsal gates.

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

## Decisions Pending Acceptance

- `wepp.cloud` is the sole production rollout origin; Bearhive is dev/test.
- Production cookie name becomes `__Host-weppcloud_session`.
- Valid legacy sessions migrate automatically while preserving the same SID.
- New cookie presence blocks downgrade; legacy lookup is bounded and preserves
  logout authority.
- Ordinary migration never deletes the generic legacy cookie.
- rq-engine dual-reads throughout the compatibility window.
- Invalid signatures may be skipped, but lookup never scans past a signed SID.
