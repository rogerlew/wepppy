# Stevens Canyon focal-event attribution results

## Conclusion

The year-34/day-203 inversion is materially prepared by antecedent PMET soil
evaporation from the burned hillslopes. Over days 173–202, burned area-weighted
realized `Es` is 28.21 mm versus 2.32 mm undisturbed, an excess loss of
25.89 mm. That is close to the independently measured 23.0 mm undisturbed
advantage in layers 1–3 at the end of day 202.

This is not caused by different weather or less water arriving at the burned
surface. Both scenarios receive 84.4 mm precipitation/rain-plus-snowmelt, and
the PMET wetting term totals 71.46 mm burned versus 61.08 mm undisturbed. The
burned surface loses more water despite receiving 10.37 mm more modeled
wetting. Plant transpiration is nearly equal over the window (113.99 mm burned,
115.05 mm undisturbed). The 24.83 mm larger burned total `Ep + Es` is therefore
almost entirely the soil-evaporation increment.

On day 203, the common area-weighted PMET reference demand is exactly
8.933 mm/day in both scenarios. Burned `Es` is 3.620 mm versus 0.255 mm
undisturbed, while runoff is 4.237 versus 10.855 mm. Event-day evaporation
occurs after storm infiltration/runoff decisions and cannot create that day's
runoff retrospectively; its importance is the cumulative antecedent depletion.

## Process attribution

The paired trace identifies the source of the potential soil-evaporation
contrast:

| Day-203 term | Burned | Undisturbed |
|---|---:|---:|
| LAI | 2.257 | 10.759 |
| Root depth (m) | 0.400 | 1.219 |
| Soil coefficient `etke` | 0.4053 | 0.0285 |
| Water reduction `etkr` | 1.000 | 1.000 |
| Residue exposure `eaj` | 0.7185 | 0.0133 |
| Constrained coefficient `kecon` | 0.3874 | 0.00594 |
| Realized `Es` (mm/day) | 3.620 | 0.255 |

The Shapley-style swap of the constrained-soil proxy over days 173–202 assigns
the undisturbed-minus-burned change as follows:

- LAI soil-partition coefficient (`etke`): −53.07 proxy-mm;
- residue/exposed-area limit (`eaj × kcmax`): −15.52 proxy-mm;
- surface-water reduction (`etkr`): +9.80 proxy-mm;
- reference ET (`etorc`): effectively zero;
- net constrained-proxy change: −58.79 proxy-mm.

The proxy is intentionally not equated to realized `Es`: residue interception,
the minimum operator, and final water-availability correction make the realized
difference 25.89 mm. It nevertheless establishes direction. LAI partitioning
and reduced residue create the burned evaporative request; surface-water
limitation partially suppresses rather than causes the contrast. Atmospheric
reference demand is identical.

## Inversion mechanism

The supported event chain is now:

1. Fire management lowers LAI, residue, and rooting depth.
2. PMET reallocates demand toward exposed-soil evaporation.
3. During the 30-day antecedent window, burned hillslopes lose 25.89 mm more
   water through `Es`, despite greater modeled wetting.
4. Undisturbed hillslopes retain approximately 23 mm more water in layers 1–3
   and enter the storm with surface saturation 0.579 versus 0.379 burned.
5. The common 58.7 mm storm produces 10.85 mm undisturbed runoff versus
   4.24 mm burned above reach 173.
6. Channel routing carries that runoff-generation inversion to the outlet;
   previous timing experiments show routing is not its primary origin.

This is strong mechanistic attribution but not a state-swap proof. Management
also changes rooting, cover, interception, and infiltration. The near closure
between excess burned `Es` and the shallow-storage deficit, combined with
identical weather and greater burned wetting, makes PMET soil evaporation a
material antecedent cause. A restart/state-swap capability would be required
to claim it is the exclusive cause.

## Validation and provenance

- 26/26 paired runs completed with finite 36,525-day outputs and 31 retained
  trace rows per hillslope.
- Observation-on and observation-off water-balance outputs from the same
  rebuilt binary are byte-identical.
- Binary SHA-256:
  `68569cca4ed4e6d5936aad1e72bb3a516696e20cb4e6a1cf486d2d0f4ae80d66`.
- Source base: `wepp-forest` commit `2f65506d239b449bbb73c6820ff9cb949fa55158`.
- Both `wepp_ui.txt` files are present and have the expected empty-file hash
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- No watershed run was performed.
- The diagnostic source patch is retained in
  [`instrumentation.patch`](instrumentation.patch).
