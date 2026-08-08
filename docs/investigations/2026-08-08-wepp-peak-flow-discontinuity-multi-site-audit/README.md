# WEPP Peak-Flow Discontinuity Multi-Site Audit

> A staged, instrumented investigation of how often WEPP peak-flow estimates
> change discontinuously under small hillslope-parameter mutations, how those
> changes propagate through watershed routing, and whether the behavior
> generalizes beyond Topanga.

**Status: PLANNING (`2026-08-08`).** Topanga is the first site and the methods
development fixture. Multi-site, snow, and overland flow element (OFE)
experiments begin only after the Topanga instrumentation and event ledger are
reproducible.

## Why This Investigation Exists

The [Topanga peak-flow investigation](../2026-08-07-topanga-2025-fire-peak-flow-analysis/README.md)
identified repeatable cases in which small parameter changes produced large
peak-runoff changes with little change in event runoff. An instrumented Hill
106 experiment traced one reversal to the way WEPP assigns daily soil-water
surface return, `surdra`, to selected subdaily intervals. A separate exact-zero
ponding-time boundary can switch the peak calculation between `APPMTH` and
`HDRIVE`.

Topanga establishes that these mechanisms can matter. It does not establish
how frequently they occur across a watershed, whether they persist through
channel routing, or whether they are specific to warm, rain-dominated
shrubland. This investigation answers those broader questions with a common
instrumentation and mutation protocol.

The intended result is a reproducible defect census and a set of compact
regression fixtures for openWEPP development. This is not a calibration study,
and it is not an attempt to repair the legacy WEPP implementation.

## Study Questions

1. How frequently do small Ksat, ground-cover, canopy, or vegetation changes
   produce discontinuous hillslope peak-flow responses?
2. How much of each response is attributable to constructing the subdaily
   forcing from `surdra`, switching between `APPMTH` and `HDRIVE`, behavior
   within one solver, or watershed routing?
3. Are the discontinuities concentrated in particular antecedent-moisture,
   soil, vegetation, rainfall, or snowmelt conditions?
4. Are large hillslope discontinuities attenuated, preserved, synchronized,
   or amplified at downstream channels and the watershed outlet?
5. Does OFE discretization change the frequency or magnitude of the response?
6. Which cases should become frozen openWEPP regression tests?

## Scenario Contract

Every site will use the same primary scenario pairing:

| Scenario | WEPPcloud role | Interpretation |
| --- | --- | --- |
| Burned | Base scenario | The site's spatially resolved burned condition |
| Unburned | Omni scenario | A spatially uniform, undisturbed land-cover and management control |

The base scenario must not be relabeled as an Omni burn. It retains the site's
spatial fire-severity pattern. The unburned scenario deliberately removes that
land-cover heterogeneity so every hillslope receives the selected undisturbed
parameterization.

Within a site, the paired scenarios must share climate realization, terrain,
watershed topology, channel inputs, simulation dates, and non-scenario model
settings. Differences in soil or management files must be enumerated before
analysis. Comparisons are made on the same calendar events; return-period
rankings are secondary summaries and never substitute for event pairing.

## Staged Study Design

### Phase 1: Establish the Mechanics at Topanga

Topanga is the development and validation site for the complete workflow. The
first phase will:

1. build an observationally instrumented WEPP executable from a pinned source
   commit;
2. prove that an unmodified build reproduces the established outputs;
3. prove that diagnostic logging does not alter normal outputs;
4. record every runoff-producing event on every hillslope;
5. calculate normal, forced-`APPMTH`, and forced-`HDRIVE` peak estimates from
   the same event forcing;
6. apply small, one-hillslope-at-a-time mutations;
7. trace each local response through downstream channels and the outlet; and
8. freeze representative reproducer decks for each distinct defect class.

Hill 106 and the February 14, 1980 Ksat pair are the first acceptance fixture.
The new ledger must reproduce the operands and peaks reported in the
[instrumented Ksat diagnostic](../2026-08-07-topanga-2025-fire-peak-flow-analysis/artifacts/hill106-ksat-peakflow-diagnostic.md).

The broader implementation evidence and official WEPP documentation are
summarized in the
[stakeholder peak-flow report](../2026-08-07-topanga-2025-fire-peak-flow-analysis/artifacts/wepp-peak-flow-solver-documentation-and-topanga-evidence.md).

### Phase 2: Complete the Topanga Watershed Census

