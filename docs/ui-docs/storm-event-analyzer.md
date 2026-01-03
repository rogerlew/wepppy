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
- Label: "Consider first year warm-up"
- Default: checked
- Behavior: when checked, exclude events from the first simulation year.

### Event Characteristics Table
Sortable table (`.wc-table.wc-table--striped.sortable`) with default sort by selected measure (ascending).
Columns:
- Measure (selected intensity, e.g., 10-min intensity in mm/hour)
- Date (YY-MM-DD)
- Depth (mm)
- Duration (hours)
- Soil saturation % (T-1 day, aggregated across hillslopes from `H.soil.parquet`)
- Snow coverage (T-1 day, percent of hillslope area with snow-water > 0 from `H.wat.parquet`)
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
   - Required columns: `sim_day_index` (absolute), `year`, `julian`, `month`, `day_of_month` (or a derived `event_date`), `duration_hours`, `depth_mm`, `tp`, `ip`, `peak_intensity_10`, `peak_intensity_15`, `peak_intensity_30`, `peak_intensity_60`.

2. **Soil saturation (T-1)**  
   - Source: `H.soil.parquet` (per hillslope, per day).
   - Aggregate: mean saturation across hillslopes for day = event_date - 1.
   - Join: use absolute `sim_day_index`; fall back to `year + julian` for legacy runs.

3. **Snow coverage (T-1)**  
   - Source: `H.wat.parquet` (`Snow-Water` column, mm + `Area`).
   - Aggregate: sum area of hillslopes with `Snow-Water` > 0 divided by total area, * 100.
   - Join: use `sim_day_index`; fall back to `year + julian` for legacy runs.

4. **Hydrology metrics**  
   - Source: `ebe_pw0.parquet` (watershed), `H.ebe.parquet` (hillslope event depth).
   - Required columns: runoff volume, peak discharge (`peak_runoff`), sediment yield, runoff coefficient.
   - Join: use `sim_day_index`; fall back to `year + julian` for legacy runs.
   - Peak discharge comes from `ebe_pw0.parquet.peak_runoff`; do not use `chan.out.parquet` (dual formats).
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
    "ev.sim_day_index",
    "ev.year",
    "ev.month",
    "ev.day_of_month",
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
  - `sim_day_index`, `elapsed_hours`, `cumulative_depth_mm`.
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
  selectedEventSimDayIndex: null,
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
│   └── hyetograph-data.js         # Fetch series per sim_day_index
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

wepppy/query_engine/
└── storm_event_analyzer.py         # Payload helpers + join strategy for analyzer queries

wepppy/tests/query_engine/
└── test_storm_event_analyzer.py    # Query-engine unit coverage for analyzer payloads
```

## Unitization and Formatting
- Display values with `unitizer(...)` in the template when possible.
- For clickable cells, store base values in `data-value` attributes, and re-render on `unitizer:preferences-changed`.
- Maintain base units (mm, mm/hour) in state and in Query Engine filters.
- Peak discharge unitization: base is `m^3/s`; English display uses CFS.
- Soil saturation values are 0..1 fractions in `H.soil.parquet`; convert to percent for display.
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

### Phase 0 Handoff (2026-01-02)
Superseded by **Phase 0b Handoff (2026-01-02)** for interchange normalization; retained for historical context.
**Test target**
- URL: `https://wc.bearhive.duckdns.org/weppcloud/runs/chinless-half-hour/disturbed9002/storm-event-analyzer`
- Run root: `/wc1/runs/ch/chinless-half-hour/`

**Route check**
- HTTP 200 with cap-gate HTML (verification required); no 500 observed.
- Gate reason still enforced via `requires_cap`; verified-user path not exercised in this pass.

**Availability matrix**

