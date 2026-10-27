# Historical-state replay and isolated original-state rollback

Date: 2026-10-27 UTC. Implementation checkpoint: `b1054fac7`.
This evidence uses actual Redis, scheduler and forked worker subprocesses.
It does not assert mixed-version workers or in-place Redis downgrade safety.

## Provenance and results

`tests/data/rq_1_16_2/running.json` and `drained.json` contain synthetic records
captured from actual RQ 1.16.2 execution. The running capture includes queued,
deferred, scheduled, started, finished and failed jobs. A second capture follows
warm worker shutdown plus a normal stop command against its owned sleeping
workhorse; queued/deferred successors remain waiting, with no started members.
No user work was stopped. Binary values use base64 with explicit Redis types;
this avoids requiring a particular Redis DUMP serialization version.

The capture generator is [retained here](baseline-generate_legacy_fixtures.py).
The earlier [raw DUMP capture](rq-1.16.2-job-fixtures.json) is retained as initial
provenance but is not the portable fixture used by the regression tests.
[Fixture hashes](historical-fixture-sha256.json) identify the regression inputs.
[Interpreter provenance](historical-runtime-provenance.json) distinguishes the
installed RQ 1.16.2 from candidate 2.12.0 loaded through an isolated PYTHONPATH.
Both use redis-py 6.2.0 and the real disposable Redis 8.6.2 server.

| Stage | Result | Evidence |
| --- | --- | --- |
| Original records under RQ 1.16.2 | 2 passed, 17 warnings, 11.17s | [log](historical-1.16.2.log) |
| Original records under candidate RQ 2.12.0 | 2 passed, 2 warnings, 11.07s | [log](historical-2.12.0.log) |
| Restore original records and run RQ 1.16.2 again | 2 passed, 17 warnings, 11.27s | [log](historical-original-state-rollback.log) |
| Rebuilt installed RQ 2.12.0, historical plus metadata suites | 10 passed, 2 warnings, 31.35s | [log](rebuilt-historical-metadata.log) |

Every test restores records into an otherwise empty, explicitly marked DB4 on
the exclusively owned test Redis Unix socket. It cleans up only records created
after asserting the empty marked database. DB0, DB1, DB2, DB3 and the application
Redis are not cleared. The third stage replays the original frozen records after
candidate processing; it does not load 2.12-written records into 1.16.

## Supported evidence and boundaries

All six original job statuses deserialize. The retained finished result equals
9.0, and the retained failed result includes the expected math domain error.
On the genuinely drained snapshot, queued work returns 4.0, its strict dependent
releases and returns 5.0, and scheduled work stays scheduled until its fixture
due score is advanced. The actual RQ scheduler then admits that job and a forked
worker returns 6.0. Historical finished/failed records remain readable after
new execution, and queued/deferred registries are empty at completion.

The running capture retains a plain job-ID started-registry member. Readability
is useful for diagnosis but does not establish cross-version running execution
or abandonment recovery. **Running 1.16.2 jobs must drain under 1.16.2.** Do not
start 2.12 consumers against a nonempty old started registry. If an unrelated job
cannot drain, postpone that shared-Redis cutover rather than terminate it.

The fixture contains supported UUID-like IDs and stdlib functions. It does not
prove every historical function import, arbitrary custom job ID, every graph
shape or every retry/callback payload. Application-specific strict graph,
recovery and metadata regression suites supplement this evidence. Retained
failed jobs are read as failed; they are not silently retried or discarded.

## Safe migration and rollback procedure

Stop admissions from all affected producers/schedulers, then warm-stop affected
old workers. Inspect real worker current-job fields and raw started registries;
require no running work and retain queued/deferred/scheduled/failed/completed
records. Do not flush Redis. Capture a consistent, protected quiescent snapshot
and old image identities before enabling any 2.12 producer or worker. Replace
all affected execution participants together; no mixed-version execution is
claimed safe. User projects and generated artifacts need their own aligned
recovery point if acceptance mutates them.

If acceptance fails after 2.12 writes state, first stop new admissions and drain
owned work under 2.12. Preserve diagnostic state and project artifacts. Restore
the **original** quiescent Redis snapshot into an isolated/disposable recovery
environment with the old runtime and matching project recovery point, then
verify status, dependencies, schedules and artifact consistency before any live
recovery. Never overlay an old snapshot on concurrent unrelated work or
in-place downgrade consumers on 2.12-written state. The local proof above covers
restoration/re-execution of original synthetic records; it does not prove live
whole-stack rollback or a production snapshot/recovery procedure.

## Rebuilt forest validation

The historical and metadata suites passed together on the recreated forest
`weppcloud` runtime, with RQ imported from the installed `/opt/venv` and no
candidate dependency overlay. The historical two tests were included in the
10-pass result above. [Runtime provenance](rebuilt-historical-runtime-provenance.json)
records source `b5cac8166eaf067ac2ef79c440a82314c114111b`, application image
`sha256:88a982e44d316824f493c99d0c3a9a3db3e4800feef86ff2c65693677039162b`,
RQ 2.12.0, redis-py 6.2.0 and UID1000/GID993. The exact `wctl exec` invocation
and dedicated socket environment variables are retained in the test log.

Production remains unchanged. This closes the installed-runtime historical
replay gate; integrated model/API acceptance remains separately owned evidence.
