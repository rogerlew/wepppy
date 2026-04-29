# Geneva HRU Choropleth Orchestration Board

## Purpose
Track execution order, dependency gates, and closure criteria for the Geneva Interactive Summary HRU choropleth feature series.

## Non-Negotiable Series Constraints
- `peak_discharge` remains watershed-level only.
- HRU choropleth is vector/deck.gl based (no raster-first map mode for this feature).
- Query access should follow query-engine call patterns used by gl-dashboard.
- Theming must align with gl-dashboard look-and-feel conventions.

## Colormap Baseline
- Water measures (including runoff-like measures) in gl-dashboard resolve to `winter`.
- `WATAR` category resolves to `jet2` and should not be reused for Geneva runoff map mode by default.

Reference implementation evidence:
- `wepppy/weppcloud/static/js/gl-dashboard/colors.js` (`resolveColormapName`)
- `wepppy/weppcloud/static/js/gl-dashboard/map/layers.js` (`weppFillColor`, `weppYearlyFillColor`)

## Package Matrix

| Package | Status | Primary Scope | Depends On | Blocks |
|---|---|---|---|---|
| [WP01 Spec + Contracts](../20260428_geneva_hru_choropleth_wp01_spec_and_contract_updates/package.md) | Done (2026-04-29 06:43 UTC) | Define HRU measure contract, watershed-only `peak_discharge`, artifact/query/report schema updates | None | WP02, WP03, WP04 |
| [WP02 Query Engine Data API](../20260428_geneva_hru_choropleth_wp02_query_engine_hru_data_api/package.md) | Ready | Persist/read HRU event-measure tables and expose query-engine retrieval contract | WP01 | WP03, WP04 |
| [WP03 Deck.gl Map UI + Controls](../20260428_geneva_hru_choropleth_wp03_deckgl_map_ui_controls/package.md) | Ready | Geneva summary deck.gl vector choropleth + themed controls + event selection integration | WP01, WP02 | WP04 |
| [WP04 Validation + Release Docs](../20260428_geneva_hru_choropleth_wp04_validation_docs_release/package.md) | Ready | End-to-end validation, docs finalization, rollout notes, residual risk disposition | WP01, WP02, WP03 | Series closure |

## Exit Gates by Package

### WP01 Exit Gate
- Canonical measure-scope matrix approved in spec.
- Explicitly documents `peak_discharge` watershed-only behavior.
- Defines additive/backward-compatible data/query/report contract changes.

WP01 gate note (2026-04-29 06:43 UTC):
- Completed in `wepppy/nodb/mods/geneva/specification.md` section `12.4` and artifact catalog section `15` additive note.
- Canonical HRU choropleth keys/units: `storm_id`, `hru_id`, `hru_value`, `measure_id`, `value`, `unit`.
- Legacy-run policy requires unavailable/empty HRU rows when artifact is absent and explicit scope error for `measure_id=peak_discharge`.

### WP02 Exit Gate
- Query-engine payload contract returns event+measure-filtered HRU rows.
- Join-key contract between HRU metric rows and vector geometry is validated.
- Contract tests cover unavailable/missing event-measure data paths.

### WP03 Exit Gate
- Geneva summary report renders deck.gl vector choropleth for selected event.
- Controls support theming and visually align with gl-dashboard map controls.
- Water/runoff color policy uses `winter` palette consistently.

### WP04 Exit Gate
- Required test suites and docs lint pass or blockers are explicitly documented.
- Specification, package trackers, and rollout notes are synchronized.
- Residual risks and follow-ups are recorded with owners.

## Sequencing
1. Execute WP01. (Completed 2026-04-29 06:43 UTC)
2. Execute WP02.
3. Execute WP03.
4. Execute WP04 and close series.

## Reporting Protocol
- Update each child `tracker.md` at every milestone.
- Mirror status changes in this board and the series `tracker.md`.
- Update `PROJECT_TRACKER.md` when series moves from Backlog to In Progress and then Done.
