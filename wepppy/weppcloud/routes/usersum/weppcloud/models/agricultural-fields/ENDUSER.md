# Agricultural Fields (AgFields)

AgFields models agricultural fields inside a WEPPcloud project by converting uploaded field boundaries into hydrologic sub-fields and then running WEPP for each sub-field. Use it when watershed totals alone are too coarse and you need field-by-field or within-field comparisons tied to crop rotations.

## What This Is For

AgFields is for questions such as:

- Which fields contribute the most runoff or sediment?
- Which parts of one mapped field behave differently because they drain through different hillslopes?
- How do crop rotations change modeled response from year to year?

This is a field-management workflow layered onto a WEPPcloud watershed project. It is not a replacement for the watershed model, and it does not assume each mapped field behaves as one uniform hydrologic unit.

## The User-Facing Setup Flow

The Agricultural Fields control on the runs page presents four stages. Work from top to bottom; each blocked stage explains which earlier result is still needed.

The core setup sequence is:

1. **Field Boundaries** — upload the field-boundary GeoJSON, review the detected field ID and crop-year columns, and confirm the schema.
2. **Sub-field Delineation** — build sub-fields and use **Show on Map** to review how fields were split across hillslopes.
3. **Crop Managements** — open **Map Crops to Managements**, choose a WEPPcloud management or uploaded plant file for each crop, and save partial progress as needed.
4. **Run WEPP on Sub-fields** — after the parent watershed hillslopes have run, start and monitor one WEPP simulation per sub-field.

Those prep stages matter because later steps assume the earlier ones already succeeded. If the field IDs, crop columns, rasterized boundaries, or sub-field abstractions are wrong, the WEPP runs are still likely to finish but the answers will be attached to the wrong field logic.

## What You Need To Supply

The current AgFields workflow expects these user-provided inputs:

| User-supplied input | What it must contain | Why it matters |
| --- | --- | --- |
| Field boundary GeoJSON | Polygon boundaries for fields in the project area | Defines where fields exist spatially |
| `field_id` attribute | A stable unique identifier in the GeoJSON | Used to join geometry, crop schedule rows, sub-fields, and outputs |
| Crop-year columns | One crop value for every modeled observed year, using a repeatable pattern such as `Crop2008`, `Crop2009`, and so on | Supplies the crop sequence that becomes management inputs |
| Crop-to-management choices | One WEPPcloud management or uploaded plant file for each crop | Tells WEPPcloud which management to use without requiring you to edit `rotation_lookup.tsv` |
| Optional plant database zip | `.man` files, including 2017.1 files if needed | Lets you use custom or external management files |

Important current rules:

- the boundary GeoJSON must contain a `field_id` column during validation,
- the crop-year pattern must work for every observed climate year,
- crop names in the schedule must match `rotation_lookup.tsv`,
- the field geometry must overlap the project DEM extent after CRS handling.

For best spatial precision, export the boundary GeoJSON in the same projected UTM CRS as the project's DEM. AgFields also accepts WGS84 longitude/latitude and files with another correctly declared projected CRS, but it will not guess an unlabeled non-UTM projection from coordinate values alone. If Stage 2 reports a CRS/extent failure, use the project EPSG code and bounds shown in the error when re-exporting the file.

## Key Choices You Actually Make

### Field boundary upload

The boundary upload is not just geometry input. During validation, AgFields normalizes the file into `ag_fields/fields.WGS.geojson` and extracts the non-geometry attributes into `ag_fields/rotation_schedule.parquet`.

After a successful upload, Stage 1 shows the uploaded file's name in a separate display below the file chooser. That display remains available after a page reload, even though the browser clears the file chooser itself. Older projects that predate stored upload names show the canonical `fields.WGS.geojson` name instead.

That means one uploaded GeoJSON is carrying two jobs at once:

- field geometry,
- the rotation schedule table.

If the uploaded file has the right polygons but the wrong or incomplete attribute table, the geometry may look fine while the crop schedule still fails later.

### Field ID column

The field ID is the backbone of the workflow. The system uses it to:

