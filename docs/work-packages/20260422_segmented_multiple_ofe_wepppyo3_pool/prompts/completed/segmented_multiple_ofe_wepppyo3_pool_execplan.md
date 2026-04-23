# Segmented MOFE Migration to wepppyo3 + Process-Pool Refactor

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, MOFE slope segmentation no longer depends on Python `SlopeFile.segmented_multiple_ofe` for production watershed build flows. Segmentation is executed by `wepppyo3` (Rust/PyO3), and `WatershedOperationsMixin._build_multiple_ofe` uses canonical `createProcessPoolExecutor` orchestration for parallel work. The result should preserve MOFE output contracts while improving runtime and operational consistency.

## Progress

- [x] (2026-04-23 03:00 UTC) ExecPlan authored and linked from package tracker.
- [x] (2026-04-23 03:08 UTC) Defined wepppyo3 segmentation API contract to mirror `SlopeFile.segmented_multiple_ofe` behavior and output format (`.mofe.slp`).
- [x] (2026-04-23 03:16 UTC) Implemented wepppyo3 segmented MOFE routine + PyO3 binding (`wepppyo3.wepp_interchange.segment_single_ofe_slope`), exported in release package, and added wepppyo3 tests.
- [x] (2026-04-23 03:18 UTC) Refactored `_build_multiple_ofe` to canonical `createProcessPoolExecutor` orchestration with spawn-first retry and bounded sequential fallback semantics.
- [x] (2026-04-23 03:19 UTC) Deprecated legacy Python segmentation path: production `SlopeFile.segmented_multiple_ofe` now calls wepppyo3; legacy Python algorithm retained only as explicit deprecated `segmented_multiple_ofe_legacy`.
- [x] (2026-04-23 03:22 UTC) Added/updated WEPPpy regression tests for parity and process-pool orchestration behavior.
- [x] (2026-04-23 03:22 UTC) Captured parity + benchmark artifacts on `/wc1/runs/po/pointy-toed-fluff` and completed package closure updates.

## Surprises & Discoveries

- Observation: Initial Rust output had formatting drift in slope-file header float text (`243` vs Python `243.0`), causing text-level parity failures despite matching segment counts.
  Evidence: Full-run parity check over `3345` source `.slp` files initially reported `444` text mismatches; after header float-format fix parity mismatches dropped to `0`.

- Observation: Canonical `wctl run-pytest` validation was blocked because the `weppcloud` compose service is not running in this environment.
  Evidence: `wctl run-pytest tests/topo/test_watershed_abstraction_slope_file.py tests/nodb/test_watershed_mofe_map.py` returned `service "weppcloud" is not running`.

## Decision Log

- Decision: Keep this package focused on MOFE segmentation + `_build_multiple_ofe` orchestration only.
  Rationale: User request targets a bounded performance hotspot and execution pattern mismatch.
  Date/Author: 2026-04-23 / Codex.

- Decision: Treat existing Python segmentation tests as behavior oracle for Rust parity.
  Rationale: Existing fixtures cover rounding/duplicate-distance and max-segment edge-cases critical to WEPP slope-file correctness.
  Date/Author: 2026-04-23 / Codex.

- Decision: Make wepppyo3 segmentation a hard production dependency for `SlopeFile.segmented_multiple_ofe` and keep Python segmentation only behind explicit deprecated legacy method.
  Rationale: Requirement is to replace Python behavior as primary production path, not keep it silently primary/fallback.
  Date/Author: 2026-04-23 / Codex.

- Decision: Benchmark and parity validation use isolated temp directories with copied source `.slp` files and never write into `/wc1/runs/po/pointy-toed-fluff`.
  Rationale: Requirement explicitly forbids modifying the source run while collecting realistic performance evidence.
  Date/Author: 2026-04-23 / Codex.

## Outcomes & Retrospective

Completed end-to-end. Production MOFE segmentation now runs through wepppyo3 (`segment_single_ofe_slope`), `_build_multiple_ofe` now follows canonical spawn-first pool orchestration with bounded fallback semantics, and the Python segmentation implementation is explicitly deprecated/non-primary.

Validation outcomes:
- WEPPpy targeted tests (direct local pytest due stopped compose service): `17 passed`.
- wepppyo3 targeted tests: `8 passed`.
- Full parity check artifact on `/wc1/runs/po/pointy-toed-fluff`: `3345` source slope files compared; `0` mismatches.
- Alternating old/new benchmark artifact on `/wc1/runs/po/pointy-toed-fluff` (10 samples, isolated temp dirs): old mean `2.148501s`, new mean `0.938375s`, delta `-56.32%`.

