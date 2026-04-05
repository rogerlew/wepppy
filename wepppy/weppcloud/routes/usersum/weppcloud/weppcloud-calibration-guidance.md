# WEPPcloud Calibration Guidance

Use this page when you have observed streamflow, sediment, or phosphorus data and need to tune a WEPPcloud run without turning calibration into unconstrained parameter fitting. It summarizes practical calibration guidance for WEPPcloud and keeps the detailed parameter definitions in [Disturbed Land Soil Lookup Table](./disturbed-land-soil-lookup.md).

## What This Is For

This page helps you answer four practical questions:

1. What counts as a defensible calibrated model in WEPPcloud?
2. What should I calibrate first?
3. Which kinds of mismatch point to which parameter family?
4. When should I stop changing parameters?

The core recommendation is simple: use **minimal calibration** so the model remains transferable to related watersheds and scenarios. Start with the most defensible hydrologic controls, fit the undisturbed condition first, and change one parameter family at a time.

## Before You Start

Before you begin calibration, make sure you have:

- a completed WEPPcloud run for the watershed,
- observed outlet data that overlap the simulated period,
- a clear calibration target such as annual water yield, peak discharge, recession behavior, annual sediment yield, or annual phosphorus load,
- a representative climate choice for the watershed and period of interest,
- a reason to calibrate beyond the default setup.

If you do not yet trust the climate, watershed delineation, soils, or observed data, fix those first. Parameter tuning cannot reliably compensate for poor forcing data or the wrong watershed setup.

## What Counts as a Good Model?

No single metric decides whether a model is "good." In practice, use several metrics together and also inspect the hydrograph shape, annual totals, and process realism.

| Metric | What it tells you | Practical reading |
| --- | --- | --- |
| `NSE` (Nash-Sutcliffe Efficiency) | How well the modeled time series beats simply using the observed mean | `1` is perfect, `0` is no better than the mean, `<0` is worse than the mean; values around `0.40-0.99` are often treated as good to excellent in applied hydrology |
| `KGE` (Kling-Gupta Efficiency) | A balanced score that combines correlation, bias, and variability | `1` is perfect; `>0` is generally useful; `>0.5` is commonly treated as satisfactory |
| `PBIAS` (Percent Bias) | Whether the model systematically overpredicts or underpredicts | `0` is ideal; values near zero are better than large positive or negative bias |

Use these as decision aids, not pass/fail laws. A model with a defensible annual water balance and recession shape may be more useful than a model that scores slightly higher on one metric but gets the dominant processes wrong.

Strong watershed-scale performance is possible with limited calibration. In one multi-watershed undisturbed application, average streamflow skill across 28 forested watersheds reached daily, monthly, and annual NSE values of about `0.55`, `0.70`, and `0.87`, with corresponding KGE values of about `0.70`, `0.78`, and `0.84`. Treat those as examples of credible performance, not as universal thresholds.

## Recommended Calibration Order

Calibrate in this order unless you have a strong reason not to:

1. Start with **undisturbed** conditions.
2. Calibrate **streamflow** first.
3. Calibrate **sediment** after streamflow is defensible.
4. Calibrate **phosphorus** only after hydrology and sediment are acceptable.
5. Use the **post-fire** run mainly as a validation of the soil burn severity setup, not as the first place to start manual parameter tuning.

This order matters because poor runoff timing, poor snow partitioning, or the wrong baseflow behavior can make sediment and phosphorus comparisons misleading.

## Streamflow Calibration for Undisturbed Conditions

For undisturbed forested watersheds, streamflow is commonly coming from:

- lateral flow,
- baseflow,
- and, in some settings, saturation-excess runoff.

Start with the simplest process questions:

| Calibration question | What to inspect first | Primary lever | Typical directional rule |
| --- | --- | --- | --- |
| Does the climate represent the watershed? | climate source, snow seasonality, rain vs snow partition | `Rain-snow threshold` | Use `0` for `CLIGEN` and `Daymet`, and `-2` for `GridMET` unless you have evidence for another threshold |
| Is annual water yield too high? | long-term `P - Q = ET` balance | `Basal crop coefficient` | If modeled water yield is too high, increase ET by increasing `kcb` |
| Is annual water yield too low? | long-term `P - Q = ET` balance | `Basal crop coefficient` | If modeled water yield is too low, decrease ET by lowering `kcb` |
| Are peak flows too high? | return periods, storm peaks, flashy runoff behavior | `Bedrock conductivity` | Increase `kslast` to allow more deep seepage and reduce quick runoff response |
| Are peak flows too low? | return periods, storm peaks, muted runoff response | `Bedrock conductivity` | Decrease `kslast` to restrict deep seepage and keep more water in quickflow pathways |
| Is recession too slow? | falling limb after storms, seasonal low-flow decline | `Baseflow coefficient` | Increase the baseflow coefficient so groundwater drains faster |
| Is recession too fast? | falling limb after storms, seasonal low-flow decline | `Baseflow coefficient` | Decrease the baseflow coefficient so groundwater drains more slowly |

