# Phase 3 Findings Resolution

## Resolution Ledger

- finding_id: P3-H1
  source: test_guardian run 2
  severity: high
  scope: restore apply path lacked explicit archive-delete failure coverage
  disposition: resolved
  status: resolved
  resolution:
  - added `test_crawl_runs_restore_reports_exception_when_archive_removal_fails` in `tests/tools/test_migrations_nodir_bulk.py`.
  - introduced `_remove_archive_after_restore(...)` helper in `wepppy/tools/migrations/nodir_bulk.py` for deterministic archive-delete semantics and direct failure injection.
  validation:
  - `wctl run-pytest tests/tools/test_migrations_nodir_bulk.py`

- finding_id: P3-H2
  source: test_guardian run 2
  severity: high
  scope: restore interruption path could be unverified for resume safety
  disposition: resolved
  status: resolved
  resolution:
  - added `test_crawl_runs_restore_failure_is_not_marked_complete_for_resume` to ensure interrupted restore events are recorded as `exception` and not resume-complete.
  validation:
  - `wctl run-pytest tests/tools/test_migrations_nodir_bulk.py`

- finding_id: P3-M1
  source: reviewer run 2 + test_guardian run 2
  severity: medium
  scope: resume scoping risk when reusing audit logs across migration modes
  disposition: resolved
  status: resolved
  resolution:
  - implemented mode-scoped resume filtering via `_MODE_COMPLETE_STATUSES` and `_load_resume_pairs(..., mode=...)`.
  - added regression test `test_crawl_runs_resume_is_scoped_to_mode`.
  validation:
  - `wctl run-pytest tests/tools/test_migrations_nodir_bulk.py`

- finding_id: P3-M2
  source: reviewer run 2
  severity: medium
  scope: per-run recoverable exception handling coverage in migration loop
  disposition: resolved
  status: resolved
  resolution:
  - centralized explicit recovery tuple `_RECOVERABLE_EXCEPTIONS` and expanded it to include additional operational error types (e.g., `zipfile.BadZipFile`, `LookupError`, `AssertionError`) without reintroducing broad `except Exception` usage.
  validation:
  - `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
  - `wctl run-pytest tests/tools/test_migrations_nodir_bulk.py`

- finding_id: P3-M3
  source: test_guardian run 2
  severity: medium
  scope: helper edge-case coverage for directory-first parquet resolution
  disposition: resolved
  status: resolved
  resolution:
  - added helper tests:
    - `test_parquet_path_helper_uses_sidecar_when_directory_missing`
    - `test_parquet_path_helper_supports_watershed_sidecar_fallback`
    - `test_parquet_path_helper_rejects_nested_logical_sidecar_mapping`
  - hardened helper mapping to reject nested climate/watershed sidecar fallback names.
  validation:
  - `wctl run-pytest tests/tools/test_migrations_parquet_backfill.py`

- finding_id: P3-M4
  source: test_guardian run 2
  severity: medium
  scope: restore status/audit behavior coverage for newly introduced mode semantics
  disposition: resolved
  status: resolved
  resolution:
  - expanded restore-mode suite to assert dry-run/apply/resume/exception behavior and mode-specific resume safety in `tests/tools/test_migrations_nodir_bulk.py`.
  validation:
  - `wctl run-pytest tests/tools/test_migrations_nodir_bulk.py`

## Post-Fix Re-Review Closure

- `reviewer` rerun: no unresolved high/medium findings.
- `test_guardian` rerun: no unresolved high/medium findings.

## Closure Check

- high unresolved: none
- medium unresolved: none
- deferred high/medium findings: none