Residual risk:
- Canonical Docker-wrapped `wctl` test execution for this package remains pending environment readiness (`weppcloud` service down). Direct local pytest evidence is captured, but containerized parity of these same tests was not rerun in this session.

## Context and Orientation

Primary implementation locations:

- `wepppy/topo/watershed_abstraction/slope_file.py`
  - `SlopeFile.segmented_multiple_ofe` (legacy Python segmentation routine).
- `wepppy/nodb/core/watershed_mixins.py`
  - `WatershedOperationsMixin._build_multiple_ofe` (current synchronous call path).
- `wepppy/nodb/base.py`
  - `createProcessPoolExecutor` canonical process-pool helper.
- `tests/topo/test_watershed_abstraction_slope_file.py`
  - Segmentation behavior edge-case tests.
- `tests/nodb/test_watershed_mofe_map.py`
  - MOFE map integration/path tests.
- `/home/workdir/wepppyo3/`
  - Rust/PyO3 workspace where new segmentation routine should live.

## Plan of Work

Milestone 1 performs API/behavior discovery and writes a minimal parity contract for segmentation inputs/outputs and edge behavior (rounding, endpoint handling, max-ofe cap, buffer mode).

Milestone 2 implements segmented MOFE generation in `wepppyo3` and exposes a Python-callable entry point used by WEPPpy.

Milestone 3 updates `_build_multiple_ofe` to use canonical `createProcessPoolExecutor` orchestration, including spawn-first context and bounded fallback semantics used elsewhere in NoDb.

Milestone 4 deprecates Python segmentation path, updates stubs/docs/tests, and validates parity + performance on `/wc1/runs/po/pointy-toed-fluff`.

## Concrete Steps

Working directories:
- `/home/workdir/wepppy`
- `/home/workdir/wepppyo3`

1. Discover and lock segmentation behavior contract.

    cd /home/workdir/wepppy
    rg -n "segmented_multiple_ofe|_build_multiple_ofe|createProcessPoolExecutor" wepppy/topo/watershed_abstraction/slope_file.py wepppy/nodb/core/watershed_mixins.py wepppy/nodb/base.py

2. Implement wepppyo3 routine + binding.

    cd /home/workdir/wepppyo3
    rg -n "pyo3|#[[:space:]]*pyfunction|#[[:space:]]*pymodule" .

3. Integrate WEPPpy call-site and process pool orchestration.

    cd /home/workdir/wepppy
    rg -n "_build_multiple_ofe|mofe_nsegments" wepppy/nodb/core/watershed_mixins.py

4. Update tests/stubs/docs.

    cd /home/workdir/wepppy
    wctl run-pytest tests/topo/test_watershed_abstraction_slope_file.py tests/nodb/test_watershed_mofe_map.py

5. Benchmark old/new behavior on target run.

    Use `/wc1/runs/po/pointy-toed-fluff` with isolated temp working directories and alternating old/new runs.

## Validation and Acceptance

Acceptance is met when:

- `segmented_multiple_ofe` production path is provided by `wepppyo3` and called from WEPPpy.
- `_build_multiple_ofe` uses canonical `createProcessPoolExecutor` orchestration semantics.
- Legacy Python segmentation path is deprecated and non-primary.
- Existing segmentation edge-case tests pass under the new path.
- MOFE map behavior remains contract-compatible.
- Benchmark artifact captures measured before/after outcome on `/wc1/runs/po/pointy-toed-fluff`.

## Idempotence and Recovery

Changes should be incremental and reversible:

- Keep legacy Python segmentation callable behind a deprecation boundary until parity validation is complete.
- If wepppyo3 integration fails, retain temporary fallback path and mark gate as incomplete rather than silently changing behavior.
- Do not remove legacy path until tests and benchmark artifacts are captured.

## Artifacts and Notes

Store outputs under:

- `docs/work-packages/20260422_segmented_multiple_ofe_wepppyo3_pool/artifacts/benchmark_summary.md`
- `docs/work-packages/20260422_segmented_multiple_ofe_wepppyo3_pool/artifacts/parity_notes.md`

## Interfaces and Dependencies

Required end-state interfaces:

- A stable Python-callable wepppyo3 function for MOFE segmentation used by `_build_multiple_ofe`.
- Legacy `SlopeFile.segmented_multiple_ofe` clearly marked deprecated in docs/stubs/comments.
- `_build_multiple_ofe` concurrency path uses `createProcessPoolExecutor` helper.

## Revision Notes

- 2026-04-23 / Codex: Initial ExecPlan authored from user-requested MOFE segmentation migration + process-pool refactor requirements.
- 2026-04-23 / Codex: Completed implementation, parity/benchmark validation, and package closure evidence capture.
