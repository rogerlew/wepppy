# Modeling roads in WEPPcloud

Use **Roads** to estimate how road drainage, surface and traffic assumptions affect
runoff and sediment in a watershed with an existing WEPP simulation. Upload road
centerlines, check how they connect to the watershed, then run a separate Roads
scenario. Your baseline WEPP results remain available for comparison.

Roads is experimental. Use its results to investigate likely source areas and
compare defensible scenarios; check priorities against field drainage, road
condition and observations before making management decisions.

## Before you begin

You need:

- A completed baseline WEPP watershed run with suitable climate, soils and landuse.
- A project delineated with WhiteboxTools (WBT). Roads is unavailable for other
  delineation backends.
- Access to enable Roads. The feature currently requires PowerUser access or an
  authorized higher role; read-only project access does not permit editing.
- Road centerlines in a GeoJSON file, with attributes identifying supported road
  designs. Surface, traffic and geometry attributes improve the interpretation.

On the project page, enable **Roads** from **Mods**, then open the **Roads** section.
The main sequence is **Upload Roads GeoJSON → Apply Attribute Mapping → Prepare
Segment Candidates → Run WEPPcloud Roads**. Optional parameter editing is described
under [Adjust runoff and erosion parameters](#adjust-runoff-and-erosion-parameters).

## Choose the road design that represents drainage

A road design specifies how water leaves the road. Select it from field evidence,
not from whichever choice produces a preferred sediment result.

An **overland flow element (OFE)** is a modeled section of a slope profile with
its own soil, cover and geometry. A road-associated profile can include road,
fill and vegetated areas. **Fill** is the embankment below the road;
**buffer** is the downslope area through which runoff travels.

| Design value in the upload | Drainage assumption | Modeled profile |
| --- | --- | --- |
| `Inslope_bd` | Insloped road draining to a bare ditch; concentrated discharge at the low point | Road only when channel-associated; road plus buffer when routed across a hillslope |
| `Inslope_rd` | Insloped road with a vegetated or rocked ditch; concentrated discharge at the low point | Same routing choices as bare ditch, with different soil-template parameters |
| `Outslope_rutted` | Outslope road with concentrated drainage; flow crosses the fill | Road → fill → buffer |
| `Outslope_unrutted` | Outslope road represented as sheet flow across an affected hillslope | Upslope landuse → road → fill, with downslope landuse when long enough; the unaffected hillslope remainder is also represented |

Design values are case-insensitive. Accepted aliases include `outrut` for
`Outslope_rutted`, and `outslope` or `outunrut` for `Outslope_unrutted`.
Unsupported or missing designs do not become modeled road contributors.
There is no fallback design selection.

Inslope designs assume ditch/culvert bypass of fill-slope processes. Rutted
outslope roads include fill erosion. These are simplified drainage representations;
uploading centerlines alone does not establish the real locations or performance
of culverts, ditches or cross drains.

### Special limits for unrutted outslope roads

Unrutted roads replace the modeled response of affected hillslopes instead of
adding a point discharge. Inclusion is assessed separately for each crossed
hillslope:

- Road overlap must be at least **10 m** long.
- Overlap length divided by the **modeled hillslope width** must be at least
  **0.60**. This is not a percentage of hillslope map area.
- At most **three qualifying crossings per hillslope** are retained, choosing
  the longest overlaps first. Additional crossings are reported as excluded.
- A downstream landuse section shorter than **10 m** is omitted from the profile.
- Fill and buffer dimensions must be supplied as described below. Failure to
  construct a valid, area-conserving profile is reported explicitly.

Inspect the included, excluded and capped counts. A visible road line is not
proof that it contributed to the simulation.

## Prepare a GeoJSON road file

Export a GeoJSON **FeatureCollection** containing **LineString** or
**MultiLineString** features. Polygons and point features are not accepted. The
standard upload limit is **50 MB**; use the limit displayed beside the upload
control if your project differs.

Use correctly georeferenced linework covering the modeled watershed. Without an
explicit GeoJSON coordinate-system declaration, the standard input assumption is
**EPSG:4326**, with coordinates ordered **longitude, latitude** in degrees. Do not
label projected meter coordinates as EPSG:4326. Reproject in your GIS before
uploading if needed. An explicit `crs.properties.name` can identify another CRS.

Put attributes directly in each feature's `properties` object. The mapping
controls do not follow nested property paths. Keep geometry clean and use
consistent attribute values. Elevation sampling and watershed resolution affect
where lines split and how low points connect to drainage.

### Design, surface and traffic attributes

You can use your own field names and select them in **Attribute Mapping**.
For example, map `ROADTYPE` to **Design field**, `SURF_CLASS` to **Surface field**,
and `TRAF_LEVEL` to **Traffic field**.

| Attribute | Recognized values | Interpretation |
| --- | --- | --- |
| Design | The four designs above | Determines routing and profile arrangement |
| Surface | `gravel`, `paved` | Chooses the simplified surface class |
| Traffic | `high`, `low`, `none` | Chooses traffic adjustments and management |

Surface aliases `graveled`, `dirt`, `native` and `unpaved` use the **gravel**
class; `asphalt` and `concrete` use **paved**. A dirt alias therefore does not
select a distinct calibrated dirt-road material. Traffic aliases `no` and
`notraffic` use **none**. These classes are not numeric vehicle-count thresholds.

When mapping is **Auto / Unset**, Roads can use legacy keys such as `DESIGN` or
`design`, `SURFACE`, `surface` or `ROAD_SURFACE`, and `TRAFFIC`, `traffic`,
`CONDITION` or `condition`. Legacy condition values `impassable`, `year round`
and `new2011` map to none, high and low traffic, respectively.

### Geometry and material attributes

The mapping selectors cover design, surface and traffic only. Additional numeric
attributes use recognized field names directly. Common inputs include
`ROAD_WIDTH_M`, `SOIL_TEXTURE` and `RFG_PCT`; inspect the resolved segment details
to confirm what the model used.

Standard fallbacks are **4 m** road width, **loam** soil texture and **20%** rock
fragments. Supported texture classes are clay, loam, sand and silt (for example,
sandy loam resolves to sand). These are modeled defaults, not measurements of
your road. Use finite numeric values and record the basis for any supplied values.

For **Outslope_rutted**, fill length and grade can be supplied using
`FILL_LENGTH_M` and `FILL_SLOPE_PCT`. Missing or invalid values use the configured
fallbacks, normally **30 m** and **10%**. Review default-use diagnostics.

For **Outslope_unrutted**, supply all four fields below; there is no silent
substitution of rutted-road defaults for missing required values. Lowercase forms
of these names are also accepted.

| Required field | Meaning | Accepted range |
| --- | --- | --- |
| `FILL_LENGTH_M` | Modeled fill length | 0.3–100 m |
| `FILL_SLOPE_PCT` | Fill grade | 0.1–150% |
| `BUFFER_LENGTH_M` | Modeled buffer length | 0.3–300 m |
| `BUFFER_SLOPE_PCT` | Buffer grade | 0.1–100% |

Grade is percent rise/fall per horizontal distance, not degrees: enter `10` for
10%, not `0.10`. Accepted ranges are implementation limits, not evidence that
any value within them is appropriate for the site.

### Example upload

This illustrates the file structure for one inslope road. Replace the coordinates
with linework inside your own watershed; these example coordinates are not a
ready-to-run project dataset.

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "LineString",
        "coordinates": [[-116.0, 45.0], [-116.0005, 45.0005]]
      },
      "properties": {
        "ROADTYPE": "Inslope_bd",
        "SURF_CLASS": "gravel",
        "TRAF_LEVEL": "low",
        "ROAD_WIDTH_M": 4.0,
        "SOIL_TEXTURE": "loam",
        "RFG_PCT": 20.0
      }
    }
  ]
}
```

## Upload, map, prepare and run

1. In the project **Roads** section, select the file under **Upload roads
   GeoJSON**, then click **Upload Roads GeoJSON**. Wait for confirmation and the
   discovered field names/sample values. Selecting a file alone does not upload it.
2. Under **Attribute Mapping**, choose **Design field**, **Surface field** and
   **Traffic field**. Check the sample values against the supported classes.
3. Choose **Surface fallback value** and **Traffic fallback value**. An explicitly
   mapped surface/traffic field with a missing or invalid value uses that fallback;
   an unset mapping checks legacy keys before falling back. Choose defensible
   defaults and correct source data when defaults would hide important variation.
4. Click **Apply Attribute Mapping** to save. Review the confirmation. A replacement
   upload rediscovers fields and attempts to preserve matching mappings; verify
   them again even if field names look familiar.
5. Optional: open **Roads Parameterization**, inspect or edit the settings, and
   return to the Roads control after saving.
6. Click **Prepare Segment Candidates** and wait for completion. Review eligible
   segments, mapped low points and decision diagnostics. Point-source lines are
   split into downhill sections and assigned routing context; unrutted roads
   follow the hillslope-overlap rules above.
7. Check exclusions before running. Point-source roads may be channel-associated
   or eligible for downslope tracing from a hillslope. A prepared non-channel
   candidate still needs to reach a channel during execution. Resolve obvious
   mapping or coordinate-system errors and prepare again after corrections.
8. Click **Run WEPPcloud Roads**. Wait for the Roads run and report resources to
   finish. Review completed and skipped contributors, targeted hillslopes and
   warnings, then open the available Roads report links.

**Prepare** does not simulate runoff or sediment. **Run** assembles the final
model inputs, executes the road-associated profiles and reroutes the watershed.
A successful run can contain skipped candidates: compare executed coverage with
the network you intended to model.

## Adjust runoff and erosion parameters

Open **Roads Parameterization** from the Roads control. This page separates
**Road**, **Fill** and **Forest/buffer** roles, each with four adjustable inputs.
Use these controls for a documented sensitivity or calibration question; keep
physical width and slope tied to site geometry.

| Parameter | Unit | General effect of increasing the input |
| --- | --- | --- |
| Baseline effective hydraulic conductivity | mm/h | Generally increases infiltration capacity and reduces runoff |
| Interrill erodibility, Ki | kg s/m⁴ | Increases sediment detachment potential between concentrated flow paths |
| Rill erodibility, Kr | s/m | Increases detachment potential where concentrated flow exceeds its threshold |
| Critical shear | Pa | Makes concentrated-flow detachment harder to initiate |

Conductivity is a baseline input, not an instantaneous infiltration rate.
Deposition, transport, climate, cover and model adjustments affect the response;
doubling an erodibility input does not promise twice the outlet sediment.

### Inspect source values before editing

Use **Resolved template group** to inspect groups with different designs,
textures, surfaces or traffic, and expand **Segment membership**. Each row shows
**Source baseline**, **Adjustment**, **Override** and **Resolved input**.

For example, a gravel/loam road's source Ki is 2,000,000 kg s/m⁴. Low traffic
divides road Ki by four to 500,000; **Multiply** by 2 then resolves to 1,000,000.
The same road-only traffic division applies to Kr. Fill and forest/buffer values
do not receive that division. No traffic also selects different management,
so low and no traffic can produce different results.

### Edit and save

1. Click **Edit overrides**.
2. For the desired role and parameter, choose **Default**, **Multiply** or
   **Absolute**. Default uses the project's resolved baseline; Multiply uses a
   dimensionless factor; Absolute supplies the final input in the displayed units.
3. Enter a positive value for Multiply or Absolute. Zero is not an off switch:
   the model can interpret zero as a request to estimate coefficients. Nonfinite
   values and values that cannot remain positive and finite in model inputs are
   rejected. Accepted values are not guaranteed calibrated or numerically safe
   for every simulation.
4. Click **Save settings** and check the saved confirmation. Saving does not run
   the model. Return using **Return to Roads · Prepare and Run**, then prepare
   and run again to produce results for the saved settings.

Overrides apply to **every template-owned row of the selected role**, not just
the group currently displayed. Forest/buffer includes template Forest rows used
upstream and in unrutted remainder profiles; independently sourced landuse is
excluded. A role that is absent is shown as unused. Overrides do not change road
geometry, traffic/surface labels or the baseline watershed soils.

**Cancel** discards unsaved edits. **Reset overrides** changes the draft to
Default; click **Save settings** to commit the reset. Reset uses the same baseline
retained by the project and leaves physical/mapping settings intact.

### Saved settings, previews and actual run inputs

An older project without a retained baseline initially shows an unbound preview.
Its first explicit Save or Prepare retains the baseline used by that project.
Later repository updates do not silently replace it. Reset does not adopt newer
repository defaults; adopting them is not available in this version.

Keep these displays separate:

- **Saved configuration** describes the settings stored for the project.
- **Preview (not prepared)** describes resolved inputs before execution.
- **Used in last completed run** reports input values actually emitted during Run.
- **Baseline / custom comparison** uses compatible retained executions. It does
  not automatically generate a default Roads execution for you.

For a parameter experiment, first run with Default overrides, then change a
controlled set of values and run again using the same geometry, climate and
report scope. Here, a default-parameter Roads execution differs from the original
watershed baseline without Roads. Missing or incompatible comparison evidence is
reported rather than estimated.

## Read the results at the right scale

Start with coverage and warnings, then compare runoff and sediment. Keep the
same watershed, climate, simulation period and report scope when comparing
baseline and Roads. A Roads scenario is a complete modeled response; its segment
values are not automatically the increment caused by adding roads.

### Watershed reports

Depending on available outputs and simulation mode, the Roads results panel can
link to Watershed Loss Summary, Return Periods, Yearly Water Balance, Daily
Streamflow, Average Annual Water Balance, GL Dashboard and Storm Event Analyzer.
Open them from the Roads results panel to select the Roads outputs.

Compare the same quantity and units in baseline and Roads reports. Watershed
outlet sediment includes downstream routing and deposition; it is not the sum of
road-profile detachment. Check each report's time scale before comparing daily,
annual, average annual or single-storm results.

Aggregate Roads water accounting uses the full modeled road/fill/buffer area.
For point-source contributors, road-associated area replaces an equal amount of
baseline hillslope response; if it exceeds the baseline area, accounting expands
to retain the full footprint. This is response mixing, not a geographic overlap
survey or a rerun of a smaller residual hillslope. Unrutted replacement profiles
instead preserve the affected hillslope's total area. Raw profile water outputs
and aggregate water-balance reports can therefore have different denominators.

### Road Segment Loss Summary

Download the **Road Segment Loss Summary** as Parquet or CSV. Rows represent
completed source profiles, which may outnumber uploaded road features.
Values are mean annual over the full simulation, including zero-export years.

| Field or quantity | Meaning | Interpretation |
| --- | --- | --- |
| `segment_run_id` | Completed source profile identifier | Use it to distinguish profiles; receiving-hillslope IDs describe routing context |
| `profile_scope` | Road-only, mixed profile or replacement remainder | Check this before attributing a value to the road prism |
| `modeled_area_m2` | Full modeled OFE area, m² | Denominator for profile densities; may include fill, buffer and landuse |
| `soil_loss_kg` | Mean annual profile soil detachment, kg/year | Sediment detached within the modeled profile |
| `soil_loss_density_kg_m2` | Mean annual detachment per modeled area, kg/m²/year | Multiply by 10 for t/ha/year |
| `sediment_yield_kg` | Mean annual sediment exported from the profile, kg/year | After within-profile transport/deposition; not watershed-outlet yield |
| `road_prism_erosion_kg` | Mean annual road-prism detachment when identifiable, kg/year | Populated only for proven road-only single-OFE inslope profiles |
| `sediment_leaving_buffer_kg` | Unavailable in this summary | A blank/NULL value does not mean zero export |

Do not treat a mixed profile's full-area density as road-surface erosion alone.
Do not divide annualized values by the simulation length again, and do not sum
profile densities as though they were masses. Compare totals and area-normalized
values together.

### GL Dashboard: output scope and road colors

The dashboard's **Output scope** selector switches between **Baseline** and
**Roads** datasets. The separate **Roads soil detachment** layer colors road
centerlines by **Mean annual detachment (t/ha/year)**. Valid current Roads results
can support that overlay in either scope; selecting Baseline does not redefine
the overlay as baseline road erosion.

Hover or select a road for its value and profile scope; use the tabular equivalent
when map interaction is inconvenient. The line color uses full-profile detachment,
including modeled non-road OFEs in mixed profiles. Multiple profiles joined to one
line use total annual detachment divided by total modeled area, not a sum of
rates. Replacement remainder profiles are excluded from the road-line layer.

The display draws centerlines, not surveyed footprints of fill and buffer areas.
Its default color range runs from zero to the project's maximum; compare numeric
legends rather than colors alone across projects. Unavailable values are not
zeros, and negative modeled detachment values remain explicitly identified.
The layer is mean annual, so selecting it does not create an annual time slider.

Roads scope applies to the current project, not an Omni scenario difference.
Incompatible scenario/comparison controls are unavailable in Roads scope. Flow
Duration remains baseline-only. Single-storm Roads results can be available
without the mean-annual detachment layer.

## Change settings or revisit older results

Uploading replacement linework, saving model-affecting mappings or parameters,
preparing again, or disabling Roads invalidates current Roads results. Previous
outputs and matching inputs are retained as history. They do not become results
for the new settings simply because the files remain downloadable.

After an input change, **Prepare Segment Candidates**, then **Run WEPPcloud
Roads**. Current report links require a successfully published result set with
its required outputs. Historical beta outputs may require a fresh execution;
reopening or regenerating a report alone does not update the simulation.

For detailed inspection, the project file browser contains:

| Location | What to inspect |
| --- | --- |
| `roads/roads.uploaded.geojson` | Uploaded source linework |
| `wepp/roads/segments/` | Prepared geometry, routing decisions and execution summaries |
| `wepp/roads/roads.log` | Preparation and execution messages |
| `wepp/roads/output/` | Roads outputs; use current report links to establish readiness |
| `wepp/roads/history/` | Retained earlier inputs and results |

A browsable file can be historical or part of a failed attempt. Use the results
panel and its warnings before interpreting it as current output.

## Troubleshooting

| Symptom | What to check or do |
| --- | --- |
| Roads is unavailable in Mods | Check WBT delineation and feature access; ask the project administrator if access is missing |
| Upload rejected | Check size, FeatureCollection structure, line-only geometries and valid coordinates |
| Few or no eligible segments | Check the Design field and its actual values; unsupported values have no design fallback |
| Unexpected splitting or misplaced roads | Check CRS, coordinate order, line geometry and terrain coverage in your GIS |
| Low points are unmapped, or traces do not reach a channel | Inspect preparation/run decisions and compare the linework with watershed drainage; a skipped contributor is not a measured zero |
| Unrutted roads are excluded | Check 10 m overlap, the 0.60 width ratio, three-crossing cap and required fill/buffer attributes |
| Run asks for fresh preparation | Inputs changed or an older project needs baseline binding; prepare again before running |
| Save rejects an override | Use a positive, finite number in the displayed units; review the error before changing other inputs |
| Operation busy | Wait for the current project operation to finish, then reload status; report a persistent conflict to support |
| Report link or detachment layer is missing | Check run completion, skipped profiles, resource readiness and simulation mode; rerun after correcting the reported cause |
| Results differ from expectations | Check defaults, group membership, full-profile area, design routing and report scope before adjusting parameters |
| Server configuration problem during activation | Contact support with the project URL; repeated uploads cannot repair activation settings |

When requesting support, include the project URL, action attempted, visible error,
and relevant segment/profile IDs. Preserve the uploaded data and logs so the
failed case can be inspected.

## Assumptions and limits

Roads uses simplified template materials and drainage arrangements. Default values
and permitted input ranges do not establish site calibration. Terrain resolution,
linework accuracy, drainage structures, cover and storm characteristics can all
affect whether the modeled routing represents the field.

Unrutted inclusion thresholds and crossing caps limit network representation.
Fill and buffer areas are model abstractions, not mapped polygons. Detachment,
profile export and watershed delivery answer different questions; none alone
establishes the incremental impact of a road or a management treatment.

Use field evidence and sensitivity analysis to assess conclusions. The native
validation suite checks specified textures, profile arrangements and numerical
behavior; it does not validate every site, storm or arbitrary parameter override.

## Related documentation

- [Roads overview in WEPPcloud Help](../../../weppcloud/routes/usersum/weppcloud/models/roads/ENDUSER.md).
- [Roads parameter validation results](../../../weppcloud/routes/usersum/vendor/wepppy-roads/tests/roads/analysis_results_current.md).
- [WEPP user guide](../../../weppcloud/routes/usersum/weppcloud/models/wepp/ENDUSER.md).
- [Roads developer and operator reference](README.md).
- [Parameter source values and transformations](../../../../docs/schemas/roads-parameterization-baseline-contract.md).
- [Segment summary definitions](../../../../docs/schemas/roads-segment-loss-summary-contract.md).
