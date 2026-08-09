# WEPP Peak-Flow Discontinuity Multi-Site Audit

> A staged, instrumented investigation of how often WEPP hillslope peak-flow
> estimates change discontinuously under small parameter mutations and whether
> the behavior generalizes beyond Topanga. Watershed propagation is a separate
> follow-up, not part of the census critical path.

**Status: PHASE 2A COMPLETE; LOCAL TOPANGA CENSUS AUTHORIZED (`2026-08-09`).**
Versioned schemas, immutable event-packet capture, process-isolated solver
replay, active-trace parity, and compact Topanga acceptance fixtures pass. The
[local-census amendment](../../work-packages/20260808_peakflow_phase2a_pilot/artifacts/study-design-amendment-local-census.md)
culls per-mutation watershed routing so unresolved routing criteria do not
block the local census. Cross-site prevalence, snow-site, and overland flow
element (OFE) work remain staged behind their own gates.

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

The intended result is first a reproducible *candidate anomaly census*. A
candidate becomes a confirmed implementation defect only after local
bracketing, frozen-event replay, and mechanism tracing. Compact confirmed
fixtures will support openWEPP development. This is not a calibration study,
and it is not an attempt to repair the legacy WEPP implementation.

## Study Questions

1. How frequently do small Ksat, ground-cover, canopy, or vegetation changes
   produce discontinuous hillslope peak-flow responses?
2. How much of each local response is attributable to constructing the
   subdaily forcing from `surdra`, switching between `APPMTH` and `HDRIVE`, or
   behavior within one solver?
3. Are the discontinuities concentrated in particular antecedent-moisture,
   soil, vegetation, rainfall, or snowmelt conditions?
4. In a separate routing follow-up, are selected large hillslope
   discontinuities attenuated, preserved, synchronized, or amplified at
   downstream channels and the watershed outlet?
5. Does OFE discretization change the frequency or magnitude of the response?
6. Which cases should become frozen openWEPP regression tests?

## Scenario Contract

Post-fire sites should use this scenario pairing:

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
analysis. Burned and unburned are analysis strata, not the primary causal
comparison. Within each frozen stratum, the causal unit is its baseline versus
the same scenario with one controlled mutation. Comparisons use the same
calendar events; return-period rankings are secondary summaries and never
substitute for event pairing.

The enriched discovery portfolio will retain the burned-base/unburned-Omni
pairing at every site. A later blind portfolio may admit a site with one or
more frozen reference scenarios when no defensible fire pairing exists. Any
such expansion changes the target population and must be preregistered before
results are examined.

## Staged Study Design

### Phase 1: Establish the Mechanics at Topanga

Topanga is the development and validation site for the protocol. Phase 1 is
limited to Gates 0–2 and has:

1. build an observationally instrumented WEPP executable from a pinned source
   commit;
2. prove that an unmodified build reproduces the established outputs;
3. prove that diagnostic logging does not alter normal outputs;
4. capture immutable event packets for the acceptance fixtures;
5. replay the selected and counterfactual methods outside the observational
   process;
6. distinguish legacy-input replay from harmonized-forcing diagnostics;
7. freeze the 1980 Ksat and 1986 canopy/cover reproducers; and
8. validate an inactive-parameter negative control.

Hill 106 and the February 14, 1980 Ksat pair are the first acceptance fixture.
The fixture must be self-contained and one-command reproducible. Its trace
must reproduce the operands and peaks reported in the
[instrumented Ksat diagnostic](../2026-08-07-topanga-2025-fire-peak-flow-analysis/artifacts/hill106-ksat-peakflow-diagnostic.md).

The broader implementation evidence and official WEPP documentation are
summarized in the
[stakeholder peak-flow report](../2026-08-07-topanga-2025-fire-peak-flow-analysis/artifacts/wepp-peak-flow-solver-documentation-and-topanga-evidence.md).

#### Phase 1 result

**Status: Gate 2.1 accepted on 2026-08-08. Phase 2A is authorized.**

The [Phase 1 work package](../../work-packages/20260808_peakflow_phase1/package.md)
contains the schemas, build manifests, parity evidence, immutable event
packets, and process-isolated replay reports. The observational build produced
byte-identical copies of all seven canonical Hill 106 outputs with tracing
actively enabled in both Ksat lanes. Its selected-method replay matched the
post-clamp production peak exactly for both lanes. The observer source is the
pushed WEPP-Forest commit `ea25ad79`.

