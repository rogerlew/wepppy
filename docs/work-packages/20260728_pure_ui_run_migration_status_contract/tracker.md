# Tracker - SURF-08 Pure UI Run Migration Status Contract

## Status

Verified 2026-07-28 UTC.

## Progress

- [x] Registered SURF-08 after verified SURF-07.
- [x] Ratified the concise host/render/enqueue/poll/worker/reload contract.
- [x] Added permission-aware direct render and seven real inline-client tests.
- [x] Passed 225 focused render, Flask, rq-engine, polling, and worker tests.
- [x] Repaired JSON-safe bootstrap, authenticated/confined polling,
  owner/admin enforcement, token-class confinement, submit serialization,
  persistence-before-publish identity, and archive/readonly failure handling
  mismatches.
- [x] Completed validation, independent security review, parent reconciliation,
  and
  close.

## Validation

- Focused Python: 225 passed.
- Focused inline Jest: 7 passed.
- Full frontend Jest: 92 suites and 684 tests passed.
- Frontend lint, RQ graph, documentation lint, broad-exception enforcement,
  and `git diff --check`: passed.
- Broad Python: stopped at the permitted unrelated
  `test_gridmet_interpolation_propagates_unpublished_suffix_to_parquet_and_prn`
  `_FakeUnits.degC` fixture defect after 2,462 passed and 40 skipped.

## Decisions

- Reuse SURF-07 only as evidence for unchanged canonical job endpoints; execute
  the migration page's own client state machine directly.
- Preserve migration selection, authorization, archive, readonly, version,
  queue, and result behavior.
- Use `tojson` for script bootstrap values and `requestWithSessionToken` for
  status and terminal jobinfo so configured required poll auth works.
- Require owner/admin at both presentation and mutation boundaries, permit
  owner matching only for user/session tokens, and use a per-run Redis NX
  reservation with job identity persisted before queue publication.
