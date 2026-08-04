# Attribute the Stevens Canyon focal inversion

This ExecPlan is maintained according to
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this study, a reader can distinguish whether the year-34/day-203
undisturbed runoff excess was prepared by PMET demand, LAI partitioning,
surface-water limitation, or residue exposure. The evidence comes from current
binary-generated traces rather than inferred annual totals.

## Progress

- [x] (2026-08-04 03:08Z) Audited fixtures, source cleanliness, and existing hooks.
- [x] (2026-08-04 03:13Z) Created disposable sparse worktree and trace extension.
- [x] (2026-08-04 03:20Z) Built and proved same-binary observation-off parity.
- [x] (2026-08-04 03:24Z) Executed 26 paired replays and counterfactuals.
- [x] (2026-08-04 03:28Z) Generated figures, documented findings, and cleaned up.

## Surprises & Discoveries

- Observation: `evappm.for` already calls `wepp_observe_pmet`, but the trace
  omits the soil coefficient, water reduction, residue exposure, and available
  surface water needed for component attribution.
  Evidence: the hook records only `etorc` through realized `Ep`/`Es`.

- Observation: Burned antecedent `Es` exceeds undisturbed by 25.89 mm despite
  identical precipitation and 10.37 mm greater burned wetting.
  Evidence: `artifacts/results.json` and `event-trace-area-weighted.csv`.

## Decision Log

- Decision: Extend the opt-in trace rather than add a new behavior lane.
  Rationale: Observation-off execution remains numerically identical and the
  study can swap recorded equation terms offline.
  Date/Author: 2026-08-04 / Codex.

## Outcomes & Retrospective

The diagnostic trace attributes the burned soil-evaporation request to LAI
partitioning and residue exposure, not reference demand. The 25.89 mm excess
burned `Es` nearly closes against the 23.0 mm shallow-storage deficit and is a
material antecedent cause of the focal runoff inversion. Exclusive causation
still requires a layer-state restart/swap experiment.

## Context and Orientation

The focal event is simulation year 34, Julian day 203. H49-H61 form the full
contributing area above reach 173. `evappm.for` computes reference ET
(`etorc`), partitions demand using LAI (`etke`, `kcbcon`), limits soil
evaporation using surface water (`etkr`) and residue exposure (`eaj`, `kcmax`),
and reports realized `Es`. The source baseline is
`/workdir/wepp-forest_260430_baseline`; it must never be edited by this study.

## Plan of Work

Create a detached worktree under `/wc1/ablation`, patch the existing gated
PMET observer to record the missing intermediate terms, build `wepp_hill`, and
prove observation-off output parity against `wepp_260803_hill` on H59. Stage
paired burned and undisturbed H49-H61 capsules with all runtime sidecars,
enable observation, and retain only days 173-203 of year 34. Analyze actual
fluxes and all-order component swaps over demand, LAI partition, water
reduction, and residue exposure. Relate the resulting attribution to existing
layer-water and day-203 runoff outputs.

## Concrete Steps

Run from `/home/workdir/wepppy`:

    .venv/bin/python docs/work-packages/20260803_stevens_event_attribution/artifacts/run_event_attribution.py
    wctl doc-lint --path docs/work-packages/20260803_stevens_event_attribution

The runner owns worktree setup, build, fixture execution, artifact generation,
and cleanup; retrying it replaces only its `/wc1/ablation` workspace and
generated package artifacts.

## Validation and Acceptance

Require byte-identical H59 water-balance output with observation disabled,
26/26 successful observed runs, 31 PMET rows per treated hillslope, finite
component values, and exact reconstruction of the traced constrained-soil
coefficient path within documented limits. No conclusion may identify a term
as causal when the intervention is only an observational swap.

## Idempotence and Recovery

The source worktree is detached and disposable. Before deletion, save
`git diff --binary`, the base commit, build command, and binary SHA-256. Remove
the worktree with `git worktree remove`, prune metadata, and verify the baseline
checkout remains clean. Temporary run capsules may be deleted after compact
traces and manifests are retained.

## Artifacts and Notes

Store results under this package's `artifacts/` directory. Each PNG receives a
same-stem Markdown sidecar with caption, interpretation, limitations, and
provenance.

## Interfaces and Dependencies

Use the baseline fixed-form Fortran build and Python NumPy/Matplotlib analysis.
No production binary is vendored and no parameter default changes.

Revision note (2026-08-04): Initial executable study specification created.

Revision note (2026-08-04): Recorded complete paired execution, attribution,
validation, and worktree cleanup outcome.
