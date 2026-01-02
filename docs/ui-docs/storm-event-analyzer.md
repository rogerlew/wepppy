# Storm Event Analyzer Specification
> Interactive report that replaces single-storm analysis by letting users filter and inspect storms for climate and hydrology measures.

**Version:** 0.1  
**Last Updated:** 2026-02-XX  
**Status:** Draft

## Table of Contents
- [Overview](#overview)
- [Goals](#goals)
- [UI Layout](#ui-layout)
- [Interaction Flow](#interaction-flow)
- [Data Model and Query Engine](#data-model-and-query-engine)
- [State Management](#state-management)
- [File Structure](#file-structure)
- [Unitization and Formatting](#unitization-and-formatting)
- [Sorting and Selection](#sorting-and-selection)
- [Error and Empty States](#error-and-empty-states)
- [Implementation Plan](#implementation-plan)
- [Open Questions](#open-questions)

## Overview
Storm Event Analyzer is a full-width report that lets users pick a frequency metric (ARI x duration) and then browse storms that match that intensity within a user-defined tolerance. It is designed to replace the single-storm workflow with an interactive, sortable, and query-driven event explorer.

## Goals
- Replace single-storm analysis with a multi-event, sortable exploration workflow.
- Provide direct comparison between modeled CLIGEN frequency estimates and NOAA Atlas 14 intensities.
- Allow users to filter storms by intensity tolerance (default +/-10 percent).
- Display per-event climate and hydrology attributes (depth, duration, saturation, snow cover, peak runoff).
- Visualize cumulative storm hyetographs and highlight the selected event.
- Use the Query Engine for all data fetches and filtering.
- Match the gl-dashboard code organization and state patterns.

## UI Layout
Use the full-width report layout (`reports/_base_report.htm`, `wc-container--fluid`). Structure follows the report UI conventions (`docs/ui-docs/report-ui-conventions.md`).

### Top row: two 50% tables
Two tables share a single row (50% width each, with a gap). Use CSS grid or flex:
- Wrapper: `.storm-event-analyzer__top` -> `display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1.5rem;`
- Each table uses `.wc-table wc-table--dense` inside `.wc-table-wrapper`.

#### Left: Precipitation Frequency Estimates
- Source: `wepp_cli_pds_mean_metric.csv` (same content used by climate report).
- Columns: ARIs as in the file (ex: 1, 2, 5, 10, 25, ...).
- Rows: metric labels from the file (including intensity rows).
- Units row: use `unitizer_units`.
- Cell values are clickable (see Interaction Flow).

#### Right: NOAA Atlas 14 Precipitation Frequency Estimates
- Source: `atlas14_intensity_pds_mean_metric.csv`.
- Render only when NOAA Atlas 14 data is available.
- Columns: only ARIs present in the Precipitation Frequency table (intersection).
- Rows: only 10, 15, 30, 60 minute intensities.
- Units row: use `unitizer_units`.
- Cell values are clickable and aligned to the same ARI columns as the left table.

### Filter range (radio group)
Below the top tables, place a radio group labeled "Filter range":
- Options: "+/-2%", "+/-5%", "+/-10%", "+/-20%".
- Default: 10%.
- Uses Pure-style radio controls (`.wc-choice` pattern).

Add a checkbox directly below the radio group:
- Label: "Consider first year warmup"
- Default: checked
- Behavior: when checked, exclude events from the first simulation year.

### Event Characteristics Table
Sortable table (`.wc-table.wc-table--striped.sortable`) with default sort by selected measure (ascending).
Columns:
- Measure (selected intensity, e.g., 10-min intensity in mm/hour)
- Date
- Precip (mm)
- Depth (mm)
- Duration (hours)
- Soil saturation % (T-1 day, aggregated across hillslopes from `H.soil.parquet`)
- Snow-Water (mm) (T-1 day, aggregated across hillslopes from `H.wat.parquet`)
- Peak discharge (m^3/s) from `ebe_pw0.parquet` (`peak_runoff`, unitize to CFS for English)

Row behavior:
- Clickable rows (single selection).
- Selected row visually highlighted.

### Cumulative Storm Hyetograph
Below the event table:
- Chart title: "Cumulative Storm Hyetograph".
- X-axis: duration in hours.
- Y-axis: cumulative depth (mm).
- One line per event in the Event Characteristics table.
- Selected event line opacity 1.0; others 0.4.

### Storm Event Hydrology Characteristics
Below the hyetograph:
- Runoff (mm)
- Runoff volume (m3)
- Tc (from `tc_out.parquet` when available)
- Peak discharge (m^3/s, CFS in English)
- Sediment yield
- Runoff coefficient

This section updates when a row is selected.

## Interaction Flow
1. User clicks a metric cell (e.g., 10-min intensity, 10-year ARI).
2. UI captures the selected metric and value in base units.
3. Filter range (default +/-10%) is applied to compute min/max target range.
4. Query Engine fetches storms within that range.
5. Event Characteristics table renders results and sorts by the selected measure.
6. Hyetograph renders cumulative curves for all listed events.
7. User selects an event row -> highlight row + line, update Hydrology Characteristics section.

## Data Model and Query Engine
All filtering and aggregation uses Query Engine (`/query-engine/runs/{runid}/{config}/query`).

### Required datasets (proposed)
If any dataset is missing, add a query-engine agent or produce a derived parquet:

1. **Storm event summary** (per event)
   - Source: `climate/wepp_cli.parquet` (storm intensity, parameters, depth, duration).
   - Required columns: `event_id`, `event_date`, `sim_day_index`, `duration_hours`, `depth_mm`, `tp`, `ip`, `peak_intensity_10`, `peak_intensity_15`, `peak_intensity_30`, `peak_intensity_60`.

2. **Soil saturation (T-1)**  
   - Source: `H.soil.parquet` (per hillslope, per day).
   - Aggregate: mean saturation across hillslopes for day = event_date - 1.

3. **Snow-Water (T-1)**  
   - Source: `H.wat.parquet` (`Snow-Water` column, mm).
   - Aggregate: mean snow water across hillslopes for day = event_date - 1.

4. **Hydrology metrics**  
   - Source: `ebe_pw0.parquet` (watershed), `H.ebe.parquet` (hillslope event depth).
   - Required columns: runoff volume, peak discharge (`peak_runoff`), sediment yield, runoff coefficient.
   - Peak discharge comes from `ebe_pw0.parquet.peak_runoff`; do not use `chan.out.parquet` (dual formats).
   - Runoff coefficient (event, spatialized): use outlet `runoff_volume` from `ebe_pw0.parquet` (driven by hillslope runoff volumes) and compute total event precipitation volume by area-weighting hillslope `H.ebe.parquet` `Precip` values. Formula: `C = runoff_volume_outlet_m3 / precip_volume_m3`, where `precip_volume_m3 = sum(Precip_mm * hillslope_area_m2 / 1000)`. This preserves spatialized climate while keeping the routed outlet runoff.
   - Runoff coefficient (event, spatialized): use outlet `runoff_volume` from `ebe_pw0.parquet` (driven by hillslope runoff volumes) and compute total event precipitation volume by area-weighting hillslope `H.ebe.parquet` `Precip` values. Formula: `C = runoff_volume_outlet_m3 / precip_volume_m3`, where `precip_volume_m3 = sum(Precip_mm * hillslope_area_m2 / 1000)`. This preserves spatialized climate while keeping the routed outlet runoff.

5. **Tc**  
   - Source: `tc_out.parquet` if available; otherwise omit or show "n/a".

### Query payload example (event filtering)
```json
{
  "datasets": [
    { "path": "wepp/output/event_summary.parquet", "alias": "ev" },
    { "path": "watershed/hillslopes.parquet", "alias": "hs" }
  ],
  "columns": [
    "ev.event_id",
    "ev.event_date",
    "ev.duration_hours",
    "ev.depth_mm",
    "ev.peak_intensity_10"
  ],
  "filters": [
    { "column": "ev.peak_intensity_10", "op": ">=", "value": 50.4 },
    { "column": "ev.peak_intensity_10", "op": "<=", "value": 61.6 }
  ],
  "order_by": [
    { "column": "ev.peak_intensity_10", "direction": "asc" }
  ]
}
```

### Hyetograph data
Storm traces must reproduce WEPP's 5-minute dual-exponential model in the frontend.

- Inputs: daily storm parameters (depth, duration, time-to-peak, peak intensity) from `climate/wepp_cli.parquet`.
- Output: per-event 5-minute cumulative depth series.
- Store or derive a time series per event:
  - `event_id`, `elapsed_hours`, `cumulative_depth_mm`.
  - Chart renders multiple event series in one plot.
- Authoritative implementation (Fortran, wepp-forest):
  - `disag.for` (subroutine `disag`) sets up the 5-minute step function and calls `dblex`.
  - `dblex.for` (subroutine `dblex`) computes the dual-exponential intensity (TIMEDL/INTDL).
  - `eqroot.for` (subroutine `eqroot`) solves `1 - exp(-u) = a*u` for `dblex`.
  - Call chain: `IDAT -> DISAG -> DBLEX -> EQROOT`.

## State Management
Follow the gl-dashboard pattern (single state module + subscribers).

Suggested state keys:
```javascript
{
  selectedMetric: {
    table: "wepp" | "noaa",
    durationMinutes: 10,
    ari: 10,
    value: 56.0, // base units (mm/hour)
    unitKey: "mm/hour"
  },
  filterRangePct: 10,
  eventRows: [],
  selectedEventId: null,
  hyetographSeries: [],
  hydrologySummary: null,
  unitPrefs: { ... } // from unitizer
}
```

## File Structure
Mirror gl-dashboard organization with a dedicated module directory:
```
wepppy/weppcloud/static/js/storm-event-analyzer/
├── storm-event-analyzer.js        # Orchestrator (bootstrap + wiring)
├── state.js                       # Centralized state + subscriptions
├── config.js                      # Table metadata, column configs
├── data/
│   ├── query-engine.js            # Reuse or wrap gl-dashboard helper
│   ├── event-data.js              # Fetch/filter storms, hydrate table rows
│   └── hyetograph-data.js         # Fetch series per event_id
├── ui/
│   ├── metric-table.js            # Click handlers for top tables
│   ├── filter-range.js            # +/- range radio group
│   ├── event-table.js             # Table render + selection
│   └── hydrology-summary.js       # Summary panel rendering
├── charts/
│   └── hyetograph.js              # Cumulative hyetograph renderer (D3 or SVG)
└── util/
    ├── unitizer.js                # Convert display <-> base units
    └── format.js                  # shared format helpers

wepppy/weppcloud/templates/reports/
└── storm_event_analyzer.htm       # Full-width report template
```

## Unitization and Formatting
- Display values with `unitizer(...)` in the template when possible.
- For clickable cells, store base values in `data-value` attributes, and re-render on `unitizer:preferences-changed`.
- Maintain base units (mm, mm/hour) in state and in Query Engine filters.
- Peak discharge unitization: base is `m^3/s`; English display uses CFS.
- Table units row follows report conventions (`data-sort-position="top"`).

## Sorting and Selection
- Event table uses `sorttable.js` with `sortable` class.
- Default sort: selected measure column ascending.
- Use `sorttable_customkey` on numeric cells to ensure correct sort.
- Row selection uses `aria-selected="true"` and a visible highlight class.

## Error and Empty States
- No data for selected metric: show an empty table message ("No storms in range") and blank hyetograph.
- Missing `tc_out.parquet`: hide Tc row or display "n/a".
- Missing snow cover or soil saturation: show "n/a" with muted styling, keep row clickable.
- Query Engine errors: surface a banner with the error message and keep previous results until the next successful query.

## Implementation Plan
Phases should be staffed by fresh agents with targeted prompts. Reuse agents only when context is still active and relevant.

### Phase 0: Discovery and alignment
- Confirm existing outputs for `wepp_cli_pds_mean_metric.csv`, `atlas14_intensity_pds_mean_metric.csv`, `climate/wepp_cli.parquet`, `H.soil.parquet`, `H.wat.parquet`, `H.ebe.parquet`, `ebe_pw0.parquet`, `tc_out.parquet`.
- Record the dual-exponential reference (Fortran in `wepp-forest`) and verify parameter mapping for JS.
- Confirm route registration and navigation links for `/runs/<runid>/<config>/storm-event-analyzer`.
- No tests; pure planning.

### Phase 1: Query Engine and data products
- Ensure event summary and join keys (including `sim_day_index`) are available and consistent across `wepp_cli.parquet`, `H.*`, and `ebe_pw0.parquet`.
- Add or confirm Query Engine agents for:
  - Event filtering by intensity range.
  - Soil saturation T-1 (mean across hillslopes).
  - Snow-water T-1 (mean across hillslopes).
  - Hydrology metrics (runoff volume, peak discharge, sediment yield, runoff coefficient).
  - Tc lookup when `tc_out.parquet` exists.
- Unit tests: Python tests for agent outputs, including missing dataset handling.

### Phase 2: Template skeleton and layout
- Create `templates/reports/storm_event_analyzer.htm` using the full-width report layout.
- Add containers for top tables, filter controls, event table, hyetograph, and hydrology summary.
- Wire the report to `/runs/<runid>/<config>/storm-event-analyzer`.
- Tests: Jinja render test (see `tests/weppcloud/routes/test_pure_controls_render.py`) and route load smoke check.

### Phase 3: State + top tables + filters
- Implement `static/js/storm-event-analyzer/state.js`, `config.js`, and UI modules for metric tables and filter range controls.
- Capture base-unit values via `data-value` attributes; update on `unitizer:preferences-changed`.
- Tests (Jest): state transitions, metric selection, filter range updates.

### Phase 4: Event table + selection
- Implement Query Engine fetch in `data/event-data.js`.
- Render event table with sortable columns, `sorttable_customkey`, and selection highlighting.
- Empty/error states follow spec; preserve previous results on query errors.
- Tests (Jest): query payload construction and selection behavior.

### Phase 5: Hyetograph computation + chart
- Implement `data/hyetograph-data.js` using the dual-exponential 5-minute steps.
- Implement `charts/hyetograph.js` with multi-series render and selected-line emphasis.
- Tests (Jest): numeric validation (monotonic cumulative, final depth matches input) and selection styling.

### Phase 6: Hydrology summary + Tc
- Implement `ui/hydrology-summary.js` and map summary fields from selected event.
- Hide or show `Tc` based on availability; keep "n/a" consistent with empty-state rules.
- Tests (Jest): formatting/unitization and missing-data behavior.

### Phase 7: Playwright smoke coverage
- Add `static-src/tests/smoke/storm-event-analyzer.spec.js`.
- Cover metric selection, filter changes, warmup toggle, event selection, hyetograph highlight, NOAA-missing scenario, and error banner persistence.
- Tests: run via `wctl run-npm smoke` with `SMOKE_RUN_PATH` or test-support run creation.

## Open Questions
- None currently. Add new questions here as data gaps or UI behaviors arise.
