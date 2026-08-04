# Execute the Palisades four-cell ET attribution experiment

This ExecPlan is a living document maintained under
`docs/prompt_templates/codex_exec_plans.md`. The required `Progress`,
`Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective`
sections must remain current.

## Purpose / Big Picture

The Palisades investigation found that undisturbed outlet hydrographs can peak
higher than burned hydrographs even at similar or lower event runoff volume.
This experiment determines whether the PMET soil-evaporation process materially
creates or amplifies that contrast. A reader can inspect four directly
comparable cells and see how switching only the ET routine changes annual and
antecedent `Es`, total ET, runoff, and soil storage in burned and undisturbed
land states.

## Progress

- [x] (2026-08-04 01:33 UTC) Transfer the standalone investigation into
  WEPPpy without nested Git metadata.
- [x] (2026-08-04 01:33 UTC) Define the factorial design, production read-only
  boundary, and cleanup contract.
- [x] (2026-08-04 01:45 UTC) Implement and smoke-test the reproducible runner;
  all four H1 cells passed the ET-selector and 16,802-row enriched-output gates.
- [x] (2026-08-04 01:54 UTC) Execute 278 hillslopes in each of four cells;
  all 1,112 runs passed.
- [x] (2026-08-04 01:58 UTC) Analyze annual and inversion-event antecedent
  responses.
- [x] (2026-08-04 02:00 UTC) Produce figures, sidecars, results narrative, and
  validation evidence.
- [x] (2026-08-04 02:00 UTC) Close the package and move this plan to
  `prompts/completed/`.

## Surprises & Discoveries

- Observation: The live Omni scenario directories were pruned of WEPP run and
  output files on 2026-05-13, while the base production run retains full input
  and water-balance files.
  Evidence: the undisturbed Query Engine catalog has no `H.wat.parquet`, and
  `/wc1/runs/up/upset-reckoning/_pups/omni/scenarios/undisturbed/wepp/runs` is
  empty.
- Observation: Canonical undisturbed management templates declare one
  simulation year even though their yearly section is reusable.
  Evidence: the first undisturbed smoke produced 366 rows; expanding the parsed
  management with `Management.build_multiple_year_man(46)` produced the
  required 16,802 rows.
- Observation: The first post-processing pass treated WEPP's calendar year as
  a one-based simulation year and failed the event join after all model runs
  had completed.
  Evidence: compact daily output initially began in year 3959. The retained
  daily values allowed an analysis-only correction without rerunning WEPP;
  corrected output spans 1980-01-01 through 2025-12-31.
- Observation: Reconstructed undisturbed PMET runoff closely matches the
  retained original Omni PASS series.
  Evidence: daily volume correlation is 0.9991; its record-total scaling ratio
  (1.0796) matches the burned replay control (1.0812).

## Decision Log

- Decision: Reconstruct undisturbed inputs from each base hillslope's original
  NLCD class, canonical undisturbed management template, and original soil file
  retained in the production `soils` directory.
  Rationale: This reproduces the Omni `remove_sbs(); landuse.build();
  soils.build()` intent without mutating or rerunning the production project.
  Date/Author: 2026-08-04 / Codex.
- Decision: Use the pinned `wepp_260803_hill` binary from the prior Stevens
  Canyon fixture and preserve `wepp_ui.txt` so enriched daily water balance is
  emitted.
  Rationale: The study requires full-profile soil water and comparable ET
  components, not watershed routing.
  Date/Author: 2026-08-04 / Codex.

## Outcomes & Retrospective

All 1,112 simulations passed and the runtime root was removed. PMET increases
burned `Es` partitioning, but also increases burned runoff and pre-event soil
storage. Its runoff effect is larger in undisturbed, yielding a -1.56 mm/year
difference-in-differences. PMET antecedent drying is rejected as a material
cause of the inversion; routed timing remains the leading mechanism.

## Context and Orientation

