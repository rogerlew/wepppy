# Post-fire active CLI identity repair

Status: Closed 2026-09-17 UTC. Owner explicitly requested fixing the concurrent
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

[Completed plan](prompts/completed/execplan.md) · [Tracker](tracker.md)


Delivered: contract checkpoint `567eacf7d`, main implementation `2b00c4165`,
final conformance repair `1003fe9ad`. Final correctness/security reviews PASS.
The earlier package repaired accepted-result freshness but missed active worker
admission/publication and source-preparation rebasing; this package closes those
boundaries while preserving strict legacy, other-source and artifact checks.

Validation: full main-repair suite 8,971 passed / 99 skipped; final corrections
107 boundary tests, 21 preparation tests and two final native legacy tests pass.
Actual overlapping WEPP materialization succeeds; changed bytes reject. Relevant
services restarted. Final named job `0c3bb451-0e7a-4814-95f5-3f1d2f219d49`
finished with a current report after reload, verified downloads and unchanged
scientific source hashes. [Runtime acceptance](artifacts/runtime_acceptance.md).

Durable decision and rationale:
[active CLI amendment](../../schemas/file-dependency-freshness-contract.md#2026-09-17-active-cli-hard-link-amendment)
and the linked M1/M3 domain amendments. No formula, climate, auth or queue-wiring
changes. Recorder/startup admission contention remains a separately documented
UX follow-up; it did not require bypassing locks or changing user configuration.
