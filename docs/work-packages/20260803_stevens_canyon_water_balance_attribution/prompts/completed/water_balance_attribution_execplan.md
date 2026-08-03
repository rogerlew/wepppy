# Attribute the Stevens Canyon hillslope water balance

This ExecPlan is a living document maintained according to
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Explain why the undisturbed scenario can be flashier than the burned scenario
by decomposing their existing hillslope water balances. A reader will be able
to inspect one paired figure per hillslope and see whether surface runoff,
subsurface lateral flow, deep percolation, or evapotranspiration carries the
difference without rerunning WEPP.

## Progress

- [x] (2026-08-03 23:00 UTC) Confirmed paired 100-year daily water-balance
  outputs exist for H49-H61.
- [x] (2026-08-03 23:20 UTC) Parsed and validated 36,525 daily rows for every
  scenario/hillslope file and matching paired calendars.
- [x] (2026-08-03 23:30 UTC) Generated and visually inspected 13 paired year-34
  figures and Markdown sidecars.
- [x] (2026-08-04 02:30 UTC) Summarized focal-event and antecedent-window attribution.
- [x] (2026-08-04 02:40 UTC) Validated documentation and selected a
  process-instrumented ET/runoff-threshold study as the next milestone.
- [x] (2026-08-04 00:10 UTC) Traced active `evappm` dynamics and identified
  exponential LAI partitioning, reinforced by residue exposure, as the leading
  driver of the soil-evaporation contrast.
- [x] (2026-08-04 00:35 UTC) Specified severity-indexed annual total-ET and
  `Es/ET` envelopes with `Ep` derived by closure.
- [x] (2026-08-04 01:35 UTC) Added and ran an additive canonical high-severity hillslope scenario for
  the forest-derived hillslopes, retaining unchanged non-forest controls.
- [x] (2026-08-04 02:30 UTC) Produced a reproducible, area-weighted cross-hillslope attribution for
  reaches 169, 172, and 173 and classify undisturbed-runoff-excess days over
  the full record.

## Surprises & Discoveries

- Observation: Existing `H*.wat.dat` files already contain `Q`, `Ep`, `Es`,
  `Er`, `Dp`, and `latqcc` for all 36,525 days.
  Evidence: each paired H49 file has 36,553 lines including its header.
- Observation: The active dual crop coefficients sum to `kcbadj` before stress
  constraints, so declining LAI transfers potential ET from plants to soil.
  Evidence: H59 `etke/kcbadj` changes from about 0.00477 undisturbed to 0.517
  burned because LAI changes from 11.875 to 1.466.
- Observation: A transpiration water accumulator assigns from `wfevp` at the
  root boundary instead of its own prior value.
  Evidence: `evappm.for` uses `wftrp = wfevp + ...`; this is recorded as a
  separate code-risk hypothesis, not yet a confirmed defect.

## Decision Log

- Decision: Treat precipitation and rain-plus-melt as input lines rather than
  members of the outgoing-flux stack.
  Rationale: stacking inputs with outputs would visually imply that they are
  additive parts of one quantity.
  Date/Author: 2026-08-03 / Codex.
- Decision: Use common axes for burned and undisturbed panels and show
  simulation year 34 with day 203 marked.
  Rationale: this makes scenario magnitudes directly comparable while retaining
  antecedent seasonal context around the inversion.
  Date/Author: 2026-08-03 / Codex.
- Decision: Treat `Ep` as plant-side ET rather than pure transpiration and
  derive its calibration target from total ET, `Es`, and `Er`.
  Rationale: the active water-balance path charges live-canopy interception
  evaporation against the `Ep` budget, so direct comparison with sap-flow
  transpiration would mix definitions.
  Date/Author: 2026-08-03 / Codex.
- Decision: Build high severity as a third scenario from the undisturbed
  fixture, changing both management and soil only for H50-H56 and H58-H61.
  Preserve H49 (shrub/scrub) and H57 (deciduous forest) as byte-identical
  controls rather than silently changing their land-cover class.
  Rationale: this tests the canonical Disturbed forest-high-severity treatment
  while retaining a clean comparison boundary and avoiding a new assumption
  about how the two non-forest classes should burn.
  Date/Author: 2026-08-04 / Codex.
- Decision: Retain canonical `ksflag=0`, `ksatadj=1`, `ksatfac=100`, and
  `ksatrec=0.3` in the high-severity fixture soils.
  Rationale: the `wepp-forest` forest-specific path applies the
  saturation-dependent conductivity calculation when `ksatadj=1`; it does not
  require a study-local `ksflag=1` override.
  Date/Author: 2026-08-04 / Roger and Codex.

