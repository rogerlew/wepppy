# RUNS-TTL-BULK-01 validation

Contract ancestor: `6cbd4404b`. Validation date: 2026-11-05.

## Completed checks

- Initial added Python sort regressions failed before implementation because the
  unknown key normalized to Last Modified. Initial inline-handler tests failed
  because the requested action did not exist.
- `wctl run-pytest tests/weppcloud/routes/test_user_runs_admin_scope.py tests/weppcloud/routes/test_runs_catalog_contract.py tests/weppcloud/utils/test_run_ttl.py tests/weppcloud/routes/test_project_bp.py --maxfail=1`: 104 passed.
- `wctl run-npm test -- runs_ttl_inline`: 16 passed after final scope fixes.
- Full `wctl run-npm test`: 124 suites, 1,067 tests passed after final fixes.
- `wctl run-npm lint`: passed.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref HEAD`: passed.
- `wctl run-python wepppy/weppcloud/controllers_js/build_controllers_js.py`: passed, no generated bundle diff (only inline template and test changes).
- Rendered-template Chromium smoke: passed, no page errors; see
  [record](chromium-smoke.json). It exercised sorting link and two selected
  requests, CSRF/site-prefix, success display and retained failed selection.
  A 375px check with the actual Pure/UI styles found and fixed toolbar overflow;
  the button now occupies x=25..350 inside the viewport. Changes are scoped to
  table-panel minimum width, toolbar wrapping and the new button text wrapping.
  Catalog/setter HTTP responses were mocked; this is not production evidence.
- Two independent contract reviews and final correctness/security reviews passed;
  no unresolved findings. Failed alias-load cache reuse and obsolete fetch errors
  found during review were fixed and regressed.
- Whitespace and final scoped documentation checks passed (12 Markdown files).

## Full Python gate

`wctl run-pytest tests --maxfail=1`: **13,218 passed, 423 skipped**,
5,840 warnings, 3,605.02 seconds (1:00:05). No failures. The Runs catalog and
admin-scope tests passed in this full run as well as the focused run. Skips and
warnings remain visible; this is not a claim that every optional environment
was exercised.

## Limits and operator handoff

No server persistence/authorization implementation changed; existing direct real
TTL-file/CSRF/auth tests are retained. No model artifact or data/schema mutation
applies. No production deploy occurred. On deployment, verify with an ordinary
user: ascending/descending expiration order, disabled dates last, selected-run
protection and reload persistence. Use disposable projects for mutation checks.
The scheduler pause from the earlier task remains outside this change set.