| Dataset | Status | Path | Key columns / notes |
| --- | --- | --- | --- |
| `wepp_cli_pds_mean_metric.csv` | present | `/wc1/runs/ch/chinless-half-hour/climate/wepp_cli_pds_mean_metric.csv` | ARIs 1,2,5,10,25; rows include depth, duration, 10/15/30/60-min intensities; units mm, hours, mm/hour. |
| `atlas14_intensity_pds_mean_metric.csv` | present | `/wc1/runs/ch/chinless-half-hour/climate/atlas14_intensity_pds_mean_metric.csv` | ARIs 1..1000; durations include 10/15/30/60-min; take ARI intersection with WEPP table. |
| `climate/wepp_cli.parquet` | present | `/wc1/runs/ch/chinless-half-hour/climate/wepp_cli.parquet` | `sim_day_index` (absolute 1..16437), `julian` (day-of-year), `year`, `month`, `day_of_month`, `prcp` (mm), `dur` (hours), `tp`, `ip`, `peak_intensity_10/15/30/60`, `storm_duration_hours` == `dur`. |
| `H.soil.parquet` | present | `/wc1/runs/ch/chinless-half-hour/wepp/output/interchange/H.soil.parquet` | `sim_day_index` == `julian` (day-of-year, resets each year), `year`, `month`, `day_of_month`, `Saturation` (0..1 fraction). Join via `year + julian` for T-1. |
| `H.wat.parquet` | present | `/wc1/runs/ch/chinless-half-hour/wepp/output/interchange/H.wat.parquet` | `sim_day_index` absolute (matches climate), `julian`, `Snow-Water` (mm), `Area` (m^2). Join via `sim_day_index` or `year + julian`. |
| `H.ebe.parquet` | present | `/wc1/runs/ch/chinless-half-hour/wepp/output/interchange/H.ebe.parquet` | No `sim_day_index`; has `julian`, `year`, `month`, `day_of_month`, `Precip`, `Runoff`, `Sed.Del`. |
| `ebe_pw0.parquet` | present | `/wc1/runs/ch/chinless-half-hour/wepp/output/interchange/ebe_pw0.parquet` | No `sim_day_index`; has `julian`, `year`, `month`, `day_of_month`, `precip`, `runoff_volume`, `peak_runoff`, `sediment_yield`, `element_id`. |
| `tc_out.parquet` | missing | n/a | `tc_out.txt` exists under `/wc1/runs/ch/chinless-half-hour/wepp/output/` and `/wc1/runs/ch/chinless-half-hour/wepp/runs/`, but no parquet emitted into `wepp/output/interchange/`. |
| `watershed/hillslopes.parquet` | present | `/wc1/runs/ch/chinless-half-hour/watershed/hillslopes.parquet` | `area` and `wepp_id` available for runoff coefficient aggregation. |

**Event identity / join notes**
- Use absolute `sim_day_index` as the canonical event key once interchange normalization is applied.
- For legacy runs that have not been regenerated, join on `year + julian`.

**Hyetograph notes (Fortran mapping)**
- Sources: `/workdir/wepp-forest/src/disag.for`, `/workdir/wepp-forest/src/dblex.for`, `/workdir/wepp-forest/src/eqroot.for`.
- Inputs from `wepp_cli.parquet`: `depth_mm = prcp`, `duration_hours = dur`, `timep = tp` (0..1), `ip` (relative peak intensity).
- Clamps: `ip < 1 -> 1`, `timep <= 0 -> 0.01`, `timep > 1 -> 1` (then constant-intensity path); `dblex` clamps `ip <= 60`, `timep <= 0.99`.
- `eqroot`: solves `1 - exp(-u) = a*u` with `a = 1/ip`, returns `u`. Then `b = u/timep`, `a = ip*exp(-u)`, `d = u/(1 - timep)`.
- Step function: `ninten = 11` by default; `deltfq = 1/(ninten-1)`. For each `fqx += deltfq`, compute `timedl` using the double-exponential formulas and `intdl = deltfq / (timedl(i+1) - timedl(i))`. Convert to dimensional series: `timem = timedl * dur`, `intsty = intdl * depth / dur`. Enforce >= 300s step by reducing `ninten` if needed.

**Missing columns / unit notes**
- `Saturation` is 0..1 fraction (convert to percent for display).
- `storm_duration_hours` equals `dur` (hours); `peak_intensity_*` duplicates the labeled intensity columns.

