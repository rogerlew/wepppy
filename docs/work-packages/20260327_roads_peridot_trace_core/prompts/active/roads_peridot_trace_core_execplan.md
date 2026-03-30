# Roads Step-1 Flowpath Trace Core in Peridot, Surfaced Through Wepppyo3

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package, a Roads pipeline can call a Rust tracer for one low-point seed and receive deterministic routing outputs to the channel network (or explicit termination reason when no channel is reached). The same Rust implementation must be available through both `peridot` (CLI/debug path) and `wepppyo3` (`pyo3` runtime path) so Roads step-2/3 work does not need to re-implement hydrology routing. Success is visible when a known seed cell produces JSON/profile outputs through `peridot` CLI and the `wepppyo3` Python API with matching values.

## Progress

- [x] (2026-03-27 00:00Z) Authored package scaffold (`package.md`, `tracker.md`, active ExecPlan).
- [x] (2026-03-27 00:00Z) Updated root `AGENTS.md` active ExecPlan pointer and `PROJECT_TRACKER.md` entry.
- [x] (2026-03-27) Milestone 1: Implemented `peridot` trace core contract and deterministic termination semantics in `src/roads_trace/trace_downslope.rs`.
- [x] (2026-03-27) Milestone 2: Added `peridot` CLI command `trace_downslope_flowpath` with JSON output contract parity.
- [x] (2026-03-27) Milestone 3: Added `wepppyo3` `roads_flowpath_rust` `pyo3` binding crate that calls the shared `peridot` core.
- [x] (2026-03-27) Milestone 4: Added `peridot` and `wepppyo3` regression tests, including CLI-vs-`pyo3` parity coverage.
- [x] (2026-03-27) Milestone 5: Updated Roads spec trace-contract section with implemented v1 fields and termination labels.
- [x] (2026-03-27) Milestone 6: Completed code review artifact with zero unresolved medium/high findings.
- [x] (2026-03-27) Milestone 7: Completed QA review artifact with zero unresolved medium/high findings.
- [x] (2026-03-27) Milestone 8: Ran final validation gates and prepared handoff summary details.

## Surprises & Discoveries

- Observation: `peridot::watershed_abstraction::walk_flowpath` already performs D8 stepping and profile accumulation, but it asserts seed topaz consistency and stops when topaz changes.
  Evidence: `/workdir/peridot/src/watershed_abstraction/watershed_abstraction.rs` (`walk_flowpath`).

- Observation: Current Roads low-point mapping only handles channel-associated low points and marks non-channel points as unmapped.
  Evidence: `wepppy/nodb/mods/roads/monotonic_segments.py` low-point decision values include `no_channel_pixel_near_lowpoint`.

- Observation: `wepppy` already deploys tracked `peridot` binaries under `wepppy/topo/peridot/bin`.
  Evidence: tracked files include `abstract_watershed`, `wbt_abstract_watershed`, `sub_fields_abstraction`.

- Observation: `wepppyo3` already ships multiple `pyo3` extension crates with a canonical release tree under `release/linux/py312/wepppyo3/`.
  Evidence: `wepppyo3/README.md` build/copy commands and current release layout.

- Observation: `cargo test -- --nocapture` in `peridot` is not globally green due pre-existing failures in untouched legacy tests (`rasters::raster::*`, `support::support::*`).
  Evidence: failing tests from command output while touched trace-module tests pass.

## Decision Log

- Decision: Implement one shared tracing core in `peridot` and expose it through both CLI and `wepppyo3`.
  Rationale: Prevents algorithm drift and keeps tests authoritative on one code path.
  Date/Author: 2026-03-27 / Codex.

- Decision: Scope this package to step 1 substrate only; Roads behavioral integration is deferred to follow-on packages.
  Rationale: Keeps implementation and acceptance criteria bounded for this package.
  Date/Author: 2026-03-27 / User + Codex.

