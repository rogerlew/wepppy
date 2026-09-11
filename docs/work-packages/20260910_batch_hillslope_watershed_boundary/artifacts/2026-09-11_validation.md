# Validation evidence

## Baseline and tests-first evidence

Forest starting source: `0c34afdb5`. Initial graph check passed; existing retry
suite: 35 passed in 12.43 s. After adding the two-job topology assertion and
before production edits, the regression failed with `AttributeError: module
wepppy.rq.batch_rq has no attribute run_batch_hillslopes_rq` (1 failed,
34 deselected, 9.11 s). Contract ancestors: `869ca7dcf`, `f221e7f2a`.

## Completed checks

- Existing BatchRunner/WATAR focused suites: 50 passed, 13.26 s.
- Real isolated Redis/RQ plus retry, worker and archive suites: 93 passed,
  29.62 s. Includes actual forking `WepppyRqWorker`, lineage/receipt rejection,
  TTL, both phase failures/retries, root failure/retry, stopped prerequisite,
  cancellation, duplicate submission, mixed leaves, concurrent Omni, attachment
  failure, real stale NoDb/cache rehydration and symlink containment.
- Final reviewed-source focused rerun: **95 passed**, 3395 warnings, **29.44 s**.
- After shortening Omni lock scope, focused deterministic barrier/Omni gate:
  4 passed, 11.61 s.
- Worker identity/no-prevalidation filesystem-access gate: 7 passed, 10.47 s.
- Canonical archive/restore retained handoff bytes for working/failed/successful/
  restored records.
- First complete `wctl run-pytest tests --maxfail=1`: **8445 passed, 94 skipped**,
  3118 warnings, **960.32 s**.
- Final reviewed-source complete suite: **8447 passed, 103 skipped**,
  3118 warnings, **960.51 s (16 minutes)**. Exit zero. The additional isolated
  RQ cases are skipped here and passed in the explicit real-Redis gate above.
- `wctl run-stubtest wepppy.rq.batch_rq` and
  `wctl run-stubtest wepppy.nodb.batch_runner`: passed.
- `wctl check-test-stubs`: passed.
- `wctl check-rq-graph`: passed; generated graph has 146 edges.
- Broad-exception enforcement: passed after refreshing the existing worker
  allowlist's stale line locations. No broad handler was added to the worker.
- Scoped Markdown lint and `git diff --check`: passed.

## Isolation and tooling notes

The pytest container has no `redis-server` executable. Real RQ tests used a
host-started disposable Redis process with no TCP listener and a shared Unix
socket, explicitly marked `batch-boundary-test-server=disposable`. The test
fixture restores `redis.StrictRedis` because the session normally substitutes
`redis.Redis`. Tests never use application Redis and retain job records until
the disposable server is stopped; teardown cancels only jobs created by that
test. The full suite skips these tests without an isolated server; their
non-skipped focused execution above is the acceptance evidence.

Code-quality observability ran with custom `/tmp` output paths, preserving the
pre-existing dirty root reports. Host `radon` is unavailable; Python complexity
telemetry is therefore limited. Changed-commit telemetry will be recorded after
the implementation commit, because the tool does not analyze uncommitted source
changes against the branch comparison.

Forest worker/browser evidence and publication evidence are separate gates.