The production project is `/wc1/runs/up/upset-reckoning`. Its base state is
the burned SBS mosaic. It contains 278 single-OFE hillslope input sets in
`wepp/runs`, a `pmetpara.txt` file with `kcb=0.95` and `rawp=0.8`, and an empty
but required `wepp_ui.txt` sidecar that enables the enriched water-balance
build's full-depth columns. The investigation is now
`docs/investigations/2026-08-03-palisades-fire-peak-flow-inversion`.

A cell is one combination of land state and ET method. The four cells are
`burned_pmet`, `undisturbed_pmet`, `burned_legacy`, and
`undisturbed_legacy`. PMET is selected by the presence of `pmetpara.txt`;
legacy ET is selected by its absence. Each hillslope is run independently, so
there is no channel or watershed routing.

## Plan of Work

Create a package-local Python runner that stages one isolated hillslope lane at
a time below `/wc1/ablation/palisades-four-cell-et-20260803`. For burned cells,
copy the production `.man` and `.sol`; for undisturbed cells, select
`Old_Forest.man`, `Shrub.man`, or the matching developed template and pair it
with the original unmodified soil file identified by stripping the disturbance
suffix from `soils.parquet`. Keep `.run`, `.slp`, and `.cli` identical within
each hillslope quartet.

For PMET cells, install a complete 278-entry `pmetpara.txt` using the plant loop
present in each selected management. For legacy cells, verify it is absent.
Always copy `gwcoeff.txt`, `snow.txt`, `wepp_ui.txt`, `chntyp.txt`, `tc.txt`,
and `chan.inp`. Disable plot output to reduce temporary I/O without changing
water balance.

Validate every `H*.wat.dat` has exactly 16,802 finite daily rows and the
enriched full-profile columns. Aggregate by authoritative hillslope area while
the raw lane exists, then delete the lane. Write reproducible daily, annual,
summary, and flagged-event antecedent tables. Plot the four-cell ET partition,
PMET effect by land state, and event antecedent response, with a Markdown
sidecar beside every PNG.

## Concrete Steps

From `/workdir/wepppy`, run:

    .venv/bin/python docs/investigations/2026-08-03-palisades-fire-peak-flow-inversion/artifacts/four-cell-et/run_four_cell_et.py --smoke

Expect four successful H1 runs, with PMET marker presence matching the cell.
Then run the full matrix:

    .venv/bin/python docs/investigations/2026-08-03-palisades-fire-peak-flow-inversion/artifacts/four-cell-et/run_four_cell_et.py --workers 16

Finally lint package and result documentation:

    wctl doc-lint --path docs/work-packages/20260803_palisades_four_cell_et
    wctl doc-lint --path docs/investigations/2026-08-03-palisades-fire-peak-flow-inversion

## Validation and Acceptance

Acceptance requires 1,112 successful simulations; exact row counts; finite
values; correct PMET marker selection; all four cells in compact outputs; an
empty/absent runtime root after completion; an unchanged production run; and a
clean WEPP source checkout. The conclusion must distinguish a PMET effect on
runoff generation or antecedent storage from channel timing, which this
hillslope-only design cannot rerun.

## Idempotence and Recovery

The runner refuses to overwrite a non-empty runtime root unless `--resume` is
explicit. Each completed hillslope is aggregated before its lane is deleted.
If interrupted, remove only the exact runtime root named above or rerun with
`--resume`; never modify the production run. The runner records input hashes
so reconstruction is auditable.

## Artifacts and Notes

Results belong under the investigation, not the work package, because the
investigation owns scientific evidence. Package files own scope, execution
state, and handoff history.

## Interfaces and Dependencies

Use Python's standard library for orchestration, NumPy for array aggregation,
DuckDB for reading production Parquet metadata, and Matplotlib for figures.
Use `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/bin/wepp_260803_hill`
as the immutable binary. Do not modify `/workdir/wepp-forest_260430_baseline`.

## Revision Note

Updated 2026-08-04 after execution to record the smoke correction, all 1,112
successful runs, the recoverable calendar post-processing defect, validation
against retained Omni PASS output, and the completed scientific disposition.
