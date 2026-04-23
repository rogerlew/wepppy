# MOFE Map Migration to wepppyo3 (Topaz Pre-Index + One-Pass Rank Assignment)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, MOFE map label construction is no longer a Python raster-scan hotspot inside `WatershedOperationsMixin._build_mofe_map`. The production path calls a Rust/PyO3 API in `wepppyo3` that pre-indexes cells by `topaz_id` and assigns OFE labels from discharge ranks in one pass per hillslope, while preserving existing contiguous-label and fallback/repair behavior.

## Progress

- [x] (2026-04-23 04:06 UTC) Package and tracker scaffold created.
- [x] (2026-04-23 04:06 UTC) Active ExecPlan authored and activated.
- [x] (2026-04-23 04:27 UTC) Implemented `wepppyo3.watershed_abstraction.assign_mofe_map` (new crate/module) with topaz pre-indexing, legacy fallback logic, and contiguous-id repair semantics.
- [x] (2026-04-23 04:29 UTC) Added wepppyo3 tests covering parity against Python legacy oracle and failure-contract checks.
- [x] (2026-04-23 04:31 UTC) Integrated WEPPpy `_build_mofe_map` to use the new Rust API via `wepppy/topo/watershed_abstraction/mofe_map.py` strict loader (no silent fallback).
- [x] (2026-04-23 04:33 UTC) Added/updated WEPPpy regression tests for legacy parity helper and Rust call-site delegation contract.
- [x] (2026-04-23 04:38 UTC) Ran targeted validation in both repos (`cargo test`, wepppyo3 pytest, and WEPPpy targeted `wctl run-pytest`).
- [x] (2026-04-23 04:43 UTC) Captured parity + benchmark artifacts (raw + summary) under `artifacts/`.
- [x] (2026-04-23 04:43 UTC) Ran WEPPpy pre-handoff sweep (`wctl run-pytest tests --maxfail=1`), observed one unrelated existing failure in `tests/nodb/test_wepp_run_service.py`.
- [x] (2026-04-23 04:43 UTC) Completed docs closure updates (`tracker.md`, `package.md`, `PROJECT_TRACKER.md`) and archived ExecPlan.

## Surprises & Discoveries

- Observation: `wepppyo3` location constraint changed during implementation (`do not use wepp_interchange`; place under watershed abstraction).
  Evidence: User instruction required moving implementation target to `wepppyo3.watershed_abstraction`, resulting in a new crate/module instead of extending `wepp_interchange`.

- Observation: Full-run MOFE map legacy benchmark is expensive; a fixed hillslope subset was required for repeatable within-session evidence.
  Evidence: One legacy pass on 200 hillslopes from `pointy-toed-fluff` took ~59-77s while Rust took ~0.27-0.42s; six alternating samples completed in-session.

- Observation: Global WEPPpy suite has an existing unrelated failure in `test_wepp_run_service.py`.
  Evidence: `wctl run-pytest tests --maxfail=1` failed at `tests/nodb/test_wepp_run_service.py::test_run_watershed_does_not_rewrite_wepp_50k_bin` with `AttributeError: module 'wepppy.wepp' has no attribute 'interchange'`.

## Decision Log

- Decision: Keep scope focused on `_build_mofe_map` and do not reopen segmentation semantics.
  Rationale: Segmentation migration already closed in `20260422_segmented_multiple_ofe_wepppyo3_pool`; this package targets a distinct runtime hotspot.
  Date/Author: 2026-04-23 / Codex.

- Decision: Preserve existing fallback/repair behavior as a contract constraint during migration.
  Rationale: Downstream landuse/soils/mod workflows depend on contiguous MOFE ids and current failure semantics.
  Date/Author: 2026-04-23 / Codex.

- Decision: Implement the new MOFE map API in `wepppyo3.watershed_abstraction` (new crate/module), not `wepp_interchange`.
  Rationale: User explicitly required the watershed abstraction module location; this keeps compute kernels colocated with watershed-domain behavior.
  Date/Author: 2026-04-23 / Codex.

