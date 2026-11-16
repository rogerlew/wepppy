# Local validation — 2026-11-16

## Passing receipts

- `wctl run-pytest tests/rq/test_batch_rq_retry_selection.py tests/rq/test_culvert_rq_pipeline.py tests/microservices/test_rq_engine_jobinfo.py tests/culverts/test_culvert_batch_rq.py --maxfail=1 -q`: 120 passed.
- `wctl run-pytest tests/rq/test_omni_rq.py tests/rq/test_cancel_job.py --maxfail=1 -q`: 38 passed.
- Real disposable Redis boundary gate: 63 passed (48.51 seconds). Command below.
- External checkout: host WEPPpy virtualenv `python -m pytest scripts/tests/test_wepp_batch_outcome.py -q`, with `WEPP_BATCH_TEST_ARCHIVE` pointing at the server-generated 32-success/one-timeout ZIP: 4 passed, including real GeoPandas/Parquet readers.
- `wctl run-stubtest wepppy.rq.job_info`: no issues; `wctl check-test-stubs`: complete.
- `wctl check-rq-graph`: generated dependency graph is current. Live real Redis trees were inspected with `recursive_get_job_details` and both HTTP polling endpoints in the boundary tests.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref HEAD`: pass. Nine existing physical-line allowlist entries moved with unchanged diagnostic handlers; no new broad exception boundary added.
- Scoped docs lint for package/schema/migration guide/dependency catalog/allowlist: zero errors/warnings. `git diff --check`: pass.

Real boundary command (the isolated host Redis socket is explicitly mounted; no production Redis or run data is used):

```bash
wctl exec -T -e BATCH_BOUNDARY_TEST_REDIS_SOCKET=/workdir/wepppy/.tmp/batch-outcome-redis/redis.sock weppcloud bash -lc 'cd /workdir/wepppy && PYTHONPATH=/workdir/wepppy /opt/venv/bin/pytest tests/rq/test_batch_outcome.py tests/rq/test_batch_task_boundary.py --basetemp=/workdir/wepppy/.tmp/batch-outcome-tests-final6 --maxfail=1 -q'
```

The suite includes real one-second worker timeout with 32 valid siblings;
failure-tolerant scheduling; ordinary linked Omni failure/cancellation; malformed
scientific artifacts/receipts; actual Culvert finalizer; repeated and concurrent
publication; canceled/retried/superseded attempts; exact identity and restricted
path rejection; actual jobinfo/jobstatus; signed-JWT download plus foreign denial;
normal browse; canonical project archive/restore; and cancellation during ZIP
build, during registration/enqueue, and after stale parent-tree fetch.
`20261116_artifact_readback.json` retains the emitted summary, manifest and ZIP hash.

## Broad suite and quality telemetry

`wctl run-pytest tests --maxfail=1` is running at implementation commit time.
Earlier attempts exposed outdated dummy Job interfaces in topology tests; fixtures
now implement refresh/save_meta and enqueue-time metadata. No full-suite pass is
claimed until its final receipt is recorded.

Code-quality observability ran in observe-only mode. Radon was unavailable and
the tool reported no changed-file analysis with the uncommitted base-ref invocation;
this is a telemetry limitation, not measured complexity parity. The new outcome
module is 716 lines. QA accepts its bounded responsibility for this change;
retain the cancellation/identity regressions before any future decomposition.

## Evidence limits and rollout

Scientific inputs here are synthetic but parse through actual output readers.
The timeout scheduling case substitutes only the finalizer entrypoint with the
shared publisher; a separate test executes the production Culvert finalizer.
HTTP feature-grant state/cancellation identity and some NoDb/archive adapters are
fixtures. No full scientific model/Celery run, deployed service, production data
mutation or incident repair is claimed. Run the existing complete user workflow
under production-equivalent identities, groups, mounts, umask and configuration
before rollout. Original incident identity is excluded by the operator.
