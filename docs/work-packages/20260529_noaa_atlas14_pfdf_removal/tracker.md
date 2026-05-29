# Tracker - PFDF Removal and Native NOAA Atlas 14 Client

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-05-29 20:25 UTC  
**Current phase**: Complete (implementation + validation)  
**Last updated**: 2026-05-29 20:57 UTC  
**Next milestone**: Package archived; follow-up only if NOAA contract drift is observed  
**Security impact**: `low`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog

- [ ] None.

### In Progress

- [ ] None.

### Blocked

- [ ] None.

### Done

- [x] Created package scaffold (`package.md`, `tracker.md`, `prompts/active`, `prompts/completed`, `artifacts`) (2026-05-29 20:25 UTC).
- [x] Mapped current `pfdf` dependency and call-site inventory (`docker/requirements-uv.txt`, climate export service, NOAA tests/docs) (2026-05-29 20:25 UTC).
- [x] Authored initial scope, migration constraints, and success criteria for dependency removal and client replacement (2026-05-29 20:25 UTC).
- [x] Registered package in root `PROJECT_TRACKER.md` backlog (2026-05-29 20:27 UTC).
- [x] Captured public NOAA PFDS endpoint contract from HDSC docs and live endpoint behavior (`cgi_readH5.py`) (2026-05-29 20:40 UTC).
- [x] Implemented WEPPpy-owned Atlas 14 client at `wepppy/climates/noaa/atlas14.py` (+ `wepppy/climates/noaa/__init__.py`) (2026-05-29 20:45 UTC).
- [x] Cut over `ClimateArtifactExportService.download_noaa_atlas14_intensity` to the in-repo client boundary (2026-05-29 20:46 UTC).
- [x] Migrated climate artifact service tests off `pfdf` module injection (`tests/nodb/test_climate_artifact_export_service.py`) (2026-05-29 20:47 UTC).
- [x] Added deterministic unit tests for the new Atlas14 client (`tests/climates/noaa/test_atlas14_client.py`) (2026-05-29 20:48 UTC).
- [x] Updated NOAA integration test imports/docs (`tests/climates/noaa/test_atlas14_download.py`, `tests/climates/noaa/README.md`) (2026-05-29 20:50 UTC).
- [x] Removed `pfdf` from dependency manifests (`docker/requirements-uv.txt`) (2026-05-29 20:50 UTC).
- [x] Ran targeted validation gates and recorded outcomes (2026-05-29 20:57 UTC).
- [x] Re-ran global sanity gate and documented unrelated baseline failure outside package scope (2026-05-29 20:57 UTC).
- [x] Updated package lifecycle docs and moved ExecPlan to `prompts/completed` (2026-05-29 20:57 UTC).

## Timeline

- **2026-05-29 20:25 UTC** - Package created and scoped.
- **2026-05-29 20:27 UTC** - Root tracker backlog entry added for package discoverability.
- **2026-05-29 20:40 UTC** - Public API contract evidence captured (HDSC FAQ + `cgi_readH5.py` endpoint response shape).
- **2026-05-29 20:50 UTC** - Client implementation, runtime cutover, test updates, and dependency removal completed.
- **2026-05-29 20:57 UTC** - Validation completed and package closed.

## Decisions Log

### 2026-05-29 20:25 UTC: Replace only Atlas 14 dependency surface, not all `pfdf` capabilities
**Context**: The active WEPPpy runtime only uses `pfdf` for NOAA Atlas 14 CSV download in climate artifact export.

**Options considered**:
1. Build a broad generic climate HTTP client framework first.
2. Replace only the Atlas 14 surface used today, preserving existing call-site behavior.
3. Keep `pfdf` and defer removal.

**Decision**: Option 2.

**Impact**: Keeps package scope bounded and directly addresses GPLv3 dependency risk with minimal collateral changes.

---

### 2026-05-29 20:25 UTC: Preserve climate artifact optionality contract during cutover
**Context**: Existing behavior treats NOAA Atlas 14 output as optional and does not fail climate build on upstream/API issues.

**Options considered**:
1. Make Atlas 14 fetch failures fatal after client rewrite.
2. Preserve optional artifact behavior and existing retry/no-coverage semantics.

**Decision**: Option 2.

**Impact**: Prevents behavior regression for runs where NOAA service is unavailable or location has no coverage.

---