After the Hill 106 fixture passes, apply the core mutation screen to every
Topanga hillslope. Mutate one hillslope per run while leaving all other
hillslopes and channels unchanged. This separates a local solver response from
changes caused by simultaneous watershed-wide parameterization.

For mutations that expose a discontinuity, retain three levels of response:

```text
hillslope parameter mutation
    -> local hillslope hydrograph and PeakRO
    -> downstream channel hydrographs
    -> watershed outlet hydrograph and peak
```

Selected mutations will then be applied to all affected hillslopes together
and watershed-wide. These combined runs test whether routing attenuates the
local errors or synchronizes them into a larger outlet response.

### Phase 3: Extend to Rain- and Snow-Dominated Sites

Once Topanga produces a stable data contract and automated analysis, add sites
incrementally. Every site must have a burned base scenario and an unburned
Omni scenario. The initial portfolio should include:

| Site class | Minimum representation | Purpose |
| --- | ---: | --- |
| Warm, rain-dominated shrub or grass | Topanga plus at least one independent site | Test generalization in the land covers where oddities have recurred |
| Rain-dominated forest | At least one site | Separate vegetation type from rainfall regime |
| Transient or seasonal snow | At least one site | Test rain-on-snow, melt timing, frozen soil, and saturation-return interactions |
| Snow-dominated forest | At least one site if a suitable fixture exists | Test persistent snowpack and spring-melt events |

Sites should vary in watershed size, soil depth, restrictive-layer behavior,
topographic relief, and the frequency of modeled `surdra`. Selection should
favor existing reproducible WEPPcloud runs with known provenance over creating
new projects solely to fill a category.

Snowmelt and mixed rain-snow events will be labeled separately from rainfall-
only events. Their diagnostic records must include snow water equivalent,
snowmelt input, frozen-soil state, and the liquid-water forcing delivered to
infiltration.

### Phase 4: Single-OFE Versus Multiple-OFE Follow-Up

Use one site to compare a single-OFE representation with a deliberately
matched multiple-OFE representation. This phase begins after the cross-site
hillslope mechanics are understood because OFE boundaries add infiltration,
routing, and state-transfer interactions.

The paired profiles should preserve, as closely as WEPP permits:

- total hillslope length, width, area, relief, and mean slope;
- climate sequence and simulation dates;
- area-weighted soil and management properties;
- initial and boundary conditions; and
- channel and watershed routing outside the test hillslope.

The first comparison should divide a homogeneous profile into multiple
identical OFEs. A second comparison may introduce a physically meaningful
upslope-to-downslope contrast. This separates discretization effects from the
effects of genuine spatial heterogeneity.

## Core Mutation Screen

The initial screen uses small perturbations as numerical probes. They are not
alternative calibration values.

| Parameter or state | Initial perturbations | Notes |
| --- | --- | --- |
| First-horizon Ksat | `-1%`, `+1%` | Expand to `-5%`, `+5%` around flagged boundaries |
| Interrill and rill cover | `-0.01`, `+0.01` | Mutate `inrcov` and `rilcov` together |
| Initial canopy cover | `-0.01`, `+0.01` | Keep LAI and other management inputs fixed initially |
| Maximum LAI | `-1%`, `+1%` | Run only after the first three probes are stable |

Each mutation changes one hillslope and one parameter family at a time. Values
must remain within their valid physical domains. Larger burned-to-unburned and
high-ET contrasts follow only after the small-perturbation response is known.

## Instrumentation Contract

Here, *instrumented* means a temporary diagnostic executable that records
internal operands without changing the model equations or normal outputs.
Counterfactual solver selection must be isolated from the observational build
and clearly labeled.

For every hillslope-event with runoff or surface return, record at least:

- site, scenario, mutation, hillslope, OFE, date, and downstream path;
- precipitation depth, intensity, and event duration;
- antecedent soil water and saturation by layer;
- snow state and melt input where applicable;
- runoff before and after water-balance reconciliation;
- hourly `ui_scrunf(ii)` where hourly water balance is active;
- daily `surdra` and the `surpls` depth passed into the peak calculation;
- positive-excess duration, `durre` or `drlast`;
- rainfall-excess series before surface-return insertion;
- solver forcing series after surface-return insertion;
- `remax` before and after reconciliation;
- `tp(2)`, `ealpha`, friction, flow width, and rill width;
- selected peak method and both shadow-method peaks;
- runoff, `PeakRO`, and rectangular-equivalent `EffDur`; and
- hillslope, downstream-channel, and outlet hydrographs and peaks.

