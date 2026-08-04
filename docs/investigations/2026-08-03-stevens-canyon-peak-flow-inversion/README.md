# Stevens Canyon Burned–Undisturbed Peak-Flow Investigation

**Status: OPEN, MECHANISM NARROWED (`2026-08-04`).** The reported peak-flow
reversals are confirmed in raw WEPP channel output. The project-to-project
channel-parameter mismatch hypothesis is ruled out. Hillslope replays support
an antecedent shallow-soil saturation mechanism, while contradicting the
simpler hypothesis that the undisturbed full profile contains more water.

## Summary

This investigation compares two public `disturbed9002` projects on `wepp1`:

- burned: `callable-shred`, scenario `Burned_Qp_allStreams`;
- undisturbed: `stabilized-housecleaning`, scenario
  `Undisturbed_Qp_allStreams`.

The projects use byte-identical DEM, watershed topology, climate, channel
definition, and WEPP watershed-control files. Their channel parameters are
therefore not responsible for the different peak-flow results.

The reported reversal is present in raw
`wepp/output/interchange/chan.out.parquet`, but it is uncommon and strongly
event-dependent. WEPP_IDs 169, 172, and 173 usually have a higher burned peak
when their scenario peaks differ. The largest common reversal occurs in
simulation year 34 on Julian day 203, a `58.7 mm` precipitation day. On that
day, the undisturbed peak is higher at all three selected reaches and at the
outlet.

A subsequent cross-site soil-evaporation decomposition corrected an informal
magnitude comparison with the Palisades fixture. Like-for-like burned-PMET,
area-weighted daily `Es` peaks at `4.96 mm/day` in Stevens Canyon and
`3.86 mm/day` in Palisades: a `1.28×` ratio, not `8×`. Their 99th-percentile
ratio is only `1.09×`. Perfect synchronization of every hillslope's individual
maximum cannot explain the residual contrast. Stevens instead combines about
twice the realized `Ep + Es` throughput on high-`Es` days with available
upper-layer water, even though Palisades assigns a larger fraction of ET to
soil evaporation.

The selected stream lines must not be classified as unaffected merely because
the line geometry is outside the fire perimeter. WEPP routes runoff from the
complete upstream contributing area. WEPP_ID 169 is locally supplied by burned
hillslopes; WEPP_ID 172 is locally supplied by burned hillslopes and two
upstream branches; and WEPP_ID 173 receives both 169 and 172. Its full
contributing area is `1279.53 ha`, of which `1080.09 ha` of evergreen forest
is parameterized as low- or moderate-severity fire in the burned project.

## Scope and Evidence

- Host: `wepp1`
- Read-only production check: `2026-08-03T08:54:20-07:00`
- Burned host path:
  `/geodata/wc1/runs/ca/callable-shred`
- Undisturbed host path:
  `/geodata/wc1/runs/st/stabilized-housecleaning`
- Container paths use the same suffixes under `/wc1/runs/`.
- Configuration: `disturbed9002.cfg`
- Simulation duration: 100 years
- Channels: 55
- Hillslopes: 138

Production files were read only. No project, output, or NoDb state was
modified.

Primary evidence:

- `watershed/channels.parquet`
- `watershed/hillslopes.parquet`
- `watershed.nodb` (`_structure`)
- `landuse/landuse.parquet`
- `disturbed.nodb`
- `soils.nodb`
- `wepp/runs/pw0.str`
- `wepp/runs/pw0.chn`
- `wepp/output/interchange/chan.out.parquet`
- `wepp/output/interchange/chnwb.parquet`

## Input Equivalence

SHA-256 comparisons found the following files byte-identical between the two
projects:

- `dem/dem.tif`
- `dem/topaz/CHANNELS.JSON`
- `watershed/channels.geojson`
- `watershed/channels.parquet`
- `climate/p10.cli`
- `wepp/runs/chan.inp`
- `wepp/runs/chntyp.txt`
- `wepp/runs/pw0.chn`
- `wepp/runs/pw0.str`
- `wepp/runs/pw0.run`
- `wepp/runs/wepp_ui.txt`

