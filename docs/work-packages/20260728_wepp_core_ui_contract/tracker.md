# Tracker - DOM-14A WEPP Core UI Contract

Closed 2026-07-28 UTC with render, controller, route/RQ-engine, lint, and docs
validation passing without a production change.

## Prep-Completion Timeout Amendment

- 2026-08-07 04:56 UTC: Complete `wepp1` bootstrap recovery measured
  1,234.117 seconds and created run commit `1e7fb6b`; the four-hour measurement
  lock released successfully.
- 2026-08-07 04:58 UTC: Operator direction recorded as a 3,703-second RQ timeout
  with a proposed 4,003-second lock lifetime. Contract checkpoint, ADR, dual
  review, standalone ancestor, implementation, and validation remain pending.
- 2026-08-07 05:09:55 UTC: Operator explicitly approved the 3,703-second
  timeout, 4,003-second lock lifetime, and two-phase consumer-first rollout.
- 2026-08-07 05:15 UTC: Independent governance and operations/security reviews
  passed after disposition. The checkpoint is accepted and ready for its
  standalone ancestor; implementation remains pending.
- Baseline signal: one confirmed prep-only `JobTimeoutException` at 180 seconds.
  Health target: zero recurrences for 14 days after deployment. Guardrails:
  default-queue wait, finalizer duration, lock contention, and Git errors.
  Owner: WEPPcloud operator. Rollback restores inherited 180/900-second limits.
- Sunset review: 14 days after phase-2 activation the operator records keep,
  reduce, or remove. Keep requires zero repeat timeout signatures and acceptable
  queue occupancy, duration, lock-contention, and Git-error signals.
