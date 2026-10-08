# Run PRISM-localized stochastic dewpoint experiment

This living plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Determine whether location-matched PRISM normals correct the dry station forcing found in the preceding stochastic study, and whether that changes evidence for a dewpoint clipping option. Deliver reproducible research results without changing production behavior.

## Progress

- [x] (2026-10-08) Register fixed sites, seeds, model inputs, and localization policy.
- [x] (2026-10-08) Retain all 117 monthly/annual rows for nine cells; January precipitation matches downloaded M4 grid to 0.0051 mm.
- [x] (2026-10-08 21:26 UTC) Generate 90 climates, verify exact seed replay, complete 180 WEPP cases.
- [x] (2026-10-08 21:34 UTC) Validate 2,344,980 daily rows, independently recalculate 792 metrics, inspect figures and publish findings.

## Surprises & Discoveries

The existing localization modifies precipitation and temperature but retains station dewpoint, radiation, wind, precipitation variability, and storm intensity parameters. These are limitations to assess, not implicit authorization to recalibrate. The production wet-day formula warns on zero station wet-after-wet probability and restores original monthly probabilities; this valid boundary is preserved. Initial study validation incorrectly required strictly positive probabilities and was corrected before generation.

## Decision Log

2026-10-08: Use the established `par_mod` wet-day adjustment and retain station humidity parameters to evaluate existing localization faithfully. The user explicitly requested PRISM location matching after the station-only study showed forest precipitation at 22–37% of GridMET. Sample current normals at nearest native cells to follow the user's caching preference. Compare synthetic seasonal distributions, not calendar-weather pairs.

## Outcomes & Retrospective

Completed all registered runs and validation. Forest precipitation moved from 22–37% to 90–102% of prior GridMET; full-record generated precipitation matches PRISM within −2.4% to +1.4%. Clipping improves seasonal RMSE in 36/36 pooled comparisons but annual bias in only 6/36. Retain production behavior. Results and limitations, including 69/90 generator quality diagnostics and retained station humidity, are recorded in `artifacts/results.md`. No production or UI changes.

## Context and Orientation

`docs/work-packages/20261008_stochastic_dewpoint/artifacts/study.py` provides generation, pairing, execution, verification, and analysis routines. The closed `20261008_dewpoint_openet/artifacts` package supplies nine hillslope fixtures, input hashes, and 36 cached OpenET series. Histories span 1980–2024, 2000–2024, or 1986–2022. Ten seeds 1001–1010 provide seven synthetic assessment years per seed after at least 16 spinup years. `wepppy/climates/cligen/cligen.py:par_mod` defines localization; current PRISM normals cover 1991–2020, whereas OpenET references 2016–2022. Different periods must be explicit.

## Plan of Work

First acquire PRISM precipitation and minimum/maximum temperature normals at the nine native grid cell centers and retain raw request/response metadata. Then adapt the prior standalone driver in this package's `artifacts/study.py` to use one localized parameter file per hill. Preserve other station rows and the pinned CLIGEN/WEPP executables. Run native and floored dewpoint copies with identical seeds and all non-dewpoint daily tokens. Finally calculate generated precipitation relative to PRISM and GridMET, 12-month ET climatology errors and within-month distribution distances against four OpenET products. Include generator diagnostics and seed variation in interpretation.

## Concrete Steps

From `/home/workdir/wepppy`, use `PYTHONPATH=. .venv/bin/python docs/work-packages/20261008_prism_stochastic_dewpoint/artifacts/study.py` with phases `prepare`, `run`, `verify`, and `analyze`. Acquire normals before prepare. Keep large outputs under `/home/workdir/wepppy-scratch/prism-stochastic-dewpoint-20261008`. Each phase retains machine-readable evidence; successful verify must report 180 cases and 2,344,980 finite daily water-balance rows. Lint package documents with `wctl doc-lint --path docs/work-packages/20261008_prism_stochastic_dewpoint`.

## Validation and Acceptance

Require finite complete normals, exact native grid identities, localized parameter readback, unchanged nonlocalized rows, 90 distinct generated climate series, deterministic replay, successful WEPP termination, full calendars, precipitation readback, output hashes, unchanged nonclimate fixtures, and exact treatment isolation. Inspect all CLIGEN logs even when exit status is zero. Independently check result calculations and visually inspect figures. Acceptance is a supported scientific conclusion including limitations, not a required direction of effect.

## Idempotence and Recovery

Cache raw normals and reuse unchanged files only after hash validation. Preserve failed outputs and diagnostics. Resume generation from validated files and completed model cases; do not overwrite frozen manifests or source project files. This package is additive and does not clone whole projects.

## Artifacts and Notes

Retain manifests, localized stations, compressed generated climates, execution records, quality diagnostics, CSV summaries, plots, and a concise results document. Hash retained files in an artifact index. Reuse the prior OpenET cache without accessing credentials.

## Interfaces and Dependencies

Use existing Python NumPy, Pandas, SciPy, Requests, and Matplotlib installations and pinned CLIGEN 5.323-k10.1 and WEPP 260803 hill executables. No new dependencies. Public PRISM point extraction is the sole new external data source.

Initial revision 2026-10-08 UTC: registered authorized location-matched follow-up.

Revision 2026-10-08: normals acquired; production parameter algorithm executes directly with cached data and stops explicitly before its generator boundary.

Final revision 2026-10-08 21:34 UTC: completed artifact and independent result validation. Seasonal improvements do not establish better annual ET totals. A future humidity-normal treatment is separate research.
