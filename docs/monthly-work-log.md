# Monthly Work Log

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

## October 2025 (660 commits)

**Theme: Highest-volume month -- type hints, UI restyling, profile testing, deck.gl map, GL dashboard, theme system, agentic AI manifesto**

### Type Hints & Code Quality
- Comprehensive type hints added to: `topaz.py`, `ron.py`, `landuse.py`, `soils.py`, `watershed.py` (2 parts), `wepp.py`, `climate.py` (118 functions), `disturbed.py`
- MyPy configuration and type hints validation tests
- Stub tooling and `requirements-stubs` build
- `nodb.core` typed; `all_your_base` type updates

### UI Restyling
- Pure CSS control restyling across all modules: outlet, landuse, soils, climate, wepp, ash
- Theme system: feasibility study, VS Code themes, dark mode, high-contrast theme, theme metrics
- UI showcase; standardized data tables; logo style guide with AI generation prompts
- Interface logos updated (US, EU, AU); landing page updates
- OAuth integration: GitHub, Google, ORCID

### deck.gl Map Migration
- 14-phase deck.gl map migration replacing Leaflet: phases 0-14
- Separate slope and aspect overlays; 2D-only map mode
- Subcatchment labels, hillslope flash, channel flash

### GL Dashboard
- Full GL dashboard: landuse, soils, WEPP stats, WEPP yearly, RAP spatial
- Omni scenario support with difference mapping; cumulative contribution curves
- OpenET integration: monthly slider, time series, functional map layer
- Year slider, timeseries plots, basemap sub-labels, legend system
- Theme selector for GL dashboard

### Profile Testing & CI
- Profile recorder and playback engine: fork/archive support, UUID runs, playback with RQ
- Playwright: controllers test suite, landuse validation, smoke tests
- CI: `wctl run-playwright`, profile consolidation, nightly coverage (pytest + npm)
- Forest workflows builder; `build_forest_workflows.py` specs
- Profile runs: Rattlesnake, US Small, Seattle SimFire, Portland, EU, 10m MOFE, debris flow, rangeland, reveg

### Other
- Agentic AI systems manifesto (multi-commit series)
- RHEM with Rust `make_rhem_storm_file` in wepppyo3 (400x speedup)
- AGENTS.md and comprehensive agent documentation (ARCHITECTURE, API_REFERENCE, CONTRIBUTING_AGENTS)
- Rangeland: preflight, RQ routing, default to RAP cover
- Markdown documentation toolkit RFC and pipeline
- CAO (Claude AI Operations): setup, unit tests, applications, Gemini CLI
- `wctl2` with tests and Claude acceptance testing
- SBS WBT MOFE support; NMME client URL fix
- Docker: `weppcloud-ui` lab updates, static asset build pipeline
- Removed legacy scripts; migrated to external repos

## November 2025 (363 commits)

**Theme: DSS export hardening, profile coverage, storm event analyzer, deck.gl map completion, UI themes, landing page**

### Storm Event Analyzer
- Complete 10-phase implementation (phases 0-9c): spec, implementation, tc_out.parquet integration
- Precipitation frequency estimates; Atlas 14 no-coverage error handling
- USGS National Map API migration for elevation service
- Climate: precip frequency WIP, cligen `run_observed` adjust, single storm profile

### DSS Export
- DSS export control show-in-DOM fix (8 iterations to resolve)
- DSS preview updates; date filter application; start/end date support
- Ensure DSS export clears WEPP task timestamps; zero-padded year formatting
- Storm parameters for return periods; `.dss` info browse support
- Double ash load profile test

### Profile & Coverage
- Profile coverage playback; verified `.coverage` file
- Profile expectations framework; transparent errors for controllers
- Controller documentation; surface exceptions testing
- Interchange fixes; `tc_out` interchange

### deck.gl & GL Dashboard Completion
- GL dashboard: TSW replaced with Saturation metrics, channel overlays, day/month/year controls
- WEPP event overlays using `H.soil.parquet` for saturation metrics
- Channel order exclusivity; cache-busting; slider behavior
- Daymet bumped to 2024; hyperlinks to soil/land use resources

