# WEPPcloud Report UI Conventions

This note captures the patterns we just introduced while modernizing the WEPP report pages. Use it whenever you touch report templates so we keep behavior and styling consistent.

## Layout & framing
- Reports always render in a full–width container. Override `body_container_class` **and** `header_container_class` with `wc-container wc-container--fluid` (see `reports/_base_report.htm`).
- Pages with a run context reuse the Pure header, not the old Bootstrap nav. `reports/_base_report.htm` already injects the run badge, name/scenario inputs, PowerUser/Unitizer toggles, etc. **Do not** include `header/_run_header_fixed.htm` directly.
- The command bar is included at the base template level; individual reports do not add it themselves.

## Script dependencies
- Until the unitizer is rewritten, we still need jQuery on report pages. `_base_report.htm` loads the vendored `vendor/jquery/jquery.js` before `controllers.js`. Keep this ordering.
- `report_csv.js` is the only bespoke JS each report needs to add the “Download CSV” behavior. It is already pulled in by `_base_report.htm`.

## Report templating
- Render reports via Jinja and `ReportBase` implementations. Reports should pass `report` (or multiple reports) to the template and iterate over `report.header`, `report.units`, and the row iterator. Avoid duplicating query logic in the template.
- Template context should include the unitizer instance (`unitizer_nodb`) and `wepppy.nodb.unitizer.precisions` so the modal controls render. `_base_report.htm` already passes these through for shared modals.
- Use the standard modal partials (`controls/unitizer_modal.htm`, `controls/poweruser_panel.htm`). The new JS expects their close buttons to set `data-close` attributes.

## Tables
- All sortable tables should add the `sortable` class and rely on `static/js/sorttable.js`. The new sorter honors `sorttable_customkey`, `data-sort-type`, and `data-sort-default` without Bootstrap dependencies.
- Use `data-sort-position="top"` or `"bottom"` on rows you need to keep anchored (e.g., the unit row).
- Table markup uses the shared `.wc-table` classes; units belong in `unitizer_units()` rows rather than bespoke spans.
- When a column needs to stay visually associated with the highlighted metric (e.g., return period tables), add `.wc-return-period__measure` to the `<th>` and `<td>` cells so styling stays consistent. See `wepppy/weppcloud/templates/reports/wepp/return_periods.htm` for the reference.

### Scalar metrics
- Render scalar callouts (e.g., outlet totals) using `.wc-table-wrapper--compact` with a nested `.wc-table.wc-table--dense.wc-table--compact`. The wrapper constrains width while the compact modifier disables zebra striping.
- Continue to run values through `unitizer(...)` and `unitizer_units(...)` so unitizer preferences apply in lockstep with tabular data.
- Keep headings in `<th scope="row">` cells to preserve semantics for screen readers.
- See `wepppy/weppcloud/templates/reports/wepp/sediment_characteristics.htm` for a complete example that mixes scalar metrics with sortable tables and CSV actions.

## CSV exports
- Every report table should expose a subtle download action. Use:
  ```jinja
  <div class="wc-table-actions">
    <button type="button" class="pure-button pure-button-link"
            data-report-csv="table_id"
            data-report-url="{{ url_for_run('...', format='csv') }}"
            data-report-table="optional_slug">
      Download CSV
    </button>
  </div>
  ```
- `report_csv.js` adds click listeners, appends the optional `table` query parameter, and streams a CSV. When exporting multiple tables from a page, set `data-report-table` so the backend can produce distinct filenames.
- The backend helper (`_render_report_csv`) converts values to the active unitizer preferences before writing the CSV. Keep new report routes consistent with the pattern in `report_wepp_avg_annual_by_landuse`.
- Filenames follow `<runid>-<timestamp>-<report-slug>[-<table>].csv`.
- Reports with multiple tables should expose a download button per table; use the slug (e.g., `hill`, `channel`) in `data-report-table` so filenames stay unique (`<runid>-<timestamp>-slug-table.csv`).

## Miscellaneous
- Stick with the new “Download CSV” CTA below the table – no wide buttons in the header.
- Sorting indicators are handled by CSS (`.sortable-indicator`); no extra markup required beyond the `sortable` class.
- When you add new reports, inherit from `_base_report.htm` and reuse these primitives rather than creating bespoke HTML/CSS.
- The Pure-based modals rely on `data-close` attributes for the close buttons. Reuse `controls/unitizer_modal.htm` and `controls/poweruser_panel.htm` as-is so the shared header triggers continue to function.
- The CSV helper expects reports to call `_render_report_csv` (or follow the same pattern) so unitizer conversions and filenames stay consistent.
- Clipboard actions should use unobtrusive buttons: add `data-copy-table="table_id"` to a `.pure-button-link`, then attach a single listener that calls `window.copytable(id)` after `DOMContentLoaded`. Avoid inline `onclick` handlers.

### Legacy `_run_header_fixed` usage
Some older routes still include `header/_run_header_fixed.htm`, which depends on Bootstrap classes, jQuery, and the legacy navbar. When migrating those views, replace the include with the new Pure-based header pattern (`reports/_base_report.htm` shows the reference implementation). Do not try to mix Bootstrap header fragments into Pure pages.

Future work ideas:
1. Port unitizer preferences handling to vanilla JS so we can drop the jQuery dependency.
2. Add integration tests that exercise the CSV endpoint to catch unit conversion regressions automatically.
