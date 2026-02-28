# Phase 4 Findings Resolution

## Resolution Summary
All Cycle 1 `HIGH`/`MEDIUM` findings were resolved in code/tests and cleared by Cycle 2 subagent re-review.

## Findings and Fixes

| Finding ID | Severity | Finding | Resolution | Evidence |
|---|---|---|---|---|
| F4-R1 | Medium | Skip-heavy microservice archive-boundary tests removed contract visibility. | Removed dynamic skip strategy and replaced with explicit directory-only rejection tests in `tests/microservices/test_files_routes.py`; replaced `tests/microservices/test_diff_nodir.py` module skip with directory-mode tests. | Microservices batch: `107 passed, 3 skipped` on required suite. |
| F4-R2 | Medium | Plain `<root>.nodir` paths could fail open instead of explicit retirement rejection. | Hardened `parse_external_subpath` in `wepppy/runtime_paths/paths.py` to reject all recognized `<root>.nodir` archive boundary paths. Added/updated tests asserting 400/403 rejection contracts. | `tests/microservices/test_files_routes.py` + `tests/microservices/test_diff_nodir.py` passing. |
| F4-R3 | Medium | aria2c could emit dead links to retired `.nodir` archive files. | Updated `wepppy/microservices/browse/_download.py` to exclude retired `<root>.nodir` archive files from aria2c spec generation. Updated coverage in `test_aria2c_spec_excludes_hidden_and_recorder_artifacts`. | Required microservices suite passing. |
| F4-R4 | Medium | Manifest creation boundary catch might miss typed conversion/parsing failures. | Tightened explicit catch set in `wepppy/microservices/browse/listing.py` to include `ValueError` and `TypeError` alongside `sqlite3.Error` and `OSError`, preserving rollback + rethrow contract. | `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` => PASS. |
| F4-T1 | Medium | RQ no-op guard retirement needed invariant coverage updates. | Updated RQ tests (`tests/rq/test_project_rq_fork.py`, `tests/rq/test_wepp_rq_nodir.py`) to assert directory-only semantics and removed legacy projection/mixed-state expectations. | `wctl run-pytest tests/rq --maxfail=1` => 145 passed. |

## Verification Commands (post-fix)
- `wctl run-pytest tests/nodb --maxfail=1` => `527 passed, 18 skipped`
- `wctl run-pytest tests/rq --maxfail=1` => `145 passed`
- `wctl run-pytest tests/query_engine/test_activate.py tests/query_engine/test_mcp_router.py` => `40 passed`
- `wctl run-pytest tests/weppcloud/routes/test_watar_bp.py tests/weppcloud/routes/test_observed_bp.py` => `7 passed`
- `wctl run-pytest tests/microservices/test_files_routes.py tests/microservices/test_download.py tests/microservices/test_browse_routes.py tests/microservices/test_browse_dtale.py tests/microservices/test_diff_nodir.py` => `107 passed, 3 skipped`
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` => `PASS`
- `python3 tools/code_quality_observability.py --base-ref origin/master` => report generated (observe-only)

## Final Disposition
- Unresolved `HIGH`: `0`
- Unresolved `MEDIUM`: `0`
- Escalations required: `none`
