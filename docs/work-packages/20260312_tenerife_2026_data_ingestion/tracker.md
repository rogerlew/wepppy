# Tracker - Tenerife 2026 Data Ingestion

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-03-12  
**Completed**: 2026-03-12  
**Current phase**: Complete  
**Last updated**: 2026-03-12  
**Next milestone**: None for this package  
**Implementation plan**: `docs/work-packages/20260312_tenerife_2026_data_ingestion/prompts/completed/tenerife_2026_data_ingestion_execplan.md`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Audited current Tenerife configs, climate wiring, and soil runtime behavior against `/workdir/tenerife-2026` (2026-03-12).
- [x] Confirmed Tenerife 5 m, 10 m, and 25 m soil rasters in `wepppy/locales/tenerife/soils/` match the 2026 source bundle byte-for-byte (2026-03-12).
- [x] Confirmed the 43 source Tenerife `.sol` files match the repo copies exactly, while raster codes `20` and `21` still depend on repo-only shim `.sol` files because the active rasters contain those values (2026-03-12).
- [x] Chose the dedicated Tenerife climate catalog approach instead of augmenting shared `ghcn_stations.db` (2026-03-12).
- [x] Added `CligenStationsManager` support for the dedicated Tenerife catalog and switched active Tenerife configs to `cligen_db = "tenerife_stations.db"` (2026-03-12).
- [x] Switched both active Tenerife configs to explicit WBT delineation with Tenerife-specific `watershed.wbt` settings (2026-03-12).
- [x] Added repeatable Tenerife climate catalog builder `wepppy/climates/cligen/_scripts/build_tenerife_station_db.py` and rebuilt `tenerife_stations.db` plus `tenerife_par_files/` from `/workdir/tenerife-2026/climate/` (2026-03-12).
- [x] Verified live `wmesque2` retrieval for `tenerife/136_MDT25_TF` and `tenerife/MDT05_Tenerife` from the WEPPpy side using direct HTTP probes (2026-03-12).
- [x] Retired the legacy Tenerife 250 m soil/config branch and template-generation artifacts, while keeping `tf_soil_10.tif` as reference-only inventory (2026-03-12).
- [x] Added Tenerife-focused regression coverage for climate catalog loading, config wiring, and supported soil raster coverage (2026-03-12).
- [x] Closed the package docs and archived the ExecPlan to `prompts/completed/` (2026-03-12).

## Timeline

- **2026-03-12** - Package created and initial Tenerife 2026 discovery completed.
- **2026-03-12** - Climate gap confirmed: only the three legacy Tenerife GHCN stations were wired into the active catalog path.
- **2026-03-12** - Dedicated Tenerife climate catalog landed, Tenerife configs switched off shared GHCN, and the Tenerife station bundle was rebuilt from Jonay's source files.
- **2026-03-12** - Direct `wmesque2` probes returned HTTP 200 for `tenerife/136_MDT25_TF` and `tenerife/MDT05_Tenerife`.
- **2026-03-12** - Active Tenerife configs were finalized onto explicit WBT delineation defaults.
- **2026-03-12** - Legacy Tenerife 250 m soil/config assets and template-generation artifacts were retired; `tf_soil_10.tif` was kept as reference inventory only.
- **2026-03-12** - Tenerife targeted tests passed and the package was closed.

## Decisions

### 2026-03-12: Keep observed Tenerife `.cli` ingestion out of this package
**Context**: The user explicitly scoped Tenerife climate file ingestion out of the current work and said those files can remain user-defined uploads.

**Options considered**:
1. Ingest both Tenerife `.par` and `.cli` assets into managed runtime paths.
2. Limit the package to station `.par` ingestion and leave observed `.cli` files user-defined.
3. Defer all Tenerife climate work.

**Decision**: Choose option 2.

**Impact**: The package focuses on station selection and CLIGEN parameter availability, not on shipping managed observed climate datasets.

---

### 2026-03-12: Use a dedicated Tenerife climate catalog instead of augmenting shared GHCN
**Context**: Tenerife's 62 `Estacion_*` station parameter files are not GHCN stations, and the active shared GHCN path carried semantic mismatch and unnecessary coupling.

**Options considered**:
1. Augment `ghcn_stations.db` and `GHCN_Intl_Stations/all_years/` with Tenerife-local files.
2. Create `tenerife_stations.db` and a Tenerife-specific `.par` directory, then point Tenerife configs there.
3. Leave Tenerife on the three existing GHCN Tenerife airport stations.

**Decision**: Choose option 2.

**Impact**: Tenerife climate work is a clean catalog addition with Tenerife-specific assets and config changes, avoiding cross-contamination of the shared GHCN path.

---

### 2026-03-12: Keep `tf_soil_10.tif` as reference inventory but retire the legacy 250 m Tenerife soil branch
**Context**: Discovery showed the repo contains three current Tenerife rasters from the 2026 bundle (`5 m`, `10 m`, `25 m`), but only the 5 m and 25 m paths are surfaced by active configs. The old 250 m Tenerife raster/config path and template-generation artifacts only obscured the current runtime source of truth.

