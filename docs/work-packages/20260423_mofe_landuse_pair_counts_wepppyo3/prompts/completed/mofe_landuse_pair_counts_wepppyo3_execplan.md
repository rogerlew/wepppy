# Multi-OFE Landuse Pair-Count Optimization via wepppyo3 Raster Characteristics

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Outcome Note

Completed on 2026-04-23 (UTC). The Rust pair-count API, WEPPpy integration, regression tests, and required benchmark/parity artifacts were delivered and validated; package lifecycle docs were closed.

## Purpose / Big Picture

After this change, WEPPpy multi-OFE landuse area coverage no longer performs repeated `np.where` scans over entire rasters for every `(topaz_id, mofe_id)` pair. Instead, WEPPpy calls a Rust/PyO3 API in `wepppyo3.raster_characteristics` that computes pair counts in one pass, preserving output semantics while substantially reducing runtime.

## Progress

- [x] (2026-04-23 16:04 UTC) Work package scaffold created and benchmark targets documented.
- [x] (2026-04-23 17:22 UTC) Implemented `wepppyo3.raster_characteristics.count_intersecting_raster_key_pairs` with explicit read/shape failure contracts.
- [x] (2026-04-23 17:22 UTC) Exported API in canonical release package (`release/linux/py312`) and added wepppyo3 Rust + Python tests.
- [x] (2026-04-23 17:22 UTC) Integrated WEPPpy `Landuse.build_managements()` multi-OFE area path to call Rust pair-count API.
- [x] (2026-04-23 17:22 UTC) Added WEPPpy regression coverage for Rust call usage and explicit failure propagation.
- [x] (2026-04-23 17:22 UTC) Ran old/new benchmark + parity comparisons on required five-run matrix and published artifacts.
- [x] (2026-04-23 17:22 UTC) Updated package docs (`Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`, `tracker.md`, `PROJECT_TRACKER.md`) for closure.

## Surprises & Discoveries

- Observation: `/wc1/runs/ob/objectionable-sublimate` does not contain `watershed/mofe.tif` and persists `domlc_mofe_d=None`.
  Evidence: benchmark harness discovery while collecting required run inputs.
- Observation: `/wc1/runs/co/cochlear-beriberi` stores subcatchments at `dem/topaz/SUBWTA.ARC` rather than `dem/wbt/subwta.tif`.
  Evidence: run-root scan during benchmark setup.

## Decision Log

- Decision: Place pair-count API in existing `wepppyo3.raster_characteristics` module.
  Rationale: Keeps raster summarization kernels in one module and minimizes integration complexity.
  Date/Author: 2026-04-23 / Codex.
- Decision: Return deterministic nested key-count maps from Rust via `BTreeMap<String, BTreeMap<String, usize>>`.
  Rationale: Stable output ordering simplifies parity artifacts and regression assertions.
  Date/Author: 2026-04-23 / Codex.
- Decision: For required non-MOFE benchmark run (`objectionable-sublimate`), synthesize an isolated temp `mofe.tif` (all ones) and derive one-segment pair map from `domlc_d`.
  Rationale: Keeps the benchmark matrix complete without mutating source runs and preserves explicit documentation of non-MOFE input constraints.
  Date/Author: 2026-04-23 / Codex.

## Outcomes & Retrospective

Delivered end-to-end optimization lane #1.

- Added production Rust/PyO3 API `count_intersecting_raster_key_pairs` with explicit `PyIOError` (raster read failure) and `PyValueError` (shape/data mismatch) contracts.
- Updated canonical release export (`release/linux/py312`) and rebuilt `raster_characteristics_rust.so`.
- Replaced WEPPpy multi-OFE pairwise `np.where` scans in `Landuse.build_managements()` with Rust pair-count aggregation while preserving `area`/`pct_coverage` semantics.
- Added targeted tests in both repos:
  - wepppyo3 Rust unit tests + Python API/failure tests.
  - WEPPpy landuse regression tests for Rust-path coverage and failure propagation.
- Produced required benchmark/parity artifacts in package `artifacts/` across all required runs with isolated temp copies.

## Context and Orientation

Current multi-OFE area aggregation in WEPPpy is expensive because it repeats full-raster scans for each pair:
- `wepppy/nodb/core/landuse.py` inside `build_managements()` computes area with `len(np.where((subwta == int(topaz_id)) & (mofe_map == int(_id)))[0])` for each pair.
- This path scales with `#pairs * #cells` and is a known hotspot in multi-OFE runs.

Existing Rust capabilities already include mode/median summarization by one and two raster keys:
- `/home/workdir/wepppyo3/raster_characteristics/src/lib.rs`
- Python exports under `/home/workdir/wepppyo3/release/linux/py312/wepppyo3/raster_characteristics/`

Target behavior:
- Add a count-focused API returning counts by intersecting keys (`topaz_id`, `mofe_id`) with explicit key filtering semantics.
- Keep WEPPpy output contracts unchanged (`managements[k].area`, `pct_coverage`, downstream parquet/report behavior).

## Plan of Work

Milestone 1: Define and implement Rust API in `wepppyo3.raster_characteristics`.
- Add a new PyO3 function that computes counts for intersecting keys in one raster pass.
- Prefer deterministic return order and explicit string/int conversion at one boundary only.
- Ensure no silent failure: shape mismatch, read errors, invalid inputs should raise explicit errors.

Milestone 2: Add/extend tests in wepppyo3.
- Unit tests for nominal counts, ignored keys/channels, and failure contracts.
- Python tests for API contract and deterministic behavior.

