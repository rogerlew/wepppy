# Test Quality Findings (`test_guardian`)

## Initial pass (2026-03-21)

### High
- README conditional behavior coverage insufficient (`skip_flowpaths`, `representative_flowpath` branches not validated).

### Medium
- Peridot coverage was writer-level only; no entrypoint wiring coverage.
- WEPPpy fallback tests were partial (flowpaths CSV fallback and missing-table errors missing).
- Legacy migration tests were narrow (`remove_csv=True` only).

### Low
- Full WEPPpy suite sanity run (`wctl run-pytest tests --maxfail=1`) did not complete in this session.

## Fixes implemented
- Added Peridot manifest conditional test coverage:
  - `peridot/tests/watershed_parquet_manifest.rs`
  - Validates `skip_flowpaths=true`, `representative_flowpath=true`, non-clipping note, legacy width note.
- Expanded WEPPpy tests:
  - `tests/topo/test_peridot_runner_wait.py`
  - Added flowpaths CSV fallback + README refresh assertions.
  - Added missing primary-table error assertions.
  - Added output dtype assertions (`Int32`) in post path.
  - Added migration `remove_csv=False` behavior test.
  - Added migration parquet-over-CSV precedence test.

## Re-review result (2026-03-21)

### Medium residual
- No end-to-end Peridot entrypoint integration test for both abstraction binaries after task wiring changes.
- README tests still do not verify CSV compatibility rows/schemas explicitly.

### Low residual
- Migration tests check values but not all explicit dtype contracts on migrated columns.
- Full-suite WEPPpy sanity run remains unexecuted in this pass.

## Residual-risk rationale
- Core changed paths are covered by targeted passing suites and real-run verification.
- Remaining gaps are broader/integration-depth improvements suitable for follow-up coverage package.