**Risks / blockers**
- `tc_out.parquet` still missing from `wepp/output/interchange/`, so Tc display must remain optional or `n/a`.
- Event identity requires a derived mapping for `H.ebe.parquet` and `ebe_pw0.parquet` to align with `sim_day_index`.
- Route is gated; verification required before seeing the actual report template in a browser.

**Suggested follow-ups for Phase 1**
- Generate `tc_out.parquet` in `wepp/output/interchange/` (confirm `watershed_tc_out_interchange.py` runs post-WEPP).
- Standardize joins on `sim_day_index` for normalized datasets and `year + julian` for legacy runs.

**Phase 1 readiness**
- Ready with caveats: Tc parquet is still missing and legacy runs require `year + julian` joins until interchange is regenerated.

### Phase 0b: Interchange normalization (absolute sim_day_index)
- Goal: Normalize `sim_day_index` across `H.soil.parquet`, `H.ebe.parquet`, and `ebe_pw0.parquet` so the Storm Event Analyzer can key events by `sim_day_index` alone.
- Scope:
  - Add absolute `sim_day_index` to `H.ebe.parquet` rows and schema.
  - Convert `H.soil.parquet` `sim_day_index` from day-of-year to absolute day since simulation start.
  - Add absolute `sim_day_index` to `ebe_pw0.parquet` rows and schema.
  - Use `_compute_sim_day_index` with CLI calendar lookup for non-Gregorian years.
  - Ensure `run_wepp_hillslope_interchange` and `run_wepp_watershed_interchange` pass `start_year` into soil/ebe interchange writers.
  - Generate `tc_out.parquet` under `wepp/output/interchange/` if missing when `tc_out.txt` exists.
- Versioning:
  - Bump `INTERCHANGE_VERSION` minor (schema additions).
  - Update `wepppy/wepp/interchange/README.md` if it still documents tuple/patch semantics.
- Tests:
  - Update soil interchange tests to assert absolute `sim_day_index` (not equal to `julian`).
  - Add/extend tests for `H.ebe.parquet` and `ebe_pw0.parquet` to assert `sim_day_index` presence, ordering, and calendar correctness.
  - Run `wctl run-pytest tests/wepp/interchange/...` for the modified modules.

### Phase 0b Handoff (2026-01-02)
**Objective**
- Normalize `sim_day_index` to be absolute and CLI-calendar aware across event datasets so the UI can use it as the sole event key.

**Changes delivered**
- `climate/wepp_cli.parquet`: now includes `julian` and absolute `sim_day_index` (1-indexed since simulation start) in both Climate NoDb export and interchange fallback export.
- `H.ebe.parquet`: added absolute `sim_day_index` using `_compute_sim_day_index` with CLI calendar lookup.
- `H.soil.parquet`: `sim_day_index` now absolute (not day-of-year); soil writer accepts `start_year` and is wired through `run_wepp_hillslope_interchange`.
- `ebe_pw0.parquet`: added absolute `sim_day_index` with CLI calendar lookup; `simulation_year` preserved.
- `tc_out.parquet`: now written under `wepp/output/interchange/` when `tc_out.txt` exists.
- Interchange version bumped to `1.2`; README updated to match major/minor semantics.

**Join guidance**
- Preferred join key across climate, soil, water, and event outputs: `sim_day_index`.
- For legacy runs without regenerated interchange outputs, fall back to `year + julian` joins.

**Tests run**
- `wctl run-pytest tests/wepp/interchange/test_soil_interchange.py`
- `wctl run-pytest tests/wepp/interchange/test_watershed_ebe_interchange.py`
- `wctl run-pytest tests/wepp/interchange/test_ebe_interchange.py`

**Remaining follow-ups**
- Re-run interchange on existing runs to materialize the new columns and updated version manifest.
- Confirm `tc_out.parquet` appears under `wepp/output/interchange/` after rerun.

