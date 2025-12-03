# WEPPcloud Major Changes: March 2025 - December 2025

> **Summary**: This document captures the major changes made to the wepppy repository from March 2025 through December 2025, encompassing 1885 commits across key feature areas.

## Overview

| Metric | Value |
|--------|-------|
| **Total Commits** | 1,885 |
| **Date Range** | March 1, 2025 - December 3, 2025 |
| **Primary Contributor** | Roger Lew (1,825 commits) |
| **AI-Assisted Contributions** | copilot-swe-agent[bot] (39), dependabot[bot] (21) |

### Commit Activity by Month

| Month | Commits | Notable Focus |
|-------|---------|---------------|
| March 2025 | 70 | Bare metal deployment, Omni framework |
| April 2025 | 79 | Climate refinements, monthly scale fixes |
| May 2025 | 71 | Peridot watershed, Chile soils integration |
| June 2025 | 35 | Stability improvements |
| July 2025 | 57 | DuckDB query engine, report migrations |
| August 2025 | 113 | Controller modernization, Pure templates |
| September 2025 | 390 | UI themes, OAuth 2.0, accessibility survey |
| October 2025 | 687 | Profile coverage, Playwright smoke tests, batch runner |
| November 2025 | 359 | DSS export, ash transport, single storm |
| December 2025 | 24 | Python 3.12 upgrade, migration scripts |

---

## Major Feature Areas

### 1. DSS Export System (November 2025)
**Purpose**: HEC-DSS export functionality for integration with HEC-RAS and other hydrologic modeling tools.

**Key Changes**:
- Added DSS export control with date filtering (start_date, end_date parameters)
- Peak channel discharge files (`peak_chan_<topaz_id>.dss`)
- Return period calendar years when available
- Skip low-order channels (orders 1 and 2) by default
- Shapefile (.shp) export support
- `ichout_override` parameter for custom output control

**Related Commits**: ~30 commits refining DSS export UI and functionality

---

### 2. Omni Scenario Framework (March-November 2025)
**Purpose**: Multi-scenario WEPP orchestration for parameter sensitivity analysis and ensemble modeling.

**Key Changes**:
- `omni_rq` worker pool integration with scenario-level orchestration
- Clone/fork support with `copy_version_for_clone`
- Dependency state synchronization between parent and child scenarios
- Query-engine integration for consolidated reporting
- NoDb file locking against parent run to prevent conflicts
- Cache invalidation on project deletion

**Commits**: ~25 commits spanning March through November

---

### 3. Ash/Wildfire Transport (WATAR) (Year-round)
**Purpose**: Enhanced wildfire ash transport modeling for post-fire erosion assessment.

**Key Changes**:
- Black and white ash differentiation in `totalwatsed` reports
- Corrected streamflow and combined sediment+ash reporting
- `ash_runoff` packed in `daily_watershed.parquet`
- Ash warnings integration in DSS export
- `ashpost` versioning with Parquet output and documentation
- Type hints added to ash transport module
- Excel permission change handling

**Impact**: Critical for BAER (Burned Area Emergency Response) team workflows

---

### 4. UI/Theme System (September-October 2025)
**Purpose**: Comprehensive theme system with VS Code theme integration and accessibility compliance.

**Key Changes**:
- **11 Production Themes**: Light/Dark defaults + 9 VS Code-inspired themes
- **WCAG AA Compliance**: Validation for all shipped themes
- **Light High-Contrast Theme**: Enhanced visibility mode
- **Configurable `theme-mapping.json`**: Semantic variable mappings for stakeholder self-service
- **User Persistence**: localStorage + cookie fallback
- **Theme Switcher UI**: Integrated into settings panel

**Deliverables**:
- Dynamic converter script with validation and reset capabilities
- Build pipeline integration with automatic theme generation
- Documentation: theme system guide, stakeholder editing guide, troubleshooting

---

### 5. Type Hints Initiative (October 2025)
**Purpose**: Comprehensive type hints for core NoDb controllers to enable mypy validation and improve agent code generation.

**Modules Enhanced**:
- `climate.py` - 118 functions typed
- `watershed.py` - Complete coverage
- `wepp.py` - Class attributes and method signatures
- `disturbed.py` - Full type annotations
- `topaz.py` - Comprehensive hints
- `soils.py` - Complete coverage
- Ash transport module

**Supporting Work**:
- Type stub management with `stubgen`/`stubtest`
- mypy configuration in `mypy.ini`
- Documentation of type hint conventions in AGENTS.md

---

### 6. Query Engine (July-November 2025)
**Purpose**: DuckDB-backed SQL analytics over Parquet interchange for instant loss reports and timeseries queries.

**Key Changes**:
- FastAPI-based query endpoint
- `topaz_id`/`wepp_id` case aliases for backward compatibility
- MCP (Model Context Protocol) spectral configuration
- Strict slashes production deployment fix
- Console routing corrections
- Wepp visualization using query engine
- Runoff visualization refactored to use query engine

**Documentation**:
- WEPP output references in query-engine README
- Human-readable query-engine documentation

---

### 7. Single Storm Mode (October-November 2025)
**Purpose**: Support for single design-storm WEPP simulations for return period analysis.

**Key Changes**:
- CLIGEN single storm generation
- Single storm profile support
- Wepp interchange guards for single storm mode
- WEPP loss summary migration for single storm support
- Climate control UI enhancements for single storm
- `nodb.Climate.parse_input` fix for single storm

---

### 8. Profile & Coverage Testing (October-November 2025)
**Purpose**: Playwright-based smoke testing and profile playback for code coverage analysis.

