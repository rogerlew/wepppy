# WEPPcloud Report UI Conventions

This note captures the patterns we just introduced while modernizing the WEPP report pages. Use it whenever you touch report templates so we keep behavior and styling consistent.

## Layout & framing
- Reports always render in a full–width container. Override `body_container_class` **and** `header_container_class` with `wc-container wc-container--fluid` (see `reports/_base_report.htm`).
- Pages with a run context reuse the Pure header, not the old Bootstrap nav. `reports/_base_report.htm` already injects the run badge, name/scenario inputs, PowerUser/Unitizer toggles, etc. **Do not** include `header/_run_header_fixed.htm` directly.
- The command bar is included at the base template level; individual reports do not add it themselves.

## Script dependencies
- Reports still rely on jQuery for legacy controllers. `_base_report.htm` loads the vendored `vendor/jquery/jquery.js` before `controllers.js`; keep this ordering until the controllers are converted.
- `report_csv.js` is the only bespoke JS each report needs to add the “Download CSV” behavior. It is already pulled in by `_base_report.htm`.

## Report templating
- Render reports via Jinja and `ReportBase` implementations. Reports should pass `report` (or multiple reports) to the template and iterate over `report.header`, `report.units`, and the row iterator. Avoid duplicating query logic in the template.
- Template context should include the unitizer instance (`unitizer_nodb`) and `wepppy.nodb.unitizer.precisions` so the modal controls render. `_base_report.htm` already passes these through for shared modals.
- Use the standard modal partials (`controls/unitizer_modal.htm`, `controls/poweruser_panel.htm`). `ModalManager` binds any button with `data-modal-open`/`data-modal-dismiss` so the shared header triggers continue to function without Bootstrap.

## Tables

### Base table structure
- All tables use `.wc-table` for consistent styling (full width, border-collapse, proper padding)
- Headers (`thead th`) are bold (700 weight) with white backgrounds
- The visual separator appears as a 1px solid black border **under the units row** (the `tbody tr[data-sort-position="top"]` row), not under the header
- Table headers should be semantic `<th>` elements; data cells use `<td>`

### Table modifiers
Apply these modifier classes to adjust table appearance based on content:

- **`.wc-table--striped`**: Adds alternating row backgrounds (even rows get surface-alt color) for improved readability. Use this for most multi-row data tables.
- **`.wc-table--dense`**: Reduces padding for compact layouts when vertical space is constrained
- **`.wc-table--compact`**: Sets `width: auto` with `min-width: 50%` instead of full width. **Use this for tables with only a few columns** (2-4 columns) so they don't stretch unnecessarily across the full page width. Examples: simple return period tables, outlet summary metrics, metadata tables.

Combine modifiers as needed: `class="wc-table wc-table--compact wc-table--striped sortable"` for a narrow, striped, sortable table.

### Wrapper classes
- **`.wc-table-wrapper`**: Standard full-width wrapper for tables
- **`.wc-table-wrapper--compact`**: Constrains wrapper width for narrow tables; pair with `.wc-table--compact` on the table itself

### Sorting
- All sortable tables should add the `sortable` class and rely on `static/js/sorttable.js`. The new sorter honors `sorttable_customkey`, `data-sort-type`, and `data-sort-default` without Bootstrap dependencies.
- Use `data-sort-position="top"` on the units row to keep it anchored at the top (below headers, above data rows)
- Use `data-sort-position="bottom"` on summary/total rows that should stay at the bottom
- Sorting indicators are handled automatically by CSS (`.sortable-indicator`); no extra markup required

### Units row placement
- Units always belong in a dedicated `<tbody>` row with `data-sort-position="top"` 
- Use the `unitizer_units()` Jinja macro to generate unit cells consistently
- This row receives the black border-bottom that visually separates headers from data

### Scalar metrics
- Render scalar callouts (e.g., outlet totals) using `.wc-table-wrapper--compact` with a nested `.wc-table.wc-table--dense.wc-table--compact`
- Continue to run values through `unitizer(...)` and `unitizer_units(...)` so unitizer preferences apply in lockstep with tabular data
- Keep headings in `<th scope="row">` cells to preserve semantics for screen readers
- See `wepppy/weppcloud/templates/reports/wepp/sediment_characteristics.htm` for a complete example that mixes scalar metrics with sortable tables and CSV actions

### Example: narrow table
```jinja
<div class="wc-table-wrapper--compact">
  <table class="wc-table wc-table--compact wc-table--striped">
    <thead>
      <tr>
        <th>Metric</th>
        <th>Value</th>
      </tr>
    </thead>
    <tbody>
      <tr data-sort-position="top">
        <td></td>
        <td>{{ unitizer_units('runoff') }}</td>
      </tr>
      <tr>
        <th scope="row">Annual Runoff</th>
        <td>{{ unitizer(avg_annual_runoff, 'runoff') }}</td>
      </tr>
    </tbody>
  </table>
</div>
```

### Example: wide data table
```jinja
<div class="wc-table-wrapper">
  <table class="wc-table wc-table--striped sortable">
    <thead>
      <tr>
        <th>Hillslope</th>
        <th>Length</th>
        <th>Area</th>
        <th>Sediment</th>
        <th>Runoff</th>
      </tr>
    </thead>
    <tbody>
      <tr data-sort-position="top">
        <td></td>
        {{ unitizer_units('length', 'area', 'sediment', 'runoff') }}
      </tr>
      {% for row in hillslopes %}
      <tr>
        <td>{{ row.wepp_id }}</td>
        <td>{{ unitizer(row.length, 'length') }}</td>
        <td>{{ unitizer(row.area, 'area') }}</td>
        <td>{{ unitizer(row.sediment, 'sediment') }}</td>
        <td>{{ unitizer(row.runoff, 'runoff') }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
```

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
- Pure-based modals now rely on `ModalManager`; trigger them with `data-modal-open="modalId"` and add `data-modal-dismiss` to close controls. Reuse `controls/unitizer_modal.htm` for the unitizer so button wiring stays consistent, and migrate the PowerUser modal separately when its redesign lands.
- The CSV helper expects reports to call `_render_report_csv` (or follow the same pattern) so unitizer conversions and filenames stay consistent.
- Clipboard actions should use unobtrusive buttons: add `data-copy-table="table_id"` to a `.pure-button-link`, then attach a single listener that calls `window.copytable(id)` after `DOMContentLoaded`. Avoid inline `onclick` handlers.

### Legacy `_run_header_fixed` usage
Some older routes still include `header/_run_header_fixed.htm`, which depends on Bootstrap classes, jQuery, and the legacy navbar. When migrating those views, replace the include with the new Pure-based header pattern (`reports/_base_report.htm` shows the reference implementation). Do not try to mix Bootstrap header fragments into Pure pages.

Future work ideas:
1. Port unitizer preferences handling to vanilla JS so we can drop the jQuery dependency.
2. Add integration tests that exercise the CSV endpoint to catch unit conversion regressions automatically.
