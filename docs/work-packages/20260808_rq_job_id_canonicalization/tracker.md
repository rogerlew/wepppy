# Tracker – RQ Job ID Canonicalization and Dashboard Compatibility

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-08 21:37 UTC
**Current phase**: Contract checkpoint
**Last updated**: 2026-08-08 21:37 UTC
**Security impact**: `low`
**Dedicated security review**: `no`

## Progress

- [x] Confirmed production failure is exact-ID mismatch, not queue rank.
- [x] Inventoried preallocated RQ UUID generation sites.
- [x] Amended canonical identifier contract with conformance pending.
- [x] Obtained two independent read-only reviews.
- [x] Dispositioned pre-checkpoint findings.
- [ ] Commit standalone checkpoint and verify ancestry.
- [ ] Implement generator and dashboard compatibility.
- [ ] Run focused tests, guards, and documentation lint.
- [ ] Obtain final correctness review and close package.

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
fallback tests passed 5 ID/dashboard cases and the affected route/fork suites
displayed no failure before completion. Canonical commands remain required.
