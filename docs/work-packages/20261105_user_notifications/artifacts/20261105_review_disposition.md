# Notification design review disposition

Date: 2026-11-05 UTC. Author: primary Codex agent.
Independent reports: [correctness/UX](20261105_correctness_review.md) and
[security](20261105_security_review.md).

## Changes

COR-01 / SEC-01: contract Flask transport and ExecPlan M3 now preserve global
CSRF JSON 400 `csrf_failed` and middleware precedence. Authentication 401 applies
when that boundary is reached. No shared contract/handler exception was introduced.

COR-02 / SEC-02: M5 now orders backup/environment checks, additive migration with
schedule disabled, candidate availability, fixture-scoped preflight, then schedule
activation. `WEPPCLOUD_NOTIFICATIONS_SWEEP_ENABLED` defaults false. Trusted optional
registration-ID scoping constrains both new candidates and previous episodes;
before/after evidence must prove no unrelated recipient rows changed. Scope is
not browser-controlled. Rollback retains tables and handles already queued tasks.

COR-03: contract and M2 specify existing startup-relative scheduler semantics:
86,400-second interval, 900-second initial delay, zero jitter. Restart can cause
an extra idempotent sweep. A fixed nighttime hour is not promised; this clarified
interpretation is part of the proposed contract checkpoint, not an added scheduler.

## Confirmation and scope

Both independent reviewers confirmed closure on 2026-11-05 UTC. Correctness
closed COR-01/02/03; security closed SEC-01/02. No open medium/high design findings.
Security's additional empty-scope no-op regression obligation is now explicit in
the contract and M2. No runtime code,
migration, scheduler setting or deployment changed. Contract ratification, ADR,
standalone ancestor commit and implementation evidence remain future gates.
