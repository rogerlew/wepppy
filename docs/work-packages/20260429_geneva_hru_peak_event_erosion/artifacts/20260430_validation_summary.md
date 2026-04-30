# Validation Summary - Geneva HRU Peak Runoff and Choropleth Measure

Date: 2026-04-30 (UTC)
Reviewer/Executor: Codex

## Binary Sync Evidence

- `/workdir/wepppyo3/release/linux/py312/wepppyo3/climate/cli_revision_rust.so`
- `/workdir/wepppy/cli_revision_rust/cli_revision_rust.abi3.so`
- SHA-256 (both): `644669cc1f04584012c9b772b2e2a0e87dfbafbb9e83745f025c07e01c6ac362`

## Required Command Gates

### `/workdir/wepppyo3`

1. `cargo test -p geneva_core`
- Result: PASS
- Evidence: `68 passed; 0 failed`

2. `cargo test -p cli_revision_rust geneva`
- Result: PASS
- Evidence: `19 passed; 0 failed`

3. `cargo fmt --check`
- Result: PASS

### `/workdir/wepppy`

1. `wctl run-pytest tests/nodb/mods/geneva --maxfail=1`
- Result: PASS
- Evidence: `71 passed; 0 failed`

2. `wctl run-pytest tests/weppcloud/routes/test_geneva_bp.py tests/weppcloud/routes/test_geneva_wp08_routes.py --maxfail=1`
- Result: PASS
- Evidence: `28 passed; 0 failed`

3. `wctl run-npm test -- geneva`
- Result: PASS
- Evidence: `2 passed suites, 14 passed tests`

4. `wctl run-npm lint`
- Result: FAIL (unrelated pre-existing baseline)
- Failure:
  - `wepppy/weppcloud/controllers_js/__tests__/landuse_map_inline.test.js`
  - `jest/no-conditional-expect` on lines `99, 100, 101, 103`
- Unrelated rationale:
  - This package did not touch `landuse_map_inline.test.js`.
  - The same lint baseline is already documented in recent Geneva package closures.

5. `python3 wepppy/weppcloud/controllers_js/build_controllers_js.py`
- Result: PASS

6. `wctl doc-lint --path docs/work-packages/20260429_geneva_hru_peak_event_erosion --path wepppy/nodb/mods/geneva/specification.md`
- Result: PASS
- Evidence: `9 files validated, 0 errors, 0 warnings`

7. `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- Result: PASS
- Evidence: `Net delta (all changed files): +0`

8. `git diff --check`
- Result: PASS

## Notes

- Focused iteration checks also passed before full-gate execution:
  - `tests/nodb/mods/geneva/test_geneva_hru_event_measure_service.py`
  - `tests/nodb/mods/geneva/test_geneva_collaborators.py`
  - `tests/nodb/mods/geneva/test_geneva_facade.py`
- No unrelated runtime/test failures were observed beyond the existing lint baseline above.
