# QA Review Findings - SSURGO Project SQLite Cache

## Review Metadata

- **Reviewer role**: `qa_reviewer`
- **Review date**: 2026-06-19 20:22 UTC
- **Reviewed scope**: Work-package artifacts, `Soils` cache helpers and SpatialAPI build path, deterministic cache tests, route/schema tests, frontend tests, and validation status.
- **Validation observed**:
  - Passed: focused package suite, 125 tests.
  - Confirmed unrelated deterministic blocker: `tests/weppcloud/routes/test_wepp_bp.py::test_view_management_effective_returns_texture_specific_preview`.

## Findings

### Finding 1: Security and Review Artifacts Were Still Open

- **Severity**: medium
- **Status**: accepted-fixed
- **Location**: `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/security_review.md`
- **Issue**: The security artifact still listed open high/medium findings and the package lacked completed subagent review artifacts.
- **Recommended action**: Complete the mandatory security review and write both subagent disposition artifacts before package closure.
- **Disposition**: Rewrote the security artifact with implemented evidence and gate status `pass`; added this QA review artifact and `code_review_findings.md`.
- **Verification**:
  - `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/security_review.md`
  - `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/code_review_findings.md`
  - `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/qa_review_findings.md`

### Finding 2: SpatialAPI Cache Clear and Use Window Was Too Short

- **Severity**: medium
- **Status**: accepted-fixed
- **Location**: `wepppy/nodb/core/soils.py:_build_spatial_api`
- **Issue**: `_build_spatial_api()` cleared or derived the project cache under a short lock, then released the lock before `SurgoSoilCollection` opened and wrote the cache. A second overlapping rebuild with cache clearing enabled could unlink the cache while the first rebuild was using it.
- **Recommended action**: Keep cache clear plus collection construction/use inside the same serialization boundary.
- **Disposition**: `_build_spatial_api()` now prepares the cache, constructs `SurgoSoilCollection`, builds WEPP soils, writes outputs, and logs invalid soils inside the existing `self.locked()` block for both SSURGO and STATSGO fallback paths.
- **Verification**:
  - `python -m py_compile wepppy/nodb/core/soils.py`
  - `wctl run-pytest tests/nodb/test_soils_ssurgo_cache.py --maxfail=1`

### Finding 3: Cache Persistence and Reuse Needed Non-Empty Coverage

- **Severity**: medium
- **Status**: accepted-fixed
- **Location**: `tests/soils/test_ssurgo_cache.py`
- **Issue**: The explicit file-cache test only asserted schema creation with an empty collection; it did not prove fetched rows persist and are reused.
- **Recommended action**: Add a deterministic monkeypatched fetch test for non-empty mukeys.
- **Disposition**: Added `test_file_backed_cache_reuses_persisted_rows`, which monkeypatches all SSURGO fetch functions, populates a file-backed cache for one mukey, constructs a second collection from the same cache, and proves no fetch function is called a second time.
- **Verification**:
  - `wctl run-pytest tests/soils/test_ssurgo_cache.py tests/nodb/test_soils_ssurgo_cache.py --maxfail=1`

### Finding 4: Diff Whitespace Needed Cleanup

- **Severity**: low
- **Status**: accepted-fixed
- **Location**: `docs/work-packages/20260619_ssurgo_project_sqlite_cache/tracker.md`
- **Issue**: `git diff --check origin/master` reported trailing whitespace in the tracker quick-status block.
- **Recommended action**: Remove trailing whitespace.
- **Disposition**: Normalized the quick-status block to ordinary markdown lines without trailing spaces.
- **Verification**:
  - `git diff --check origin/master`

### Finding 5: Full-Suite Blocker Is Outside This Package

- **Severity**: note
- **Status**: deferred
- **Location**: `tests/weppcloud/routes/test_wepp_bp.py::test_view_management_effective_returns_texture_specific_preview[clay-1.1-2.1-0.11]`
- **Issue**: The full pytest suite still fails on a deterministic WEPP disturbed preview route test.
- **Recommended action**: Treat it as unrelated to this package unless owner directs this package to also repair disturbed-management preview semantics.
- **Disposition**: Deferred as a separate WEPP disturbed preview issue. The test fails standalone outside the SSURGO cache surface and appears to conflict with existing disturbed normalization unit coverage.
- **Verification**:
  - Standalone reproduction recorded in `tracker.md`.

## Summary

- **Unresolved critical/high findings**: none
- **Unresolved medium findings**: none
- **Residual risk accepted by package owner**: Full pre-handoff pytest is not green because of the unrelated WEPP disturbed preview blocker recorded above; targeted package validation is green.
