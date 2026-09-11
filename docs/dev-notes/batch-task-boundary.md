# Batch hillslope and watershed jobs

Each selected batch leaf runs as two jobs on the existing `batch` queue.
`run_batch_hillslopes_rq` initializes/resumes the project and completes enabled
preparation, hillslope WEPP and hillslope interchange.
`run_batch_watershed_rq` opens the leaf afresh and completes watershed WEPP,
postprocessing, WATAR and Omni submission. Both remain on the existing workers.

The job tree exposes `jobs:0,hillslopes,runid:<leaf>` and
`jobs:0,runid:<leaf>` on the root. The latter remains the terminal leaf ID.
The root finishes dispatch before hillslope jobs start; the batch finalizer
waits for watershed jobs and any attached Omni finalizers.

Inspect `batch_handoff/<hillslope-job-id>.json` through normal leaf browsing or
download. It records the attempt IDs, completion time, host and process. These
records travel with ordinary archives/restores. They are diagnostic records;
copying a receipt cannot authorize another attempt. Root and hillslope job
identity records do not expire automatically, so a delayed downstream job can
still verify them; this change does not add job deletion. Stage two requires a
finished upstream job and matching run/attempt identity in durable and RQ state.

A failed hillslope job still releases the second job as a failure observer.
It records terminal failure without running watershed work. Watershed failures
retain the existing failed metadata/result behavior. Use ordinary batch retry:
completed leaves are skipped, partial leaves resume their missing timestamps,
and new attempts receive new job IDs. Explicit full rerun still resets leaves.
Terminal attempt outcome and retry classification remain separate: completed
enabled-task timestamps retain precedence over stale failed metadata, including
a zero-enabled-task fixture. This boundary preserves that existing selection
rule.

Tree cancellation stops both phases and the finalizer; it is not completion.
If Omni dispatch or dependency attachment fails after starting work, root
`batch_pending_omni_links` records the affected leaf and the batch finalizer
fails explicitly rather than announcing completion. Inspect the linked Omni
jobs, allow active work to finish or cancel it, then use ordinary batch retry.
Do not manually clear the pending flag to claim completion.

Developers use `BatchRunner.run_batch_hillslopes` and
`BatchRunner.run_batch_watershed` for the phase APIs. The synchronous
`run_batch_project` wrapper remains for the existing standalone WATAR evidence
script; RQ never calls it. Stage two does not resynchronize base attributes,
clean hillslope outputs or clear locks. It evicts only leaf-local in-process
instances and clears explicit mutable-controller Redis cache scopes before
hydration. Normal locking and stale-write protection still apply. The worker preserves
these stages' composite metadata and defers filesystem logging until the task
validates identity; leaf diagnostics use the BatchRunner logger rather than
automatic worker `rq.log` attachment.

The normative authority is
[Batch task boundary contract](../schemas/batch-task-boundary-contract.md).
This boundary establishes job/process separation; it does not guarantee a new
container/cgroup or establish memory headroom. The openwepp.org batch/memory
acceptance belongs to its subsequent deployment package.

## Isolated RQ regression tests

`tests/rq/test_batch_task_boundary.py` uses a disposable Redis process with a
Unix socket and no TCP listener. Where `redis-server` is absent from the pytest
container, start the disposable server on the host at a shared workspace path,
set its `batch-boundary-test-server` key to `disposable`, and pass its socket as
`BATCH_BOUNDARY_TEST_REDIS_SOCKET` through `wctl exec weppcloud`. Never point this
variable at the application Redis. Tests retain terminal records and cancel
only their own remaining jobs. Stop the disposable server after validation.
The ordinary test suite skips this integration module if neither isolated
option is available; focused acceptance must run it against real Redis.
