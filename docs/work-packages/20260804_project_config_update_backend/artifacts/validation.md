# WP08 Validation Evidence

## Behavioral coverage

- Pure availability/preview leaves project artifacts and directory entries
  unchanged.
- Builder and preset fixtures materialize complete missing-value deltas with
  source IDs/revisions while preserving existing values.
- Stale preview, arbitrary trigger, invalid/newer chain, authorization loss,
  concurrent apply, and three transaction interruption points are covered.
- Reader-triggered recovery repairs a recorded interrupted pair without loading
  the current registry.
- Route tests cover default-off behavior, owner/Admin/Root authorization,
  preview/apply errors, one-job enqueue, and active-job conflict.

## Gates

- Focused NoDb/RQ/route suite: passed (`109` tests in the combined final set;
  the service file independently passed `13` tests).
- OpenAPI and focused route suite: `15 passed`.
- `wctl run-stubtest wepppy.nodb.project_config_update`: passed.
- `wctl check-test-stubs`: passed.
- `wctl check-rq-contracts`: passed.
- `wctl check-rq-graph`: passed (`144` edges).
- Changed-file broad-exception enforcement: passed, net delta `+0`.
- Full suite: `6925 passed, 63 skipped`.
- Scoped isolation quick gate: passed across all five affected test files and
  both seeds, including isolated-per-file execution.

The diagnostic isolation mode's five test executions and all isolated-file
runs passed. Its optional state-diff phase returned nonzero because every
selected file reported the same existing `pyexpat.errors` module and
environment-variable baseline noise; no WP08-specific order failure occurred.
