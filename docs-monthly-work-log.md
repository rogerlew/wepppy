# Monthly Work Log: May 2025 – September 2026

Retroactive summaries of WEPPpy and companion-repository development activity by month, constructed from git history. Counts exclude merge commits. July–September 2026 uses fetched remote history and the explicit branch scope recorded under [Updating This Document](#updating-this-document).

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

## April 2026

### Features

- **Usersum Expansion + Searchable Docs UX** — Expanded usersum end-user coverage (climate options, roads, run-results, model references), linked controls into docs, and shipped manifest-driven search snippets with improved navigation/role filtering.
  *(~120 commits)*

- **Geneva (WildCat) Module Delivery** — Moved Geneva HRU preprocessing into native kernels, added storm-shape/CN/frequency workflows, delivered interactive summary/report contracts, and completed staged WP closures for fixtures, routes, RQ wiring, and docs.
  *(~70 commits)*

- **RQ-Engine Controller-State + Operator APIs** — Added setup/readiness/orchestration discovery surfaces, strengthened controller-state/auth/concurrency contracts, and aligned operator-facing docs/roadmaps around canonical APIs.
  *(~60 commits)*

- **Shape Converter + Async Landuse Mapping** — Implemented inspect/convert pipeline hardening, parser containment and CI gates, then shifted landuse mapping mutation flows into async rq-engine execution with runtime safety checks. Provides secure shapefile upload capability.
  *(~40 commits)*

- **MOFE Optimization Sprint** — Optimized MOFE landuse/disturbed execution paths (process-pool synthesis, `wepppyo3` pair-count/map-assignment acceleration), added closure-audit tooling, and hardened `mofe_max_ofes`/mapping persistence contracts.
  *(~18 commits)*

- **WEPP Binary Release Cadence + Closure Audits** — Repeated WEPP binary vendor/update cycles (`wepp_260409` through `wepp_260430`) with provenance checks, totalwatsed3/hillslope closure-audit tooling, and climate guardrails for observed/noaa workflows.
  *(~70 commits)*

- **Roads Workflow Iteration** — Added roads map drilldown/overlay parity and advanced stepwise outslope unrutted/rutted replacement flows, including PASS token normalization and ag-fields CRS tolerance.
  *(~20 commits)*

- **Accessibility and Governance Evidence** — Added Section 508 statement artifacts, VPAT workspace deliverables, and additional security/governance package gate coverage.
  *(~15 commits)*

### Debugging & QA

- Fixed NoDb cache signature regressions that could overwrite fresh `wepp_bin` state on same-signature rewrites
- Fixed `totalwatsed3` precipitation/runoff closure accounting and added optional storage-term handling
- Fixed repeated completion dispatch on identical job IDs and guarded WEPP interchange post-stage queue dependencies
- Fixed climate enqueue/observed-year edge cases and added deterministic NOAA Atlas14 retry/backoff coverage
- Fixed legacy arc-export AshPost lookup and multiple MOFE persistence/overflow edge cases
- Fixed upload error-envelope consistency while removing unsafe message-based size fallback checks
- Fixed rq-engine propagation gaps for WEPP advanced options and hardened operator bootstrap/discovery flows
- Fixed usersum `src/raw` canonical-path auth bypass
- Fixed GL dashboard simulation-year date normalization and unitized numeric sorting behavior
- Fixed disturbed CSV editor freeze-column/viewport behavior and RAP recovery indexing for two-digit fire dates

### Cross-repo: weppcloud-wbt (25 commits, +8.0K / −414)

- Implemented and productionized IFOLP (Iterative First-Order Link Prune): parser/kernel contracts, max-junction support, cycle/boundary hardening, regression fixtures, wrapper smoke tests, and release docs
- Built and published IFOLP-enabled WBT binaries with integration/runbook updates for WEPPpy cutover

### Cross-repo: peridot (4 commits, +1.6K / −189)

- Refined watershed abstraction flowpath mapping/outputs and fixed full-suite regressions
- Repositioned project documentation and removed legacy Rust CI workflow

### Cross-repo: wepppyo3 (20 commits, +10.2K / −456)

- Delivered Geneva-native kernels (rainfall-excess/CN, UH/frequency/storm-shape paths) and moved HRU map preparation into Rust hot paths
- Added HRU-local peak runoff outputs, MOFE slope segmentation/map assigner APIs, and raster key-pair count contracts
- Refreshed Py3.12 release artifacts/provenance and module catalog docs

### Cross-repo: wepp-forest (89 commits; large binary/evidence churn)

- Ran a rapid WEPP release train (`wepp_260409` through `wepp_260430`) with repeated watershed/hillslope binary rebuilds and changelog/stakeholder-brief synchronization
- Modernized compiler posture around strict SIGFPE trapping (no physics rewrite) to eliminate silent numeric corruption and improve cross-platform determinism/debuggability
- Operationalized formal ablation campaigns with incident packages (`incident.md`, `matrix.csv`, `notes.md`, reproducible artifact manifests/checksums) for every production failure signature
- Ran explicit parity validation lanes against canonical `wepp_dcc52a6` and IFX Windows witness builds, including raw-file and tolerance-based drift checks before release promotion
- Closed targeted guard campaigns across both watershed and hillslope paths: frost-layer indexing (`locate`), dry-year/event ratios (`wshpas`), frost-season soil-water math (`saxfun`), impermeable-boundary seepage (`perc`), hydraulic calibration domains (`watbal_hourly`/`watbal`), and Penman-Monteith crop-stress denominator (`evappm`)
- Added optional WAT storage terms plus Gregorian/leap-day handling corrections in release binaries (`wepp_260429`/`wepp_260430`) and synchronized downstream vendoring
- Scaled proactive generative fuzzing/single-OFE pressure campaigns with climate/slope stratification and positive-control sensitivity checks to convert recurring SIGFPE classes into regression-gated hardening milestones

### Cross-repo: openWEPP (0 commits)

- Included in the April all-repo scan; no April 2026 activity appears in local history, and the first non-merge commits in `/workdir/openWEPP` begin on 2026-05-11

---

## May 2026

### Features

- **RUSLE Rock/Soil Parameterization** — Added conservative POLARIS K gap fill, optional CFVO K adjustment, cosurffrags-first rock proxies, RAP/SBS rock partitioning, and UI/docs contracts for interpreting surface-rock effects.
  *(~25 commits)*

- **Feature Maturity and Access Governance** — Introduced the feature/config maturity registry, beta visibility gating, sponsor/access governance docs, and universal parameterization ADR provenance requirements.
  *(~20 commits)*

- **WEPP Binary, HBP, and Sidecar Integration** — Continued WEPP binary vendoring through `wepp_260514`, added HBP pass-family support, schema2 sidecar handling, optional interception-storage parsing, and binary-contract-aware watershed run prompts.
  *(~35 commits)*

- **MOFE, Disturbed, and Omni Reliability** — Advanced MOFE closure auditing and triage, fixed runtime mulch-key rebuilds, added per-scenario Omni treatment filters, and hardened disturbed nodata/BAER remapping behavior.
  *(~20 commits)*

- **NoDb/RQ/Culvert/Export Hardening** — Refactored map handling, hardened stale-write and lock-conflict paths, invalidated inherited WEPP markers on fork, expanded features-export tests, and tightened rq-engine/session payload behavior.
  *(~25 commits)*

- **Usersum, Profiles, and Research Artifacts** — Clarified usersum language around model behavior and governance, refreshed profile/UI bundle assets, and added the I-CREWS poster specification and supporting figures.
  *(~15 commits)*

### Debugging & QA

- Fixed observed CLIGEN silent-pass warning persistence and climate validation messages
- Fixed stream-order fallback regressions, disturbed nodata leakage, and WBT/Topaz set-outlet validation
- Fixed WEPP bootstrap summary deferral for stale job states and detached config fallback coverage
- Fixed landuse lock-conflict error surfacing, culvert batch stale-write races, and inherited WEPP job markers on fork
- Fixed SSURGO quote serialization and clarified `kslast` bedrock-control conductivity units
- Fixed RUSLE RAP endpoint protocol, RAP year discovery, K-factor gap fills, and residual no-flow LS routing cells
- Fixed CI Redis bind collisions, docs-quality size-gate assertions, and detached Ron `fetch_dem` fixtures
- Replaced the PFDF Atlas14 dependency with the in-repo NOAA client

### Cross-repo: weppcloud-wbt (3 commits, +291 / −77)

- Hardened `RusleLsFactor` with bounded no-flow fallback behavior, residual no-flow masking, and refreshed release artifacts
- Removed tracked Python cache output from the WBT tree

### Cross-repo: peridot (0 commits)

- No May 2026 activity in local history

### Cross-repo: wepppyo3 (9 commits, +5.2K / −744)

- Added optional `InterceptionStorage` support in hill WAT parsing and deterministic `raster_characteristics` API ordering
- Implemented HBP reader/pass-family dispatch, HBP schema2 dual-major parser support, and direct negative-path parser tests
- Migrated interchange crates from `arrow2`/`parquet2` to `arrow-rs` and refreshed Py3.12 release artifacts

### Cross-repo: wepp-forest (343 commits, +26.4M / −24.5K)

- Continued the WEPP release train through `wepp_260514` and `wepp_260516fc1`, including HBP v2/schema2 sidecar support and FC recertification artifacts
- Executed watershed-routing modernization across WB33-WB36, covering channel geometry, impoundment routing, Muskingum-Cunge/time-of-concentration paths, publish-balance retirement, and peak-summary outputs
- Expanded water-balance, winter, soil, snow/frost, ET, erosion, and channel-sediment closure campaigns with contract-derived vectors and replay evidence
- Added formal authority, science-contract, ablation, and release-gate documentation for the Fortran modernization stream
- Carried large binary/evidence churn from release artifacts, ablation packages, and parity/replay fixture publication

### Cross-repo: openWEPP (381 commits, +542.7K / −49.4K)

- Launched the Rust openWEPP workspace with governance, non-clean-room provenance policy, reference ingestion, and architecture-first science-contract strategy
- Authored the initial science-contract corpus and work-package program for climate, water balance, snow/freeze, runoff partitioning, evaporation, percolation, subsurface hydrology, soil, residue, hydraulics, sediment, routing, irrigation, impoundments, plant growth, and system behavior
- Implemented the early hillslope CLI/runner surface, Python wrapper, WAT parquet output, integration tests, and legacy comparison suite
- Ported and staged kernels across water balance, ET, percolation, lateral drainage, peak runoff, watershed channel/impoundment routing, erosion, frost, and snow workflows
- Added HBP serializer/parser work, release-gate automation, authority-stack tests, fixture provenance checks, and Apache-2.0 relicensing from inception

---

## June 2026

### Features

- **SSURGO Project Cache and Reclaimed Soils** — Added project-local SSURGO SQLite caching, cache metadata sidecars, an ADR for cache behavior, geospatial metadata authoring guidance, and reclaimed-soil fallback handling.
  *(~10 commits)*

- **Browse, Download, and Parquet UX Hardening** — Added a dedicated archive download service, lazy parquet D-Tale backend, Arrow-to-pandas browse-path removal, themed browse tree/parquet preview UI, and clearer download documentation.
  *(~15 commits)*

- **Omni Sediment Inversion Investigation** — Documented the honeyed-marathoner sediment inversion, including version-stable reproduction, slope/aspect/runoff partitioning, canopy evaporation/saturation-excess findings, storm timing, SBS raster preservation, and follow-on frost sensitivity notes.
  *(~15 commits)*

- **ERMiT and RQ-Engine Export Flow** — Restored ERMiT export in Run Results, moved ERMiT export through rq-engine, and proxied legacy ERMiT downloads through rq-engine.
  *(3 commits)*

- **Batch, Climate, and Geneva Reliability** — Hardened batch runner retry durability, normalized Geneva NOAA frequency rows, normalized observed Daymet radiation bounds for CLI publication, and added Treasure Valley hydropower-to-USGS gauge validation.
  *(~8 commits)*

- **Forest Management and Land/Soil Inputs** — Added deciduous and mixed forest managements, documented forest management hemisphere limits and GDD senescence investigations, normalized RAP_TS management cover fractions, and synced disturbed land-soil lookup data.
  *(~8 commits)*

- **WEPPcloud Paper and Research Artifacts** — Advanced the ACG 2026 manuscript planning, abstract, figures, SocketIO framing, highlights, bibliography, operational lessons narrative, and JOSS submission tracking.
  *(~12 commits)*

### Debugging & QA

- Fixed OMNI SBS raster preservation and mulch lookup ordering
- Fixed map fly-to parsing for Unicode minus values
- Fixed observed Daymet radiation bounds and normalized Daymet radiation for CLI publication
- Fixed ERMiT export availability in Run Results and routed export/download paths through rq-engine
- Fixed batch runner retry durability and added a durability work package
- Added totalwatsed3 interception-flux closure support consuming openWEPP interception flux
- Added SSURGO reclaimed-soil fallback and project-cache metadata safeguards
- Added UI Lab keyboard-focus hardening for the light landing page

### Publication Tracking

- **JOSS submission** — Opened [openjournals/joss-reviews#10701](https://github.com/openjournals/joss-reviews/issues/10701) on 2026-06-11 for `[PRE REVIEW]: weppcloud-wbt: TOPAZ-style watershed parameterization tools for WEPPcloud workflows in WhiteboxTools`; initial pre-review metadata lists `weppcloud-wbt` version `2.3.0.post2`, managing EiC Kristen Thyng, and editor/reviewers pending.

### Cross-repo: weppcloud-wbt (65 commits, +19.1K / −603)

- Added weppcloud-wbt paper/JOSS artifacts, WEPPcloud workflow framing, figures, bibliography updates, claim-test matrix, and Zenodo DOI citation
- Built PyPI packaging and release machinery: `whitebox_tools` shim package, wheel inspection, Linux auditwheel repair, Windows DLL/PROJ bundling, macOS/Linux/Windows validation reports, and manual publish workflow
- Expanded integration coverage for FindOutlet, HillslopesTopaz, FVSlope, stream-junction identifiers, RaiseRoads, PruneStrahlerOrder, UnnestBasins, ClipRaster, watershed, and VRT variants
- Refreshed README/end-user docs for WEPPcloud-owned tools and upstream attribution, added OSS maintenance artifacts, CI workflows, and a 2.3.0.post2 changelog release

### Cross-repo: peridot (0 commits)

- No June 2026 activity in local history

### Cross-repo: wepppyo3 (0 commits)

- No June 2026 activity in local history

### Cross-repo: wepp-forest (0 commits)

- No June 2026 activity in local history; WEPP engine modernization work during June was concentrated in `/workdir/openWEPP`

### Cross-repo: openWEPP (666 commits, +12.2M / −224.2K)

- Advanced hydrology physics closure across HPHYS/WB lanes: FC/WP theta authority, lateral/drainage, percolation, PMET demand, snowpack state, snowmelt infiltration, storage-budget lineage, and unit-boundary governance
- Closed the first single-OFE water-balance rung by publishing daily interception flux to `H.wat`, adding totalwatsed3 companion support, and formalizing conservation/publication acceptance rules
- Executed MOFE and watershed closure work: per-OFE state architecture, sequential OFE lane execution, Q/QOFE geometry validation, openWEPP-native runvol, totalwatsed3 CLI ownership, and watershed routed-output milestones
- Built the array-native/direct runtime path: indexed runtime surfaces, HillslopeDayFrame architecture, direct publication/runtime spans, direct WAT/PMET producers, winter-column snow/frost state, and RSS/performance characterization
- Expanded snow/frost fidelity work with frost-depth heat-flow diagnostics, ksflag frost activation, observed frost fixtures, SNOTEL snow-density rubrics, Harder-Pomeroy phase default activation, multilayer snow/frost insulation gates, and dynamic litter/residue frost-surface coupling
- Continued governance and maintainability work: ADRs, ROADMAP and backlog tracking, science-contract restructuring, required-reading budgeting, mechanical refactor guidance, Rust line-count governance, CQR/CRAP complexity burndown, and kernel-boundary typing/deletion planning

---

## July 2026

### Features

- **AgFields Watershed Workflow** — Added the runs-page UI, backend readiness checks, management synthesis, weighted subfield PASS delivery, channel connectivity, and watershed routing schemes. Added parent-job orchestration, interrupted-job recovery, and subfield interchange publication; AgFields remained an internal beta.

- **Native WEPP Interchange Cutover** — Moved hillslope WAT and the remaining WEPP interchange writers to WEPPpyo3, retired the Python fallback, bounded result backlogs and multi-OFE aggregation, and made parser loss and native-library provenance observable.

- **SSURGO Intelligent Fallback** — Built empirical masked-valid and holdout cohorts, evaluated local MUKEY candidates and ranking rules, then implemented intelligent fallback with categorical raster support, candidate metadata, concurrent publication checks, and Parquet provenance.

- **PATH-CE v2** — Resynchronized the upstream cost-effectiveness solver and completed its Parquet pipeline, optimization UI, Quarto report, and end-user quick start.

- **Pure UI Contracts and Browser Diagnostics** — Audited run controls, reports, account/admin pages, and job consoles against rendered UI contracts. Added live browser diagnostics and session reset, hardened remembered login and same-origin checks, and introduced account preferences with autosave and active-user ownership.

- **WBT Conditioning and Run Visibility** — Integrated TOPAZ-compatible DEM conditioning, surfaced conditioning diagnostics in channel summaries, rejected unresolved bounded breaches, and added project TTL deletion schedules and queue-specific active-job views.

### Debugging & QA

- Fixed the short-ton-to-tonne unit conversion factor
- Fixed Ash model selection propagation, static ash transport, and readonly rendering
- Fixed Omni mod-state synchronization, contrast sidecar preservation, and inherited WEPP executable selection
- Hardened partial-year observed climate builds and SSURGO field-capacity/wilting-point and Rosetta silt inputs
- Fixed channel smoothing persistence, fork destination readiness, and ERMiT export retry behavior
- Vendored WEPP releases through `wepp_260727` for output precision, SOIL OFE overflow, and HBP area indexing repairs; the default-lineage correction and withdrawal followed in August

### Cross-repo: weppcloud-wbt (12 commits, +5.6K / −411)

- Added `TopazConditionDem` with TOPAZ parity checks, contained runtime execution, and timeout enforcement through process exit
- Added unresolved-depression failures and conditioning diagnostic sidecars; fixed FillDepressions edge outlets and a worker race
- Removed mutable WBT settings from version control and documented conditioning controls

### Cross-repo: peridot (2 commits, +590 / −11)

- Added a subfield channel-connectivity CLI and per-subfield connection details for AgFields watershed routing

### Cross-repo: wepppyo3 (31 commits, +9.2K / −350)

- Added weighted AgFields PASS combination, explicit slope breakpoints, native interchange writers, direct WAT Parquet output, and subfield interchange writers
- Hardened atomic publication, UTF-8 Arrow batches, parser diagnostics, and widened deep-percolation, annual LOSS area, and SOIL OFE parsing
- Added clustered local MUKEY candidate/geometry kernels and bounded categorical raster support, with refreshed Python 3.12 release artifacts

### Cross-repo: wepp-forest (18 commits, +1.86M / −1.7K)

- Raised hillslope management capacity for AgFields, repaired soil cursor alignment beyond layer capacity, and added native Apple Silicon build support
- Improved deep-percolation and hillslope-area output precision, repaired watershed SOIL OFE overflow and HBP hillslope-area indexing, and published July release binaries across the release branches
- Retained the carved-letter MOFE closure root-cause assessment on the subsequently abandoned kernel branch; repeated AgFields regression fixtures across release branches dominate the monthly line additions
- Superseded the water-balance kernel brief; counts cover the deduplicated branch set recorded below, including experimental history

### Cross-repo: openWEPP (1,254 commits, +10.43M / −139.1K)

- Activated native single-OFE sediment continuity, extended hydrograph-resolved erosion and inter-OFE sediment handoff, ported enrichment calculations, and corrected ground-cover initialization and erosion-cover derivation
- Added native forest landuse and generalized GSI canopy phenology, coherent canopy-height publication, and calibration/reproduction studies
- Advanced hourly HBP watershed consumption and retired the old watershed runtime
- Investigated snow-surface energy balance, sub-canopy longwave exchange, thin-pack thermal behavior, and layer reconciliation
- Expanded science assurance reports, coverage/complexity remediation, and test orchestration; later retired the legacy planner/TESTGATE control plane and introduced an advisory workplan linter

---

## August 2026

### Features

- **Project-Owned Configuration and Config Builder** — Implemented project config readers, registry/resolver, preset snapshots, capability enforcement, Builder API/UI, update workflows, and lifecycle integrity. Added model/binary options, locale authority, automatic validation, and Forest acceptance evidence; production cutover preparation continued into September.

- **WEPPcloud Runtime and Rendering Backends** — Published runtime and auxiliary-service images, hydrated LFS assets, added a self-hosted GHCR builder, and implemented WEPPcloudR execution backends and Kubernetes control-plane adapters. Repaired root-squashed NFS rendering paths, writable intermediates, and offline report assets.

- **Sessions and Deployment Reliability** — Migrated session-cookie ownership with mixed-version continuity, exercised OAuth/remember/logout and token-revocation canaries, and hardened CAP deployment, targeted web-service deployment, and RQ fence renewal.

- **Batch WATAR and Fork Recovery** — Integrated WATAR into Batch Runner, validated WATAR-only retries, added an Omni-resetting fork option, serialized fork/archive jobs, and hardened Omni symlinks, empty-state forks, and NFS-safe quarantine.

- **RQ Status and Dependency Recovery** — Added advisory queue position, canonical UUID job identifiers, fork-worker-aware status, deferred-submission retries, and strict dependency recovery. Repaired Omni finalizers that could remain deferred indefinitely.

- **Soil, SBS, and Climate Reliability** — Added EU disturbed-soil replay/quality validation, adopted the USGS SBS palette and explicit class transport, exposed ESDAC rejection reasons, and implemented climate multiple-build finalization locking.

- **Peak-Flow Investigations** — Retained Stevens Canyon/Palisades ET attribution, Topanga runoff calibration, mutation-census evidence, and a standalone peak-flow report. Documented saturation-return peak-flow limitations and continued the multi-site audit.

### Debugging & QA

- Restored the default WEPP release lineage, vendored `wepp_260803`, and withdrew `wepp_260727` binaries
- Derived PASS format from release sidecars and recognized completed watershed interchange
- Fixed Batch Omni multi-OFE treatment propagation and batch climate-station drift
- Fixed browser RQ account identity, Config Builder ownership, and stored locale/capability compatibility
- Repaired SBS rendering without unstable GDAL lookup tables and added accessible table overflow cues
- Replaced run-inventory globs with Parquet footers and optimized initial Bootstrap Git repositories
- Replaced the f-esri dependency with OpenFileGDB

### Cross-repo: weppcloud-wbt (2 commits, +35 / −21)

- Updated fork-tool documentation and backfilled the post-submission changelog

### Cross-repo: peridot (0 commits)

- No August 2026 non-merge commits on the fetched `origin/main` history

### Cross-repo: wepppyo3 (2 commits, +206 / −44)

- Fixed widened hillslope SOIL parsing and aligned SBS palette/NoData export

### Cross-repo: wepp-forest (6 commits, +2.8K / −156)

- Ported SOIL OFE output width to the default release lineage and published `wepp_260803`
- Added an isolated peak-flow event observer on the investigation branch, hardened its contract, and scoped the next SURDRA kinematic-wave study to hourly routing; this was investigation work, not a released routing repair

### Cross-repo: openWEPP (751 commits, +1.22M / −99.2K)

- Advanced coupled C3 woody vegetation, canopy radiation, carbon/nitrogen state, phenology storage transfers, and root-zone hydraulic integration
- Added native half-hour forcing and persisted direct-hydrology restart transactions, with restart equivalence and rollback checks
- Established hourly peak-runoff authority and transactional five-minute water-balance diagnostics
- Expanded snow/land-surface-energy coupling, persistent surface-liquid state, routed runon, frozen litter, exact soil enthalpy carry, and adaptive Stage 3 microstepping
- Evaluated SNOTEL/ERA5 forcing and snow accumulation/energy diagnostics; retained numerical and performance holds for unresolved coupled-solver cases

---

## September 2026

### Features

- **Postfire Debris-Flow Preview** — Implemented Staley M1/M3 watershed workflows, dNBR normalization, Horn-slope/SBS intersection, soil-depth and rainfall adapters, source preparation, model selection, RQ execution, and preflight status. Added saved likelihood reports, fine-earth Kf handling, rainfall-response curves, and user guidance; the feature was explicitly marked preview.

- **Native Summaries and Raster Weighting** — Required native WEPPpyo3 producers for totalwatsed3, hillslope water balance, and AshPost. Added project-grid area-weighted `kslast` for ordinary and MOFE soils and vendored the Peridot centroid projection correction.

- **MOFE Artifact Integrity and Omni Treatments** — Added per-OFE hillslope clipping and repaired landuse, fire, canopy, and ground-cover propagation into generated management files. Validated eight production scenario repairs, corrected treatment segment eligibility, preserved omitted API settings, and added 30/50% and 60/70% thinning variants.

- **File and Cache Freshness** — Bound NoDb hydration, CLI Parquet, raster summaries, D-Tale datasets, scientific reports, feature exports, and Geneva publication to verified input content. Added uploaded-SBS byte receipts and event-bound profile replay, with generated-artifact validation requirements.

- **Batch and Climate Throughput** — Split batch hillslope and watershed execution into dependent RQ tasks, coordinated GridMET acquisition through Redis FIFO admission, repaired climate/RAP and Daymet/PRISM contention, and scaled continuous watershed timeouts using simulation years and hillslope counts.

- **Project Configuration and Run Catalog** — Added project config run summaries and canonical stored-config routing, repaired Builder SBS uploads, and implemented a rebuildable PostgreSQL run catalog with staged Forest cutover and forest1 shadow-rollout evidence.

- **Research and User Inputs** — Added single user-defined landuse/soil support and `7777` soil-format upload validation, retained fire-validation and Omni response analyses, drafted the Omni scenarios/contrasts paper, and published historical WEPPcloud usage charts.

### Debugging & QA

- Fixed postfire upload/status and enqueue-handoff races, preserved active CLI identity through hard-link preparation, and published results directly in the module output directory
- Preserved acquired Daymet source Parquet and configuration-owned climate scale maps
- Fixed DEVAL worker identity/shared-path permissions and verified production-worker rollout
- Released canceled execution-directory locks only after writers stopped; repaired GridMET queue waiting and Redis transport recovery
- Restored yearly runoff reporting and all-years report links, run-sync replacement, and visible project-creation failure diagnostics
- Fixed disabled-input contrast across bundled themes and elevated-user session authorization
- Preserved archive directory permissions, corrected disturbed thinning-soil lookup, and repaired Omni contrast EBE dependencies

### Cross-repo: weppcloud-wbt (4 commits, +16.4K / −151)

- Optimized least-cost breaching and added a runtime concurrency override
- Added paired Staley terrain fixtures, upstream-relief analysis and a resolution study, plus Horn slope and uncertainty-preserving SBS intersection

### Cross-repo: peridot (3 commits, +367 / −37)

- Corrected metadata centroids with pointwise PROJ transformation and documented the projection contract
- Declared the MIT license

### Cross-repo: wepppyo3 (13 commits, +233.6K / −238)

- Added bounded native totalwatsed3, hillslope water-balance summaries, and AshPost with fixture/RQ acceptance and refreshed release artifacts
- Added a generic projected-cell area-weighted raster mean with coverage/default handling
- Fixed native SBS NoData handling; retained validation fixtures account for much of the insertion count

### Cross-repo: wepp-forest (0 commits)

- No September 2026 non-merge commits in the fetched branch set used for this update

### Cross-repo: openWEPP (249 commits, +48.05M / −59.8K)

- Most line additions are retained solver captures, diagnostics, and review/recovery evidence, not new runtime code
- Investigated Stage 3 throughput, memory, residual/Jacobian evaluation, and physical-pipeline execution; retained unresolved accuracy/runtime holds
- Simplified agent context and evidence handling and introduced a directory-format science-contract checker, including land-surface-energy contract migration
- Advanced WB14 native capture, reader, restart/restoration diagnostics, and bounded promotion controls with explicit evidence of remaining blockers
- Evaluated cold-canopy coupled solvers, trust-region controls, finite-precision behavior, BVLS/face-solve refinements, and physical-domain failures; September ended with reduction/cadence investigations blocked rather than a qualified deployable solver

---

## Twelve-Month Totals (October 2025 – September 2026)

| Metric | Oct 2025 | Nov 2025 | Dec 2025 | Jan 2026 | Feb 2026 | Mar 2026 | Apr 2026 | May 2026 | Jun 2026 | Jul 2026 | Aug 2026 | Sep 2026 | **Total** |
|--------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|-----------|
| Commits (all repos) | 678 | 363 | 284 | 307 | 443 | 326 | 659 | 880 | 802 | 1,590 | 1,036 | 532 | **7,900** |
| Lines added (wepppy) | ~304K | ~410K | ~136K | ~744K | ~304K | ~711K | ~957K** | ~58K | ~71K | ~167K | ~588K | ~1.15M | **~5.60M** |
| Lines removed (wepppy) | ~103M* | ~329K | ~56K | ~21K | ~46K | ~13K | ~16K | ~4K | ~2K | ~26K | ~14K | ~16K | — |

\* The 103M deletion figure reflects removal of legacy submodules, deprecated `wepp.out` parsers, and old binary test data. Net new functional code for October is approximately 225K lines.
\** April insertions include a 713K-line ablation evidence commit plus repeated WEPP binary vendoring; functional logic churn is materially smaller than raw LOC.

July–September counts by repository:

| Repository | Jul 2026 | Aug 2026 | Sep 2026 | **Quarter total** |
|------------|----------|----------|----------|-------------------|
| wepppy | 273 | 275 | 263 | **811** |
| weppcloud-wbt | 12 | 2 | 4 | **18** |
| peridot | 2 | 0 | 3 | **5** |
| wepppyo3 | 31 | 2 | 13 | **46** |
| wepp-forest | 18 | 6 | 0 | **24** |
| openWEPP | 1,254 | 751 | 249 | **2,254** |
| **All six repositories** | **1,590** | **1,036** | **532** | **3,158** |

Raw line counts include fixtures, generated reports, and retained experimental evidence. WEPPpy's August additions include a 201.5K-line Topanga investigation commit; September includes a 307.8K-line Omni paper/analysis commit and several large validation records. openWEPP's September additions are dominated by solver evidence, including individual 5.25M- and 4.92M-line captures. These figures measure repository churn, not functional code growth. Earlier monthly figures are preserved from the previous update.

### Key Themes Across the Period

1. **Interchange & Query Engine** (Oct–Jun): Migration from text-file WEPP parsing to typed Parquet interchange, followed by sustained closure audits, export hardening, HBP sidecar support, lazy parquet browse paths, and downstream reliability fixes.

2. **Containerization & DevOps** (Oct–Jun): Full Docker Compose stack plus ongoing deploy/runtime hardening, secrets wiring, rq-engine integration, dedicated archive downloads, and service startup reliability fixes.

3. **Modern Frontend** (Nov–Jun): Leaflet→deck.gl migration followed by GL dashboard refinements (contrast UX, legend controls, date/unit handling), RUSLE panel tuning, themed browse previews, UI Lab keyboard-focus fixes, and controller usability polish.

4. **Culvert-at-Risk Integration** (Jan–Feb): Culvert-Web-App integration matured with batch finalization queueing, token-auth boundaries, race-condition fixes, and audit/test coverage.

5. **NoDir + Auth Boundary Hardening** (Feb): NoDir reversal completion paired with extensive CSRF/session/cookie-bearer fallback contract hardening and regression coverage.

6. **Omni/Batch/Export + MOFE Maturity** (Jan–Jun): Continued Omni contrast/batch orchestration improvements plus MOFE throughput hardening, closure audits, sediment-inversion investigations, and contract stabilization, culminating in hardened features-export matrix contracts and legacy export cutover.

7. **RUSLE + Roads Modeling Stack** (Mar–May): RUSLE and Roads NoDb workflows landed, then advanced with drilldown overlays, outslope flow refinements, companion native tooling support, and conservative rock/soil parameterization.

8. **Usersum as In-Product Documentation** (Mar–Jun): Manifest-driven usersum engine expanded with role-aware discovery, richer search snippets, broad control-to-doc linking, governance/frost-gating clarifications, and paper-facing operational narratives.

9. **Accessibility & Compliance Evidence** (Mar–Jun): Section 508 statement updates, VPAT workspace packaging, feature governance policy, keyboard-focus fixes, and automated/manual accessibility smoke checks expanded release evidence.

10. **Rust/Fortran Performance Baseline** (Oct–Jun): Continued investment in owned native components (`weppcloud-wbt`, `peridot`, `wepppyo3`, `wepp-forest`, `openWEPP`) for geometry, roads, Geneva kernels, WEPP binary workflows, WBT packaging, and the Rust reimplementation path.

11. **WEPP Incident-Ablation Discipline** (Apr–Jun): `wepp-forest` and `openWEPP` established milestone-driven ablation/fuzzing evidence, policy gates, release traceability, and closure-campaign mechanics as a recurring hardening workflow.

12. **openWEPP Launch and Runtime Maturity** (May–Jun): `/workdir/openWEPP` became an active Rust reimplementation workspace with science contracts, runner/CLI surfaces, legacy comparison lanes, early hydrology/erosion/watershed kernels, direct runtime work, and snow/frost fidelity programs.

13. **AgFields and Native Processing** (Jul–Sep): Agricultural watershed routing and subfield interchange expanded alongside the WEPPpyo3-only interchange cutover, native aggregate producers, and area-weighted raster kernels.

14. **Configuration and Operational Recovery** (Jul–Sep): Pure UI audits, account preferences, Config Builder and locale authority, session migration, rendering backends, RQ recovery, and a rebuildable run catalog strengthened project lifecycle behavior.

15. **Scientific Inputs and Artifact Correctness** (Jul–Sep): SSURGO fallback studies, Staley postfire preview, MOFE management propagation, file-content freshness, and generated-artifact validation tied model execution to inspectable inputs and outputs.

16. **Native Physics and Bounded Investigations** (Jul–Sep): openWEPP advanced erosion, vegetation, restart, and coupled snow/energy work while recording unresolved solver and throughput limits; WEPP peak-flow investigations retained attribution evidence and explicit release-lineage distinctions.

---

## Updating This Document

To extend this log for additional months, use the following approach with Claude Code or any git-capable environment.

### 1. Gather commit messages

Fetch each repository with `git -C <path> fetch origin`, then read its selected
remote refs without switching branches or merging into the checkout. Use explicit
local month bounds on committer dates so boundary-day commits do not leak into the
adjacent month.

The July–September 2026 update fetched all six repositories on 2026-10-07. Sources
were `/home/workdir/<repository>` (the local equivalent of the paths below), with
midnight on each month's first day through 23:59:59 on its last day, at `-0700`
(America/Los_Angeles). Source tips at collection:

| Repository | Remote ref(s) and tip(s) |
|------------|------------------------|
| wepppy | `origin/master` — `e5a6e0b9fc38` |
| weppcloud-wbt | `origin/master` — `a97abb7754a2` |
| peridot | `origin/main` — `6eaa326ef60b` |
| wepppyo3 | `origin/main` — `60ba09905ff4` |
| openWEPP | `origin/main` — `9a640496cc37` |
| wepp-forest | `origin/master` — `2f65506d239b`; `origin/kernelized-abandoned` — `d3949f91a001`; `origin/wepp_260714_agfields` — `4b71c6f5b557`; `origin/wepp_260430_negmeltfix_comparator` — `d7cb2edf2e32`; `origin/feature/peakflow-phase1-observer` — `7cec75b23053` |

WEPP-forest requires several refs because release and investigation work diverged;
its current checkout alone misses July/August work. Pass all five refs to one
`git log` so shared commit IDs count once. Separate cherry-picked commits remain
separate history entries, including repeated fixture additions. Other repositories
use only their listed mainline. A zero means no non-merge commits in that scope,
not proof of inactivity on every possible branch. Use the recorded tips instead of
moving refs to reproduce this update.

```bash
# July example: repeat with August 1–31 and September 1–30 bounds.
month_start="2026-07-01 00:00:00 -0700"
month_end="2026-07-31 23:59:59 -0700"
git -C /workdir/wepppy log origin/master --since="$month_start" --until="$month_end" --oneline --no-merges
git -C /workdir/wepppyo3 log origin/main --since="$month_start" --until="$month_end" --oneline --no-merges
git -C /workdir/weppcloud-wbt log origin/master --since="$month_start" --until="$month_end" --oneline --no-merges
git -C /workdir/peridot log origin/main --since="$month_start" --until="$month_end" --oneline --no-merges
git -C /workdir/openWEPP log origin/main --since="$month_start" --until="$month_end" --oneline --no-merges
git -C /workdir/wepp-forest log origin/master origin/kernelized-abandoned \
  origin/wepp_260714_agfields origin/wepp_260430_negmeltfix_comparator \
  origin/feature/peakflow-phase1-observer \
  --since="$month_start" --until="$month_end" --oneline --no-merges
```

### 2. Gather LOC statistics

Aggregate insertions/deletions per repo per month:

```bash
git -C /workdir/wepppy log origin/master --since="$month_start" --until="$month_end" --no-merges --shortstat --format="" \
  | awk '{for (n=2; n<=NF; n++) {if ($n ~ /^file/) f+=$(n-1); if ($n ~ /^insertion/) i+=$(n-1); if ($n ~ /^deletion/) d+=$(n-1)}} END {printf "Files: %d, +%d, -%d\n", f, i, d}'
```

Match insertion/deletion labels rather than fixed field positions: Git omits the
insertion field on deletion-only commits. Use the same refs and bounds as the
commit count, including the multi-ref WEPP-forest selection.

Commit count:

```bash
git -C /workdir/wepppy log origin/master --since="$month_start" --until="$month_end" --oneline --no-merges | wc -l
```

### 3. Identify LOC outliers

Large test fixtures, generated assets, or scaffolds inflate LOC counts. Find commits with unusually high insertions to annotate them:

```python
# Run via: python3 -c "..."
import subprocess
result = subprocess.run(
    ['git', '-C', '/workdir/wepppy', 'log', 'origin/master',
     '--since=2026-07-01 00:00:00 -0700', '--until=2026-07-31 23:59:59 -0700',
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

Add a column for each new month in the totals table after the monthly entries,
update the sums and repository breakdown, and rename the totals heading as the
range grows. Refresh the title, themes, source refs, and LOC outlier notes. Keep
experimental or blocked work distinct from completed production behavior.

### Repositories

| Repository | Path | Description |
|------------|------|-------------|
| wepppy | `/workdir/wepppy` | Core WEPPcloud application — Python backend, Flask/FastAPI services, JS frontend, Docker infrastructure |
| wepppyo3 | `/workdir/wepppyo3` | Native Rust/PyO3 kernels and interchange substrate used by WEPPpy for high-throughput geospatial/model workflows |
| weppcloud-wbt | `/workdir/weppcloud-wbt` | WhiteboxTools fork — Rust geospatial binaries for channel delineation, hillslope profiling, raster ops |
| peridot | `/workdir/peridot` | Rust CLI tools for topographic analysis — sub-field abstraction, flowpath generation, DEM processing |
| wepp-forest | `/workdir/wepp-forest` | Fortran WEPP model source — hillslope and watershed erosion simulation binaries |
| openWEPP | `/workdir/openWEPP` | Rust reimplementation of the WEPP hillslope and watershed simulation engine |
