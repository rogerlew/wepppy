# Archive fixture environment failure-class assessment

Date: 2026-11-17. This is test isolation work discovered by the broad gate;
production Roads/native source and its completed evidence remain unchanged.

## Confirmed class and bounded repair

Ordinary archive provenance tests inherited the development stack's
`VECTOR_UPLOAD_RUN_FILESYSTEM_ID` plus the validation driver's global `/tmp`
filesystem-root override. Those tests
have no vector-retention filesystem/ledger fixture, but inherited configuration
activates the real maintenance lease against the general `RecordingRedis` stub.
Both ownership checks and release then raise `AttributeError` for missing `eval`.

The two directly owned tests reproduce this exact failure on immutable baseline
`96555f2f95326350d2d7007c19327378ea831ab0`:

- `tests/nodb/test_cli_parquet_lineage.py::test_cleanup_skeleton_archive_restore_keep_history`
- `tests/wepp/reports/test_report_cache_freshness.py::test_canonical_archive_restore_keeps_report_provenance_and_failed_work`

Baseline result under that driver override: **2 failed**, 11.64 seconds.
This does not establish failure under canonical `/wc1`; see the later controlled
comparison and driver-scope correction in `validation_environment_scope.md`. The repair deletes only those two
inherited environment variables inside each test via `monkeypatch`; the CLI test
adds the standard fixture argument. Real archive/restore behavior, provenance and
failed-work assertions remain intact. Neither production code nor Redis stubs
change. Dedicated vector-retention tests keep their explicit environment and real
ledger setup.

## Consumer coverage

Repository search for `ArchiveRuntime`, `archive_rq` and `restore_archive_rq`
identified exactly three direct runtime constructors: the two tests above and
`tests/nodb/mods/geneva/test_geneva_cache_freshness.py`, handled separately by the
integrator. Other ordinary archive consumers reuse the already repaired
`archive_rq_environment` fixture.

`tests/nodb/test_redis_prep_snapshots.py` has four archive/restore consumers through
its own wrapper fixture and disposable-Redis lifecycle. A scoped baseline attempt
skipped all four because neither `redis-server` nor `RQ212_TEST_REDIS_SOCKET` is
available in the image. Their runtime behavior is unqualified here; no speculative
repair was made. `tests/rq/test_project_rq_archive_helpers.py` invokes only pure
archive helpers and passed all three tests in the same baseline attempt.

## Evidence

The guarded one-off `wctl` commands and complete outputs are retained in
`candidate_logs/direct-archive-baseline.log`,
`candidate_logs/direct-archive-redis-baseline.log`, and
`candidate_logs/direct-archive-candidate.log`. Both complete candidate modules pass: **76 passed**, four deprecation warnings,
42.14 seconds. `archive_fixture_receipt.json` records scoped counts and source/log
hashes. Broad-suite continuation remains with the integrator.
