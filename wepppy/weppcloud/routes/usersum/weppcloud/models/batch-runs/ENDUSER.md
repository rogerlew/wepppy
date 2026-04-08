# Batch Runs Operator Guide

This guide is for operators who prepare, launch, rerun, and monitor WEPPcloud batch runs. A batch creates one shared `_base` project, uses it to initialize one child run per uploaded GeoJSON feature, and then executes the selected workflow stages across that child-run set.

## Operator Scope

Batch Runs is the operator surface for applying one approved WEPPcloud setup to many watersheds or outlet features without rebuilding each run by hand.

It is useful when you need to:

- screen many watersheds under one shared configuration,
- stage the workflow across multiple passes,
- control when existing child runs should be reused versus rebuilt from `_base`,
- monitor queue activity while many related runs are being processed.

It is not the right tool when different groups of watersheds require materially different base assumptions, different calibration strategies, or different modeling workflows from the beginning.

## When to Use It

Use Batch Runs when:

- one shared set of assumptions should be applied across many features,
- you already have a GeoJSON `FeatureCollection` that defines the members of the batch,
- the feature properties contain enough information to build unique run IDs,
- you want WEPPcloud to queue and process many runs for you under operator control.

Use separate batches, or separate standard runs, when different groups of watersheds need different base settings.

## Before You Begin

- The current Batch Runner surface is an operator-facing preview. In many deployments it is only available to Admin or operator-level accounts and may be disabled entirely.
- You need to know which base configuration should be used for the shared `_base` project.
- You need a valid GeoJSON `FeatureCollection`. The uploaded feature properties must include any fields you plan to use in the run ID template.
- The GeoJSON upload limit is currently 10 MB unless your deployment changes it.
- If you are using a disturbed-land workflow and want one soil burn severity raster reused across the whole batch, prepare that SBS map in advance.

## How Batch Works

1. You create a batch and choose the configuration for the shared `_base` project.
2. WEPPcloud creates one batch workspace with a `_base` project, a `runs` area for child runs, and a `resources` area for uploaded files.
3. You open `_base` and set the shared project defaults just as you would in a standard run.
4. You upload the watershed GeoJSON that defines which runs will be created.
5. You enter and validate a run ID template so each feature produces a usable child run ID.
6. You choose which batch tasks should run.
7. WEPPcloud clones `_base` into one child run per feature and processes the features largest area first.

The result is a collection of standard WEPPcloud-style runs that share one common starting setup.

## The `_base` Project

The `_base` project is the master copy for the batch. Treat it as the place where the operator sets every assumption that should be shared by all child runs.

Use `_base` to set things such as:

- DEM and delineation choices,
- landuse and soils settings,
- climate selections,
- WEPP options and report-related settings,
- enabled mods and their parameters,
- scenario defaults that should be copied into every child run.

The batch page itself handles the batch-only controls such as GeoJSON upload, SBS upload, run ID validation, and batch task toggles. Those are not configured inside `_base`.

Important rerun behavior:

- Child runs are copied from `_base` when their run workspace is initialized.
- `Remove existing files` is off by default.
- If a child run already exists, changing `_base` later does not automatically refresh that child run.
- To force child runs to rebuild from the current `_base`, enable `Remove existing files` before rerunning, or create a new batch.

## How To Configure The `_base` Project

Open `_base` with `Configure Base Project`. Once you are inside `_base`, use the normal WEPPcloud controls just as you would in a standard run:

- in the watershed controls, set delineation, DEM, outlet, and abstraction options,
- in `Landuse`, set the landuse source and related options,
- in `Soils`, set saturation and disturbed-soil options if needed,
- in `Climate Options`, choose the dataset, station-selection mode, spatial mode, and year range,
- in `WEPP`, set the run and report options you want copied into the child runs,
- in any enabled mod, set the shared parameters that all child runs should inherit.

The primary buttons in `_base` still matter. Use the main action on each card, such as:

- `Build Channels`,
- `Build Subcatchments`,
- `Build Landuse`,
- `Build Soils`,
- `Build Climate`,
- `Run WEPP`.

In `_base` batch context, those buttons act as apply-and-save actions for batch processing. They persist the inputs you chose, then return a batch-processing confirmation message instead of running the full computation for `_base` itself. In practical terms, configure a control, click its primary button so the settings are stored, confirm the batch-processing response, then move on to the next control or return to the batch page.

