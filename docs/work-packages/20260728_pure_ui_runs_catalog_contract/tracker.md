# Tracker - SURF-06 Pure UI Runs Catalog Contract

## Status

Verified 2026-07-28 UTC.

## Progress

- [x] Registered SURF-06 after verified SURF-15.
- [x] Ratified ownership, Admin scope, catalog/map, readonly, exact
  run/config deletion, RQ polling, and reload intent.
- [x] Add direct render and actual-inline-client evidence.
- [x] Retain route, ownership, delete enqueue/worker, and reload evidence.
- [x] Repair only confirmed conformance mismatches.
- [x] Complete security review, focused/broad gates, parent reconciliation,
  commit, and clean closeout.

Focused Python passed 65 tests, focused inline/lifecycle Jest passed 7 tests,
frontend lint and all 98 suites/703 tests passed, and the repository-wide
Python sweep passed 5,540 tests with 58 skips.

## Decisions

- Non-privileged `alias` input never changes the acting user's ownership scope.
- Admin/Root scope resolves only an exact ID or case-insensitive email.
- Catalog identity is the stored `(runid, config)` pair; deletion cannot replace
  the configuration with a default.
- Readonly runs cannot be selected or deleted.
- Row removal follows a confirmed finished job, never enqueue alone.

## Conformance Classification

The client hardcoded configuration `0` in its deletion URL and interpolated
unencoded server values into action paths. Direct regressions established both
mismatches before the minimal identity-preserving repair. Readonly deletion
also returned an error envelope with HTTP 200; it now returns HTTP 400.