The authoritative authorization and pilot exit criteria are recorded in the
[Gate 2.1 review disposition](../../work-packages/20260808_peakflow_gate21/artifacts/gate21-review-disposition.md).

The legacy `APPMTH` input has `v* = 1.3753` for Ksat 20 and `v* = 4.4017` for
Ksat 35, both outside the documented `v* ≤ 1` derivation range. Recomputing
the summary from the same post-surplus forcing passed to `HDRIVE` gives
`v* = 0.7449` and `0.9026`. This does not repair WEPP; it demonstrates that
legacy algorithm disagreement is mixed with inconsistent forcing summaries.

The frozen 1986 checks reproduce the `3.563 → 294.416 mm/h` canopy jump and
the `3.563 → 312.292 mm/h` ground-cover jump. Both remain
`mechanism_unresolved`. A version-9002 `ksatfac` mutation from `1.3` to `9.3`
produced byte-identical canonical outputs and passed as the inactive-parameter
negative control.

### Phase 2: Complete the Topanga Watershed Census

Phase 2 begins with the authorized
[Phase 2A multi-hillslope pilot](../../work-packages/20260808_peakflow_phase2a_pilot/package.md).
The pilot completed on 2026-08-09 and passed seven of its ten original exit
criteria. Its [exit report](../../work-packages/20260808_peakflow_phase2a_pilot/artifacts/phase2a-exit-report.md)
correctly withholds the original routing-coupled census. A subsequent
[study-design amendment](../../work-packages/20260808_peakflow_phase2a_pilot/artifacts/study-design-amendment-local-census.md)
retires routing criteria 5–7 as gates for the local census while preserving
them as failed pilot evidence.

The pilot nevertheless mechanism-traced the undisturbed Hill 106 1986 day-46
response: an `84.95×` APPMTH peak jump lies inside a Ksat bracket only
`8.54e-5 mm/h` wide and coincides with a surplus-assignment switch from
`positive_excess` to `storm`. This is a candidate forcing-construction defect,
not authorization for prevalence claims.

For the local census, mutate one hillslope per run and execute only its
full-history hillslope model and observer. Retain the target pass, event
ledger, mutation manifest, and candidate evidence. Do not execute the
watershed binary or retain all-channel output for every mutation.

Delivery is split into two work packages. The completed
[census-preparation package](../../work-packages/20260808_peakflow_topanga_census_prep/package.md)
extracted a site-independent engine, proved Phase 2A parity, and froze the
complete eligible Topanga trial plan without executing it. Its GO disposition
authorized the active
[full-census execution package](../../work-packages/20260809_peakflow_topanga_census_execution/package.md)
to consume the frozen plan and produce outcomes after preflight gates pass.

For mutations that expose a discontinuity, retain the local response and its
mechanism evidence:

```text
hillslope parameter mutation
    -> local hillslope hydrograph and PeakRO
    -> adaptive bracket and frozen-event replay
```

Selected routing experiments may later test downstream consequences after the
channel-output authority is reconciled. They are a separate sampled study and
do not gate local prevalence or mechanism results.

### Phase 3: Extend to Rain- and Snow-Dominated Sites

Phase 3 begins after the local Topanga census passes Gate 3. Add sites
incrementally under two preregistered portfolios:

- **enriched discovery:** known-positive cases such as Topanga, Palisades, and
  Stevens Canyon, used to discover and reproduce mechanisms; and
- **blind audit:** sites selected by declared hydrologic and provenance
  criteria before their peak anomalies are examined.

Report prevalence separately for the two portfolios. The initial combined
portfolio should include:

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

The homogeneous paired profiles must preserve, as closely as WEPP permits:

- the complete slope profile, total length, width, area, and relief;
- climate sequence and simulation dates;
- the complete hydraulic, soil, and management parameterization;
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

Here, *observational instrumentation* means a diagnostic WEPP executable that
captures internal operands without changing equations, control flow, shared
state, or canonical outputs. It executes the normally selected peak method
exactly once. Additional solver calls are not permitted inside this process.

The required architecture is:

```text
observational WEPP execution
    -> capture versioned, immutable event packet
    -> execute the normal selected solver exactly once
    -> preserve all normal WEPP outputs
    -> replay APPMTH and HDRIVE from the event packet
       in a separate process or standalone diagnostic executable
```

