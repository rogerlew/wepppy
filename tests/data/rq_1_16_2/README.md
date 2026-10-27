# RQ 1.16.2 historical job fixtures

These synthetic Redis records were generated on forest on 2026-10-27 with the
installed RQ 1.16.2 / redis-py 6.2.0 runtime and isolated Redis 8.6.2. Functions
are only stdlib `math.sqrt` and `time.sleep`; no user data or credentials appear.
Keys and binary values are base64; explicit Redis types allow replay without
depending on a particular Redis DUMP serialization version. TTLs are retained
relative to snapshot restoration.

`running.json` records real queued, deferred, scheduled, running, successful and
failed jobs. A real worker and forked workhorses produced these records.
`drained.json` follows warm worker shutdown and a normal stop command against
the owned sleeping workhorse. This stops that job and leaves queued/deferred
successors unexecuted for migration tests. It is not a forged empty registry.

Generator provenance:
`docs/work-packages/20261027_rq_2_12_upgrade/artifacts/baseline-generate_legacy_fixtures.py`.
The generator refuses a nonempty isolated database; select another dedicated
database for a fresh capture. Never run it against application Redis.

`tests/rq/test_rq212_historical.py` restores these records only into explicitly
marked, otherwise empty DB4 on a supplied isolated Unix socket. It exercises
retained result reads, queued execution, strict dependent release and scheduled
execution using actual worker subprocesses. Running records are read for
diagnostic coverage, not represented as a supported cross-version handover.
Drain all running jobs under the old version before replacing workers.
