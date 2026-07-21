# Phase 0 — Parity Fixture + Upstream Reference Goldens

**Date**: 2026-07-20 20:30 UTC
**Evidence class**: Executional — Jackson's unmodified code (commit `4e3b4a6`) was run in a scratch venv pinned to the wepppy image versions (pandas 2.2.2, numpy 1.26.0, PuLP 3.3.0/CBC 2.10.3, pyarrow 23.0.1; python 3.12).

## What ran

1. **Parquet-native smoke test** (`goldens/run_reference.py`): `prepare_ce_and_plot_data()` executed unmodified against raw wepppy artifacts from run `honeyed-marathoner` (`omni/scenarios.hillslope_summaries.parquet`, `omni/contrasts.out.parquet`, `omni/contrast_id_definitions.psv`, `omni/scenarios.out.parquet` as outlet totals, `watershed/hillslopes.parquet`). Completed end-to-end: 100 contrast groups × 39 columns including the full `Sddc post-treat / post-fire / reduction` set, with `Sddc post-fire` = 44006.7 broadcast as the outlet scalar. Confirms executionally that parquet-native integration is a seam change — no schema translation layer needed.
2. **Solver goldens, real data, single treatment** (`goldens/solver_goldens.json` + `goldens/prepared_frame.parquet`, generator `make_goldens.py`): `ce_select_sites_flexible()` on the prepared honeyed-marathoner frame (contrast_id schema), treatment `2 tons/acre` @ $2475 × qty 2, fixed $1500. Cases: (sdyd 15, sddc 43000) → primary optimal, 17 selected, cost $1.22M; (5, 40000) and (1, 35000) → primary infeasible, secondary maximize path, statuses/selections/costs recorded.
3. **Solver goldens, pacificcreek, three treatments** (`goldens/solver_goldens_3treat.json`, generator `make_goldens_3treat.py`): Jackson's own `PATH_prepared_hillslope_data.csv` (63 hillslopes, wepp_id schema). Cases (15,1), (10,1), (5,1) → primary optimal with escalating tier assignments ([9,0,0] → [25,0,1] → [17,8,16]); (10,0) → secondary path with distinct assignment. QMD-default cost vectors.

Golden payloads capture: primary status, selected/per-treatment hillslope sets, total/fixed cost, total Sddc reduction, final Sddc, untreatable counts (incl. increase class), and final-Sdyd checksum.

## Findings for later phases

- **Partial contrast coverage is the norm in existing runs**: every local run with `contrasts.out.parquet` (4 found) has contrasts for `mulch_60_sbs_map` only. Phase 2 precondition validation must check per-treatment contrast coverage and name the missing scenarios; treatment auto-alignment (upstream `_align_treatments_to_data`) already narrows the treatment set to what the data supports — decide in Phase 2 whether PATH errors or narrows with a warning.
- **Two live schema modes confirmed in production data**: `honeyed-marathoner` (topaz backend; cumulative contrasts with `contrast_topaz_id` + single-topaz psv) and `walk-in-obsessive-compulsive` (wbt backend; grouped contrasts named `sbs_map,{n}__to__…`, **no** `contrast_topaz_id`, **no psv present**). The latter means the psv is not guaranteed for older runs — precondition validation should require it for grouped-mode runs rather than assume it.
- **`omni/scenarios.out.parquet` uses column `value`** (not `v` as the artifact survey stated) — it matches upstream `outlet_totals` expectations (`key`/`value`) as-is.
- **Secondary-model behavior note**: in the real-data secondary cases, total Sddc reduction is negative (final Sddc above post-fire) because sdyd equality constraints can force treatments with negative Sddc deltas. This is faithful upstream behavior; preserved in goldens, worth surfacing in the report/UI copy eventually.
- **pacificcreek `Sddc post-fire` = 0.1** — near-zero outlet scalar in that dataset; goldens use sddc_threshold=1 to exercise the primary path and 0 to exercise secondary.

## Reproduction

Scratch venv: `uv venv --python 3.12` + `pandas==2.2.2 numpy==1.26.0 PuLP==3.3.0 pyarrow==23.0.1`; scripts under `artifacts/goldens/` run against `/workdir/PATH-cost-effective` @ `4e3b4a6` and `/wc1/runs/ho/honeyed-marathoner`. Goldens are environment-pinned; regenerate if image pins change. Fixture data (prepared frame + goldens) moves into `tests/` fixtures during Phase 1.
