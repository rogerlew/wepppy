# RUSLE LS Tooling: `RusleLsFactor` in `weppcloud-wbt`

**Status**: Closed (2026-03-20)

## Closure Summary
- Implemented and registered `RusleLsFactor` in `/workdir/weppcloud-wbt`.
- Added wrapper bindings in both Python wrapper files.
- Added WEPPpy LS integration entrypoint and tests under `wepppy/nodb/mods/rusle` and `tests/nodb/mods/`.
- Closed validation gates:
  - `cargo check -p whitebox_tools`
  - `cargo build -p whitebox_tools`
  - `cargo test -p whitebox_tools rusle_ls_factor -- --nocapture`
  - `python -m py_compile whitebox_tools.py WBT/whitebox_tools.py`
  - `wctl run-pytest tests/nodb/mods/test_rusle_ls_integration.py --maxfail=1`
  - `wctl run-pytest tests --maxfail=1`
- Acceptance validation passed across 5 real `/wc1/runs/*` DEMs with breached-preprocess workflow:
  - all 5 LS output rasters emitted and valid
  - `LS = L * S` max absolute error `< 2e-5`
  - effective slope length cap honored (`<= 304.8 m`)
  - expected rejection of unconditioned pit-containing raw DEMs
- Closed plan and tracker artifacts:
  - `prompts/completed/rusle_ls_factor_execplan.md`
  - `tracker.md` (this package)

## Follow-Up
- Add fixture-style scientific-parity tests for LS raster outputs/mask-routing scenarios in `weppcloud-wbt`.
- Add representative-AOI benchmarking for diagnostic-output overhead and publish runtime notes.

## Problem Statement
`wepppy` currently has a locked scientific direction for RUSLE `LS`, but no purpose-built WhiteboxTools implementation. The existing `SedimentTransportIndex` tool is intentionally not canonical RUSLE `LS` because it is a unit-stream-power surrogate with different assumptions and parameterization.

This package defines the end-to-end implementation scope for a new `RusleLsFactor` tool in `/workdir/weppcloud-wbt`, plus `wepppy` integration and validation requirements so the shipped result is auditable, scientifically bounded, and operationally stable.

## Goals
- Implement a new WBT tool named `RusleLsFactor` using the locked v1 equations:
  - `L`: Desmet and Govers (1996) raster method with aspect-dependent contour-width correction.
  - `S`: McCool/RUSLE piecewise slope-steepness equations.
- Ship with `DInf` default routing, with `FD8` (sensitivity) and `D8` (comparison) as optional non-default modes.
- Enforce explicit slope-length termination behavior at channels and stop masks (`blocking_mask` and non-hillslope masks passed from `wepppy`).
- Produce canonical and diagnostic outputs (`LS`, `L`, `S`, `SCA`, effective slope length) with explicit metadata.
- Integrate the tool into `wepppy` RUSLE orchestration and `rusle/manifest.json` provenance.
- Provide regression and scientific-validation evidence that the implementation matches the locked spec assumptions.

## Non-Goals
- Reusing or renaming `SedimentTransportIndex` as canonical RUSLE `LS`.
- Implementing alternative `LS` science in v1 (e.g., Nearing continuous `S` branch as default).
- Treating disturbance as a direct `LS` input.
- Adding hidden DEM fill/breach fallback inside `RusleLsFactor`.
- Building full `R`, `K`, `C`, `P` production logic in this package unless required to wire and validate `LS` end-to-end.

## Scientific Basis
- **Desmet and Govers (1996) raster `L` path** remains canonical for gridded `LS`.
- **McCool (1987, 1989) RUSLE `S` and `m` relations** remain canonical for v1.
- **Tarboton (1997) D-infinity routing** provides the default specific-catchment-area basis.
- **Panagos et al. (2015)** is accepted precedent for Desmet-Govers + multiple-flow implementation at scale.
- **USDA-NRCS RUSLE2 Handbook** is accepted precedent for enforcing a default slope-length cap basis (`1000 ft`, `304.8 m`) in this implementation.
- **GRASS `r.watershed`** is precedent for `blocking`/`max_slope_length` controls and MFD defaults, but not for canonical v1 equations.
- **SAGA LS-Factor (field based)** is precedent for exposing Desmet-Govers as a distinct method and publishing diagnostic outputs.

### Locked vs Implementation Choice
Locked in spec:
- Equation family (`Desmet-Govers L`, `McCool S`).
- Default routing (`DInf`).
- Disturbance not used as `LS` input.
- `max_slope_length_m = 304.8` default, with override allowed only as explicit sensitivity control and documented rationale.
- DEM input is assumed hydrologically sound; tool must fail fast on likely interior no-flow artifacts.
- Stop-mask routing behavior is terminal sink with no renormalization of terminated multi-flow fractions.

Resolved by this package:
- Tool API shape and output contract.
- Metadata contract for reproducibility and audit.
- Validation protocol and acceptance thresholds.

## Implementation Plan
1. Finalize LS contract in `wepppy` spec with minimal wording changes only where ambiguity remains (mask semantics, diagnostics, applicability notes).
2. Implement `RusleLsFactor` as a new Rust tool in `weppcloud-wbt` terrain-analysis toolbox (not a modification of `SedimentTransportIndex`).
3. Register the tool in WBT module exports/tool manager and add Python wrapper methods in both wrapper files.
4. Add fixture-driven and synthetic-grid tests for equations, routing modes, stop-mask behavior, and optional `max_slope_length_m`.
5. Wire `wepppy` RUSLE orchestration to call `RusleLsFactor`, consume diagnostics, and persist manifest provenance.
6. Validate against known precedents and run-level acceptance checks; document limitations and residual risks.