The intentional scenario differences are land cover, management, and soil
parameterization. The burned project has a spatial SBS assignment; the
undisturbed project restores the corresponding undisturbed land cover and soil
uses.

## Network Relationships

The selected identifiers are WEPP **channel-element** IDs. Land use belongs to
their contributing hillslopes, not to the channel lines themselves.

```text
WEPP 170 ----\
              > WEPP 172 --\
WEPP 171 ----/               \
                              > WEPP 173
WEPP 169 --------------------/
```

The direct and recursive relationships derived from `watershed.nodb` are:

| Channel WEPP_ID | Channel TOPAZ ID | Direct hillslope TOPAZ IDs | Upstream channel WEPP_IDs | Full contributing hillslopes |
| ---: | ---: | --- | --- | ---: |
| 169 | 264 | 261, 262, 263 | None | 3 |
| 172 | 234 | 232, 233 | 170, 171 | 8 |
| 173 | 224 | 222, 223 | 169, 172 | 13 |

Thus, reach 173 contains the effects propagated through both selected upstream
reaches. Reach 172's full contributing set also includes hillslopes attached to
reaches 170 and 171.

## Channel Characteristics

`slope_scalar` is dimensionless rise/run; the percent values below are
`100 * slope_scalar`.

| WEPP_ID | TOPAZ ID | Order | Length (m) | Width (m) | Channel slope (%) | Aspect (degrees) | Local channel area (m2) | Elevation (m) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 169 | 264 | 1 | 222.43 | 1.14 | 14.07 | 63.28 | 254.43 | 2213.2 |
| 172 | 234 | 2 | 4090.73 | 3.01 | 2.86 | 64.23 | 12318.19 | 2297.0 |
| 173 | 224 | 2 | 939.41 | 3.66 | 4.49 | 79.86 | 3435.35 | 2177.4 |

The channel input file is identical across scenarios and applies the same
default waterway-channel definition. Scenario differences enter these reaches
through hillslope runoff and routed upstream flow.

## Contributing-Area Overview

Area-weighted slope uses the watershed `slope_scalar` assigned to each
hillslope. It describes the full contributing hillslope set listed above; it
is not the channel-bed slope.

| Channel WEPP_ID | Contributing area (ha) | Hillslopes | Area-weighted slope (%) | Hillslope slope range (%) | Burned-project land-use composition (ha) |
| ---: | ---: | ---: | ---: | ---: | --- |
| 169 | 90.09 | 3 | 25.02 | 13.50–25.93 | 83.07 moderate fire; 7.02 low fire |
| 172 | 1086.84 | 8 | 15.33 | 4.00–25.56 | 570.60 moderate fire; 339.30 low fire; 176.94 deciduous forest |
| 173 | 1279.53 | 13 | 15.76 | 4.00–25.93 | 653.67 moderate fire; 426.42 low fire; 176.94 deciduous forest; 22.50 shrub/scrub |

The matching undisturbed composition is:

| Channel WEPP_ID | Evergreen forest (ha) | Deciduous forest (ha) | Shrub/scrub (ha) |
| ---: | ---: | ---: | ---: |
| 169 | 90.09 | 0.00 | 0.00 |
| 172 | 909.90 | 176.94 | 0.00 |
| 173 | 1080.09 | 176.94 | 22.50 |

For WEPP_ID 173, `1080.09 ha` changes from evergreen forest in the
undisturbed project to a fire-severity management in the burned project. The
deciduous forest and shrub/scrub portions remain in their original land-use
classes.

## Hillslope Detail

The following table covers the complete contributing area of WEPP_ID 173 and,
therefore, contains the contributing sets for 169 and 172. `H WEPP_ID` is the
hillslope element identifier. Area is plan area from
`watershed/hillslopes.parquet`.

