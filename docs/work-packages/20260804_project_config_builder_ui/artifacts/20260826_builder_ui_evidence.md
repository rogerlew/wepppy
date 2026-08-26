# WP07 Config Builder UI evidence

## Automated evidence

- `wctl run-npm lint`: passed.
- `wctl run-npm test`: 106 suites and 786 tests passed.
- `wctl run-pytest tests --maxfail=1`: 6,902 passed, 63 skipped.
- `wctl run-stubtest wepppy.nodb.config_builder.schema`: passed.
- `wctl run-stubtest wepppy.nodb.config_builder.resolver`: passed.
- `wctl check-test-stubs`: passed.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`: passed with net delta zero.
- `wctl run-playwright --project runs0 --workers 1 --grep 'authenticated config builder'`: one authenticated test passed against the development stack with zero axe violations.

## Browser evidence

The authenticated smoke loaded registered choices from rq-engine, verified no
document overflow at a 640 by 900 viewport, tabbed from Locale to Elevation
source, and completed the structural WCAG 2.0/2.1 A/AA axe rules enabled by the
repository suite. The page makes no create request during this check. Creation
remains governed by the default-off WP06 writer flag.

## Regression coverage

Jest covers stable-ID payloads, exact server review rendering, dependent choice
replacement and announcement, role-described cell-size controls, actionable
error focus, duplicate-submit suppression, stale-revision refresh, retained
valid choices, and navigation to the server-provided config location. Flask
tests cover authentication, semantic/error relationships, and the unchanged
named Interface creation forms.
