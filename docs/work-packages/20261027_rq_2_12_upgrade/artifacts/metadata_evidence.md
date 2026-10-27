# Metadata publication and context evidence

**Date**: 2026-10-27 19:18 UTC
**Checkpoint ancestor**: `b1054fac7`
**Scope**: `wepppy/rq/auth_actor.py`, `wepppy/profile_coverage/runtime.py`, focused metadata/graph tests.

## Confirmed failure and smallest repair

Before source edits, actual RQ 1.16.2 queue publication produced a real Redis job
hash with empty metadata while the enqueue wrappers had not yet returned. Both
`enqueue` and `enqueue_call` failed direct readback at this publication boundary.
The profile hook also wrote a standalone metadata hash before a caller-owned
pipeline executed; resetting the pipeline left that hash behind. Three failing
regressions are retained in [metadata-before.log](metadata-before.log).

The repair adds metadata through the existing `enqueue_call(meta=...)` argument
before RQ creates and publishes the job. RQ persists it in its own existing
transaction, including explicit caller pipelines. Remove the separate late
`save_meta` writes. No new queue or serializer mechanism is introduced.
Positional `meta` is argument 11 in both released 1.16.2 and 2.12.0; direct
positional coverage retains that public call shape. `enqueue` delegates to the
same boundary. Auth-actor and valid correlation values explicitly supplied by
the producer keep their precedence; invalid/missing correlation receives current
context. Active profile context continues to override a stale supplied slug.
Caller dictionaries are copied, not modified.

## Real boundary coverage

`tests/rq/test_rq212_metadata.py` uses the explicitly marked disposable Redis Unix
socket at `.pytest_cache/rq212-baseline/redis.sock`, reserved DB3 and unique queue
names. It never flushes a database. Cleanup removes keys created by each test.
The actual worker subprocess uses `WepppyRqWorker`, real workhorses and profile
coverage. Test-only connection routing directs incidental NoDb/status clients to
the same disposable server; it does not replace RQ, metadata, queue or worker
behavior. Subprocesses retain the selected RQ import path.

The eight regressions cover both enqueue methods at publication, aborted and
committed caller pipelines, acknowledged-commit loss with exact-ID recovery and
no duplicate queue entry, positional metadata, explicit precedence/input
immutability, and real root/child metadata plus an unrelated subsequent job with
empty context. Existing hook doubles now model RQ's `meta` input instead of
assuming a later `save_meta` call.

## Commands and results

On the unchanged 1.16.2 image, after the source repair:

    wctl exec -T -e RQ212_METADATA_REDIS_SOCKET=/workdir/wepppy/.pytest_cache/rq212-baseline/redis.sock weppcloud /opt/venv/bin/python -m pytest tests/rq/test_rq212_metadata.py tests/rq/test_dependency_graph_tools.py -q

Result: **27 passed**, 32 warnings, 23.36 seconds. See
[metadata-116.log](metadata-116.log). All new direct tests ran; none skipped.

Candidate 2.12.0 overlay command:

    wctl exec -T -e RQ212_METADATA_REDIS_SOCKET=/workdir/wepppy/.pytest_cache/rq212-baseline/redis.sock -e PYTHONPATH=/workdir/wepppy/.pytest_cache/rq212-deps:/workdir/wepppy weppcloud /opt/venv/bin/python -m pytest tests/rq/test_rq212_metadata.py tests/rq/test_dependency_graph_tools.py tests/rq/test_submission_recovery.py -q

Result: **37 passed**, 6 warnings, 26.98 seconds; no skipped direct tests. See
[metadata-212.log](metadata-212.log). This includes the two existing correlation
tests that initially failed because their doubles ignored the enqueue `meta`
argument. Rebuilt-runtime validation remains a separate parent-package gate. No production or remote operation was
performed by this lane. Native webhook configuration was not added.


## Validation limits and harness correction

The first actual-worker harness attempts lacked the test module import path and
allowed incidental status clients to inherit pytest's intentionally cleared Redis
credentials. Corrected the harness to include `tests/rq` on the inherited import
path and route all Redis pools to disposable DB3; no production worker repair
was made for those harness failures. Final 1.16.2 and 2.12.0 results above use the
corrected real-process harness. Source diff whitespace check and artifact doc lint
passed. Broader repository gates and final rebuilt runtime evidence are owned by
the parent package.
