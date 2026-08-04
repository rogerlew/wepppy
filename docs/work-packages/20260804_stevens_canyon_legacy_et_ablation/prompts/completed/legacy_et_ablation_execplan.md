# Run the Stevens Canyon burn matrix with legacy ET

This ExecPlan is a living document maintained according to
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Determine what happens to forest and post-fire evapotranspiration when WEPP's
Penman-Monteith routine, called PMET here, is not selected. The observable
result is a paired 100-year matrix for low-, moderate-, and high-severity fire
showing annual soil evaporation (`Es`), plant-side evapotranspiration (`Ep`),
residue evaporation (`Er`), total ET, burned-to-undisturbed total-ET ratio, and
`Es/ET`. This is a model-form ablation, not a proposed production default.

## Progress

- [x] (2026-08-04 00:24 UTC) Scaffolded the package and fixed its experimental
  contract.
- [x] (2026-08-04 00:31 UTC) Implemented an isolated runner that proves PMET is absent while preserving
  the hourly-water-balance and supporting sidecars.
- [x] (2026-08-04 00:33 UTC) Executed and validated 33 hillslope runs and retained compact annual results.
- [x] (2026-08-04 00:38 UTC) Produced a figure, sidecar, and result interpretation.
- [x] (2026-08-04 00:42 UTC) Removed temporary lanes, verified the source checkout, and closed the package.

## Surprises & Discoveries

- Observation: Legacy ET assigns the undisturbed forest zero `Es` and `Er`,
  placing approximately 324 mm/year entirely in `Ep`.
  Evidence: `legacy-et-ablation-summary.csv`.
- Observation: Median low- and moderate-severity total-ET ratios are 0.990 and
  0.997; switching model form changes partitioning without materially reducing
  annual ET.
  Evidence: `legacy-et-ablation-summary.csv`.
- Observation: High-severity median ET ratio is 0.862 and `Es/ET` is 0.501, so
  it misses both envelopes. No severity has a joint-pass year.
  Evidence: `legacy-et-ablation-annual.csv.gz`.
- Observation: A complete second 33-run execution reproduced both compact
  artifacts byte for byte.
  Evidence: `sha256sum -c` reported `OK` for the summary CSV and compressed
  annual CSV.

## Decision Log

- Decision: Run the undisturbed references through legacy ET as well as the
  burned inputs.
  Rationale: A ratio between a legacy burned run and a PMET undisturbed run
  would conflate burn severity with ET method.
  Date/Author: 2026-08-04 / Codex.
- Decision: Treat the absence of `pmetpara.txt` as the model-selection control.
  Rationale: `infile.for` selects the legacy `evap` routine when that file
  cannot be opened; an empty or malformed file is not an equivalent control.
  Date/Author: 2026-08-04 / Codex.
- Decision: Exclude H49 and H57 and exclude runoff from the objective.
  Rationale: Those hillslopes are unchanged non-forest controls, and the user
  requested that ET partitioning be resolved before runoff is interpreted.
  Date/Author: 2026-08-04 / Codex.

## Outcomes & Retrospective

The runner completed 33 valid 100-year simulations with no PMET announcement,
stderr, or malformed water-balance output. Removing PMET did not generate the
expected severity-dependent total-ET reduction and exposed an implausible zero
soil/residue evaporation partition for undisturbed forest. The package rejects
legacy ET as a production workaround and narrows the next step to a
forest-specific ET formulation or instrumentation study. No source or
production inputs changed; all temporary lanes were removed.

## Context and Orientation

The immutable source fixture is
`/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes`. It contains the
`burned`, `undisturbed`, and `high_severity` scenarios, plus the staged
`wepp_260803_hill` binary. Low severity comprises H50, H56, H58, H60, and H61;
moderate severity comprises H51-H55 and H59; high severity applies the
high-severity counterfactual to all eleven forest hillslopes. Areas are used as
weights within each severity class.

WEPP writes one `H*.wat.dat` file with 36,525 daily records for each 100-year
run. Total ET is defined as `Ep + Es + Er`. The diagnostic targets are low
severity: ET ratio `0.65-0.80` and `Es/ET` `0.15-0.30`; moderate: `0.50-0.70`
and `0.25-0.40`; high: `0.40-0.60` and `0.30-0.45`.

## Plan of Work

Add a standalone runner to the investigation artifacts. For each of the eleven
forest hillslopes, run undisturbed, burned, and high-severity inputs in an
isolated lane under
`/wc1/ablation/stevens-canyon-legacy-et-ablation-20260804`. Copy the `.run`,
`.man`, `.slp`, `.cli`, and `.sol` files plus `gwcoeff.txt`, `snow.txt`,
`wepp_ui.txt`, `chntyp.txt`, `tc.txt`, and `chan.inp`. Do not copy or create
`pmetpara.txt`. Capture model stdout and reject any run announcing the FAO
Penman-Monteith method. Validate every water-balance file before aggregating.

Write deterministic compressed annual data and a severity summary into the
investigation artifacts. Compare the legacy result to the fixed target matrix
and to the original PMET fixture result. Plot distributions for ET ratio and
`Es/ET`, plus median absolute annual components for burned and undisturbed
conditions. Document the figure with a same-stem Markdown sidecar and write a
plain-language result report.

## Concrete Steps

Run from `/home/workdir/wepppy`:

    .venv/bin/python docs/investigations/2026-08-03-stevens-canyon-peak-flow-inversion/artifacts/run_legacy_et_ablation.py
    .venv/bin/python docs/investigations/2026-08-03-stevens-canyon-peak-flow-inversion/artifacts/plot_legacy_et_ablation.py
    wctl doc-lint --path docs/work-packages/20260804_stevens_canyon_legacy_et_ablation

## Validation and Acceptance

All 33 invocations must exit zero with empty stderr, no PMET announcement, no
`pmetpara.txt` in the lane, and exactly 36,525 finite water-balance records.
Each severity must retain 100 paired annual records. The summary must report
medians and 10th-90th percentiles for ET ratio and `Es/ET`, the fraction of
years jointly inside both envelopes, and median absolute ET components. The
figure must have a Markdown sidecar that states the result and limitations.

## Idempotence and Recovery

The runner may replace only the explicitly named legacy-ablation work root.
It never writes into the fixture or `/workdir/wepp-forest_260430_baseline`.
Temporary lanes are removed after successful extraction. If interrupted, the
runner can be invoked again to rebuild all compact results from scratch.

## Artifacts and Notes

The experiment selects an already implemented WEPP model path; it does not
alter source, formulas, production parameters, or project data. No
parameterization ADR is required for this diagnostic package.

## Interfaces and Dependencies

Use the repository virtual environment, Python standard library, NumPy,
Matplotlib, and the staged WEPP binary. Add no dependency. The scripts and
outputs are investigation artifacts, not production interfaces.

Plan revision note (2026-08-04): Initial plan authored to make the paired
model-selection control, sidecar contract, scoring exclusions, and cleanup
requirements self-contained before execution.

Plan revision note (2026-08-04): Recorded the completed 33-run result, the
zero-`Es` undisturbed legacy behavior, target failures, byte-reproducibility,
and verified cleanup.
