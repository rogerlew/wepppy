# Roads

Use the **Roads** control when you want to test how mapped road segments change runoff, routing, and sediment relative to an existing WEPPcloud watershed run. This workflow keeps the original watershed run as the baseline and writes a separate Roads-specific result set for comparison.

## What This Is For

Roads is for questions such as:

- Which road segments are likely to contribute the most road-related loss?
- How much do inslope roads change watershed results compared with the no-roads baseline?
- How sensitive are results to road design, surface, and traffic assumptions in the uploaded linework?

It is not a general road inventory tool and it does not replace the baseline WEPP watershed model.

## When to Use It

Use Roads when:

- the run already has a completed baseline WEPP solution,
- the project uses the WBT delineation backend,
- you have road centerlines in GeoJSON form,
- the uploaded road attributes can be mapped to road meaning the model understands.

## Before You Begin

Before opening the **Roads** control, make sure you have:

- a baseline WEPP run you trust enough to use as the no-roads comparison,
- a roads GeoJSON `FeatureCollection` with `LineString` or `MultiLineString` features,
- road attributes that can identify road design and, ideally, surface and traffic,
- realistic expectations about which uploaded roads are actually in-scope.

In the current Roads model, only inslope designs that resolve to `Inslope_bd` or `Inslope_rd` are eligible for segment preparation and Roads WEPP runs. Other uploaded roads may remain in the file but will not become modeled Roads segments.

## What You See In The UI

The **Roads** control has four user-facing stages:

| Visible control | What you choose or do | What WEPPcloud does behind the scenes | Why it matters |
| --- | --- | --- | --- |
| `Upload roads GeoJSON` and `Upload Roads GeoJSON` | Choose and upload the linework file | Posts the file to `tasks/roads/upload_geojson`, validates geometry, stages `roads.uploaded.geojson`, discovers top-level attributes, and tries to auto-map fields | A bad upload blocks everything else; a good upload populates the mapping controls with real fields from your file |
| `Attribute Mapping` | Choose `Design field`, `Surface field`, `Surface fallback value`, `Traffic field`, and `Traffic fallback value`, then click `Apply Attribute Mapping` | Posts the selected mapping and defaults to `tasks/roads/set_params`, persists them, and clears stale prepare/run state | This step controls how WEPPcloud interprets your road attributes and whether features are eligible later |
| `Prepare Segment Candidates` | Start preprocessing | Queues `tasks/roads/prepare_segments` and creates monotonic segments, low points, routing diagnostics, and eligibility summaries | Preparation is where linework becomes modeled road segments |
| `Run WEPPcloud Roads` | Start the Roads scenario run | Queues `tasks/roads/run` and runs the prepared segments, combines pass effects, reroutes watershed results, and regenerates Roads-scoped reports | This is the actual Roads scenario execution step |

The control also shows a summary panel and a Roads results panel. After a run finishes, the results panel reports:

- `Controller state`
- `Run summary`
- `Resources`

Those status values tell you whether report links are ready or whether you still need to rerun or regenerate Roads resources.

## Upload Mapping: What The Controls Mean

The mapping controls use the labels the user sees in the Roads form:

| UI label | What Roads expects | How to choose |
| --- | --- | --- |
| `Design field` | The upload property that identifies road design eligibility | Point this at the field containing values such as `Inslope_bd` or `Inslope_rd` if those are your intended modeled roads |
| `Surface field` | The upload property describing road surfacing | Use the field that best distinguishes gravel-like versus paved behavior |
| `Surface fallback value` | The fallback used when the mapped surface field is blank, missing, or unrecognized | Choose the more defensible default for unmapped segments; do not use this to hide poor source data |
| `Traffic field` | The upload property describing traffic class | Use the field that best separates `high`, `low`, and `none` style use |
| `Traffic fallback value` | The fallback used when the mapped traffic field is blank, missing, or unrecognized | Pick the least misleading default for the roads you expect to remain after eligibility filtering |

Important mapping behavior:

- Roads only discovers top-level `feature.properties` keys from the uploaded GeoJSON.
- If mapping is unset, legacy property keys are still checked.
- If mapping is set but a value is missing or invalid, the selected fallback value is used.
- Changing mapping or fallback choices clears stale prepared and run summaries. If you change them, prepare again before running.

## Prepare And Run Are Different Steps

Do not treat **Prepare Segment Candidates** and **Run WEPPcloud Roads** as interchangeable.

