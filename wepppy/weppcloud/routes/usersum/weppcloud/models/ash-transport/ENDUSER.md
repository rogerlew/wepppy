# Ash Transport (WATAR)

Use the `Wildfire Ash Transport And Risk (WATAR)` control when you need post-fire ash movement estimates that build on an existing WEPPcloud fire run. In WEPPcloud, this is a hillslope-and-watershed ash screening workflow that uses the run's hydrologic context from WEPP and then applies ash-specific transport assumptions on top of it.

## What This Is For

Use Ash Transport to answer questions such as:

- How much ash is likely to move off burned hillslopes?
- Which parts of the watershed contribute the most transported ash?
- How do ash loads change through time after a fire?
- How sensitive are results to different ash-calibration choices?
- Which scenarios suggest greater contaminant-loading concern after wildfire?

This workflow is for post-fire screening and comparison. It is not a replacement for field sampling, drinking-water compliance testing, or a full water-quality fate model.

## What You Actually See In The UI

The control card is titled `Wildfire Ash Transport And Risk (WATAR)`. The visible run controls are:

| UI control | What the user sees | Why it matters |
| --- | --- | --- |
| `Fire day for ash model (month/day)` | Fire timing input | Anchors when the ash model starts relative to the post-fire simulation period |
| `Ash depth mode` | `Specify Depth`, `Specify Load`, `Upload Maps` | Chooses whether you enter ash as depths, loads, or raster inputs |
| `Initial ash depth – moderate/low severity` and `Initial ash depth – high severity` | Only shown in `Specify Depth` mode | Directly sets the starting ash depth by severity class |
| `Initial ash load – high severity` and `Initial ash load – moderate/low severity` | Only shown in `Specify Load` mode | Sets ash as surface load instead of depth |
| `Load map (tonne/ha)` | Only shown in `Upload Maps` mode | Required raster input for gridded ash loads |
| `Ash type map (optional)` | Only shown in `Upload Maps` mode | Optional raster where `0 = none`, `1 = black ash`, `2 = white ash` |
| `Field-measured ash bulk density – low/moderate severity` and `Field-measured ash bulk density – high severity` | Always visible | Used directly in load-based setup and as ash-property context |
| `Run Model` | Main action button | Starts the ash run or, in batch/base-project contexts, saves ash settings for later processing |

Under `Advanced options`, the user also sees:

- `Run wind transport`
- `Ash model`
- `Transport mode` when `Ash model = Watanabe2025`
- white-ash and black-ash property fields such as bulk density, particle density, decomposition factor, roughness limit, and model-specific transport parameters

## What Each `Ash depth mode` Means

### `Specify Depth`

Use this when you already want to enter ash thickness directly in millimeters.

The visible fields are:

- `Initial ash depth – moderate/low severity`
- `Initial ash depth – high severity`

This is the simplest setup path when you have defensible depth assumptions by severity class.

### `Specify Load`

Use this when your initial ash information is better expressed as surface mass rather than thickness.

The visible fields are:

- `Initial ash load – high severity`
- `Initial ash load – moderate/low severity`
- `Field-measured ash bulk density – low/moderate severity`
- `Field-measured ash bulk density – high severity`

In the current rq-engine route, WEPPcloud converts the entered loads to ash depth before enqueueing the run. That means bulk density is not just metadata in this mode; it changes the starting ash depth the model actually uses.

### `Upload Maps`

Use this when the ash distribution is spatially variable enough that one value for the whole burned area is too coarse.

The visible fields are:

- `Load map (tonne/ha)` required
- `Ash type map (optional)`

The upload help is explicit that raster uploads should remain under `100 MB` and retain source projection. In the current route, `Upload Maps` fails if the load map is missing. The ash-type map is optional.

### Practical caution

The top-level setup fields are labeled by burn-severity grouping, while many advanced fields are labeled by `white ash` and `black ash`. Treat those as one connected parameterization, not as unrelated inputs. If you are calibrating carefully, keep your severity-based setup assumptions and your white/black ash property assumptions internally consistent.

## Available Models

In `Advanced options`, the `Ash model` dropdown currently shows:

- `Srivastava2023`
- `Watanabe2025`

If you choose `Watanabe2025`, a second dropdown appears: `Transport mode`, with:

- `Dynamic`
- `Static`

Both model families use the same watershed, climate, burn-severity, and WEPP runoff context. The difference is how they convert ash availability and runoff conditions into transported ash.

| UI option | Additional UI option | Main assumption | Mode-specific fields the user sees |
| --- | --- | --- | --- |
| `Srivastava2023` | None | Simpler depletion-style ash transport formulation | `Initial erodibility (white ash)`, `Initial erodibility (black ash)`, `Final erodibility (white ash)`, `Final erodibility (black ash)` |
| `Watanabe2025` + `Dynamic` | `Transport mode = Dynamic` | The UI text says `Dynamic formulation with K(x)` and states transport capacity responds to shear stress, organic matter, and ash availability | `Organic matter (white ash, fraction)`, `Organic matter (black ash, fraction)` |
| `Watanabe2025` + `Static` | `Transport mode = Static` | The UI text says `Static exponential formulation (A, B)` and states transport follows a fixed exponential decay controlled by initial capacity `A` and depletion coefficient `B` | `Initial transport capacity (white ash, t ha^-1 mm^-1)`, `Initial transport capacity (black ash, t ha^-1 mm^-1)`, `Depletion coefficient (white ash, mm^-1)`, `Depletion coefficient (black ash, mm^-1)` |

