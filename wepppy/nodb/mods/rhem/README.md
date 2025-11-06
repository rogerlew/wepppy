# RHEM NoDb Controller
> Prepares and runs rangeland hillslope simulations, now with parallel prep and Rust-backed storm generation.

## Overview
The `Rhem` NoDb controller orchestrates Rangeland Hydrology and Erosion Model (RHEM) runs for each TOPAZ subcatchment. It assembles slope/cover/soil inputs, writes model parameter and storm files, executes the Fortran solver in parallel, and posts results for downstream reporting (for example `RhemPost` summaries and UI panels). The controller is included when a project’s mods list contains `"rhem"`.

Key responsibilities:
- Manage `rhem/` working directories (`runs`, `output`) and reset them safely.
- Prepare hillslope runs by combining watershed slopes, soils, and rangeland cover attributes.
- Generate RHEM parameter (`*.par`), storm (`*.stm`), and run (`*.run`) files and enqueue execution jobs.
- Emit job status/logging through the shared `controlBase` interface so front-end controllers and WebSocket clients stay in sync.
- Defer post-processing to `RhemPost` once hillslope jobs finish.

## Recent Changes (November 2025)
- **Parallel prep & telemetry.** `prep_hillslopes` now uses a `ThreadPoolExecutor` so storm/parameter generation scales across CPU cores while streaming progress logs (`(completed/total)`).
- **Rust storm files.** Storm creation is delegated to `wepppyo3.climate.make_rhem_storm_file`, the new PyO3 helper that parses `.cli` inputs in Rust. This dropped per-hillslope prep time from ~100 s to roughly 0.25 s.
- **Python fallback.** If the Rust extension is unavailable, the controller falls back to the legacy `ClimateFile.make_storm_file` implementation to keep existing environments working.
- **WEPP decoupling.** The unused `run_wepp_hillslopes` path has been removed; RHEM no longer attempts to hand hillslope runs to the WEPP controller automatically.
- **UI alignment.**
  - The RHEM run page hides Landuse/WEPP panels when only RHEM is active to avoid bootstrap errors.
  - Summary reports now use modern Pure components (`wc-summary-pane`, `wc-table--dense`) for consistent styling.
- **Preflight updates.** `preflight2` marks `rhem` complete whenever `timestamps:run_rhem` exists, and `rangeland_cover` is flagged purely by its own timestamp. Soil completion now accepts either Landuse or Rangeland Cover runs as prerequisites.

## Developer Notes
- **Concurrency safety.** Prep and run methods continue to rely on NoDb locks (`with self.locked(): …`) when mutating controller state. Threaded prep only covers file creation; shared data structures and logging remain synchronized.
- **Unitizer compatibility.** Report templates pull values through `Unitizer` helpers. When editing report markup keep both default units and display unit slots intact (`unitizer()` plus `unitizer_units()`).
- **Extending prep.** Additional metadata (for example new cover fractions) should be added inside `prepare_single` in `prep_hillslopes`. Remember to time/trace new steps so operators see progress in UI logs.
- **Testing.** There are no dedicated automated tests yet. When refactoring, build a temporary run via `run_rhem_rq` and inspect:
  - `${run}/rhem/runs/*.par|*.stm|*.run`
  - `${run}/rhem/output/*.sum`
  - `/report/rhem/run_summary/`
  - Preflight payload from `preflight2`.

## Further Reading
- `wepppy/nodb/mods/rhem/rhem.py` – controller implementation.
- `wepppy/nodb/mods/rhem/rhempost.py` – post-processing helper invoked after successful runs.
- `wepppy/weppcloud/templates/controls/rhem_pure.htm` – run page panel that surfaces job controls.
- `services/preflight2/internal/checklist/checklist.go` – logic that sets the dashboard checklist flags.
- `docs/dev-notes/controlBase-and-command_btn_id-Implementation.md` – shared control lifecycle patterns used by the RHEM front-end controller.
