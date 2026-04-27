# Validation Summary (2026-04-26)

## Scope

Validation covered the Peridot runtime/source changes, WEPPpy compatibility normalization, package documentation, and manual Peridot documentation path checks for `20260426_peridot_runtime_contract_hardening`.

## Command Results

### Peridot

```bash
cd /home/workdir/peridot
cargo fmt
```

Result: passed.

```bash
cd /home/workdir/peridot
cargo test --test watershed_parquet_manifest --test field_flowpaths_schema --bin abstract_watershed --bin wbt_abstract_watershed
```

Result: passed.

Observed summary:

- `abstract_watershed` CLI wrapper test: `1 passed`.
- `wbt_abstract_watershed` CLI wrapper test: `1 passed`.
- `field_flowpaths_schema` integration test: `1 passed`.
- `watershed_parquet_manifest` integration test: `3 passed`.

```bash
cd /home/workdir/peridot
cargo test
```

Result: passed after follow-up Peridot full-suite fixes landed in commit `e09f54c` (`Fix Peridot full-suite regressions`).

Observed summary:

- Library tests: `23 passed`, `0 failed`.
- `abstract_watershed` CLI wrapper tests: `1 passed`.
- `wbt_abstract_watershed` CLI wrapper tests: `1 passed`.
- Integration tests: `14 passed`, `0 failed`.
- Doctests: `1 passed`, `0 failed`.

Interpretation: the earlier support interpolation panic-expectation failures and raster fixture/GDAL open failures are closed. The Peridot source/test tree is clean enough to start benchmark work. Two unused-import warnings remain in unrelated test modules and do not fail the suite.

```bash
cd /home/workdir/peridot
git diff --check
```

Result: passed.

### WEPPpy

```bash
cd /workdir/wepppy
wctl run-pytest tests/topo/test_peridot_sub_fields_schema.py
```

Result: passed: `4 passed, 2 warnings`.

```bash
cd /workdir/wepppy
wctl run-pytest tests/topo/test_peridot_runner_wait.py tests/topo/test_peridot_sub_fields_schema.py
```

Result: passed: `26 passed, 2 warnings`.

```bash
cd /workdir/wepppy
wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260426_peridot_runtime_contract_hardening
```

Result: passed: `6 files validated, 0 errors, 0 warnings`.

```bash
cd /workdir/wepppy
git diff --check
```

Result: passed.

## Manual Peridot Documentation Validation

No Peridot-local Markdown/doc lint tooling was found with:

```bash
cd /home/workdir/peridot
find . -maxdepth 3 \( -iname '*markdown*' -o -iname '*mdlint*' -o -iname '.markdown*' -o -iname 'Makefile' -o -iname 'justfile' \) -print | sort
```

Result: no tooling files returned.

Manual path checks passed for:

- `README.md`
- `docs/contracts/watershed-output-contract.md`
- `docs/migration/prepwepp-to-peridot.md`
- `docs/operations.md`
- `docs/benchmarks.md`
- `docs/contracts/`
- `docs/migration/`

Manual content check confirmed the old duplicate-header/follow-up language is gone from current Peridot docs and `flowpath_topaz_id` is present in docs, source, and tests.

## Validation Interpretation

- `confirmed`: CLI wrappers now propagate injected abstraction `io::Error` values in unit tests.
- `confirmed`: `field_flowpaths.csv` header generation now has unique first-five headers: `field_id`, `topaz_id`, `sub_field_id`, `flowpath_topaz_id`, `fp_id`.
- `confirmed`: WEPPpy post-processing accepts canonical `flowpath_topaz_id`, accepts historical pandas `topaz_id.1`, and rejects ambiguous mixed schemas.
- `confirmed`: Peridot full `cargo test` now passes after commit `e09f54c`; the earlier support/raster failures are no longer benchmark blockers.
- `inference`: Process status for propagated write-stage errors is now reliable because `main()` returns the wrapper `io::Result<()>`; Rust converts returned errors from `main` into non-zero process termination.
- `hypothesis`: Existing downstream consumers outside WEPPpy that depended on pandas `topaz_id.1` may need equivalent normalization if they read raw `field_flowpaths.csv` directly.

## Not Run

- Full WEPPpy suite: not run. The package touched Peridot runner normalization, tests, and docs; active package notes already identify unrelated broader-suite blockers.
- Peridot binary rebuild/deployment validation: not run. Deployment was explicitly out of scope, and preexisting dirty `target/release/*` binaries were left untouched.
