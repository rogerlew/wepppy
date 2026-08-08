# WEPP Peak-Flow Estimation: Long-Standing Discontinuities and Their Implementation Basis

*Version 1.5 — 2026-08-08*

*Audience: WEPP developers, hydrologists, agency staff, and other WEPP
stakeholders evaluating peak-flow results. This report is intended for readers
with an undergraduate understanding of hydrology.*

## Why this review was needed

WEPPcloud investigations have encountered implausible or difficult-to-explain
peak-flow responses for years, particularly on shrub- and grass-dominated
hillslopes.
The behavior has been hard to isolate because peak runoff responds to rainfall
timing, infiltration, antecedent soil water, vegetation, surface cover, and
hydraulic roughness at the same time. When an unusual peak appeared, there was
usually no controlled way to distinguish a real threshold response from a
parameterization problem or a numerical artifact.

The 2025 Topanga fire analysis supplied that control. A small watershed and a
single representative hillslope, Hill 106, could be rerun while changing one
or two inputs at a time. Those experiments produced repeatable cases in which
nearly unchanged event runoff was assigned radically different peak rates.
One vegetation mutation changed the peak by `82.7x`. A ground-cover matrix
bracketed a `91.9x` range. A separate Ksat experiment was instrumented inside
the model and exposed how the implementation can make greater infiltration
produce a larger peak even while total runoff decreases.

Topanga is therefore the worked example, not the scope of the concern. This
report uses it to illustrate particular shortcomings in WEPP peak-flow
estimation that are present in both the public September 2024 Windows WEPP
source and the WEPP-Forest lineage. It compares those implementations with the
official WEPP technical documentation, explains the calculation in hydrologic
terms, and separates what has been demonstrated from what still requires
investigation.

## Key findings

The official documentation describes a continuous-simulation peak estimate
derived from kinematic-wave routing. It assumes that runoff volume, the
duration of rainfall excess, and the maximum and average excess rates describe
one coherent subdaily forcing. The documented piecewise equations are intended
to join at calculated boundaries; a two-order-of-magnitude jump is not a
documented hydrologic regime change (Stone et al., 1995, §§4.4.2.1–4.4.2.2).

Both Windows WEPP 2024 and WEPP-Forest add water returned from a full soil
profile to the peak-flow calculation in a way that does not preserve when that
water reached the surface. The model collects the returned water as a daily
depth, `surdra`, divides it by the duration of intervals that already have
positive infiltration excess, and adds the resulting constant rate only to
those intervals. This is also what reaches the peak calculation when the
hourly water-balance option is enabled: the hourly surface-return values are
first summed into the daily `surdra` value. Ksat can change both the amount of
returned water and the selected duration, so a larger daily depth can be
compressed into a shorter period and create a larger calculated peak.

The event path also switches between two peak algorithms according to whether
the stored ponding time, `tp(2)`, is exactly zero or positive. The value zero
has two meanings: it can represent zero time, and it is also used as a special
flag telling the code to use the approximate method. A positive value tells
the code to use characteristic routing. There is no continuity check between
the returned peaks at that boundary. This switch can enlarge a discontinuity,
although the instrumented Topanga Ksat experiment shows that it is not the
primary cause in that case.

Finally, the reported effective duration is calculated after the peak as
runoff divided by peak, with a one-day cap. A very short `EffDur` is therefore
a consequence of a large calculated peak. It cannot be offered as independent
evidence that the physical runoff pulse became shorter.

## Why runoff timing matters

A runoff hydrograph is discharge through time. Event runoff is the area under
that curve; peak runoff is its maximum height. The same runoff volume can have
a low peak when spread over many hours or a high peak when concentrated into a
short pulse. A credible peak estimate therefore requires both the amount of
surface water and a defensible account of when that water becomes available
and moves downslope.

Surface saturated hydraulic conductivity, or Ksat, controls how readily water
enters saturated surface soil. All else equal, increasing Ksat permits more
infiltration and tends to reduce Hortonian runoff, which occurs when rainfall
intensity exceeds infiltration capacity. Surface cover generally increases
hydraulic resistance and tends to slow and spread shallow overland flow.

Antecedent saturation complicates these relationships. Water that infiltrates
an already full soil profile can be returned to the surface. That does not,
however, determine the returned water's subdaily timing. A daily water-balance
surplus cannot be converted into a peak rate until the model assigns it a time
distribution or routes it from a resolved source.

## What the official WEPP documentation describes

### The intended role of the peak estimate

WEPP was designed principally as an erosion-prediction model for conservation
and land-management analysis. Chapter 4 states that surface hydrology supplies
the erosion component with rainfall-excess duration, rainfall intensity during
that period, runoff volume, and peak discharge (Stone et al., 1995, §4.1,
printed p. 4.1). The erosion calculation then treats the peak as a steady
discharge acting for an equivalent duration.

The peak also enters watershed calculations, so its relevance is not limited
to hillslope erosion. Nevertheless, its original computational role explains
why a continuous event is reduced to runoff, peak, intensity, and duration
rather than retained as a complete hydrograph that can be compared directly
with observations.

### The documented routing methods

Chapter 4 describes two methods (Stone et al., 1995, §4.4):

1. A semi-analytical solution of the kinematic-wave equations routes a
   rainfall-excess time series in single-event mode.
