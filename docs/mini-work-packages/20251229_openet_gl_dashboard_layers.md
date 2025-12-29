# OpenET GL Dashboard Layer + Monthly Slider
> Spec + implementation plan for adding OpenET monthly overlays to the gl-dashboard map.
> Status: draft

## Context
OpenET time series data is written to `openet/openet_ts.parquet` but the gl-dashboard does not surface it in the Layers control. OpenET is the first monthly map layer, so the yearly slider is insufficient. We need a monthly time slider that behaves like the year slider (play/pause + graph split placement) and only appears when an OpenET overlay is active.

## Goals
- Surface an OpenET section in the gl-dashboard Layers control when `openet/openet_ts.parquet` exists.
- Provide a radio option per `dataset_key` (ex: `ensemble`, `eemetric`).
- Introduce a monthly time slider with the same play behavior and split-pane placement as the yearly slider.
- Ensure the monthly slider shows only for OpenET; hide the yearly slider while OpenET is active.

## Non-Goals
- No changes to OpenET acquisition, Climate Engine API calls, or NoDb logic.
- No OpenET graphs (map-only for now).
- No new backend endpoints beyond Query Engine use of `openet/openet_ts.parquet`.

## Data Contract
Source: `openet/openet_ts.parquet`

| Column | Type | Notes |
| --- | --- | --- |
| `topaz_id` | string | Hillslope id (stringified) |
| `year` | int | Calendar year |
| `month` | int | Calendar month (1-12) |
| `dataset_key` | string | `ensemble`, `eemetric` |
| `value` | float | ET (mm) |
| `units` | string | `mm` |

Query Engine payload examples (base scenario only):
```json
{
  "datasets": [{ "path": "openet/openet_ts.parquet", "alias": "openet" }],
  "columns": ["DISTINCT openet.dataset_key AS dataset_key"],
  "order_by": ["dataset_key"]
}
```
```json
{
  "datasets": [{ "path": "openet/openet_ts.parquet", "alias": "openet" }],
  "columns": ["DISTINCT openet.year AS year", "openet.month AS month"],
  "order_by": ["year", "month"]
}
```
```json
{
  "datasets": [{ "path": "openet/openet_ts.parquet", "alias": "openet" }],
  "columns": ["openet.topaz_id AS topaz_id", "openet.value AS value"],
  "filters": [
    { "column": "openet.dataset_key", "op": "=", "value": "ensemble" },
    { "column": "openet.year", "op": "=", "value": 2023 },
    { "column": "openet.month", "op": "=", "value": 7 }
  ]
}
```

## UX Requirements
- Layers sidebar shows **OpenET** section only if the parquet exists and has at least one `dataset_key`.
- The OpenET section lists radio buttons for each `dataset_key`.
- Selecting a dataset key:
  - Deselects other subcatchment overlays.
  - Fetches OpenET values for the selected month + dataset.
  - Shows the monthly slider and hides the yearly slider.
- Monthly slider behavior:
  - Label shows month + year (ex: `Jul 2023`).
  - Min/max labels show first/last available month.
  - Play/pause cycles month-by-month and wraps to the start.
  - Same split-pane placement as the yearly slider (top slot above the graph panel).
- When OpenET is inactive:
  - Monthly slider is hidden.
  - Yearly slider reverts to existing behavior (RAP/WEPP yearly/climate graphs only).

## State Additions
`wepppy/weppcloud/static/js/gl-dashboard/state.js`
- `openetLayers: []`
- `openetSummary: null` (topaz_id -> value)
- `openetRanges: {}` (min/max for legend)
- `openetMetadata: null` (month list, min/max, dataset keys)
- `openetSelectedDatasetKey: null`
- `openetSelectedMonthIndex: null` (index into `openetMetadata.months`)

## Detection + Data Flow
1. `layers/detector.js` adds `detectOpenetOverlays`:
   - Uses `postBaseQueryEngine` only (OpenET is always base-only).
   - Queries distinct `dataset_key` and `(year, month)` once per load.
   - Builds `openetMetadata.months` as a sorted list of `{ year, month, label }` and uses month index (not computed range).
   - Picks defaults:
     - dataset: `ensemble` if present, else first key.
     - month: latest month in the list.
   - Builds `openetLayers` with `visible: false` so the user explicitly selects a dataset.
   - Defers summary fetch to the OpenET data manager when a dataset is selected.
2. `layers/orchestrator.js`:
   - Calls `detectOpenetOverlays()` during initial `detectLayers()` run.
   - Updates state with metadata + layers + summary.
   - Triggers `updateLayerList()` and `applyLayers()`.

## OpenET Data Manager
Add `data/openet-data.js` with:
- `refreshOpenetData()`:
  - Uses `postBaseQueryEngine` only (scenario state ignored).
  - Reads `openetSelectedDatasetKey` + selected month/year from the month index list.
  - Updates `openetSummary` and `openetRanges`.
  - Returns `true` on data changes (so gl-dashboard can refresh legends + map).

