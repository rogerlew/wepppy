# POLARIS NoDb Runs Client for Project-Aligned Raster Layers

**Status**: Closed (2026-03-14)

## Overview
This package scopes and implements a run-scoped POLARIS raster client in NoDb/mods. The target behavior is to fetch POLARIS soil property layers from the Duke endpoint, align each output raster to the active project grid (same projection, extent, dimensions, and cell size as other run rasters), and persist artifacts under `polaris/` with attribution and metadata.

The immediate use case is gridded RUSLE-style detachment analysis. A downstream follow-up may derive WEPP-ready soils from POLARIS layers once the retrieval/alignment substrate is stable.

## Objectives
- Build a NoDb/mods POLARIS client that supports broad layer access (all published POLARIS properties/stats/depths).
- Make layer selection configuration-driven (run config + package defaults) instead of hardcoding a narrow subset.
- Ship phase-1 defaults for top-horizon mean layers: `sand`, `clay`, `bd`, `om`.
- Guarantee run-local outputs are grid-aligned to project rasters using canonical NoDb map/grid contracts.
- Persist all fetched artifacts and metadata under `<wd>/polaris/`, including a generated `polaris/README.md` with attribution and provenance.
- Add regression coverage for endpoint parsing, alignment correctness, and idempotent re-runs.

## Scope

### Included
- POLARIS endpoint inventory and layer-catalog contract.
- NoDb mod/client implementation under `wepppy/nodb/mods/polaris/`.
- Config-driven layer request schema (properties/statistics/depths).
- Initial config wiring in `wepppy/nodb/configs/disturbed9002_wbt.cfg`.
- Raster fetch + alignment pipeline to run grid.
- Run artifact metadata (`polaris/README.md`, per-layer metadata sidecars/manifests).
- RQ/task orchestration hooks and focused tests.

### Explicitly Out of Scope
- Full WEPP soil-generation pipeline from POLARIS layers.
- Final RUSLE model implementation and calibration.
- Broad UI redesign for POLARIS controls (minimal API/automation path only in this package).
- ASCII grid output variants (GeoTIFF-only for phase 1).

## Stakeholders
- **Primary**: NoDb/soil pipeline maintainers and geospatial workflow maintainers.
- **Reviewers**: RQ-engine maintainers and test-suite maintainers.
- **Informed**: RUSLE experimentation stakeholders and WEPP soils maintainers.

## Success Criteria
- [x] POLARIS client can enumerate and request any of the published endpoint layers through config.
- [x] Requested layers are materialized under `<wd>/polaris/` and registered in the run catalog.
- [x] Output rasters are aligned to run grid contracts (extent/projection/shape/cellsize match run map rasters).
- [x] `polaris/README.md` is generated with source attribution, units/depth/stat metadata, and fetch timestamp/provenance.
- [x] Focused NoDb + RQ route tests pass; docs/tracker/ExecPlan stay synchronized.

## Dependencies

### Prerequisites
- `Ron.map` / run DEM grid contract from `wepppy/nodb/core/ron.py`.
- Raster alignment helper `wepppy/all_your_base/geo/geo.py::raster_stacker`.
- POLARIS endpoint availability: `http://hydrology.cee.duke.edu/POLARIS/PROPERTIES/v1.0/`.

### Blocks
- Follow-on work to derive WEPP soil parameters from POLARIS layers.
- Follow-on gridded RUSLE detachment package that consumes POLARIS-aligned rasters.

## Related Packages
- **Related**: [20260312_tenerife_2026_data_ingestion](../20260312_tenerife_2026_data_ingestion/package.md) (recent raster/catalog ingestion patterns)
- **Follow-up**: POLARIS-to-WEPP soil generation package (to be scoped)
- **Follow-up**: POLARIS-backed gridded RUSLE detachment package (to be scoped)

## Timeline Estimate
- **Expected duration**: 1-2 weeks (discovery + implementation + validation)
- **Complexity**: High
- **Risk level**: Medium-High (remote source stability, geospatial alignment correctness)

## References
- `docs/work-packages/20260313_polaris_nodb_runs_client/prompts/completed/polaris_nodb_runs_client_execplan.md` - completed implementation plan and retrospective.
- `docs/work-packages/20260313_polaris_nodb_runs_client/notes/polaris_source_inventory.md` - endpoint discovery notes.
- `wepppy/nodb/core/ron.py` - canonical map/grid state (`Map`, `Ron.map`, `cellsize`).
- `wepppy/all_your_base/geo/geo.py` - `raster_stacker` alignment helper.
- `wepppy/nodb/mods/openet/openet_ts.py` - reference NoDb mod + RQ wiring pattern.
- `http://hydrology.cee.duke.edu/POLARIS/PROPERTIES/v1.0/` - POLARIS source index.

## Deliverables
- New POLARIS mod/client code + tests.
- Run-scoped `polaris/` artifact contract with generated metadata README.
- RQ/task wiring for asynchronous acquisition path.
- Updated work-package docs (`package.md`, `tracker.md`, ExecPlan, artifacts).

## Follow-up Work
- POLARIS-to-WEPP soil profile translation and validation.
- RUSLE detachment model integration using POLARIS-derived rasters.
- Optional UI controls for layer selection once API/contracts stabilize.

## Closure Summary (2026-03-14)
- Delivered a run-scoped POLARIS NoDb mod (`wepppy/nodb/mods/polaris/`) with catalog-driven layer selection, config defaults for top-horizon `sand/clay/bd/om`, and DEM-grid alignment to GeoTIFF outputs in `<wd>/polaris/`.
- Added async orchestration via `POST /api/runs/{runid}/{config}/acquire-polaris` with RQ task wiring and RedisPrep task tracking.
- Generated run-local `polaris/manifest.json` and `polaris/README.md` with attribution, request metadata, and layer inventory.
- Validated on a real run (`/wc1/runs/in/insightful-peacock/`) and verified output parity (CRS/transform/shape) versus run DEM.
- Closed required quality gates including full-suite sanity: `wctl run-pytest tests --maxfail=1` -> `2321 passed, 34 skipped`.