- Decision: Trace contract should be machine-usable (arrays + geometry + termination), not HTML/raster-only output.
  Rationale: Roads MOFE assembly needs deterministic numeric profiles and explicit termination outcomes.
  Date/Author: 2026-03-27 / User + Codex.

- Decision: Define channel-mask truth in v1 as `mask > 0` and document it in Roads spec.
  Rationale: Removes ambiguity between wrappers and keeps CLI/`pyo3` behavior deterministic for mixed raster conventions.
  Date/Author: 2026-03-27 / Codex.

## Outcomes & Retrospective

- Implemented one shared Rust tracer core in `peridot` and surfaced it through both a CLI binary and a `wepppyo3` `pyo3` module with no duplicated routing algorithm.
- Added deterministic regression coverage for all required termination modes and profile invariants in `peridot`, plus Python schema/parity tests in `wepppyo3`.
- Updated Roads specification trace-contract text to match implemented v1 output fields and termination labels.
- Completed mandatory code/QA review artifacts with no unresolved medium/high findings.
- Validation summary:
  - all targeted new/required tests passed,
  - `peridot` full-suite command still reports pre-existing unrelated failures outside touched scope.

## Context and Orientation

This package touches three repositories in one workspace.

1. `/workdir/peridot` is the Rust hydrology/topography core used by WEPPpy. It already has D8 walking logic and writes watershed abstractions.
2. `/workdir/wepppyo3` hosts Rust `pyo3` extension crates deployed as `wepppyo3.*` Python modules.
3. `/workdir/wepppy` hosts Roads NoDb logic and docs; this package updates Roads specification and package trackers there.

Current gap:

- Roads step-2+ design needs one-point downslope tracing from non-channel low points to channel.
- Existing implementation in Roads does not trace this path; it only maps low points that are near channel pixels.
- Existing `peridot` flowpath walking logic is close but not shaped as a stable point-source tracing contract.

Terms used in this plan:

- D8 flow direction: one-cell-per-step drainage direction encoded per raster cell.
- Seed point: the low-point cell selected from a road segment.
- Termination reason: explicit status describing why tracing stopped (`hit_channel`, `invalid_flow_direction`, `loop_detected`, `raster_edge`, `max_steps_exceeded`, or equivalent agreed enum labels).
- Profile arrays: ordered vectors for cumulative distance and elevation along the traced path.

## Plan of Work

Milestone 1 creates a reusable trace core in `peridot`.

- Add a new `peridot` module (for example `src/roads_trace/mod.rs` and `src/roads_trace/trace_downslope.rs`) and export it from `src/lib.rs`.
- Define explicit trace result and termination types.
- Implement one-point tracing that:
  - validates seed row/col bounds,
  - follows D8 direction cell-by-cell,
  - tracks visited cells to prevent loops,
  - accumulates geometry and profile vectors,
  - marks channel reach when channel condition is met,
  - exits with explicit termination reason on failure/non-channel completion.
- Ensure no panic-path for invalid direction/edge; return structured errors or termination states.

Recommended v1 interface in `peridot` (name can vary, semantics must match):

    pub enum TraceTerminationReason {
        HitChannel,
        InvalidFlowDirection,
        LoopDetected,
        RasterEdge,
        MaxStepsExceeded,
    }

    pub struct TraceDownslopeResult {
        pub seed_row: i32,
        pub seed_col: i32,
        pub seed_topaz_id: i32,
        pub reaches_channel: bool,
        pub channel_row: Option<i32>,
        pub channel_col: Option<i32>,
        pub channel_topaz_id: Option<i32>,
        pub termination_reason: TraceTerminationReason,
        pub rows: Vec<i32>,
        pub cols: Vec<i32>,
        pub indices: Vec<usize>,
        pub distance_m: Vec<f64>,
        pub elevation_m: Vec<f64>,
        pub segment_slope: Vec<f64>,
        pub path_length_m: f64,
        pub drop_m: f64,
        pub mean_slope: f64,
        pub max_slope: f64,
    }

    pub fn trace_downslope_flowpath(
        subwta: &Raster<i32>,
        flovec: &Raster<u8>,
        relief: &Raster<f32>,
        seed_row: usize,
        seed_col: usize,
        channel_mask: Option<&Raster<i32>>,
        max_steps: usize,
    ) -> Result<TraceDownslopeResult, TraceError>

