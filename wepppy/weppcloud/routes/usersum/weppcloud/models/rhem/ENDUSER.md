# RHEM

Use **RHEM** when your question is specifically about runoff and erosion from rangeland hillslopes. In WEPPcloud, this workflow runs the **Rangeland Hydrology and Erosion Model** across the TOPAZ subcatchments in the project, then summarizes the results as hillslope-level average annuals and watershed-level return-period tables.

## What This Is For

Use RHEM to answer questions such as:

- Which rangeland hillslopes are the largest runoff sources?
- Which hillslopes are the main sediment-yield or soil-loss contributors?
- How do watershed-scale runoff, sediment yield, and soil loss change across return periods?

RHEM is the right workflow when the land cover and management question is rangeland-focused. It is not the best first choice for forest treatment, roads, or post-fire channel-routing questions.

## What You See In The UI

The main control card is intentionally simple:

| UI element | What the user sees | Why it matters |
| --- | --- | --- |
| `RHEM` | Control card title | Identifies the rangeland-specific model workflow. |
| `Run RHEM` | Main action button | Starts the full RHEM preparation and run sequence. |

After a successful run, the report panel exposes three user-facing links:

- `Average Annuals by Hillslope`
- `Return Periods Report`
- `Run Log`

Those links are the main user-visible outputs of the workflow.

## Before You Run It

The UI description is explicit: **Execute WEPP first so base hydrology is available.**

In practice, RHEM expects the run to already have usable:

- watershed delineation and TOPAZ subcatchments,
- soils,
- climate,
- rangeland cover data.

If those inputs are missing, the background job will fail because RHEM builds one hillslope input set per subcatchment from those existing project layers.

## What The Button Actually Does

When you click **Run RHEM**, the UI posts to:

- `POST /rq-engine/api/runs/{runid}/{config}/run-rhem`

The normal UI does not show advanced toggles. It submits the run with the default full workflow:

- clean previous RHEM run folders,
- prepare hillslope input files,
- execute the RHEM binary,
- post-process results into reports and queryable summaries.

The API can accept advanced boolean flags such as `clean`, `prep`, and `run` or their `_hillslopes` aliases, but those controls are not exposed in the standard end-user card. In normal UI use, **Run RHEM** means "do the whole sequence."

## How The Rangeland Workflow Differs From WEPP

RHEM and WEPP are not interchangeable, even when they use the same watershed geometry.

### Use RHEM when

- the watershed is primarily shrubland, grassland, or other rangeland,
- your question is about rangeland runoff and erosion response,
- you want hillslope-by-hillslope rangeland summaries and return-period reporting.

### Use WEPP when

- the question is mainly forest, roads, or post-fire WEPP response,
- you need the broader WEPP hillslope and watershed workflow,
- you care about WEPP-specific management files, channels, or other WEPP routing products.

### Practical interpretation

RHEM is a rangeland-specific hillslope model aggregated across the watershed. WEPP is the core WEPPcloud hydrology and erosion framework. If your land cover and management setting is truly rangeland, RHEM is usually the more appropriate erosion model to consult first. If your question is about broader WEPP outputs or non-rangeland behavior, stay with WEPP.

## What RHEM Builds Behind The Scenes

For each TOPAZ subcatchment, the workflow prepares:

- a parameter file based on slope, soils, and rangeland cover,
- a storm file derived from the run climate,
- a run file for the RHEM binary.

It then runs each hillslope and aggregates the outputs into watershed summaries. This is why the workflow is end-user simple but still depends heavily on the upstream project being prepared correctly.

## What The Reports Mean

### `Average Annuals by Hillslope`

This report lists each `Topaz ID` and shows:

- `Runoff`
- `Sediment Yield`
- `Soil Loss`
- `Rain`

Each measure is reported both:

- `over hill`
- `per unit`

That distinction matters:

- `over hill` is the total for the whole hillslope area.
- `per unit` normalizes by area, which is usually better for comparing hillslopes of different sizes.

The report also includes a watershed row, so you can compare individual source areas against the watershed total.

### `Return Periods Report`

This report summarizes watershed-scale:

- `Rain`
- `Runoff`
- `Sediment Yield`
- `Soil Loss`

for the return periods available in the run. Values are shown both as totals and as area-normalized forms where applicable.

Use this report when the question is, "How large is the watershed response under more frequent versus rarer storm conditions?"

### `Run Log`

Use this when the run finishes with missing outputs, incomplete hillslope summaries, or a result that looks inconsistent with the project setup. It is the user-visible way to inspect run progress and failures.

## Additional Query Outputs

After RHEM post-processing completes, WEPPcloud also exposes subcatchment query layers for:

- runoff,
- sediment yield,
- soil loss.

These are the values used for map-style source-area summaries by subcatchment. They are reported as annualized per-area measures for each TOPAZ hillslope.

## How To Interpret Runoff, Sediment Yield, And Soil Loss

- `Runoff` is water leaving the hillslope.
- `Sediment Yield` is sediment leaving the hillslope.
- `Soil Loss` is sediment detached from the hillslope.

Do not treat `Sediment Yield` and `Soil Loss` as identical:

- `Soil Loss` is what was detached on the hillslope.
- `Sediment Yield` is what left the hillslope.

If soil loss is much larger than sediment yield, the hillslope is detaching material that is not all leaving the slope. If both are high, that hillslope is both eroding and exporting sediment efficiently.

## Assumptions And Limits

- RHEM is intended for rangeland-dominated settings.
- It depends on the quality of rangeland cover fractions, soils, slope geometry, and climate already prepared in the run.
- The workflow runs hillslopes independently and then aggregates them. Treat watershed totals as a model summary of hillslope behavior, not as a complete substitute for every WEPP routing product.
- Return-period outputs are modeled scenario summaries, not guarantees that a storm of that exact response will occur on schedule.
- Missing or incomplete hillslope outputs can reduce confidence in the watershed summary. If a report looks incomplete, check the `Run Log`.

## When Not To Use RHEM Alone

Do not rely on RHEM alone when you need:

- a forest-oriented erosion workflow,
- road or crossing analysis,
- a non-rangeland management interpretation,
- a direct substitute for all WEPP watershed-routing outputs.

## Related Docs

- [WEPP](../wepp/ENDUSER.md)
- [Gridded RUSLE](../gridded-rusle/ENDUSER.md)
- [Getting Started](../../getting-started.md)