Range calculation: compute min/max across visible values; fall back to `{ min: 0, max: 1 }` if empty.
Performance: assume Query Engine is performant; keep calls minimal by only re-querying when dataset key or month index changes.

## Map Layer Rendering
`map/layers.js`
- Add `buildOpenetLayers()` similar to RAP/WEPP:
  - Uses `state.openetLayers`, `state.openetSummary`, `state.subcatchmentsGeoJson`.
  - Uses winter colormap or explicit OpenET palette.
  - Update triggers: selected month index + dataset key + ranges.
- Add OpenET tooltip entry in `formatTooltip()`:
  - Include dataset key and selected month label.
- Add OpenET to legend resolution:
  - `getActiveLayersForLegend()` includes OpenET.
  - `renderLegendForLayer()` uses `openetRanges` and `mm` units.

## Monthly Slider Implementation
Option A (preferred): new module `ui/month-slider.js`
- Mirror `ui/year-slider.js` API.
- Accept `formatValue` callback for labels (ex: `Jul 2023`).
- `setRange(min, max, current)` maps to month index range.

Option B: generalize `ui/year-slider.js` to `ui/time-slider.js` and instantiate twice.

Template/CSS updates (`templates/gl_dashboard.htm`):
- Add new slider markup (`#gl-month-slider`, `#gl-month-slider-input`, labels, play button).
- Reuse the year slider CSS by sharing classes or adding `gl-month-slider` equivalents.
- Ensure the slider can be appended into `#gl-graph-year-slider` slot just like the year slider.

Graph-mode updates (`ui/graph-mode.js`):
- Accept `monthSlider`.
- Add `positionMonthSlider()` with the same placement rules as `positionYearSlider()`.
- When OpenET is active, hide year slider and show month slider.

## Layers Sidebar Wiring
`layers/renderer.js`
- Add OpenET section to `subcatchmentSections` when `openetLayers.length`.
- In the OpenET radio change handler:
  - Call `deselectAllSubcatchmentOverlays()`.
  - Mark selected `openetLayer.visible = true`.
  - Update `openetSelectedDatasetKey`.
  - Show monthly slider, hide yearly slider.
  - Call `refreshOpenetData()`, `applyLayers()`, `updateLayerList()`, `updateLegendsPanel()`.

`gl-dashboard.js`
- Instantiate the month slider.
- Wire month slider `change` event to:
  - Update `openetSelectedMonthIndex`.
  - Call `refreshOpenetData()` + `applyLayers()` + `updateLegendsPanel()`.
- Extend `deselectAllSubcatchmentOverlays()` to include `openetLayers` and reset OpenET state.

## Integration Points Checklist
- `wepppy/weppcloud/templates/gl_dashboard.htm` (new slider DOM + CSS)
- `wepppy/weppcloud/static/js/gl-dashboard/config.js` (OpenET constants)
- `wepppy/weppcloud/static/js/gl-dashboard/state.js` (OpenET state keys)
- `wepppy/weppcloud/static/js/gl-dashboard/data/openet-data.js` (new)
- `wepppy/weppcloud/static/js/gl-dashboard/layers/detector.js` (OpenET detection)
- `wepppy/weppcloud/static/js/gl-dashboard/layers/orchestrator.js` (wire detection)
- `wepppy/weppcloud/static/js/gl-dashboard/layers/renderer.js` (OpenET section + slider toggle)
- `wepppy/weppcloud/static/js/gl-dashboard/map/layers.js` (OpenET deck layer + tooltip/legend)
- `wepppy/weppcloud/static/js/gl-dashboard/ui/graph-mode.js` (monthly slider placement)
- `wepppy/weppcloud/static/js/gl-dashboard.js` (init slider + event wiring)

## Implementation Plan (ordered)
1. Add OpenET state defaults + constants (path, labels, units).
2. Add monthly slider module and DOM/CSS wiring.
3. Implement OpenET detection in `layers/detector.js` + wire into orchestrator.
4. Add `data/openet-data.js` and hook refresh to slider changes.
5. Update `layers/renderer.js` to render OpenET section and toggle sliders.
6. Update `map/layers.js` for OpenET rendering, tooltips, legends.
7. Update `gl-dashboard.js` orchestration (slider init, deselect helper, refresh flow).
8. Update smoke tests to verify OpenET section + slider behavior.

## Testing Plan
- Playwright smoke: extend `static-src/tests/smoke/gl-dashboard-layers.spec.js` with an OpenET block (skip if no OpenET data).
- Add a small unit test for the monthly slider controller (play/pause, label formatting).
- Manual: load a run with `openet/openet_ts.parquet`, toggle dataset keys, confirm slider updates + legend range changes.
- Example project for validation: `/wc1/runs/un/unapproachable-edict`.

## Decisions
- OpenET overlays are base-only; always use `postBaseQueryEngine` even in scenario mode.
- Use the month index list to drive the monthly slider (do not assume contiguous months).
- Assume Query Engine performance is adequate; limit calls to dataset/month changes.
- Month label format: `MMM YYYY` (for example, `Jul 2023`).