The event ledger must preserve raw values and units. Derived classifications
belong in separate columns so the source observations remain auditable.

## Event Classification

Every mutation is paired to its baseline by site, scenario, hillslope, and
date. The analysis will calculate changes in runoff, peak, `surdra`, positive-
excess duration, `surdra/durre`, pre- and post-reconciliation forcing, solver
selection, and downstream peak timing.

Initial diagnostic flags are:

- **timing compression:** a small mutation strongly changes
  `surdra/durre`;
- **solver switch:** `tp(2)` crosses zero and changes the selected method;
- **solver disagreement:** shadow `APPMTH` and `HDRIVE` peaks differ
  materially on identical forcing;
- **within-solver discontinuity:** peak changes abruptly without a method
  switch;
- **routing attenuation or amplification:** the downstream response is
  proportionally smaller or larger than the local response;
- **synchronization change:** outlet peak changes because tributary timing
  changes; and
- **unresolved:** recorded mechanics do not yet explain the response.

A small mutation is screened as potentially discontinuous when it causes any
of the following:

- more than a 25% peak change with less than a 5% runoff change;
- more than a twofold peak change;
- a solver-method switch;
- more than a twofold change in `surdra/durre`; or
- reversal of the expected local response to Ksat or surface cover.

These thresholds organize review; they do not define physical correctness.
All continuous values will be retained.

## Required Outputs

The investigation will maintain:

1. a manifest of source commits, executable hashes, site run identifiers, and
   scenario inputs;
2. an event ledger with one row per run, hillslope, and date;
3. a routing ledger relating hillslope responses to downstream channels;
4. a discontinuity census by site, scenario, parameter, and mechanism;
5. paired plots of runoff ratio versus peak ratio;
6. plots of peak response versus `surdra/durre` and solver selection;
7. local and outlet hydrographs for representative events;
8. maps of flagged hillslopes and their routing paths; and
9. frozen input decks for openWEPP regression development.

## Reproducibility and Change Control

- Pin source commits and record executable SHA-256 hashes.
- Preserve an unmodified reference build beside each diagnostic build.
- Demonstrate that logging-only builds reproduce ordinary output exactly.
- Keep forced-method counterfactuals separate from observational runs.
- Run complete climate histories so mutations generate their own antecedent
  states.
- Do not compare unmatched event dates as evidence of a mechanism.
- Record every input mutation as a machine-readable patch or manifest entry.
- Store derived tables and figures under [`artifacts/`](artifacts/README.md).
- Restore shared source worktrees after temporary diagnostic builds.

## Current Decisions

| Decision | Rationale |
| --- | --- |
| Start with Topanga | Hill 106 supplies an established acceptance fixture and known discontinuities |
| Complete mechanics before adding sites | Prevents inconsistent instrumentation and repeated forensic work |
| Burned base versus unburned Omni at every site | Provides one consistent cross-site scenario contract |
| Compare identical dates | Preserves storm and antecedent-state context |
| Mutate one hillslope first | Separates local calculation defects from watershed synchronization |
| Include snow sites after Topanga | Tests a materially different water-input and soil-state regime without complicating initial development |
| Defer OFE comparison | OFE boundaries introduce additional coupling best studied after the single-profile mechanics are understood |
| Produce openWEPP fixtures, not a legacy repair | The legacy code lacks the isolation and regression coverage needed for a dependable repair effort |

## Immediate Next Steps

1. Define the diagnostic executable's event-ledger schema.
2. Reproduce the Hill 106 February 14, 1980 Ksat trace through that schema.
3. Add noninvasive shadow calculations for both peak methods.
4. Prove normal-output parity between the reference and logging-only builds.
5. Run the `±1%` Ksat and `±0.01` paired-cover screen across Topanga.
6. Review the Topanga census before selecting the next site.

## Related Investigations

- [Topanga 2025 fire peak-flow analysis](../2026-08-07-topanga-2025-fire-peak-flow-analysis/README.md)
- [Palisades fire peak-flow inversion](../2026-08-03-palisades-fire-peak-flow-inversion/README.md)
- [Stevens Canyon peak-flow inversion](../2026-08-03-stevens-canyon-peak-flow-inversion/README.md)

## Revision Log

| Version | Date | Changes |
| --- | --- | --- |
| 1.0 | 2026-08-08 | Established the Topanga-first multi-site audit, scenario contract, snow-site phase, and single- versus multiple-OFE follow-up. |
