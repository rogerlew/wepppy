# Execute WP03 - Deck.gl Map UI and Themed Controls

Execute after WP01 and WP02 are complete.

Required outcomes:
1. Add Geneva summary deck.gl HRU choropleth map for selected events.
2. Implement themeable controls with gl-dashboard-like look and behavior.
3. Fetch data with query-engine-style calls and handle empty/error states.
4. Apply water-measure color mapping using `winter` palette.

Validation commands (minimum):
- `wctl run-npm lint`
- `wctl run-npm test -- geneva_summary_report`
- `python3 wepppy/weppcloud/controllers_js/build_controllers_js.py`
- `wctl doc-lint --path docs/work-packages/20260428_geneva_hru_choropleth_wp03_deckgl_map_ui_controls`
- `git diff --check`

Lifecycle updates required:
- Update WP03 `tracker.md` with UTC progress and decisions.
- Update series orchestration board and tracker status.
