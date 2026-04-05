# Gridded RUSLE

Use **RUSLE** when you want a map of long-term sheet-and-rill detachment potential across the watershed. In WEPPcloud, this workflow builds gridded factors for `A = R * K * LS * C * P` and then writes a final `A` raster for the factor choices you selected. It is a prioritization and interpretation layer, not a sediment-delivery model.

## What This Is For

Use Gridded RUSLE to answer questions such as:

- Where are the likely hillslope detachment hotspots in this watershed?
- How much do the hotspot patterns change if I use observed cover versus a scenario burn-severity lookup?
- How sensitive is the final `A` map to the K-factor method or to the R-factor source?

This tool is most useful when you need a fast, spatially explicit planning layer that complements WEPP rather than replaces it.

## What You See In The UI

The control card is titled **RUSLE**. The user-facing build options are:

| UI control | Values shown in the UI | Why it matters |
| --- | --- | --- |
| `R factor mode` | `WEPP Climate-Derived R`, `Momm 2025 County Climatology`, `Canonical RUSLE2` | Chooses the rainfall-erosivity source used for the whole run. |
| `C factor mode` | `Observed RAP`, `Scenario SBS` | Chooses whether cover comes from observed RAP cover data or from a scenario lookup based on disturbed class and soil burn severity. |
| `RAP year` | Year selector | Only shown when `Observed RAP` is selected. Picks which observed RAP year supplies the cover condition. |
| `K factor modes` | `POLARIS Nomograph`, `POLARIS EPIC` | Chooses which K rasters to build. You can build both for comparison. |
| `Default K mode for final A` | `POLARIS Nomograph` or `POLARIS EPIC` | Chooses which of the built K rasters is actually used in the final `A` raster. |
| `Maximum slope length cap` | Numeric field in meters | Limits slope length before the LS calculation. |
| `P factor scalar` | Numeric field | Applies one run-wide support-practice multiplier. |
| `Force POLARIS refresh before build` | Checkbox | Reacquires POLARIS inputs instead of reusing apparently aligned layers. |
| `Build RUSLE` | Main action button | Starts the asynchronous factor build and final `A` raster generation. |

## How To Choose The Build Options

### `R factor mode`

#### `WEPP Climate-Derived R`

Use this when you want the R factor tied to the WEPP climate already associated with the run. This is usually the most internally consistent choice when you are comparing RUSLE with WEPP outputs from the same project.

#### `Momm 2025 County Climatology`

Use this when you want a planning-climatology reference based on the watershed centroid. This is a reference-style R choice rather than a run-specific WEPP climate reconstruction.

#### `Canonical RUSLE2`

Use this when you want a more canonical RUSLE2-style reference climatology at the watershed centroid. This is useful for method comparison, but it is still a planning climatology rather than an event simulation.

### `C factor mode`

#### `Observed RAP`

Use this when you want current or historical observed cover conditions from the **Rangeland Analysis Platform**. The `RAP year` selector appears only in this mode. This is the best choice when your question is about actual observed ground-cover condition for a known year.

#### `Scenario SBS`

Use this when you want a planning scenario driven by land-cover family and soil-burn-severity class rather than observed RAP cover. In the UI help text, this mode uses landcover plus SBS classes, or unburned defaults when no SBS map is present. Use this mode for pre-fire/post-fire comparisons, treatment planning, or scenario work where you want the same scenario logic applied consistently across the watershed.

### `K factor modes`

#### `POLARIS Nomograph`

This is the default K estimator and is the closest fit to classic RUSLE-style K semantics. Use it when you want a RUSLE-facing soil erodibility interpretation.

#### `POLARIS EPIC`

Use this as a sensitivity or alternate method path. It is a valid built option, but it is less directly comparable to standard NRCS-style K interpretations than the nomograph approach.

#### `Default K mode for final A`

This setting matters more than many users expect. You can build both K rasters, but the final `A` raster uses only the one selected here. If you change the default K mode, the final `A` map can change even when every other input stays the same.

