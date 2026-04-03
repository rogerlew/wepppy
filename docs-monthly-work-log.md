# Monthly Work Log: May 2025 – March 2026

Retroactive summaries of WEPPpy development activity by month, constructed from git history. Commit counts are non-merge commits on master.

---

## May 2025 (72 commits)

**Theme: DuckDB integration, Omni scenarios, fire season prep**

- Integrated DuckDB into NoDb pipeline for accelerated data queries
- Built `land_and_soils` API with RQ routing for landuse/soil validation
- Overhauled GeoPackage export (`gpkg_export`) to use watershed parquet files and handle `.gdb` naming
- Launched Omni scenario framework (scenario descriptions, dependency state sync, Redis integration)
- SBS map hardening: float64 support without colortables, sanity checking for float maps, 4-class export
- ERMIT/disturbed input revisions (clip hillslope length to 300m, min 10% rock content)
- Return periods export and watershed CSV file improvements
- Updated SSURGO to 2025 revision
- Revised climate `_ss_time_to_peak_intensity_pct` default from 0.4 to 40
- ClimateNA API client (WIP)
- WeppCloud app health filter and browse fixes
- Disturbed management mapping: herbaceous to tall grass, `disturbed_class` safeguards

---

## June 2025 (35 commits)

**Theme: WhiteboxTools topaz emulator, parquet pipelines, daily streamflow**

- WhiteboxTools (WBT) Topaz Emulator: functional integration exporting `taspec.tif`, fill-or-breach option
- Extended disturbed land-soil lookup for fire series with external CSV parameters
- Daily streamflow graph rewrite: D3 v7 migration, hyetograph overlay, rain+melt, overlapping area bars
- Dump landuse and soils parquet with NoDb lifecycle (`dump_and_unlock`, `dump_landuse_parquet`)
- 15-min precip intensity for return periods
- Standardized thinning disturbed classes across US, EU, AU, and revegetation configs
- Omni: compile hillslope and channel summaries, mulch troubleshooting
- WeppCloud map: hillslope flash identify feature, fix `cmap_canvas_loss_min` display
- Updated EU-CORINE disturbed classes
- Runs 2.0 user page with pagination and self-hosted `sorttable.js`
- Added `last_accessed` and `last_modified` to Run data model with Alembic migration
- `db_api` to update postgres; `NoDbBase.dump` calls `update_last_modified`

---

## July 2025 (55 commits)

**Theme: Containerization, query engine, WEPP interchange**

- Full Docker Compose containerization: Caddy TLS termination, `wctl` CLI, service files, Gunicorn production config
- Query engine inception: core SQL-like parser, aggregators, group-by, order-by, catalog hooks, GeoJSON support
- WEPP interchange pipeline: hillslope and watershed interchange writers with ProcessPoolExecutor + streaming writer queue
- Removed legacy `wepppost` module (yeeted across ~10 commits)
- Migrated microservices from weppcloud2 to wepppy; Gunicorn installation
- `preflight2` and `status2` rewritten as Go apps; removed Python microservice predecessors
- `totalwatsed3` derived from WEPP interchange; daily streamflow via query engine
- Consolidated Redis config; Redis settings module
- WeppCloudR Docker container with optimized binary installation
- Interchange DSS exports; refactored ash to use interchange
- Removed legacy submodules (portland, seattle, taudem, county_db, cligen-ghcn-daily)
- NoDb atomic Redis locks with docs and tests
- AgFields module: functional sub-field running, management rotation stack/synth
- Batch runner: CLI monitor, generation GeoJSON boundary per watershed

---

## August 2025 (113 commits)

**Theme: Batch runner, ProxyFix, climate fixes, WATAR model**

