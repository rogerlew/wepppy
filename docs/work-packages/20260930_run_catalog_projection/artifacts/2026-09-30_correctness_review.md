# Correctness and user-experience review — run catalog projection

## Metadata and status

Reviewer: Dirac, independent read-only `reviewer` agent
`01a0f460-85ce-7b71-9137-0ceea20a52e8`. Date: 2026-09-30 UTC.
Reviewed specification commit: `62d4273d9006156745649b12f3bb96225cb5042f`.
Runtime baseline: `c8497e2cbf210ebc74ef51e2c73cb5351373da2f`.
Authority: [catalog specification](../../../schemas/run-catalog-projection-contract.md).
Initial contract-only verdict: **HOLD**, with two medium and one low finding.
Final independent contract-only verdict: **PASS**, after two amendment rounds.
Runtime tests/deployment are future gates, not claimed by this review.

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

| ID | Severity | Finding | Author disposition |
| --- | --- | --- | --- |
| COR-01 | Medium | TTL failed-source retention conflicts with ready-only expiry CHECK | Clear stored expiry on failure; preserve prior observation time and successful Ron updates; require recovery transition test |
| COR-02 | Medium | Finalizer-gated pending state lacks a recoverable completion predicate | Define metadata readiness independent of job completion; specify partial/failed/lost-event/restart behavior and initial optional-TTL failure visibility |
| COR-03 | Low | Null policy bypasses the original CHECK through SQL three-valued logic | Require null-safe `IS TRUE`; specify constraint truth table |
| COR-04 | High | Application rollback removes redaction while terminal diagnostics remain public | Require compatible public serializers throughout retained job lifetime, including rollback |
| COR-05 | Medium | Reserved prefix conflicts with canonical identifier generation | Explicit catalog-only prefixed UUID exception and exact-string handling; duplicate of SEC-05 |

Exact references, scenario, remedies, and other review obligations are in the
[disposition record](2026-09-30_contract_review_disposition.md). No risk acceptance
was requested. Reviewer found no additional blockers in the existing locking
intent but requires future coordinator-loss, revision, UUID, and coalescing
tests. The scheduler wakeup and portable extraction details were also clarified.

Dirac confirmed COR-01 through COR-05 closed and supported SEC-04 closure;
no new blocking contradictions were found. Independent post-fix verdict: **PASS**.
Operator detailed-policy ratification
and runtime correctness/UX sign-off remain separate requirements.