**Options considered**:
1. Preserve the old 250 m branch and template artifacts in place.
2. Remove the old 250 m branch and template artifacts, keep `tf_soil_10.tif` as inert reference inventory until a real runtime consumer exists.
3. Remove both the old 250 m branch and `tf_soil_10.tif`.

**Decision**: Choose option 2.

**Impact**: Active Tenerife runtime support is now explicitly limited to the 5 m and 25 m maps, while the 10 m raster stays available for future Tenerife work without pretending to be an active config path.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Jonay's 62 Tenerife station `.par` files could drift from repo assets during future refreshes. | Medium | Medium | Re-run `build_tenerife_station_db.py` against the new source bundle and keep the dedicated Tenerife tests green. | Mitigated |
| Active Tenerife soil rasters still contain codes `20` and `21`, which remain runtime shims rather than source-bundle soil profiles. | Medium | High | Keep `20.sol` and `21.sol` documented in `wepppy/locales/tenerife/soils/README.md` unless `wepppy/nodb/core/soils.py` grows explicit non-`.sol` handling for those classes. | Accepted |

## Verification Checklist

### Data and Runtime
- [x] Tenerife 25 m config can resolve its DEM catalog entry and soil map path.
- [x] Tenerife 5 m config can resolve its DEM catalog entry and soil map path.
- [x] Active Tenerife climate catalog lookup surfaces Jonay's Tenerife stations through the dedicated Tenerife catalog.
- [x] Every raster code encountered in supported Tenerife soil maps resolves to a valid runtime action.

### Tests and Validation
- [x] Tenerife-focused pytest coverage added or updated.
- [x] Targeted Tenerife pytest passes with the local project venv fallback.
- [x] Manual or scripted Tenerife smoke checks recorded for climate catalog lookup and soil resolution.

### Documentation
- [x] `package.md`, `tracker.md`, and the completed ExecPlan are synchronized.
- [x] Remaining Tenerife assets kept in-repo are documented with intent.
- [x] `PROJECT_TRACKER.md` remains aligned with package status.

## Progress Notes

### 2026-03-12: Initial audit and package setup
**Agent/Contributor**: Codex

**Work completed**:
- Compared current Tenerife repo assets against `/workdir/tenerife-2026`.
- Confirmed the active climate gap: Jonay's 62 `Estacion_*` `.par` files were not wired into the active `ghcn_stations.db` path.
- Recorded the decision to create a dedicated Tenerife climate catalog instead of augmenting shared GHCN.
- Confirmed the active soil runtime gap was mostly contract clarity, not missing source files: the 5 m, 10 m, and 25 m rasters and 43 source `.sol` files already matched the source bundle, but runtime still depended on special `20.sol` and `21.sol` shims and carried legacy Tenerife artifacts.
- Created the Tenerife 2026 work package and active ExecPlan.

**Test results**:
- Discovery only.

### 2026-03-12: Tenerife implementation and closeout
**Agent/Contributor**: Codex with explorer and worker subagents

**Work completed**:
- Added `CligenStationsManager` support for `tenerife_stations.db`.
- Added `wepppy/climates/cligen/_scripts/build_tenerife_station_db.py`.
- Rebuilt `wepppy/climates/cligen/tenerife_stations.db`, `wepppy/climates/cligen/tenerife_stations.csv`, and `wepppy/climates/cligen/tenerife_par_files/` from `/workdir/tenerife-2026/climate/`.
- Switched `wepppy/nodb/configs/tenerife-disturbed.cfg` and `wepppy/nodb/configs/tenerife-5m-disturbed.cfg` to `cligen_db = "tenerife_stations.db"` and explicit WBT delineation.
- Recorded Tenerife soil runtime intent in `wepppy/locales/tenerife/soils/README.md`.
- Closed the old Tenerife 250 m soil/config path and retired template-era Tenerife soil generation artifacts.
- Added `tests/climates/test_cligen_tenerife_catalog.py` and `tests/soils/test_tenerife_soil_catalog.py`.
- Archived the ExecPlan and closed the package/tracker docs.

**Blockers encountered**:
- Direct Python import of `wepppy.all_your_base.geo` outside the usual runtime env failed on missing `utm`, so DEM verification used direct `wmesque2` HTTP probes instead of the helper wrapper.

**Validation evidence**:
- `python wepppy/climates/cligen/_scripts/build_tenerife_station_db.py --source-climate-dir /workdir/tenerife-2026/climate --output-dir /workdir/wepppy/wepppy/climates/cligen`
- `PYTHONPATH=/workdir/wepppy /workdir/wepppy/.venv/bin/pytest tests/climates/test_cligen_tenerife_catalog.py tests/soils/test_tenerife_soil_catalog.py --maxfail=1`
- Direct HTTP probes to `https://wepp.cloud/webservices/wmesque2/retrieve/tenerife/136_MDT25_TF/` and `.../tenerife/MDT05_Tenerife/` both returned HTTP 200 for a Tenerife-centered bbox.

## Watch List

- **Future Tenerife refreshes**: Rebuild the dedicated Tenerife catalog from source rather than hand-editing the SQLite DB or `.par` directory.
- **Soil code `20` / `21` behavior**: If Tenerife ever moves away from `.sol` shims for those codes, make it a deliberate runtime change in `wepppy/nodb/core/soils.py`, not an asset-only cleanup.
