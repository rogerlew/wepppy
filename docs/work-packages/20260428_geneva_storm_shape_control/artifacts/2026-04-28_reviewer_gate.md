# Reviewer Gate - Geneva Storm Shape Control

**Date**: 2026-04-28  
**Reviewer role**: `reviewer`  
**Agents**: `019dd620-5972-7203-ab52-266244897ccd`, `019dd626-d2ca-76c1-9501-42d2bf573486`  
**Scope**: WEPPpy + wepppyo3 storm-shape implementation diff, with focus on correctness, regressions, compatibility, and stale-artifact behavior.

## Findings and Dispositions

1. **High** - Missing runtime callable `geneva_build_hyetograph` in deployed/imported kernel bindings.  
   **Disposition**: **Closed**. Rebuilt `cli_revision_rust` release binary and refreshed both runtime import surfaces:
   - `/workdir/wepppyo3/release/linux/py312/wepppyo3/climate/cli_revision_rust.so`
   - `/workdir/wepppy/cli_revision_rust/cli_revision_rust.abi3.so`
   Also added gateway regression coverage for fallback callable resolution in:
   - `tests/nodb/mods/geneva/test_geneva_collaborators.py` (`test_kernel_gateway_falls_back_to_cli_revision_rust_for_hyetograph_api`)
   Runtime smoke verification (container import) now confirms callable exists in both module paths.

2. **High** - Hyetograph endpoint behavior can produce non-uniform timestep grid rejected by CN kernel.  
   **Disposition**: **Closed**. Added explicit run-batch validation in:
   - `wepppy/nodb/mods/geneva/collaborators/batch_run_service.py`
   The service now rejects non-divisible `duration_minutes / time_step_minutes` combinations as `invalid_input` before CN kernel execution. Added regression:
   - `tests/nodb/mods/geneva/test_geneva_collaborators.py` (`test_batch_run_rejects_non_divisible_duration_time_step`)

3. **High** - Stale summary artifacts can be reported as completed for a different storm shape.  
   **Disposition**: **Closed**. Added distribution-consistency checks and stale-status suppression in:
   - `wepppy/nodb/mods/geneva/collaborators/report_payload_service.py`
   Added lifecycle clearing on panel distribution change in:
   - `wepppy/nodb/mods/geneva/geneva.py`
   Added regressions:
   - `tests/nodb/mods/geneva/test_geneva_report_payload_service.py`
   - `tests/nodb/mods/geneva/test_geneva_facade.py`

4. **Medium** - Frequency panel cache ignored requested `distribution_type` when `rebuild=false`.  
   **Disposition**: **Closed**. Updated cache logic in:
   - `wepppy/nodb/mods/geneva/collaborators/frequency_panel_service.py`
   Cached panel now returns only when distribution matches; otherwise service rebuilds with requested shape. Added regression:
   - `tests/nodb/mods/geneva/test_geneva_collaborators.py` (`test_frequency_panel_service_rebuilds_cached_panel_when_requested_shape_changes`)

5. **Medium** - Zero-depth available cells accepted upstream but rejected by hyetograph kernel (`depth_mm > 0`).  
   **Disposition**: **Closed**. Aligned contracts across layers:
   - `wepppy/nodb/mods/geneva/schemas/query_schema.py` now requires positive `depth_mm` and `intensity_mm_per_hr` for available cells.
   - `wepppy/nodb/mods/geneva/collaborators/batch_run_service.py` now rejects `depth_mm <= 0`.
   - `/workdir/wepppyo3/geneva_core/src/frequency_panel.rs` now enforces `depth_mm > 0` and `intensity > 0`.
   Added regressions in Python and Rust test suites.

6. **Medium** - Required WinTR-20 resource files were untracked.  
   **Disposition**: **Closed (worktree state)**. Resource files are now present under:
   - `/workdir/wepppyo3/geneva_core/resources/`
   including raw, normalized CSV, and metadata artifacts required by package gate and Rust `include_str!` use.

## Residual Risk

- `wctl run-npm lint` still reports an unrelated pre-existing failure in `controllers_js/__tests__/landuse_map_inline.test.js` (`jest/no-conditional-expect`); this package did not modify that file.
