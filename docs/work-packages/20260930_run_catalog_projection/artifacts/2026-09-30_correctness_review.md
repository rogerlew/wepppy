# Correctness and user-experience review — run catalog projection

## Metadata and status

Reviewer: unassigned. Date: 2026-09-30 UTC. Scope: specification and future
implementation. Base: `c8497e2cbf210ebc74ef51e2c73cb5351373da2f`.
Authority: [catalog specification](../../../schemas/run-catalog-projection-contract.md).
Gate: **pending / hold**. This is a prepared review artifact, not a completed
independent review. No passing verdict or finding count is asserted.

## User outcome and valid states

Users can browse their authorized project list/map promptly while portable
projects retain file authority. The reviewer must exercise this matrix
independently from mode/scope/input combinations:

| State | Required result | Evidence status |
| --- | --- | --- |
| Standalone without PostgreSQL | Normal project use, no new DB/web import | Pending |
| New registration/unindexed metadata | Scoped pending presentation; eventual normal row | Pending |
| Valid empty project strings/no map | Preserve empty strings; no invented map | Pending |
| Populated current or supported legacy | Equivalent fields and authorized visibility | Pending |
| Missing/invalid Ron | Existing omission with internal classification | Pending |
| Transient source I/O failure | Explicit stale last-good row, or unavailable if never indexed | Pending |
| Missing/invalid/disabled TTL | Null expiry, existing Last Modified display | Pending |
| Hostile identity/path/payload | No unauthorized data access or unsafe reconstruction | Pending |

Database errors remain explicit; a successful project file save is not called
rolled back because its mirror failed. Pending/stale UI and TTL freshness are
intentional detailed deltas requiring review, not discovered implementation policy.

## Required evidence chain

Record actual user/worker mutation, committed source readback, observer outcome,
SQL row and revision, authorized JSON, and rendered table/map. Demonstrate
unchanged source/version files during extraction and preserved model artifacts
through representative save/run/archive/restore. Real SQL/file/process tests
must cover concurrency, crash gap, offline same-size edits, and recovery.

Host evidence is required separately for forest, forest1 test production, and
wepp1, including rollback, observation windows, latency, and complete
reconciliation. Source counts/mtime/RQ SUCCESS are not substitutes for content.

## Findings and sign-off

No independent findings collected yet. Reviewer must enumerate severity,
source, affected valid state, evidence, remedy, and disposition for each finding.
Close all medium/high findings before acceptance. Security review is separate
and cannot substitute for correctness or user-experience approval.
Reviewer sign-off and package-owner disposition: pending.