- burn fields into `field_boundaries.tif`,
- join rotation rows back to the right field,
- connect sub-fields to their parent field,
- organize field and sub-field outputs.

Duplicate IDs are not fatal at validation time, but they are a warning sign. If one ID refers to multiple distinct field records, later summaries become much harder to interpret.

### Crop-year column pattern

AgFields uses a user-defined pattern such as `Crop{}` to find the per-year crop columns. This choice is checked against the run's observed climate years.

That means the crop schedule is not free-form. If the climate is observed from 2008 through 2015, the chosen accessor must resolve to valid columns for every year in that range.

If one year is missing, the later WEPP run step fails when it tries to build the crop rotation schedule for that field.

### Crop-to-management lookup

`rotation_lookup.tsv` tells the system how to turn crop names into WEPP management files.

The `database` column can currently point to:

- `weppcloud`
- `plant_file_db`

Use `weppcloud` when the crop should map to a WEPPcloud management ID. Use `plant_file_db` when the crop should map to a `.man` file stored under `ag_fields/plant_files/`.

When a custom archive comes from Jim's management interface, WEPPcloud also handles its known applied-residue placeholder: a nonpositive `hmax` is raised to the minimum positive management-file value, but only for plants that are referenced purely as residue. Active crop heights are never changed by this rule, and the plant-file inventory records the original and normalized values so the adjustment stays visible.

This lookup is where many "the model ran but the management is wrong" problems actually begin. If the crop spelling in the uploaded schedule does not match the lookup spelling, the crop cannot be mapped cleanly.

### WEPP executable

Stage 4's **Run options** includes a **WEPP Exec** selection. Agricultural projects default to `wepp_dcc52a6`, and you should leave it there: it is the executable validated end-to-end against imported agricultural rotations. Newer WEPP executables have aborted partway through multi-year agricultural simulations on these same inputs, so a different selection is a deliberate modeling decision, not a routine upgrade.

Two things follow from this:

- The AgFields executable is independent of the parent watershed's WEPP executable. It is normal for the watershed to run a newer build while the sub-fields run `wepp_dcc52a6`.
- Your selection is saved with the project, so sub-field results remain attributable to the executable that produced them.

Projects created before this default existed inherit the parent watershed executable until you set **WEPP Exec** once in Stage 4.

## Why API-Backed Prep Matters

AgFields has several preprocessing steps that materially change what gets modeled. They are not bookkeeping.

| Prep stage | What the system creates | Why the result changes the model |
| --- | --- | --- |
| Validate boundaries | `fields.WGS.geojson`, `rotation_schedule.parquet` | Freezes the geometry and schedule table the rest of the workflow uses |
| Rasterize boundaries | `field_boundaries.tif` | Aligns fields to the project DEM grid so field extents match the hydrologic raster stack |
| Abstract sub-fields with Peridot | `sub_field_id_map.tif`, `fields.parquet`, slope files | Splits mapped fields into hydrologically meaningful pieces |
| Polygonize sub-fields | `sub_fields.geojson`, `sub_fields.WGS.geojson` | Turns the raster abstraction into polygons you can inspect and export |
| Run WEPP per sub-field | `wepp/ag_fields/runs/*`, `wepp/ag_fields/output/*` | Produces the actual sub-field simulations and output tables |

For end users, the practical lesson is simple: if the prep products do not look reasonable, the final WEPP results will not become more trustworthy by rerunning them.

## Field And Sub-Field Assumptions

AgFields does not assume one polygon equals one hydrologically uniform field.

Instead, it assumes:

- a user-defined field may cross multiple hydrologic units,
- those intersections can be represented as separate sub-fields,
- each sub-field can be modeled with a representative hillslope profile,
- each sub-field inherits climate, soils, and routing context from the watershed structure it intersects.

This is why one mapped field may become several modeled sub-fields.

That behavior is intentional. A large field that crosses more than one drainage setting can have materially different slope length, contributing area, and erosion response in different parts of the same mapped parcel.

Current simplifications to keep in mind:

