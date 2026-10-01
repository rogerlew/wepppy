# Idle-worker admission implementation evidence

Contract ancestor: `79de4341fa2b2b6db3fd6441468f28dd3d2c3db5`.
Implementation is local and not deployed. Forest1 remains on its prior candidate;
no live queue, service, scheduler setting or SQL read mode was changed.

## Implementation

`run_catalog_rq.enqueue_sweep` first observes the destination queue's registered
worker keys. A Redis transaction reads global suspension and each worker's
state, actual queue membership, compatibility metadata, death marker and TTL.
Only a positive-TTL, non-dead, idle matching consumer permits existing atomic
admission. Unknown/unavailable evidence skips the tick without pointer/job
mutation; Redis errors propagate to the existing scheduler boundary. Worker
heartbeats and TTLs are never renewed by discovery. The admission guard itself
is unchanged, including its handling of all four outstanding states.

## Validation

- Focused catalog/RQ and scheduler selection: 50 passed in 11.09 seconds.
- Final affected-subsystem selection (catalog admission, all tools and
  microservices, catalog CLI/extractor/PostgreSQL/readers): 1,858 passed in
  94.91 seconds, no skips. Log: `/tmp/catalog-worker-admission-subsystems.log`.
- Uses actual RQ registrations and disposable Redis over a Unix socket, with
  no TCP listener or persistence; no live global suspension was toggled.
  Reuses `tests.rq.test_batch_task_boundary.isolated_rq`. Where the container
  lacks `redis-server`, start a dedicated host instance with `--port 0`,
  `--save ''`, `--appendonly no` and a socket inside the shared ignored pytest
  cache; mark it with `SET batch-boundary-test-server disposable`. Pass its
  container-visible path as `BATCH_BOUNDARY_TEST_REDIS_SOCKET` through
  `wctl exec -T -e ... weppcloud` when invoking pytest. Without either the binary
  or this verified socket, these integration tests skip rather than touch the
  deployment Redis. Shut down the dedicated server after validation.
- Covers missing/expired/non-expiring/dead workers, busy/unknown/suspended states,
  stale queue membership/name reuse, missing/malformed/incompatible metadata,
  mixed pools, suspension/resumption, unchanged heartbeat/TTL, repeated ticks,
  concurrent admission, worker loss after observation, and explicit Redis errors.
- Executes the real sweep against an isolated PostgreSQL schema and project
  file; verifies source-derived SQL output and the real terminal job tree via
  `recursive_get_job_details`, including reserved-ID redaction and null results.
- Queue graph regenerated for the moved enqueue line; graph validation passes.
  No new queue, dependency edge or scheduling interval was introduced.
- Changed broad-exception gate and whitespace checks pass.
- Code-quality observability ran in non-blocking mode; the host lacks `radon`
  and its committed-revision comparison does not analyze this uncommitted patch.
  No complexity-clearance claim is made; generated baseline reports were restored
  rather than including unrelated repository-wide telemetry changes.
- A read-only probe from forest's actual scheduler environment returned an
  available compatible idle consumer; it did not enqueue or restart anything.
- Full repository sanity: 5,725 passed, 56 skipped, then one failure in
  `tests/rq/test_batch_task_boundary.py::test_production_worker_preserves_identity_and_forks_each_stage`
  after 2,106.42 seconds. The production worker refused a second stage because
  its pytest supervisor already had child processes; that test does not call the
  changed admission path. A fresh-interpreter/fresh-disposable-Redis rerun of
  the exact case passed (one test, 9.39 seconds). No containment safeguard or
  unrelated test was changed. Full-suite success is not claimed; logs:
  `/tmp/catalog-worker-admission-full.log` and
  `/tmp/catalog-worker-admission-boundary-rerun.log`.

The first focused run found a test-teardown monkeypatch leak, not a runtime
failure; limiting the injected Redis failure to a monkeypatch context fixed it.
Dirac (correctness) and Ohm (security/compatibility) independently returned PASS
for the implementation; SEC-21 is closed. They inspected code and evidence,
not an independent rerun of the tests. Live host admission acceptance
requires a separately authorized rollout; no isolated result claims deployment.

## Handoff

The operator authorized committing the work tree on 2026-10-01. Runtime changes,
tests, generated queue-line metadata and completion evidence are included in
this implementation commit, following the approved contract ancestor.
No push, deployment, live queue mutation or service restart
was performed. Disposable Redis instances are stopped after validation.
