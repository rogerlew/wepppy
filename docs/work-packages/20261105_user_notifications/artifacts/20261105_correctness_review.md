# Notification design correctness and UX review

Reviewer: independent `notification_correctness_review` agent (reviewer role).
Date: 2026-11-05 UTC. Starting revision: `5fb446744d1e5d0e193c3d3aa2cf2dc040e22823`.
Scope: proposed notification contract, package/checkpoint/tracker and ExecPlan,
compared with current Flask, scheduler and deployment sources. Read-only review;
no runtime tests. Primary agent retained this report from the review response.

## User outcome and valid-state coverage

The proposed workflow is a quiet inbox with persisted read state, current-page
bulk selection, sorting and pagination. The contract/plan enumerate absent and
empty inboxes, populated read/unread data, resolved/unavailable history, missing
legacy TTL, revoked membership, deleted registrations, and hostile input.
Actual persistence, middleware, concurrency and browser evidence remains pending.
The planned semantic chain is TTL bytes → worker → database rows → API/Jinja →
browser actions; highest supported completion claim is reviewed design only.

## Findings

| ID | Severity | Finding | Required correction | Disposition |
| --- | --- | --- | --- | --- |
| COR-01 | Medium | Draft required CSRF 403 and blanket API 401, conflicting with global Flask 400/precedence in app.py | Preserve 400 `csrf_failed` and middleware order; test authentication separately | Closed by independent recheck |
| COR-02 | Medium | Forest real-worker preflight preceded migration; no bounded fixture scope | Migrate with schedule disabled before candidate/preflight; scope both candidate creation and reconciliation | Closed by independent recheck |
| COR-03 | Low | “Nightly” suggested a fixed UTC clock while scheduler is startup-relative and defaults to jitter | Specify task timing/restart behavior without introducing scheduler machinery | Closed by independent recheck |

## Initial verdict

Hold for two medium findings; no high findings. The remaining design is bounded:
additive PostgreSQL, Flask ownership, badge-only attention, current-page selection,
persistent read state, retry-safe episodes, unchanged deletion eligibility and
explicit forest versus forest1 scope. The plan provides meaningful real database,
TTL-byte, authorization, pagination, browser and runtime evidence requirements.

## Final design disposition

Independent reviewer confirmed all three findings closed on 2026-11-05 UTC;
no remaining high/medium findings. Suitable for the pre-implementation checkpoint.
Implementation correctness/UX review
must still use the repository correctness template with actual evidence; this
document does not certify test results, migration safety or deployed behavior.