### Landing & Theme
- Landing page: collaborator entities, points of contact, sponsors, quick links, Run Atlas Hero, pinned map
- WeppCloud UI updates; dark mode map fix
- Theme metrics badge; nightly workflows

### Infrastructure
- Go microservice CI; CAP server phases 2-9 (full deployment)
- RQ-engine readonly FastAPI service for polling
- Upload blueprint refactoring (phases 1-2); trigger refactor
- Controller polling completion refactor (fork, archive with controlBase)
- Interchange parser: handle Fortran `*****` values

## December 2025 (282 commits)

**Theme: GL dashboard quality pass, migrations, NoDb versioning, observed model, query engine closeout**

### GL Dashboard Quality Pass
- 6-phase quality pass: documentation, testing strategy, refactoring, landuse comparison
- Omni scenarios integration (6+ iterations); cumulative contribution curves
- Climate yearly; disturbed fire-adjusted soil erodibility for mulch scenarios
- Basemap fixes; dominant landuse fix for non-NLCD keys; WEPP statistics/unit clarity
- D8 overlay: flow vector arrows with WGS map
- Color scheme support; theme metrics for numeric spinners

### Migrations & Versioning
- Functional run migration system; single storm migration for WEPP loss summary support
- NoDb `py/state` migration for jsonpickle; versioned peridot binaries
- `wctl migrate-run` command
- Parquet backfill hardening; lazy interchange module loading

### Observed Model & UI
- Observed report combined with graph; observed optimizations
- Streamflow graph stacking re-implementation; NHD Flowlines layer
- UI: condense run controls, last modified time on UI, sorting in manifest/directory listings
- Client-side search and pagination for runs; runs map and search
- Graph layer switching bug fixes; monthly stats for station files

### Omni
- Omni contrasts: stream-order pruning spec and implementation
- Omni delete scenarios feature; contrast management features
- Scenario preferential colors; base scenario descriptive names
- Scenario change keeps layer; run slug canonical access

### Other
- NoDb file handler patch for file descriptor exhaustion
- Python 3.12 dev and prod migration; Docker build cache cleanup on deploy
- Browse: explicit font size, default styles, markdown improvements
- Batch runner: Pure CSS doc/tests, memory watchdog, WBT backend `fvslope`
- Channel delineation: map-object builds, fly map center
- SWAT module: add channel parameter handling, interchange integration, `print.prt` config
- Disturbed: shrub management files aligned with Tahoe templates, `bb=14`, severity-based `hmax`
- WEPP minimum channel width; `wepp_50k` guard

## January 2026 (286 commits)

**Theme: rq-engine migration, culvert-at-risk integration, secrets migration, NoDir, security hardening**

### rq-engine Migration
- Complete rq-engine migration: Flask export routes, response contract updates
- Error schema standardization (6 phases); run-sync dashboard with polling + status stream
- Bootstrap UI: poll async enable job, auto-refresh, git workflow
- Admin RQ info details UI and job detail endpoints
- rq-engine route contract checklist and agent API contract guide

### Culvert-at-Risk Integration
- Multi-phase integration (phases 0-5d): spec, AI coding agent guide, skeleton, DEM handling
- Culvert landuse/soil native CRS retrieval; batch retry per point
- Browse token minting; auth restriction for downloads
- Caddy proxy timeout increases; wmesque2 optional CRS
- `UnnestBasins` migration guide with hydro-enforcement analysis

### Secrets Migration
- 3-phase secrets migration: Docker secret files, rq-engine salt, postgres
- Forest rollout with Docker inspect gate; `wctl2` Redis auth fix
- Secrets inventory aligned with compose mounts

### NoDir (Archive-backed Run Roots)
- NoDir inception: `.nodir` archive-backed run roots, behavior matrix, materialization contract
- Parquet sidecars (WD-level canonical); query-engine `fs_path` integration
- Phase 2-7: browse/files/download integration, symlink validation, thaw/freeze state machine
- Bulk rollout; root mutation adoption; maintenance plumbing

