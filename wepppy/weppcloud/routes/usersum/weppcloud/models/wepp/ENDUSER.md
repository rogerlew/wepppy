# WEPP

WEPP is the main runoff and erosion model used by most WEPPcloud watershed projects. In WEPPcloud, it turns your delineated watershed, soils, land cover, disturbance inputs, and climate into modeled hillslope runoff, sediment production, channel routing, and watershed-outlet summaries.

## What This Is For

Use WEPP when your question is about runoff, erosion, or sediment delivery under a specific landscape condition, such as:

- current conditions versus burned conditions,
- treated versus untreated conditions,
- observed recovery versus assumed recovery,
- how much sediment comes from hillslopes versus what reaches the outlet.

In most projects, this is the central model run that all later reports and exports depend on.

## What You Actually Control In The UI

On the run page, the main control is titled `WEPP` or `WEPP-SWAT+`. The top-level buttons the user actually sees are:

| Visible action | Where it appears | What it does |
| --- | --- | --- |
| `Run WEPP` | main WEPP card | Submits the whole current WEPP form, including any enabled advanced options |
| `Prep Only` | `WEPP Advanced Options` > `WEPP Exec` | Builds hillslope and watershed inputs without executing the WEPP binary |
| `Run WEPP Watershed` | `WEPP Advanced Options` > `WEPP Exec` | Runs the watershed/channel routing phase using existing hillslope outputs |
| `Run WEPP Hillslopes and Watershed` | `Bootstrap` > `Run (No Prep)` | Runs the bootstrapped WEPP inputs exactly as checked out, without rebuilding inputs in the browser |
| `Run WEPP Watershed` | `Bootstrap` > `Run (No Prep)` | Runs only the bootstrapped watershed/channel routing step |

`WEPP Advanced Options` is where most result-changing assumptions live. These are the visible cards and controls the user actually works with:

| Advanced card | User-facing controls | Why an end user would touch it |
| --- | --- | --- |
| `WEPP UI - Hourly Seepage` | `Run hourly seepage (wepp_ui.txt)` | Use only for runs where hourly seepage behavior is relevant; the card itself notes this is for 7778 soils and not WEPP-PEP |
| `Potential ET (PMET)` | `Basal crop coefficient ratio (kcb)`, `Readily available water fraction (rawp)`, `Run PMET (pmetpara.txt)` | Switches from the default Penman ET treatment to Penman-Monteith and exposes crop-water assumptions |
| `Frost` | `Write frost inputs (frost.txt)` plus `wintRed`, `fineTop`, `fineBot`, `ksnowf`, `kresf`, `ksoilf`, `kfactor(1)`, `kfactor(2)`, `kfactor(3)` | Only for cold-region runs where frozen-soil behavior is materially important |
| `Snow` | `Write snow inputs (snow.txt)`, `Rain/snow threshold temperature`, `Density of new snow`, `Snow settling density` | Only when snow accumulation and melt assumptions matter |
| `Baseflow Processing` | `Initial groundwater storage`, `Baseflow coefficient`, `Deep seepage coefficient`, `Watershed groundwater baseflow threshold area` | Important for continuous simulations when low-flow or delayed-flow behavior matters |
| `Channel Inputs (chan.inp)` | `Output interval override (dtchr_override, seconds)`, `Channel hydrograph output (ichout_override)`, `Channel TOPAZ IDs of interest (chn_topaz_ids_of_interest)` | Use when you need more or less channel hydrograph detail or want outputs only for selected channels |
| `Channel Parameters` | `Use variable channel critical shear as a function of channel slope (tcr.txt)`, `Critical shear`, `Channel erodibility`, `Minimum channel width`, `Total Manning roughness coefficient allowing for vegetation (chnn)`, `Manning roughness coefficient for bare soil in the channel (chnnbr)`, and optional `taumin`, `taumax`, `k`, `n` | Important when channel erosion or routing behavior is a major decision driver |
| `Bedrock` | `Hydraulic conductivity for restrictive layer (kslast)` | Use when shallow restrictive layers or perched-water assumptions are important |
| `Clip Hillslopes` | `Clip hillslopes`, `Hillslope clip length` | Useful when very long representative hillslopes appear to overstate erosion |
| `Soil Options` | `Clip Soils Maximum Depth`, `Soils Maximum Depth`, `Clip Soils Minimum Depth`, `Soils Minimum Depth`, `Estimate wc and fc using Rosetta when soils have bd override`, `Initial soil saturation` | Use when the default soil-depth or starting-wetness assumptions are not defensible |
| `Phosphorus` | `Surface runoff concentration`, `Subsurface lateral flow concentration`, `Baseflow concentration`, `Sediment concentration` | Optional pollutant-sidecar settings for runs that need phosphorus output assumptions |
| `Export Configuration` | `Prep details`, `Geopackage export (.gpkg)`, `Legacy ArcMap export (.shp)` | Choose which deliverables should be generated automatically when a run completes |
| `Interchange` | `Delete raw WEPP outputs after successful interchange conversion` | Storage-management choice; keeps interchange products while discarding raw text outputs |
| `WEPP Exec` | `WEPP binary version`, `Run WEPP Watershed` checkbox, `Prep Only` button, `Run WEPP Watershed` button | Execution-mode controls, including whether the main run should include channel/watershed routing |
| `Revegetation Scenarios` | `Cover transformation scenario`, `Upload cover transform file (.csv)` | Post-fire cover-recovery scenario control when revegetation is enabled |