| Channel membership | TOPAZ ID | H WEPP_ID | Area (ha) | Slope (%) | Profile length (m) | Aspect (degrees) | Burned project | Undisturbed project |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 173 direct | 222 | 49 | 22.50 | 12.58 | 204.85 | 29.50 | Shrub/Scrub | Shrub/Scrub |
| 173 direct | 223 | 50 | 80.10 | 12.14 | 542.13 | 118.01 | Low Severity Fire | Evergreen Forest |
| 172 direct | 232 | 51 | 140.22 | 25.56 | 319.71 | 318.80 | Moderate Severity Fire | Evergreen Forest |
| 172 direct | 233 | 52 | 210.33 | 16.74 | 514.16 | 110.57 | Moderate Severity Fire | Evergreen Forest |
| 172 via 171 | 241 | 53 | 81.90 | 19.33 | 724.26 | 335.28 | Moderate Severity Fire | Evergreen Forest |
| 172 via 171 | 242 | 54 | 64.71 | 22.33 | 528.86 | 265.27 | Moderate Severity Fire | Evergreen Forest |
| 172 via 171 | 243 | 55 | 73.44 | 13.67 | 542.13 | 55.01 | Moderate Severity Fire | Evergreen Forest |
| 172 via 170 | 251 | 56 | 82.62 | 4.00 | 904.26 | 56.40 | Low Severity Fire | Evergreen Forest |
| 172 via 170 | 252 | 57 | 176.94 | 12.26 | 327.43 | 12.49 | Deciduous Forest | Deciduous Forest |
| 172 via 170 | 253 | 58 | 256.68 | 11.79 | 474.99 | 108.76 | Low Severity Fire | Evergreen Forest |
| 169 direct | 261 | 59 | 83.07 | 25.93 | 1115.33 | 86.90 | Moderate Severity Fire | Evergreen Forest |
| 169 direct | 262 | 60 | 2.34 | 15.97 | 102.43 | 40.00 | Low Severity Fire | Evergreen Forest |
| 169 direct | 263 | 61 | 4.68 | 13.50 | 121.07 | 111.63 | Low Severity Fire | Evergreen Forest |

### Management-cover differences

The generated land-use tables report these cover values:

| Management class | Canopy cover | Interrill cover | Rill cover |
| --- | ---: | ---: | ---: |
| Evergreen Forest | 0.90 | 1.00 | 1.00 |
| Low Severity Fire | 0.75 | 0.85 | 0.85 |
| Moderate Severity Fire | 0.60 | 0.60 | 0.60 |
| Shrub/Scrub | 0.70 | 0.90 | 0.90 |

These are not visual labels alone. They select different generated management
and soil-use inputs. For example, direct hillslopes 261–263 above WEPP_ID 169
change from `Evergreen Forest` to one moderate- and two low-severity fire
parameterizations. Direct hillslopes 232–233 above WEPP_ID 172 both change to
moderate-severity fire. Direct hillslope 223 above WEPP_ID 173 changes to
low-severity fire, while direct shrub hillslope 222 is unchanged.

## Confirmed Peak-Flow Pattern

The two `chan.out.parquet` datasets have the same `2,008,875` event-channel
keys; there are no unmatched rows. Counts below compare raw peak discharge at
each selected reach and exclude equal days from the directional counts.

| WEPP_ID | Undisturbed > burned days | Burned > undisturbed days | Equal days | Largest undisturbed-minus-burned difference (m3/s) |
| ---: | ---: | ---: | ---: | ---: |
| 169 | 45 | 9202 | 27278 | 8.259 |
| 172 | 48 | 20500 | 15977 | 23.800 |
| 173 | 52 | 19881 | 16592 | 33.180 |
| Outlet 193 | 198 | 35936 | 391 | 73.000 |

The dominant reversal is simulation year 34, Julian day 203:

| WEPP_ID | Burned peak (m3/s) | Undisturbed peak (m3/s) | Burned time to peak (s) | Undisturbed time to peak (s) |
| ---: | ---: | ---: | ---: | ---: |
| 169 | 0.000746 | 8.26 | 7200 | 1800 |
| 172 | 9.60 | 33.40 | 3600 | 2400 |
| 173 | 9.32 | 42.50 | 4200 | 2400 |
| Outlet 193 | 150.00 | 223.00 | 5400 | 4800 |

The different times to peak show that the comparison is not simply a fixed
multiplier on runoff. Tributary hydrograph timing and synchronization can alter
the instantaneous watershed peak. The channel water-balance output also shows
that the scenarios enter the day with materially different hydrologic states
and routed-flow histories.

