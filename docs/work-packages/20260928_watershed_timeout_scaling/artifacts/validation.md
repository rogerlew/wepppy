# WRT-01 implementation validation

Contract ancestor: `728965382`. Validation in the local Compose environment;
no production deployment, worker restart, stored-job mutation or retry.

## Behavior and generated artifacts

`wctl run-pytest tests/rq/test_watershed_timeout.py tests/rq/test_wepp_rq_pipeline.py -q`:
98 passed. Covers exact rounding/floor/range, controller and prepared workload,
all four paths, ordinary and batch single storms, hillslope-only bypass,
pre-enqueue errors, legacy/modern templates and fork metadata/callback preservation.
Correctness review C1 added bounded structural checks and malformed-file tests.

`wctl run-python docs/work-packages/20260928_watershed_timeout_scaling/artifacts/verify_live_rq.py`:
4 live Redis graphs inspected through `job_info`, with 41 disposable jobs removed.
[Raw evidence](live_rq.json) retains child identities, dependencies, stored budgets,
metadata and matching before/after native source hashes. All continuous leaves
store 97,200 seconds for 1,000 years and 1,908 hillslopes. No-prep ignores stale
1-year/1-hillslope controller values. Fork lineage and callbacks survive real RQ
serialization. The isolated queue was never consumed; no model inputs or outputs
were regenerated. RQ serialization and dependency artifacts are the changed output
contract; a new native simulation is not necessary to validate unchanged model code.

## Checks

- `wctl check-rq-graph`: passes after canonical regeneration. All 146 records
  equal the ancestor after removing only `source_lineno`.
- `wctl run-stubtest wepppy.rq.watershed_timeout`: passes.
- `wctl check-test-stubs`: passes.
- Scoped package, contract, ADR and RQ README document lint: passes.
- `git diff --check`: passes.
- Broad-exception changed-file enforcement: passes, zero new handlers.
- Code-quality observability completed in observe-only mode; local `radon`
  unavailable and ancestor-to-HEAD scan excludes uncommitted implementation.
  No complexity gate is claimed. The helper is bounded and pipeline edits small.
- Final correctness and security review artifacts: approved, no unresolved findings.

`wctl run-pytest tests/rq -q --maxfail=1`: 1,216 passed, 29 skipped in 149 seconds.
Full repository regression is pending.

## Limits

This allowance is an empirical policy, not a runtime guarantee. Existing jobs keep
their saved timeout. Timeout subprocess cleanup remains a separate known issue.
No changes to native outputs, single-storm limits, other stage budgets or admission
controls were part of this implementation.
