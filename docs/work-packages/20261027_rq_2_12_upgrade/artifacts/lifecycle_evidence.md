# RQ lifecycle regression evidence

Status: candidate and rebuilt-runtime lifecycle validation passed, 2026-10-27 UTC. Tests are in
`tests/rq/test_rq212_lifecycle.py`; importable tasks and actual production worker
bootstrap are in `tests/rq/rq212_tasks.py`. No production implementation is owned
by this test lane.

## Environment and isolation

Runs use canonical `wctl exec` into the existing forest `weppcloud` container;
`wctl run-pytest` does not forward the arbitrary disposable-socket environment
variable, so explicit `exec -e` is necessary for these integrated checks.
The candidate is the verified RQ 2.12.0/croniter installation at
`/workdir/wepppy/.pytest_cache/rq212-deps`, prepended to PYTHONPATH for these
processes only. Initial installed-runtime baseline was 1.16.2. After the root operator rebuilt
and recreated forest services at source `b5cac8166`, readback confirmed installed
RQ **2.12.0** at `/opt/venv/lib/python3.12/site-packages/rq/__init__.py`
with ordinary `PYTHONPATH=/workdir/wepppy`. All 13 installed-runtime cases passed. Each worker is a real `WepppyRqWorker` subprocess with
real workhorses; pool coverage uses RQ's actual `WorkerPool` and scheduler.

All lifecycle state uses DB 2 on the disposable Unix socket
`/workdir/wepppy/.pytest_cache/rq212-baseline/redis.sock`; the fixture verifies
its disposable marker before use. Unique UUID-prefixed queues/job IDs prevent
collisions. No Redis flush is used. Worker import-time NoDb/WD-cache connection
configuration is redirected to this same real Redis server; status publication
also uses real Redis. This is test configuration, not mocked queue transitions.

A Python socket audit hook in every worker and inherited child records and
rejects attempted TCP connections from production imports or job execution.
The test asserts no attempted outbound connection occurred. Ordinary jobs have
no webhook configuration; retained metadata is checked as well. This establishes
no webhook delivery or attempted TCP delivery for these exercised workflows.

Only test-owned supervisors and workhorses receive stop/SIGKILL. The abandoned
execution test terminates both the supervisor process group and the separately
grouped RQ workhorse before expiring the real started-registry lease. Evidence
is retained on disposable Redis until package-owned server cleanup.

## Coverage

The suite exercises retained result readback and strict release; failed required
prerequisites and tolerant finalizers; real deferred-graph reconciliation and
new-attempt resubmission; immediate and scheduler-driven retries; terminal retry
failure; queued cancellation; running stop, timeout and workhorse SIGKILL;
post-failure resubmission; execution IDs, public registry IDs, worker current-job
reporting, enum JSON and UTC timestamps; abandoned-job cleanup; and pool worker
replacement plus scheduled submission. Directory-lock descendant containment,
metadata propagation and historical-state fixtures have separate package lanes.

## Confirmed stop discrepancy

The direct test exposed a released-runtime difference:

- 1.16.2 releases its failure-tolerant finalizer after a stopped prerequisite,
  and the next independent job succeeds. It also releases an ordinary strict
  child, violating the current strict-prerequisite contract. The test therefore
  correctly fails its strict-child assertion. See
  [baseline evidence](lifecycle-stopped-baseline.log).
- 2.12.0 leaves both strict and tolerant children deferred after the actual
  stop command. Strict blocking is correct; stranding the approved tolerant
  terminal observer is a migration regression. See
  [candidate evidence](lifecycle-stopped-candidate-before.log).

The worker repair restores only the approved tolerant observer release and
retains strict blocking. The same real-worker case now passes: **1 passed** in
22.38 seconds; see [repaired candidate](lifecycle-stopped-candidate-after.log).
It confirms finalizer completion, strict-child nonexecution, subsequent successful
resubmission, empty started registry and no outbound TCP attempt.

## Commands and results

Candidate invocation (no credentials):

    wctl exec -T \
      -e RQ212_TEST_REDIS_SOCKET=/workdir/wepppy/.pytest_cache/rq212-baseline/redis.sock \
      -e PYTHONPATH=/workdir/wepppy/.pytest_cache/rq212-deps:/workdir/wepppy \
      weppcloud /opt/venv/bin/python -m pytest tests/rq/test_rq212_lifecycle.py -q

Baseline uses `PYTHONPATH=/workdir/wepppy` with the same selected stop test.
The first candidate run excluding stop reached eight successful scenarios; the pool
assertion exposed a harness observation race (job completion precedes worker
idle publication), now changed to wait for actual idle state. The repaired full candidate suite passed **13 tests in 183.84 seconds**; see
[complete candidate result](lifecycle-candidate-passing.log). The rebuilt installed-runtime suite then passed **13 tests in 201.70 seconds**,
with four dependency deprecation warnings and no failures; see
[installed-runtime transcript](rebuilt-lifecycle.log). This rerun uses ordinary
`PYTHONPATH=/workdir/wepppy` and adds `-rP` to retain all passed worker output,
including actual worker identities, RQ version, scheduler events, and injected
failure/recovery diagnostics. All test-owned processes exited after the run.


## Pool failure investigation

The candidate suite reached **11 passed, 1 failed** in 183.82 seconds:
[full provisional result](lifecycle-candidate-before-pool-repair.log).
The remaining failure is real: after an idle supervisor receives SIGKILL, the
pool registers a replacement, but the first new job can be moved into the
intermediate queue with status queued and no worker identity/execution. Waiting
for actual old-PID disappearance and new registration did not resolve it.
The killed supervisor's scheduler remains alive until test-owned group cleanup.
See [candidate pool evidence](lifecycle-pool-candidate-before.log).

The identical test passed on 1.16.2 (**1 passed**, 23.18 seconds), including a
scheduled job after replacement: [baseline pool evidence](lifecycle-pool-baseline.log).
The first apparent version difference was disproved by a deterministic FD probe:
1.16.2 also retains the killed worker's blocking Redis connection in its scheduler.
The earlier baseline success killed the worker before it blocked. The regression
now waits for the actual new DB2 BLMOVE client before SIGKILL. This is a confirmed
baseline recovery defect exposed by required acceptance, not a new 2.12-only
failure. The production worker now disconnects idle Redis connections immediately
before scheduler forks, preserving the active pubsub connection. The complete
candidate suite passes the deterministic pool replacement case and executes a
scheduled job on the replacement worker.

Released RQ 2.12 standard intermediate cleanup first records a first-seen time,
waits more than 60 seconds, then calls the worker failure handler and removes the
intermediate member. Worker maintenance defaults to 600 seconds; therefore a
20-second observation cannot establish permanent loss. A separate direct test
crashes after real dequeue and advances only its own job's first-seen timestamp
to exercise standard maintenance and retained failure/resubmission behavior.
The direct interrupted-dequeue recovery test passed: **1 passed**, 41.56 seconds,
with retained failure, strict blocking, tolerant finalization and successful
resubmission. See [recovery evidence](lifecycle-intermediate-recovery.log).
This proves the standard recovery transition, not a 60-second production SLA:
normal maintenance scheduling remains unchanged. The pool root-cause repair
also passes in both the complete candidate and rebuilt installed-runtime suites.

The separate real maintenance-takeover probe confirms the second scheduler fork
path excludes the supervisor command socket, survives supervisor SIGKILL without
retaining its blocked Redis client, and permits replacement execution. See
[worker repair evidence](worker_compatibility_repairs.md#scheduler-fork-and-worker-replacement).