- Decision: Keep a Python legacy assignment helper (`_build_mofe_map_labels_python_legacy`) in WEPPpy as a parity oracle, while production `_build_mofe_map` always calls Rust.
  Rationale: Allows deterministic parity/benchmark evidence without reintroducing a silent production fallback path.
  Date/Author: 2026-04-23 / Codex.

- Decision: Benchmark/parity evidence uses a fixed 200-hillslope subset from `/wc1/runs/po/pointy-toed-fluff` with isolated temp dirs.
  Rationale: Full-run legacy timing is too slow for alternating multi-sample in-session capture; fixed subset preserves repeatability and source-run immutability.
  Date/Author: 2026-04-23 / Codex.

## Outcomes & Retrospective

Implementation completed end-to-end for this package scope:

- Production `_build_mofe_map` now delegates MOFE label assignment to `wepppyo3.watershed_abstraction.assign_mofe_map`.
- Rust path pre-indexes raster cells by `topaz_id` once and computes hillslope labels without repeated full-raster scans.
- Legacy fallback/repair semantics (including contiguous-id guarantees and rank/segment-count behavior) are preserved and validated against a Python oracle.

Validation summary:

- wepppyo3: `cargo test -p watershed_abstraction_rust` passed (4 tests), and `pytest tests/watershed_abstraction/test_assign_mofe_map.py tests/wepp_interchange/test_segment_single_ofe_slope.py` passed.
- WEPPpy targeted tests: `wctl run-pytest tests/nodb/test_watershed_mofe_map.py tests/topo/test_watershed_abstraction_mofe_map.py` passed (`9 passed`).
- WEPPpy pre-handoff sweep: `wctl run-pytest tests --maxfail=1` reached `2051 passed` before one unrelated existing failure in `tests/nodb/test_wepp_run_service.py::test_run_watershed_does_not_rewrite_wepp_50k_bin`.

Performance/parity evidence:

- Parity subset (200 hillslopes from `pointy-toed-fluff`) mismatch count: `0`.
- Alternating benchmark (6 samples, 3 old/3 new) mean timings: old `65.949s`, new `0.282s`, delta `-99.57%`.

Residual risk:

- Global suite failure is unrelated to this package but blocks a clean all-tests pass signal in this environment.

## Context and Orientation

Current implementation lives in `wepppy/nodb/core/watershed_mixins.py`:

- `_build_mofe_map` reads `subwta` and `discha` rasters in Python.
- For each hillslope (`topaz_id`), it repeatedly computes boolean masks and `np.where` scans against full rasters.
- It computes MOFE fractions from `*.mofe.slp`, assigns ids via percentile thresholds, and falls back to nearest-discharge cell if bins are empty.
- It performs a contiguous-id repair with `_assign_mofe_ids_by_discharge_rank` when needed.

Optimization target:

- Move the per-hillslope assignment into Rust with explicit inputs (subwta raster, discha raster, per-hillslope segment fractions/counts) and return MOFE map labels.
- Reduce repeated full-raster scans by pre-indexing cell positions by `topaz_id` once, then operating on those indices only.

Key files:

- `wepppy/nodb/core/watershed_mixins.py`
- `tests/nodb/test_watershed_mofe_map.py`
- `wepppy/topo/watershed_abstraction/slope_file.py` (for MOFE fraction source expectations)
- `/home/workdir/wepppyo3` (new PyO3 API + Rust core tests)

## Plan of Work

Milestone 1: Lock Python behavior contract for MOFE-map assignment and define Rust API surface. This milestone records exact semantics for segment counts, contiguous-label guarantees, and fallback behavior.

Milestone 2: Implement Rust core assignment with topaz pre-indexing and one-pass discharge-rank labeling, expose PyO3 binding, and add focused Rust/Python tests in wepppyo3.

