# Culvert_web_app Strategy Assessment

**Date:** 2026-02-18
**Author:** Claude Code analysis
**Status:** Decision document

---

## Context

Culvert_web_app developer leaves for a new position. This document evaluates two paths forward:

- **Option A — Standalone Refactor**: Bring Culvert_web_app up to production
  quality as an independent application.
- **Option B — WEPPcloud Incorporation**: Port the scientifically valid
  Culvert_web_app functionality into wepppy as a native interface, leveraging the
  existing batch GL Dashboard, Query Engine, and CI/CD infrastructure.

The analysis below is grounded in a file-level review of both codebases
conducted 2026-02-18.

### Staffing Reality

wepppy is maintained by a single developer. Based on the work log
(docs-monthly-work-log.md) — 1,632 commits across 4 repos over 4 months,
spanning Python, Rust, Go, JavaScript, Docker, and CI/CD — an independent
assessment estimates this workload at **4–5 FTE** in a typical software
organization.

The current effective load is **~0.7 FTE** on wepppy (the remainder being
teaching, advising, grant writing, and other non-development obligations). This
means every hour spent on Culvert_web_app maintenance is an hour not spent on
wepppy core development, CI hardening, or new research features.

This constraint makes the choice between Option A and Option B existential rather
than merely architectural:

| | Option A | Option B |
|---|---|---|
| Implementation (at 0.7 FTE) | 20 wks / 0.7 = **~29 calendar weeks** | 14.5 wks / 0.7 = **~21 calendar weeks** |
| Ongoing cost against 0.7 FTE budget | 0.3 FTE/yr = **43% of available capacity** | 0.1 FTE/yr = **14% of available capacity** |
| wepppy development during implementation | **Halted or severely degraded** | **Partially degraded** (work is additive to wepppy) |
| wepppy development after implementation | **Permanently reduced** by maintenance tax | **Negligible impact** (shared infra) |

At 0.7 FTE, Option A's ongoing maintenance alone (0.3 FTE/yr) would consume
nearly half the total development budget indefinitely — leaving roughly 0.4 FTE
for all of wepppy: core modeling, GL Dashboard, Query Engine, CI, Rust
acceleration, production operations, and new research integrations. That is not
viable.

Option B's maintenance (0.1 FTE/yr) preserves 0.6 FTE for wepppy, and the
implementation work itself strengthens wepppy rather than building a parallel
system that competes for the same scarce hours.

---

## 1. Fourteen-Dimension Comparison Matrix

