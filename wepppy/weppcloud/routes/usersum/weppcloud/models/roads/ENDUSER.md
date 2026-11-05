# Roads

Use the **Roads** control when you want to test how mapped road segments change runoff, routing, and sediment relative to an existing WEPPcloud watershed run. This workflow keeps the original watershed run as the baseline and writes a separate Roads-specific result set for comparison.

For the complete workflow, upload examples, required unrutted-road attributes,
parameter editing, dashboard interpretation and troubleshooting, see the
[detailed Roads user guide](../../../../../../nodb/mods/roads/ENDUSER.md).

## What This Is For

Roads is for questions such as:

- Which road segments are likely to contribute the most road-related loss?
- How much do inslope and outslope roads change watershed results compared with the no-roads baseline?
- How sensitive are results to road design, surface, and traffic assumptions in the uploaded linework?

It is not a general road inventory tool and it does not replace the baseline WEPP watershed model.

## Parameter validation

The [Roads parameter validation report](../../../vendor/wepppy-roads/tests/roads/analysis_results_current.md)
compares clay, loam, sand and silt across road surfaces, traffic settings, profile
arrangements and site-derived geometries. It reports native profile detachment,
water outputs, sensitivity controls and separate project integration checks.
Mixed-profile detachment includes non-road OFEs; it is not road-prism-only erosion.

The validation suite corrected management plant references for one/two-OFE
profiles, including a no-traffic execution failure, and removed a stray character
from the paved sandy-loam rocked-ditch soil template. Prepare and rerun Roads to
use corrected inputs; existing results are not automatically replaced.

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

Current Roads design support:

- `Inslope_bd` and `Inslope_rd` run as point-source road contributors.
- `Outslope_rutted` runs as a routed `road -> fill -> buffer` point-source contributor.
- `Outslope_unrutted` runs as a hillslope replacement workflow (`landuse -> road -> fill` or `landuse -> road -> fill -> landuse`, depending on downslope buffer length).

Roads with other design values remain in the uploaded file but are excluded from modeled segment execution.

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

## Roads Parameterization

The approved dedicated **Roads Parameterization** view lets you inspect and adjust
runoff and erosion drivers without changing road width or slope merely to tune
results. The implemented workflow is locally validated; see the
[program status](../../../../../../../docs/work-packages/20261029_roads_parameterization_program/tracker.md)
for current evidence. The behavior below describes the approved feature.

Open it from the Roads control. The view separates **Road**, **Fill**, and
**Forest/buffer** parameters. Each role has four controls:

| Parameter | Unit | What changing it generally does |
| --- | --- | --- |
| Baseline effective hydraulic conductivity | mm/h | Lower values generally increase runoff; higher values generally decrease runoff |
| Interrill erodibility, Ki | kg s/m4 | Higher values increase sediment supply from areas between concentrated flow paths |
| Rill erodibility, Kr | s/m | Higher values increase detachment capacity where concentrated flow exceeds its erosion threshold |
| Critical shear | Pa | Higher values make concentrated-flow erosion harder to initiate |

These are input controls, not guaranteed proportional changes in outlet sediment.
Transport, deposition, climate and management can change the response. Conductivity
is a baseline model input, not the instantaneous infiltration rate throughout a run.

### See where each value comes from

For each parameter, inspect the selected source template, its baseline value,
applied adjustments, your override and the final resolved input. Where segments
have different source choices, inspect their groups and member segments.

For example, ordinary gravel/loam settings have these input values after low-traffic
adjustment and before user overrides:

| Parameter | Road | Fill | Forest/buffer |
| --- | ---: | ---: | ---: |
| Conductivity, mm/h | 8.1 | 11.4 | 26 |
| Ki, kg s/m4 | 500,000 | 2,000,000 | 120,000 |
| Kr, s/m | 0.000075 | 0.0003 | 0.0003 |
| Critical shear, Pa | 2 | 2 | 2 |

The source road Ki is 2,000,000 and Kr is 0.0003. Low and no traffic divide both
road values by four; fill/buffer values are unchanged by that division. No traffic
also selects different management, so its results can differ from low traffic.
Rocked-ditch and other texture/surface choices have different source values. The
[complete repository baseline reference](../../../../../../../docs/schemas/roads-parameterization-baseline-contract.md)
contains the full matrix and rules; these example values are not a promise that
all your segments share them.

### Edit, save and reset

Each of the 12 role/parameter entries offers:

- **Default:** use the project's resolved baseline value.
- **Multiply:** scale that resolved value. A road Ki multiplier of 2 changes
  500,000 to 1,000,000 in the example above.
- **Absolute:** supply the final input value in the displayed units.

Overrides apply to all modeled template rows of that role, after ordinary source
and traffic adjustments. They do not change road geometry or surface/traffic
labels. Forest/buffer includes template Forest rows used upstream or as unrutted
remainders; it does not change independently sourced landuse or the baseline
watershed soils. A role absent from the configuration is labeled as unused.

