# Execute: Deterministic Return Ordering for wepppyo3 Raster Characteristics APIs

Execute this work package end-to-end:

- Package: `/workdir/wepppy/docs/work-packages/20260512_wepppyo3_raster_characteristics_deterministic_order/`
- Active ExecPlan: `/workdir/wepppy/docs/work-packages/20260512_wepppyo3_raster_characteristics_deterministic_order/prompts/active/wepppyo3_raster_characteristics_deterministic_order_execplan.md`
- WEPPpy repo: `/workdir/wepppy`
- wepppyo3 repo: `/home/workdir/wepppyo3`

Required outcomes:
1. All public map-returning `wepppyo3.raster_characteristics` APIs return deterministic key order.
2. Value semantics and error contracts are preserved.
3. Deterministic-order and parity tests pass in `wepppyo3`.
4. Targeted WEPPpy consumer tests pass.
5. Release artifact is rebuilt and refreshed in `release/linux/py312` with runtime import + hash evidence.
6. `wepppyo3` docs are updated (`README.md`, `docs/module-registry.md`, `docs/release-provenance.md`).
7. Mandatory independent code review artifact is completed with no unresolved high/medium findings.
8. Package lifecycle docs and tracker states are closed cleanly.

Read first:
1. `/workdir/wepppy/AGENTS.md`
2. `/home/workdir/wepppyo3/AGENTS.md`
3. `/workdir/wepppy/docs/prompt_templates/codex_exec_plans.md`
4. `/workdir/wepppy/docs/work-packages/20260512_wepppyo3_raster_characteristics_deterministic_order/package.md`
5. `/workdir/wepppy/docs/work-packages/20260512_wepppyo3_raster_characteristics_deterministic_order/tracker.md`
6. `/workdir/wepppy/docs/work-packages/20260512_wepppyo3_raster_characteristics_deterministic_order/prompts/active/wepppyo3_raster_characteristics_deterministic_order_execplan.md`

Implementation scope:
- wepppyo3 implementation:
  - `/home/workdir/wepppyo3/raster_characteristics/src/lib.rs`
  - `/home/workdir/wepppyo3/release/linux/py312/wepppyo3/raster_characteristics/__init__.py`
- wepppyo3 tests:
  - `/home/workdir/wepppyo3/tests/raster_characteristics/`
- WEPPpy targeted consumer tests:
  - `tests/nodb/test_landuse_coverage_area_source.py`
  - `tests/soils/test_wepppyo3_nodata_guard.py`
  - Optional if needed: `tests/nodb/mods/test_omni_contrast_build_service.py`, `tests/nodb/mods/test_omni.py`
- wepppyo3 docs:
  - `/home/workdir/wepppyo3/README.md`
  - `/home/workdir/wepppyo3/docs/module-registry.md`
  - `/home/workdir/wepppyo3/docs/release-provenance.md`
- Work-package lifecycle and artifacts:
  - `/workdir/wepppy/docs/work-packages/20260512_wepppyo3_raster_characteristics_deterministic_order/package.md`
  - `/workdir/wepppy/docs/work-packages/20260512_wepppyo3_raster_characteristics_deterministic_order/tracker.md`
  - `/workdir/wepppy/docs/work-packages/20260512_wepppyo3_raster_characteristics_deterministic_order/artifacts/`
  - `/workdir/wepppy/PROJECT_TRACKER.md`

Execution constraints:
- Keep scope limited to deterministic ordering hardening plus required tests/release/docs/review gates.
- Do not introduce silent fallback wrappers or broad exception handlers.
- Preserve existing public API names, arguments, output values, and canonical failure contracts.
- Keep the active ExecPlan and tracker as living documents with UTC timestamps.
- Do not stage or revert unrelated dirty files.

Execution sequence:
1. Set package state to `In Progress` in `PROJECT_TRACKER.md` and log kickoff in package `tracker.md`.
2. Baseline every public `raster_characteristics` API return container and current ordering behavior.
3. Implement deterministic ordering at the `wepppyo3` API boundary.
4. Add or adjust deterministic-order and semantic-parity tests in `wepppyo3`.
5. Run targeted WEPPpy consumer tests.
6. Refresh release artifact:
   - build `raster_characteristics_rust`
   - copy `.so` into `release/linux/py312/wepppyo3/raster_characteristics/`
   - verify import from release tree
   - capture SHA256
7. Update wepppyo3 docs for deterministic-order contract and release-refresh evidence.
8. Dispatch mandatory independent code review (`reviewer` sub-agent), disposition findings, and resolve all high/medium findings.
9. Capture validation evidence in artifacts and close package docs, including moving active ExecPlan to `prompts/completed/` when complete.

Validation commands:
- From `/home/workdir/wepppyo3`:
  - `pytest tests/raster_characteristics -q`
  - `cargo test -p raster_characteristics_rust`
  - `export PYO3_PYTHON=/usr/bin/python3.12`
  - `export PYTHON_SYS_EXECUTABLE=$PYO3_PYTHON`
  - `cargo build -p raster_characteristics_rust --release`
  - `cp target/release/libraster_characteristics_rust.so release/linux/py312/wepppyo3/raster_characteristics/raster_characteristics_rust.so`
  - `PYTHONPATH=/home/workdir/wepppyo3/release/linux/py312 python3.12 -c "from wepppyo3.raster_characteristics import raster_characteristics_rust as rc; print(rc.__file__)"`
  - `sha256sum release/linux/py312/wepppyo3/raster_characteristics/raster_characteristics_rust.so`
  - `git diff --check`
- From `/workdir/wepppy`:
  - `wctl run-pytest tests/nodb/test_landuse_coverage_area_source.py tests/soils/test_wepppyo3_nodata_guard.py --maxfail=1`
  - Optional: `wctl run-pytest tests/nodb/mods/test_omni_contrast_build_service.py tests/nodb/mods/test_omni.py --maxfail=1`
  - `wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260512_wepppyo3_raster_characteristics_deterministic_order`
  - `git diff --check`

Required artifacts:
- `artifacts/ordering_contract_matrix.md`
- `artifacts/validation_summary.md`
- `artifacts/20260513_release_refresh.md`
- `artifacts/20260513_code_review.md`

Finish with:
- Changed files grouped by repository (`/workdir/wepppy` and `/home/workdir/wepppyo3`).
- Deterministic-order contract summary for each public API.
- Validation command results with pass/fail counts.
- Release refresh provenance summary (`.so` path, import proof, SHA256).
- Code-review disposition summary and any accepted residual risks.