This isolation is required because `HDRIVE` overwrites shared COMMON-block
hydrograph arrays, time arrays, counters, and integration state. Snapshot and
restore inside WEPP is out of scope unless complete state restoration can be
audited and output parity demonstrated. The offline selected-method replay
must reproduce the production-selected peak; that is the completeness test for
the event packet.

Two counterfactual families must remain distinct:

1. **Legacy-input replay** supplies each method exactly the operands the legacy
   implementation provides. `HDRIVE` receives the post-`surdra` series, while
   `APPMTH` receives runoff, duration, and the legacy pre-insertion `remax`.
2. **Harmonized-forcing diagnostic** derives the approximate-method summaries
   from the same post-`surdra` forcing series supplied to `HDRIVE`. This is not
   legacy behavior; it tests algorithm disagreement after removing the
   inconsistent forcing summaries.

For every captured hillslope-event, the scalar packet must include:

```text
positive_excess_duration_s
surplus_assignment_duration_s
surplus_assignment_mode
surplus_depth_mm
surplus_added_rate_mm_h
remax_pre_surplus_mm_h
forcing_max_post_surplus_mm_h
tp2_s
selected_solver
```

`surplus_assignment_mode` distinguishes positive-excess duration, storm
duration, upstream duration, and the 24-hour fallback. It prevents the
shorthand `surdra/durre` from hiding which duration was actually used.

For `APPMTH`, also capture `vave`, `vstar`, `tstar`, `tc`, `qpstar`, equation
branch, documented-domain flags for `vstar` and `tstar`, and finite-result
status. For `HDRIVE`, capture the stopping condition, final routed-volume
fraction, iteration count, and whether an array or iteration limit was
reached. Common state includes precipitation and snow forcing, antecedent
layer water and saturation, hourly `ui_scrunf(ii)` when active, pre- and
post-reconciliation runoff, `ealpha`, friction, flow width, rill width, and
the complete pre- and post-surplus interval series.

## Versioned Data Contract

No single table is expected to hold scalar events, layers, or interval series.
Gate 0 requires versioned schemas for the core local grains. Routing schemas
apply only when the separate routing follow-up is executed:

| Dataset | Grain |
| --- | --- |
| Build manifest | one row per compiled executable |
| Run manifest | one row per executable/input run |
| Mutation manifest | one row per requested mutation |
| Event scalar ledger | run × hillslope × OFE × model day × solver-call ordinal |
| Layer-state ledger | event × soil layer |
| Event forcing series | event × forcing stage × interval |
| Routing response ledger (follow-up only) | mutation event × downstream reach |
| Hydrograph series (follow-up only) | routing response × timestamp |
| Site-selection manifest | one row per candidate or admitted site |
| Artifact-storage manifest | one row per authoritative large artifact |

Keys, units, nullability, enumerations, and schema versions must be explicit.
The mutation manifest records requested and realized values so clipping,
formatting, or input-file rounding cannot pass silently. The event key includes
a solver-call ordinal even when only one call is expected.

Baseline and mutation ledgers are outer-joined. A mutation may create or
remove runoff, so absence is represented with an explicit `event_present`
field and is never silently converted to numerical zero. Raw observations and
derived classifications remain separate.

## Event Classification

Every mutation is paired to its baseline by site, scenario, hillslope, and
date. Full-history sensitivity allows each mutation to generate its own
antecedent state. Every flagged case also receives frozen-event replay from an
immutable packet so forcing construction and solver response can be isolated.

Initial diagnostic flags are:

- **timing compression:** a small mutation strongly changes
  `surplus_added_rate_mm_h` or its assignment mode;
- **solver switch:** `tp(2)` crosses zero and changes the selected method;
- **legacy solver disagreement:** legacy-input replays differ materially;
- **harmonized solver disagreement:** methods differ materially after their
  summaries are derived from the same post-surplus forcing;
- **within-solver discontinuity:** peak changes abruptly without a method
  switch;
- **routing attenuation or amplification (follow-up only):** the downstream
  response is proportionally smaller or larger than the local response;
- **synchronization change (follow-up only):** outlet peak changes because
  tributary timing changes; and
- **unresolved:** recorded mechanics do not yet explain the response.

A small mutation is screened as a candidate anomaly when it causes any of the
following, subject to preregistered absolute floors for runoff, peak, surplus,
and their denominators:

- more than a 25% peak change with less than a 5% runoff change;
- more than a twofold peak change;
- a solver-method switch;
- more than a twofold change in assigned surplus rate; or
- reversal of the expected local response to Ksat or surface cover.