This is especially important for controls that do more than change one visible field. Clicking the primary button confirms that the controller inputs were parsed and saved in the `_base` project that the child runs will later clone.

### Climate recommendation for geographically dispersed batches

If the batch watersheds are spread across a large area, leave `Station selection mode` on `Auto` in `_base`.

That matters because:

- in batch mode, the `_base` climate button stores the climate settings but does not build the climate for `_base`,
- when each child run later reaches `Build Climate`, the child climate build can choose the closest station at runtime,
- this gives each watershed a station choice based on that watershed's own location rather than forcing one fixed station onto the entire batch.

If you manually lock in one station in `_base`, that explicit station choice can be inherited by all child runs, which is usually a poor fit for a geographically dispersed batch.

## What You See In The Batch UI

| UI area | What you do there | Why it matters |
| --- | --- | --- |
| `Base Project` | Open `_base` with `Configure Base Project` | This is where you set the defaults that all child runs inherit |
| `Resource Intake` | Upload the watershed GeoJSON | Defines which runs will be created and exposes properties for template building |
| `SBS Map (optional)` | Upload one SBS raster for the batch | Reuses one burn-severity map across all child runs and crops it to each DEM automatically |
| `Run ID Template` | Build and validate run names from feature properties | Prevents duplicate, empty, or invalid run IDs before queuing work |
| `Batch Tasks` | Toggle workflow stages on or off | Lets you decide which parts of the pipeline should run, and whether reruns should wipe existing child workspaces |
| `Batch Progress` and status panels | Watch run progress and queue activity | Shows coarse progress, the live status stream, and the active RQ job link |
| `Run Batch` | Start the queued batch workflow | Launches one child run per uploaded feature |

The `Resource Intake` panel also shows:

- metadata about the uploaded GeoJSON,
- the detected property schema,
- sample features that help you choose the right property names for the run ID template.

If you upload a new GeoJSON after validating the template, validate again before running.

## Key Terms And Settings

| Setting or control | What it means | Why it matters |
| --- | --- | --- |
| `Configuration for _base project` | The starting run type used to create the shared `_base` project | Determines which controls and defaults are available in the batch |
| `GeoJSON file` | The uploaded `FeatureCollection` that defines the batch members | Each feature becomes one child run |
| `Template` | An expression that builds a run ID from feature properties | Batch cannot run until the template validates cleanly |
| `Validate Template` | Checks for duplicates, missing values, and evaluation errors | Catches naming problems before jobs are queued |
| `SBS Map` | Optional soil burn severity raster stored once for the whole batch | Useful when every child run should use the same burn-severity input |
| `Batch Tasks` | The workflow stages to include in the run | Lets you trim the workflow or force a clean rebuild |
| `Remove existing files` | Rebuilds an existing child workspace from `_base` instead of reusing it | Important when `_base` changed and you want those changes copied into reruns |

In template expressions, the most useful context is usually `properties[...]`, plus `index`, `one_based_index`, and helper functions such as `slug()`, `lower()`, `upper()`, `replace()`, and `zfill()`.

## Operator Workflow

1. Open `Create Batch Run`.
   In the current UI this is available from the WEPPcloud `More` menu. In many deployments this surface is limited to Admin or operator-level accounts.

2. Enter a batch name and choose the configuration for `_base`.
   Use a batch name that will still make sense when you return to it later.

3. Open `Configure Base Project`.
   Set the shared project parameters in `_base` exactly the way you want them copied into the child runs. Use the primary action on each relevant control so the `_base` project saves those settings, then return to the batch page.

4. Return to the batch page and upload the watershed GeoJSON.
   Expect the page to show feature count, property names, and sample rows after upload.

5. Optional: upload an SBS map.
   Do this when the same burn-severity raster should be reused across the whole batch.

6. Enter a run ID template and click `Validate Template`.
   Start with a simple expression based on a property that is clearly present in the uploaded schema, for example `{slug(properties["name"])}`.

7. Review the validation summary and preview.
   Do not continue until duplicate or missing-value issues are resolved. `Run Batch` stays blocked until validation is in an OK state.

8. Review `Batch Tasks`.
   Leave the defaults on unless you have a reason to skip a stage. Turn on `Remove existing files` when you want a clean rebuild from the current `_base`.

