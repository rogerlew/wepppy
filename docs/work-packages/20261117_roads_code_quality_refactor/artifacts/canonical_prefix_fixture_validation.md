# Canonical prefix fixture qualification

The prior global `/tmp` retention-root override hid missing storage declarations
in upload fixtures and activated managed-retention behavior in unrelated tests.
This qualification preserves the inherited `dev-wc1` / `/wc1` environment and
replays all 14 modules selected in `canonical-prefix-sensitive-modules.json`.
No production code or new test cases were added.

## Failure-class evidence and repairs

The complete pre-repair run collected **537 items**: 31 failed, 477 passed and
29 skipped (47.50 seconds). All failures belong to four modules:

| Module under tests/microservices | Failures | Bounded repair |
| --- | ---: | --- |
| test_rq_engine_ag_fields_routes.py | 6 | Existing route fixture declares ID and tmp_path root |
| test_rq_engine_omni_routes.py | 6 | Existing normalizer fixture receives tmp_path and declares ID/root |
| test_rq_engine_upload_batch_runner_routes.py | 7 | Existing normalizer fixture receives tmp_path and declares ID/root |
| test_vector_upload_normalization.py | 12 | Local autouse fixture declares ID and tmp_path root |

Every affected module reproduced a representative failure on immutable baseline
`96555f2f95326350d2d7007c19327378ea831ab0`. Route probes yielded nine failures,
56 passes and one skip; a separate direct-normalizer probe failed with a temporary
filesystem root outside `/wc1`. Failures arise before the intended upload or
quarantine assertions, while constructing/persisting real upload evidence.

Each repaired fixture uses a bounded constant identity and its own temporary
root. Existing fake ledgers/leases remain unchanged. Dedicated real-ledger tests
still declare their unique identities explicitly; the missing-identity test still
deletes both settings and asserts rejection. `monkeypatch` restores environment
settings after each case. The change is 14 added lines and two replaced signature
lines across four test files.

## Final canonical replay

The full 14-module maxfail-zero replay passes **508 tests, 29 skipped** in
46.50 seconds. All **537 unique nodeids** exactly match the supplied prefix
selection. The external audit plugin retains setup/call/teardown outcomes, exit status,
and before/after SHA-256 values for all 14 modules, both applicable conftest files,
and pyproject.toml. The integrator's full-source manifest covers remaining imported
dependencies. Qualification must use these current-source outcomes for all 537
prefix items; earlier outcomes from globally aligned drivers are not substituted.

`canonical_prefix_execution.json` records all phases and unchanged source hashes:
517 setup passes, 20 setup skips, 508 call passes, nine call skips, and 537 teardown
passes. No phase failed; exit status is zero. `canonical_prefix_selection.json`
retains exact selection identities; `canonical_prefix_receipt.json` binds the
audit, logs, JUnit files and external runner snapshots by SHA-256. Logs/JUnit
files are under `candidate_logs/`, runners under `scripts/`. The immutable
baseline evidence is preserved.
