# Tenerife 2026 Data Ingestion

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

This package is complete. Tenerife now uses reviewed 25 m and 5 m configs with explicit WBT delineation defaults, climate station search resolves Jonay's 2026 station parameter files through a dedicated Tenerife catalog, and the Tenerife soil runtime surface is explicit: 5 m and 25 m are supported, `tf_soil_10.tif` is reference-only, `20.sol` and `21.sol` are required shims, and the old 250 m Tenerife branch is retired. Observed Tenerife `.cli` ingestion remains out of scope.

## Progress

- [x] (2026-03-12 19:20Z) Reviewed root guidance, NoDb guidance, work-package conventions, and the ExecPlan template.
- [x] (2026-03-12 19:20Z) Audited Tenerife source bundle contents under `/workdir/tenerife-2026/`.
- [x] (2026-03-12 19:20Z) Audited current Tenerife repo assets under `wepppy/nodb/configs/`, `wepppy/climates/cligen/`, and `wepppy/locales/tenerife/soils/`.
- [x] (2026-03-12 19:20Z) Confirmed Tenerife 5 m, 10 m, and 25 m soil rasters and the 43 source `.sol` files already match the 2026 source bundle byte-for-byte.
- [x] (2026-03-12 19:20Z) Confirmed Jonay's 62 Tenerife `Estacion_*` `.par` files were not wired into the active climate catalog path used by Tenerife configs.
- [x] (2026-03-12 19:20Z) Created work-package scaffolding and recorded the initial findings in `package.md` and `tracker.md`.
- [x] (2026-03-12 20:10Z) Added the dedicated Tenerife climate catalog (`tenerife_stations.db`, `tenerife_stations.csv`, `tenerife_par_files/`) and the `CligenStationsManager` selector branch.
- [x] (2026-03-12 20:15Z) Switched the active Tenerife configs to `cligen_db = "tenerife_stations.db"` and explicit WBT delineation defaults.
- [x] (2026-03-12 20:35Z) Retired the Tenerife 250 m soil/config branch and template-generation artifacts while keeping `tf_soil_10.tif` as reference-only inventory.
- [x] (2026-03-12 20:50Z) Added Tenerife-focused tests for climate catalog loading, config wiring, and supported soil raster coverage.
- [x] (2026-03-12 22:35Z) Verified live `wmesque2` retrieval for `tenerife/136_MDT25_TF` and `tenerife/MDT05_Tenerife` with direct HTTP probes against a Tenerife-centered bbox.
- [x] (2026-03-12 22:45Z) Closed the package docs and archived this ExecPlan.

## Surprises & Discoveries

- Observation: The new Tenerife soil rasters and 43 source `.sol` files were already in the repo and matched the 2026 source bundle exactly.
  Evidence: Hash comparison on 2026-03-12 showed `tf_soil_5.tif`, `tf_soil_10.tif`, `tf_soil_25.tif`, and all 43 shared `.sol` files are byte-identical between `/workdir/tenerife-2026/` and `wepppy/locales/tenerife/soils/`.

- Observation: Active Tenerife soil runtime still depends on `20.sol` and `21.sol`.
  Evidence: Raster inspection and the Tenerife soil test both showed `20` and `21` present in `tf_soil_5.tif` and `tf_soil_25.tif`, so removing those `.sol` files would break current runs.

- Observation: Direct Python import of `wepppy.all_your_base.geo` outside the usual runtime environment fails on missing `utm`, so the cleanest DEM verification path in this session was a direct `wmesque2` HTTP probe rather than the local helper wrapper.
  Evidence: A direct import-and-call attempt raised `ModuleNotFoundError: No module named 'utm'`, while raw HTTP requests to `https://wepp.cloud/webservices/wmesque2/retrieve/tenerife/...` returned HTTP 200 for both active Tenerife DEM dataset keys.

- Observation: By closeout time, the legacy Tenerife 250 m soil/config branch and template-era artifacts were already deleted from the worktree; the main remaining gap was documentation alignment.
  Evidence: `git status --short wepppy/locales/tenerife/soils wepppy/nodb/configs/legacy/tenerife-disturbed.toml` showed only deletions for the 250 m raster/config artifacts plus a new Tenerife soils README.

## Decision Log

