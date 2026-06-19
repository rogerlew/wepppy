# Package Authoring Review Findings

## Review Metadata

- **Review roles**: `reviewer`, `qa_reviewer`
- **Review date**: 2026-06-19 19:16-19:24 UTC
- **Reviewed scope**:
  - `docs/work-packages/20260619_ssurgo_project_sqlite_cache/package.md`
  - `docs/work-packages/20260619_ssurgo_project_sqlite_cache/tracker.md`
  - `docs/work-packages/20260619_ssurgo_project_sqlite_cache/prompts/active/ssurgo_project_sqlite_cache_execplan.md`
  - `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/subagent_review_disposition_template.md`
  - `PROJECT_TRACKER.md`
- **Validation observed**: Initial doc-lint pass before review fixes; final doc-lint rerun passed for package, tracker, active ExecPlan, review templates/artifacts, security artifact, and `PROJECT_TRACKER.md`.

## Findings

### Finding 1: Mandatory High-Impact Security Artifact Was Ambiguous

- **Severity**: high
- **Status**: accepted-fixed
- **Location**: `package.md`, `prompts/active/ssurgo_project_sqlite_cache_execplan.md`, `artifacts/subagent_review_disposition_template.md`
- **Issue**: The package marked security impact `high` but used conditional language for `security_review.md`.
- **Recommended action**: Make `artifacts/security_review.md` mandatory.
- **Disposition**: Removed conditional language, added mandatory gate wording, and created an initial `artifacts/security_review.md` with implementation evidence pending.
- **Verification**: `wctl doc-lint` passed for changed package docs/artifacts and `PROJECT_TRACKER.md`.

### Finding 2: Absolute Cache Path Serialization Risk

- **Severity**: high
- **Status**: accepted-fixed
- **Location**: `package.md`
- **Issue**: The initial scope implied persisted absolute cache paths, which can become stale after run moves or forks.
- **Recommended action**: Serialize behavior/options only and derive cache paths from `Soils.soils_dir`.
- **Disposition**: Updated package, tracker, and ExecPlan to require runtime path derivation from the active `soils_dir`.
- **Verification**: `wctl doc-lint` passed for changed package docs/artifacts and `PROJECT_TRACKER.md`.

### Finding 3: SQLite Sidecar Names Were Underspecified

- **Severity**: medium
- **Status**: accepted-fixed
- **Location**: `tracker.md`, `prompts/active/ssurgo_project_sqlite_cache_execplan.md`
- **Issue**: SQLite WAL sidecars are derived as `<cache_path>-wal` and `<cache_path>-shm`, not generic `.wal` and `.shm` extensions.
- **Recommended action**: Specify exact sidecar paths.
- **Disposition**: Updated package, tracker, and ExecPlan to require exact sidecar derivation.
- **Verification**: `wctl doc-lint` passed for changed package docs/artifacts and `PROJECT_TRACKER.md`.

### Finding 4: Batch Route Persistence Was Not Explicitly Tested

- **Severity**: medium
- **Status**: accepted-fixed
- **Location**: `package.md`, `tracker.md`, `prompts/active/ssurgo_project_sqlite_cache_execplan.md`
- **Issue**: `build-soils` returns early for batch runs, so checkbox persistence must be tested before the no-enqueue return.
- **Recommended action**: Add batch no-enqueue route coverage.
- **Disposition**: Added batch-route persistence to scope, risks, tests, and acceptance.
- **Verification**: `wctl doc-lint` passed for changed package docs/artifacts and `PROJECT_TRACKER.md`.

### Finding 5: Durable Cache Docs Were Optional Despite Known Staleness

- **Severity**: medium
- **Status**: accepted-fixed
- **Location**: `tracker.md`, `package.md`
- **Issue**: Existing docs mention shared `/dev/shm` SSURGO cache behavior; package made durable docs optional.
- **Recommended action**: Require updates to `wepppy/soils/README.md` and `wepppy/soils/ssurgo/ssurgo.md`.
- **Disposition**: Added durable docs updates to scope, success criteria, tracker, and validation commands.
- **Verification**: `wctl doc-lint` passed for changed package docs/artifacts and `PROJECT_TRACKER.md`.

### Finding 6: Full-Suite Validation Wording Was Too Weak

- **Severity**: medium
- **Status**: accepted-fixed
- **Location**: `tracker.md`, `prompts/active/ssurgo_project_sqlite_cache_execplan.md`
- **Issue**: The package allowed merely considering the full pytest suite, weaker than the work-package standard.
- **Recommended action**: Require full suite before closure unless the package owner explicitly accepts risk.
- **Disposition**: Updated tracker and ExecPlan to make `wctl run-pytest tests --maxfail=1` a closure gate unless explicit owner risk acceptance is recorded.
- **Verification**: `wctl doc-lint` passed for changed package docs/artifacts and `PROJECT_TRACKER.md`.

### Finding 7: Constructor Site Coverage Was Too Broad

- **Severity**: medium
- **Status**: accepted-fixed
- **Location**: `package.md`, `tracker.md`, `prompts/active/ssurgo_project_sqlite_cache_execplan.md`
- **Issue**: A future implementation could miss one current `SurgoSoilCollection` constructor site.
- **Recommended action**: Name all current `Soils` constructor sites and require coverage/inspection evidence.
- **Disposition**: Added `build_statsgo`, `_build_spatial_api` primary SSURGO, `_build_spatial_api` STATSGO fallback, `_build_single`, and `_build_gridded` as explicit scope and test gates.
- **Verification**: `wctl doc-lint` passed for changed package docs/artifacts and `PROJECT_TRACKER.md`.

### Finding 8: Cache Filename and STATSGO Strategy Were Open

- **Severity**: medium
- **Status**: accepted-fixed
- **Location**: `tracker.md`, `prompts/active/ssurgo_project_sqlite_cache_execplan.md`
- **Issue**: Handoff left exact cache filenames and STATSGO strategy undecided.
- **Recommended action**: Decide before implementation or define explicit alternatives.
- **Disposition**: Fixed filenames as `ssurgo_tabular_cache.sqlite` and `statsgo_tabular_cache.sqlite`.
- **Verification**: `wctl doc-lint` passed for changed package docs/artifacts and `PROJECT_TRACKER.md`.

### Finding 9: Direct Non-Soils Callers Were Not Audited

- **Severity**: low
- **Status**: accepted-fixed
- **Location**: `prompts/active/ssurgo_project_sqlite_cache_execplan.md`
- **Issue**: Direct callers exist outside `Soils`, including the bundled DB builder and `spatializer.py`.
- **Recommended action**: Disposition direct callers.
- **Disposition**: Required `surgo_tabular_db_builder.py` to pass its explicit DB path and documented `spatializer.py` as intentionally in-memory unless implementation evidence shows it needs persistence.
- **Verification**: `wctl doc-lint` passed for changed package docs/artifacts and `PROJECT_TRACKER.md`.

## Summary

- **Unresolved critical/high findings**: none
- **Unresolved medium findings**: none
- **Residual risk accepted by package owner**: none
