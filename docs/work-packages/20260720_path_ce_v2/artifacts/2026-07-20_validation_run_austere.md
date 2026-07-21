# Validation Run Designation — austere-inaction

**Date**: 2026-07-20 23:55 UTC
**Evidence class**: Executional — Jackson's unmodified pipeline (`4e3b4a6`) run end-to-end on this run's raw parquet in the pinned scratch venv (pandas 2.2.2, PuLP 3.3.0/CBC).
**Designated by**: Roger — `https://wc.bearhive.duckdns.org/weppcloud/runs/austere-inaction/disturbed9002_wbt/`, local dir `/wc1/runs/au/austere-inaction`.

## Why this run

First local run with **full per-treatment Omni contrast coverage**: scenarios + outlet contrasts for all of `mulch_15_sbs_map`, `mulch_30_sbs_map`, `mulch_60_sbs_map` (plus `sbs_map` baseline and `undisturbed`). Every other local run carries `mulch_60` contrasts only. Grouped-contrast mode (wbt backend), psv present (24 ids), 71 hillslopes, 3 treatable contrast groups — solves are instant, ideal for Phase 2/5 end-to-end validation.

## What ran (all unmodified upstream code)

`prepare_ce_and_plot_data()` on raw run parquet → 3×63 final_df (contrast_id schema, full Sddc column set, outlet scalar 48.3 t). `ce_select_sites_flexible()` goldens in `goldens/solver_goldens_austere.json` (+ `prepared_frame_austere.parquet`, generator `make_goldens_austere.py`):

- (sdyd 15, sddc 48.3) → primary optimal, empty selection (threshold already met), cost $0
- (sdyd 15, sddc 48.2) → primary optimal, group 12 @ 0.5 t/ac, cost $207,714
- (sdyd 15, sddc 48.0) → primary infeasible → secondary, group 12 @ 2 t/ac, reduction 0.1 t

## Findings

1. **psv ids legitimately exceed contrasts.out ids.** The psv defines 24 contrasts (8 groups × 3 treatments); Omni skipped 15 as `landuse_unchanged` (mulching doesn't alter unburned groups), leaving ids 10–18 in `contrasts.out.parquet`. Phase 2 precondition validation must NOT treat psv ids absent from contrasts.out as an error — per-treatment coverage means each configured treatment scenario appears among completed contrasts, not that every psv id has rows.
2. **Grouped-mode severity is dominant-landuse-based and can be unmapped.** Group severity comes from the most frequent landuse code by row count (largest code wins ties); these groups are dominated by unburned codes (42/71), so group `Burn severity` lands in the unmapped class even though members burned (106/118). A burn-severity filter here would exclude everything. Faithful upstream behavior; UI copy should caveat the severity filter in grouped mode.
3. **Force-exclusion rule dominates this fixture.** Groups 15 and 18 have all-negative Sdyd reductions (mulch marginally increases modeled yield on these near-zero-erosion groups), so upstream forces them untreated — even though group 18 holds the largest outlet reduction (0.3 t @ mulch_60). Max achievable Sddc reduction is therefore 0.1 t against a 48.3 t baseline; primary is feasible only at `sddc_threshold ≥ 48.2`. Faithful preserved behavior; validation thresholds must be chosen in that window.
4. **Parquet preserves list-typed columns CSV would stringify.** `final_df` carries `topaz_ids` / `topaz_ids_all` as arrays; a frame-wide `replace([inf,-inf])` (as the QMD does on CSV-round-tripped data) raises `ValueError` on them. The vendored solver seam must clean numerics only (or drop list columns before solve). Captured in the golden generator.
5. **Small magnitudes.** This watershed barely erodes (per-group Sdyd ~0.001 t/ac); it validates plumbing, not model expressiveness. honeyed-marathoner remains the large-N parity fixture.

## Reproduction

Same pinned venv recipe as `2026-07-20_phase0_goldens.md` (recreate anywhere: `uv venv --python 3.12` + `pandas==2.2.2 numpy==1.26.0 PuLP==3.3.0 pyarrow==23.0.1`), then `python make_goldens_austere.py <out_dir>` from `artifacts/goldens/`.