- Batch runner phases 0-2: manifest handling, initialization refactoring, yeet manifest
- `weppcloud.app` ProxyFix for reverse proxy URL generation; fork links to new projects
- Alex WATAR Excel spreadsheet model integration (serialized features, static transport model)
- Ash model: Srivastava2023 vs Watanabe2025 selection, revised contaminant concentration
- Omni: `run_contrast` method, `clone_sibling`, worker pool integration
- Climate fixes: `par_mod` hotfix for very low precip, PRISM minimum monthly precip to 0.01
- Multi-OFE landuse building fix; MOFE hotfixes for soil building
- Combined watershed generator with Glify viewer
- Multiple channel-of-interest support for Ebe/ReturnPeriods
- Return period advanced options; Hill Streamflow in mm and m^3; Hill Sed Del in tonne
- Channel width hard minimum enforcement; channel slopes wrap aspect
- NLCD 2024 added; peridot bins updated
- Daymet: `daily_interpolation` validation for `identify_pixel_coords`
- Web push notifications (functional)
- Omni contrasts: NDJSON logging, Pareto validation script
- `weppcloud.app` refactored to conda env; updated `wepppy310-env.yml`

---

## September 2025 (396 commits)

**Theme: Massive platform modernization -- NoDb Redis cache, command bar, logging refactor, Flask security, blueprint reorg, CI Samurai**

### NoDb & Redis
- Unified NoDb loader logic; Redis caching of project `.nodb` files (DB 13, 72h TTL)
- `NoDbBase` refactored: file locking moved to Redis, `dump_and_unlock`, `ClassVar` for filename
- `StatusMessengerHandler` for logging to Redis channels
- `nodb_setter` decorator applied across dozens of properties for logging and locking
- `ProcessPoolExecutor` with spawn context for improved multiprocessing
- `tryGetInstance` refactored across NoDb API routes
- NoDb lock management: `clear_locks` command, lock statuses in preflight payload

### UI & UX
- Command bar: proof of concept through full implementation (browse, set, help, log-level, outlet commands, keyboard shortcuts)
- Poweruser panel: resource lock icons, tooltip functionality, restore button for anonymous users
- Blueprint reorganization: browse, archive-dashboard, fork-console, rq-archive-dashboard, runs0, create
- Flask security rewrite from scratch; authorization refactoring
- `controllers_js` reorganized with Gunicorn `on_start` compositing
- Usersum for soil files and automated indexing

### Logging & Observability
- Complete logging refactor: removed `LogMixin`/`Logger`, added Redis log handlers (from Iglesys347)
- Redis connection handling refactored to connection pool
- `timed` context manager in NoDbBase for performance measurement
- Comprehensive logging added to Climate, Soils, Landuse, Disturbed modules

### Infrastructure
- CI Samurai: end-to-end workflow, prompt tuning, Codex authoring pass, GPT-5 deep research
- `wctl` CLI tool: installer, shims for workflows, reorganization
- Profile recorder: end-to-end logging, playback engine
- Omni: Redis integration, locked NoDb files against parent run