- sub-fields are treated as hydrologically disconnected modeled units in this workflow,
- very small sub-fields can be filtered with `sub_field_min_area_threshold_m2`,
- representative slope files simplify local variation within each sub-field,
- operations such as terraces, turn rows, irrigation features, and temporary traffic patterns are not automatically inferred from the field polygon.

## How To Work Through An AgFields Run

1. Prepare the base WEPPcloud project first.
   AgFields depends on the normal project DEM, watershed, soils, landuse context, and observed climate range.

2. Upload a field-boundary GeoJSON that includes `field_id` and crop-year columns.
   Expect the workflow to extract the attribute table into `rotation_schedule.parquet`.
   Prefer coordinates in the same UTM CRS shown by the project header's `EPSG:` pill; this avoids an unnecessary reprojection and retains project-grid precision. WGS84 longitude/latitude is accepted. If you use another projected CRS, the file must include correct CRS metadata.

3. Confirm the ID field and crop-year pattern.
   The ID must be stable across the workflow, and the crop-year pattern must match every observed climate year in the run.

4. Select **Build Sub-fields**.
   Coordinate-system mistakes and extent mismatches usually become obvious here. The error reports the project DEM's EPSG code and both extents. If the fields do not overlap the project, re-export the GeoJSON in that project CRS (preferred) or attach the correct source CRS before continuing.

5. Select **Show on Map** and review the result.
   Expect fields that span more than one hydrologic setting to split into multiple sub-fields. Check that the geometry matches your understanding of local drainage before spending compute on WEPP.

6. Open **Map Crops to Managements**.
   Choose a WEPPcloud management for each crop, or upload a plant database zip and choose a valid `.man` file. You can save an incomplete mapping and return later; the run remains blocked until every crop is valid.

7. Run the parent watershed WEPP hillslopes if they are not already complete.
   AgFields reuses their soil and climate files, so the final stage explains this prerequisite when it is missing.

8. Expand **Run options**, confirm **WEPP Exec** is `wepp_dcc52a6` (see "WEPP executable" above), and select **Run WEPP on Sub-fields**.
   Expect one WEPP hillslope-style simulation per sub-field rather than one simulation per original field polygon. The status panel reports progress, and successful runs link to the output browser and Features Export. **Clear Previous Runs and Outputs** removes only regenerable AgFields run artifacts.

## What Outputs To Look At

The most useful AgFields outputs are usually:

- `ag_fields/sub_fields/sub_fields.geojson` or `sub_fields.WGS.geojson` for inspecting the modeled sub-field layout,
- `ag_fields/sub_fields/fields.parquet` for the sub-field metadata table,
- `wepp/ag_fields/output/` for the actual WEPP result files,
- `AgFields Spatial` and `AgFields Metrics` in export-oriented tooling when available.

Interpret results at the right scale:

- compare one field to another when the management question is field prioritization,
- compare sub-fields inside one field when the question is internal variability,
- compare years when the question is crop-rotation effect.

A large difference between two sub-fields in the same mapped field usually means the field spans different hydrologic settings, not that the model is unstable.

## Assumptions And Limits

- AgFields requires observed climate years because the crop schedule is checked against explicit year columns.
- The uploaded GeoJSON must carry both usable geometry and a usable rotation table.
- `field_id` is required and should be stable and effectively unique for interpretation to remain clear.
- Crop names must match `rotation_lookup.tsv`; near-matches are still mismatches.
- WEPP accepts at most 20 plant scenarios in one management rotation. AgFields consolidates duplicate plant and operation definitions automatically, so typical multi-year rotations fit comfortably, but a rotation drawing on very many distinct managements can still exceed the limit. When that happens the run fails before simulation with an error identifying the rotation, rather than producing partial results.
- Sub-field simulations run the executable selected in Stage 4 (default `wepp_dcc52a6`), which may differ from — and produce different numbers than — the parent watershed executable.
- Sub-fields are representative hydrologic units, not full operational replicas of every within-field feature.
- Results inherit the strengths and weaknesses of the underlying watershed, soils, climate, and management data.

## Related Docs

- [WEPP](../wepp/ENDUSER.md)
- [Ag Field Mod](../../ag_field-mod.md)
- [Getting Started](../../getting-started.md)
