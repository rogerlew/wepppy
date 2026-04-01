# Current Evidence Index

This file is the staging index for the evidence expected to support the next buyer-facing VPAT / ACR issue.

## Canonical Evidence

| Evidence | Purpose |
| --- | --- |
| `docs/ui-docs/acr-draft-int.md` | Living source worksheet for the future formal `VPAT 2.5Rev INT` issue |
| `docs/ui-docs/accessiblity.md` | Strategy, evidence map, update policy, and conformance posture |
| `docs/ui-docs/manual-at-pass-20260331.md` | Core-flow manual pass and formal local browser / OS / AT matrix |
| `wepppy/weppcloud/routes/usersum/weppcloud/accessibility-statement.md` | Public-facing accessibility statement source |
| `tests/weppcloud/routes/test_pure_controls_render.py` | Template and route semantics assertions |
| `tests/weppcloud/routes/test_user_runs_admin_scope.py` | Runs-template map semantics assertion |
| `wepppy/weppcloud/controllers_js/__tests__/copytext.test.js` | Copy-control accessibility regression coverage |
| `wepppy/weppcloud/controllers_js/__tests__/map_gl.test.js` | Map modal and keyboard accessibility assertions |
| `wepppy/weppcloud/static-src/tests/smoke/theme-metrics.spec.js` | Rendered contrast measurements for the validated theme set |
| `wepppy/weppcloud/static-src/tests/smoke/a11y/` | Representative anonymous and authenticated `axe` smoke coverage |

## Expected Validation Loop

- `wctl doc-lint --path docs/ui-docs`
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py tests/weppcloud/routes/test_user_runs_admin_scope.py --maxfail=1`
- `wctl run-npm test -- copytext map_gl`
- `wctl run-playwright --suite theme-metrics`
- `wctl run-playwright --suite full --grep "axe accessibility" --workers 1`

## Evidence Maintenance Rule

If a conformance-impacting change lands before production deployment, refresh the relevant evidence here and keep the update in `current/` until the production-bound VPAT package is cut.

