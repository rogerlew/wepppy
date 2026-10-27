# Rebuilt forest targeted regression evidence

Date: 2026-10-27 UTC. Source `b5cac8166eaf067ac2ef79c440a82314c114111b`.
All runs use installed RQ 2.12.0 from `/opt/venv`, redis-py 6.2.0, and the recreated
forest `weppcloud` container. No candidate PYTHONPATH dependency overlay is used.
[Runtime/image provenance](rebuilt-historical-runtime-provenance.json) records
application image `88a982e44d316824f493c99d0c3a9a3db3e4800feef86ff2c65693677039162b`.

| Selection | Result | Exact command and output |
| --- | --- | --- |
| Historical records and metadata | 10 passed, 2 warnings, 31.35s | [log](rebuilt-historical-metadata.log) |
| Real Redis batch boundaries, query-catalog recovery and pilot | 73 passed, 8 warnings, 21.89s | [log](rebuilt-query-batch-clean.log) |
| Existing worker, dependency, cancellation, status, fork/archive, run-sync, acknowledgment, auth and startup regressions | 498 passed, 76 warnings, 41.62s | [log](rebuilt-targeted-recovery-api.log) |
| Directory locks, actual stop delivery and descendant process containment | 17 passed, 2 warnings, 77.28s | [log](rebuilt-containment.log) |

All 598 selected tests pass with no skips. These focused checks supplement the
separately owned broad suite and live installed-pool/model/API acceptance. They
do not replace generated-artifact acceptance.

The first two commands use canonical `wctl exec` with explicit disposable Redis
socket environment variables because `wctl run-pytest` does not forward arbitrary
host environment variables. Historical tests exclusively use DB4; metadata DB3;
batch/query tests DB0. The third command uses `wctl run-pytest` directly.

## Installed-worker containment evidence

`wctl run-pytest tests/rq/test_directory_lock_cleanup.py -rs --maxfail=1`
passed all 17 tests, including eight unmocked integration cases. The configured
Redis credential file enabled the real Redis cases; none were skipped. Fresh
interpreters create only unique `cancel-probe-*` queues and temporary run paths,
then start actual RQ worker pools using `WepppyRqWorker` from the installed
upgraded runtime. Cleanup targets only those probes' jobs, worker registrations,
scheduler keys, locks and processes.

Actual `cancel_jobs` stop delivery terminates inherited-group and detached-session
writers, records terminal cleanup, and permits immediate reacquisition of the
execution's directory locks. The scheduler, unrelated writer and unrelated
legacy lock survive. A prior workhorse SIGKILL forces supervisor replacement;
later cancellation preserves the previous execution's foreign writer. Diagnostic
WATCH/Redis failures do not prevent writer termination or lock release. Separate
direct process containment verifies that the detached writer is gone and its
output file stops growing. Unit checks additionally prove that uncertain process
inspection, permission errors, missing kernel inspection and scheduler identity
loss refuse lock release; those injected failure checks are not represented as
unmocked kernel failures.

## Retained failed attempt and isolation diagnosis

The initial batch/query attempt stopped at **47 passed, one failed**:
`test_killed_worker_recovers_after_rq_abandonment`. Its
[failed log](rebuilt-query-batch.log) shows abandonment cleanup finding earlier
retained `batch/demo` started fixtures and releasing an old approved finalizer
after the old test's monkeypatches had ended. That finalizer correctly failed
because `/wc1/batch/demo` does not exist. The external-socket fixture intentionally
preserves job records, so reusing its database across baseline/candidate/final
runs accumulated test state. This is test-environment contamination; the clean
repeat did not reproduce a migration failure.

After all DB0 test processes exited, the parent authorized cleanup only of this
package's disposable DB0. We verified the exact Unix socket, DB0, and ownership
marker, retained a precleanup snapshot, then deleted its 1,086 enumerated owned
keys individually while preserving the marker. No FLUSHDB/FLUSHALL operation was
used; no other database or application Redis was changed.
[Cleanup receipt](rebuilt-disposable-cleanup.json) retains the snapshot path/hash
and scope. The entire 73-test combined selection then passed on the clean owned
database, including abandonment recovery and running cancellation.

For repeat external-socket runs, use a fresh owned database/server or explicitly
retire only records created by the prior owned run. Retained old running records
are recovery test inputs, not a clean test baseline. No production fallback or
fixture assertion was weakened to obtain the passing result.