## Milestones
1. **Contract Freeze (Spec + API)**
- Finalize CLI argument contract, output set, metadata keys, and failure behavior.
- Confirm that the spec explicitly distinguishes canonical science defaults vs operational controls.

2. **WBT Core Tool Implementation**
- Add `whitebox-tools-app/src/tools/terrain_analysis/rusle_ls_factor.rs`.
- Implement equation path, routing selector, stop-mask semantics, and optional max slope length cap.
- Add metadata entries to each output raster.

3. **Registration and Bindings**
- Register tool in:
  - `whitebox-tools-app/src/tools/terrain_analysis/mod.rs`
  - `whitebox-tools-app/src/tools/mod.rs`
- Add wrappers in:
  - `whitebox_tools.py`
  - `WBT/whitebox_tools.py`

4. **Validation and Regression Coverage**
- Add Rust unit tests in the tool module.
- Add fixture-based smoke tests with known outputs and metadata assertions.
- Validate parity/behavior against SAGA/GRASS expectations where comparable.

5. **`wepppy` Integration**
- Add/extend `wepppy` RUSLE controller wiring to invoke `RusleLsFactor` and stage required masks.
- Persist `rusle/manifest.json` fields for routing mode, stop-mask usage, and cap usage.
- Add integration tests for output existence, metadata propagation, and config controls.

## Validation Plan
- **Equation tests**: synthetic rasters validating `L`, `S`, `LS` values against known calculations.
- **Routing tests**: compare `DInf` default behavior vs `FD8`/`D8` optional modes on the same DEM.
- **Mask termination tests**:
  - Channels terminate slope-length growth.
  - Combined stop masks terminate growth and prevent upslope carry-through.
- **Operational-control tests**: `max_slope_length_m` only affects runs where explicitly set.
- **No hidden conditioning test**: unconditioned DEM inputs fail with explicit actionable error.
- **Integration tests** (`wepppy`): required rasters emitted and manifest metadata complete.
- **Toolchain gates** (`weppcloud-wbt`):
  - `cargo check -p whitebox_tools`
  - `cargo test -p whitebox_tools`
  - `python -m py_compile whitebox_tools.py WBT/whitebox_tools.py`
- **Repo gates** (`wepppy`):
  - `wctl run-pytest tests/<rusle paths>`
  - `wctl run-pytest tests --maxfail=1` before closure.

## Risks and Assumptions
- **Applicability-domain risk**: fixed 304.8 m cap can under-represent long uninterrupted flow paths in some landscapes; override path must remain available for sensitivity runs and clearly manifested.
- **Mask semantics risk**: ambiguous handling at barriers can materially change `LS`; semantics must be explicit and test-covered.
- **Routing comparability risk**: `FD8`/`D8` are for sensitivity/comparison only and must never silently replace default `DInf`.
- **DEM quality assumption**: tool assumes hydrologically conditioned DEM or equivalent precomputed `SCA`/slope inputs.
- **Performance risk**: diagnostic output family increases I/O; benchmark and document runtime overhead on representative AOIs.

## Expected File and Module Touch Points
`/workdir/weppcloud-wbt`
- `whitebox-tools-app/src/tools/terrain_analysis/rusle_ls_factor.rs` (new)
- `whitebox-tools-app/src/tools/terrain_analysis/mod.rs`
- `whitebox-tools-app/src/tools/mod.rs`
- `whitebox_tools.py`
- `WBT/whitebox_tools.py`
- `test_fixtures/` (new `rusle_ls_*` fixture set)
- `README.md` (fork-specific feature inventory)

`/workdir/wepppy`
- `wepppy/nodb/mods/rusle/specification.md` (targeted tightening only)
- `wepppy/nodb/mods/rusle/` (controller and factor orchestration files)
- `wepppy/nodb/configs/` (rusle-enabled config path)
- `tests/nodb/mods/` (new RUSLE LS integration/contract tests)
- `docs/work-packages/20260320_rusle_ls_factor_wbt/*` (this package)

## Open Questions
- None at package-authoring time. Initial implementation should treat `blocking_mask` as optional explicit input from `wepppy`; no hidden auto-derived barrier mask inside `RusleLsFactor`.

## References
- `wepppy/nodb/mods/rusle/specification.md`
- `weppcloud-wbt/whitebox-tools-app/src/tools/terrain_analysis/sediment_transport_index.rs`
- `weppcloud-wbt/whitebox-tools-app/src/tools/hydro_analysis/dinf_flow_accum.rs`
- `https://www.mdpi.com/2076-3263/5/2/117`
- `https://grass.osgeo.org/grass-stable/manuals/r.watershed.html`
- `https://saga-gis.sourceforge.io/saga_tool_doc/9.9.2/ta_hydrology_25.html`
- `https://jblindsay.github.io/ghrg/Whitebox/Help/SedimentTransportIndex.html`
- `https://jblindsay.github.io/ghrg/Whitebox/Help/FlowAccumDinf.html`
- `https://www.nrcs.usda.gov/sites/default/files/2022-10/RUSLE2%20Handbook_0.pdf`