These thresholds organize review; they do not prove a discontinuity or define
physical correctness. Sign reversals are diagnostic only because saturated
systems need not be globally monotone in Ksat or cover. All continuous values
and all applicable flags are retained.

Each candidate receives an adaptive local bracket, frozen-event replay, and
separate review of forcing construction and solver response. Evidence state is
recorded as one of:

```text
screened
reproduced
locally_bracketed
mechanism_traced
confirmed_implementation_defect
physically_unresolved
```

The candidate anomaly census and confirmed-mechanism census are reported
separately.

## Required Outputs

The investigation will maintain:

1. versioned build, run, mutation, site-selection, and storage manifests;
2. normalized scalar, layer, and forcing datasets;
3. a candidate anomaly census by site, stratum, parameter, and mechanism;
4. a separately adjudicated confirmed-mechanism census;
5. paired plots of runoff ratio versus peak ratio;
6. plots of peak response versus assigned surplus rate and solver selection;
7. local hydrographs for representative events;
8. maps of flagged hillslopes; and
9. frozen input decks for openWEPP regression development.

Cross-site rates use explicit denominators: eligible mutation trials, paired
runoff-producing events, eligible hillslopes, and audited sites. Observations
within one hillslope or site are not treated as statistically independent.

## Reproducibility and Change Control

- Pin source commits and record compiler and version, optimization and
  floating-point flags, preprocessor definitions, linker and runtime
  libraries, operating system, architecture, instrumentation-patch hash,
  source-tree cleanliness, input-tree hash, and executable SHA-256.
- Preserve an unmodified reference build beside each diagnostic build.
- Define the canonical files and fields used for parity. Prefer byte equality;
  preregister tolerances and ignored metadata where byte equality is not
  deterministic.
- Keep every forced-method replay outside the observational WEPP process.
- Run complete climate histories so mutations generate their own antecedent
  states.
- Use frozen-event replay to adjudicate every screened candidate.
- Do not compare unmatched event dates as evidence of a mechanism.
- Record every input mutation as a machine-readable patch or manifest entry.
- Use inactive `kr` and version-9002 `ksatfac` mutations as negative controls;
  their manifests must prove the intended inactive token changed while
  hydrologic output did not.
- For a separate routing follow-up, assert that channels outside the declared
  downstream closure remain unchanged and verify volume consistency and
  hydrograph timestamps along the affected path.
- Store one complete baseline ledger per stratum. Local census mutation runs
  retain the target hillslope pass, observer ledger, and immutable manifest;
  do not retain all-channel or outlet output.
- Store large scalar data in partitioned Parquet and variable-length series in
  separately compressed storage. Commit schemas, manifests, compact fixtures,
  summaries, and content hashes rather than bulk output.
- Restore shared source worktrees after temporary diagnostic builds.

Internal reproducibility means authorized developers can rebuild the
restricted WEPP-Forest source and verify the executable. Public
reproducibility requires an external reviewer to rebuild and execute the
fixture from a public source tree such as DEP Windows WEPP or openWEPP. Every
result and fixture must state which level it satisfies. A binary hash alone
provides identity, not public rebuildability.

## Acceptance Gates

### Gate 0 — Protocol and Schemas

Pass when versioned schemas exist for builds, runs, mutations, scalar events,
interval forcing, site selection, and artifact storage. Requested and realized
mutation values must both be recorded. Routing-response schemas are required
only for a separate routing follow-up.

### Gate 1 — Instrumentation Safety

Pass when:

1. the unmodified pinned build reproduces the frozen reference output;
2. the observational build satisfies its declared non-diagnostic output-parity
   policy;
3. the captured event packet is immutable and versioned;
4. offline selected-method replay reproduces the normal selected peak;
5. counterfactual `HDRIVE` cannot mutate the observational process; and
6. legacy-input and harmonized-forcing results are separately labeled.

### Gate 2 — Topanga Acceptance Fixtures

Pass when:

- the compact 1980 Ksat-20/Ksat-35 pair is committed and one-command
  reproducible;
- its complete operand trace agrees with the existing diagnostic;
- the 1986 canopy and ground-cover fixtures reproduce their extreme responses
  and remain labeled `mechanism_unresolved`;
- an inactive-parameter control produces no hydrologic response; and
- all `APPMTH` domain flags and surface-return assignment branches are
  represented in the schema.

The 1980 fixture must include both input decks, `SHA256SUMS`, the exact input
diff, a complete build manifest, full-precision expected event values, and a
one-command checker. The checker must prove that exactly one intended soil
value differs.