| # | Dimension | Culvert_web_app | wepppy | Evidence |
|---|-----------|-----------------|--------|----------|
| 1 | **Code Quality** | **3 / 10** | **7 / 10** | Culvert: 5,786-line monolithic `app.py`, 307+ `print()` stmts in production, bare `except:` (app.py:102), inconsistent naming (`determine_WS_char` vs `vuln_by_comparing_peak_Q_with_discharge_capacity`), mutable global `active_tasks = {}` (app.py:96). wepppy: clear module boundaries, dataclass contracts (`nodir/errors.py`), consistent snake_case; complexity remains in large RQ files (`wepp_rq.py` 2,346 lines). |
| 2 | **Maintainability** | **2 / 10** | **8 / 10** | Culvert: all 71 routes in one file, email logic mixed with auth (app.py:310-427), 22-file `junk/` directory (2.4 MB dead code), Jupyter notebooks in production tree. wepppy: `ARCHITECTURE.md` (153 lines), `AGENTS.md` (1,097 lines), lazy blueprint loading (`routes/__init__.py`), pluggable NoDb mods. |
| 3 | **Security** | **2 / 10** | **7 / 10** | Culvert: `eval()` on user data (`hydrogeo_vuln_analysis_task.py:573`), default secret key fallback `'dev-secret-key-change-in-production'` (app.py:224), bare `extractall()` on uploaded ZIPs (4 sites, see GH issue #182), `secure_filename` imported but inconsistently used. wepppy: centralized `get_secret()` with `_FILE` env pattern (`config/secrets.py:16-47`), path-traversal validation in query engine (`core.py:30-62`), DuckDB parameterized queries, argon2 password hashing, test fixtures that scrub secrets (`conftest.py:22-47`). |
| 4 | **Best Practices / Modernity** | **3 / 10** | **8 / 10** | Culvert: no type hints (5 files use `typing`), no linting config, no CI/CD, gevent monkey-patching, ESRI Shapefiles as primary data format. wepppy: Python 3.12, `str \| None` unions, `@dataclass(slots=True)`, mypy + ESLint + stylelint configured, `uv` package manager, DuckDB + Parquet, deck.gl 9.x. |
| 5 | **Technical Debt** | **3 / 10** | **7 / 10** | Culvert: hardcoded timeouts (600/720/3600) and pool sizes (20/30/25) scattered across files, "TEMPORARILY FORCE EMAIL ENABLED" (app.py:323), `junk/` folder with 22 abandoned files, shapefile column-truncation workarounds in visualization. wepppy: 6 TODO comments total, minimal deprecated usage (proper `@deprecated` decorator), Flask 3 compatibility shim documented inline. |
| 6 | **Flexibility / Adaptability** | **2 / 10** | **8 / 10** | Culvert: adding a new analysis method requires editing 5+ files (390-line popup builder, basemap generator, task orchestrator, app.py routes, visualization CSS dict). Email hardcoded to Zoho. No plugin system. wepppy: NoDb mods plugin architecture (`nodb/mods/`), lazy blueprint registration, 30+ env vars, query-engine presets, dynamic OAuth provider loading. |
| 7 | **Testing** | **0 / 10** | **8 / 10** | Culvert: zero test files, no `tests/` directory, 0% coverage. wepppy: 1,482 test functions across 270 files, markers (unit/integration/routes/slow/nodb), Playwright E2E specs, nightly CI suites, `conftest.py` with secret scrubbing + RQ fixtures. |
| 8 | **Error Handling** | **3 / 10** | **7 / 10** | Culvert: 307 `print()` instead of `logging`, bare `except:` (app.py:102), `centralized_logger.py` exists but underused. wepppy: `NoDirError` frozen dataclass with HTTP status + error code (`nodir/errors.py:21-28`), factory functions (`nodir_mixed_state` -> 409, `nodir_locked` -> 503), 119 files import `logging`, documented RQ response contract. |
| 9 | **Performance** | **4 / 10** | **8 / 10** | Culvert: rasters loaded entirely in-memory (4,033-line delineation file), no HTTP caching, DEMs re-downloaded each run, `dissolve()` collapses subcatchment geometry. wepppy: Rust acceleration via PyO3 (`wepppyo3`, peridot, weppcloud-wbt), DuckDB vectorized analytics, 6-DB Redis caching (72-hr NoDb TTL), `ProcessPoolExecutor`, singleton controllers. |
| 10 | **DevOps / Deployment** | **4 / 10** | **9 / 10** | Culvert: Docker + Compose exist, no CI/CD, no health checks, no resource limits, no `.env.example`. wepppy: 47 GitHub Actions workflows, multi-stage Docker with non-root user, Docker secrets, Makefile deploy targets, HAProxy health checks, composable env anchors (`x-wepppy-env`). |
| 11 | **Data Architecture** | **1 / 10** | **9 / 10** | Culvert: 50+ `to_file(driver='ESRI Shapefile')` calls, column names truncated to 10 chars, zip-bomb/zip-slip surface (GH #182), rank-based scoring destroys absolute values, all data pre-baked server-side into static HTML. wepppy: Query Engine (DuckDB over Parquet), HTTP range-request support, client-side dynamic loading via deck.gl, typed JSON API contracts, catalog auto-discovery. |
| 12 | **Frontend / Visualization** | **2 / 10** | **8 / 10** | Culvert: Folium static Leaflet maps, 390-line f-string popup builder (`subroutine_add_layers_to_base_map.py`), 55-entry CSS dict interpolated in Python, duplicate `get_consistent_map_css()` across two files. wepppy: deck.gl WebGL, modular ES6 (2,500 lines / 15 files), centralized state with subscriber pattern, lazy async layers, canvas graphs, year/month sliders. |
| 13 | **Scientific Rigor** | **3 / 10** | **7 / 10** | Culvert: SBEVA/WDFM are arbitrary weighted sums with no theoretical basis, RUSLE properly implements A=R*K*LS*C*P (Renard et al. 1997) but rank-scores the output, WEPP results dissolved to watershed scale discarding hillslope resolution, EHVI ensemble averages process-based with heuristic methods. wepppy: WEPP process model at hillslope/channel resolution, stochastic climate, results preserved at native spatial resolution. |
| 14 | **Documentation** | **2 / 10** | **8 / 10** | Culvert: minimal docstrings (except dev-package copies), no architecture docs, no onboarding guide. wepppy: `ARCHITECTURE.md`, `AGENTS.md` (1,097 lines), `readme.md` (538 lines), `rq-response-contract.md`, module docstrings with examples, `docs/` with specs and work packages. |

### Aggregate

|                          | Culvert_web_app | wepppy |
|--------------------------|-----------------|--------|
| **Overall**              | **2.4 / 10**    | **7.8 / 10** |
| Dimensions at critical (0-2) | 5 of 14     | 0 of 14 |
| Dimensions passing (>=5)     | 0 of 14     | 14 of 14 |

---

## 2. Culvert_web_app Functional Inventory

What Culvert_web_app provides that wepppy does not:

| Feature | Lines | Scientific Basis | External Data |
|---------|-------|-----------------|---------------|
| Watershed delineation from pour points (WS_deln) | 4,033 (`subroutine_nested_watershed_delineation.py`) | Standard hydrology (D8 flow, breach/fill) | USGS 3DEP, OSM roads |
| Hydrologic frequency analysis (R-based) | 919 (`subroutine_regional_freq_analysis.py`) | L-moments, GEV, LP3 (Hosking & Wallis 1997) | User streamflow/precip data |
| Peak discharge estimation | 1,640 (`subroutine_rational_method.py`) + 505 (GPDM) | Rational method Q=CIA, USGS regression, GPDM | NOAA Atlas-14 |
| Culvert capacity comparison | 596 (`subroutine_culvert_discharge_capacity.py`) | HDS-5 / FHWA hydraulics | User culvert dimensions |
| RUSLE | 3,370 (`subroutine_rusle_analysis.py`) | A=R*K*LS*C*P (Renard et al. 1997) | NOAA Atlas-14, GSSURGO, NLCD |
| SBEVA | 1,581 (`subroutine_sbeva_analysis.py`) | **None** (arbitrary weighted sum, 10 variables) | NLCD, PRISM, eVIIRS NDVI |
| WDFM | 2,129 (`subroutine_wdfm_analysis.py`) | **None** (arbitrary weighted sum, 15 variables) | NWI, PRISM |
| EHVI ensemble | ~200 lines in `hydrogeo_vuln_analysis_task.py` | **None** (averages WEPP with heuristic scores) | — |
| Report generation (R-based plots) | 1,787 (`subroutine_generate_CULVERT_Report.py`) | — | — |

What wepppy already provides for the culvert workflow:

| Function | wepppy Location | Status |
|----------|----------------|--------|
| Culvert batch orchestration | `rq/culvert_rq.py` (2,139 lines) | Complete |
| Payload validation | `microservices/culvert_payload_validator.py` | Complete |
| Per-culvert WEPP execution | `rq/culvert_rq.py:run_culvert_run_rq()` | Complete |
| DEM symlink/VRT management | `nodb/culverts_runner.py` | Complete |
| Batch GL Dashboard | `docs/mini-work-packages/20260209_gl_dashboard_batch_mode.md` | MVP (phases 0-5) |
| Query Engine analytics | `query_engine/` (DuckDB + Parquet) | Complete |
| Watershed delineation backends | `topo/peridot/`, `topo/wbt/`, `topo/topaz/` | Complete |
| NLCD/SSURGO ingestion | `nodb/core/landuse.py`, `nodb/core/soils.py` | Complete |
| Browse/download service | `weppcloud/routes/culvert_browse_bp.py` | Complete |

---

## 3. Option A — Standalone Refactor

Bring Culvert_web_app to production quality while keeping it as a separate
application.

### Implementation Plan

| Phase | Work | Weeks | Key Files |
|-------|------|-------|-----------|
| A1 | Critical security fixes | 1 | `eval()` at `hydrogeo_vuln_analysis_task.py:573`, secret key at `app.py:224`, bare `extractall()` (4 sites), `secure_filename` enforcement |
| A2 | Refactor `app.py` into Flask blueprints + service layer | 3 | Split 5,786 lines into auth_bp, project_bp, ws_deln_bp, hydro_vuln_bp, hydrogeo_vuln_bp, report_bp, download_bp |
| A3 | Replace shapefiles with GeoJSON/GeoParquet | 3 | 50+ `to_file(driver='ESRI Shapefile')` calls, visualization pipeline rework, eliminates column truncation + zip-bomb surface |
| A4 | Fix visualization (Jinja popups, deduplicate CSS) | 2 | 390-line `create_universal_popup()` -> Jinja template, 55-entry CSS dict -> stylesheet, merge duplicated code across `subroutine_add_layers_to_base_map.py` and `subroutine_basemap_generator.py` |
| A5 | Write tests (0% -> ~70% coverage) | 4 | pytest infra, unit tests for 26 subroutines, integration tests for 9 tasks, route tests for 71 endpoints, mocks for USGS/NOAA/WEPP Cloud/OSM |
| A6 | Type hints + linting | 2 | mypy, ruff/flake8 config, dataclasses for data structures |
| A7 | CI/CD pipeline | 1 | GitHub Actions (test/lint/build), Docker image pipeline |
| A8 | Clean dead code + logging | 1 | Remove `junk/` (22 files, 2.4 MB), replace 307 `print()` with `logging`, remove unused imports |
| A9 | Centralize configuration | 0.5 | `config.py`, `.env.example`, extract ~40 hardcoded values |
| A10 | Fix WEPP data usage | 2 | Use subcatchment-level results (stop dissolving), read per-hillslope Parquets, reconsider EHVI dilution |
| A11 | Documentation | 1 | Architecture doc, module READMEs, onboarding guide |
| | **Total** | **~20 weeks** | |

### What you still have after Option A

- Two applications, two Docker stacks, two dependency trees.
- Folium-based static HTML maps (improved but fundamentally server-rendered).
- No real client-side interactivity beyond Leaflet basics.
- 21 R packages for frequency analysis (Docker build complexity, rpy2 bridge).
- SBEVA/WDFM still present (arbitrary weighted sums, no theoretical basis).
- Every wepppy API change requires a corresponding Culvert_web_app update.

---

## 4. Option B — WEPPcloud Incorporation

Port the scientifically valid features into wepppy. Drop what has no theoretical
basis. Leverage existing infrastructure.

### What transfers, what gets dropped

| Feature | Decision | Rationale |
|---------|----------|-----------|
| Watershed delineation from pour points | **Transfer** (mostly exists) | wepppy has WBT/Peridot/TOPAZ + culvert batch orchestration |
| RUSLE (A=R*K*LS*C*P) | **Drop** | Redundant — WEPP already models erosion with a physically-based process model at hillslope resolution; RUSLE is an empirical approximation of what WEPP computes directly |
| Hydrologic frequency analysis | **Transfer** (rewrite w/o R) | Valuable; replace 21 R packages with `scipy.stats` L-moments |
| Peak discharge methods | **Transfer** | Rational method, USGS regression, GPDM -- all well-established |
| Culvert capacity comparison | **Transfer** | Core product function |
| WEPP execution | **Already in wepppy** | `culvert_rq.py` (2,139 lines) |
| Batch orchestration | **Already in wepppy** | `batch_rq.py` + `culvert_rq.py` |
| GL Dashboard visualization | **Already in wepppy** | Batch mode MVP (phases 0-5) |
| Query Engine analytics | **Already in wepppy** | DuckDB over Parquet |
| SBEVA | **Drop** | Arbitrary weighted sum, no theoretical basis |
| WDFM | **Drop** | Arbitrary weighted sum, 15 variables including categoricals with no natural ordering |
| EHVI ensemble | **Drop** | Was averaging WEPP with heuristic noise; WEPP alone is the vulnerability signal |
| Folium visualization | **Drop** | Replaced by deck.gl GL Dashboard |
| Shapefile I/O | **Drop** | Replaced by GeoParquet + GeoJSON |
| R dependency (21 packages) | **Drop** | Replaced by `scipy.stats` (~200 MB smaller Docker image) |

### Implementation Plan

| Phase | Work | Weeks | Details |
|-------|------|-------|---------|
| B1 | Culvert project NoDb mod | 2 | `nodb/mods/culverts/` -- inventory upload (GeoJSON/CSV/Shapefile), project metadata, Point_ID tracking, CRS validation. Inherits NoDb locking, serialization, singleton pattern. |
| B2 | Pour-point watershed delineation | 2 | Multi-point delineation using existing WBT backend: boundary clip, hydro-enforce, flow accumulation, snap pour points, per-point watershed extraction. Orchestration glue + snap-to-stream logic. |
| B3 | Hydrologic frequency analysis | 2.5 | `nodb/mods/culverts/frequency.py` -- L-moments via `scipy.stats` or `lmoments3`, extreme value fitting (GEV, LP3, Gumbel), rational method, USGS regression lookup tables, return period estimation. All outputs -> Parquet. |
| B4 | Culvert capacity + vulnerability scoring | 1 | Capacity calculation, Safe/At-Risk/Critical classification. Vulnerability index: WEPP erosion/sediment + frequency-analysis peak Q vs capacity. Use absolute values (not rank-based scoring). |
| B5 | GL Dashboard culvert interface | 2.5 | Extend batch GL Dashboard: vulnerability color-mapped polygons, WEPP at subcatchment resolution (not dissolved), culvert status indicators, comparison slider. Leverage phases 0-5. |
| B6 | Reporting + export | 1.5 | Culvert report template (Jinja2 + matplotlib, no R), Query Engine for data aggregation, GeoParquet + GeoJSON + CSV export, PDF rendering. |
| B7 | API routes (Flask blueprint) | 1 | `culvert_project_bp.py` -- CRUD, upload, trigger analysis, retrieve results. Register in `_BLUEPRINT_IMPORTS`. |
| B8 | Testing + hardening | 2 | pytest unit + integration + route tests following existing `conftest.py` patterns. Playwright smoke tests for GL Dashboard culvert views. |
| | **Total** | **~14.5 weeks** | |

---

## 5. Maintenance Burden Comparison

### Ongoing effort

| Factor | Option A (Standalone) | Option B (Incorporated) |
|--------|-----------------------|------------------------|
| Codebases to maintain | 2 | 1 |
| Docker stacks | 2 (Ubuntu+R+GDAL, python-slim+Rust) | 1 |
| CI/CD pipelines | 2 (must build Culvert pipeline from scratch) | 1 (47 workflows exist) |
| Dependency trees | 79 Python + 21 R + wepppy API coupling | Existing wepppy deps + scipy |
| Test maintenance | Isolated test suite to maintain | New tests inherit existing infra |
| WEPP integration sync | Every wepppy API change -> Culvert update | Internal (no cross-app sync) |
| Frontend maintenance | Folium (static HTML, server-rendered) | deck.gl (all GL Dashboard improvements free) |
| Security patching | Independent tracking | Single security surface |

### Annual maintenance cost estimate

| Category | Option A | Option B |
|----------|----------|----------|
| Bug fixes + dependency updates | 200 hrs/yr | 60 hrs/yr |
| Security patches | 80 hrs/yr | 20 hrs/yr (shared) |
| WEPP integration sync | 100 hrs/yr | 0 (internal) |
| Feature enhancements | 150 hrs/yr | 80 hrs/yr (leverages infra) |
| Infrastructure / DevOps | 100 hrs/yr | 20 hrs/yr (shared) |
| **Total** | **~630 hrs/yr (~0.3 FTE)** | **~180 hrs/yr (~0.1 FTE)** |

### Impact on a 0.7 FTE budget

Available development capacity: ~1,456 hrs/yr (0.7 * 2,080).

| | Option A | Option B |
|---|---|---|
| Culvert maintenance | 630 hrs/yr | 180 hrs/yr |
| Remaining for wepppy | 826 hrs/yr (0.40 FTE) | 1,276 hrs/yr (0.61 FTE) |
| Effective wepppy capacity loss | **43%** | **14%** |

For context, the Oct 2025 – Jan 2026 work log documents 1,632 commits across
10+ work streams. Even minor reductions in available capacity directly impact
the ability to maintain CI pipelines, ship features, and respond to production
issues. A 43% reduction (Option A) would likely mean abandoning at least 4–5
active work streams; a 14% reduction (Option B) is absorbable.

---

## 6. Recommendation

**Option B (WEPPcloud Incorporation)** is the only viable path for a single
developer at 0.7 FTE.

| Metric | Option A | Option B |
|--------|----------|----------|
| Implementation time | 20 dev-weeks (~29 calendar weeks at 0.7 FTE) | 14.5 dev-weeks (~21 calendar weeks at 0.7 FTE) |
| Ongoing maintenance | 0.3 FTE/yr (43% of budget) | 0.1 FTE/yr (14% of budget) |
| Remaining capacity for wepppy | 0.4 FTE | 0.6 FTE |
| Scientific quality | Carries SBEVA/WDFM noise, rank-scores everything | Clean: WEPP process model + frequency analysis, absolute values |
| Visualization | Folium (static HTML) | deck.gl (WebGL, interactive) |
| Data architecture | GeoJSON/GeoParquet (improved) | Parquet + Query Engine (SQL, range requests) |
| Testing from day one | Must build from scratch | 1,482 tests + 47 CI workflows inherited |
| R dependency | 21 packages, rpy2 bridge | Eliminated (scipy.stats) |
| Context-switching tax | Constant (two codebases, two mental models) | Zero (single codebase) |

Option A is not merely inferior — it is unsustainable. A 0.3 FTE/yr maintenance
burden on a 0.7 FTE budget leaves 0.4 FTE for the entire wepppy ecosystem:
core modeling, GL Dashboard, Query Engine, 47 CI workflows, Rust acceleration,
production operations, Docker infrastructure, and new research integrations. The
wepppy work log shows that even 0.7 FTE is already compressing 4–5 FTE worth of
work through extreme context-switching. Adding a second codebase with its own
Docker stack, dependency tree, and zero test coverage would degrade both
projects.

Option B is 8 calendar weeks shorter to implement, 3x cheaper to maintain, and
every hour of implementation directly strengthens wepppy rather than building a
parallel system. The context-switching cost — which is already the primary tax on
a single developer covering Python, Rust, Go, JS, Docker, and CI — goes to zero
for culvert work.

The losses are SBEVA, WDFM, RUSLE, and the EHVI ensemble. SBEVA and WDFM are
arbitrary weighted overlays with no published theoretical basis. RUSLE is a
legitimate empirical equation (Renard et al. 1997) but is redundant — WEPP
already computes erosion via a physically-based process model at hillslope
resolution, making RUSLE an empirical approximation of what WEPP solves
directly. The EHVI ensemble averaged WEPP with these weaker signals, degrading
rather than enhancing the output. What remains — WEPP process-model erosion and
sediment yield plus hydrologic frequency analysis — is a cleaner and more
defensible product.

---

## Appendix A: Key File References

### Culvert_web_app

| File | Lines | Role |
|------|-------|------|
| `culvert_app/app.py` | 5,786 | Monolithic Flask app (71 routes) |
| `culvert_app/tasks/hydrogeo_vuln_analysis_task.py` | 769 | Main analysis orchestrator |
| `culvert_app/tasks/wepp_cloud_integration_task.py` | 425 | WEPP Cloud submit/poll/download |
| `culvert_app/tasks/build_payload.py` | 885 | Payload ZIP construction |
| `culvert_app/utils/subroutine_nested_watershed_delineation.py` | 4,033 | Watershed delineation |
| `culvert_app/utils/subroutine_rusle_analysis.py` | 3,370 | RUSLE (A=R*K*LS*C*P) |
| `culvert_app/utils/subroutine_wdfm_analysis.py` | 2,129 | WDFM (arbitrary weighted sum) |
| `culvert_app/utils/subroutine_sbeva_analysis.py` | 1,581 | SBEVA (arbitrary weighted sum) |
| `culvert_app/utils/subroutine_regional_freq_analysis.py` | 919 | R-based frequency analysis |
| `culvert_app/utils/subroutine_rational_method.py` | 1,640 | Rational method variants |
| `culvert_app/utils/subroutine_generate_CULVERT_Report.py` | 1,787 | Report generation |
| `culvert_app/static/visualization/subroutine_add_layers_to_base_map.py` | 904 | Folium popup builder |
| `culvert_app/static/visualization/subroutine_basemap_generator.py` | 1,229 | Folium basemap generator |
| `culvert_app/utils/junk/` | 22 files, 2.4 MB | Dead code |

### wepppy (culvert-relevant)

| File | Lines | Role |
|------|-------|------|
| `wepppy/rq/culvert_rq.py` | 2,139 | Culvert batch orchestration |
| `wepppy/rq/batch_rq.py` | 595 | Generic batch runner |
| `wepppy/nodb/culverts_runner.py` | ~600 | Batch state + run management |
| `wepppy/microservices/rq_engine/culvert_routes.py` | ~500 | Culvert API endpoints |
| `wepppy/microservices/culvert_payload_validator.py` | ~200 | Payload validation |
| `wepppy/nodb/core/watershed.py` | ~2,000 | Watershed NoDb controller |
| `wepppy/query_engine/core.py` | ~200 | DuckDB query builder |
| `wepppy/query_engine/executor.py` | ~80 | DuckDB executor |
| `docs/culvert-at-risk-integration/weppcloud-integration.spec.md` | 378 | API spec |
| `docs/culvert-at-risk-integration/weppcloud-integration.plan.md` | 625 | Implementation plan |
| `docs/mini-work-packages/20260209_gl_dashboard_batch_mode.md` | 239 | Batch GL Dashboard spec |

### wepppy commit velocity (last 4 months)

| Month | Commits | LOC Added | Key Themes |
|-------|---------|-----------|------------|
| Oct 2025 | 678 | ~304K | Parquet interchange, Query Engine, Docker stack, OAuth |
| Nov 2025 | 363 | ~410K | Profile playback, Playwright, coverage infra, wctl2 |
| Dec 2025 | 284 | ~136K | Leaflet->deck.gl, GL Dashboard, rq-engine, Python 3.12 |
| Jan 2026 | 307 | ~744K | Culvert-at-Risk integration, Storm Event Analyzer, SWAT |
| **Total** | **1,632** | **~1.59M** | |

### Culvert_web_app commit velocity (same period)

| Period | Commits | Pattern |
|--------|---------|---------|
| 3 weeks | 13 (5 merge PRs) | Repetitive "wepp integrated" messages, 3 active days |

---

## Appendix B: Security Posture (Culvert_web_app)

A code-level security review identified concerns in several OWASP Top 10
categories including injection, insecure design, and security misconfiguration.
Specific findings have been filed as GitHub issues on the Culvert_web_app
repository and are not reproduced here.

Key areas of concern:

- Unsafe deserialization of user-controlled input
- Weak default configuration for session management
- Insufficient validation of uploaded archive contents
- Missing upload size limits and rate limiting
- Inconsistent use of filename sanitization

Option B eliminates most of these concerns by moving user-facing functionality
into wepppy, which has centralized secret management, parameterized queries,
path-traversal validation, and argon2 password hashing.

---

## Appendix C: SBEVA / WDFM Scientific Assessment

### SBEVA (Streamside Buffer Erosion Vulnerability Assessment)

- 10-variable weighted sum clipped to a 20m stream buffer.
- Variables include slope, NDVI, saturation index, land cover, flow
  concentration -- mixed on 1-5 ordinal scales.
- No published theoretical basis. Weights appear to be subjective.
- Score = weighted sum -> rank -> 5-point ordinal scale.
- Destroys absolute magnitude information via rank-based scoring.

### WDFM (Wetland and Floodplain Disturbance Assessment)

- 15-variable weighted sum including categoricals (wetland type, land cover
  class) that have no natural ordering.
- Uses NWI, PRISM, flow accumulation, buffer distances.
- No published theoretical basis.
- Same rank-based scoring issue.

### RUSLE (Revised Universal Soil Loss Equation)

- A = R * K * LS * C * P (Renard et al. 1997).
- The only empirical method with a published, peer-reviewed equation.
- Properly implemented in `subroutine_rusle_analysis.py`.
- However, WEPP already models the same erosion processes (detachment,
  transport, deposition) with a physically-based approach at hillslope
  resolution using daily timesteps over stochastic climate. RUSLE is an
  empirical approximation of what WEPP computes directly.
- **Decision**: drop. Redundant given WEPP integration.

### EHVI (Ensemble Hydrogeomorphologic Vulnerability Index)

- Averages rank-normalized scores from WEPP, SBEVA, RUSLE, WDFM.
- Degrades the WEPP process-based signal by averaging with heuristic noise.
- **Decision**: drop. WEPP erosion/sediment output is the vulnerability signal.
