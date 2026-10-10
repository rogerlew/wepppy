# Discovery evidence

Read-only inspection: 2026-10-10 20:28 UTC on forest. No model or report assets
were generated for this scaffold.

## Existing integration points

- `wepppy/weppcloud/static/js/gl-dashboard/config.js`: `GRAPH_DEFS` and graph context keys.
- `wepppy/weppcloud/static/js/gl-dashboard/graphs/graph-loaders.js`: `createGraphLoaders`, `buildScenarioList`, `scenarioDisplayName`, `scenarioColor`, query/caching patterns.
- `wepppy/weppcloud/static/js/gl-dashboard/graphs/timeseries-graph.js`: graph renderer; line x domain currently uses shared `years`; existing scale toggle is boxplot y-axis only. Probability series may have independent N/x points, so do not simply pass them as years.
- `wepppy/weppcloud/static/js/gl-dashboard/ui/graph-mode.js`, `state.js`, and `wepppy/weppcloud/static/js/gl-dashboard.js`: mode/layout, state, dependency injection and activation.
- `wepppy/weppcloud/templates/gl_dashboard.htm`: existing graph host and controls.
- `wepppy/weppcloud/static/js/gl-dashboard/data/query-engine.js`: `postQueryEngineForScenario(payload, scenarioPath)` passes scenario in POST body; never append child paths to the endpoint URL.
- `wepppy/weppcloud/routes/gl_dashboard.py`: graph scenario discovery currently checks child `wepp.nodb`; this does not prove FDC source readiness.
- `docs/ui-docs/gl-dashboard.md` and module `README.md`: current dashboard contracts. The module AGENTS references a stale `wepppy/docs/` path; actual spec is under root `docs/`.

The existing outlet stream graph reads annual loss-report summaries. Those
cannot supply a daily duration population. Return-period ranked-event assets
also omit much of the daily population and are not an FDC source.

## Candidate daily sources

| Source | Dataset and field | Verified semantics / remaining work |
| --- | --- | --- |
| Hillslopes | `wepp/output/interchange/totalwatsed3.parquet`, `Streamflow`, `Area` | Watershed-wide daily Streamflow depth in mm and area in m²; verify calendar/area consistency and baseflow meaning against producer docs |
| Channel outlet | `wepp/output/interchange/chanwb.parquet`, `Outflow (m^3)` | Daily routed volume; `Chan_ID` and `Elmt_ID` need verified outlet mapping |
| Rejected substitute | `chnwb.parquet`, `Q (mm)` | Channel water-balance depth over its area, not interchangeable with routed outlet volume |
| Rejected substitute | `chan.out.parquet` or `ebe_pw0.peak_runoff` | Peak discharge, not daily mean flow |

For discharge units, proposed conversions are `Streamflow * Area / 1000 / 86400`
and `Outflow / 86400` respectively. These must be accepted in an ADR, validated
against daily volume conservation and established unit conversion, and never
mixed with peak rates. Do not recompute totalwatsed Streamflow from components.

Actual project `/wc1/runs/ei/eighty-five-synthetic` and child
`_pups/omni/scenarios/undisturbed` each contain 16,437 rows in both candidate
Parquets, spanning 1980–2024; chanwb has one distinct Chan_ID in each. Neither
totalwatsed series has zero Streamflow in this example. This confirms source
availability, not date uniqueness, complete coverage, outlet identity, or
correct conversion. Separate intermittent and multi-channel fixtures are needed.

## Scientific reference and local precedent

[USGS Flow-duration curves (Searcy, 1959)](https://www.usgs.gov/publications/flow-duration-curves)
defines duration in terms of the fraction of time a discharge is equaled or
exceeded, without preserving temporal sequence. This supports resolving daily
sampling and zero/missing-day policy explicitly; it does not settle the chosen
plotting-position formula.

`docs/work-packages/20261007_warming_combined_release/artifacts/assess.py`
contains a research FDC of totalwatsed and routed daily discharge, using midpoint
rank probabilities and logarithmic **y**, not x. Treat it as historical evidence,
not a canonical requirement or an instruction to reuse its plotting stack.

## Unit preferences follow-up

Verified 2026-10-10: dashboard route/bootstrap contains no Unitizer preference
payload or client integration. Graph loaders and config use fixed metric labels
and conversions (mm, m³, tonne, tonne/ha). Project Unitizer settings therefore do
not currently drive dashboard graph values/axes. The initial suggestion to use
existing preferences was an integration proposal, not an existing capability.
The requirements register now makes that distinction explicit; broader Unitizer
support needs a separate scope decision.