The most important practical distinctions are:

- `Run WEPP Watershed` inside `WEPP Exec` controls whether the main `Run WEPP` submission includes watershed/channel routing, not just hillslope execution.
- `Prep Only` and the `Bootstrap` no-prep buttons are advanced workflows for QA, export, or intentionally edited input files. They are not the normal starting point for scenario comparison.
- Most users should leave `Frost`, `Snow`, `PMET`, `Bedrock`, and `Phosphorus` at defaults unless they have a specific hydrologic reason to override them.

## What Happens When You Click Run

The visible buttons trigger different API-backed actions:

1. `Run WEPP`
   This submits the serialized form to `/rq-engine/api/runs/<runid>/<config>/run-wepp`. The payload includes any enabled advanced-option values, such as soil clipping, baseflow settings, export flags, and `reveg_scenario`. WEPPcloud stores those run settings, queues the WEPP hillslope workflow, and then loads the run-summary and results panels when the job finishes.

2. `Prep Only`
   This submits to `/rq-engine/api/runs/<runid>/<config>/prep-wepp-watershed`. It builds hillslope and watershed inputs only. It does not execute the full model.

3. `Run WEPP Watershed`
   This submits to `/rq-engine/api/runs/<runid>/<config>/run-wepp-watershed`. Use it when hillslope outputs already exist and you want only the watershed/channel routing pass. The UI itself warns that this requires a prior full WEPP run.

4. Bootstrap `Run WEPP Hillslopes and Watershed` or `Run WEPP Watershed`
   These use the no-prep bootstrap routes `/rq-engine/api/runs/<runid>/<config>/run-wepp-npprep` and `/rq-engine/api/runs/<runid>/<config>/run-wepp-watershed-no-prep`. They assume you have already cloned, edited, committed, and checked out the desired input files through `Bootstrap`. They skip normal preparation and rerun with the current bootstrapped inputs.

After a successful run, the controller fetches:

- `/runs/<runid>/<config>/report/wepp/results/`
- `/runs/<runid>/<config>/report/wepp/run_summary/`

That is why the `Run Results` area updates only after the queued job completes.

## Run, Prep, And Report Surfaces

### Run surface

The run surface is where you configure and queue model execution. This is where scenario choices, advanced options, and export-on-completion choices are submitted.

### Prep surface

`Prep Only` is the user-facing way to build WEPP inputs without executing the model. This is most useful when:

- you are checking whether inputs were built correctly,
- you want prep artifacts for QA or export,
- you are using bootstrap and plan to edit inputs outside the browser.

### Report surface

After a successful run, `Run Results` exposes the outputs users typically need first:

- `Watershed Loss Summary`
- `Return Periods Report`
- `Summary by Landuse Report`
- `Sediment Characteristics Report`
- `TotalWatSed3 CSV`
- `TotalWatSed2 CSV`
- `The Deval in the Details Report`
- `GL Dashboard`
- `Storm Event Analyzer` when available
- `Prep Details`
- `Post WEPP Geopackage Features Export`
- `Post WEPP Geodatabase (ESRI) Features Export`
- `Average Annual Report`
- `Yearly Report`
- `Daily Runoff / Lateral Flow / Baseflow Graph`

Read these as different views of the same run:

- use `Watershed Loss Summary` for outlet-scale planning numbers,
- use `Summary by Landuse Report` and mapped outputs to find source areas,
- use `Return Periods Report` for frequency-style interpretation,
- use the water-balance reports to understand whether a result is being driven by runoff generation, lateral flow, or baseflow.

Single-storm output is explicitly flagged in the UI as deprecated and unsupported. For event-scale work, the page points users to `Storm Event Analyzer` instead.

## How To Interpret WEPP Results

The most important distinction is scale:

- hillslope outputs tell you where runoff and sediment are generated,
- channel and watershed outputs tell you what is routed downstream,
- outlet values do not tell you which hillslopes caused the problem by themselves.

The second distinction is time scale:

- event-style outputs help explain storm behavior,
- annual and return-period outputs are better for planning and comparison,
- a single dramatic event can coexist with moderate long-term averages.

The strongest end-user use of WEPP is usually comparative:

- baseline versus burned,
- untreated versus treated,
- observed recovery versus assumed recovery,
- one advanced-option choice versus another.

## Core Model Assumptions And Limits

- WEPP is a physically based model, but it still simplifies the watershed into representative hillslopes and channels rather than modeling every field feature directly.
- Runoff is generated through infiltration-excess and saturation-excess mechanisms, so soil properties and starting wetness matter.
- Channel routing is only included when watershed/channel routing is enabled.
- Many advanced cards only write optional WEPP text inputs such as `frost.txt`, `snow.txt`, `tcr.txt`, or `pmetpara.txt`. If you enable them, you are replacing the default internal behavior with your chosen override values.
- `Baseflow Processing` is not implemented for single-storm climates.
- Very local features such as short road ditches, small berms, culverts, or engineered controls may not be represented unless another workflow models them explicitly.
- Results are only as defensible as the watershed delineation, soil inputs, climate record, land cover, burn severity, and treatment scenario behind them.
- A good outlet number does not prove the source-area pattern is correct. Review hillslope and channel outputs too.

## Related Docs

- [WEPP Model](../../wepp-model.md)
- [WEPP Advanced Options](../../wepp-advanced-options.md)
- [Getting Started](../../getting-started.md)
