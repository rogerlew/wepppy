# POLARIS NoDb/Mods Client for Run-Scoped Raster Retrieval and Grid Alignment

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Completion Outcome (2026-03-14)

- Status: Completed and moved to `prompts/completed/`.
- Final validations:
  - Focused POLARIS tests passed.
  - Full-suite sanity passed (`wctl run-pytest tests --maxfail=1` -> `2321 passed, 34 skipped`).
  - Route contract freeze artifacts updated for `acquire-polaris`.

## Purpose / Big Picture

After this package lands, a run can fetch POLARIS soil property rasters from the Duke endpoint and store them under `<wd>/polaris/` in the same projection, extent, resolution, and raster shape as existing project maps. Layer selection is configuration-driven and not limited to a narrow hardcoded subset, so the same substrate can support gridded RUSLE detachment analysis now and WEPP-soils derivation in a follow-up package.

Observable outcomes:

1. A configured layer request (for example `clay_mean_0_5`) produces an aligned run-local raster and metadata sidecar under `polaris/`.
2. The generated `polaris/README.md` documents attribution, units/log-space notes, request config, and fetched layers.
3. Focused tests confirm alignment and idempotent re-runs.

## Progress

- [x] (2026-03-13 20:15Z) Created package scaffold (`package.md`, `tracker.md`, active ExecPlan path, `notes/`, `artifacts/`).
- [x] (2026-03-13 20:25Z) Captured POLARIS source inventory from endpoint + readme and validated VRT count (`390`).
- [x] (2026-03-13 20:35Z) Mapped run-grid alignment seams (`Ron.map`, `raster_stacker`, run DEM contracts).
- [x] (2026-03-13 21:10Z) Milestone 1: contract decisions locked from user feedback (defaults/config path/endpoint/output/cache/scope).
- [x] (2026-03-13 22:05Z) Milestone 2: implemented POLARIS mod scaffold + endpoint catalog parser under `wepppy/nodb/mods/polaris/`.
- [x] (2026-03-13 22:10Z) Milestone 3: implemented fetch + align pipeline with manifest + run-local `polaris/README.md`.
- [x] (2026-03-13 22:15Z) Milestone 4: integrated async rq-engine endpoint + RQ task (`acquire-polaris`, `fetch_and_align_polaris_rq`).
- [x] (2026-03-13 23:05Z) Re-ran focused validations (`pytest` targets, broad-exception enforcement, rq-graph check, docs lint).
- [x] (2026-03-13 23:45Z) Added direct `acquire_and_align()` unit coverage for skip/force-refresh and re-ran focused tests (`7 passed`).
- [x] (2026-03-13 23:50Z) Real-run integration validation on `insightful-peacock` created `polaris.nodb` and verified DEM grid parity.
- [ ] Milestone 5: validations and closeout synchronization (completed: focused tests, integration validation, broad-exception gate, rq-graph drift check, docs lint, final validation artifact; remaining: optional full-suite sanity run).

## Surprises & Discoveries

- Observation: The POLARIS endpoint is directory-index based, not a JSON API.
  Evidence: `http://hydrology.cee.duke.edu/POLARIS/PROPERTIES/v1.0/` serves Apache index pages and a plain-text `Readme`.
- Observation: Published VRT catalog is full-factorial across property/stat/depth axes.
  Evidence: `390` VRT links under `/POLARIS/PROPERTIES/v1.0/vrt/` (13 properties x 5 statistics x 6 depths).
- Observation: POLARIS VRT layers are EPSG:4326 with 1-arcsec resolution and `NoDataValue=-9999`.
  Evidence: `clay_mean_0_5.vrt` header includes WGS84 geotransform step `2.7777777777570245e-04` and nodata `-9999`.
- Observation: Existing NoDb raster alignment utility already supports "match raster grid exactly" behavior.
  Evidence: `wepppy/all_your_base/geo/geo.py::raster_stacker` reprojects/resamples source to the target raster profile.
- Observation: `rasterio` can read POLARIS VRT URLs directly, so remote source tiles can be streamed without persisting local raw rasters by default.
  Evidence: local probe opening `http://hydrology.cee.duke.edu/POLARIS/PROPERTIES/v1.0/vrt/clay_mean_0_5.vrt` returned valid dimensions/CRS.

## Decision Log

- Decision: Keep the layer selection mechanism catalog-driven and configuration-backed from the start.
  Rationale: User requirement explicitly calls for broad support across POLARIS layers; hardcoded subsets create recurring rework.
  Date/Author: 2026-03-13 / Codex
- Decision: Align outputs immediately to run grid contracts rather than storing only native EPSG:4326 intermediates.
  Rationale: Downstream model consumers in this repo are run-grid-centric and should not need another reprojection stage.
  Date/Author: 2026-03-13 / Codex