### 2026-05-29 20:40 UTC: Use NOAA `cgi_readH5.py` endpoint contract as primary implementation source
**Context**: Public docs expose the scrape endpoint and parameters; live responses return JS-style assignments (`result`, `quantiles`, `upper`, `lower`, metadata) that map directly to existing artifact format needs.

**Options considered**:
1. Scrape `pfds_printpage.html` table HTML and parse rendered output.
2. Call `cgi_readH5.py` directly and render NOAA-style artifact text from structured response assignments.

**Decision**: Option 2.

**Impact**: Reduced parser complexity, deterministic response contract, and easier compatibility with existing NOAA artifact schema consumed by WEPPcloud routes.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| NOAA PFDS endpoint/format assumptions diverge from documented behavior | High | Medium | Captured public references + added deterministic unit tests for parser/render boundary | Mitigated |
| Client replacement changes retry/no-coverage semantics | High | Medium | Kept `download_noaa_atlas14_intensity` retry wrapper intact and retained compatibility tests | Mitigated |
| `pfdf` references remain in runtime/dependency paths after cutover | Medium | Medium | Removed dependency pin and validated repo-wide import/manifest matches | Mitigated |
| License-clean boundary unclear to maintainers | Medium | Low | Updated NOAA README with public API references and in-repo ownership boundary | Mitigated |

## Verification Checklist

### Code Quality
- [x] Focused NOAA artifact tests pass after client cutover.
- [x] No production-path `pfdf` imports remain.
- [x] Retry/backoff and no-coverage behavior remain deterministic.

### Security
- [x] Security impact triage recorded (`low`) with rationale.
- [x] Outbound request construction and file-write boundaries reviewed for safe defaults.

### Documentation
- [x] Work-package scaffold created.
- [x] NOAA client contract documentation updated with public API references.
- [x] `PROJECT_TRACKER.md` lifecycle entry updated at package start and close.

### Testing
- [x] Unit tests updated for new client boundary.
- [x] Integration/live download tests updated (network-gated by `ATLAS14_DOWNLOADS=1`).
- [x] Repo-wide grep confirms dependency/reference cleanup in production path.

## Progress Notes

### 2026-05-29 20:57 UTC: End-to-end execution and closure
**Agent/Contributor**: Codex

**Work completed**:
- Added `wepppy`-owned NOAA Atlas14 client (`wepppy/climates/noaa/atlas14.py`) and package export (`wepppy/climates/noaa/__init__.py`).
- Replaced runtime `pfdf` import path in `wepppy/nodb/core/climate_artifact_export_service.py`.
- Migrated climate artifact service tests to patch the new client boundary (`tests/nodb/test_climate_artifact_export_service.py`).
- Added deterministic client unit coverage (`tests/climates/noaa/test_atlas14_client.py`).
- Updated NOAA integration test imports and README public API references.
- Removed `pfdf` dependency pin from `docker/requirements-uv.txt`.
- Updated package docs and project tracker lifecycle status.

**Blockers encountered**:
- Full-suite pre-handoff run halted on unrelated baseline failure outside package scope:
  - `tests/nodb/test_ron_fetch_dem_copernicus.py::test_fetch_dem_uses_copernicus_backend_when_scheme_is_copernicus`
  - `AttributeError: 'Ron' object has no attribute '_cellsize'`

**Next steps**:
1. No package-local code follow-up required.
2. Track unrelated `Ron._cellsize` baseline failure in its owning package/workstream.

**Test results**:
- `wctl run-pytest tests/climates/noaa/test_atlas14_client.py --maxfail=1` -> `4 passed`
- `wctl run-pytest tests/nodb/test_climate_artifact_export_service.py --maxfail=1` -> `12 passed`
- `wctl run-pytest tests/climates/noaa/test_atlas14_download.py --maxfail=1` -> `4 skipped` (network-gated)
- `wctl check-test-stubs` -> pass
- `wctl run-pytest tests --maxfail=1` -> `1 failed` (unrelated baseline as noted above)

## Communication Log

### 2026-05-29 20:25 UTC: User requested work-package preparation and execution
**Participants**: User, Codex  
**Question/Topic**: Remove GPLv3 `pfdf` dependency and author Atlas14 client from public API docs; then execute package end-to-end.  
**Outcome**: Package fully implemented and closed with validation evidence recorded.
