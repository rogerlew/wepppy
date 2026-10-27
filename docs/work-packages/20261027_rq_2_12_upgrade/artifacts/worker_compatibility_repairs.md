# Worker and dependency compatibility repairs

Recorded 2026-10-27; updated 19:37 UTC. Implementation follows checkpoint `b1054fac7`.
This evidence uses the existing container plus an isolated RQ 2.12 import target;
rebuilt-runtime validation remains the parent package's separate gate.

## Confirmed failures and bounded repairs

| Consumer | Failure | Repair and evidence |
| --- | --- | --- |
| `project_rq._enqueue_serial_subcatchment_tree` transaction | RQ 2.12 removes `Job.get_redis_server_version`; real serialized-tree test raises AttributeError | Assign both job version caches from `Queue.get_redis_server_version` before MULTI. Both versions support this cache property; no fallback wrapper. Full WBT integration suite passes. |
| Approved stopped-parent terminal observer | Actual 2.12 worker stop leaves tolerant observer deferred; 1.16 releases it | Surviving worker rechecks only failure-tolerant dependents using existing WATCH-protected release helper and the exact stopped parent ID. Strict edges, canceled observer, canceled other prerequisite, missing dependencies and unfinished siblings cannot release. |
| Strict dependency helper | Calling existing helper on a strict failed edge would release work, contrary to canonical strict semantics | Explicit `allow_dependency_failures` check retains failed-prerequisite allowance only for approved tolerant edges. Direct real-Redis regression confirms strict work remains deferred. This restores canonical behavior rather than preserving an existing defect. |
| Inline WBT test worker | RQ 2.12 makes Worker and SimpleWorker siblings, so the multiple-inheritance fixture unexpectedly forks and caplog misses the controlled error | Test fixture explicitly selects `SimpleWorker.execute_job`; production execution and logging remain unchanged. Real process behavior is separately covered by lifecycle/batch tests. |

`docs/schemas/batch-task-boundary-contract.md#failure-retry-and-cancellation`
requires stopped hillslope work to release the gated terminal observer; that
observer cannot perform scientific work without a finished predecessor and valid
handoff. `docs/schemas/rq-response-contract.md` retains strict scientific
prerequisites. The RQ 1.16 direct stop test also exposed an existing violation:
ordinary strict children could execute after a stopped prerequisite. RQ 2.12's
strict block is preserved; the compatibility repair does not reinstate that bug.

The stopped allowance is contextual: the exact stopped parent must belong to
the current dependency set and remain stopped at the WATCH-protected commit.
Every other prerequisite must already be finished or failed. This matches the
prior direct-parent release path; it does not claim new fan-in semantics when a
stopped parent precedes another still-active prerequisite. Canceled observer
state is checked before promotion and duplicate release does not enqueue twice.

No enqueue edge, queue name, identity, permission, exception envelope, webhook
configuration or scientific output changed. Worker override signatures retain
the released RQ 2.12 interface. `job_dependencies.pyi` matches the added
keyword-only stopped-parent parameter.

## Validation

- Candidate targeted worker/dependency/WBT integration: **64 passed**, 37 warnings,
  15.45 seconds. [Transcript](candidate-worker-repairs.log).
- Same source on baseline RQ 1.16: **64 passed**, 1047 warnings, 18.46 seconds.
  [Transcript](baseline-worker-repairs.log).
- Candidate full batch boundary using disposable Unix-socket Redis:
  **26 passed**, 6 warnings, 14.21 seconds. [Transcript](candidate-batch-boundary.log).
- `wctl run-stubtest wepppy.rq.job_dependencies`: pass, one module.
  [Transcript](job-dependencies-stubtest.log).
- `wctl check-test-stubs`: all stubs complete. [Transcript](check-test-stubs.log).
- Lifecycle agent independently reran actual stop: **1 passed**, 22.38 seconds;
  tolerant finalizer finished, strict child remained deferred/unexecuted,
  supervisor completed a subsequent job, and started registry emptied. Its
  retained lifecycle evidence owns that subprocess result.

The new helper matrix additionally covers finished/failed siblings, active,
canceled and stopped siblings, canceled observer, strict refusal and idempotent
promotion. Tests use package-owned jobs and queues; shared Redis is never flushed.
The batch and lifecycle tests use the package's isolated disposable Redis server.