- Decision: Treat run-local `polaris/README.md` + per-layer metadata as first-class deliverables.
  Rationale: Provenance/units/log-space context is critical for safe scientific reuse and later WEPP/RUSLE derivations.
  Date/Author: 2026-03-13 / Codex
- Decision: Use top-horizon `sand`, `clay`, `bd`, and `om` as the phase-1 default layer request.
  Rationale: User-selected default balances immediate utility with manageable fetch/runtime costs.
  Date/Author: 2026-03-13 / Codex
- Decision: Add rq-engine endpoint in phase 1 and keep outputs as GeoTIFF-only.
  Rationale: User explicitly requested endpoint exposure and format simplification.
  Date/Author: 2026-03-13 / Codex
- Decision: Keep aligned outputs only by default, with a config/payload flag to retain intermediates for debugging.
  Rationale: Minimize storage overhead while preserving low-friction debugging path when needed.
  Date/Author: 2026-03-13 / Codex
- Decision: Constrain phase 1 to retrieval/alignment only.
  Rationale: De-risks core substrate before deriving RUSLE/WEPP products.
  Date/Author: 2026-03-13 / Codex
- Decision: Keep POLARIS endpoint execution manual for phase 1 (no auto-trigger in pipeline).
  Rationale: User requested manual-only operation to keep retrieval explicit during contract hardening.
  Date/Author: 2026-03-13 / Codex

## Outcomes & Retrospective

Work package scaffolding and implementation milestones are complete for the phase-1 retrieval/alignment contract.

Implementation is now functionally in place for phase-1 scope:
- POLARIS NoDb mod implemented.
- Async endpoint + RQ task implemented.
- Config defaults locked to top-horizon `sand/clay/bd/om`.
- Focused tests and required changed-file gates are passing.
- Real-run integration check completed on `/wc1/runs/in/insightful-peacock` with raster parity against run DEM.

Remaining closeout is optional broad-suite sanity (`wctl run-pytest tests --maxfail=1`) before package completion.

## Context and Orientation

Relevant repository context:

- Run map/grid source of truth:
  - `wepppy/nodb/core/ron.py` (`Map` object, `Ron.map`, `cellsize`, `extent`, `dem_fn`)
- Existing raster grid alignment utility:
  - `wepppy/all_your_base/geo/geo.py` (`raster_stacker`)
- Reference NoDb mod patterns:
  - `wepppy/nodb/mods/openet/openet_ts.py` (mod state, caching, run artifacts)
  - `wepppy/nodb/mods/shrubland/shrubland.py` (run raster acquisition pattern)
- Async API wiring pattern:
  - `wepppy/microservices/rq_engine/openet_ts_routes.py`
  - `wepppy/rq/project_rq.py`
  - `wepppy/nodb/redis_prep.py`

POLARIS source structure (validated):

- Base: `http://hydrology.cee.duke.edu/POLARIS/PROPERTIES/v1.0/`
- Properties: `alpha`, `bd`, `clay`, `hb`, `ksat`, `lambda`, `n`, `om`, `ph`, `sand`, `silt`, `theta_r`, `theta_s`
- Statistics: `mean`, `mode`, `p5`, `p50`, `p95`
- Depth intervals: `0_5`, `5_15`, `15_30`, `30_60`, `60_100`, `100_200`
- VRT naming pattern: `<property>_<stat>_<depth>.vrt`

## Plan of Work

Milestone 1 freezes contracts and keeps scope disciplined. Define where POLARIS requests are configured (run cfg section and/or repo-side default config file), the exact schema for selecting properties/stats/depths, and the metadata schema written alongside outputs. This milestone also decides whether POLARIS execution is config-only, mod-toggle-enabled, or both.

Milestone 2 adds the implementation scaffold under `wepppy/nodb/mods/polaris/`. Create the controller class, endpoint catalog parsing/validation helpers, and a normalized internal layer-request model. Include robust failures for malformed requests and unavailable source layers.

Milestone 3 implements raster retrieval and alignment. For each selected layer, fetch from POLARIS (via VRT/tile source strategy chosen in Milestone 1), warp/resample onto run grid using canonical alignment utility, and write deterministic outputs under `<wd>/polaris/`. Emit sidecar metadata and generate `polaris/README.md` with attribution, units, and layer inventory.

Milestone 4 adds async orchestration. Introduce a focused rq-engine endpoint and RQ task so POLARIS acquisition can run asynchronously from controls/automation. Wire RedisPrep task bookkeeping and optional batch-run hook if approved by contract decisions.

Milestone 5 closes quality and docs loops. Add targeted tests for parsing, alignment, idempotence, and route contracts; run required validation commands; synchronize tracker/package/ExecPlan and capture final artifacts.

## Concrete Steps

Run all commands from `/workdir/wepppy`.

