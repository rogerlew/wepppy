# QA Reviewer Disposition - 2026-05-20

## Context

- Package: `docs/work-packages/20260519_nodb_atomic_write_hardening/`
- Reviewer agent: `qa_reviewer`
- Scope reviewed:
  - `wepppy/nodb/base.py`
  - `tests/nodb/test_base_boundary_characterization.py`

## Round Summary

### Round 1 (Implementation first pass)

- Findings:
  - High: file mode regression on rewrite path.
  - High: replace-failure signature poisoning (`_nodb_mtime/_nodb_size` assigned before commit).
  - Medium: missing failure-path tests for atomic flow.
- Disposition: Resolved.
- Actions:
  - preserved destination mode on rewrite,
  - staged signatures locally until commit succeeds,
  - added tests for replace-failure cleanup/retry and mode behavior.

### Round 2 (Follow-up review)

- Findings:
  - Medium: first-create mode behavior could still regress to restrictive defaults.
- Disposition: Resolved.
- Actions:
  - implemented umask-derived mode for first-create atomic writes,
  - added `test_dump_atomic_replace_initial_create_uses_umask_mode`.

### Round 3 (Closure pass)

- Findings:
  - High: 0
  - Medium: 0
- Disposition: Closed.
- Evidence:
  - `wctl run-pytest tests/nodb/test_base_boundary_characterization.py --maxfail=1` -> `22 passed`.

## Residual Notes

- Broad `tests/nodb` remains blocked by unrelated baseline failure:
  - `tests/nodb/test_ron_fetch_dem_copernicus.py::test_fetch_dem_uses_copernicus_backend_when_scheme_is_copernicus`
  - `AttributeError: 'Ron' object has no attribute '_cellsize'`
- No unresolved QA High/Medium findings for this package scope.