### Phase 1: Query Engine and data products
Status: complete (2026-01-02). Phase 1 is done; see **Phase 1 Handoff**. Tasks below retained for reference.
- Ensure the event summary includes `sim_day_index` (absolute), `year`, `julian`, and calendar date fields (`month`, `day_of_month` or derived `event_date`).
- Normalize join strategy: `sim_day_index` across climate, `H.wat.parquet`, `H.soil.parquet`, `H.ebe.parquet`, and `ebe_pw0.parquet`, with `year + julian` fallback for legacy runs.
- Add or confirm Query Engine agents for:
  - Event filtering by intensity range.
  - Soil saturation T-1 (mean across hillslopes).
  - Snow-water T-1 (mean across hillslopes).
  - Hydrology metrics (runoff volume, peak discharge, sediment yield, runoff coefficient).
  - Tc lookup when `tc_out.parquet` exists.
- Verify `tc_out.parquet` exists after interchange reruns; keep Tc optional when missing.
- Unit tests: Python tests for agent outputs, including missing dataset handling.

### Phase 1 Handoff (2026-01-02)
**Delivered**
- Added query-engine payload helpers for Storm Event Analyzer under `wepppy/query_engine/storm_event_analyzer.py` with explicit dataset constants, intensity filtering, and T-1 joins.
- Join strategy selects `sim_day_index` when interchange version >= 1.1 (current is 1.2) and enforces column presence; legacy runs fall back to `year + julian` using date arithmetic for T-1 joins.
- Hydrology payload computes runoff coefficient from `ebe_pw0.parquet` runoff volume and area-weighted `H.ebe.parquet` precipitation volume; Tc payload is optional when `tc_out.parquet` is missing.
- NOAA Atlas 14 CSV generation is wired into climate building; UI should still treat the file as optional when missing.
- Unit tests cover join strategy selection, legacy fallback joins, intensity filter payloads, hydrology coefficient presence, and missing Tc behavior (`tests/query_engine/test_storm_event_analyzer.py`).

**Tests run**
- `wctl run-pytest ./tests/query_engine/test_storm_event_analyzer.py` (8 passed; 2 warnings from pytz/pyparsing)

**Remaining gaps**
- Front-end wiring for these payloads is pending (Phase 2+).

### Phase 2: Template skeleton and layout
- Create `templates/reports/storm_event_analyzer.htm` using the full-width report layout.
- Add containers for top tables, filter controls, event table, hyetograph, and hydrology summary.
- Wire the report to `/runs/<runid>/<config>/storm-event-analyzer`.
- Tests: Jinja render test (see `tests/weppcloud/routes/test_pure_controls_render.py`) and route load smoke check.

### Phase 2 Handoff (2026-01-02)
**Delivered**
- Replaced the placeholder report with a full-width template skeleton in `wepppy/weppcloud/templates/reports/storm_event_analyzer.htm`.
- Added top table grid, filter controls, event table, hyetograph placeholder, and hydrology summary containers with required hook IDs/classes.
- Included section-level empty-state copy and sortable table structure per report conventions.
- Added minimal inline layout styles for the two-column grid and hyetograph container.

**Tests run**
- Not run (template-only change).

### Phase 3: State + top tables + filters
- Implement `static/js/storm-event-analyzer/state.js`, `config.js`, and UI modules for metric tables and filter range controls.
- Capture base-unit values via `data-value` attributes; update on `unitizer:preferences-changed`.
- Tests (Jest): state transitions, metric selection, filter range updates.

### Phase 3 Handoff (2026-01-02)
**Delivered**
- Added a Storm Event Analyzer front-end module set under `wepppy/weppcloud/static/js/storm-event-analyzer/` with state, CSV parsing, table rendering, and filter wiring.
- Dynamic ARI headers/rows now render from `climate/wepp_cli_pds_mean_metric.csv` fetched directly via `url_for_run("download/...")`, storing base-unit values in `data-value` attributes for Phase 4.
- NOAA CSV loading is optional; the NOAA table hides and the "NOAA data unavailable" message shows when missing.
- Unitizer hooks re-render values and units on `unitizer:preferences-changed`.
- Added Jest coverage for state updates, CSV parsing, dynamic headers/rows, and NOAA availability; updated `wepppy/weppcloud/static-src/jest.config.mjs`.

