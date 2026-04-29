# Execute WP04 - Validation, Docs Closure, and Release Notes

Execute after WP01-WP03 are complete.

Preflight context:
- WP01-WP03 are complete and WP04 is unblocked.
- There is a known pre-existing unrelated frontend lint baseline in `wepppy/weppcloud/controllers_js/__tests__/landuse_map_inline.test.js`; if it still reproduces during WP04, document it explicitly as external to this series unless remediated in-scope.

Required outcomes:
1. Run required test/lint/documentation validation commands and capture results.
2. Verify specification and implementation behavior match (including watershed-only `peak_discharge`).
3. Update all package trackers and the series orchestration board to closure state.
4. Publish residual risks and follow-up recommendations.

Validation commands (minimum):
- `wctl run-pytest tests/nodb/mods/geneva tests/query_engine tests/weppcloud/routes/test_geneva_bp.py --maxfail=1`
- `wctl run-npm lint`
- `wctl run-npm test -- geneva_summary_report`
- `wctl doc-lint --path docs/work-packages/20260428_geneva_hru_choropleth_series --path docs/work-packages/20260428_geneva_hru_choropleth_wp01_spec_and_contract_updates --path docs/work-packages/20260428_geneva_hru_choropleth_wp02_query_engine_hru_data_api --path docs/work-packages/20260428_geneva_hru_choropleth_wp03_deckgl_map_ui_controls --path docs/work-packages/20260428_geneva_hru_choropleth_wp04_validation_docs_release --path PROJECT_TRACKER.md`
- `git diff --check`

Lifecycle updates required:
- Close WP04 and series `package.md`/`tracker.md` docs.
- Move finished prompts from `prompts/active/` to `prompts/completed/` with outcomes.