2. An approximate kinematic-wave method estimates the peak for most events in
   continuous-simulation mode.

The semi-analytical method combines continuity with the depth-discharge
relation

\[
q = \alpha h^m,
\]

where (q) is discharge per unit width, (h) is flow depth, (\alpha) is a
hydraulic coefficient, and (m) is the depth-discharge exponent (Eqs.
[4.4.1]–[4.4.7]). The documentation acknowledges flat-topped partial-
equilibrium hydrographs and an infinite mathematical recession. The
implementation stops routing after 95% of the volume has passed or discharge
falls to 10% of peak (printed pp. 4.5–4.6).

The continuous-simulation approximation uses total rainfall-excess depth
(V_t), duration (D_v), average excess rate (v_a = V_t/D_v), maximum
excess rate (v_p), flow length, and (\alpha). These form dimensionless
time, intensity, and peak ratios (t^*), (v^*), and (q^*) (Eqs.
[4.4.19]–[4.4.22]). Three piecewise equations estimate (q^*) for variable
rainfall excess (Eqs. [4.4.23]–[4.4.25]), with their intersection calculated
explicitly by Eq. [4.4.26]. The published branches are intended to meet at
their boundaries.

### The approximation's tested domain

The approximation was derived over the range in Chapter 4 Table 4.4.1:

| Quantity | Minimum | Maximum |
| --- | ---: | ---: |
| Dimensionless time, (t^*) | 0.09 | 10.0 |
| Mean-to-maximum excess ratio, (v^*) | 0.08 | 1.0 |
| Dimensionless peak ratio, (q^*) | 0.07 | 8.0 |

The reported average errors relative to kinematic routing were 1%, 10%, and
5% for the three equations, or 6.6% combined. Figure 4.4.4 shows close
comparison on a rainfall-disaggregation dataset except for one event. The
documentation does not specify warnings, clamps, or an alternate method
outside the Table 4.4.1 domain. It also does not report continuity or
monotonicity tests under small changes in Ksat, vegetation, or cover.

### Effective duration is a volume-equivalence calculation

Chapter 4 defines effective duration as

\[
D_e = \frac{Q_v}{q_p},
\]

where (Q_v) is runoff depth and (q_p) is peak runoff rate (Eq. [4.4.30],
printed p. 4.12). This creates a rectangle whose height is peak discharge and
whose area equals event runoff. It allows the erosion component to use steady
flow at the peak without losing the event volume.

It is not an independently routed rainfall-excess duration, hydrograph
duration, or time to peak. If the calculated peak changes from `3.56` to
`294.42 mm/h` while runoff remains near `44 mm`, the reported duration must
collapse from roughly 12 hours to minutes by arithmetic alone.

### The documented limitations are substantial

Chapter 4 §4.6 says surface hydrology should perform best for large events on
a single overland flow element (OFE) and worst for medium events on multiple
OFEs. It states that WEPP does not explicitly represent variable contributing
areas or return flow; rainfall excess is calculated before routing; routed
water and infiltration do not fully interact; and the peak approximation has
more error for multi-peaked hydrographs.

Chapter 6 reports that runoff volumes compared more favorably with observations
than peak rates in a drainage evaluation. In one dataset, peak runoff was
consistently overpredicted. Because hydraulic roughness had not been measured,
the authors concluded that validation of runoff routing—and therefore peak-
runoff validity—remained undetermined (Savabi et al., 1995, §6.3.3, printed
p. 6.9).

Those cautions argue against overconfidence in peak estimates. They do not
describe or justify the discontinuous responses demonstrated below.

## A shared implementation in Windows WEPP and WEPP-Forest

### Source comparison

The public Daily Erosion Project repository contains the source imported as
WEPP 2024 on September 30, 2024. The reviewed checkout was DEP commit
`e2609d9e67757f667c603e01048e8f9890ef657c`; its history records the
`src/wepp20240930` tree as a verbatim import at commit
`5e746b578e8999044727fc6a4a50302ccf605bae`. The local audit path was
`/workdir/dep/src/wepp20240930`.

The WEPP-Forest comparison used commit
`2f65506d239b449bbb73c6820ff9cb949fa55158`. File hashes and direct diffs show
the following relationship:

| Routine or state file | DEP Windows WEPP versus WEPP-Forest | Relevance |
| --- | --- | --- |
| `reid.for` | Byte-identical | Selects positive-excess intervals and sums their duration |
| `appmth.for` | Byte-identical | Implements the dimensionless peak approximation |
| `hdrive.for` | Byte-identical | Routes the characteristic hydrograph |
| `grna.for` | Byte-identical | Builds rainfall excess and initializes `tp(2)` |
| `chydrol.inc` | Byte-identical | Defines shared runoff, peak, duration, and surplus state |
| `irs.for` | Same peak/surplus logic; other edits differ | Inserts daily surplus, selects solver, derives `EffDur` |
| `watbal.for` | Same surface-surplus concept; WEPP-Forest later refactored other water-balance paths | Produces `surdra` and adds it to daily runoff |
| `watbal_hourly.for` | Same hourly aggregation; WEPP-Forest later refactored other water-balance paths | Sums hourly `ui_scrunf` into daily `surdra` |

