# Cancellation lock validation

Checkpoint ancestor: 3903cb778.
No production mutation or deployment performed.

## Focused tests

wctl run-pytest tests/rq/test_directory_lock_cleanup.py --maxfail=1 -q:
17 passed, including automatic real Redis scenarios under configured Compose.

Earlier compatibility selection: 32 passed, 3 opt-in scenarios skipped before
automatic enablement was added. Selection included test_rq_worker_runid.py,
test_cancel_job.py and test_mutations_thaw_freeze_contract.py.

Real scenarios cover ownership/replacement Lua races, legacy/malformed locks,
queued/repeated cancellation, detached and forked writers, thread-acquired locks,
scheduler survival, metadata WATCH/Redis faults, lock-Redis release faults,
crashed-supervisor replacement and injected early-probe failure.

## Worker identity and run-mount evidence

Command:

    wctl docker compose exec -T -e RQ_CANCEL_TEST_RUN_PARENT=/wc1/runs/rq rq-worker /opt/venv/bin/python -m tests.rq.cancel_directory_lock_probe cancel

At 2026-09-10 04:42:36 UTC, job
637ea73a-4394-4dbc-8ef4-df406b76d3ac completed cancellation cleanup under UID
1000, GID 993, groups [993], umask 0022. Run:
 /wc1/runs/rq/rq-cancel-locks-ipx3vak8.
Real RQ 1.16.2 WorkerPool with scheduler and automatic replacement enabled,
real configured Redis, actual worker
container identity and run mount. The probe used a detached-session continuous
writer matching CLIGEN's process-launch behavior; it did not download GridMET
data or execute the complete climate model.

Receipt state complete, execution 3a1883f535b24fa0a012dac5aaac9561; released
climate (path scope), soils and watershed locks. Assertions verified writers
terminated, immediate climate reacquisition, and survival of scheduler,
unrelated writer and landuse lock. Probe resources removed.

## Other gates

Worker and helper stubtests passed. Helper stubtest initially found missing
LOGGER; the stub was amended and passed on rerun. check-test-stubs passed.
Broad-exception enforcement passed after placing added worker methods after
existing methods, preserving line-based allowlist positions. No broad catch
was introduced.

Full wctl run-pytest tests --maxfail=1: 8202 passed, 83 skipped in 870.04s.
That run collected before the last regression additions; the final 17-test
WorkerPool-based focused suite separately passed with real Redis enabled.
Markdown lint, 17-test focused rerun, staged diff checks and broad-exception
enforcement passed. The final WorkerPool-based focused rerun passed: 17 tests
in 77.01s. All local validation gates are complete.

## Limits and rollout

No queue wiring change, no lock TTL/default change, no model parameter changes.
Existing orphaned locks without execution ownership are not retroactively
cleared. Whole-container death remains existing recovery scope. Deployment must
use the canonical production workflow and separate operator authorization.
