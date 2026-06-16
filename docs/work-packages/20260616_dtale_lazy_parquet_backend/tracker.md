# Tracker - D-Tale Lazy Parquet Backend

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-06-16 19:51 UTC  
**Current phase**: Implementation complete locally; production observation pending  
**Last updated**: 2026-06-16 20:16 UTC  
**Next milestone**: Deploy/observe D-Tale worker RSS on production if requested  
**Security impact**: `low`  
**Dedicated security review**: `no`  
**Security artifact**: N/A

## Task Board

### Ready / Backlog
- [ ] Production rollout/observation if requested.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Package scaffolded with package brief, tracker, and active ExecPlan (2026-06-16 19:51 UTC).
- [x] Direction selected: patch the existing D-Tale lazy-backend seam rather than carrying a broad fork (2026-06-16 19:51 UTC).
- [x] Implemented `LazyParquetDtaleInstance` with bounded DuckDB/PyArrow page reads (2026-06-16 20:10 UTC).
- [x] Wired Parquet `/internal/load` to register lazy datasets instead of calling `_load_dataframe` (2026-06-16 20:10 UTC).
- [x] Patched D-Tale endpoint `dtale.get_data` only for registered lazy Parquet IDs (2026-06-16 20:10 UTC).
- [x] Updated D-Tale service notes with the lazy backend contract and upstream sync seam (2026-06-16 20:16 UTC).
- [x] Focused D-Tale tests passed: `5 passed, 4 skipped` (2026-06-16 20:16 UTC).
- [x] Stub validation passed: `wctl run-stubtest wepppy.webservices.dtale` and `wctl check-test-stubs` (2026-06-16 20:16 UTC).
- [x] Broad microservice validation passed: `967 passed, 4 skipped` (2026-06-16 20:16 UTC).
- [x] Changed-file broad exception gate passed with net delta `+0` (2026-06-16 20:16 UTC).
- [x] Work-package docs lint passed: `3 files validated, 0 errors, 0 warnings` (2026-06-16 20:16 UTC).

## Timeline

- **2026-06-16 19:51 UTC** - Package created after D-Tale upstream/local investigation identified ArcticDB-style lazy paging as the lowest-drift seam.

## Decisions Log

### 2026-06-16 19:51 UTC: Use a lazy Parquet backend modeled on D-Tale ArcticDB mode
**Context**: The user asked whether patching D-Tale could be done while minimizing upstream sync burden. Local and upstream inspection showed D-Tale is pandas-first, but already has an ArcticDB path that pages rows/columns and accepts reduced functionality.

**Options considered**:
1. Make D-Tale Arrow-native across all routes - too broad and high drift.
2. Fork D-Tale locally - high long-term sync burden.
3. Add a WEPP lazy Parquet backend that mirrors the ArcticDB instance contract - smaller, testable, and aligned with upstream behavior.

**Decision**: Implement option 3.

**Impact**: This package targets the main D-Tale grid first. Unsupported analysis/export/transformation routes should fail explicitly or stay hidden rather than silently loading the full Parquet file.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| D-Tale internals change on upgrade | Medium | Medium | Keep the patch narrow and add contract tests around the patched seam | Open |
| A secondary D-Tale route uses one-row sample data rather than full lazy data | Medium | Medium | Document route limits and keep `LazyParquetDtaleInstance.data` raising to prevent full-file fallback | Open |
| Lazy paging changes grid sorting/filter behavior | Medium | Medium | Start with grid paging parity and defer unsupported features explicitly | Open |
| Added query translation weakens path/filter validation | Medium | Low | Keep existing `_resolve_target` and filter compiler boundaries intact | Open |

## Hardening Signal Log

- **Baseline health signals**: Current D-Tale service uses eager pandas DataFrame loading for Parquet files.
- **Post-change health signals**: Focused tests show `/internal/load` registers lazy Parquet datasets and `/dtale/data/<id>` returns rows from bounded reads. Broad microservice tests passed.
- **Danger signals observed**: Distinct filtered D-Tale loads initially collided on display name; fixed by appending a short filter hash to filtered display names.
- **Temporary callus register**: None.
- **Softening experiments**: None.

## Verification Checklist

### Code Quality
- [x] Focused D-Tale tests passing (`wctl run-pytest tests/microservices/test_browse_dtale.py`).
- [x] Broad microservice tests passing (`wctl run-pytest tests/microservices --maxfail=1`).
- [x] Changed-file broad exception gate clean (`python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`).
- [x] Stubtest clean (`wctl run-stubtest wepppy.webservices.dtale`).
- [x] Test stubs complete (`wctl check-test-stubs`).

