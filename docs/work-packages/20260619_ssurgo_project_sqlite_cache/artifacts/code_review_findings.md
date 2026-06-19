# Code Review Findings - SSURGO Project SQLite Cache

## Review Metadata

- **Reviewer role**: `reviewer`
- **Review date**: 2026-06-19 20:27 UTC
- **Reviewed scope**: `wepppy/nodb/core/soils.py`, `wepppy/soils/ssurgo/ssurgo.py`, new cache tests, RQ route/schema changes, soil pure UI wiring, and changed soil docs.
- **Validation observed**:
  - Passed: focused Python package tests, 137 tests.
  - Passed: `wctl run-npm test`, 84 suites / 605 tests.
  - Passed: `wctl run-npm lint`.
  - Confirmed unrelated deterministic blocker: `tests/weppcloud/routes/test_wepp_bp.py::test_view_management_effective_returns_texture_specific_preview`.

## Findings

### Finding 1: Cache Clear Must Reject Symlink Escape

- **Severity**: medium
- **Status**: accepted-fixed
- **Location**: `wepppy/nodb/core/soils.py:_clear_project_surgo_cache`
- **Issue**: Cache deletion used `abspath/commonpath`. If the project `soils` directory was a symlink to a location outside the run root, clearing could unlink cache files outside the project tree.
- **Recommended action**: Use realpath/effective-root checks before unlinking cache files or reject unmanaged symlink ancestors.
- **Disposition**: `_clear_project_surgo_cache` now checks the real `soils` directory under the real project root, checks each cache candidate under the real soils directory, deletes only exact cache files/sidecars, and still refuses non-symlink directories.
- **Verification**:
  - `tests/nodb/test_soils_ssurgo_cache.py::test_clear_project_surgo_cache_rejects_soils_dir_symlink_outside_project`
  - `wctl run-pytest tests/soils/test_ssurgo_cache.py tests/nodb/test_soils_ssurgo_cache.py --maxfail=1`

### Finding 2: New Cache Tests Must Ship

- **Severity**: medium
- **Status**: accepted-fixed
- **Location**: `tests/soils/test_ssurgo_cache.py`, `tests/nodb/test_soils_ssurgo_cache.py`
- **Issue**: The new test files were still untracked at review time; unstaged tests would not ship with the implementation.
- **Recommended action**: Include both files in the final commit.
- **Disposition**: The tests remain part of the working tree and are included in the final staging/commit set for this package.
- **Verification**:
  - `git status --short` lists both new files before staging.
  - Final commit staging includes both paths.

### Finding 3: Touched Soil Docs Must Pass Doc Lint

- **Severity**: low
- **Status**: accepted-fixed
- **Location**: `wepppy/soils/README.md:565`, `wepppy/soils/ssurgo/ssurgo.md:1015`
- **Issue**: `doc-lint` found stale broken links in changed docs.
- **Recommended action**: Repair the stale links or explicitly disposition the pre-existing gate failure.
- **Disposition**: Updated the NoDb README link in `wepppy/soils/README.md` and corrected the relative soil-file specification link in `wepppy/soils/ssurgo/ssurgo.md`.
- **Verification**:
  - `wctl doc-lint --path wepppy/soils/README.md`
  - `wctl doc-lint --path wepppy/soils/ssurgo/ssurgo.md`

## Summary

- **Unresolved critical/high findings**: none
- **Unresolved medium findings**: none
- **Residual risk accepted by package owner**: none
