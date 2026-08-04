# Execute the Stevens–Palisades peak-Es counterfactual decomposition

This ExecPlan is a living document maintained according to
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

This study will replace the qualitative explanation for Stevens Canyon's much
larger peak soil evaporation with reproducible measurements. A reader will be
able to rerun the hillslope analysis and see how the observed cross-site peak
gap changes under perfect hillslope synchronization and under matched
surface-water and vegetation-exposure conditions.

## Progress

- [x] (2026-08-04 02:40Z) Inventory prior fixtures, binary, outputs, and sidecars.
- [x] (2026-08-04 02:42Z) Built and smoke-tested the reproducible runner.
- [x] (2026-08-04 02:45Z) Executed the full burned-PMET hillslope experiment.
- [x] (2026-08-04 02:48Z) Generated tables, figure, sidecar, and interpretation.
- [x] (2026-08-04 02:49Z) Validated artifacts, updated both investigations, and closed.

## Surprises & Discoveries

- Observation: Stevens retained individual daily outputs, whereas Palisades
  retained only an area-weighted daily series.
  Evidence: the prior four-cell runner deleted temporary per-hillslope lanes.

- Observation: The canonical area-weighted peak ratio is 1.2836, not eight.
  Evidence: Stevens peaks at 4.9588 mm/day and Palisades at 3.8633 mm/day.

- Observation: Perfect synchronization is a negative explanation.
  Evidence: synchronization efficiencies are 0.957 Stevens and 0.976
  Palisades; the bound increases rather than closes the site gap.

## Decision Log

- Decision: Rerun only the Palisades burned-PMET cell and parse the retained
  Stevens burned cell.
  Rationale: This is the minimum computation needed for a spatial peak bound
  and preserves the exact prior parameterization.
  Date/Author: 2026-08-04 / Codex.

- Decision: Do not alter WEPP source or production parameter files.
  Rationale: The requested decomposition is diagnostic; parameter mutation
  would introduce calibration effects and require an ADR.
  Date/Author: 2026-08-04 / Codex.

## Outcomes & Retrospective

The work package reproduced both sites, rejected the eightfold premise, and
bounded synchronization exactly. Stevens' remaining 1.28-fold peak difference
coincides with about twice the realized high-day `Ep + Es` throughput and a
wetter upper layer. Palisades has the larger soil fraction, so cross-site PMET
partitioning is not the primary cause. No source or production tree changed.

## Context and Orientation

`Es` is daily soil evaporation in millimeters. Stevens outputs live under
`/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/burned`. Palisades
inputs are reconstructed by `docs/investigations/2026-08-03-palisades-fire-peak-flow-inversion/artifacts/four-cell-et/run_four_cell_et.py`.
Both use the vendored `wepp_260803_hill` executable. An area-weighted peak can
be smaller than the weighted sum of each hillslope's own maximum when those
maxima occur on different days; the latter is the perfect-synchronization
upper bound.

## Plan of Work

Create a package-local Python runner that imports the proven Palisades fixture
construction, executes its burned-PMET cell while retaining arrays in memory,
parses every Stevens burned water-balance file, and validates calendars and
finite values. Compute actual area-weighted peaks, individual maxima, their
timing dispersion, perfect-synchronization bounds, and peak-day precipitation,
rain-plus-snowmelt, soil water, and ET partition. Join twice-monthly element
states to characterize LAI and dead biomass around peak days. Write compact
CSV/JSON evidence and figures with explanatory sidecars.

## Concrete Steps

From `/home/workdir/wepppy`, run:

    .venv/bin/python docs/work-packages/20260803_stevens_palisades_es_counterfactual/artifacts/run_counterfactual.py --smoke
    .venv/bin/python docs/work-packages/20260803_stevens_palisades_es_counterfactual/artifacts/run_counterfactual.py --workers 16
    wctl doc-lint --path docs/work-packages/20260803_stevens_palisades_es_counterfactual

The smoke run must validate H1 and H59. The full run must report 278 Palisades
and 13 Stevens hillslopes and produce nonempty finite result tables.

## Validation and Acceptance

Acceptance requires exact reproduction of the prior Palisades area-weighted
maximum within output precision, an independently calculated Stevens maximum,
and identities showing that each actual aggregate peak does not exceed its
perfect-synchronization bound. Every PNG must have a same-stem Markdown file
with caption, interpretation, limitations, and provenance.

## Idempotence and Recovery

Temporary lanes are confined to
`/wc1/ablation/stevens-palisades-es-counterfactual-20260804` and are removed in
a `finally` block. Re-execution replaces only generated package artifacts. No
WEPP source tree is changed, so no source cleanup is required.

## Artifacts and Notes

Results will be written under this package's `artifacts/` directory. Generated
daily data will be gzip-compressed and deterministic where practical.

## Interfaces and Dependencies

Use Python's standard library plus NumPy and Matplotlib already present in the
WEPPpy virtual environment. Reuse `load_hills`,
`prepare_undisturbed_managements`, and `run_hill` from the prior Palisades
runner rather than duplicating fixture reconstruction rules.

Revision note (2026-08-04): Initial executable specification created to turn
the qualitative cross-site explanation into bounded, reproducible evidence.

Revision note (2026-08-04): Recorded completed execution, the failed eightfold
reproduction, and the negative synchronization counterfactual.