The byte-identical SHA-256 values are recorded in
[Software and source provenance](#software-and-source-provenance). The
WEPP-Forest `irs.for` differences include a replacement water-balance call,
an upslope-runoff guard, and later OFE output mapping. They do not remove the
daily-surplus insertion, `tp(2)` solver selection, or effective-duration
calculation discussed here.

The Topanga runtime instrumentation was performed with WEPP-Forest. The public
Windows source comparison is static: it establishes that the same peak-flow
mechanics are present, not that every Windows compiler and executable has been
run on the Topanga fixtures.

### The source records the unresolved timing problem

The public Windows `watbal.for` contains a 1993 comment immediately before the
surface-drainage code. It says surface drainage should be added back to current-
day runoff, but notes that runoff had already been routed and erosion already
computed. It proposes moving the water-balance call into the infiltration-
runoff sequence and somehow adding the water as an input before rerunning those
calculations ([DEP `watbal.for`, lines 780–798](#windows-wepp-2024-implementation-references)).

Later changes did move the water-balance call into `IRS` and add `surdra` to
the routing input. The remaining problem is temporal: the water balance returns
a daily depth, not a subdaily hydrograph. The implementation supplies timing by
assigning that depth to intervals selected by infiltration excess.

This code history is important. The defect is not that developers ignored
surface drainage. The source explicitly recognized a difficult coupling and
implemented a mass-conserving way to return the water. What remained
unresolved was whether the assigned timing produces a defensible peak.

## How the implemented peak calculation works

### Rainfall excess first defines a duration

The infiltration routines create a subdaily rainfall-excess rate for each
climate interval. `REID` defines `durre` as the sum of only the intervals whose
rainfall excess is positive. Zero-excess gaps between bursts are excluded:

```text
durre = sum(interval duration where rainfall_excess > 0)
```

This behavior is identical in public Windows WEPP and WEPP-Forest
([DEP `reid.for`, lines 48–72](#windows-wepp-2024-implementation-references);
[WEPP-Forest `reid.for`, lines 48–72](#wepp-forest-implementation-references)).

For the original infiltration-excess time series, this is a meaningful
duration. It does not establish the timing of surface water returned later by
the daily soil-water balance.

### The water balance returns water from a full soil profile

`IRS` calls the water-balance routine during the event calculation and then
reads back revised runoff and `surdra`. In daily mode, `surdra` is water above
the permitted surface-layer storage. That depth is removed from soil storage
and added to daily runoff ([DEP `watbal.for`, lines
794–820](#windows-wepp-2024-implementation-references)).

Hourly mode does not resolve this problem for the peak calculation. The main
water-balance routine dispatches to `watbal_hourly` when the hourly option is
enabled. That routine calculates surface return in an hourly array,
`ui_scrunf(ii)`, but immediately sums the hourly values into the same daily
`surdra` variable. After the hourly routine returns, `IRS` uses `surdra`, not
the hourly array, to construct the input to the peak solver. This sequence is
present in both Windows WEPP 2024 and WEPP-Forest
([DEP `watbal.for`, lines 236–246 and `watbal_hourly.for`, lines 840–880](#windows-wepp-2024-implementation-references);
[WEPP-Forest `watbal.for`, lines 268–278 and `watbal_hourly.for`, lines
936–990](#wepp-forest-implementation-references)).

At this point the peak calculation has two representations:

- a subdaily series of infiltration-excess rates; and
- a daily surface-surplus depth without its original within-day timing.

### The daily surplus is compressed into selected intervals

When both `surdra` and existing rainfall excess are positive, `IRS` divides
the entire daily surplus by `durre`. It adds that constant rate only to
intervals whose existing excess rate is already positive:

```text
surplus_rate = daily_surface_surplus / positive_excess_duration

for each subdaily interval:
    if existing_excess_rate > 0:
        solver_lateral_inflow += surplus_rate
```

The Windows implementation is at [DEP `irs.for`, lines
539–628](#windows-wepp-2024-implementation-references); the WEPP-Forest
implementation is at [WEPP-Forest `irs.for`, lines
545–635](#wepp-forest-implementation-references).

The operation gets the daily water amount right: multiplying the added rate by
the selected duration recovers the original surplus depth. It does not get the
timing from the water balance. Instead, it places all of that water into the
parts of the storm that already produced infiltration-excess runoff.

Consider a simplified example in which rainfall exceeds infiltration capacity
during two short bursts totaling two hours. Suppose the water balance also
reports 20 mm returned to the surface during the day. The code adds 10 mm/h to
both hours, regardless of whether that return actually occurred during those
hours, between the bursts, or after the rain. If a parameter change shortens
the selected rainfall-excess duration to one hour, the same 20 mm is assigned
at 20 mm/h. The water volume still balances, but the constructed peak forcing
doubles. These numbers are illustrative, not a Topanga model result.

This distinction is important because a hydrograph depends on both volume and
timing. Physically routing the returned water would retain when it reached the
surface and then move it downslope through surface storage and hydraulic
resistance. The implemented calculation instead chooses its timing after the
water balance is complete, using the timing of Hortonian rainfall excess—a
different runoff process. In hourly mode, it does this even though the water
balance had already calculated hourly surface-return values. Conserving a
daily volume therefore does not guarantee a physically credible peak.

Ksat can alter both terms in the imposed rate:

```text
larger daily surface surplus
             +
shorter positive-excess duration
             ↓
larger imposed subdaily inflow rate
             ↓
larger calculated peak
```

Thus greater infiltration can produce a larger peak even while event runoff
decreases. This is the mechanism demonstrated in the instrumented Ksat case.

When surplus exists without a positive rainfall-excess duration, another
branch spreads the water across a storm-derived duration, an upslope duration,
or a one-day fallback. It sets `tp(2) = 0` so the approximate solver is used.
In plain terms, the code must invent a time window because no positive-excess
window exists. It tries the storm duration, then an upslope-flow duration, and
finally 24 hours. None of those choices records when the soil actually
returned the water. The choice matters directly: putting the same depth into
a shorter window creates a higher input rate and can create a higher peak.

### An exactly zero ponding time switches the peak algorithm

For the reviewed continuous-event path, `IRS` stores a ponding-time value in
`tp(2)` and makes this selection:

```text
if tp(2) > 0:
    use HDRIVE characteristic routing
else:
    use APPMTH approximation
```

The public and WEPP-Forest implementations are cited under
[Implementation references](#implementation-references). `GRNA` initializes
`tp(2)` to exactly zero. The code then treats zero as a special instruction:
use `APPMTH`. Any positive value means use `HDRIVE`. This use of a particular
value as both data and an instruction is sometimes called a *sentinel value*.
A small change that moves the stored value across zero therefore changes the
entire peak algorithm rather than merely making a small adjustment within one
algorithm. No check requires the two methods to give similar answers at that
boundary, and there is no gradual transition between them.

`APPMTH` implements the Chapter 4 approximation. It calculates
`vave = runoff/effdrr`, forms (t^*) and (v^*), selects a piecewise peak
factor, and returns `peakro = vave*qpstar`. `HDRIVE` instead routes the
lateral-inflow step series using characteristics and samples the hydrograph at
the supplied breakpoints and then at 60-second increments.

### Effective duration is calculated last

After either method returns a peak, `IRS` calculates

```text
effdrn = runoff / peakro
effdrn = min(effdrn, 86400 seconds)
```

This implements the volume-equivalent purpose of Chapter 4 Eq. [4.4.30]. It
does not diagnose why a physical hydrograph was short. Any peak discontinuity
automatically creates an inverse duration discontinuity.

## Topanga as a controlled example

### Overview of the evidence

All Topanga values in this report were produced with the pinned
`wepp_260803` executable. The experiments address different questions and
should not be treated as interchangeable demonstrations of one cause.

| Experiment | Controlled change | Peak response | Runoff response | What it establishes |
| --- | --- | ---: | ---: | --- |
| 1980 burned Ksat | Surface Ksat 20 → 35 mm/h | 47.71 → 92.71 mm/h (`1.94x`) | 60.12 → 58.63 mm | Instrumented causal trace of surplus compression; solver switch is secondary |
| 1986 canopy screen | Maximum LAI 5 → 6 and initial canopy 0.70 → 0.90 | 3.56 → 294.42 mm/h (`82.7x`) | 43.47 → 44.05 mm | Severe vegetation-to-peak discontinuity; exact internal transition unresolved |
| 1986 cover bracket | Paired ground cover 0.80 → 0.90 at canopy 0.70 | 312.29 → 3.56 mm/h (`87.7x` decrease) | 43.41 → 43.47 mm | Compact ground-cover boundary for replay |
| 1986 full matrix | 36 canopy/ground-cover combinations | 3.516–323.029 mm/h (`91.9x`) | 42.834–44.115 mm | Two peak regimes across a controlled response surface |
| 2005 cover step | Paired ground cover 0.80 → 0.90 at canopy 0.70 | 97.74 → 157.62 mm/h (`1.61x`) | 71.186 → 71.166 mm | A secondary discontinuity on another date |

### The instrumented Ksat case identifies a cause

In this report, *instrumented* means that we compiled a temporary diagnostic
version of WEPP with additional print statements inside the model. Those
statements recorded intermediate values that ordinary WEPP output does not
show. They did not change the water-balance or peak-flow equations. This let
us observe the calculation between the input file and the published runoff
and peak values instead of inferring the cause from final output alone.

The diagnostic used WEPP-Forest source commit
`2f65506d239b449bbb73c6820ff9cb949fa55158` in an isolated worktree. Before
adding any diagnostics, we compiled the unmodified source and verified that it
reproduced the established Hill 106 event result exactly. Keeping this work in
a separate worktree prevented the temporary logging and solver tests from
altering the baseline source tree.

#### Experimental design

We selected February 14, 1980 because an earlier controlled screen had exposed
a counterintuitive response: increasing surface Ksat raised the peak even
though it reduced runoff. The paired runs used the burned Hill 106 climate,
slope, management, soil profile, and simulation history. The only intended
input change was first-horizon Ksat, from `20` to `35 mm/h`. The model was run
through the complete preceding climate sequence rather than initialized only
for the selected storm, so each event inherited the antecedent state generated
by its own simulation.

The resulting pre-event profile-water values were `211.87` and `211.85 mm`.
That near equality does not prove that every internal soil state was
identical, but it shows that a large difference in total antecedent water was
not responsible for the peak reversal. Higher Ksat slightly reduced final
runoff, from `60.122` to `58.630 mm`, while nearly doubling the reported peak.

#### Values recorded inside WEPP

We added diagnostic output at the handoff between the water balance and the
peak routines. For the selected hillslope and date, it recorded:

- runoff before publication;
- `surdra`, the daily surface-return depth produced by the water balance, and
  `surpls`, the corresponding depth passed into the peak calculation;
- `drlast`, the total duration of intervals with positive infiltration
  excess;
- `remax`, the maximum infiltration-excess rate before adding the returned
  water;
- the maximum value in the peak solver's lateral-inflow series after adding
  the returned water;
- `tp(2)`, the stored ponding time used to choose the peak method;
- the selected peak method; and
- the final `PeakRO` value.

Recording values both before and after the `surdra` insertion was essential.
It separated the infiltration response to Ksat from the later operation that
constructed the peak solver's forcing.

| Recorded operand | Ksat 20 | Ksat 35 |
| --- | ---: | ---: |
| Final surface-runoff volume | 60.122 mm | 58.630 mm |
| Daily surface return, `surpls` | 36.999 mm | 51.637 mm |
| Positive-excess duration, `drlast` | 4,536.60 s | 2,478.44 s |
| Imposed return rate, `surpls/drlast` | 29.36 mm/h | 75.00 mm/h |
| Maximum excess before return insertion, `remax` | 34.69 mm/h | 19.35 mm/h |
| Maximum forcing after return insertion | 64.05 mm/h | 94.35 mm/h |
| Stored ponding time, `tp(2)` | 0 s | 5,100 s |
| Selected peak method | `APPMTH` | `HDRIVE` |
| Published `PeakRO` | 47.710 mm/h | 92.714 mm/h |

The higher-Ksat case behaved intuitively up to the water-balance handoff: it
had less runoff and a lower maximum infiltration-excess rate. The reversal
appeared when WEPP divided a larger daily surface-return depth by a duration
that was 45% shorter. This raised the assigned return rate from `29.36` to
`75.00 mm/h` and raised the maximum forcing supplied to the peak solver.

#### Separating the timing defect from the solver switch

The observational trace also showed that Ksat changed `tp(2)` from exactly
zero to positive, causing WEPP to use different peak methods in the paired
runs. We therefore made separate counterfactual builds that overrode only this
method selection: one sent both already-constructed event inputs through
`HDRIVE`, and another sent both through `APPMTH`. These were diagnostic tests,
not proposed model configurations.

| Solver assignment | Ksat 20 peak | Ksat 35 peak |
| --- | ---: | ---: |
| Normal WEPP selection | 47.710 mm/h (`APPMTH`) | 92.714 mm/h (`HDRIVE`) |
| Force both through `HDRIVE` | 61.751 mm/h | 92.714 mm/h |
| Force both through `APPMTH` | 47.710 mm/h | 85.162 mm/h |

The method switch enlarged the difference, but it did not create the reversal.
Under either common method, the higher-Ksat case retained the much larger peak
because the daily surface return had already been concentrated into its
shorter positive-excess duration. The experiment therefore identifies the
`surdra` timing construction as the primary cause for this event and the
zero/positive `tp(2)` method switch as a secondary discontinuity.

### The 82.7× canopy case establishes an extreme discontinuity

The February 15, 1986 experiment compared two undisturbed,
no-restrictive-layer Hill 106 runs. Climate, soil, surface Ksat, PMET settings,
slope, and ground cover were fixed. The management mutation increased maximum
LAI from `5` to `6` and initial canopy cover from `0.70` to `0.90`. Those
inputs changed the evolving vegetation and hydraulic state, including
event-date LAI, canopy height, biomass, friction, and rill width.

The event followed `149.1 mm` of precipitation during the preceding five days
and received another `64.7 mm`. Both modeled surface zones were nearly
saturated.

| February 15, 1986 metric | Baseline | Dense canopy |
| --- | ---: | ---: |
| Event precipitation | 64.7 mm | 64.7 mm |
| Pre-event total soil water | 211.10 mm | 206.02 mm |
| Surface saturation fraction | 0.99 | 0.98 |
| Effective rainfall intensity | 39.12 mm/h | 39.12 mm/h |
| Runoff | 43.47 mm | 44.05 mm |
| `PeakRO` | 3.56 mm/h | 294.42 mm/h |
| Reported `EffDur` | 12.20 h | 0.150 h |

Runoff changed by `0.58 mm`, or 1.3%, while peak changed by `82.7x`. The dense
case was slightly drier in the reported antecedent measures. The identical
effective intensity and near-identical runoff do not explain the peak ratio.
The dense-canopy `PeakRO` of `294.42 mm/h` is `7.5x` the reported effective
rainfall intensity for a storm that delivered `64.7 mm` in total. In WEPP's
rectangular-equivalent representation, nearly all `44.05 mm` of runoff is
therefore concentrated at the peak rate for only nine minutes. The baseline
run assigns essentially the same runoff from the same storm across 12.2 hours.
The `EffDur` collapse follows arithmetically from the peak jump; it is not an
independent explanation for that contrast.

This experiment establishes a severe discontinuity between management state
and peak output. It does not yet identify the immediate internal branch. The
frozen pair is intended for an operand-complete replay of surface surplus,
friction, `ealpha`, `drlast`, `remax`, `tp(2)`, method selection, and the full
`HDRIVE` forcing series.

### The cover matrix brackets the 1986 boundary

A 6-by-6 experiment varied initial canopy cover and paired initial interrill
and rill ground cover. Maximum LAI, Ksat, climate, PMET, slope, soil, and all
other inputs were held fixed. Across 36 runs, the February 1986 peak ranged
from `3.516` to `323.029 mm/h`, while runoff remained between `42.834` and
`44.115 mm`.

At initial canopy cover `0.70`, changing paired ground cover from `0.80` to
`0.90` produced:

| Metric | Ground cover 0.80 | Ground cover 0.90 |
| --- | ---: | ---: |
| Runoff | 43.41 mm | 43.47 mm |
| Effective rainfall intensity | 39.12 mm/h | 39.12 mm/h |
| Pre-event soil water | 211.45 mm | 211.10 mm |
| `PeakRO` | 312.29 mm/h | 3.56 mm/h |
| Reported `EffDur` | 0.139 h | 12.20 h |

The two regimes persist at every canopy level tested. Ground cover `0.80`
produces peaks of approximately `296–323 mm/h`; ground cover `0.90` produces
approximately `3.52–3.61 mm/h`. This is not a smooth hydraulic-resistance
response. It supplies a tight, reproducible boundary for tracing the solver.

The direction differs from the earlier dense-canopy experiment because that
experiment also changed maximum LAI and therefore the evolving plant and
hydraulic state. Together, the studies show a nonlinear interaction among
vegetation, cover-dependent hydraulics, antecedent state, and peak logic. They
do not support a general claim that denser canopy increases peaks or that a
0.10 increase in ground cover physically reduces a peak by two orders of
magnitude.

### Smaller steps occur on other dates

Seven of twelve selected events changed by less than 10% across the complete
cover matrix. The remaining events show that the response is event specific
and that the 1986 case is an extreme member of a broader pattern.

| Event | Peak range across matrix | Maximum/minimum | Interpretation |
| --- | ---: | ---: | --- |
| 1982-11-30 | 102.90–112.78 mm/h | `1.10x` | Runoff also changes; less diagnostic |
| 1995-01-10 | 81.84–115.55 mm/h | `1.41x` | Step-like increase across cover thresholds |
| 2005-01-09 | 97.43–157.87 mm/h | `1.62x` | Strong secondary counterexample |
| 2021-12-29 | 94.54–107.11 mm/h | `1.13x` | Moderate response |
| 2021-12-30 | 108.89–135.92 mm/h | `1.25x` | Opposite-direction step at high cover |

For January 9, 2005 at canopy cover `0.70`, increasing ground cover from
`0.80` to `0.90` changes runoff from `71.186` to `71.166 mm` and pre-event
soil water from `213.21` to `213.20 mm`, yet raises `PeakRO` from `97.74` to
`157.62 mm/h`. Effective intensity rises from `38.27` to `41.15 mm/h`, while
derived `EffDur` falls from `0.728` to `0.451 h`.

These secondary cases have not been instrumented internally and may not share
one exact cause. They establish that cover-related peak steps recur and should
be included in regression testing rather than dismissed as one anomalous 1986
storm.

## What the evidence supports

The following conclusions are supported directly by documentation, source, or
controlled execution:

1. Continuous WEPP peak flow is an approximation of kinematic-wave routing,
   and effective duration is runoff divided by peak for steady-state erosion
   calculations.
2. Both public Windows WEPP 2024 and WEPP-Forest assign a daily surface-surplus
   depth to subdaily intervals by dividing it by the duration of already-
   positive rainfall excess.
3. In the instrumented 1980 Ksat case, this operation changes the imposed
   surplus rate from `29.36` to `75.00 mm/h` and produces a larger peak despite
   lower runoff and lower original maximum rainfall excess.
4. Both implementations use a `tp(2)` zero/nonzero boundary to select
   `APPMTH` or `HDRIVE` in the reviewed path, without a continuity check.
5. Controlled Topanga vegetation and cover mutations produce 82.7–91.9× peak
   ranges with only small runoff and antecedent-state differences.
6. Smaller cover-related peak steps recur on other dates.

The following questions remain open:

- The exact branch responsible for the 1986 cover boundary has not been
  traced.
- The current evidence does not show that every cover-related step is caused
  by surface-surplus compression or the `tp(2)` switch.
- Neither side of the extreme 1986 boundary has been established as the
  physically correct peak.
- Similar runoff volume and antecedent storage do not require identical
  hydrographs. The concern is the discontinuous response and the implemented
  timing assumption, not volume similarity alone.
- The Windows source shares the mechanics statically, but the Topanga fixtures
  have not yet been instrumented in the Windows executable.
- The separate Topanga finding that undisturbed vegetation and ET are probably
  underrepresented remains important because it affects how often the soil
  approaches saturation. It does not validate the imposed timing of `surdra`.

## Why this could remain unresolved for years

The implementation conserves the inserted surplus volume, and `EffDur` adjusts
automatically to the calculated peak. Annual runoff totals and erosion
bookkeeping can therefore remain internally plausible while event timing is
not. A large peak produces a short duration rather than an obvious mass-balance
failure.

The original evaluation compared peak approximations across collections of
events. It did not report the small-perturbation tests that reveal these
problems: whether increasing Ksat can raise peak while lowering runoff, whether
small cover changes cause steps, or whether the two solvers agree as `tp(2)`
crosses zero.

The peak approximation also predates source changes dated 2003–2004 that added
and adjusted the surface-surplus path, as well as 2009 comments about the
difficulty of water-balance/global-state sequencing. The cross-timescale
coupling was not part of the 1995 approximation's reported calibration.

Finally, vegetation, roughness, infiltration, and antecedent moisture are all
uncertain on shrub and grass hillslopes. Without a controlled mutation, an
implausible peak can be attributed to parameterization. The Topanga matrix is
valuable because it changes that situation: it locates narrow boundaries while
holding almost everything else fixed.

## Reproducibility

The Topanga evidence is preserved in the following artifacts:

- [instrumented Ksat diagnostic](hill106-ksat-peakflow-diagnostic.md);
- [Ksat event comparison data](hill106-burned-ksat35-event-comparison.csv);
- [canopy high-ET screen summary](hill106-high-et-screen-summary.csv);
- [cover-matrix study](hill106-cover-matrix-study.md);
- [cover-matrix event data](hill106-cover-matrix-selected-events.csv);
- [cover-matrix summary](hill106-cover-matrix-summary.csv);
- [cover-matrix response figure](hill106-cover-matrix-selected-events.svg); and
- [frozen 1986 baseline and dense-canopy decks](openwepp-hill106-effective-duration-reproducer/README.md).

The [Topanga investigation README](../README.md) provides the larger watershed,
ET, calibration, and return-period context.

## Software and source provenance

### Windows WEPP 2024

- Repository: [dailyerosion/dep](https://github.com/dailyerosion/dep)
- Reviewed commit: `e2609d9e67757f667c603e01048e8f9890ef657c`
- Verbatim WEPP 2024 import commit:
  `5e746b578e8999044727fc6a4a50302ccf605bae`
- Source tree: `src/wepp20240930`

### WEPP-Forest

- Repository: `wepp-in-the-woods/wepp-forest` (access restricted)
- Reviewed commit: `2f65506d239b449bbb73c6820ff9cb949fa55158`
- Instrumented executable: `wepp_260803`
- Executable SHA-256:
  `4a5158e224c175ac06c760f1006cc19f7691a9bd28911d94788af2622ba178a5`

### Byte-identical implementation files

| File | SHA-256 in both reviewed trees |
| --- | --- |
| `reid.for` | `cd6a90311da8d7220e3ddff4375a7a6dd011328e962f6824b025cbacc60bfca0` |
| `appmth.for` | `a9fc9839b343f574d6a1b4edd09da4d66609e7cd9c6740016c9f630823afba07` |
| `hdrive.for` | `c4954e16363dd5ece9d5dfbf7d8799bf082718ff21fab9d5ddfaf573c9d3e0c6` |
| `grna.for` | `59cd0c46c61cbc3f314457eaa2cdfe2cc1350947b30f3b95b3006d6675d3e842` |
| `chydrol.inc` | `856fca5a3971ba49836b4150c1ff32d296e1da99e5d53f60b234e3feb4c10a63` |

## Implementation references

### Windows WEPP 2024 implementation references

These links are public and identify the reviewed DEP commit:

- [`WATBAL`: original timing-problem comment and surface surplus](https://github.com/dailyerosion/dep/blob/e2609d9e67757f667c603e01048e8f9890ef657c/src/wepp20240930/watbal.for#L780-L820)
- [`WATBAL`: dispatch to hourly water balance](https://github.com/dailyerosion/dep/blob/e2609d9e67757f667c603e01048e8f9890ef657c/src/wepp20240930/watbal.for#L236-L246)
- [`WATBAL_HOURLY`: hourly surface return summed into daily `surdra`](https://github.com/dailyerosion/dep/blob/e2609d9e67757f667c603e01048e8f9890ef657c/src/wepp20240930/watbal_hourly.for#L840-L880)
- [`REID`: positive-excess duration](https://github.com/dailyerosion/dep/blob/e2609d9e67757f667c603e01048e8f9890ef657c/src/wepp20240930/reid.for#L48-L72)
- [`IRS`: daily water-balance call and surface-surplus insertion](https://github.com/dailyerosion/dep/blob/e2609d9e67757f667c603e01048e8f9890ef657c/src/wepp20240930/irs.for#L539-L628)
- [`IRS`: solver selection](https://github.com/dailyerosion/dep/blob/e2609d9e67757f667c603e01048e8f9890ef657c/src/wepp20240930/irs.for#L639-L700)
- [`IRS`: effective-duration calculation](https://github.com/dailyerosion/dep/blob/e2609d9e67757f667c603e01048e8f9890ef657c/src/wepp20240930/irs.for#L718-L732)
- [`APPMTH`: dimensionless approximation](https://github.com/dailyerosion/dep/blob/e2609d9e67757f667c603e01048e8f9890ef657c/src/wepp20240930/appmth.for#L78-L132)
- [`HDRIVE`: characteristic hydrograph calculation](https://github.com/dailyerosion/dep/blob/e2609d9e67757f667c603e01048e8f9890ef657c/src/wepp20240930/hdrive.for#L91-L154)
- [`GRNA`: `tp(2)` initialization and excess construction](https://github.com/dailyerosion/dep/blob/e2609d9e67757f667c603e01048e8f9890ef657c/src/wepp20240930/grna.for#L282-L306)

### WEPP-Forest implementation references

These links require repository access and identify the reviewed commit:

- [`REID`: positive-excess duration](https://github.com/wepp-in-the-woods/wepp-forest/blob/2f65506d239b449bbb73c6820ff9cb949fa55158/src/reid.for#L48-L72)
- [`IRS`: daily water-balance call and surface-surplus insertion](https://github.com/wepp-in-the-woods/wepp-forest/blob/2f65506d239b449bbb73c6820ff9cb949fa55158/src/irs.for#L545-L635)
- [`IRS`: solver selection](https://github.com/wepp-in-the-woods/wepp-forest/blob/2f65506d239b449bbb73c6820ff9cb949fa55158/src/irs.for#L646-L706)
- [`IRS`: effective-duration calculation](https://github.com/wepp-in-the-woods/wepp-forest/blob/2f65506d239b449bbb73c6820ff9cb949fa55158/src/irs.for#L725-L739)
- [`APPMTH`: dimensionless approximation](https://github.com/wepp-in-the-woods/wepp-forest/blob/2f65506d239b449bbb73c6820ff9cb949fa55158/src/appmth.for#L78-L132)
- [`HDRIVE`: characteristic hydrograph calculation](https://github.com/wepp-in-the-woods/wepp-forest/blob/2f65506d239b449bbb73c6820ff9cb949fa55158/src/hdrive.for#L91-L154)
- [`GRNA`: `tp(2)` initialization and excess construction](https://github.com/wepp-in-the-woods/wepp-forest/blob/2f65506d239b449bbb73c6820ff9cb949fa55158/src/grna.for#L282-L306)
- [`WATBAL`: surface surplus added to runoff](https://github.com/wepp-in-the-woods/wepp-forest/blob/2f65506d239b449bbb73c6820ff9cb949fa55158/src/watbal.for#L845-L876)
- [`WATBAL`: dispatch to hourly water balance](https://github.com/wepp-in-the-woods/wepp-forest/blob/2f65506d239b449bbb73c6820ff9cb949fa55158/src/watbal.for#L268-L278)
- [`WATBAL_HOURLY`: hourly surface return summed into daily `surdra`](https://github.com/wepp-in-the-woods/wepp-forest/blob/2f65506d239b449bbb73c6820ff9cb949fa55158/src/watbal_hourly.for#L936-L990)

## References

Flanagan, D. C., Ascough, J. C., II, Nicks, A. D., Nearing, M. A., & Laflen,
J. M. (1995). Overview of the WEPP erosion prediction model. In D. C. Flanagan
and M. A. Nearing (Eds.), *USDA Water Erosion Prediction Project: Hillslope
profile and watershed model documentation* (NSERL Report No. 10, Chapter 1).
USDA-ARS National Soil Erosion Research Laboratory.
[Official PDF](https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/chap1.pdf).

Savabi, M. R., Skaggs, R. W., & Onstad, C. A. (1995). Subsurface hydrology. In
D. C. Flanagan and M. A. Nearing (Eds.), *USDA Water Erosion Prediction
Project: Hillslope profile and watershed model documentation* (NSERL Report
No. 10, Chapter 6). USDA-ARS National Soil Erosion Research Laboratory.
[Official PDF](https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/chap6.pdf).

Stone, J. J., Lane, L. J., Shirley, E. D., & Hernandez, M. (1995). Hillslope
surface hydrology. In D. C. Flanagan and M. A. Nearing (Eds.), *USDA Water
Erosion Prediction Project: Hillslope profile and watershed model
documentation* (NSERL Report No. 10, Chapter 4). USDA-ARS National Soil Erosion
Research Laboratory.
[Official PDF](https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/chap4.pdf).

On August 8, 2026, the official Chapter 1, 4, and 6 PDFs were byte-identical to
the copies vendored in openWEPP under `references/50201000`. Their SHA-256
digests were, respectively, `4669e7bb9de3cdc32a6ac745f9e96bac160558d1c531a5e2343fc92ef7460fd6`,
`33d6a8725d40f86e115ff81da8d3da250aa7dd0c216a4056d69a3d52b3d3cce5`,
and `0fa5dd028d906ee901ee092bceac54dbfc72517019483cab715617942389d885`.

## Revision Log

| Version | Date | Changes |
| --- | --- | --- |
| 1.0 | 2026-08-08 | Initial documentation, implementation, and Topanga evidence synthesis. |
| 1.1 | 2026-08-08 | Reframed the report around long-standing WEPP peak-flow behavior, reorganized it as a stakeholder narrative, and added the public Windows WEPP 2024 implementation comparison. |
| 1.2 | 2026-08-08 | Explained the daily and hourly surface-return timing path in plain language and clarified the exact-zero peak-method switch. |
| 1.3 | 2026-08-08 | Defined runtime instrumentation and documented the Ksat experiment's controls, recorded operands, and forced-method counterfactuals. |
| 1.4 | 2026-08-08 | Removed WEPP development recommendations; the report now ends its analysis with the documented evidence and limitations. |
| 1.5 | 2026-08-08 | Added event precipitation and rainfall-intensity context for the extreme 1986 canopy discontinuity. |