### Other
- `wmesque2` migrated to FastAPI with benchmark
- SBS map hotfixes (series of 7)
- DSS export: chan.out export, start/end dates
- SSURGO: in-memory data views (Roger's idea, Gemini 2.5 Pro implementation)
- Revised `dem_db` default to `ned1/2024`

---

## October 2025

### Features

- **WEPP Interchange Pipeline** — Replaced the legacy `wepp.out` text-file parsers with a Parquet-based interchange layer (`hill_pass`, `watershed`, `totalwatsed3`). Hillslope interchange writers use a `ProcessPoolExecutor` + streaming writer queue for throughput. Watershed interchange adds memory-optimized streaming. Schema documentation auto-generated from `.parquet` files.
  *(~120 commits across interchange, query-engine, and related refactors)*

- **Query Engine** — New SQL-like query engine over interchange Parquet catalogs with aggregators, `GROUP BY`, `ORDER BY`, `IN`, `BETWEEN`, null handling, and type checking. Streamflow, runoff viz, and reports migrated from `wepppost` to the query engine. GeoJSON output support added. MCP (Model Context Protocol) spectral config published.
  *(~50 commits)*

- **Batch Runner** — Multi-watershed batch execution framework: `TaskEnum` breakout for hillslope vs. watershed runs, manifest-free Phase 2 design, CLI dashboard monitor, GeoJSON boundary per watershed, codex template system, `WatershedCollection` consolidation.
  *(~40 commits, phases 0–2)*

- **Docker Containerization** — Full production Docker Compose stack: Caddy reverse proxy, rq-worker farm, rq-dashboard container, postgres-backup sidecar, weppcloudr container (R environment), status2/preflight2 Go microservices, consolidated Redis config, static asset build pipeline (local vendor assets replacing CDN). Deprecated bare-metal deployment.
  *(~80 commits)*

- **AgFields Module** — Agricultural sub-field delineation: `AgFieldsNoDbLockedException`, polygonized ag fields, management rotation stack and synthesis, WEPP 2016.3 management file support with 98.4 downgrade converter.
  *(~25 commits)*

- **UI Overhaul ("Unstyling")** — Systematic removal of Bootstrap/jQuery styling from all controller panels (outlet, landuse, soils, climate, WEPP). Pure CSS controls adopted. Theme system introduced with VS Code-inspired themes and documentation.
  *(~60 commits)*

- **OAuth / Authentication** — GitHub, Google, and ORCID OAuth providers integrated via AuthLib 1.6.5.
  *(5 commits)*

- **CI Samurai** — Automated CI agent: end-to-end infrastructure tests, out-of-tree CAO server, NUC health checks, Gemini CLI integration, smoke tests.
  *(~30 commits)*

### Debugging & QA

- Fixed `wepp.out` hill_pass parser confusion (`sbrunf` vs `sbrunv`)
- Fixed `exclude_yr_indx` removal in omni
- Fixed race condition in `wepppost` with containerization
- Fixed `sbs_map` GDAL lib dependency
- Fixed `Modify Fire Class` rendering bug, `sbs_map` double-rendering
- Fixed query-engine strict-slash routing in production
- Fixed Climate.observed_start_year defaulting to `''` instead of `None`
- Hardened flask sessions post-containerization, atomic Redis locks for NoDb
- Resolved `.docker-data/redis` runner permission errors
- Thread-safe singleton caching and deterministic hydration for NoDb controllers

### Removals

- Removed legacy `wepp.out` parsers, `wepppost`, `fsweppy`, deprecated batch processor
- Removed `taudem`, Portland/Seattle submodules, `lt` template, old test projects
- Moved county DBs, cligen-ghcn-daily, old scripts to separate GitHub repos

### Cross-repo: peridot (14 commits, +2.8K / −4.1K)

- New `wbt_sub_fields_abstraction` CLI tool for agricultural sub-field slope profiles with area threshold filtering
- Code reorganization and documentation updates

### Cross-repo: wepp-forest (3 commits, +486 / −32)

- Added hillslope-optimized WEPP build (`wepp_hill`) alongside watershed binary
- Fixed WEPP hillslope hangs under IFX build by relaxing deposition tolerance

---

## November 2025

### Features

- **Profile Playback System** — CI-grade automated test runner: profile recorder captures run sequences, playback engine replays them with RQ polling, fork/archive support, UUID-based runs, seed configs. Integrated with `wctl` CLI. Multiple profile runs implemented (Rattlesnake, US Small, Earth Small, Seattle SimFire, Portland, EU, debris flow, RHEM rangeland, MOFE undisturbed/10m).
  *(~80 commits)*

- **DSS Export Enhancements** — HEC-DSS export with start/end date filtering, shapefile output, `ichout_override`, peak channel files per topaz ID, sediment volume concentrations. Single-storm interchange guards. Skip channel orders 1 and 2 by default.
  *(~30 commits)*

- **Landing Page Redesign** — deck.gl-powered active projects map, Run Atlas Hero section, quick links with map transitions, pinned map, points of contact, collaborating entities, sponsors section.
  *(~20 commits)*

- **High Contrast Theme / Accessibility** — `light-high-contrast-theme`, high-visibility summary panel, single-storm unitization for climate and ash controls.
  *(~10 commits)*

- **HEC-RAS Buffer** — Initial implementation using skimage for HEC-RAS boundary generation (GML output).
  *(5 commits)*

- **RHEM Rangeland** — Re-enabled rangeland module with RAP default cover, Rust `make_rhem_storm_file` via wepppyo3 (400× speedup), rangeland RQ and preflight.
  *(~10 commits)*

- **wctl2 CLI** — Rewritten CLI with tests, Claude acceptance testing, shim system for workflows, refactored installer.
  *(~20 commits)*

- **Playwright Test Suites** — Controller smoke tests, landuse validation, theme-metrics suite, treatments setup. Profile-based nightly runs.
  *(~15 commits)*

- **Coverage Infrastructure** — pytest-cov nightly with 2-hour fixer loop, NPM coverage nightly, GitHub badges for both.
  *(~15 commits)*

### Debugging & QA

- Fixed NoDb lock contention (thread-safe singleton caching, deterministic hydration)
- Fixed race condition in playback
- Fixed invalid cache refresh (`test_getinstance_refreshes_after_external_dump`)
- Fixed `dss_export` control DOM show bug (7+ iterations to resolve)
- Fixed ISRIC WKT projection issue
- Fixed NMME client URL
- Fixed `set_outlet` lon/lat mode
- Fixed `run_sync_rq` provenance cleanup
- Regression fixes for RHEM, stubs, and controller surface exceptions

### Cross-repo: all other repos inactive in November

---

## December 2025

### Features

- **deck.gl Map Migration** — Complete replacement of Leaflet map with deck.gl/MapLibre GL: 14 migration phases covering base tiles, subcatchment/channel overlays, slope/aspect rendering, 2D/3D modes, terrain, NHD flowlines, RAP spatial layers, landuse/soils legends, basemap sublabels. Client-side search and pagination for runs page.
  *(~30 commits)*

- **GL Dashboard** — Interactive WebGL analysis dashboard: WEPP event viewer with day/month/year controls, yearly data slider, timeseries plots, cumulative contribution curves, OpenET integration (monthly slider, map layer, time series), saturation metrics (replacing TSW), channel overlays with order exclusivity, omni scenario support with difference mapping, landuse comparison, basemap management, theme selector. Extensive documentation and test coverage.
  *(~70 commits)*

- **CAP (Cloud Analytics Platform)** — New Node.js container service for client analytics, phased rollout (8 phases), vendor `cap.js`.
  *(~10 commits)*

- **rq-engine** — Read-only FastAPI service for job status polling, decoupled from main Flask app.
  *(3 commits)*

- **Omni Enhancements** — Scenario preferential colors, base scenario descriptive names, delete scenarios feature, stream-order contrasts, treatments ground cover serialization to management summary and `landuse.parquet`.
  *(~15 commits)*

- **Observed Climate** — Report combined with graph, optimizations, proper monthly stats for station files.
  *(5 commits)*

- **Controller Trigger Refactor** — Polling completion refactored with `controlBase`, fork/archive updated to new polling contract, failure exception handling.
  *(~10 commits)*

- **Production Deployment** — Python 3.12 upgrade, `wctl` deploy scripts, health check URL resolution, geodata permission fixes, Docker build cache cleanup, file descriptor exhaustion fix through handler reuse.
  *(~15 commits)*

### Debugging & QA

- Fixed GL Dashboard: dominant landuse for non-NLCD keys, graph layer switching, WEPP/WEPP Yearly unit labels, basemap rendering
- Fixed fire-adjusted soil erodibility for mulch treatment scenarios
- Fixed snow density unit system (g/cm³)
- Fixed NRCS SDM Tabular service error handling
- Fixed omni scenario project UI loading
- Fixed `map-gl` resize/redraw on browser zoom
- Hardened NoDb file logging (preventing file descriptor exhaustion)
- Fixed 2023.* pw0.slp file invalidation
- Fixed preflight last-modified time propagation
- Fixed wildcard path searching

### Cross-repo: weppcloud-wbt (1 commit, +347K / −0)

- Added `fvslope` (filled valley slope) feature to WBT backend

### Cross-repo: peridot (1 commit, +44 / −1)

- Versioned binary release

---

## January 2026

### Features

- **Culvert-at-Risk Integration** — Major multi-phase integration (phases 0–5d) between WEPPcloud and `Culvert_web_app`: project synopsis generation with rasterio/fiona, viability checks (hydro DEM, watersheds, streams, culverts), DEM symlink/VRT management, native CRS landuse/soils retrieval, batch processing with `rq-worker-batch`, point-level retry, AI coding agent guide. Integration spec and ID bookkeeping documentation.
  *(~60 commits)*

- **Storm Event Analyzer** — New 9-phase analysis module: specification, `tc_out.parquet` with `sim_day_index` and julian keys, `wepp_cli.parquet` sim_day_index, precipitation frequency estimates, Atlas 14 integration, USGS National Map API migration for elevation service.
  *(~15 commits)*

- **Omni Contrasts** — User-defined hillslope group contrasts, stream-order pruning contrasts, 4-phase refactor (area contrasts, batch worker scaling, sidecar documentation, preflight refresh), scenario-local management keys for mulch treatments, composite runid resolution for nested scenarios.
  *(~25 commits)*

- **rq-engine Migration** — Complete migration of Flask export routes to rq-engine FastAPI service, create flow moved to rq-engine, error schema standardization (6 phases), RQ auth actor tagging with `rq-info` detail view, multipart upload routes, response contract updates.
  *(~20 commits)*

- **SWAT NoDb Module** — New SWAT (Soil and Water Assessment Tool) module with templates and specifications.
  *(1 commit, +286K LOC — initial scaffold)*

- **GL Dashboard Enhancements** — D8 flow arrow overlays, contrast support, OpenET payload documentation, bound contour GeoJSON outputs.
  *(~10 commits)*

- **Error Schema Standardization** — 6-phase normalization of error responses across Flask and FastAPI surfaces, internal error page with stacktrace details.
  *(7 commits)*

- **Production Hardening** — CPU pinning to isolate UI from compute workers, Redis auth, Gunicorn workers 2→4, Caddy/Redis image bumps, worker deployment guide, NFS delete/recreate benchmarks, idle transaction + FD leak work-package.
  *(~15 commits)*

### Debugging & QA

- Fixed case mismatch in `ca-disturbed.json` for `Shrub.man` path
- Fixed `has_sbs` to respect Baer when Disturbed is empty
- Fixed omni undisturbed SBS gate check
- Fixed CA disturbed severity mapping
- Fixed unitizer canonical value handling in form serialization
- Fixed numpy 1.25+ compatibility for jsonpickle deserialization in SSURGO soils
- Fixed GDAL constant reference for opening DEM files
- Fixed migration job dashboard link prefix
- Fixed user-defined climate station metadata
- Fixed PASS CLI hint and CLI calendar validation
- Hardened cligen timeouts with API backoff
- Idle transaction + file descriptor leak hardening validated in production

### Cross-repo: weppcloud-wbt (16 commits, +147K / −550)

- Added VRT (Virtual Raster) support for `whitebox-raster` with acceptance tests and fixtures
- Added binary output option to `PruneStrahlerStreamOrder`
- `hillslopes_topaz` profiling improvements and minimal stream handling fixes
- Epsilon guard for `rasters_share_geometry`

### Cross-repo: peridot (5 commits, +1.9K / −213)

- Added representative flowpath mode for WBT channel delineation
- Added source-cell edge flowpaths with WBT fixture
- Added VRT file support for raster inputs
- Memory optimizations and logging for observability

---

## February 2026

### Features

- **NoDir Reversal Completion** — Completed the NoDir reversal across runtime, tests, and documentation, including materialization/thaw-freeze contract work and cleanup of legacy compatibility paths.
  *(~45 commits)*

- **Browse/Auth/Session Hardening** — Hardened cross-service auth boundaries: cookie/bearer fallback parity tests, CSRF coverage for legacy flows, token scoping, stale-session recovery, and route contract documentation.
  *(~40 commits)*

- **Omni + Batch/Composite Reliability** — Continued Omni refactors and contrast workflows, with durability fixes for composite runids, clone/reset behavior, dir-root mutations, and missing-source recovery in batch contexts.
  *(~35 commits)*

- **Culvert Batch Integration** — Added queue wiring and orchestration for Culvert batch finalization, privileged admin token handling for downloads, and lock/race hardening in batch workers.
  *(~20 commits)*

- **rq-engine Surface Expansion** — Extended rq-engine/UI integration with admin job detail endpoints, token URL fallback fixes, and improved route wiring for queued workflows.
  *(~20 commits)*

- **SWAT Controller Integration** — Advanced SWAT NoDb integration with controller mixin splits, interchange handling updates, hydraulic-sediment option plumbing, and UI/file-browsing support.
  *(~10 commits)*

- **Topaz/DEM Resilience** — Hardened Topaz execution loops (`dednm` PRUNE fix, subprocess guardrails), plus NED1 VRT alignment tooling and GDAL openability wait checks.
  *(~6 commits)*

### Debugging & QA

- Fixed DEVAL `weppcloudR` argument compatibility and R expression parsing
- Fixed CSRF on disturbed CSV save and expanded legacy POST CSRF coverage
- Fixed batch browse auth flow and composite runid browse cookie scoping
- Fixed batch runner workspace reset behavior and stale batch GeoJSON cache refresh
- Fixed Omni dir-root cloning edge cases and root projection/soils path durability
- Fixed climate prep race conditions and malformed `srad` start-date URL handling
- Fixed WEPP completion event handling and report triggering when interchange invalidates `loss_pw0.txt`
- Fixed culvert batch lock race and added retry for missing clipped raster outputs
- Fixed CAP/rq-engine environment propagation and secrets-migration startup regressions
- Hardened JWT/session lifecycle, route auth fallback behavior, and Firefox session recovery

### Cross-repo: weppcloud-wbt (4 commits, +971 / −124)

- Enhanced `UnnestBasins` with hierarchy sidecar output and faster order mapping
- Added bibliography references (including Lindsay 2015/2016) and description cleanup
- Removed persistent environment snapshot behavior in WhiteboxTools wrapper

### Cross-repo: peridot (2 commits, +2.7K / −454)

- Fixed zero-elevation channel panic and added `sooke03` regression tests
- Applied rustfmt/style cleanup

### Cross-repo: wepp-forest (1 commit, +53 / −35)

- Added TSMF soil output column and saturation guard logic

---

## March 2026

### Features

- **Usersum Docs Engine** — Shipped a manifest-driven usersum documentation engine with richer linking contracts, searchable snippets, source footers, and expanded in-app guide coverage.
  *(~17 commits)*

- **RUSLE Integration** — Delivered RUSLE NoDb + UI integration with climatology datasets, canonical selectors (`r_mode`, MOMM), slope-length controls, and GL dashboard visualization support.
  *(~34 commits)*

- **Roads NoDb Workflow** — Implemented Roads NoDb end-to-end workflow in WEPPcloud and aligned it with peridot trace-core work, routing rules, and execution contracts.
  *(~19 commits)*

- **WEPP:Road Patches & Tests (`fswepp-docker`)** — Fixed WEPP:Road batch slope-type handling and added parity-matrix tests for OU/native/high behavior alignment in the containerized toolchain.
  *(2 commits in `rogerlew/fswepp-docker` during March 2026)*

- **FSWEPP Run ZIP Download API (`fswepp-docker`)** — Added API/CGI endpoint support for downloading zipped FSWEPP (ERMiT) run outputs, including deployment/security notes and downloader-script integration.
  *(2 commits in `rogerlew/fswepp-docker` during March 2026)*

- **Features Export Matrix Cutover** — Hardened features export contracts (temporal/unit/CRS handling), added deterministic artifact packaging, and retired legacy export writer paths.
  *(~25 commits)*

- **Disturbed Lookup Expansion** — Added disturbed lookup live E2E harnessing, extended/base variant persistence in NoDb, and panel workflow refinements for rerun scenarios.
  *(~20 commits)*

- **Accessibility / Section 508 Package** — Published accessibility statement updates, VPAT workspace artifacts, manual `axe` smoke suite, and nightly accessibility workflow coverage.
  *(~12 commits)*

- **GL Dashboard UX Refinements** — Added editable legend ranges, tooltip-only filepath exposure, and RUSLE raster visualization improvements.
  *(~5 commits)*

### Debugging & QA

- Fixed disturbed CSV editor freeze-column and viewport sizing behavior
- Fixed `usersum_doc_link` callback signature and markdown link resolution issues
- Fixed baseline route tests and disturbed lint assertions during extended lookup rollout
- Fixed Caddy routing for published feature-download endpoints
- Fixed GeoParquet writer output and `.geoparquet` browse support
- Fixed MOMM split-county RUSLE selection and escaped RUSLE help text
- Fixed Tenerife soil token replacement regressions and NoDb locale-path expansion
- Fixed Omni contrast rerun behavior for existing scenarios and dependency path checks
- Fixed `totalwatsed3` sediment delivery handling with interchange README reliability updates
- Fixed rq-engine create flow fallback for expired RQ tokens

### Cross-repo: weppcloud-wbt (4 commits, +4.6K / −4)

- Added `RaiseRoads` tool with CRS reprojection and fixture validation
- Added `RusleLsFactor` terrain tool and bindings
- Refreshed WhiteboxTools integration metadata and prompt tracking

### Cross-repo: peridot (7 commits, +2.0K / −73)

- Added shared roads downslope trace core and CLI
- Added watershed Parquet tabular outputs plus manifest generation/slope-bundle summaries
- Updated watershed abstraction binaries and slope-scalar derivation (`zonal median fvslope`)

### Cross-repo: wepp-forest (13 commits, +15.9K / −199)

- Switched default builds to gfortran with pinned rebuild scripts/artifacts
- Widened hillslope/channel ID output fields and fixed watershed-pass metadata parsing
- Added WEPP run comparison tools + tests and daily runoff partitioning updates
- Added instability regression fixtures, refreshed oneAPI builds, and documented ELF loader compatibility gates

---

## Six-Month Totals

| Metric | Oct 2025 | Nov 2025 | Dec 2025 | Jan 2026 | Feb 2026 | Mar 2026 | **Total** |
|--------|----------|----------|----------|----------|----------|----------|-----------|
| Commits (all repos) | 678 | 363 | 284 | 307 | 443 | 326 | **2,401** |
| Lines added (wepppy) | ~304K | ~410K | ~136K | ~744K | ~304K | ~711K | **~2.61M** |
| Lines removed (wepppy) | ~103M* | ~329K | ~56K | ~21K | ~46K | ~13K | — |

\* The 103M deletion figure reflects removal of legacy submodules, deprecated `wepp.out` parsers, and old binary test data. Net new functional code for October is approximately 225K lines.

### Key Themes Across the Period

1. **Interchange & Query Engine** (Oct–Mar): Migration from text-file WEPP parsing to typed Parquet interchange, then continued stabilization/hardening in downstream analytics and export paths.

2. **Containerization & DevOps** (Oct–Mar): Full Docker Compose stack plus ongoing deploy/runtime hardening, secrets wiring, rq-engine integration, and service startup reliability fixes.

3. **Modern Frontend** (Nov–Mar): Leaflet→deck.gl migration followed by GL dashboard refinements (contrast UX, legend controls, RUSLE raster views) and controller usability polish.

4. **Culvert-at-Risk Integration** (Jan–Feb): Culvert-Web-App integration matured with batch finalization queueing, token-auth boundaries, race-condition fixes, and audit/test coverage.

5. **NoDir + Auth Boundary Hardening** (Feb): NoDir reversal completion paired with extensive CSRF/session/cookie-bearer fallback contract hardening and regression coverage.

6. **Omni/Batch/Export Maturity** (Jan–Mar): Continued Omni contrast and batch orchestration improvements, culminating in hardened features-export matrix contracts and legacy export cutover.

7. **RUSLE + Roads Modeling Stack** (Mar): New RUSLE capabilities and Roads NoDb workflow landed with companion tooling in weppcloud-wbt/peridot and UI/dashboard integration.

8. **Usersum as In-Product Documentation** (Mar): Manifest-driven usersum engine and broad guide-link coverage moved documentation closer to where controls are configured.

9. **Accessibility & Compliance Evidence** (Mar): Section 508 statement updates, VPAT workspace packaging, and automated/manual accessibility smoke checks expanded release evidence.

10. **Rust/Fortran Performance Baseline** (Oct–Mar): Continued investment in owned native components (`weppcloud-wbt`, `peridot`, `wepp-forest`) for geometry, roads, and stable WEPP binary workflows.

---

## Updating This Document

To extend this log for additional months, use the following approach with Claude Code or any git-capable environment.

### 1. Gather commit messages

For each repository, pull the one-line log for the target month:

```bash
# Adjust --after and --before for the target month
git -C /workdir/wepppy      log --after="2026-01-31" --before="2026-03-01" --oneline --no-merges
git -C /workdir/weppcloud-wbt log --after="2026-01-31" --before="2026-03-01" --oneline --no-merges
git -C /workdir/peridot      log --after="2026-01-31" --before="2026-03-01" --oneline --no-merges
git -C /workdir/wepp-forest  log --after="2026-01-31" --before="2026-03-01" --oneline --no-merges
```

### 2. Gather LOC statistics

Aggregate insertions/deletions per repo per month:

```bash
git -C /workdir/wepppy log --after="2026-01-31" --before="2026-03-01" --no-merges --shortstat --format="" \
  | awk '{f+=$1; i+=$4; d+=$6} END {printf "Files: %d, +%d, -%d\n", f, i, d}'
```

Commit count:

```bash
git -C /workdir/wepppy log --after="2026-01-31" --before="2026-03-01" --oneline --no-merges | wc -l
```

### 3. Identify LOC outliers

Large test fixtures, generated assets, or scaffolds inflate LOC counts. Find commits with unusually high insertions to annotate them:

```python
# Run via: python3 -c "..."
import subprocess
result = subprocess.run(
    ['git', '-C', '/workdir/wepppy', 'log',
     '--after=2026-01-31', '--before=2026-03-01',
     '--no-merges', '--oneline', '--shortstat'],
    capture_output=True, text=True)
lines = result.stdout.strip().split('\n')
i = 0
while i < len(lines):
    if lines[i] and not lines[i].startswith(' '):
        commit = lines[i]
        if i+1 < len(lines) and 'changed' in lines[i+1]:
            stat = lines[i+1].strip()
            for p in stat.split(','):
                if 'insertion' in p and int(p.strip().split()[0]) > 10000:
                    print(f'  {commit}  ({stat})')
            i += 2; continue
    i += 1
```

### 4. Document structure

Each month should follow this template:

```markdown
## Month Year

### Features
- **Feature Name** — Plain-language description of what it does and why it matters.
  *(~N commits)*

### Debugging & QA
- Fixed [specific bug description]

### Cross-repo: repo-name (N commits, +X / −Y)
- Summary of changes
```

### 5. Update the summary table and totals

Add a column for the new month in the Summary table at the top and update the Four-Month Totals section (rename it as the range grows).

### Repositories

| Repository | Path | Description |
|------------|------|-------------|
| wepppy | `/workdir/wepppy` | Core WEPPcloud application — Python backend, Flask/FastAPI services, JS frontend, Docker infrastructure |
| weppcloud-wbt | `/workdir/weppcloud-wbt` | WhiteboxTools fork — Rust geospatial binaries for channel delineation, hillslope profiling, raster ops |
| peridot | `/workdir/peridot` | Rust CLI tools for topographic analysis — sub-field abstraction, flowpath generation, DEM processing |
| wepp-forest | `/workdir/wepp-forest` | Fortran WEPP model source — hillslope and watershed erosion simulation binaries |
