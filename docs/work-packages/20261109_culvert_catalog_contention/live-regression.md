# Live culvert batch regression

The fast clone regression in `tests/culverts/test_culverts_runner.py` exercises
real copying and catalog identity for absent, initialized and pending metadata.
It reproduces the original production failure before the clone fix. Real Redis
and process races in `tests/nodb/test_redis_prep_snapshots.py` cover sibling catalog
publication versus RedisPrep writes; HTTP contention tests retain waiting behavior.

`tests/culverts/test_culvert_batch_live.py` is an opt-in regression through normal
HTTP admission, parallel RQ workers, finalization and authenticated download.
Run it inside the forest stack with its mounted culvert root. It requires:

- `CULVERT_BATCH_TEST_ORIGIN`: explicit ingress origin, e.g. `http://caddy:8080`.
- `CULVERT_BATCH_TEST_PAYLOAD`: path to a known-good multi-culvert ZIP.
- `CULVERT_BATCH_TEST_TOKEN_FILE`: private file containing a service JWT with
  `culvert:batch:submit` scope. Never put the token in commands or committed files.
- `CULVERT_BATCH_TEST_HOST`: ingress Host override when using internal Caddy.
- Optional `CULVERT_BATCH_TEST_TIMEOUT`: seconds, default 7200.

Execute through `wctl exec -T -e ... weppcloud` with the above environment paths,
then `/opt/venv/bin/pytest tests/culverts/test_culvert_batch_live.py -s -q` from
`/workdir/wepppy`. Unconfigured full-suite runs skip this intentionally mutating
live test. Partial configuration fails; it must not silently skip a configured gate.

The test creates a fresh batch and retains it, including failures. It never
retries failed children. It asserts every expected point succeeds, distinct base
and child catalog identities, matching hillslope/landuse/soil IDs, positive finite
areas, finite daily/event outputs, contiguous simulation days, readable Parquet,
all child/finalizer RQ statuses, at least two overlapping child execution intervals,
authenticated browse/download and every ZIP member
hash against generated files. A finished finalizer alone cannot pass this gate.

Pytest's temporary directory retains non-secret `evidence.json`, the downloaded
archive and mode-0600 admission credentials for diagnosis. Do not publish the
private admission file. Do not run this against production without explicit
operator authorization. The exact incident payload is retained outside git at
`/tmp/culvert-catalog-regression-20261109/payload.zip`; SHA-256 is recorded in the
active plan. No production payload or credentials are committed to the suite.


## Disposable Redis gate

The process-concurrency suites need real Redis. In this container image they
skip unless a disposable server is supplied. Set `RQ212_TEST_REDIS_SOCKET` for
RedisPrep races and `BATCH_BOUNDARY_TEST_REDIS_SOCKET` for catalog worker/pilot
suites to the marked disposable socket defined by their fixtures. Check actual
executed counts; a skipped concurrency suite is not acceptance. The clone-state
pytest does not require running a full model or the live batch gate.