Channel-detection rule for v1:

- channel is true if `channel_mask` exists and cell value indicates channel.
- if `channel_mask` is absent, treat `subwta` suffix `4` as channel.
- this dual rule allows immediate use in both TOPAZ and WBT run contexts.

Milestone 2 adds a thin `peridot` CLI wrapper over the shared core.

- Add `[[bin]]` entry in `/workdir/peridot/Cargo.toml` and create `src/bin/trace_downslope_flowpath.rs`.
- CLI should accept explicit raster paths and seed cell coordinates:
  - `--subwta`
  - `--flovec`
  - `--relief`
  - optional `--channel`
  - `--seed-row`
  - `--seed-col`
  - optional `--max-steps` (default required in docs)
  - optional `--out-json` (default stdout JSON)
- CLI output must serialize the same core contract fields so downstream tests can compare CLI vs `pyo3`.

Milestone 3 adds a `wepppyo3` binding crate that calls the shared `peridot` core.

- Add a new crate (recommended name `roads_flowpath_rust`) in `/workdir/wepppyo3`.
- Add crate to workspace members in `/workdir/wepppyo3/Cargo.toml`.
- Add `peridot` path dependency from the new crate.
- Export one primary Python function with row/col inputs:

    trace_downslope_flowpath(
        subwta_path: str,
        flovec_path: str,
        relief_path: str,
        seed_row: int,
        seed_col: int,
        channel_path: Optional[str] = None,
        max_steps: int = 20000,
    ) -> dict

- Return a Python dict matching v1 trace contract keys.
- Update canonical release tree with:
  - `release/linux/py312/wepppyo3/roads_flowpath/__init__.py`
  - `release/linux/py312/wepppyo3/roads_flowpath/roads_flowpath_rust.so`
- Update `wepppyo3/README.md` build-copy instructions to include the new module.

Milestone 4 adds tests and optional WEPPpy shim smoke coverage.

- In `peridot`, add synthetic-raster unit/integration tests (new test file such as `tests/roads_trace_downslope.rs`) covering:
  - channel hit,
  - invalid flow direction,
  - loop detection,
  - raster edge termination,
  - max-step termination,
  - deterministic `distance_m` and `elevation_m` length/value invariants.
- In `wepppyo3`, add tests under `tests/roads_flowpath/` that:
  - call Python binding,
  - verify key schema and deterministic values on synthetic rasters,
  - compare selected outputs to CLI/core expectations.
- If a WEPPpy wrapper utility is introduced, add focused test(s) under `tests/topo/peridot/` and avoid changing Roads behavior in this package.

Milestone 5 updates docs/spec.

- Update `wepppy/nodb/mods/roads/specification.md` future architecture section to record implemented v1 trace contract fields and termination labels.
- Keep package docs and tracker current as milestones close.

Milestones 6 and 7 are mandatory review gates.

- Milestone 6 (Code Review):
  - run independent reviewer pass on changed files,
  - record findings in `docs/work-packages/20260327_roads_peridot_trace_core/artifacts/20260327_code_review.md`,
  - resolve all medium/high findings before proceeding.
- Milestone 7 (QA Review):
  - run independent QA review on tests/contracts/build packaging,
  - record findings in `docs/work-packages/20260327_roads_peridot_trace_core/artifacts/20260327_qa_review.md`,
  - resolve all medium/high findings before final closure.

Milestone 8 runs final gates and handoff.

## Concrete Steps

Use exact working directories shown.

1. Implement peridot core + CLI:

    cd /workdir/peridot
    rg -n "walk_flowpath|Flowpath|PATHS" src/watershed_abstraction
    cargo fmt
    cargo test --test edge_flowpaths -- --nocapture
    cargo test --test roads_trace_downslope -- --nocapture
    cargo test -- --nocapture
    cargo run --bin trace_downslope_flowpath -- --help