## Cross-Event Peak-Timing Test

To test whether the early undisturbed peak on year 34, day 203 is a persistent
pattern, channel records were paired by simulation year, Julian day, and
`Elmt_ID`. Days with peaks below `0.01 m3/s` in either scenario were excluded.
The timing difference is defined as undisturbed minus burned, so a negative
value means the undisturbed peak arrived earlier. Reported peak times in these
records occur in 600-second increments.

Two peak-discharge similarity bands were tested:

- strict: undisturbed-to-burned peak ratio from `0.8` through `1.25`;
- broad: undisturbed-to-burned peak ratio from `0.5` through `2.0`.

The broad, factor-of-two comparison provides enough upstream events for a
directional test:

| WEPP_ID | Comparable events | Undisturbed earlier | Same time | Undisturbed later | Median timing difference (s) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 169 | 0 | 0 | 0 | 0 | n/a |
| 172 | 69 | 18 | 9 | 42 | +600 |
| 173 | 41 | 15 | 5 | 21 | +600 |
| Outlet 193 | 520 | 128 | 234 | 158 | 0 |

Under the strict band, reach 172 has only one comparable event, on which the
undisturbed peak is 1,800 seconds later; reaches 169 and 173 have none. At the
outlet, 93 events meet the strict criterion: the undisturbed peak is earlier on
3, simultaneous on 68, and later on 22, with a median difference of zero.

The conclusion does not change when the comparison is limited to events where
the undisturbed peak magnitude exceeds the burned peak. Reach 172 has eight
such nontrivial events: undisturbed is earlier on three, simultaneous on one,
and later on four. Reach 173 has nine: earlier on four, simultaneous on two,
and later on three. At the outlet there are 24: earlier on 14, simultaneous on
8, and later on 2. This outlet tendency is real within the small subset, but it
does not establish a general timing rule for similar-magnitude events.

On year 34, day 203, the undisturbed peak leads the burned peak by 5,400
seconds at reach 169, 1,200 seconds at reach 172, 1,800 seconds at reach 173,
and 600 seconds at the outlet. Those leads are therefore event-specific and,
at the upstream reaches, materially larger than the cross-event medians.

These tests compare **peak discharge magnitude**, not daily runoff volume or
storm-total flow. A separate volume-conditioned comparison would be needed to
answer whether similar runoff-producing storms have a different timing
pattern.

## Antecedent Soil-Moisture Test

H49-H61 were replayed locally with `wepp_260803_hill`. The fixture retained the
production climate, management, slope, soil, and runtime sidecars, while
enabling two complementary daily outputs:

- `H*.wat.dat`: full-profile soil-water storage and profile capacities;
- `H*.grph.dat`: total soil water and water in soil layers 1 through 10.

The event is simulation year 34, Julian day 203. Day 202 is the immediately
preceding end-of-day state. Values below are hillslope-area-weighted over each
reach's full contributing set.

| Channel WEPP_ID | Scenario | Day-202 full-profile water (mm) | Day-202 profile porosity fraction | Day-202 surface saturation fraction | Day-203 hillslope runoff (mm) |
| ---: | --- | ---: | ---: | ---: | ---: |
| 169 | Burned | 504.23 | 0.651 | 0.369 | 0.31 |
| 169 | Undisturbed | 377.05 | 0.487 | 0.719 | 22.17 |
| 172 | Burned | 266.28 | 0.538 | 0.390 | 4.94 |
| 172 | Undisturbed | 216.23 | 0.437 | 0.571 | 10.49 |
| 173 | Burned | 299.07 | 0.554 | 0.379 | 4.24 |
| 173 | Undisturbed | 238.31 | 0.442 | 0.579 | 10.85 |

The full-profile hypothesis is therefore rejected: the undisturbed profiles
are not wetter overall. Immediately before the storm, the burned full profile
above reach 173 holds about `60.8 mm` more water and occupies a larger fraction
of its total porosity capacity.

The vertical distribution gives the opposite result near the surface. The
undisturbed-minus-burned day-202 layer-water differences above reach 173 are:

| Layer | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Difference (mm) | +9.0 | +5.2 | +8.8 | -21.3 | -11.0 | -10.3 | -10.3 | -10.3 | -10.3 | -10.3 |