**Tests run**
- Manual testing verifies frequency tables render, and unitization is functional

### Phase 4: Event table + selection
- Implement Query Engine fetch in `data/event-data.js`.
- Render event table with sortable columns, `sorttable_customkey`, and selection highlighting.
- Empty/error states follow spec; preserve previous results on query errors.
- Hide the WEPP empty-state message once event rows render; show it only when the event table is truly empty or failed.
- Tests (Jest): query payload construction and selection behavior.

### Phase 4 Handoff (2026-01-02)
**Delivered**
- Added Query Engine client + event data loader (`wepppy/weppcloud/static/js/storm-event-analyzer/data/query-engine.js`, `data/event-data.js`) with intensity filtering, warm-up exclusion, and per-event soil/snow/peak discharge lookups.
- Wired dynamic event table rendering/selection with unitizer formatting (`wepppy/weppcloud/static/js/storm-event-analyzer/ui/event-table.js`) and state-driven refresh logic in `wepppy/weppcloud/static/js/storm-event-analyzer/main.js`.
- Added error banner + empty-state toggles in `wepppy/weppcloud/templates/reports/storm_event_analyzer.htm`, including hiding the WEPP empty message once event rows exist.
- Added Jest coverage for payload construction and row selection in `wepppy/weppcloud/static/js/storm-event-analyzer/__tests__/event-data.test.js` and `wepppy/weppcloud/static/js/storm-event-analyzer/__tests__/event-table.test.js`.

**Tests run**
- `wctl run-npm test -- storm-event-analyzer` (passes; VM Modules warning from Node).

### Phase 5: Hyetograph computation + chart
- Implement `data/hyetograph-data.js` using the dual-exponential 5-minute steps.
- Implement `charts/hyetograph.js` with multi-series render and selected-line emphasis.
- Tests (Jest): numeric validation (monotonic cumulative, final depth matches input) and selection styling.

### Phase 5 Handoff (2026-01-02)
**Delivered**
- Added dual-exponential hyetograph computation (`wepppy/weppcloud/static/js/storm-event-analyzer/data/hyetograph-data.js`) and appended tp/ip fields to event payload mapping.
- Added canvas hyetograph renderer aligned with gl-dashboard theming (`wepppy/weppcloud/static/js/storm-event-analyzer/charts/hyetograph.js`) and wired state updates in `wepppy/weppcloud/static/js/storm-event-analyzer/main.js`.
- Added Jest coverage for hyetograph numeric monotonicity and selected-series emphasis.
- Reworked event selection UX: radio column + row click selection, header-only sorting, and distinct border styling for selected rows (`wepppy/weppcloud/static/js/storm-event-analyzer/ui/event-table.js`, `wepppy/weppcloud/templates/reports/storm_event_analyzer.htm`).
- Enabled line-click selection in the hyetograph chart (`wepppy/weppcloud/static/js/storm-event-analyzer/charts/hyetograph.js`).
- Updated frequency tables: removed unit rows, added NOAA spacer rows for alignment, and inserted WEPP Depth/Duration rows that drive event filtering (`wepppy/weppcloud/static/js/storm-event-analyzer/data/frequency-data.js`, `wepppy/weppcloud/static/js/storm-event-analyzer/ui/frequency-table.js`, `wepppy/weppcloud/templates/reports/storm_event_analyzer.htm`).
- Adjusted event filtering/measure units to support depth/duration metrics and added a cache-busting import to avoid stale module exports (`wepppy/weppcloud/static/js/storm-event-analyzer/data/event-data.js`, `wepppy/weppcloud/static/js/storm-event-analyzer/main.js`).

**Tests run**
- `wctl run-npm test -- --testPathPattern storm-event-analyzer` (passes; npm warns about --testPathPattern; VM Modules warning; expected console.warn from event-data test)

