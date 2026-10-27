# RQ 1.16.2 forest baseline

Captured 2026-10-27 19:08–19:12 UTC by independent baseline agent. No application
source, installed runtime, shared queue, user project, or remote host changed.

## Runtime and unrelated work

Host is `forest`; Docker context `default` selects `unix:///var/run/docker.sock`.
Installed `wctl` selects `docker/docker-compose.dev.yml`, Compose project `docker`.
The checked application image is
`sha256:f03d9c55f49229bd1dfb9f720c420ef2568de7919b132ddd7c735a71f4652bcf`.
Web, rq-engine, all three worker pools, scheduler, query-engine, profile-playback,
browse and download report RQ 1.16.2 / redis-py 6.2.0, UID1000/GID993, groups993.
Worker umask is 0022. The separately built dashboard reports RQ 2.0.0 /
redis-py 5.2.0 and UID0/GID0; it is an existing mixed-version observer, not proof
that mixed-version execution is safe.

All 11 registered workers were idle: six `default`, four `batch`, one
`fork-archive`, using `wepppy.rq.WepppyRqWorker`. Worker-pool commands do not pass
`--with-scheduler`; the separate scheduler runs `wepppy.tools.scheduler`.
Shared queues have zero started jobs, but contain unrelated deferred work:
592 default, 445 batch, seven `qcat-mill-creek-model-20261023`. Queue
`qcat-variants-catalog-20261023` has one queued job and no registered listener.
These states were observed without registry cleanup and remain untouched.

Sanitized evidence: [versions](baseline-runtime-versions.json),
[configuration and mounts](baseline-runtime-configuration.json),
[queue/worker snapshot](baseline-queue-workers.json). Configuration contains only
literal secret-file references, never secret values. Original project scans
used raw files, avoiding NoDb hydration or cache writes.

## Regression results

`wctl run-pytest` ran worker identity, dependency, cancellation, job-info,
query-catalog, fork/archive/run-sync and corresponding API tests:
**363 passed, 24 skipped, 84 warnings, 38.99s**.
[Transcript](baseline-targeted-pytest.log) retains the exact selection. The 24
skips require a Redis executable absent from the application image; they were
subsequently exercised against an isolated real server below.

Auth, submission acknowledgment recovery, mutation containment and startup tests:
**122 passed, 28 warnings, 1.69s**.
[Transcript](baseline-auth-submission-pytest.log) retains the exact selection.

Real Redis batch/task-boundary and query-catalog tests:
**51 passed, zero skipped, 4787 warnings, 32.91s**.
[Transcript](baseline-real-redis-enabled-pytest.log) includes real production worker
fork execution, dependency/finalizer semantics, concurrent graph attachments and
killed-worker abandonment recovery. These tests are focused integration evidence;
they do not establish model/API acceptance or every upgrade requirement.

## Isolated Redis and historical fixtures

Created only `rq212-baseline-redis`, using canonical `wctl run --no-deps --rm`,
the installed Redis image, UID1000/GID993, TCP disabled, persistence disabled,
and an owned override for `/data`. Its Unix socket is mode700 at
`/workdir/wepppy/.pytest_cache/rq212-baseline/redis.sock`; the shared application
Redis volume is never mounted into this test instance. DB0 has the required
`batch-boundary-test-server=disposable` marker. DB1 contains synthetic fixtures.
No shared Redis flush or cleanup was performed.

The generic `wctl run-pytest` wrapper does not forward
`BATCH_BOUNDARY_TEST_REDIS_SOCKET`. The enabled run uses equivalent canonical
`wctl exec -T -e BATCH_BOUNDARY_TEST_REDIS_SOCKET=... weppcloud bash -lc ... pytest`;
the transcript records the exact command. This is a tooling limitation, not a
test skip or migration defect.

[Initial 20 Redis DUMP payloads](rq-1.16.2-job-fixtures.json) capture actual RQ 1.16.2 jobs in
six states: queued, deferred, scheduled, started, finished and failed. Completed
and failed results use real forked workhorses; the started job is captured while
its workhorse sleeps. After capture it is stopped with RQ's stop command and the
worker exits. The queued/deferred successors then finish on the disposable server;
the retained snapshot preserves their earlier states. All job functions are
stdlib `math.sqrt` or `time.sleep`; no project data, identity tokens or executable
application payloads are embedded. Redis server version is recorded in the JSON.

The [retained generator](baseline-generate_legacy_fixtures.py) was subsequently
updated to capture portable typed records plus a genuinely drained snapshot.
[Historical compatibility](historical_compatibility.md) records those fixtures,
candidate execution and original-state rollback results.

Restoration tests must use another empty disposable database and restore only
these payloads; never load them into shared Redis. A started snapshot includes
historical worker/execution bookkeeping and is a recovery test input, not
authorization to resume an old workhorse. The server remains available for the
parent's upgrade tests. After all owned work is finished, remove it with
`docker stop rq212-baseline-redis` (its `--rm` policy removes the owned container).
Retain the fixtures and logs; do not remove shared queue records.

## Bounded model/API candidate

Read-only inspection found `/wc1/runs/rl/rlew-international-refuge`: 28 hillslope
decks, six observed climate years (2000–2005), `disturbed-wbt-profile.cfg`, and
complete soil, landuse, climate, watershed and interchange artifacts. Its selected
`wepp_250915` and hillslope executable are present locally. Clone using the actual
fork API with a unique `target_runid` and `skip_wepp_runs_output=true`, then submit
`POST /api/runs/{runid}/{config}/run-wepp` with run-scoped authorization. Compare
fresh generated inputs and outputs on independent baseline/upgraded clones.
This is a candidate, not yet verified acceptance. Preserve the original source.

`tools/surf14a_local_acceptance.py` demonstrates real HTTP session and JWT handling;
its old fixed-resource workflow must not be run directly. A smaller three-deck
`wb34-impoundment-cohort` is unsuitable because it lacks project NoDb and input
directories. The prior `anisotropic-sassafras` acceptance donor has 73 hillslopes
and 100 years, so the 28-hillslope candidate should bound this migration better.

No live API submissions or model runs were made by this baseline task.