### Security
- JWT auth hardening: browse JWT cookie fallback, bearer-fallback parity tests
- Runs0 next-target sanitization; double-encoded traversal blocking
- Session-claim and token-class auth coverage; cross-service token hardening
- CSRF rollout and session polling fixes
- Zoho SMTP configuration via env
- Profile recorder: cookie/authorization redaction, request body redaction

### Other
- Composite runid slugs: nested batch+omni support, 3+ segment docs
- Browse service: package reorg, dtale handlers, files JSON API, manifest helpers
- GL dashboard: batch mode flag, query-engine URL encoding, contrasts missing guard
- SBS color-shift palette (Okabe-Ito accessibility); legacy palette mode option
- NFS benchmarks: smallfile microbench, cache mount profile
- Deployment: CPU pinning, polling rate-limit tuning, Gunicorn 4 workers
- WEPP: hillslope timeout backoff, flake metrics, completion events
- Culvert RQ: pipeline split, manifest modules, graph queue names

## February 2026 (431 commits)

**Theme: Highest commit month -- NoDir reversal, Omni/climate/wepp refactoring, code quality observability, broad-exception elimination, CLAUDE.md/AGENTS.md establishment, TerrainProcessor spec**

### NoDir Full Reversal
- Complete NoDir reversal: runtime cleanup, tests, documentation
- 10+ phases: projection migration, helper adoption, race safety, lock contention handling
- Mixed nodir root recovery; config opt-in for new-run default markers
- Phase 9 clean: vestigial nodir compatibility complexity removed

### Module Refactoring (Codex-driven)
- Omni: facade/collaborator extraction, contrast builders decomposition, orchestration/services tightening
- Climate: facade collaborator extraction with regressions
- Wepp: facade collaborators, NoDir lock override hardening
- Map GL: controller helper split with contract retention
- Watershed: operations/lookups split into mixins
- `wepp_rq`: stage wrapper split into modules; `project_rq` breakup
- `culvert_rq`: pipeline helpers and manifest modules
- Browse: flow quality and route test gap closure

### Code Quality & Observability
- Code quality observability report and workflow configuration
- Changed-file metric exceptions for telemetry
- Module quality refactor workflow with NoDb role standard
- Broad-exception boundary elimination: work-package, milestone 8, phase 2 cleanup, NoDb closure, residual zero
- Culvert web app codebase audit (MD + PDF)

### Agent Infrastructure
- CLAUDE.md operating guide established (this project's primary Claude Code guide)
- AGENTS.md accuracy refresh; agent onboarding docs refinement
- Codex multi-agent config and role profiles; QA reviewer role
- Prompt templates: red-zone exit for module refactor closure
- Exception-handling policy in agent docs
- RQ dependency graph extraction and drift checks

### Security & Auth
- CSRF headers hardening for legacy POST fetch flows
- Correlation IDs end-to-end implementation with debugging docs
- Culvert batch browse auth flow documentation
- Admin user tokens for culvert downloads
- Batch browse: public access for GL dashboard runs

### Infrastructure
- Redis durability enabled; explicit RQ DB 9 deploy flush
- RQ queue preservation by default; worker registry sync
- Copernicus DEM backend with guarded OpenTopo fallback
- OpenTopography rate reduction (5x)
- Button tab order normalization; stale controllers-gl refresh prompt
- Climate prep race fix during multi-climate rebuild

### Other
- TerrainProcessor high-level spec for configurable terrain DAG
- DEVAL weppcloudR arg compatibility fix
- Topaz: guard subprocess output growth and prompt loops; bundled `dednm` binary with PRUNE loop fix
- `dednm` hang report
- SBS 4-class export: Rust helpers and benchmarks
- Peridot: zero-elevation-drop channel panic fix
- GridMET: HTTPS THREDDS endpoint
- ISRIC soils fetch fix when directory missing
- Batch GeoJSON validation cache refresh fix
- Worker Discord token secret wiring; rq-info operator runbook

## March 2026 (4 commits, month in progress)

**Theme: TerrainProcessor documentation**

- TerrainProcessor spec: high-level configurable terrain DAG concept document
- Culvert_web_app comparison added to TerrainProcessor spec
- Lindsay guidance and refined road embankment strategies incorporated
- Spec renamed from "spec" to "concept document"
