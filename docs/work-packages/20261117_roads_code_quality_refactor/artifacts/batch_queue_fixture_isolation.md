# Batch deferred-recovery fixture isolation

The v3 continuation reached a test that enqueued real jobs on Redis database 9's
shared `batch` queue. An active worker started the test's job before the test
could remove it. The test file was byte-identical to immutable baseline
`96555f2f95326350d2d7007c19327378ea831ab0`; both SHA-256 values were
`2ea4b9d244889061dad363cd37ff9169a5d5118de6d8c5e349b4b71499f80355`.

A separate read-only observation at 2026-11-18 00:49:41 UTC found four workers
registered for `batch`, with recent heartbeats and idle state. It used only
`SMEMBERS rq:workers` and worker metadata `HMGET`. No original shared-queue test
was rerun and no worker was stopped.

## Bounded test-only repair

`tests/rq/test_batch_deferred_recovery.py` now creates a real private UUID queue,
following `test_job_dependencies.py`. The fixture maps the production request for
`Queue("batch", connection=...)` to that private queue, asserting the requested
logical name and connection. Both tests retain real Redis WATCH transactions,
job cancellation, byte-ID handling and deferred-registry assertions. Registry
readback uses `DeferredJobRegistry(queue=queue)`. Existing cleanup removes only
test-created jobs; fixture teardown deletes only the private queue.

A private-queue-only diagnostic failed both cases with `mismatch`, because the
production association predicate explicitly requires origin `batch`. Persisting
that origin would redirect native RQ registry operations toward shared storage.
The reviewed fixture adapter instead requires the actual private origin, makes a
shallow copy only for the original association predicate, and sets `batch` on
that unpersisted copy. The original function, arguments and metadata checks stay
active; actual jobs keep private origins for WATCH, cancellation and cleanup.
No production code or RQ wiring changed.

This fixture qualifies recovery against a private real queue. It does not test
literal production queue-name selection. Independent QA approved the bounded
logical-name adapter before its implementation.

## Evidence

Both tests pass against canonical real Redis: **2 passed**, 9.79 seconds.
The guarded equivalent of `wctl check-test-stubs` (`tools/check_stubs.py`) passes.
The final test source SHA-256 is
`823469a8b90c95607c1bd6a468dfceaf9cccdeb4dc7f2e0a535e97914aaad5cd`.

`batch_queue_fixture_receipt.json` binds the source, read-only worker observation,
original v3 failure log, private-queue diagnostic, final pytest/JUnit result,
stub gate and exact observation script. Logs are in `candidate_logs/`.
