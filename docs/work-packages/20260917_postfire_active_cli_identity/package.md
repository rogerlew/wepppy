# Post-fire active CLI identity repair

Status: executing, 2026-09-17 UTC. Owner explicitly requested fixing the concurrent
WEPP/post-fire superseded failure. Prior package remains immutable history.

Scope: M1/M3 active CLI ctime-only drift caused by ordinary hard-link preparation.
Preserve strict other-input identity, selection/owner checks, SQLite guards,
result-artifact publication and actual climate-content invalidation. No new
schema, dependency or infrastructure. No climate/scientific parameter changes.
Security impact high: independent correctness/security contract and final reviews.
Compatibility: hashless legacy snapshots retain strict behavior; no migrations.

Acceptance: failing real-filesystem baseline; positive link creation/removal at
admission, preparation, pre-publication and locked publication; negative content,
selection, symlink and read-race cases; focused/full regression; restart relevant
services after inspecting canonical orchestration; actual overlapping worker and
WEPP materialization on a disposable run. Restore the user's named assessment
through its normal Run flow after verification; preserve prior accepted results
and failed evidence. No production deployment or unrelated project mutation.

[Plan](prompts/active/execplan.md) · [Tracker](tracker.md)
