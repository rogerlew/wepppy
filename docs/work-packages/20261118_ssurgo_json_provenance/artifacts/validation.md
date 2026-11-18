# Integration validation

Candidate code: 39f24ce92442e76e8192ddf329ba70708d52c52a.
Contract ancestors: 090e9f2b6 and 2f9aff0a7. Service runtime: 9dc2264;
parity harness: soil-data-access 60a699f. Independent reviews are in
[contract-reviews.md](contract-reviews.md).

## Executed checks

- 75 focused tests passed: real HTTP and SQLite, error/deadline handling, cache
  isolation/events, sidecar publication, all six consumers, and NoDb persistence.
- The NoDb test used a disposable Unix-socket Redis with real locking and reload;
  it did not skip. The disposable Redis was stopped afterward.
- Stubtest passed for wepppy.soils.ssurgo.ssurgo and wepppy.nodb.core.soils.
- Test-stub completeness and changed broad-exception enforcement passed.
- The service's 34 Python contract/reference tests passed.
- Broad pytest was attempted and blocked at collection by missing test secrets:
  SECRET_KEY, then SECURITY_PASSWORD_SALT after supplying a disposable test key.
- Extended soils validation reached 46 passed and five skipped before the existing
  STATSGO spatial test opened an unhydrated LFS pointer as SQLite. No unrelated
  production settings or test expectations were changed to hide these blockers.

Tests used wctl --project-dir /workdir/wepppy-ssurgo-json --compose-file with an
isolated Compose configuration and run --rm --no-deps weppcloud. Its mount points
to the exact candidate checkout. The usual shared service run-pytest command would
consume the shared worktree instead, so no shared container was remounted/recreated.
Test containers had network_mode: none; only the explicit Redis socket was mounted.

## Generated-output evidence

The retained service reports live under artifacts/wepppy-parity/json-client in
soil-data-access, with actual source/image hashes and a reproducible client Compose
configuration. Fresh candidate caches query the real Rust/PostgreSQL service on an
internal Docker network with external connect errno 101. The comparison checks
positive row multisets, negative-key sets, selected components/horizons, invalid
outcomes, canonical soil bytes, and hash-verified base-soil sidecars.

The original development-image paired-case run failed two base diagnostic-comment
values because the numerical environment differs from the frozen reference. The
failure is retained as initial-image-failure.json. Matching reference Python/libc,
NumPy/DuckDB binaries and Rosetta code/model restores strict byte comparison;
no numerical tolerances or new comment exclusions were introduced. This does not
certify deployment-image equivalence. Full NoDb/RQ/raster workflows, national source
coverage, official imports, capacity, and rollout remain separate service gates.

Final replay result: all 24,049 positive cache rows and 501 canonical artifacts
match, with 499 valid soils, six preserved non-valid outcomes, 34 HTTP fetch events,
and 499 verified base sidecars. statsgo-001 remains empty and statsgo-002 remains
incomplete/excluded. The null-texture failure reproduces the exact reference
ValueError with the real candidate cache and collection horizon defaults.
