# Tracker - Seamless Session Cookie Namespace Migration

## Quick Status

**Started**: 2026-08-23 21:45Z
**Current phase**: Bearhive rehearsal implementation
**Last updated**: 2026-08-23 23:15Z
**Next milestone**: Implement the accepted contract and focused regressions.

## Task Board

### In Progress

- [ ] Implement cross-principal detection, logout fencing, and reader-first
  deployment support.
- [ ] Complete production inventory, thresholds, and executable commands in
  `artifacts/rollout_runbook.md`.

### Ready

- [ ] Obtain explicit operator acceptance of the final contract checkpoint.
- [ ] Commit the accepted checkpoint as a standalone ancestor.
- [ ] Implement shared bounded cookie-candidate parsing and selection.
- [ ] Implement Flask and rq-engine migration adapters.
- [ ] Add configuration/docs and mixed-version rollout support.
- [ ] Execute focused, broad, browser, and live-canary validation.
- [ ] Complete final correctness, security, operations, UX, and QA reviews.

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

## Decisions Pending Acceptance

- `wepp.cloud` is the sole production rollout origin; Bearhive is dev/test.
- Production cookie name becomes `__Host-weppcloud_session`.
- Valid legacy sessions migrate automatically while preserving the same SID.
- New cookie presence blocks downgrade; legacy lookup is bounded and preserves
  logout authority.
- Ordinary migration never deletes the generic legacy cookie.
- rq-engine dual-reads throughout the compatibility window.
- Invalid signatures may be skipped, but lookup never scans past a signed SID.