- Decision: Keep observed Tenerife `.cli` ingestion out of this package.
  Rationale: The user explicitly scoped that work out and said those files can stay user-defined.
  Date/Author: 2026-03-12 / Codex.

- Decision: Use a dedicated Tenerife climate catalog instead of augmenting the shared GHCN path.
  Rationale: Jonay's Tenerife stations are not GHCN stations, and the repo already supports a clean catalog-specific DB plus `.par` directory with only a small loader change.
  Date/Author: 2026-03-12 / Codex.

- Decision: Keep the supported Tenerife runtime surface to the 25 m and 5 m configs.
  Rationale: Those are the only active Tenerife configs, and the user described the supported setup as two maps.
  Date/Author: 2026-03-12 / Codex.

- Decision: Retain `tf_soil_10.tif` as reference-only 2026 inventory.
  Rationale: It belongs to Jonay's delivered 2026 bundle, but there is no active config that should imply a third Tenerife runtime path.
  Date/Author: 2026-03-12 / Codex.

- Decision: Keep `20.sol` and `21.sol`, but retire the template-era Tenerife soil branch.
  Rationale: The active rasters still require `20` and `21`, while the old 250 m config/raster path and template-generation files no longer represent the runtime source of truth.
  Date/Author: 2026-03-12 / Codex.

## Outcomes & Retrospective

Outcome:
- Tenerife now has a dedicated station catalog with 62 Jonay-provided station parameter files.
- The active Tenerife configs use that dedicated catalog instead of shared GHCN and explicitly default to WBT delineation.
- The Tenerife soil runtime surface is reduced to the supported 5 m and 25 m maps, with `tf_soil_10.tif` preserved only as reference inventory.
- Legacy Tenerife soil assets that obscured the runtime source of truth are retired.
- Tenerife-specific tests and validation now cover the exact contracts this package changed.

Remaining gap:
- None within the scoped data-ingestion package.

Lesson learned:
- The dangerous Tenerife loose ends were mostly ambiguous source-of-truth problems. Once catalog ownership and supported runtime inventory were made explicit, the actual data integration was small and deterministic.

## Final Validation

- `python wepppy/climates/cligen/_scripts/build_tenerife_station_db.py --source-climate-dir /workdir/tenerife-2026/climate --output-dir /workdir/wepppy/wepppy/climates/cligen`
- `PYTHONPATH=/workdir/wepppy /workdir/wepppy/.venv/bin/pytest tests/climates/test_cligen_tenerife_catalog.py tests/soils/test_tenerife_soil_catalog.py --maxfail=1`
- Direct HTTP probes to:
  - `https://wepp.cloud/webservices/wmesque2/retrieve/tenerife/136_MDT25_TF/?bbox=-16.543,28.2907,-16.523,28.3107&cellsize=25&format=GTiff`
  - `https://wepp.cloud/webservices/wmesque2/retrieve/tenerife/MDT05_Tenerife/?bbox=-16.543,28.2907,-16.523,28.3107&cellsize=5&format=GTiff`
- `wctl doc-lint --path docs/work-packages/20260312_tenerife_2026_data_ingestion`
- `wctl doc-lint --path PROJECT_TRACKER.md`
- `wctl doc-lint --path AGENTS.md`
- `wctl doc-lint --path wepppy/climates/cligen/README.md`
- `wctl doc-lint --path wepppy/locales/tenerife/soils/README.md`
- `tools/check_agents_size.sh AGENTS.md`

## Final Interfaces

- `wepppy/nodb/configs/tenerife-disturbed.cfg`
- `wepppy/nodb/configs/tenerife-5m-disturbed.cfg`
- `wepppy/climates/cligen/tenerife_stations.db`
- `wepppy/climates/cligen/tenerife_stations.csv`
- `wepppy/climates/cligen/tenerife_par_files/`
- `wepppy/climates/cligen/_scripts/build_tenerife_station_db.py`
- `wepppy/climates/cligen/cligen.py`
- `wepppy/locales/tenerife/soils/README.md`
- `tests/climates/test_cligen_tenerife_catalog.py`
- `tests/soils/test_tenerife_soil_catalog.py`

Revision note (2026-03-12): Created as the active Tenerife ExecPlan after discovery, then archived to `prompts/completed/` after implementation, validation, and package closeout.
