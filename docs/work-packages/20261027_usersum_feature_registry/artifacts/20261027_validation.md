# Focused validation evidence

Date: 2026-10-27 UTC. Contract ancestor: `96f7df370`.

- `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py tests/weppcloud/routes/test_feature_registry_runtime.py --maxfail=1`: 219 passed, four dependency deprecation warnings, 13.65 seconds.
- After review wording correction, `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py -k feature_catalog --maxfail=1`: 8 passed, 54 deselected, 8.39 seconds.
- Direct `wctl exec weppcloud python` Flask test-client readback with real Usersum blueprint, shell and registry loaders: anonymous HTTP 200; 18 feature rows and 16 config rows matched real registry source order; prefixed index/catalog/maturity links passed. HTML written to container `/tmp/usersum-feature-catalog.html` (temporary inspection artifact). Final wording is covered by the subsequent eight real-render tests.
- Changed specifications, user/developer guides and work-package docs pass `wctl doc-lint --path` checks; `git diff --check` passes.

Presentation reuses `usersum/layout.j2`, shared maturity pills and
`wc-table-wrapper`/`wc-table` patterns. No new CSS or JavaScript. Tables use
captions, scoped headers, and keyboard-focusable overflow regions.

The operator requested light final gates based on the changes. No broad Python,
frontend suites, browser visual session, production restart or deployment was
performed. The evidence supports local implementation/HTTP validation only.
