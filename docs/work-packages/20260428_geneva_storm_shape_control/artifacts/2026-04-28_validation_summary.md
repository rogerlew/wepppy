# Validation Summary - Geneva Storm Shape Control

**Date**: 2026-04-28  
**Last rerun**: 2026-04-28 22:42 UTC (post-reconnect confirmation)
**Scope**: Required package validation commands from `prompts/active/execute_geneva_storm_shape_control_prompt.md`

## WEPPpy (`/workdir/wepppy`)

1. `wctl run-npm test -- geneva`  
   **Result**: Pass (`2` suites, `10` tests).

2. `wctl run-npm lint`  
   **Result**: **Known unrelated failure** in `wepppy/weppcloud/controllers_js/__tests__/landuse_map_inline.test.js` (`jest/no-conditional-expect`, 4 errors).  
   **Package impact**: None. Geneva-targeted JS tests remain green.

3. `python3 wepppy/weppcloud/controllers_js/build_controllers_js.py`  
   **Result**: Pass.

4. `wctl run-pytest tests/nodb/mods/geneva tests/weppcloud/routes/test_geneva_bp.py tests/weppcloud/routes/test_geneva_wp08_routes.py tests/rq/test_geneva_rq.py tests/microservices/test_rq_engine_geneva_routes.py --maxfail=1`  
   **Result**: Pass (`91 passed`).

5. `wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260428_geneva_storm_shape_control --path wepppy/nodb/mods/geneva/specification.md --path wepppy/nodb/mods/geneva/culvert-cn-comparison.md`  
   **Result**: Pass (`13 files validated, 0 errors, 0 warnings`).

6. `git diff --check`  
   **Result**: Pass.

## wepppyo3 (`/workdir/wepppyo3`)

1. `cargo test -p geneva_core`  
   **Result**: Pass (`64 passed`).

2. `git diff --check`  
   **Result**: Pass.

## Additional Runtime Smoke Check

- `wctl exec weppcloud python - <<'PY' ...` import probe for both module paths:  
  - `wepppyo3.climate.cli_revision_rust`: `geneva_build_hyetograph=True`  
  - `cli_revision_rust`: `geneva_build_hyetograph=True`

This confirms the updated compiled bindings expose the callable required by WEPPpy `GenevaBatchRunService`.

## Binary Provenance (cli_revision_rust)

- Build command executed:
  - `cd /workdir/wepppyo3 && cargo build -p cli_revision_rust --release`
- Sync commands executed:
  - `cp /workdir/wepppyo3/target/release/libcli_revision_rust.so /workdir/wepppyo3/release/linux/py312/wepppyo3/climate/cli_revision_rust.so`
  - `cp /workdir/wepppyo3/target/release/libcli_revision_rust.so /workdir/wepppy/cli_revision_rust/cli_revision_rust.abi3.so`
- SHA-256:
  - `334693548f6458c926afac7b31f0011d9538d2160ca0c3d93adf8e9ddd855519` `/workdir/wepppyo3/release/linux/py312/wepppyo3/climate/cli_revision_rust.so`
  - `334693548f6458c926afac7b31f0011d9538d2160ca0c3d93adf8e9ddd855519` `/workdir/wepppy/cli_revision_rust/cli_revision_rust.abi3.so`
