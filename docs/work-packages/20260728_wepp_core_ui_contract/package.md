# DOM-14A WEPP Core UI Contract

**Status**: Original audit closed 2026-07-28 UTC; timeout amendment accepted, implementation pending
**Package ID**: DOM-14A  
**Parent**: `20260716_pure_ui_contract_standardization_c`

## Outcome

Actual rendering now proves the core run, executable, watershed action, hint,
and lifecycle targets. Existing controller, Flask, and RQ-engine tests cover
payload coercion, authorization, job enqueue, result hydration, and watershed
preconditions. No production mismatch was found.

## 2026-08-07 Prep-Completion Timeout Amendment

The prep-only terminal RQ job has a 3,703-second execution timeout, based on the
ceiling of three times the 1,234.117-second complete production bootstrap
recovery. Its run-scoped bootstrap Git lock lasts 4,003 seconds so exclusivity
outlives the RQ boundary by five minutes. Other WEPP completion paths retain
their current timeout behavior. Implementation conformance is pending the
standalone checkpoint ancestor described in
`artifacts/2026-08-07_prep_completion_timeout_contract_decision.md`.

The hardening scope is: fix the confirmed prep-only completion timeout without
changing other WEPP completion paths, queue topology, bootstrap Git semantics,
or NFS implementation. The hypothesis is that a 3,703-second job boundary and
4,003-second lock lifetime will eliminate this timeout signature for operations
at or below the measured duration during a 14-day observation window. Primary
health signals are zero repeat `JobTimeoutException` failures in
`_log_prep_complete_rq` and successful prep-completion triggers. Guardrails are
default-queue wait time, finalizer duration, bootstrap-lock contention, and any
Git index/commit error. Revisit or roll back if a finalizer approaches the new
boundary, the default queue incurs material delay, or lock/data-integrity errors
appear.

During the 14-day window, inspect RQ/worker state daily and after each prep-only
finalizer. Fence new prep-only submissions and assess rollback for any repeat
timeout, duration at or above 3,333 seconds, oldest default-queue wait above 10
minutes attributable to finalizers, three or more concurrent prep finalizers
lasting over 10 minutes, lock contention, or any Git/index error. The
WEPPcloud operator owns collection and disposition.

Related precedent is the repository hardening lifecycle and
`wepppy/weppcloud/bootstrap/enable_jobs.py::_bootstrap_enable_lock_ttl_seconds`,
which already couples an RQ timeout to a lock with a 300-second margin. This
amendment reuses explicit evidence, finite limits, observation, and rollback.
Fourteen days after phase-2 activation, the operator must explicitly record
keep, reduce, or remove; keep requires no repeat signature and acceptable
queue/lock guardrails.
