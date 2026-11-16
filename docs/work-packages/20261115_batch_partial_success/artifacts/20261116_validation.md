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

Real boundary command (the isolated host Redis socket is explicitly mounted; no production Redis or run data is used). To reproduce, start a disposable host Redis with TCP/persistence disabled, a socket below the mounted repository, and marker `batch-boundary-test-server=disposable` in database 0. Pass that socket through `BATCH_BOUNDARY_TEST_REDIS_SOCKET`. The fixture routes all Redis collaborators to it and refuses a server without the marker. Shut down that server after acceptance; this session did so after checking the marker. Without the override, the fixture starts its own local Redis or skips when `redis-server` is unavailable.

Command used:

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

The operator explicitly waived the full-suite requirement: “i don't think we need
to run the full suite of tests”. The running `wctl run-pytest tests --maxfail=1`
was interrupted promptly: **766 passed, 32 skipped**, no failure before interruption
(520.67 seconds). This is a partial receipt, not a full-suite pass. Earlier attempts
exposed outdated dummy Job interfaces; those fixtures were updated and their
focused suites pass. No further broad run is required for this delivery.

Code-quality observability reran against checkpoint `0aec93f1c` after commit:
20 changed files analyzed; 25 metric increases; observe-only gate passed. Radon
was unavailable, so complexity scores are unknown. The outcome module is 716
physical lines / 647 source lines; its longest function is 119 lines. Existing
batch dispatch grows from 185 to 208 lines for explicit enrollment and cancellation
guards; Culvert/Omni changes retain established structure. QA accepted these
bounded additions; preserve cancellation/identity coverage before future extraction.

Spelling previews found no changes in the new schema/package prose. Three shared
docs contain existing terminology or identifiers changed by whole-file `uk2us`;
those unrelated edits were not applied.

## Evidence limits and rollout

Scientific inputs here are synthetic but parse through actual output readers.
The timeout scheduling case substitutes only the finalizer entrypoint with the
shared publisher; a separate test executes the production Culvert finalizer.
HTTP feature-grant state/cancellation identity and some NoDb/archive adapters are
fixtures. No full scientific model/Celery run, deployed service, production data
mutation or incident repair is claimed. Run the existing complete user workflow
under production-equivalent identities, groups, mounts, umask and configuration
before rollout. Original incident identity is excluded by the operator.

## Delivery

Server implementation: `f13e4ce6f` in WEPPpy. Companion client implementation:
`c56fa19a7` in `/workdir/Culvert_web_app` on its existing `Production` branch.
No branch switch, push, deployment or production requeue. Unrelated dirty files
remain untouched. Temporary boundary projects and disposable Redis were cleaned
up after retaining the artifact/readback receipt.

## Push integration — 2026-11-16

WEPPpy implementation and closeout were pushed to `origin/master`. The client
remote advanced before push, so `c56fa19a7` was applied to current
`origin/Production` in an isolated detached checkout and pushed as `189af34e1`.
The conflict was integrated into the newer renewable-token polling helper,
preserving terminal 401/403 handling and returning the final payload for download.
Focused integration checks: 7 passed, 1 optional artifact-dependent test skipped;
syntax compilation and diff checks passed. Earlier 32-run artifact readback remains
recorded above. The original client checkout and unrelated local edits were left
unchanged; its local branch was not reset to the rewritten remote history.