## Scheduler fork and worker replacement

The initial RQ 1.16 pool test passed by timing. A subsequent process/socket probe
reproduced the defect under **both 1.16.2 and 2.12.0**: the forked scheduler retained
the supervisor's idle Redis command socket. When that socket later blocked in
`BLMOVE`, killing the supervisor left an orphan scheduler holding it open. Redis
consumed the next submitted job into the intermediate queue with no worker left
to receive the response. The replacement worker could not execute that job.
Killing only the package-owned orphan scheduler removed the stale client and
allowed a subsequent job to execute. This is an existing lifecycle conformance
defect, not a claim that RQ 2.12 introduced it.

The bounded repair disconnects **available** Redis pool connections immediately
before `_start_scheduler` and `run_maintenance_tasks`. The latter is required
because released RQ can start a replacement scheduler directly from maintenance.
Redis 6.2.0's public `ConnectionPool.disconnect(inuse_connections=False)` preserves
in-use connections, including the existing pubsub listener, while closing idle
command sockets before the fork. Its exact installed signature and source are
retained in [Redis API evidence](redis-pool-disconnect-api.log). No fork hook,
scheduler replacement, timeout, pool size, queue, or process topology is added.

Both actual fork paths passed under RQ 2.12:

- Initial scheduler: its file descriptors exclude the supervisor command socket;
  after supervisor SIGKILL the old blocked Redis client disappears, and the
  pool replacement executes the first new job with an empty intermediate queue.
  [Before repair](candidate-scheduler-fd-probe-before.log),
  [after repair](candidate-scheduler-fd-probe-after.log),
  [RQ 1.16 defect reproduction](baseline-scheduler-fd-probe.log).
- Maintenance takeover: kill the package-owned scheduler, allow real worker
  maintenance to start scheduler PID 3962710, and successfully execute a scheduled
  job. Supervisor PID 3960051 then dies by SIGKILL; its blocked Redis client 1654
  disappears even though the replacement scheduler survives. A new worker
  completes the first submitted job with result `{"attempt": 1, "value": 42}`;
  intermediate queue is empty. The supervisor command socket inode 161285447 is
  absent from scheduler file descriptors. [Transcript](candidate-scheduler-maintenance-takeover.log).
- The independent lifecycle suite subsequently passed **13 tests in 183.84s**,
  including deterministic synchronization on an actually blocked `BLMOVE` before
  killing the pool supervisor, replacement execution, and scheduler execution.
  The lifecycle agent retains that suite's transcript.
- Baseline worker and directory-lock regressions: **24 passed**, 2 warnings,
  81.64 seconds. [Transcript](baseline-worker-scheduler-repairs.log).
- `wctl run-stubtest wepppy.rq.rq_worker`: pass, one module.
  [Transcript](rq-worker-stubtest.log). Both new override signatures are declared
  in `rq_worker.pyi`.

Exact diagnostic source is retained as
[pool probe](scheduler_pool_fd_probe.py),
[maintenance probe](scheduler_maintenance_takeover_probe.py), and its
[isolated worker helper](scheduler_probe_worker_db10.py). These are diagnostic
snapshots, not general operator commands. The maintenance helper is the lifecycle
helper with Redis database 10 selected instead of 2. Before replaying the exact
probe, place that retained helper at `.pytest_cache/rq212_tasks_db10.py` and use
the package-owned Unix socket `/workdir/wepppy/.pytest_cache/rq212-baseline/redis.sock`.
The maintenance probe refuses a nonempty DB10; it admitted an empty database,
terminated only its own process groups, and removed its own records during cleanup.
Post-cleanup readback confirmed **zero DB10 keys**. The baseline/candidate package
databases and historical fixtures were not cleared. All probe processes finished
before the parent began the authorized stack cutover.

```bash
wctl exec -T \
  -e PYTHONPATH=/workdir/wepppy/.pytest_cache/rq212-deps:/workdir/wepppy \
  weppcloud /opt/venv/bin/python \
  docs/work-packages/20261027_rq_2_12_upgrade/artifacts/scheduler_maintenance_takeover_probe.py
```