The undisturbed scenario stores more water in layers 1-3 but substantially
less in layers 4-10. Its area-weighted surface saturation fraction is `0.579`
before the storm, compared with `0.379` burned. During day 203 those fractions
rise to `0.908` and `0.788`, respectively, while undisturbed hillslope runoff
is `10.85 mm` versus `4.24 mm` burned.

This pattern is strongest above reach 169, where the pre-event surface
saturation fractions are `0.719` undisturbed and `0.369` burned, followed by
day-203 runoff of `22.17 mm` and `0.31 mm`. Eleven of the 13 hillslopes have a
higher undisturbed day-202 surface saturation fraction; two unchanged land-use
hillslopes are equal, and none has a higher burned fraction.

The evidence supports the proposed **shallow-layer saturation-excess**
explanation, not a full-profile wetness explanation. It does not yet prove that
saturation excess is the only runoff-production mechanism on the event. A
process-level infiltration/runoff trace would be needed to separate saturation
excess formally from every other WEPP runoff threshold. The observed vertical
storage pattern, surface saturation, and runoff direction nevertheless form a
coherent and materially large signal.

## Interpretation

Two separate observations should not be conflated:

1. **Why an apparently unburned stream line changes:** the channel line drains
   burned local or upstream hillslopes. Fire-line intersection is not the
   correct exposure metric; fire coverage over the full upstream contributing
   area is.
2. **Why a particular undisturbed event peak exceeds burned:** this is a real,
   rare, event-scale reversal. It is not explained by different channel
   parameters or by greater undisturbed full-profile water. The hillslope
   replays show greater undisturbed water in the upper three layers, much higher
   pre-event surface saturation, and greater event runoff. Routed tributary
   timing then determines how those hillslope hydrographs combine into the
   channel peak. Cross-event comparisons show no persistent undisturbed-earlier
   timing bias: on similar-magnitude events, peaks are generally simultaneous
   or later in the undisturbed scenario.

The first observation is resolved for WEPP_IDs 169, 172, and 173 by the
contributing-area tables above. The second is narrowed to a supported
shallow-storage mechanism but remains open for process-level attribution and
routing decomposition.

A leading alternative routing hypothesis is that the active lateral-inflow
builder uses a universal peak-time fraction (`tc = td / 2.67`) instead of the
event- and hillslope-specific overland-flow time of concentration already
computed as `htcs`. The dormant `htcs` statement also appears to use the
current channel index rather than the contributing hillslope index, so it
cannot safely be enabled literally. The proposed experiment and branch audit
are documented in [Hillslope Synchronization Sensitivity
Design](artifacts/synchronization-sensitivity-design.md).

## Synchronization Sensitivity Results

A volume-preserving timing experiment was completed against the unchanged
undisturbed hillslope pass outputs. One fixed spatial pattern was applied to
H49-H61 at low (10%), medium (20%), and high (30%) amplitudes. Each hillslope's
event duration was multiplied and its supplied peak divided by the same factor,
leaving runoff volume and `peak × duration` unchanged. All three lanes completed
the configured 100 years with empty stderr and the hourly-water-balance startup
marker enabled by the required zero-byte `wepp_ui.txt` sidecar.

On day 203, medium dispersion reduced peaks at reaches 169, 172, and 173 by
approximately 10.7%, 9.0%, and 6.1%, respectively. It reduced the outlet peak
by about 0.9%. The inversion remained large relative to burned. High dispersion
was non-monotonic: it raised reach 173 from `42.5` to `42.7 m3/s` and the outlet
from `223` to `225 m3/s`. Hillslope synchronization therefore affects the peak,
but the tested timing variation does not explain away the inversion.

Day-203 channel inflow, outflow, and balance values are identical across the
baseline and three dispersion lanes to the precision reported by `chanwb.out`.
This confirms that the experiment changed hydrograph timing rather than daily
routed volume.

- [Figure 1: Day-203 peak sensitivity](figures/figure-1-day203-peak-sensitivity.md)
- [Figure 2: Full-record peak response](figures/figure-2-full-record-peak-response.md)
- [Figure 3: Day-203 hillslope timing inputs](figures/figure-3-day203-hillslope-timing-inputs.md)