2. Implement wepppyo3 binding and release module:

    cd /workdir/wepppyo3
    cargo fmt
    cargo build --release -p roads_flowpath_rust
    mkdir -p release/linux/py312/wepppyo3/roads_flowpath
    cp target/release/libroads_flowpath_rust.so \
      release/linux/py312/wepppyo3/roads_flowpath/roads_flowpath_rust.so
    pytest tests/roads_flowpath -q

3. Optional WEPPpy shim smoke tests and docs:

    cd /workdir/wepppy
    wctl run-pytest tests/topo -k peridot --maxfail=1
    wctl doc-lint --path wepppy/nodb/mods/roads/specification.md
    wctl doc-lint --path docs/work-packages/20260327_roads_peridot_trace_core/package.md
    wctl doc-lint --path docs/work-packages/20260327_roads_peridot_trace_core/tracker.md
    wctl doc-lint --path docs/work-packages/20260327_roads_peridot_trace_core/prompts/active/roads_peridot_trace_core_execplan.md

4. Perform mandatory review gates:

    - Code review artifact with finding severities/disposition.
    - QA review artifact with test matrix and residual-risk callouts.

5. Final cross-check:

    - confirm no unresolved medium/high findings in either artifact,
    - update `Progress`, `Decision Log`, and `Outcomes & Retrospective`,
    - update package tracker timeline/verification sections.

## Validation and Acceptance

Acceptance requires all items below.

- Peridot:
  - core trace API exists and is callable from tests,
  - CLI trace command exists and emits JSON with required keys,
  - tests prove all termination behaviors and profile invariants.
- Wepppyo3:
  - Python-callable function exists and returns contract-aligned dict,
  - binding uses shared `peridot` core (no duplicated routing algorithm),
  - test(s) validate deterministic outputs on synthetic rasters.
- Docs:
  - Roads specification future architecture section reflects implemented v1 contract.
  - package tracker and ExecPlan living sections are current.
- Reviews:
  - code review artifact complete with zero unresolved medium/high findings,
  - QA review artifact complete with zero unresolved medium/high findings.

## Idempotence and Recovery

- Peridot and wepppyo3 build/test steps are idempotent and safe to rerun.
- If `wepppyo3` release copy is stale, regenerate `.so` from the latest `cargo build --release` and recopy to the canonical release path.
- If CLI contract changes during implementation, update both `pyo3` serialization and contract tests in the same commit before proceeding.
- Do not introduce silent fallback to Python routing; failures must be explicit to preserve traceability.

## Artifacts and Notes

Required artifacts:

- `docs/work-packages/20260327_roads_peridot_trace_core/artifacts/20260327_code_review.md`
- `docs/work-packages/20260327_roads_peridot_trace_core/artifacts/20260327_qa_review.md`

Recommended artifact snippets:

- sample CLI JSON output for a passing channel-hit case,
- sample CLI JSON output for one non-channel termination case,
- brief parity check notes comparing CLI and `pyo3` output for the same seed.

## Interfaces and Dependencies

End-state interface requirements:

- `peridot` library exports a stable trace API with explicit termination enum and profile arrays.
- `peridot` CLI `trace_downslope_flowpath` calls only the library trace API.
- `wepppyo3` module exports `trace_downslope_flowpath(...)` and maps directly to peridot-core result fields.
- No pure-Python implementation of downslope trace logic is introduced.

Cross-repo dependency expectations:

- `wepppyo3` can depend on `/workdir/peridot` path dependency for development in this workspace.
- Packaging instructions in `wepppyo3/README.md` must include the new module copy step.
- If WEPPpy runtime uses new API in this package, any new import surface must keep tests/stubs in sync.

---

Revision note (2026-03-27 00:00Z): Initial ExecPlan authored for Roads step-1 flowpath trace substrate with explicit peridot core, CLI, `pyo3` binding, and mandatory code/QA review gates.
