# Palisades Four-Cell ET Attribution

**Status:** Closed 2026-08-04
**Timezone:** UTC
**Security impact:** none

## Overview

Determine whether WEPP-forest's `pmetpara.txt`-selected Penman-Monteith routine
materially contributes to the Palisades burned-versus-undisturbed peak-flow
inversion. The study runs the same production-derived hillslopes in a two by
two matrix: burned versus undisturbed land state, each with PMET versus legacy
ET.

## Objectives

- Reconstruct paired burned and undisturbed hillslope inputs for all 278
  `upset-reckoning` hillslopes without running watershed routing.
- Execute all four cells with the pinned `wepp_260803_hill` binary and full
  daily water-balance output.
- Quantify annual `Es`, `Ep`, `Er`, total ET, runoff, and full-profile soil
  water, including antecedent windows for the previously flagged inversions.
- Separate the land-state effect, ET-method effect, and their interaction.

## Scope

The production run under `/wc1/runs/up/upset-reckoning` is read-only. Runtime
lanes are isolated below `/wc1/ablation/palisades-four-cell-et-20260803` and
are deleted after each output is validated and aggregated. The experiment does
not alter WEPP source, production parameter defaults, or project state.

Watershed/channel execution and parameter calibration are out of scope. This
is an attribution experiment, not a proposal to use legacy ET operationally.

## Success Criteria

- [x] All 1,112 hillslope simulations complete with finite 16,802-row water
  balance files.
- [x] PMET selection is positively verified in PMET cells and excluded in
  legacy cells.
- [x] Compact daily, annual, event-window, and summary artifacts are written.
- [x] Every figure has a same-stem Markdown sidecar.
- [x] Runtime lanes are removed and both source and production trees remain
  unchanged.

## Parameterization ADR Gate

- **Parameterization change present:** no
- **ADR required:** no
- **Decision provenance captured:** yes; user-requested diagnostic experiment
  on 2026-08-03 Pacific time, executed by Codex.

## Security Impact and Review Gate

- **Security impact triage:** none
- **Dedicated security review required:** no
- **Triage rationale:** local, read-only production-derived scientific inputs;
  no service, authentication, secret, or public attack-surface changes.

## Related Packages

- **Investigation:** [Palisades peak-flow inversion](../../investigations/2026-08-03-palisades-fire-peak-flow-inversion/README.md)
- **Related:** [Stevens Canyon legacy-ET ablation](../20260804_stevens_canyon_legacy_et_ablation/package.md)
- **Related:** [Stevens Canyon PMET calibration](../20260804_stevens_canyon_pmet_calibration/package.md)

## Deliverables

Results will live under the Palisades investigation's `artifacts/four-cell-et`
and `figures/four-cell-et` directories. The active execution plan and package
tracker provide the reproducibility and cleanup contract.

## Closure Notes

**Closed:** 2026-08-04

All 1,112 simulations passed. PMET increased burned median annual `Es` by
25.77 mm and undisturbed `Es` by 20.43 mm, but increased runoff in both states
and increased undisturbed runoff more. The runoff difference-in-differences was
-1.56 mm/year, opposite the proposed mechanism. Flagged-event antecedent soil
storage was also higher, not lower, with PMET. The experiment therefore rejects
PMET antecedent drying as a material cause of the Palisades peak inversion.

The full result is [documented in the investigation](../../investigations/2026-08-03-palisades-fire-peak-flow-inversion/artifacts/four-cell-et/results.md).
