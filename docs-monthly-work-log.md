# Monthly Work Log: October 2025 – January 2026

## Summary

| Month | wepppy | weppcloud-wbt | peridot | wepp-forest | Total Commits |
|-------|--------|---------------|---------|-------------|---------------|
| Oct 2025 | 661 commits, +304K / −103M* | — | 14 commits, +2.8K / −4.1K | 3 commits, +486 / −32 | **678** |
| Nov 2025 | 363 commits, +410K / −329K | — | — | — | **363** |
| Dec 2025 | 282 commits, +136K / −56K | 1 commit, +347K / −0 | 1 commit, +44 / −1 | — | **284** |
| Jan 2026 | 286 commits, +744K / −21K | 16 commits, +147K / −550 | 5 commits, +1.9K / −213 | — | **307** |

\* October deletions dominated by removal of legacy code, submodules, and deprecated `wepp.out` parsers (103M lines removed).
LOC figures include generated assets (package-lock.json, test fixtures, SVGs). See per-month notes for context on large outliers.

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

## Four-Month Totals

| Metric | Oct 2025 | Nov 2025 | Dec 2025 | Jan 2026 | **Total** |
|--------|----------|----------|----------|----------|-----------|
| Commits (all repos) | 678 | 363 | 284 | 307 | **1,632** |
| Lines added (wepppy) | ~304K | ~410K | ~136K | ~744K | **~1.59M** |
| Lines removed (wepppy) | ~103M* | ~329K | ~56K | ~21K | — |

\* The 103M deletion figure reflects removal of legacy submodules, deprecated `wepp.out` parsers, and old binary test data. Net new functional code for October is approximately 225K lines.

### Key Themes Across the Period

1. **Interchange & Query Engine** (Oct–Nov): Wholesale migration from text-file WEPP output parsing to typed Parquet interchange, enabling the query engine and downstream analytics.

2. **Containerization & DevOps** (Oct–Dec): Full Docker Compose production stack, Go microservices for preflight/status, Caddy reverse proxy, Python 3.12 migration, deploy automation.

3. **Modern Frontend** (Nov–Dec): Leaflet→deck.gl map migration, GL Dashboard for interactive watershed analysis, Pure CSS controls replacing Bootstrap/jQuery.

4. **Culvert-at-Risk Integration** (Jan): Cross-application integration bringing culvert vulnerability assessment into WEPPcloud with batch processing and native CRS support.

5. **QA & CI Infrastructure** (Oct–Jan): Profile playback system, Playwright test suites, pytest/NPM coverage nightly runs, CI Samurai automation, error schema standardization.

6. **Rust Acceleration** (Oct–Jan): RHEM storm file via wepppyo3 (400× speedup), SBS map Rust helpers, peridot VRT support, weppcloud-wbt binary output and VRT support.

7. **Batch Processing & Omni Scenarios/Contrasts** (Oct–Jan): Batch runner framework for multi-watershed execution with CLI dashboard, omni scenario management for side-by-side watershed comparisons (e.g., pre-fire vs. post-fire vs. revegetation), user-defined hillslope group contrasts, stream-order pruning contrasts, and difference mapping in the GL Dashboard.

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
