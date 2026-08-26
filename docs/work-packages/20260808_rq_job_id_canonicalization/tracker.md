# Tracker – RQ Job ID Canonicalization and Dashboard Compatibility

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-08 21:37 UTC
**Current phase**: Closed
**Last updated**: 2026-08-08 22:05 UTC
**Security impact**: `low`
**Dedicated security review**: `no`

## Progress

- [x] Confirmed production failure is exact-ID mismatch, not queue rank.
- [x] Inventoried preallocated RQ UUID generation sites.
- [x] Amended canonical identifier contract with conformance pending.
- [x] Obtained two independent read-only reviews.
- [x] Dispositioned pre-checkpoint findings.
- [x] Commit standalone checkpoint and verify ancestry (`1778b66d1`).
- [x] Implement generator and dashboard compatibility (`41b23983d`).
- [x] Run focused hermetic tests and repository guards.
- [x] Obtain final correctness review and close package.

## Decisions

- Canonical new UUID RQ ID: exact output of `str(uuid4())`.
- Stored RQ IDs are opaque strings; lookup/UI layers never alter punctuation.
- Existing bare-hex jobs remain supported for their Redis lifetime.
- A shared helper owns preallocated RQ IDs; non-job UUID uses are excluded.

## Findings Disposition

- High: implementation preceded checkpoint preparation. Disposition: all
  implementation and regression-test edits were removed before checkpoint;
  implementation will be reapplied only after the checkpoint commit.
- Medium: canonical contract scope was too narrow. Disposition: expanded Scope
  to enqueue, worker, Redis, URL, and UI boundaries.
- Medium: AgFields used correct formatting but bypassed the planned helper.
  Disposition: include AgFields child, parent, and finalizer generation.
- Low: AST-only dashboard evidence was insufficient. Disposition: add an
  executable parameterized route test for both exact ID forms.

## Validation Notes

Canonical Docker tests are temporarily blocked by unrelated investigation
processes stuck in uninterruptible I/O in the shared dev container. Hermetic
fallback tests passed 6 ID/dashboard cases. The 181 affected migration,
fork/archive, AgFields, and project-fork cases completed without a failure.
The static RQ graph and broad-exception guards passed; graph changes were
line-number-only. Canonical Docker test and doc-lint commands remain blocked by
the shared container condition and are not claimed as passing.

## Commits and Review

- Contract checkpoint: `1778b66d1`
- Implementation: `41b23983d`
- Final independent correctness verdict: Approve; no remaining High or Medium
  findings (Sagan, `rq_refactorer`).