```text
topanga-h106-1980-ksat/
├── README.md
├── SHA256SUMS
├── baseline-ksat20/runs/...
├── mutant-ksat35/runs/...
├── input-diff.txt
├── build-manifest.json
├── expected-event.json
└── run-and-check.sh
```

`expected-event.json` includes full-precision runoff before and after
reconciliation, `surdra`, `surpls`, both duration definitions, assignment
mode and rate, pre-insertion `remax`, post-insertion forcing maximum, `tp(2)`,
selected method, and every required replay peak.

### Gate 3 — Topanga Candidate Census

Pass when every eligible local trial has a terminal disposition, event pairing
uses outer joins, absent and zero events remain distinct, and selected
candidates receive local bracketing, frozen-event replay, and mechanism
classification. Routing closure and combined watershed experiments are not
Gate 3 requirements.

### Gate 4 — Cross-Site Work

Pass when enriched and blind portfolios are preregistered, at least one
independent rain-dominated site and one snow-influenced site satisfy the same
contract, schema changes are versioned, and every prevalence estimate names
its population and denominator.

### Gate 5 — OFE Experiment

Pass when the homogeneous single- and multiple-OFE pair preserves the complete
slope profile and hydraulic parameterization. OFE state and forcing use their
own table grains. The heterogeneous follow-up remains a separate experiment.

## Current Decisions

| Decision | Rationale |
| --- | --- |
| Start with Topanga | Hill 106 supplies an established acceptance fixture and known discontinuities |
| Complete mechanics before adding sites | Prevents inconsistent instrumentation and repeated forensic work |
| Treat burned and unburned as strata | Controlled mutations within a frozen scenario are the causal comparison |
| Retain burned base versus unburned Omni in the discovery portfolio | Preserves a consistent post-fire WEPPcloud context without conflating it with the mutation effect |
| Compare identical dates | Preserves storm and antecedent-state context |
| Mutate one hillslope first | Separates local calculation defects from watershed synchronization |
| Isolate solver replay by process | Prevents `HDRIVE` shared-state mutations from contaminating observational output |
| Separate legacy and harmonized replay | Distinguishes solver algorithms from inconsistent legacy forcing summaries |
| Include snow sites after Topanga | Tests a materially different water-input and soil-state regime without complicating initial development |
| Defer OFE comparison | OFE boundaries introduce additional coupling best studied after the single-profile mechanics are understood |
| Produce openWEPP fixtures, not a legacy repair | The legacy code lacks the isolation and regression coverage needed for a dependable repair effort |
| Cull routing from the census critical path | Local prevalence and mechanism questions can be answered without the unresolved cost and authority problems in watershed output |

## Immediate Next Steps

1. Complete execution-package compatibility, preflight, explicit-selection,
   dry-run, and security checkpoints against the frozen plan.
2. Execute all 1,088 eligible hillslope observer trials without watershed
   routing and reconcile every terminal.
3. Screen the outer-joined event ledger and publish local candidate prevalence.
4. Keep mechanism adjudication separate from screening and publish no
   downstream-impact
   claims.

## Related Investigations

- [Topanga 2025 fire peak-flow analysis](../2026-08-07-topanga-2025-fire-peak-flow-analysis/README.md)
- [Palisades fire peak-flow inversion](../2026-08-03-palisades-fire-peak-flow-inversion/README.md)
- [Stevens Canyon peak-flow inversion](../2026-08-03-stevens-canyon-peak-flow-inversion/README.md)

## Revision Log

| Version | Date | Changes |
| --- | --- | --- |
| 1.0 | 2026-08-08 | Established the Topanga-first multi-site audit, scenario contract, snow-site phase, and single- versus multiple-OFE follow-up. |
| 1.1 | 2026-08-08 | Incorporated the conditional planning review: isolated solver replay, dual replay semantics, normalized schemas, fixture requirements, evidence states, negative controls, storage policy, sampling portfolios, and acceptance gates. |
| 1.2 | 2026-08-09 | Culled watershed routing from the census critical path; authorized a local hillslope census and deferred downstream-impact claims to a separate sampled follow-up. |
| 1.3 | 2026-08-09 | Split delivery into a durable-engine and frozen-matrix preparation package followed by a separately authorized Topanga execution package. |
| 1.4 | 2026-08-09 | Recorded preparation GO and activated the separately gated execution package for the frozen 1,088-trial matrix. |