### Phase 6: Hydrology summary + Tc
- Implement `ui/hydrology-summary.js` and map summary fields from selected event.
- Hide or show `Tc` based on availability; keep "n/a" consistent with empty-state rules.
- Tests (Jest): formatting/unitization and missing-data behavior.

### Phase 6 Handoff (2026-01-02)
**Delivered**
- Added hydrology summary renderer with Unitizer formatting, empty-state toggles, and Tc hide/placeholder behavior (`wepppy/weppcloud/static/js/storm-event-analyzer/ui/hydrology-summary.js`).
- Expanded event data payloads to include runoff volume, sediment yield, runoff coefficient, runoff depth, and Tc lookup with sim_day_index-first fallback (`wepppy/weppcloud/static/js/storm-event-analyzer/data/event-data.js`).
- Wired summary updates to event selection + unitizer changes in `wepppy/weppcloud/static/js/storm-event-analyzer/main.js`.
- Added Jest coverage for summary rendering and Tc availability handling.

**Tests run**
- `wctl run-npm test -- --testPathPattern storm-event-analyzer` (passes; npm warns about --testPathPattern; VM Modules warning; expected console.warn from event-data test)
- Manual test verifies the hydrology summary renders and unitzation is supported.

### Phase 7: Playwright smoke coverage
Status: complete (2026-01-02). Phase 7 is done; see **Phase 7 Handoff**.
- Add `static-src/tests/smoke/storm-event-analyzer.spec.js`.
- Cover metric selection, filter changes, warm-up toggle, event selection, hyetograph highlight, NOAA-missing scenario, and error banner persistence.
- Tests: run via `wctl run-npm smoke` with `SMOKE_RUN_PATH` or test-support run creation.

### Phase 7 Handoff (2026-01-02)
**Delivered**
- Added a Storm Event Analyzer smoke spec covering metric selection, filter and warm-up toggles, event selection summary updates, hyetograph selection state, NOAA-missing handling, and error banner persistence (`wepppy/weppcloud/static-src/tests/smoke/storm-event-analyzer.spec.js`).

**Tests run**
- `SMOKE_RUN_PATH=\"https://wc.bearhive.duckdns.org/weppcloud/runs/chinless-half-hour/disturbed9002/storm-event-analyzer\" wctl run-npm smoke -- tests/smoke/storm-event-analyzer.spec.js` (passes; rerun 2026-01-02)

### Phase 8: Event Characteristics table enhancements
Status: complete (2026-01-02). Phase 8 is done; see **Phase 8 Handoff**.
- Remove redundant Precip column from the Event Characteristics table.
- Switch snow metric to Snow coverage (%) based on hillslope area with Snow-Water > 0 at T-1.
- Clarify Date units as YY-MM-DD and update T-1 labels to use subscript.
- Tests: run `wctl run-npm test -- storm-event-analyzer` and smoke against a public run.

### Phase 8 Handoff (2026-01-02)
**Delivered**
- Removed the Precip column from the Event Characteristics table and updated render logic/tests (`wepppy/weppcloud/templates/reports/storm_event_analyzer.htm`, `wepppy/weppcloud/static/js/storm-event-analyzer/ui/event-table.js`, `wepppy/weppcloud/static/js/storm-event-analyzer/__tests__/event-table.test.js`).
- Replaced Snow-water depth with Snow coverage (%) derived from hillslope area with snow-water > 0 at T-1, updating query payloads and UI bindings (`wepppy/query_engine/storm_event_analyzer.py`, `wepppy/weppcloud/static/js/storm-event-analyzer/data/event-data.js`, `wepppy/weppcloud/templates/reports/storm_event_analyzer.htm`).
- Clarified Date units to YY-MM-DD and updated T-1 label formatting (`wepppy/weppcloud/static/js/storm-event-analyzer/ui/event-table.js`, `wepppy/weppcloud/templates/reports/storm_event_analyzer.htm`).

**Tests run**
- Not run (wctl run-npm test -- storm-event-analyzer; wctl run-npm smoke -- tests/smoke/storm-event-analyzer.spec.js)

## Open Questions
- None currently. Add new questions here as data gaps or UI behaviors arise.
