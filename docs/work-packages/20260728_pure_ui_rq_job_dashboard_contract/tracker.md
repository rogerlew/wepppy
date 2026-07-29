# Tracker - SURF-07 Pure UI RQ Job Dashboard Contract

## Status

Verified 2026-07-28 UTC.

## Progress

- [x] Registered SURF-07 after the completed run-domain and shared shell work.
- [x] Ratified the concise host/poll/tree/cancel/token contract.
- [x] Added actual-render and four real inline-client regressions.
- [x] Passed 268 focused Flask, rq-engine polling/cancel, session, payload, and
  render tests.
- [x] Repaired the regression-confirmed required poll-auth mismatch with one
  fallback-token retry.
- [x] Completed validation, independent security review, parent reconciliation,
  and
  close.

## Validation

- Focused Python: 268 passed.
- Focused inline Jest: 4 passed.
- Frontend lint: passed.
- Full frontend: 91 suites, 677 tests passed.
- Broad Python: stopped at the permitted unrelated GridMET fixture failure
  after 2,455 passed and 40 skipped:
  `test_gridmet_interpolation_propagates_unpublished_suffix_to_parquet_and_prn`
  failed because `_FakeUnits` has no `degC`.
- Child/parent/project documentation lint and `git diff --check`: passed.

## Decisions

- Exercise SHR-02, SHR-03A, and SHR-03B only through this concrete dashboard;
  do not claim their shared producer packages.
- Preserve canonical job payloads, poll-auth policy, token scopes, cancellation
  authority, and queue behavior.
- Retry job-info once with the authenticated rq-engine token only after a 401
  or 403; open-mode polling retains its existing unauthenticated fast path.
