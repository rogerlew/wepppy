# Execute: Landuse Multi-OFE Build Optimization

Execute the active work package end-to-end:

- Package: `/home/workdir/wepppy/docs/work-packages/20260423_landuse_multi_ofe_build_optimization/`
- Active ExecPlan: `/home/workdir/wepppy/docs/work-packages/20260423_landuse_multi_ofe_build_optimization/prompts/active/landuse_multi_ofe_build_optimization_execplan.md`

Required scope:
1. Optimize repeated management lookup in SBS burn-remap loop:
   - `wepppy/nodb/core/landuse.py` SBS remap path
   - avoid per-pair repeated `get_management_summary(...)` when reusable summary already exists
2. Optimize duplicate heavy passes in `Landuse.build()` for multi-OFE:
   - remove or merge duplicate `build_managements()` call
   - preserve output parity and trigger/event semantics
3. Ensure no unnecessary MOFE raster/pair-count work in first pass when `domlc_mofe_d` is not yet set.
4. Reduce logging overhead for large watersheds:
   - move large dict dumps/per-hillslope nonessential info logs to debug/compact summaries
   - keep warning/error diagnostics intact

Execution constraints:
- Preserve explicit failure contracts; do not add silent fallback wrappers.
- Apply smallest safe changes first, then the duplicate-pass collapse.
- Add/extend targeted tests for:
  - SBS remap parity
  - build-pass/event contract preservation
  - first-pass no-op guard behavior
  - logging behavior where practical
- Run benchmark/parity comparisons on isolated temp dirs (no source run mutation).

Artifacts to produce under package `artifacts/`:
- `benchmark_raw.json`
- `benchmark_summary.md`
- `parity_raw.json`
- `parity_notes.md`

Package-doc updates required:
- Update active ExecPlan living sections (`Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`).
- Update `tracker.md` with UTC timestamps.
- On successful completion:
  - update `package.md` closure notes
  - move active ExecPlan to `prompts/completed/` with outcome note
  - update `PROJECT_TRACKER.md` lifecycle/status entries

Validation expectations:
- Targeted pytest suites for touched landuse modules pass.
- Benchmark summary includes per-run timings, mean/stddev, and percent delta.
- Parity artifacts confirm no output drift for required benchmark runs.

Finish with a concise closure summary:
- changed files
- behavior delta
- tests run/results
- benchmark results
- residual risks/follow-ups