The source-level contributor-indexed `htcs` lane was not accepted as evidence.
The current rebuilt source expects binary pass shards, whereas this production
fixture contains legacy text shards. The lane stopped at that explicit
compatibility boundary before routing. No failed-lane values are included in
the figures.

## Contributor-Indexed `htcs` Results

A follow-on study resolved that text-pass compatibility boundary in an
isolated build. It restored the historical text reader while retaining the
current routing source, then corrected the dormant `htcs` expression to use
the actual contributing hillslope. The production checkout and projects
remained unchanged. Both full 100-year lanes completed with hourly
water-balance output and empty stderr.

The same-build control exactly reproduces the archived production focal peaks:
`8.26`, `33.4`, `42.5`, and `223 m3/s` at reaches 169, 172, 173, and 193.
Direct contributor-indexed `htcs` gives `8.22`, `33.2`, `42.2`, and `224
m3/s`. This small, mixed response does not explain the inversion.

| CV | Reach 169 median (p05–p95) | Reach 172 median (p05–p95) | Reach 173 median (p05–p95) | Outlet median (p05–p95) |
| ---: | ---: | ---: | ---: | ---: |
| 0.10 | +2.43% (+0.36–+13.52%) | +0.30% (-2.42–+4.26%) | +0.24% (-2.84–+2.89%) | 0.00% (-0.44–+0.87%) |
| 0.25 | +5.34% (+0.72–+18.45%) | +1.21% (-6.04–+6.96%) | -0.47% (-4.54–+4.74%) | -0.44% (-1.75–+1.31%) |
| 0.50 | +11.04% (+0.36–+22.63%) | +2.42% (-8.16–+6.98%) | -0.83% (-6.45–+6.41%) | -1.31% (-3.93–+0.87%) |

All 300 accepted, area-normalized spatial realizations preserve day-203
channel inflow and outflow at the four targets to reported precision. The
inversion persists. Timing variation materially affects the small upstream
reach, but its outlet-scale effect is modest.

Across the full record, the direct source change has a median response of zero
at every target and changes few qualifying events. Events with routed inflow
within 25% of the focal magnitude are rare: four at reach 169, two each at 172
and 173, and only the focal event at the outlet. This record cannot establish a
consistent response among similar-magnitude events.

- [Figure 4: Day-203 contributor-indexed `htcs` ensemble](figures/figure-4-day203-htcs-ensemble.md)
- [Figure 5: Full-record `htcs` response](figures/figure-5-htcs-full-record-response.md)
- [Figure 6: Magnitude-matched events](figures/figure-6-htcs-magnitude-matched-events.md)

The compact ensemble fixture lacks 33 years of preceding channel state. It is
paired routing sensitivity, not absolute production replay. Full-record
conclusions use the same-build control/direct pair. That control has exact
focal production parity but documented full-record drift from the archived
binary, so causal inference is confined to the same-build pair.

## Next Checks

1. Confirm that simulation year 34, Julian day 203 is the storm used in the
   external spreadsheet. If not, repeat the event trace for its exact year and
   Julian day.
2. Add or enable a process-level runoff trace that distinguishes saturation
   excess from other infiltration/runoff thresholds on day 203.
3. Add a counterfactual hillslope-input swap to partition the inversion between
   runoff generation and channel routing.
4. Repeat the magnitude-conditioned test with a larger climate ensemble; the
   current record supplies too few comparable events.
5. Compare antecedent surface-layer water, canopy interception, percolation,
   evapotranspiration, and snow state over an appropriate pre-event window.
6. Map each reach by its recursively contributing fire-severity area rather
   than by stream-line intersection with the SBS raster.

Local hillslope-only burned, undisturbed, and high-severity replay fixtures for
H49-H61 and `wepp_260803_hill` are
documented in [Hillslope Replay Fixtures](artifacts/hillslope-fixtures.md). The
fixture preserves the production run-directory sidecars and enables daily
full-profile soil-water fields through `H*.wat.dat` and layer-by-layer soil
water through `H*.grph.dat`; it does not execute a watershed run.

