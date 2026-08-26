# Topanga Investigation Handoff

Hi Bill, Mariana, Erin, and Anurag,

Thanks for the report.

This details the 9002 soils and the additional parameters:
[WEPPcloud soil-file specifications](https://wepp.cloud/weppcloud/usersum/doc/usersum.input_file_specifications.soil_file_spec).

The 14 parameters are read but aren't used by the model. They were added for
Anurag to support development. We would need to create yet another soil version
to remove them, so I opted to leave them.

We (Codex and Roger) ballpark replicated your Hill 106 Windows results. The
main takeaway is that WEPPcloud runs with neither `wepp_ui.txt` nor
`pmetpara.txt` most closely reproduce the reported Windows results.

For the unburned hillslope, our ordinary Windows run gave `226 mm` runoff,
`365 mm` ET, and `21 mm` lateral flow. You reported `220`, `368`, and `22 mm`.
That is the closest match we found.

Adding `wepp_ui.txt` changed the answer dramatically. Lateral flow increased
from `21` to `120 mm/year`, while runoff and ET both decreased. With PMET also
enabled, lateral flow reached `145 mm/year`. This sidecar turns on the hourly
lateral-flow update used by WEPPcloud. Its effect is large enough that we are
confident it was not present for your Windows runs.

Adding `pmetpara.txt` by itself switched the run from legacy Penman ET to
Penman-Monteith ET. ET decreased from `365` to `336 mm/year`; runoff increased
from `226` to `250 mm/year`; and lateral flow increased slightly from `21` to
`25 mm/year`. This also moved the result away from your reported values, so
`pmetpara.txt` was probably absent too.

The two files interact. With both present, lower ET leaves more water available
for the hourly lateral-flow routine. We should therefore treat them as two
parts of the water balance, not as independent adjustments.

Earlier this week we investigated an anomaly identified by Scott on the
Stevens Canyon fire with peak flow that traced down to the `pmetpara.txt` ET
partitioning.

The largest reversal occurred in simulation year 34 on day 203, with
`58.7 mm` of rain. The undisturbed scenario produced the higher peak at all
three reaches we examined, even though the burned scenario would normally be
expected to respond more strongly.

The 30 days before that storm show what happened. These are area-weighted soil
evaporation totals:

| Reach | Burned (mm) | Undisturbed (mm) | Burned/undisturbed |
| ---: | ---: | ---: | ---: |
| 169 | 33.12 | 1.32 | 25.1× |
| 172 | 27.74 | 1.88 | 14.8× |
| 173 | 28.20 | 2.31 | 12.2× |

At reach 169, for example, the model removed `77.4 mm` as total ET from the
burned hillslopes during those 30 days, versus `38.0 mm` undisturbed. On the
storm day itself, burned-soil evaporation was another `4.50 mm`, compared with
only `0.05 mm` undisturbed. The burned profile entered the storm drier and
produced only `0.31 mm` of surface runoff, while the undisturbed profile
produced `22.17 mm`. The same pattern, though less extreme, appeared at reaches
172 and 173.

The concern is how the FAO-56 partition is constructed. In this implementation,
LAI divides nearly the same potential ET demand between plants and soil:

`plant share = 1 - exp(-0.45 × LAI)`

`soil share = exp(-0.45 × LAI)`

When fire reduces LAI, the plant share falls but the soil share rises by almost
the same amount. In other words, loss of living canopy mostly transfers demand
from transpiration to soil evaporation instead of reducing total ET. Lower
residue after fire exposes still more soil. For recently burned forest, this
can sustain implausibly large soil-water losses before a storm, dry the burned
profile relative to the forested profile, and reverse the expected runoff and
peak-flow response. Changing the PMET crop coefficient scales demand but does
not independently fix this plant-versus-soil partition.

We also matched your burned result after adjusting the management file. Our
best 40-year ballpark gave:

|  | Our replay | Your result |
| --- | ---: | ---: |
| Runoff (mm/year) | 245 | 246 |
| ET (mm/year) | 345 | 346 |
| Lateral flow (mm/year) | 18.2 | 18 |
| Maximum lateral flow (mm/day) | 0.80 | 0.8 |

That match used a `0.5 m` root depth, initial canopy/interrill cover of
`0.70/0.90`, and maximum LAI of `2.25`. It is a fitted approximation, not proof
of your original settings.

One other useful finding: the `0.8 mm/day` burned maximum is not a fixed cap in
the code. It comes from the soil-water conditions in this run. With
`wepp_ui.txt` active, the same hillslope reached more than `10 mm/day`.

---

## Here is the full arc

The short version is that there are two different problems superimposed in
these runs:

1. The undisturbed watershed is probably not losing enough water through ET.
   WEPP does not represent the dense channel vegetation or the mixture of
   shrubs, tall grasses, and buffered hillslope vegetation visible at this
   site. That likely leaves the modeled intact watershed too responsive and
   makes saturation-excess runoff more common than it should be.
2. WEPP has a separate event-scale peak-flow defect. When a soil profile
   produces daily saturation surplus, WEPP assigns that daily water volume an
   artificial within-storm timing. The assigned rate depends strongly on the
   duration of infiltration excess. A small parameter change can therefore
   produce a much larger peak even when total event runoff decreases. A second
   discontinuity switches between two peak solvers based on a ponding-time
   sentinel.

The first problem affects the watershed's antecedent water balance and how
often the second problem is activated. It does not explain or validate the
counter-intuitive peak calculations.

### Where We Started

Bill's report showed the surprising result that the original undisturbed
Topanga scenario had larger 2-, 5-, and 10-year peaks than the burned scenario.
It also reported large differences between WEPPcloud and Windows WEPP,
especially in lateral flow, and compared the model with approximately
`6.2 mm` of calendar-year 2020 discharge at the Los Angeles County Topanga
Creek F54C-R gauge.

We treated those results as hypotheses and worked backward from the archived
inputs and raw output. We did not need Bill's original files to get a useful
reconstruction.

One bookkeeping correction matters throughout this discussion. The `288 mm`
WEPPcloud value in the report is not calendar-year 2020 surface runoff. It is
the long-term Hill 106 average of `121 mm/year` surface runoff plus
`167 mm/year` lateral flow. The analogous `242 mm` Windows value is the
long-term average of approximately `220 + 22 mm/year`. The archived WEPPcloud
Hill 106 result for 2020 is `9.74 mm` surface runoff plus `105.92 mm` lateral
flow, or `115.66 mm` combined.

The `6.2 mm` observation is channel discharge, not surface runoff alone. It is
reproduced from `234 acre-feet` of calendar-year 2020 flow divided by the
reported `18.0 square mile` gauge drainage area. It includes all upstream
surface, subsurface, groundwater, storage, and loss processes. The gauge also
does not exactly match the modeled watershed boundary, so `6.2 mm` is a useful
magnitude check rather than a direct calibration target.

## Reconstructing the Windows Runs

We ballpark-reproduced Bill's Hill 106 Windows results by testing the two
WEPPcloud sidecars that are not part of a conventional Windows run but are used by default in weppcloud:

- `wepp_ui.txt`, which activates the hourly waterbalance seepage/lateral-flow update used by
  WEPPcloud; and
- `pmetpara.txt`, which switches ET from the legacy Penman path to the optional
  FAO-56-style Penman-Monteith pathway.

For the unburned hillslope, the ordinary Windows-style run with neither file
gave `226 mm/year` runoff, `365 mm/year` ET, and `21 mm/year` lateral flow.
Bill reported `220`, `368`, and `22 mm/year`. That is the closest match.

Adding only `wepp_ui.txt` increased lateral flow from `21` to approximately
`120 mm/year` and reduced both runoff and ET. Adding both files raised lateral
flow to approximately `145 mm/year`. The effect is much too large to have been
present in the Windows result Bill reported.

Adding only `pmetpara.txt` changed ET from `365` to `336 mm/year`, runoff from
`226` to `250 mm/year`, and lateral flow from `21` to `25 mm/year`. That also
moved the result away from Bill's values. Our best interpretation is therefore
that the reported Windows runs used neither sidecar.

The files are not independent corrections. PMET changes how much water remains
in the profile, and the hourly seepage routine then acts on that altered water
balance. The large WEPPcloud-versus-Windows lateral-flow difference is mainly a
configuration difference, not a mysterious platform difference.

We also reproduced Bill's burned Hill 106 result with a fitted management
approximation:

| Long-term result | Our reconstruction | Bill's result |
| --- | ---: | ---: |
| Runoff | 245 mm/year | 246 mm/year |
| ET | 345 mm/year | 346 mm/year |
| Lateral flow | 18.2 mm/year | 18 mm/year |
| Maximum lateral flow | 0.80 mm/day | 0.8 mm/day |

That lane used a `0.5 m` root depth, initial canopy/interrill cover of
`0.70/0.90`, and maximum LAI of `2.25`. It is a useful ballpark, not proof of
Bill's exact original management inputs. The apparent `0.8 mm/day` lateral-flow
maximum is also not a hard-coded cap. The same hillslope exceeds `10 mm/day`
when the hourly seepage sidecar is active.

## The Restrictive Layer and the 2020 Water Balance

The original Hill 106 soil contains a highly restrictive lower boundary.
Historically, WEPPcloud's automatic `kslast` assignment moved from `0.01` of
minimum horizon Ksat, to the full minimum Ksat in 2020, back to `0.01` in 2023,
and then to the current `0.001` rule. For Hill 106, the current rule produces
`0.000108 mm/h`, rounded to `0.00011 mm/h` in the soil file.

Using original horizon Ksat, anisotropy `10`, and PMET `Kcb = 0.95`, the 2020
Hill 106 response is:

| Fraction of minimum Ksat | `kslast` | Surface runoff | Lateral flow | Combined runoff |
| ---: | ---: | ---: | ---: | ---: |
| `0.001×` | 0.000108 mm/h | 9.74 mm | 105.92 mm | 115.66 mm |
| `0.01×` | 0.00108 mm/h | 9.75 mm | 104.41 mm | 114.16 mm |
| `0.1×` | 0.0108 mm/h | 9.87 mm | 91.47 mm | 101.34 mm |
| `1.0×` | 0.108 mm/h | 10.07 mm | 29.11 mm | 39.18 mm |
| No restrictive layer | — | 10.08 mm | 2.08 mm | 12.16 mm |

This is substantial leverage: removing the restriction moves the Hill 106
surface-plus-lateral total from `115.66` to `12.16 mm`, almost ten times closer
to the provisional `6.2 mm` magnitude. Reasonable horizon-Ksat, anisotropy, and
Kcb changes have much less influence. Our closest screened, reasonably bounded
Hill 106 case produced `9.35 mm` with no effective restriction, anisotropy `1`,
and `Kcb = 1.20`.

That does not mean the whole watershed would discharge only `12 mm`. Removing
the restriction redirects water into deep percolation and WEPP's groundwater
reservoir, from which much of it returns as baseflow.

For the complete 140-hillslope undisturbed watershed in 2020:

| Component | Original WEPPcloud | No restriction, `Kcb = 1.20` |
| --- | ---: | ---: |
| Precipitation | 337.38 mm | 337.38 mm |
| Surface runoff | 11.48 mm | 5.74 mm |
| Lateral flow | 114.12 mm | 11.97 mm |
| Deep percolation | 0.43 mm | 82.98 mm |
| Groundwater baseflow | 0.44 mm | 133.84 mm |
| ET | 265.77 mm | 262.76 mm |
| Component-sum streamflow | 126.04 mm | 151.55 mm |
| Routed outlet flow | 125.61 mm | 149.68 mm |

Lateral flow collapses, but groundwater return more than replaces it. The
no-restriction run therefore has more routed outlet flow, not less. This is why
neither Hill 106 surface runoff nor Hill 106 surface-plus-lateral flow can be
treated as watershed discharge.

## A Controlled Burned-Versus-Undisturbed Comparison

We next ran burned and undisturbed versions of the complete watershed with the
same climate, original horizon Ksat and anisotropy, no restrictive layer, and
PMET `Kcb = 1.20` for the natural hillslopes. Developed hillslopes remained
developed in both scenarios.

The 2020 water balance was:

| Component | Burned | Undisturbed | Burned minus undisturbed |
| --- | ---: | ---: | ---: |
| Precipitation | 337.38 mm | 337.38 mm | 0.00 mm |
| Surface runoff | 10.47 mm | 5.86 mm | +4.61 mm |
| Lateral flow | 19.00 mm | 11.97 mm | +7.03 mm |
| Deep percolation | 158.47 mm | 83.62 mm | +74.85 mm |
| Groundwater baseflow | 217.90 mm | 134.60 mm | +83.30 mm |
| ET | 141.58 mm | 261.96 mm | -120.38 mm |
| Routed outlet flow | 245.28 mm | 150.57 mm | +94.71 mm |

At an annual scale, the model behaves in the expected direction: the burned
watershed has much lower ET and much greater outlet flow. The unexpected result
is in the event peaks.

## Return Periods Still Show the Inversion

We applied the same Gringorten-corrected return-period method used in Bill's
analysis to these 45-year no-restriction, `Kcb = 1.20` runs:

| Return period | Burned peak | Undisturbed peak | Burned difference |
| ---: | ---: | ---: | ---: |
| 2 years | 63.17 m³/s | 87.62 m³/s | -27.9% |
| 5 years | 83.95 m³/s | 112.51 m³/s | -25.4% |
| 10 years | 106.00 m³/s | 138.19 m³/s | -23.3% |
| 20 years | 124.38 m³/s | 161.64 m³/s | -23.1% |
| 25 years | 145.55 m³/s | 174.67 m³/s | -16.7% |

Undisturbed is higher at every return period. This confirms that the inversion
is not caused solely by the restrictive layer.

There is an important limitation: the burned and undisturbed series are ranked
independently, so each row can compare different storms. Return-period tables
describe the distributions, but they are a poor way to diagnose the process.
We therefore took the union of the ten dates selected by the two curves and
compared both scenarios on every date.

Undisturbed had the larger peak on seven of those ten shared dates. The median
undisturbed-to-burned peak ratio was `1.53`, yet **daily component-sum streamflow
differed by only `3.5%` on average**. Mean event-day differences were only
`1.7 mm` for surface runoff, `0.8 mm` for lateral flow, and `0.04 mm` for ET.
Thirty-day ET and prior-day channel storage did not consistently predict which
scenario had the larger peak.

This was the first clear indication that the anomaly was primarily about
within-day hydrograph construction rather than daily water volume.

The watershed binary used for those runs does not export a usable
total-profile antecedent soil-water state. We did not infer one from incomplete
fields. Hill 106 was therefore the appropriate place to obtain a complete
event-level comparison with the newer diagnostic binary.

## Antecedent Moisture Did Not Explain the Hill 106 Inversions

The Hill 106 event record contains 201 dates on which both burned and
undisturbed produced a positive peak. Contrary to our initial suspicion, the
modeled undisturbed profile was usually drier:

| Paired Hill 106 statistic | Result |
| --- | ---: |
| Median undisturbed-minus-burned pre-event soil water | -15.66 mm |
| Mean undisturbed-minus-burned pre-event soil water | -26.82 mm |
| Events where undisturbed was wetter | 11 of 201 (5.5%) |
| Events where undisturbed peak was higher | 88 of 201 (43.8%) |

On the 88 dates with an undisturbed peak inversion, undisturbed was drier in
80 cases (`90.9%`). Its median antecedent deficit was `15.81 mm`, while its
median peak was `1.65` times the burned peak. Even among the 14 inversion dates
where runoff volumes differed by no more than `1 mm`, undisturbed was drier in
12.

This rules out “undisturbed starts wetter” as the general explanation for the
modeled inversion. Antecedent saturation still matters because it controls the
production of soil-water surplus, but the direction of the paired soil-water
difference does not explain why undisturbed peaks are larger.

## The Ksat Mutation Exposed the Peak-Flow Defect

The burned and undisturbed Hill 106 inputs differ in several ways. We isolated
first-horizon Ksat because burned uses `20 mm/h` and undisturbed uses
`35 mm/h`. We ran:

- burned management and soil with Ksat `20`;
- the identical burned case with only Ksat changed to `35`; and
- undisturbed management and soil with Ksat `35`.

The February 14, 1980 event was nearly controlled:

| Case | Pre-event soil water | Runoff | `PeakRO` |
| --- | ---: | ---: | ---: |
| Burned, Ksat 20 | 211.87 mm | 60.12 mm | 47.71 mm/h |
| Burned, Ksat 35 | 211.85 mm | 58.63 mm | **92.71 mm/h** |
| Undisturbed, Ksat 35 | 201.91 mm | 59.91 mm | **94.09 mm/h** |

Changing only burned Ksat almost reproduced the undisturbed peak even though
the Ksat-35 burned run had slightly less runoff and effectively identical
antecedent soil water. At first we described this as higher Ksat filtering out
low-intensity excess and leaving a shorter, sharper pulse. Source-level
instrumentation showed that explanation was incomplete and physically
misleading.

### What WEPP Actually Does

Higher Ksat allows more storm water into an already wet profile. WEPP's daily
water-balance routine then returns some of that water as soil-water surface
surplus. The peak-flow routine has no physical subdaily time series for this
returned water. It assigns one by dividing the complete daily surplus by the
duration of positive infiltration excess and adding that rate only to the
intervals where excess is already occurring.

For this event:

| Instrumented operand | Ksat 20 | Ksat 35 |
| --- | ---: | ---: |
| Final runoff volume | 60.122 mm | 58.630 mm |
| Daily soil-water surface surplus | 36.999 mm | 51.637 mm |
| Positive-excess duration | 4536.60 s | 2478.44 s |
| Imposed surplus rate | 29.36 mm/h | 75.00 mm/h |
| Underlying maximum infiltration-excess rate | 34.69 mm/h | 19.35 mm/h |
| Maximum forcing after surplus is added | 64.05 mm/h | 94.35 mm/h |
| Production solver | `APPMTH` | `HDRIVE` |
| Published peak | 47.710 mm/h | 92.714 mm/h |

The physically intuitive parts are present: higher Ksat produces slightly less
total runoff and a lower maximum infiltration-excess rate. The reversal occurs
when WEPP takes `51.64 mm` of daily saturation surplus and compresses it into
`2478 s`. The assigned contribution becomes `75.00 mm/h`, compared with only
`29.36 mm/h` in the Ksat-20 case.

This is not a resolved hydrograph for saturation-excess runoff. It is an
assumption about timing, and the assumed rate is jointly controlled by the
surplus volume and an infiltration-excess duration. Greater infiltration can
therefore produce a much larger calculated peak even as total runoff declines.

### A Second Discontinuity in Solver Selection

The Ksat mutation also changes WEPP's ponding-time sentinel `tp(2)` from zero
to `5100 s`. That switches the peak calculation from the approximate method,
`APPMTH`, to the characteristic solution, `HDRIVE`.

We forced both event inputs through each existing solver:

| Solver assignment | Ksat 20 peak | Ksat 35 peak |
| --- | ---: | ---: |
| Production selection | 47.710 mm/h | 92.714 mm/h |
| Force both through `HDRIVE` | 61.751 mm/h | 92.714 mm/h |
| Force both through `APPMTH` | 47.710 mm/h | 85.162 mm/h |

The branch switch enlarges the gap, but it is not the primary cause. The
Ksat-35 peak remains much larger under either common solver because the daily
surface surplus has already been concentrated into the shorter duration.

This gives us a specific defect statement:

> WEPP combines a daily saturation-excess volume with a subdaily
> infiltration-excess hydrograph by assigning the entire daily surplus over
> only the positive rainfall-excess intervals. Ksat controls both the surplus
> volume and the selected duration, so the construction is not monotone with
> respect to surface conductivity. A separate ponding-time sentinel can then
> switch peak solvers without a continuity constraint.

The output called effective duration does not cause this behavior. After the
peak has already been calculated, WEPP reports `EffDur = runoff / PeakRO`,
capped at one day. A collapsing `EffDur` is therefore a symptom of a large
peak, not an explanation for it.

Across all 88 original Hill 106 inversion dates, changing burned Ksat to
`35 mm/h` reduced the summed positive peak gap by approximately `70%`, from
`2138` to `633 mm/h`. That makes this daily-surplus timing mechanism a strong
candidate for much of the broader inversion, although management-dependent
roughness and routing interactions still affect individual events.

## A Separate Extreme Solver-Regime Anomaly

An undisturbed high-ET screen exposed an extreme February 15, 1986 outlier.
Increasing maximum LAI from `5` to `6` and initial canopy cover from `0.70` to
`0.90` changed runoff only from `43.47` to `44.05 mm`, but changed `PeakRO`
from `3.56` to `294.42 mm/h` an **82.7x** under roughly identical conditions.

That event followed `149.1 mm` of precipitation over five days and occurred
near saturation. It appears to cross another peak-flow response regime through
management-dependent friction and geometry. It is serious, but it is an outlier
and should not be used as the main explanation for the Topanga return-period
inversion. The broader Ksat/surface-surplus mechanism is supported across many
events; the 1986 case requires its own solver investigation.

### Cover Matrix: What “More Cover” Actually Did

We followed that result with 36 full Hill 106 runs that independently varied
initial canopy cover and paired initial interrill/rill ground cover from `0.30`
to `0.95`. Maximum LAI remained `5`; surface Ksat remained `35 mm/h`; PMET
remained at `Kcb = 1.20`; and every other input was fixed. This separates the
two cover controls that the earlier baseline-versus-dense screen had partly
confounded with LAI.

The important result is that **increasing cover does not generally increase
peak flow**. Seven of the 12 selected events change by less than 10% anywhere
in the matrix. A few events contain abrupt steps, and those steps can point in
either direction.

| Event | Original undisturbed peak | Matrix minimum | Matrix maximum | Range |
| --- | ---: | ---: | ---: | ---: |
| 1980-02-14 | 96.11 mm/h | 95.57 mm/h | 97.08 mm/h | 1.02x |
| 1982-11-30 | 109.35 mm/h | 102.90 mm/h | 112.78 mm/h | 1.10x |
| 1983-03-01 | 114.12 mm/h | 113.29 mm/h | 114.46 mm/h | 1.01x |
| 1986-02-15 | 3.56 mm/h | 3.52 mm/h | 323.03 mm/h | 91.87x |
| 1995-01-03 | 135.56 mm/h | 133.16 mm/h | 144.02 mm/h | 1.08x |
| 1995-01-10 | 115.28 mm/h | 81.84 mm/h | 115.55 mm/h | 1.41x |
| 1996-02-20 | 85.45 mm/h | 85.22 mm/h | 85.55 mm/h | 1.00x |
| 2005-01-09 | 157.62 mm/h | 97.43 mm/h | 157.87 mm/h | 1.62x |
| 2005-02-21 | 81.38 mm/h | 80.05 mm/h | 81.57 mm/h | 1.02x |
| 2019-01-16 | 77.02 mm/h | 76.77 mm/h | 77.28 mm/h | 1.01x |
| 2021-12-29 | 96.10 mm/h | 94.54 mm/h | 107.11 mm/h | 1.13x |
| 2021-12-30 | 133.03 mm/h | 108.89 mm/h | 135.92 mm/h | 1.25x |

February 1986 sharply localizes the problem. At the original canopy cover of
`0.70`, paired ground cover of `0.80` gives a `312.29 mm/h` peak, while ground
cover of `0.90` gives `3.56 mm/h`. Runoff is `43.41` versus `43.47 mm`,
effective rainfall intensity is identical at `39.12 mm/h`, and pre-event soil
water is `211.45` versus `211.10 mm`. This boundary persists at every canopy
level, so canopy cover alone cannot be the explanation. The earlier LAI-plus-
canopy screen moved a high-ground-cover input into the opposite regime,
showing that the trigger is an interaction among vegetation state,
cover-dependent hydraulics, and the peak solver—not a defensible physical
claim that denser cover creates more peak flow.

January 1995, January 2005, and December 2021 show smaller step-like changes,
including a downward step at the highest cover. These results give OpenWEPP a
tightly bracketed pair of cases (`c70_g80` and `c70_g90`) for tracing the internal
friction, geometry, and solver operands. The full matrix and response-surface
figure are in
[`hill106-cover-matrix-study.md`](hill106-cover-matrix-study.md).

## Why ET Still Matters

Finding the peak-flow defect does not make the ET problem disappear. It helps
us state the relationship correctly.

WEPP's optional PMET pathway is an empirical crop-coefficient implementation,
not a complete native-vegetation energy and ecohydrology model. In this
implementation, LAI partitions similar atmospheric demand between plant and
soil evaporation:

```text
plant share = 1 - exp(-0.45 × LAI)
soil share  =     exp(-0.45 × LAI)
```

When fire reduces LAI, much of the lost plant demand is transferred to exposed
soil evaporation rather than disappearing with the loss of living canopy,
stomatal conductance, interception storage, litter storage, and active roots.
This was especially clear in the earlier Stevens Canyon investigation. During
the 30 days before its largest inversion event, modeled burned-soil evaporation
was `12` to `25` times the undisturbed value, leaving the burned profiles drier
and reversing the expected runoff response.

Topanga adds another concern. Satellite and street-level imagery show
substantial vegetation in and near the channels, along with shrubs and tall
grass on buffered parts of the hillslopes. The WEPP discretization does not
represent that vegetation, its interception, or its access to channel and
near-channel water. A single upland point also misses much of this spatial
structure.

The vendored [2024–2025 OpenET Explorer comparison](topanga-openet-2024-2025.pdf)
shows a visible prefire-to-postfire vegetation and ET signal. At the Hill 106
point, February–December 2025 ET is `26%` below the 2016–2024 mean and NDVI is
`22%` lower, while reference ET is only `7%` lower. The decline occurs despite
greater total precipitation, although precipitation timing is a confounder.
This is qualitatively consistent with fire-driven vegetation loss.

We cannot use the absolute OpenET point values as a calibration target. They
fail a basic water-balance check: the 2016–2025 series reports `10,055 mm` of
ET against `5,527 mm` of precipitation, and the 2020 estimate is `1045 mm` ET
against approximately `313 mm` precipitation. Published OpenET evaluations
also report weak performance in western shrublands. The pre/post signal is
useful corroboration; the absolute millimeters are not credible here without
an independently demonstrated water source.

WEPP at watershed scale is still over-predicting combined runoff despite absence
of restrictive layer.

Our best interpretation is therefore that WEPP probably underpredicts actual
unburned ET and interception at the watershed scale even though the modeled
undisturbed Hill 106 profile is usually drier than the modeled burned profile.
Those statements are not contradictory:

- within the current WEPP parameterization, undisturbed loses more water than
  burned and is usually modeled drier;
- compared with the real intact watershed, both the amount and spatial pattern
  of unburned vegetation water use may still be too small; and
- missing unburned ET would keep more modeled locations near the saturation
  threshold, increasing how often the defective daily-surplus peak treatment
  becomes important.

Increasing Kcb from `1.20` to `1.40` at Hill 106 raised 2020 ET by about
`13.5 mm` and reduced combined surface-plus-lateral runoff by only about
`1.1 mm`. It changed the median peak on the selected dates by roughly `-0.3%`.
Uniform Kcb tuning is therefore not a repair for the peak defect, and it is
unlikely to capture the missing channel and vegetation structure by itself.

## What We Think the Results Mean

The return-period inversion most likely sequence is:

1. Vegetation and ET parameterization establish the antecedent water balance
   and determine how frequently profiles approach saturation.
2. During wet events, the daily water-balance calculation generates soil-water
   surface surplus.
3. WEPP assigns that daily surplus to only the positive infiltration-excess
   intervals, creating an assumed subdaily rate that can increase sharply as
   the selected duration shortens.
4. A ponding-time sentinel can also switch between two peak solvers.
5. Hillslope peaks carrying those timing assumptions are combined and routed
   through the watershed, where synchronization can amplify or attenuate the
   original problem.

This explains how paired scenarios can have similar daily flow volumes but
very different peaks, and why changing Ksat can raise a peak while reducing
runoff volume. It also explains why annual calibration alone cannot establish
that the event peaks are correct.

We would currently treat the burned annual water balance as more plausible
than the undisturbed representation, because the postfire landscape has much
less vegetation for WEPP to omit. That is still a hypothesis, not validation.
Neither scenario's peak-frequency curve should be treated as authoritative
until the saturation-surplus timing defect is corrected or bounded.

## What This Investigation Does Not Establish

- It does not establish that the F54C-R gauge is a direct calibration target
  for the modeled watershed.
- It does not show that `6.2 mm` is surface runoff; it is measured channel
  discharge.
- It does not identify a single calibrated `kslast`, Ksat, anisotropy, or Kcb
  set as the correct Topanga parameterization.
- It does not validate OpenET's absolute ET magnitude at this shrubland pixel.
- It does not show that antecedent soil water is generally greater in the
  modeled undisturbed Hill 106 case; the event statistics show the opposite.
- It does not imply that forcing every event through `HDRIVE` or `APPMTH` fixes
  the main peak defect.
- It does not use the February 1986 outlier as representative evidence for the
  return-period inversion.

## Supporting Material

The complete methods, tables, and provenance are in the
[Topanga investigation](https://github.com/rogerlew/wepppy/blob/master/docs/investigations/2026-08-07-topanga-2025-fire-peak-flow-analysis/README.md).
The most directly relevant supporting artifacts are:

- [Windows sidecar reconstruction](https://github.com/rogerlew/wepppy/blob/master/docs/investigations/2026-08-07-topanga-2025-fire-peak-flow-analysis/artifacts/windows-sidecar-ballpark.md)
- [restrictive-layer calibration study](https://github.com/rogerlew/wepppy/blob/master/docs/investigations/2026-08-07-topanga-2025-fire-peak-flow-analysis/artifacts/kslast-anisotropy-calibration-study.md)
- [return-period results](https://github.com/rogerlew/wepppy/blob/master/docs/investigations/2026-08-07-topanga-2025-fire-peak-flow-analysis/artifacts/no-restriction-kcb12-peak-return-periods.csv)
- [paired watershed event context](https://github.com/rogerlew/wepppy/blob/master/docs/investigations/2026-08-07-topanga-2025-fire-peak-flow-analysis/artifacts/no-restriction-kcb12-date-context.csv)
- [Hill 106 Ksat event comparison](https://github.com/rogerlew/wepppy/blob/master/docs/investigations/2026-08-07-topanga-2025-fire-peak-flow-analysis/artifacts/hill106-burned-ksat35-event-comparison.csv)
- [instrumented Ksat peak-flow diagnostic](https://github.com/rogerlew/wepppy/blob/master/docs/investigations/2026-08-07-topanga-2025-fire-peak-flow-analysis/artifacts/hill106-ksat-peakflow-diagnostic.md)
- [OpenWEPP solver-regime reproducer](https://github.com/rogerlew/wepppy/tree/master/docs/investigations/2026-08-07-topanga-2025-fire-peak-flow-analysis/artifacts/openwepp-hill106-effective-duration-reproducer)
- [Stevens Canyon ET investigation](https://github.com/rogerlew/wepppy/tree/master/docs/investigations/2026-08-03-stevens-canyon-peak-flow-inversion)

The key practical conclusion is that the Topanga peak inversion should not be
resolved by tuning ET or soil parameters until the peak calculation can carry
a physically timed saturation-excess source. Calibration can change how often
the defect appears, but it cannot make the imposed hydrograph timing physical.