Use positive values. Zero is not an off switch: it can ask the native model to
estimate a parameter instead. The application rejects nonfinite values and values
that become zero or overflow during native conversion. Accepted input limits are
not field-calibrated ranges.

**Save settings** commits your changes but does not run WEPP. Return to Roads, Prepare and
Run to generate new results. **Cancel** discards the draft and reloads saved values.
**Reset overrides** sets the draft entries to Default; **Save settings** commits that reset.
Reset preserves the project's saved baseline and physical/mapping settings.

The project saves its baseline template contents and overrides together in
`roads.nodb`. Repository updates do not silently change a bound project. An older
unbound project is labeled as a preview until its first explicit Save or Prepare;
a previously prepared legacy project must Prepare before a new Run. Choosing
newer repository defaults is a separate action, not part of Reset, and is not
available in this first version.

The view reports whether repository defaults match the retained baseline, differ
from it, or could not be checked. A failed repository check leaves valid retained
settings inspectable and unchanged.

### Compare actual inputs and results

Keep **Saved configuration**, **Preview**, and **Used in last completed run**
separate. Final soil and management inputs are assembled during Run, so geometry
preparation alone cannot establish their emitted values. Native WEPP may further
adjust coefficients during simulation; baseline inputs and runtime diagnostics
are not interchangeable.

Saving changes makes old Roads results historical. They remain inspectable but
must not be labeled as results of your new settings. Compare actual retained runs
only when climate, geometry, area and report scope match. Inspect both total runoff
and sediment and area-normalized values. Missing comparisons mean the required
runs do not yet exist; no baseline run is generated automatically.

The bounded driver study varied road parameters in two profile arrangements using
one climate/texture/surface/traffic combination. It supports useful adjustment
controls, not universal response ranges for fill/buffer or field calibration.
Matching observations or expectations is an analytical choice, not proof of
physical validity. The [project parameterization contract](../../../../../../../docs/schemas/roads-settings-contract.md)
defines ownership, validation and lifecycle details.

## Upload Mapping: What The Controls Mean

The mapping controls use the labels the user sees in the Roads form:

| UI label | What Roads expects | How to choose |
| --- | --- | --- |
| `Design field` | The upload property that identifies road design eligibility | Point this at the field containing values such as `Inslope_bd`, `Inslope_rd`, `Outslope_rutted`, or `Outslope_unrutted` |
| `Surface field` | The upload property describing road surfacing | Use the field that best distinguishes gravel-like versus paved behavior |
| `Surface fallback value` | The fallback used when the mapped surface field is blank, missing, or unrecognized | Choose the more defensible default for unmapped segments; do not use this to hide poor source data |
| `Traffic field` | The upload property describing traffic class | Use the field that best separates `high`, `low`, and `none` style use |
| `Traffic fallback value` | The fallback used when the mapped traffic field is blank, missing, or unrecognized | Pick the least misleading default for the roads you expect to remain after eligibility filtering |

Important mapping behavior:

- Roads only discovers top-level `feature.properties` keys from the uploaded GeoJSON.
- If mapping is unset, legacy property keys are still checked.
- If surface or traffic mapping is set but a value is missing or invalid, the selected fallback value is used. Design has no fallback class.
- Changing mapping or fallback choices clears stale prepared and run summaries. If you change them, prepare again before running.

Numeric upload attributes must be finite numbers. Optional width, rock-fragment and rutted fill/buffer values containing NaN or infinity use the existing invalid-value fallback; segment details identify when configured defaults were used. Required unrutted fill/buffer values remain mandatory and invalid values are rejected. Correct the source attributes and prepare/run again to replace old results; existing saved outputs are not rewritten automatically.

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
   Point-source designs require mapped routing context. `Outslope_unrutted` uses hillslope-overlap inclusion rules (`60%` overlap ratio and `>=10 m` overlap length), with a cap of `3` qualifying crossings per hillslope.

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

- Roads is a scenario workflow for supported road designs, not a universal road process model.
- Supported modeled designs are `Inslope_bd`, `Inslope_rd`, `Outslope_rutted`, and `Outslope_unrutted`.
- Surface and traffic behavior are simplified into the values the Roads model recognizes after normalization.
- Results depend strongly on clean linework, reasonable CRS interpretation, and correct attribute mapping.
- Point-source designs depend on lowpoint and routing context; `Outslope_unrutted` depends on hillslope overlap and required fill/buffer attributes.
- Roads-scoped outputs are comparison outputs. They do not overwrite or "fix" the original baseline watershed run.
- Results are decision support, not field verification. Segment priorities should still be checked against real road drainage features and local knowledge.

## Roads Activation Error

If Roads reports “Roads is unavailable because of a server configuration problem,”
its saved activation settings disagree and the request was not processed. Contact
support and include your project's URL. Editing your GeoJSON or repeating the
upload will not resolve this server-side problem.

## Related Docs

- [WEPP](../wepp/ENDUSER.md)
- [Culvert Modeling](../culvert-modeling/ENDUSER.md)
- [Mods Overview](../../mods-overview.md)
- [FAQ](../../faq.md)