Milestone 3: Integrate WEPPpy `_build_mofe_map` to call the new API, keeping file I/O and `*.mofe.slp` fraction extraction behavior unchanged.

Milestone 4: Add/refresh WEPPpy regression tests, run parity and performance benchmarks, and close package documentation.

## Concrete Steps

Working directories:

- `/home/workdir/wepppy`
- `/home/workdir/wepppyo3`

1. Contract discovery and baseline capture.

    cd /home/workdir/wepppy
    rg -n "def _build_mofe_map|_assign_mofe_ids_by_discharge_rank|mofe_distance_fractions" wepppy/nodb/core/watershed_mixins.py wepppy/topo/watershed_abstraction/slope_file.py
    wctl run-pytest tests/nodb/test_watershed_mofe_map.py

2. Implement Rust/PyO3 API.

    cd /home/workdir/wepppyo3
    rg -n "#[[:space:]]*pyfunction|#[[:space:]]*pymodule|mofe|watershed" src tests

3. Integrate WEPPpy call site.

    cd /home/workdir/wepppy
    rg -n "_build_mofe_map|read_raster|write_raster" wepppy/nodb/core/watershed_mixins.py

4. Validate tests and capture artifacts.

    cd /home/workdir/wepppy
    wctl run-pytest tests/nodb/test_watershed_mofe_map.py

    Run parity/benchmark scripts and store outputs under:
    - `docs/work-packages/20260423_mofe_map_wepppyo3/artifacts/parity_*.{md,json}`
    - `docs/work-packages/20260423_mofe_map_wepppyo3/artifacts/benchmark_*.{md,json}`

## Validation and Acceptance

Acceptance is met when all conditions hold:

- WEPPpy production `_build_mofe_map` calls a wepppyo3 API for label assignment.
- Output parity with Python baseline is demonstrated for targeted fixtures/runs.
- Contiguous-id guarantees and fallback repair semantics are preserved.
- Targeted WEPPpy and wepppyo3 tests pass.
- Benchmark artifact reports per-run timings, mean/stddev, and percent delta.

## Idempotence and Recovery

- Keep changes additive while introducing the new API; preserve a deterministic baseline path during development for parity checks.
- If parity fails, keep Rust path non-default until discrepancies are resolved and documented.
- Benchmark/parity runs must use isolated temp directories and must not modify source runs.

## Artifacts and Notes

Store implementation evidence under:

- `docs/work-packages/20260423_mofe_map_wepppyo3/artifacts/benchmark_summary.md`
- `docs/work-packages/20260423_mofe_map_wepppyo3/artifacts/benchmark_raw.json`
- `docs/work-packages/20260423_mofe_map_wepppyo3/artifacts/parity_notes.md`
- `docs/work-packages/20260423_mofe_map_wepppyo3/artifacts/parity_raw.json`

## Interfaces and Dependencies

Expected end-state interface:

- A stable Python-callable `wepppyo3` function for MOFE-map assignment that accepts raster arrays and per-hillslope segmentation boundaries/counts and returns an `int32` MOFE label raster with contiguous per-hillslope ids.
- WEPPpy `_build_mofe_map` remains responsible for reading/writing raster files and `*.mofe.slp` fraction discovery, delegating only assignment computation to Rust.

Dependencies:

- Prior segmentation migration package: `docs/work-packages/20260422_segmented_multiple_ofe_wepppyo3_pool/`.
- wepppyo3 build/test toolchain in `/home/workdir/wepppyo3`.

## Revision Notes

- 2026-04-23 / Codex: Initial ExecPlan authored from user request to migrate `_build_mofe_map` to wepppyo3 with pre-index and one-pass rank assignment focus.
- 2026-04-23 / Codex: Completed implementation in `wepppyo3.watershed_abstraction`, integrated WEPPpy production path, captured parity/benchmark artifacts, and recorded validation outcomes.
- 2026-04-23 / Codex: Archived this ExecPlan to `prompts/completed/` and added closure outcome note.
