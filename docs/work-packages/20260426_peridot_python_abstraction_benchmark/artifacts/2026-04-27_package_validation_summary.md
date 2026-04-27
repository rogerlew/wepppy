# Package Validation Summary (2026-04-27)

## Scope

Validation covered preparation of the Peridot vs WEPPpy Python abstraction benchmark work package and post-close updates to the Peridot runtime-contract package.

## Command Results

```bash
cd /home/workdir/peridot
cargo test
```

Result: passed. Observed summary: `23` library tests, `2` CLI-wrapper unit tests, `14` integration tests, and `1` doctest passed. Two unused-import warnings remain in unrelated test modules.

```bash
cd /workdir/wepppy
wctl run-pytest tests/topo/test_peridot_runner_wait.py tests/topo/test_peridot_sub_fields_schema.py
```

Result: passed: `26 passed, 2 warnings`.

```bash
cd /workdir/wepppy
wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260426_peridot_runtime_contract_hardening --path docs/work-packages/20260426_peridot_python_abstraction_benchmark
```

Result: passed: `11 files validated, 0 errors, 0 warnings`.

```bash
cd /workdir/wepppy
git diff --check
```

Result: passed.

## Interpretation

- `confirmed`: Peridot source/test health is no longer blocking benchmark package execution.
- `confirmed`: WEPPpy Peridot runner schema tests still pass after package documentation updates.
- `confirmed`: The new benchmark work package and updated root tracker pass scoped doc lint.
- `inference`: The next benchmark package executor can start with comparator discovery rather than unresolved Peridot full-suite triage.
- `hypothesis`: The stale WEPPpy Python abstraction may still require remediation before meaningful benchmark timing can be collected.