9. Click `Run Batch`.
   Expect the button to lock, the status stream to start updating, and the RQ job hint to appear under the run controls.

## Monitoring Batch Runs

Use all three monitoring surfaces together:

- `Batch Progress` shows one line per child run and refreshes every 10 seconds.
- The live status panel shows queue messages while the batch is running.
- The RQ hint under the buttons links to the active RQ dashboard job for deeper queue-level monitoring.

How to read `Batch Progress`:

- runs are listed largest area first,
- each row represents one child run,
- the row fills in task icons as stages complete,
- read the task order left to right in the same order shown in `Batch Tasks`,
- blank positions usually mean that stage has not finished yet.

This panel is a quick progress view, not a full diagnostic report. Use the live status panel and the child runs themselves when you need detail.

## Phased Execution And Rebuild Strategy

Batch Runs supports staged passes because each batch task only runs when both of these are true:

- the task is enabled in `Batch Tasks`,
- that child run does not already have a completion timestamp for that task.

This means you can intentionally break the batch into phases.

Example phased workflow:

1. First pass:
   Enable `Fetch DEM`, `Build Channels`, `Find Outlet`, `Build Subcatchments`, and `Abstract Watershed`. Leave later tasks off. Run the batch.

2. Second pass:
   Enable `Build Landuse`, `Build Soils`, and `Build Climate`. Run the batch again.

3. Third pass:
   Enable `Run WEPP Hillslopes` and `Run WEPP Watershed`, plus any later tasks you want such as OMNI work. Run the batch again.

In this pattern, the earlier completed steps are skipped automatically on later passes because those child runs already have timestamps for them, while the not-yet-completed steps still run.

Important limitation:

- phased passes reuse the existing child workspaces,
- if you change `_base` after the first pass, those changes do not automatically flow into the already-created child runs,
- use phased passes when you are sequencing unfinished work,
- use `Remove existing files` when you need existing child runs rebuilt from updated `_base` settings.

### What the task toggles are good for

Use `Batch Tasks` when you want to:

- delay expensive downstream work until you have inspected earlier outputs,
- split a large batch into logical phases,
- run tasks that have not yet been completed for the existing child runs.

### What the task toggles do not do by themselves

Simply turning a completed task back on does not force it to rerun. The batch runner skips tasks that already have timestamps in the child run workspace.

If you need to rerun already completed steps across the batch, use `Remove existing files`. That recreates each child workspace from the current `_base` and clears the old per-run timestamps during initialization. Without that clean rebuild, the batch runner treats completed steps as already done.

Practical rule:

- for unfinished later steps, use phased passes with the task toggles,
- for a real rebuild of already completed steps from updated `_base` settings, turn on `Remove existing files` and rerun the batch.

## Interpreting Results

Each child run should be interpreted as a normal WEPPcloud run that inherited the shared settings from `_base`.

That means differences across child runs usually come from:

- the geometry and location of each uploaded feature,
- the DEM, outlet, and watershed products built for that feature,
- the fetched soils, climate, landuse, or mod inputs specific to that location.

If differences look surprising, first check whether:

- every child run was built from the same `_base` version,
- an older child workspace was reused instead of rebuilt,
- the run ID template actually matches the features you intended to model.

## Assumptions And Limits

- The current Batch Runner surface is an operator-facing preview and may be disabled in some deployments.
- The batch only runs after a valid GeoJSON upload and a validated run ID template are both present.
- Uploading a new GeoJSON can make an older validation result stale. Revalidate before running.
- `Remove existing files` is off by default, so reruns may reuse existing child workspaces instead of rebuilding from the latest `_base`.
- The progress display is intentionally coarse. One child run can fail without stopping the rest of the batch.
- Batch Runs work best when all child runs should share one setup. If the watersheds need different assumptions, use different batches.
- A batch-level SBS upload applies one raster across the batch. It does not replace per-watershed judgment about whether that raster is appropriate.

## Related Docs

- [WEPP](../wepp/ENDUSER.md)
- [Ash Transport (WATAR)](../ash-transport/ENDUSER.md)
- [Culvert Modeling](../culvert-modeling/ENDUSER.md)
- [RQ Engine](../../rq-engine.md)
- [SBS Map Preparation](../../sbs-map-preparation.md)
- [Mods Overview](../../mods-overview.md)