1. Rebuild/verify source inventory and layer counts.

    curl -sS 'http://hydrology.cee.duke.edu/POLARIS/PROPERTIES/v1.0/Readme'

    curl -sS 'http://hydrology.cee.duke.edu/POLARIS/PROPERTIES/v1.0/vrt/' | rg -o 'href="[^"]+\.vrt"' | wc -l

2. Implement POLARIS mod scaffold and supporting helpers.

    Create and edit:
    - `wepppy/nodb/mods/polaris/__init__.py`
    - `wepppy/nodb/mods/polaris/polaris.py`
    - `wepppy/nodb/mods/polaris/polaris_config.py` (or equivalent schema helper)
    - `wepppy/nodb/mods/polaris/README.md`

3. Implement async route/task surfaces (if approved by Milestone 1 decision).

    Edit:
    - `wepppy/microservices/rq_engine/polaris_routes.py` (new)
    - `wepppy/microservices/rq_engine/__init__.py`
    - `wepppy/rq/project_rq.py`
    - `wepppy/nodb/redis_prep.py`
    - `wepppy/nodb/batch_runner.py` (only if batch support included in scope)

4. Add/update tests.

    Candidate test files:
    - `tests/nodb/mods/test_polaris.py` (new)
    - `tests/microservices/test_rq_engine_polaris_routes.py` (new)

5. Run validation.

    wctl run-pytest tests/nodb/mods/test_polaris.py tests/microservices/test_rq_engine_polaris_routes.py -q

    wctl run-pytest tests --maxfail=1

    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master

    wctl doc-lint --path docs/work-packages/20260313_polaris_nodb_runs_client

## Validation and Acceptance

Acceptance requires all items below:

- Selected POLARIS layers are fetched and written under `<wd>/polaris/` with deterministic naming.
- Output rasters match run-grid contracts (same CRS/transform/shape as template project raster, typically `ron.dem_fn`).
- `polaris/README.md` is generated with attribution, units/log-space notes, depth/stat definitions, and layer manifest.
- Re-running acquisition with unchanged config is idempotent (no duplicate/misaligned artifacts).
- Focused tests pass and required docs/tracker synchronization is complete.

## Idempotence and Recovery

- Layer materialization should be safe to re-run; unchanged requests should skip or overwrite deterministically.
- On per-layer fetch failure, preserve completed layers and return explicit error details for failed layers.
- Metadata generation should be atomic: write to temp file then rename.
- Recovery path: delete `<wd>/polaris/` and re-run acquisition to rebuild from source.

## Artifacts and Notes

Required artifacts in this package:

- `docs/work-packages/20260313_polaris_nodb_runs_client/notes/polaris_source_inventory.md`
- `docs/work-packages/20260313_polaris_nodb_runs_client/artifacts/final_validation_summary.md` (at closeout)
- `docs/work-packages/20260313_polaris_nodb_runs_client/tracker.md`

Optional implementation artifacts:

- Endpoint parsing snapshots.
- Alignment verification report (CRS/transform/shape comparisons).

## Interfaces and Dependencies

Primary dependencies and interfaces:

- POLARIS endpoint: `http://hydrology.cee.duke.edu/POLARIS/PROPERTIES/v1.0/`
- Run map/grid: `wepppy.nodb.core.ron.Map`, `Ron.map`, `Ron.dem_fn`
- Alignment utility: `wepppy.all_your_base.geo.geo.raster_stacker`
- NoDb base contracts: `wepppy.nodb.base.NoDbBase`
- RQ surfaces: `wepppy.rq.project_rq`, `wepppy.microservices.rq_engine`

Target interfaces to implement:

- A POLARIS controller class exposing at minimum:
  - catalog discovery/validation
  - layer acquisition for a request set
  - run-local metadata materialization
- Optional rq-engine route:
  - enqueue POLARIS acquisition with canonical response envelope

## Resolved Milestone 1 Decisions

1. Default request targets top-horizon means for `sand`, `clay`, `bd`, and `om`.
2. Initial config contract is anchored in `wepppy/nodb/configs/disturbed9002_wbt.cfg` (`[polaris]` section).
3. rq-engine endpoint is included in phase 1 (`/api/runs/{runid}/{config}/acquire-polaris`).
4. Output format is GeoTIFF-only.
5. Default storage keeps aligned outputs only; `keep_source_intermediates` flag is available for debugging.
6. Phase 1 scope is retrieval/alignment only.

Revision note (2026-03-13 20:45Z): Initial ExecPlan authored with discovery evidence, milestone sequence, and explicit open questions for implementation kickoff.  
Revision note (2026-03-13 21:10Z): Open questions resolved from user decisions; Milestone 1 marked complete and implementation constraints locked.
Revision note (2026-03-13 22:20Z): Implemented POLARIS mod, rq-engine endpoint, RQ task, focused tests, and required queue-graph synchronization.