Three-scenario year-34 stacked-area plots of surface runoff, lateral subsurface flow,
deep percolation, and the three evapotranspiration components are indexed in
[Hillslope Water-Flux Figures](figures/hillslope-water-fluxes/README.md). These
figures use the H49-H61 outputs. The high-severity forest counterfactual retains
canonical `ksflag=0`, `ksatadj=1`, `ksatfac=100`, and `ksatrec=0.3`; the forest
conductivity adjustment is activated by `ksatadj` in the model path. H49 and
H57 remain unchanged controls.

The active evaporation source and paired management inputs are traced in
[Soil-Evaporation Code Trace](artifacts/soil-evaporation-code-trace.md). The
leading mechanism is an exponential LAI-based transfer of potential ET from
plant transpiration to soil evaporation, reinforced by reduced residue. Canopy
cover does not directly attenuate soil evaporation in the active equations.
The diagnostic acceptance envelopes are specified in [Post-Fire Annual ET
Calibration Targets](artifacts/et-calibration-targets.md).

## Cross-Hillslope Water-Balance Attribution

The reproducible [area-weighted attribution](artifacts/water-balance-attribution.md)
aggregates H49-H61 over the recursive contributing sets for reaches 169, 172,
and 173. On year 34, day 203, reach 173 receives `10.85 mm` of undisturbed
hillslope runoff versus `4.24 mm` burned. Lateral flow is only `0.26 mm` versus
`0.03 mm`, and the preceding 30 days contain approximately zero lateral flow
in either scenario. The inversion is therefore carried primarily by surface
runoff generation, not by accumulated lateral subsurface delivery.

Undisturbed area-weighted daily runoff exceeds burned on only 21 of 36,525
days above reach 173. On those uncommon days the mean undisturbed-minus-burned
differences are `+1.555 mm` for runoff, `+0.090 mm` for lateral flow,
`+0.563 mm` for plant-side ET, and `-1.279 mm` for soil evaporation. This is
consistent with the previously identified shallow-water mechanism: burned
soil evaporation depletes the surface while undisturbed plant uptake draws
more strongly from the rooted profile.

Across the full record, total ET is nearly conserved between the mixed burned
and undisturbed scenarios above reach 173 (`321.75` versus `328.65 mm/year`),
despite the model moving about `100 mm/year` from plant-side ET into soil
evaporation. The clean high-severity comparison above reach 169 has a median
paired annual ET ratio of `0.877` and median `Es/ET` of `0.521`; none of 100
years meets the provisional `0.40-0.60` high-severity ET-ratio target. Thus the
high-severity extension confirms rather than resolves the ET-partition concern.

### PMET coefficient calibration

A subsequent [924-run `kcb`/`rawp` calibration](artifacts/pmet-calibration-results.md)
tested 42 coefficient pairs independently for low-, moderate-, and
high-severity forest over all 100 climate years. Low severity came marginally
close at `kcb=0.35`, `rawp=0.80` (ET ratio `0.837`, `Es/ET=0.317`), but only 4%
of years met both envelopes. Moderate severity remained far too high in total
ET at its best edge candidate. High severity remained far too soil-evaporation
dominated (`Es/ET=0.617`) even when total ET approached its magnitude range.

All best candidates were on the lowest `kcb` boundary, and changing `rawp`
across `0.30-0.80` moved median ET ratios by only `0.01-0.03` at fixed `kcb`.
The experiment therefore rejects `kcb` and `rawp` as sufficient controls for
the full severity target matrix. No production values were changed.

The resulting design alternatives and recommended development sequence are
captured in [Forest and Post-Fire ET Model Options](artifacts/forest-et-model-options.md).

### Stevens–Palisades peak-`Es` counterfactual

The completed
[counterfactual work package](../../work-packages/20260803_stevens_palisades_es_counterfactual/artifacts/results.md)
replayed all 278 Palisades burned-PMET hillslopes and parsed all 13 Stevens
contributing hillslopes with the canonical `wepp_260803_hill` output. The exact
perfect-synchronization bounds are `5.181 mm/day` Stevens and `3.958 mm/day`
Palisades, compared with observed area-weighted peaks of `4.959` and
`3.863 mm/day`. Synchronization therefore widens the site difference slightly
and is a negative explanation.