### `Maximum slope length cap`

The default is `304.8 m` (`1000 ft`), which the UI help ties to the RUSLE2 handbook basis. Change this only if you are deliberately testing sensitivity. Raising or lowering it changes LS and can shift where the largest `A` values appear.

### `P factor scalar`

This is a single run-wide multiplier for support practices. The default is typically `1.0`, meaning no reduction from support practices. Lower values reduce `A`; higher values increase it.

### `Force POLARIS refresh before build`

Use this when you suspect the cached POLARIS layers are stale, misaligned, or otherwise not the layers you want to rely on for the new build.

## What The Button Actually Does

When you click **Build RUSLE**, the UI submits a background request to:

- `POST /rq-engine/api/runs/{runid}/{config}/build-rusle`

The payload includes the user-facing selections:

- `r_mode`
- `c_mode`
- `rap_year` when `Observed RAP` is selected
- `k_modes`
- `default_k_mode`
- `max_slope_length_m`
- `p_value`
- `force_polaris_refresh`

The controller enforces at least one K mode, keeps `Default K mode for final A` synchronized with the checked K modes, removes `rap_year` from the payload when `Scenario SBS` is selected, and then queues the build.

When the job completes, the UI refreshes the **Run Results** area and loads links to:

- `GL Dashboard`
- `View RUSLE Outputs Directory`

Those are the main user-facing places to inspect the finished artifacts.

## Interpreting `A` Versus Delivered Sediment

The most important interpretation rule is this:

- `A` is modeled long-term average sheet-and-rill detachment potential.
- `A` is not delivered sediment at the channel.
- `A` is not delivered sediment at the watershed outlet.

If a cell has high `A`, it means the factor combination predicts high detachment potential there. It does not mean all of that sediment reaches a stream, survives channel routing, or leaves the basin.

Use **Gridded RUSLE** when the decision is about:

- hotspot identification,
- scenario comparison,
- understanding why one part of the landscape is more erosion-prone than another.

Use **WEPP** or another routing-capable workflow when the decision is about:

- runoff generation through time,
- sediment delivery to channels or the outlet,
- channel processes,
- treatment effects on delivered sediment rather than detachment potential alone.

## What The Factor Maps Mean

- `R` is rainfall erosivity. In this workflow it is a run-wide scalar, not a storm-by-storm map.
- `K` is soil erodibility from the selected POLARIS method.
- `LS` is the slope-length and steepness factor. This often explains why steep converging terrain lights up even when the other factors are moderate.
- `C` is the cover-management factor from either observed RAP cover or the scenario SBS lookup.
- `P` is the support-practice factor, applied here as one scalar for the run.

If the final `A` pattern looks surprising, inspect `LS`, `K`, and `C` first. Those three usually explain most of the spatial pattern.

## Assumptions And Limits

- This is a long-term average RUSLE-style detachment workflow, not an event simulation.
- It is explicitly not a sediment-delivery model, deposition model, channel erosion model, or gully erosion model.
- The current implementation is for WBT-based runs. TOPAZ-only runs are not the intended target.
- Some important data sources are US-specific in the current implementation, especially POLARIS and RAP-backed paths.
- `Scenario SBS` is a scenario-building path, not an observed-condition path.
- `Observed RAP` is best for actual condition by year, but only where RAP is appropriate for the site and question.
- The workflow is not a full clone of desktop RUSLE2. Treat it as a defensible gridded planning layer inside WEPPcloud, not as a one-for-one substitute.

## When To Prefer WEPP Instead

Prefer WEPP over Gridded RUSLE when you need:

- storm-event runoff and erosion timing,
- hillslope and watershed sediment delivery,
- channel routing effects,
- comparisons tied to full WEPP management and hydrology behavior.

Gridded RUSLE is strongest when you want a fast, transparent factor-based map to explain spatial vulnerability.

## Related Docs

- [WEPP](../wepp/ENDUSER.md)
- [Revegetation](../revegetation/ENDUSER.md)
- [Mods Overview](../../mods-overview.md)