All three model choices still share a large common set of ash-property fields, including:

- `Initial bulk density (white ash)` and `Initial bulk density (black ash)`
- `Final bulk density (white ash)` and `Final bulk density (black ash)`
- `Bulk density factor (white ash)` and `Bulk density factor (black ash)`
- `Particle density (white ash)` and `Particle density (black ash)`
- `Ash decomposition factor (white ash, 1/day)` and `Ash decomposition factor (black ash, 1/day)`
- `Roughness limit (white ash)` and `Roughness limit (black ash)`

The control description above the form also states that ash depths below the roughness limit are treated as non-transportable.

## How The Model Choices Differ

`Srivastava2023` is the simpler baseline option. It keeps the older depletion-style structure and exposes explicit erodibility terms.

`Watanabe2025` with `Dynamic` is the more process-sensitive option. The visible UI description says transport capacity responds to shear stress, organic matter, and ash availability. Use it when you want the newer calibration family and the more dynamic transport-capacity formulation.

`Watanabe2025` with `Static` stays in the Watanabe family but switches to the fixed `A, B` style transport-capacity decline shown in the UI text. Use it when you want the newer family without the dynamic `K(x)` formulation.

For each runoff timestep, Static mode subtracts the exponential capacity after the current ash-runoff increment from the capacity at the previous cumulative ash runoff. This produces a nonnegative daily increment that declines for equal runoff increments as cumulative runoff increases. The model clips that increment to the ash remaining on the hillslope.

If you compare `Srivastava2023`, `Watanabe2025 Dynamic`, and `Watanabe2025 Static` on the same watershed, treat the differences as model-structure uncertainty. A difference across those runs means the answer is sensitive to the transport assumptions, not that one option is automatically correct by itself.

## What The Button Actually Does

### `Run Model`

Clicking `Run Model` submits a multipart form request to:

- `POST /rq-engine/api/runs/<runid>/<config>/run-ash`

The rq-engine route requires:

- `ash_depth_mode`
- depth fields when `ash_depth_mode = 1`
- load and bulk-density fields when `ash_depth_mode = 0`
- a `Load map (tonne/ha)` upload when `ash_depth_mode = 2`

If validation passes, WEPPcloud updates the Ash controller state, stores uploads when present, and either:

- enqueues `run_ash_rq` for a normal run, or
- returns `Set ash inputs for batch processing` when the run is in batch/base-project context

### `Run wind transport`

This checkbox is not only submitted on the next full run. In the current controller, changing it posts immediately to:

- `/runs/<runid>/<config>/tasks/set_ash_wind_transport/`

Use it when you want the ash workflow to include wind-driven removal in addition to water-driven transport. If you are comparing scenarios, keep this setting consistent unless wind transport itself is the thing you are testing.

## What You See In Results

After a successful run, the ash run-summary surface shows:

- `View Watershed Ash Transport Model Results`
- `Contaminant and Reservoir Loading Analysis`

If the watershed has no burned hillslopes, the run summary instead says:

- `Watershed does not have burned hillslopes.`

These are report surfaces, not setup controls. The watershed and contaminant reports are where the user interprets results after the background job completes.

## Interpreting Results

The most useful outputs are usually:

- hillslope patterns showing likely ash source areas,
- daily or annual transport totals,
- cumulative transported ash over the modeled period,
- burn-severity summaries,
- contaminant-loading summaries when those outputs are configured,
- wind-transport totals when `Run wind transport` is enabled

High ash transport usually reflects some combination of:

- more starting ash available,
- stronger runoff forcing from the WEPP side,
- model settings that keep ash transportable for longer,
- less ash being trapped below the roughness limit

If values are low, that can mean either ash supply was limited or the selected transport assumptions made ash less available for movement.

## Assumptions And Limits

- Ash Transport is a post-fire comparison workflow that depends on the existing WEPP hydrologic context. If the WEPP fire run is weak, the ash results will be weak too.
- `Ash model` and, for `Watanabe2025`, `Transport mode` materially affect results. They can change both total transport and source-area ranking.
- `Specify Load` is not just another way to enter the same thing. The route converts load and bulk density into the starting depth used for the run.
- `Upload Maps` requires a load map. The ash-type map is optional.
- `Run wind transport` changes the process assumptions. Compare like with like if your goal is scenario ranking rather than process sensitivity.
- The UI mixes severity-based setup labels with white/black ash property labels. Use care when mapping your field assumptions into the visible controls.
- Contaminant outputs indicate modeled ash-associated loading potential, not confirmed concentration at a real sampling point.

## Related Docs

- [WEPP](../wepp/ENDUSER.md)
- [Getting Started](../../getting-started.md)
- [Mods Overview](../../mods-overview.md)