Milestone 3: Integrate WEPPpy multi-OFE area path.
- Replace repeated `np.where` loop in `Landuse.build_managements()` with a one-pass count map from Rust API.
- Preserve area conversion (`cell2 / 10000`) and existing type normalization semantics.
- Keep behavior explicit: no silent fallback to legacy slow path unless intentionally guarded and documented.

Milestone 4: Validate + benchmark + document closure.
- Run targeted tests in both repos.
- Run old/new comparison benchmarks on required run set using isolated temp dirs and no source run mutation.
- Record per-run timings, mean/stddev, percent delta, plus parity checks.
- Update package docs and close package.

## Concrete Steps

Working directories:
- WEPPpy: `/home/workdir/wepppy`
- wepppyo3: `/home/workdir/wepppyo3`

1. Implement Rust API and tests in wepppyo3.

    cd /home/workdir/wepppyo3
    rg -n "identify_mode_single_raster_key|identify_mode_intersecting_raster_keys" raster_characteristics/src/lib.rs

    Add pair-count function and export; then run:

    cargo test -p raster_characteristics
    pytest tests/raster_characteristics

2. Integrate WEPPpy call site.

    cd /home/workdir/wepppy
    rg -n "build_managements\(|np.where\(\(subwta == int\(topaz_id\)\)" wepppy/nodb/core/landuse.py

    Update multi-OFE area loop to consume Rust count output.

3. Run targeted WEPPpy tests.

    cd /home/workdir/wepppy
    wctl run-pytest tests/nodb/test_landuse_coverage_area_source.py tests/nodb/test_landuse_mofe_disturbed_scalar_lookup.py

4. Benchmark/parity run matrix (local roots + URL references).

    URL: https://wc.bearhive.duckdns.org/weppcloud/runs/moth-eaten-blackhead/disturbed9002-wbt-mofe/
    Local root: /wc1/runs/mo/moth-eaten-blackhead

    URL: https://wc.bearhive.duckdns.org/weppcloud/runs/objectionable-sublimate/disturbed9002_wbt/
    Local root: /wc1/runs/ob/objectionable-sublimate

    URL: https://wc.bearhive.duckdns.org/weppcloud/runs/cochlear-beriberi/disturbed9002-mofe/
    Local root: /wc1/runs/co/cochlear-beriberi

    URL: https://wc.bearhive.duckdns.org/weppcloud/runs/ordained-incentive/disturbed9002-wbt-mofe/
    Local root: /wc1/runs/or/ordained-incentive

    URL: https://wc.bearhive.duckdns.org/weppcloud/runs/uninsured-deformation/disturbed9002-wbt-mofe/
    Local root: /wc1/runs/un/uninsured-deformation

    For each run, execute old/new timing in isolated temp dirs and write artifacts under:

    - `docs/work-packages/20260423_mofe_landuse_pair_counts_wepppyo3/artifacts/benchmark_raw.json`
    - `docs/work-packages/20260423_mofe_landuse_pair_counts_wepppyo3/artifacts/benchmark_summary.md`
    - `docs/work-packages/20260423_mofe_landuse_pair_counts_wepppyo3/artifacts/parity_raw.json`
    - `docs/work-packages/20260423_mofe_landuse_pair_counts_wepppyo3/artifacts/parity_notes.md`

5. Close package and archive prompt.

    - Update `package.md`, `tracker.md`, and `PROJECT_TRACKER.md`.
    - Move this ExecPlan from `prompts/active/` to `prompts/completed/` with an outcome note.

## Validation and Acceptance

Acceptance is met when all conditions hold:
- WEPPpy multi-OFE area computation no longer relies on repeated pairwise full-raster `np.where` scans.
- Output parity is demonstrated against the baseline path for tested runs.
- wepppyo3 + WEPPpy targeted tests pass.
- Benchmark artifacts contain per-run old/new timings plus aggregate mean/stddev/percent delta.
- Failure contracts remain explicit (no swallowed mismatches/errors).

## Idempotence and Recovery

- Benchmark/parity steps must run against copied/intermediate artifacts only; source run directories under `/wc1/runs/*` must not be mutated.
- If benchmark collection is interrupted, rerun only missing run entries and append/update artifact JSON with deterministic run identifiers.
- If parity fails, keep integration change behind a documented branch point until mismatch is resolved with tests.

## Artifacts and Notes

Required artifacts:
- `artifacts/benchmark_raw.json`
- `artifacts/benchmark_summary.md`
- `artifacts/parity_raw.json`
- `artifacts/parity_notes.md`

Optional support notes can be added under `notes/`.

## Interfaces and Dependencies

Expected wepppyo3 interface:
- New function in `wepppyo3.raster_characteristics` that returns intersecting key-pair counts suitable for multi-OFE area aggregation.
- Inputs and outputs must be documented in tests and reflected in Python wrapper exports.

Expected WEPPpy integration surface:
- `wepppy/nodb/core/landuse.py::Landuse.build_managements` (multi-OFE branch only).
- Preserve existing downstream state fields (`managements`, `domlc_mofe_d`, parquet/report behavior).

Dependencies:
- Existing wepppyo3 raster-characteristics infrastructure and release packaging.
- Existing MOFE map generation pipeline from closed package `20260423_mofe_map_wepppyo3`.

## Revision Notes

- 2026-04-23 / Codex: Initial ExecPlan authored from user request to start optimization lane #1 (Rust pair-count API in raster_characteristics + WEPPpy integration + run-matrix benchmarks).
- 2026-04-23 / Codex: Implemented API + integration + tests + benchmark/parity artifacts and updated living sections for closure.