**Key Changes**:
- **Playwright Smoke Harness**: YAML profile support for health snapshots
- **Profile Playback**: Coverage file verification and playback tracer
- **Dynamic Dev Server Nightly Profile Tests**: Automated testing workflows
- **Batch Execution**: `run_profile_coverage_batch` with quiet mode
- **Test Support Blueprint**: `/tests/api/*` endpoints for automation

**Environment Variables**:
- `SMOKE_CREATE_RUN`, `SMOKE_RUN_CONFIG`, `SMOKE_RUN_PATH`
- `SMOKE_KEEP_RUN`, `SMOKE_RUN_ROOT`, `SMOKE_BASE_URL`

---

### 9. Python 3.12 Upgrade (December 2025)
**Purpose**: Upgrade development and production environments to Python 3.12.

**Key Changes**:
- Production Python 3.12 deployment
- Development environment 3.12 migration
- Enhanced logging initialization to prevent file descriptor exhaustion
- NoDb base file logging revision to avoid open file handles
- Handler reuse patterns for async logging

---

### 10. OAuth 2.0 Authentication (September 2025)
**Purpose**: Modern authentication support for user management.

**Key Changes**:
- OAuth 2.0 support implementation
- Integration with Flask-Security
- Documentation in `docs/oauth_spec.md`

---

### 11. Batch Processing & Runner (September-October 2025)
**Purpose**: Automated batch execution of WEPP scenarios with CLI monitoring.

**Key Changes**:
- **Batch Runner**: CLI dashboard with boundary GeoJSON generation
- **Task Orchestration**: Breakout of `TaskEnum` for hillslope/watershed runs
- **Run State Reporting**: JSON-pickling TaskEnum fixes
- **Archive Support**: Fork and archive with UUID tracking
- **Fresh Clone**: Run isolation for reproducibility

---

### 12. Controller Modernization (August-October 2025)
**Purpose**: Migrate controllers to Pure templates with unified StatusStream telemetry.

**Key Changes**:
- **Pure Template Migration**: All controllers converted
- **StatusStream Integration**: Replaced WSClient shim with `controlBase.attach_status_stream`
- **Bootstrap Refactor**: Helper-driven initialization patterns
- **URL Construction Fix**: Standardized `url_for_run()` pattern
- **Legacy Control Cleanup**: Removed deprecated WEPP advanced controls

**Documented Polish Items**:
- Legend styling, table standardization, TOC indicators
- Map layer wiring, inline help icons, hint deduplication

---

## Infrastructure & DevOps

### Docker & Deployment
- Python 3.12 production images
- Docker build cache cleanup on deploy
- Revised `docker-compose.dev` subnet for weppcloudr outbound
- Deploy scripts ensuring Docker GID is 993
- `.docker-data/redis` runner permission resolution
- Static asset build pipeline in Dockerfile

### Dependency Updates (via Dependabot)
- **werkzeug**: 3.1.3 → 3.1.4
- **fonttools**: 4.43.0 → 4.61.0
- **starlette**: 0.47.2 → 0.49.1
- **authlib**: 1.3.1 → 1.6.5
- **tornado**: 6.5
- **js-yaml**: 4.1.0 → 4.1.1
- **glob**: 10.4.5 → 10.5.0
- **go-redis**: Updated in Go microservices
- **protobuf**: Updated in preflight2/status2

### CI/CD Improvements
- GitHub Actions workflow refinements
- Profile coverage workflow updates
- npm-coverage-nightly workflow
- pytest-coverage-nightly workflow
- Theme metrics nightly badge generation
- Go microservice CI pipelines

---

## Documentation Improvements

### New Documentation
- `ARCHITECTURE.md` - System design and component diagrams
- `API_REFERENCE.md` - Quick reference for key APIs
- `CONTRIBUTING_AGENTS.md` - AI coding assistant guidelines
- `docs/AGENT_ACCESSIBILITY_SURVEY.md` - Accessibility survey results
- `docs/oauth_spec.md` - OAuth 2.0 specification
- `docs/README_TEMPLATE_SUMMARY.md` - README authoring templates

### README Audit
- Comprehensive README audit across all modules
- Standard template system for README authoring
- Quality checklist and maintenance workflow

---

## Testing Improvements

### Test Infrastructure
- Common test config for `sys.modules` stubs
- Stub completeness checker (`wctl check-test-stubs`)
- pytest updates for NoDb controller testing
- npm test improvements for frontend validation

### New Test Suites
- DSS export tests with start/end date coverage
- Double ash load profile tests
- ESDAC soil build tests
- RHEM blueprint tests
- Playwright controller test suite

---

## Work Packages Completed (October 2025)

| Package | Duration | Outcome |
|---------|----------|---------|
| VS Code Theme Integration | 3 days | 11 themes, WCAG AA compliance |
| UI Style Guide Refresh | 2 days | 8 copy-paste templates |
| Smoke Tests & Profile Harness | - | Playwright harness operational |
| Frontend Integration | ~4 weeks | Pure migration complete |
| StatusStream Cleanup | 1 day | Unified telemetry pipeline |
| Controller Modernization Docs | 1 week | Helper-first documentation |

---

## Notable Fixes

- **File descriptor exhaustion**: Enhanced logging handler reuse
- **ISRIC WKT issue**: Projection handling fix
- **Future climate start year**: Interchange fix
- **Subcatchment labels**: Min/max deduplication
- **Map race conditions**: Preflight script resolution
- **SSURGO WAL mode**: SQLite write-ahead logging enforcement
- **Climate station selection**: Mode naming improvements
- **Watershed readonly check**: Edge hillslope identification guard

---

## Credits

**Contributors**:
- Roger Lew (University of Idaho)
- GitHub Copilot / Codex agents
- Dependabot (automated dependency updates)

**Acknowledgments**:
- BAER teams providing feedback on ash transport workflows
- Hydrologists validating DSS export compatibility
- UI/UX feedback driving theme system development