### Security
- [x] Security impact triage recorded as `low` with rationale.
- [x] Dedicated security artifact is not required for the current scope.
- [x] Existing internal token and run path validation remain unchanged.
- [x] Residual risks and follow-up mitigation actions are recorded.

### Documentation
- [x] D-Tale service notes updated.
- [x] Work package closure notes complete.
- [x] Parameterization ADR not required because no defaults/formulas/thresholds/unit conversions/fallback heuristics change.

### Testing
- [x] Unit/route coverage for lazy Parquet registration.
- [x] Paged grid-load coverage from a Parquet fixture.
- [x] Eager non-Parquet behavior remains covered.
- [x] Manual or local container smoke evidence not required; route-level tests exercise the Flask app through the service module.

### Deployment
- [x] Tested in the `wctl` docker-compose environment.
- [ ] Production rollout/observation notes added if deployed from this package.

## Progress Notes

### 2026-06-16 19:51 UTC: Package scaffold
**Agent/Contributor**: Codex

**Work completed**:
- Created package brief, tracker, and active ExecPlan.
- Recorded the design direction from upstream/local D-Tale investigation.
- Added the package to `PROJECT_TRACKER.md`.

**Blockers encountered**:
- None.

**Next steps**:
- Implement the lazy Parquet backend.
- Add focused tests for registration and paged reads.
- Update this tracker and the active ExecPlan as code decisions are made.

**Test results**: Not run yet.

### 2026-06-16 20:16 UTC: Lazy Parquet implementation and focused tests
**Agent/Contributor**: Codex

**Work completed**:
- Added `LazyParquetDtaleInstance` in `wepppy/webservices/dtale/dtale.py`.
- Parquet/GeoParquet/PQ `/internal/load` now registers lazy datasets and removes Parquet from the eager `_load_dataframe` dispatch.
- Added a narrow `dtale.get_data` endpoint wrapper for lazy IDs only.
- Filtered Parquet D-Tale launches use the existing `CompiledParquetFilter` DuckDB SQL and remain lazy.
- Added tests for lazy registration, grid-row retrieval, and distinct filtered dataset IDs.
- Updated `wepppy/webservices/dtale/AGENTS.md`.

**Blockers encountered**:
- Distinct filtered datasets initially shared one display name and upstream D-Tale rejected the second startup. The loader now appends an eight-character filter hash to filtered display names.

**Next steps**:
- Run broad microservice tests.
- Run changed-file broad exception gate.
- Run docs lint for the new package.
- Update closeout notes with final validation evidence.

**Test results**: `wctl run-pytest tests/microservices/test_browse_dtale.py` passed with `5 passed, 4 skipped`.

### 2026-06-16 20:16 UTC: Validation and local closeout
**Agent/Contributor**: Codex

**Work completed**:
- Re-ran focused D-Tale tests after the sort and export-guard changes.
- Re-ran broad microservice tests.
- Ran stubtest and test-stub consistency checks for the D-Tale module.
- Ran changed-file broad-exception enforcement.
- Ran work-package docs lint and spelling normalization previews.
- Updated package and ExecPlan closeout notes.

**Blockers encountered**:
- None.

**Next steps**:
- Deploy and observe D-Tale worker RSS on production if this implementation is promoted.
- Decide later whether lazy Parquet chart/export features are worth adding or should stay unsupported.

**Test results**:
- `wctl run-pytest tests/microservices/test_browse_dtale.py`: `5 passed, 4 skipped`.
- `wctl run-pytest tests/microservices --maxfail=1`: `967 passed, 4 skipped`.
- `wctl run-stubtest wepppy.webservices.dtale`: success.
- `wctl check-test-stubs`: success.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`: PASS, net delta `+0`.
- `wctl doc-lint --path docs/work-packages/20260616_dtale_lazy_parquet_backend`: `3 files validated, 0 errors, 0 warnings`.

## Watch List

- **D-Tale route drift**: Keep local patch points small and guarded by tests.
- **Unsupported D-Tale features**: Avoid silent fallback to full DataFrame loads.
- **RSS behavior**: Validate representative Parquet launches after functional tests pass.

## Communication Log

### 2026-06-16 19:51 UTC: User direction
**Participants**: User, Codex  
**Question/Topic**: User asked to scaffold and execute a package to patch D-Tale while minimizing upstream sync burden.  
**Outcome**: Package created and execution started.