## Outcomes & Retrospective

The study now includes a validated third high-severity scenario. All 13 runs
produced 36,525 daily water-balance rows, full-depth graphics output, and empty
stderr logs. The 13 figure/sidecar pairs were regenerated as three-panel
comparisons. The source checkout remained clean. The initial fixture
unnecessarily overrode `ksflag`; correcting it exposed an important distinction
between WEPP's general internal Ksat flag and the forest-specific `ksatadj`
path. The fixture now preserves the canonical input.

The completed attribution shows that surface runoff carries the focal
inversion while antecedent lateral flow is negligible. Undisturbed runoff
excess occurs on only 21 days above reach 173. The clean high-severity
comparison has a median paired annual ET ratio of `0.877` and misses the
provisional `0.40-0.60` target in every year, while median `Es/ET` is `0.521`.
The next package should instrument the ET partition and runoff threshold
directly.

## Context and Orientation

The paired replay root is
`/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes`. Burned and
undisturbed outputs are under their respective `wepp/output` directories.
H49-H61 comprise the complete contributing hillslope set for channel WEPP_ID
173, including the nested sets for 169 and 172. `H*.wat.dat` is a daily table;
all fluxes are depths in millimeters over the hillslope.

Surface runoff is `Q`. Lateral subsurface flow is `latqcc`. Deep percolation is
`Dp`. The evapotranspiration components are plant transpiration `Ep`, soil
evaporation `Es`, and residue evaporation `Er`. A stacked outgoing-flux plot is
descriptive accounting, not proof that one component caused a routed peak.

## Plan of Work

Add an analysis script under the existing investigation's `artifacts`
directory. It will parse the fixed whitespace table, enforce one row per day
and matching scenario calendars, generate one two-panel PNG for every
hillslope, and write a same-stem Markdown sidecar. Each sidecar will contain
day-203, preceding 7-day, preceding 30-day, and year-34 totals. Add an index
linking the figures and summarize what the visual set can and cannot establish.

Complete the package with an area-weighted analysis over the fixed contributing
hillslope sets. Report focal-event and antecedent-window fluxes, 100-year annual
means, and counts and composite flux differences for days when undisturbed
daily runoff exceeds burned. Daily hillslope output cannot diagnose subdaily
flashiness, so keep channel peak-timing conclusions separate.

## Concrete Steps

Run from `/home/workdir/wepppy`:

    .venv/bin/python docs/investigations/2026-08-03-stevens-canyon-peak-flow-inversion/artifacts/plot_hillslope_water_fluxes.py
    wctl doc-lint --path docs/investigations/2026-08-03-stevens-canyon-peak-flow-inversion

The script must report 13 generated figure/sidecar pairs and no calendar or
finite-value failures.

## Validation and Acceptance

Each H49-H61 figure must have exactly three panels, a shared y-axis, six stacked
outgoing fluxes, precipitation and rain-plus-melt input lines, and a day-203
marker. The panels represent burned, undisturbed, and high severity. Each
sidecar must define units and report scenario totals. All source
files must have 36,525 unique daily rows, and paired calendars must match.

## Idempotence and Recovery

The plotting script overwrites only its named figure and sidecar outputs. It
reads existing model results and never modifies run inputs or production data.
Rerunning it is safe. Remove generated files only by their explicit H49-H61
names if the visualization design changes.

The high-severity fixture extension is additive. It writes only beneath the
fixture's `high_severity` directory and leaves the existing burned and
undisturbed scenarios untouched. Recovery consists of removing that explicitly
named directory. Validation must show identical climate, slope, run controls,
and required sidecars, byte-identical H49/H57 management and soil controls,
36,525 daily water-balance rows per run, full-depth graphics output, and empty
WEPP stderr logs. This experiment changes no production parameter defaults and
therefore requires no parameterization ADR.

## Artifacts and Notes

The source data were created by the previously documented hillslope replay and
already include the `wepp_ui.txt` hourly-water-balance sidecar. No watershed
execution is part of this package.

## Interfaces and Dependencies

Use the repository virtual environment, Python standard library, NumPy, and
Matplotlib. Add no dependency. The script is a command-line artifact with no
production API surface.

Revision note (2026-08-03): Initial plan created for existing-output
water-balance visualization and attribution.
