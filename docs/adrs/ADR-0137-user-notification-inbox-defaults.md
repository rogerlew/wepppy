# ADR-0137: Quiet account notification defaults

Status: Accepted  
Date: 2026-11-05

## Context

Users need notice of recorded upcoming automatic project deletion without repeated
interruptions. The existing stack provides PostgreSQL, Flask sessions and a
startup-relative RQ scheduler.

## Decision

Use a 14-day upcoming window with overdue catch-up, a daily 86,400-second task
with 900-second initial delay and zero jitter, and 100-row pages/bulk actions.
Default ordering is unread first, then newest creation and ID. Server-side read
state persists across retries and sessions. A bell badge is the only attention
cue. Fixed wall-clock nighttime scheduling is not promised.

## Decision Provenance

Decision Venue: operator/Codex conversation, 2026-11-05, UTC records in package.  
Participants Present: requesting operator and Codex; independent design reviewers.  
Decision Owner: requesting operator, ratified by “execute the work-package”.  
Implementer: Codex.

## Change Summary

Previously there was no account notification inbox or population schedule. Add
the above workflow defaults and generic notification/recipient tables. Existing
TTL duration, access refresh, protections and garbage collection remain unchanged.

## Rationale and Alternatives

A daily task and a read/unread inbox reuse existing mechanisms. Popups, email,
real-time transport, repeated reminders and a separate service are excluded to
keep attention and operational cost low. Page-bound selection limits accidental
bulk changes. PostgreSQL survives session/project deletion unlike browser state
or project-local files.

## Consequences

Warnings reflect last observed TTL and can lag visits. Users must return to see
them. Notification delivery does not guarantee a grace period. Read changes and
new arrivals can move offset-paginated rows; no snapshot pagination guarantee.

## Evidence

- [Canonical contract](../schemas/user-notifications-contract.md).
- [Execution package](../work-packages/20261105_user_notifications/package.md).
- [Independent review disposition](../work-packages/20261105_user_notifications/artifacts/20261105_review_disposition.md).

## Risk and Rollback Notes

Enable the new schedule only after migrations and fixture-scoped forest preflight.
On rollback disable admissions, inventory queued tasks and revert application
activation while retaining tables/read state. Never flush Redis or change GC.

## Implementation Notes

No new dependencies, services or queues. Validate real database concurrency,
non-mutating TTL reads, account boundaries, browser actions and scheduled execution.