Two important cautions:

- `Effective hydraulic conductivity` is a major runoff-control parameter, but it should be treated as field-based and not changed casually.
- If the hydrology is poor, do not move on to sediment calibration yet.

## Sediment Calibration for Undisturbed Conditions

For relatively undisturbed forested watersheds, the conceptual message is:

- hillslopes are usually **less likely** to be the dominant sediment source,
- channels are usually **more likely** to control the watershed sediment signal.

That leads to a different calibration mindset than the one many users start with.

| Calibration question | Start here | Why |
| --- | --- | --- |
| Annual sediment is too high or too low, but flow is already reasonable | `Channel critical shear stress` | In undisturbed settings, channel erosion often controls the watershed sediment signal more than hillslope detachment |
| You are tempted to change `ki`, `kr`, or hillslope `shcrit` first | Usually do **not** start there | Those hillslope disturbed-soil parameters should be left at defaults in most cases |
| You want a first estimate for channel critical shear | use `D50` as a practical starting point | Channel critical shear can be approximated from bed-material particle size in millimeters |

Practical interpretation:

- Higher channel critical shear means **less channel erosion**.
- Lower channel critical shear means **more channel erosion**.
- Typical examples include `70-170` for coarse-bed West Cascades style channels and `20-50` for more erosion-prone Inland Pacific Northwest settings.

If you have not yet achieved reasonable streamflow, do not try to fix sediment with channel parameters alone.

## Phosphorus Calibration

Phosphorus should be calibrated last. A practical starting point is to use average annual concentrations for:

- surface runoff,
- lateral flow,
- baseflow,
- and sediment-attached phosphorus.

Those values can improve constituent-load estimates, but they do not fix hydrologic problems. If streamflow or sediment behavior is poor, correct those first.

## Post-Fire Calibration Guidance

The recommended approach for post-fire calibration is intentionally conservative.

For post-fire runs:

- use the `SBS` map,
- assume streamflow is more likely to be driven by **infiltration-excess runoff**,
- assume sediment is more likely to come from **hillslopes** and less from channels,
- and **make no manual parameter changes** unless you have strong site-specific evidence.

The reason is that WEPPcloud already alters soil and vegetation properties by burn severity. If the post-fire run is poor, first check:

1. whether the `SBS` map is representative,
2. whether the climate and event period are representative,
3. whether the watershed build and channel network are credible,
4. whether the undisturbed baseline was already defensible.

Do not treat the disturbed land soil lookup table as the first place to tune a burned watershed. In most post-fire workflows, it is better to improve the inputs than to manually override the severity-driven parameterization.

## Calibration Workflow Checklist

Use this checklist to keep the process disciplined:

1. Confirm that the observed record overlaps the simulated period.
2. Start with the **undisturbed** run, not the burned run.
3. Make sure the climate source and rain-snow threshold are defensible.
4. Check annual water yield before worrying about daily details.
5. Check peak discharge and return-period behavior.
6. Check recession behavior.
7. Only then move to sediment.
8. Change one parameter family at a time.
9. Re-run WEPP after each change and record what changed.
10. Stop when the fit is good enough for the management decision, not when you have exhausted every possible parameter.

## What Not To Do

- Do not start by changing many parameters at once.
- Do not use calibration to compensate for a poor watershed delineation or the wrong climate.
- Do not calibrate a post-fire run first and then assume the same changes are valid for the undisturbed case.
- Do not use a single metric by itself to declare success.
- Do not assume a better numerical score always means a more defensible process representation.

## Related Docs

- [Observed Model Fitting](./observed-model-fitting.md)
- [Disturbed Land Soil Lookup Table](./disturbed-land-soil-lookup.md)
- [WEPP Advanced Options](./wepp-advanced-options.md)
- [Climate Options](./climate-options.md)
- [WEPP](./models/wepp/ENDUSER.md)
