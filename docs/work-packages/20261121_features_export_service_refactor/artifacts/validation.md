# Features Export validation evidence

## Targeted tests

- `wctl run-pytest --profile python -- tests/nodb/mods/test_features_export*.py tests/rq/test_features_export_rq.py -q`
  passed 210 tests on the candidate source. The worktree runner recorded a
  matching source fingerprint before and after pytest in receipt
  `3b4c324777a24fca986a148ea2a63a48`.
- `tests/microservices/test_rq_engine_features_export_routes.py` passed 21
  tests in a disposable `wctl run` container with the candidate bind-mounted
  at `/workdir/wepppy`. The original combined invocation failed during
  collection because the installed dev image lacked `comrak`. The retry added
  the repository-pinned `comrak-ext==0.2.8` wheel through a read-only temporary
  mount and used `/opt/venv/bin/python -m pytest`.
- The full test suite was waived by the operator.

## Artifact readback

The service test with two subcatchments and format `geopackage` opens the
download ZIP, extracts its GeoPackage member, and queries the actual file.
The `gpkg_contents` identifier `shared__watershed.subcatchments` resolves to
a features table containing two rows and two non-null geometries. Companion
tests check ZIP members and cache-hit job metadata, regenerate invalid
GeoPackages and SQLite files missing GeoPackage markers, and read published
download paths from the persisted registry. The tabular materialization
tests read watershed Parquet identity pairs and assert Topaz ID backfill and
join-key retargeting.

## Source review

The extracted identity and format-check control flow matches the original
service bodies after import and name substitutions. The legacy column lookup
still accepts only string labels. The shared join planner implementations
match the service implementations they replace. Run-relative path resolution
still runs before cache format checks for export reuse and publication.
The changed-file broad-exception guard passed with zero net increase.

This evidence supports local fixture validation. Production execution and
deployment are outside this refactor.
