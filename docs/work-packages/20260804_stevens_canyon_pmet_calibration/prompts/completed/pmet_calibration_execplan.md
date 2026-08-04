# Calibrate PMET coefficients for post-fire forest severities

This ExecPlan is a living document maintained according to
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Determine whether the two coefficients supplied through `pmetpara.txt` can
produce credible post-fire evapotranspiration. The result will be a ranked,
reproducible calibration surface for low-, moderate-, and high-severity forest
managements. Success means finding `kcb` and `rawp` combinations near both the
annual `Es/ET` fraction and total-ET magnitude targets. A demonstrated failure
to reach both targets is also a useful result because it identifies a
structural limitation rather than encouraging arbitrary coefficient tuning.

## Progress

- [x] (2026-08-04 23:30 UTC) Scaffolded the work package and fixed its
  calibration contract.
- [x] (2026-08-05 00:05 UTC) Implemented and validated the isolated grid runner.
- [x] (2026-08-05 00:20 UTC) Executed 924 runs and retained 126 summaries and
  12,600 paired annual records.
- [x] (2026-08-05 00:30 UTC) Generated and visually inspected three
  severity-specific figures and sidecars.
- [x] (2026-08-05 00:40 UTC) Interpreted identifiability, closed the package,
  and verified clean source and repository states.

## Surprises & Discoveries

- Observation: `evappm.for` partitions the adjusted basal coefficient using
  `exp(-0.45 * LAI)`, so changing `kcb` scales both potential soil evaporation
  and potential plant-side ET before water stress and residue limits.
  Evidence: assignments to `kcbcon` and `etke` at lines 298-301.
- Observation: `rawp` enters the plant water-stress threshold through
  `RAW = rawpaj * TAW`; it does not directly enter the soil-evaporation
  coefficient.
  Evidence: `evappm.for` lines 414-425.
- Observation: Every severity's minimum-distance candidate occurs at
  `kcb=0.35`, the lower grid boundary, while `rawp` changes median ET ratio by
  only 0.01-0.03 at fixed `kcb`.
  Evidence: `pmet-calibration-summary.csv`.
- Observation: The high-severity response surface never intersects its
  `Es/ET` target; values range from about 0.528 to 0.626.
  Evidence: high-severity response surface and annual result table.

## Decision Log

- Decision: Use `kcb` values 0.35 through 0.95 at 0.10 increments and `rawp`
  values 0.30 through 0.80 at 0.10 increments.
  Rationale: the grid spans severe canopy-loss demand through the current 0.95
  value while keeping the coefficients within interpretable FAO-style bounds.
  Date/Author: 2026-08-04 / Codex.
- Decision: Score severity-specific, hillslope-area-weighted annual values over
  all 100 paired climate years.
  Rationale: this respects climate pairing and avoids selecting coefficients
  for the anomalous focal year alone.
  Date/Author: 2026-08-04 / Codex.
- Decision: Use H50, H56, H58, H60, and H61 for low severity; H51-H55 and H59
  for moderate severity; and the high-severity counterparts of all eleven
  treated forest hillslopes for high severity.
  Rationale: these are the actual fire-class assignments in the burned fixture;
  high severity is a counterfactual for the same forest area. H49 and H57 are
  unchanged controls and do not belong in fire-severity calibration.
  Date/Author: 2026-08-04 / Codex.

## Outcomes & Retrospective

The isolated runner completed 924 valid 100-year hillslope runs with no stderr
or malformed water-balance output. Low severity approached both targets only
at `kcb=0.35`, `rawp=0.80`, and only 4% of paired years passed jointly.
Moderate severity retained excessive total ET. High severity retained excessive
soil evaporation at every coefficient pair. The result rejects `kcb` and
`rawp` as sufficient controls for the severity target matrix. No source,
production input, or production parameter default changed; temporary lanes
were removed after extraction.

## Context and Orientation

The source fixture is
`/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes`. Its `burned`
scenario supplies low- and moderate-severity management and soil inputs; its
`high_severity` scenario supplies high-severity inputs; and `undisturbed`
supplies paired reference outputs. Each `H*.wat.dat` contains 36,525 daily rows
covering 100 climate years. Model ET is `Ep + Es + Er`, where `Ep` is
plant-side ET, `Es` is soil evaporation, and `Er` is residue evaporation.

The target matrix is low severity: ET ratio 0.65-0.80 and `Es/ET` 0.15-0.30;
moderate: 0.50-0.70 and 0.25-0.40; high: 0.40-0.60 and 0.30-0.45. Magnitude
targets are calculated per year from the paired undisturbed ET rather than from
one fixed illustrative annual depth.

## Plan of Work

Add a standalone runner under the investigation `artifacts` directory. For
each severity and grid point it will create an isolated temporary lane under
`/wc1/ablation`, copy only required hillslope inputs and runtime sidecars,
rewrite every PMET record to the candidate coefficients, run
`wepp_260803_hill`, validate water-balance output, and aggregate annual ET by
hillslope area. Parallel workers may execute independent hillslopes. Compact
CSV results and figures belong in the investigation; bulk lane outputs remain
outside Git and are removed by the runner after successful parsing.

Rank candidates by normalized distance to the central ET ratio and `Es/ET`
targets, with an additional penalty for medians outside their envelopes.
Report absolute median `Ep`, `Es`, and ET and the percentage of paired years
inside both envelopes. The ranking must not include runoff.

## Concrete Steps

Run from `/home/workdir/wepppy`:

    .venv/bin/python docs/investigations/2026-08-03-stevens-canyon-peak-flow-inversion/artifacts/run_pmet_calibration.py
    .venv/bin/python docs/investigations/2026-08-03-stevens-canyon-peak-flow-inversion/artifacts/plot_pmet_calibration.py
    wctl doc-lint --path docs/work-packages/20260804_stevens_canyon_pmet_calibration

## Validation and Acceptance

Every candidate must contain 100 finite annual values for each target metric.
Every WEPP invocation must exit zero with empty stderr and a 36,525-row water
balance. Figures must show the ET-ratio and `Es/ET` response surfaces for each
severity and mark the target box and best candidate. Each figure needs a
same-stem Markdown sidecar. The final report must state whether any candidate
meets both envelopes and whether `kcb` and `rawp` are separately identifiable.

## Idempotence and Recovery

The calibration root is
`/wc1/ablation/stevens-canyon-pmet-calibration-20260804`. The runner may safely
replace only this explicitly named directory. It never writes to the source
fixture or `/workdir/wepp-forest_260430_baseline`. Compact repository artifacts
are deterministic and may be regenerated. If interrupted, rerun the runner;
completed compact rows may be recomputed rather than trusted from partial
lanes.

## Artifacts and Notes

This is experimental calibration, not a production parameter-default change.
No ADR is required unless a later package changes the production lookup or
formula. Candidate values are hypotheses until checked against external
observations.

## Interfaces and Dependencies

Use the repository virtual environment, Python standard library, NumPy,
Matplotlib, and the staged `wepp_260803_hill` binary. Add no dependency. The
runner and plotter are investigation artifacts, not production APIs.