Across each site's top 100 `Es` days, median realized `Ep + Es` is
`7.79 mm/day` Stevens and `3.62 mm/day` Palisades. Their median soil fractions
are `0.455` and `0.770`, respectively. The higher absolute Stevens `Es` is thus
carried by greater total evaporative throughput coincident with surface-water
availability, not by a stronger cross-site PMET allocation to soil. Fully
separating meteorological reference demand from water and vegetation limits
would require output of the intermediate PMET terms; the current comparison
does not claim that unresolved split.

### Legacy-ET model-form ablation

A paired [burn matrix without PMET](artifacts/legacy-et-ablation-results.md)
ran all eleven forest hillslopes under undisturbed, burned, and high-severity
inputs with `pmetpara.txt` absent but `wepp_ui.txt` and the other runtime
sidecars preserved. No severity produced a year inside both diagnostic target
envelopes. Median total-ET ratios were `0.990`, `0.997`, and `0.862` for low,
moderate, and high severity, respectively.

The legacy routine assigns undisturbed ET entirely to `Ep` (`Es=Er=0`) and
then reallocates demand into `Es` and `Er` after canopy and residue loss. It
changes the partition, particularly for low severity, but barely changes the
total-ET response relative to the existing PMET fixture. This rules out simply
disabling PMET as a credible post-fire correction and shows that the excessive
ET response is shared across both model paths.

## Preliminary Conclusion

### Focal-event process attribution

The completed
[year-34/day-203 attribution study](../../work-packages/20260803_stevens_event_attribution/artifacts/results.md)
now identifies antecedent PMET soil evaporation as a material cause of the
shallow-storage and runoff inversion. Over days 173–202, area-weighted burned
`Es` is `28.21 mm` versus `2.32 mm` undisturbed, an excess loss of `25.89 mm`.
That nearly closes against the independently measured `23.0 mm` undisturbed
advantage in layers 1–3 before the storm.

The paired climate supplies `84.4 mm` to both scenarios. Burned hillslopes
actually receive `10.37 mm` more of the PMET wetting/infiltration term, while
plant transpiration differs by only `1.06 mm`. Instrumented equation terms show
that low LAI and reduced residue create the burned soil-evaporation request;
surface-water limitation suppresses rather than creates it, and PMET reference
demand is identical. This evidence upgrades PMET antecedent depletion from a
plausible concern to a material event mechanism. It does not establish PMET as
the exclusive cause because management simultaneously changes rooting, cover,
interception, and infiltration.

The selected reaches are not hydrologically outside the fire. WEPP_ID 169 is
entirely supplied by hillslopes assigned low- or moderate-severity fire;
WEPP_ID 172 receives a predominantly fire-parameterized contributing area; and
WEPP_ID 173 aggregates both. Substantial burned-versus-undisturbed changes at
these reaches are therefore expected.

The larger undisturbed peak on the dominant year-34/day-203 event is unusual
relative to the full 100-year record, propagates to the outlet, and cannot be
attributed to a channel-input mismatch. It also is not caused by a wetter
undisturbed profile overall. The undisturbed scenario instead concentrates
more antecedent water near the surface, producing a much higher surface
saturation fraction and more hillslope runoff during the storm. That supports
a saturation-excess interpretation. The early undisturbed peak is not a
consistent cross-event trend, including among events with similar peak
discharges, and appears to be part of this event's runoff-generation and
hydrograph-synchronization response. Contributor-indexed `htcs` routing and 300
spatial-variation realizations do not remove the inversion, and their outlet
response is small. Area-weighted hillslope accounting shows that surface runoff
rather than lateral flow carries the focal inversion. The strongest next study
was the process-instrumented `evappm` experiment now completed above. Its trace
supports excess burned soil evaporation as the antecedent mechanism. The
remaining highest-value causal test is a restart or state-swap experiment that
holds the day-202 layer-water profile fixed while swapping management/runoff
physics. Route resulting hillslope hydrographs through a common channel state
only after that state intervention; broad parameter mutation remains
premature.