`Prepare Segment Candidates` is the deterministic preprocessing step. It:

- splits uploaded roads into monotonic segments,
- orients each segment from high point to low point,
- identifies low points,
- attributes low points to channel and receiving hillslope context,
- records routing and mapping diagnostics.

`Run WEPPcloud Roads` uses only the prepared state. It assumes the latest upload and mapping choices are already reflected in the prepared segments. If the upload changed, or the Roads parameters changed, the run is intentionally blocked until you prepare again.

This separation matters because many apparent "run problems" are really preparation problems:

- the wrong `Design field` means no eligible segments,
- poor geometry can create unexpected segmentation,
- low points may be found but not mapped into routing context,
- changing upload or mapping after prepare makes the prepared segments stale by design.

## How To Work Through A Roads Run

1. Run baseline WEPP first.
   Roads is a comparison workflow. The baseline watershed run provides the no-roads reference case and the watershed context Roads builds on.

2. In **Roads**, upload the linework with `Upload Roads GeoJSON`.
   Expect the control to discover fields from the uploaded GeoJSON and repopulate the `Attribute Mapping` section.

3. Review `Attribute Mapping` before you prepare anything.
   Start with `Design field`. If this is wrong, the prepare stage may find linework but very few or no eligible segments.

4. Click `Apply Attribute Mapping`.
   This saves the mapping and fallback defaults. If you are iterating, remember that this invalidates stale prepare/run state.

5. Click `Prepare Segment Candidates`.
   Expect a summary that reports counts such as `Eligible segments`, `Mapped lowpoints`, and lowpoint decision totals. This is the first place to check whether your upload and mapping are behaving as intended.

6. Review the map and diagnostics before running.
   Only segment candidates with `mapped` lowpoint decisions are eligible for Roads WEPP runs. Segments that are eligible but not mapped still tell you something important about coverage gaps or routing ambiguity.

7. Click `Run WEPPcloud Roads`.
   Expect a Roads-scoped run summary, Roads results links, and regenerated outputs under the Roads output tree rather than the baseline watershed output tree.

## How To Compare Baseline And Roads Results

Roads is most useful when you make a clean baseline-versus-roads comparison.

That comparison assumes:

- the same watershed delineation is being used,
- the same climate and baseline hillslope/channel setup are being used,
- the only intended change is the addition of the prepared road segments and their routing effects,
- you are comparing baseline outputs to Roads-scoped outputs, not mixing files from different runs or different prep states.

In practical terms:

- baseline content stays under the normal watershed output tree,
- Roads writes a separate Roads-scoped output tree under `wepp/roads/output/`,
- Roads report links appear only when the Roads run and Roads resources are ready.

If the baseline run itself changes, or if you change the uploaded roads after preparing, you no longer have a clean apples-to-apples comparison.

## Interpreting Results

Start with the prepare summary, then the run summary.

The prepare summary answers:

- How many uploaded features became eligible road segments?
- How many of those segments received usable lowpoint routing context?
- Why were some low points skipped or marked non-routable?

The run summary answers:

- How many mapped segments were actually run?
- How many hillslopes were targeted by the Roads scenario?
- Which skip reasons remained after preparation?

Then use the Roads results links to compare watershed-scale changes against baseline outputs. The most decision-relevant pattern is usually not one absolute number but whether adding the modeled road network materially changes:

- runoff delivery,
- sediment delivery,
- source-area ranking,
- the identity of priority road segments or hillslopes.

## Assumptions And Limits

- Roads is a phase-1 inslope-road workflow, not a universal road process model.
- Only designs resolving to `Inslope_bd` or `Inslope_rd` are currently eligible for modeled segment processing.
- Surface and traffic behavior are simplified into the values the Roads model recognizes after normalization.
- Results depend strongly on clean linework, reasonable CRS interpretation, and correct attribute mapping.
- Only segments with enough lowpoint and routing context can become fully modeled Roads segments.
- Roads-scoped outputs are comparison outputs. They do not overwrite or "fix" the original baseline watershed run.
- Results are decision support, not field verification. Segment priorities should still be checked against real road drainage features and local knowledge.

## Related Docs

- [WEPP](../wepp/ENDUSER.md)
- [Culvert Modeling](../culvert-modeling/ENDUSER.md)
- [Mods Overview](../../mods-overview.md)
- [FAQ](../../faq.md)
