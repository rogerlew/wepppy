# Landuse->Disturbed MOFE Pipeline: Optimization Candidates

## Confirmed inefficiencies (evidence + code-path linkage)

1. Repeated management rebuilds across the DOMLC hook chain.
- Evidence from logs:
  - Cycle 1 has three `LANDUSE_BUILD_COMPLETE` events in the same chain (`00:01:17`, `00:06:39`, `00:06:40`).
  - Cycle 2 repeats the same pattern (`05:09:11`, `05:15:02`, `05:15:03`).
  - References: `disturbed.log:12`, `disturbed.log:20-21`, `disturbed.log:19782`, `disturbed.log:19790-19791`.
- Code path references:
  - Landuse triggers disturbed hook, then calls `build_managements()` again: `landuse.py:1161-1164`.
  - Disturbed DOMLC handler calls `remap_landuse()` and `remap_mofe_landuse()`: `disturbed.py:1094-1110`.
  - Each remap function calls `landuse.build_managements()`: `disturbed.py:1274`, `disturbed.py:1456`.

2. High-volume INFO logging in tight per-hillslope loops.
- Evidence from logs:
  - `landuse.log` contains `9,784` `topaz_id` lines and `9,630` `burning` lines.
  - Each 5-second remap window produced about `10k` landuse log lines.
  - Disturbed MOFE soils add `4,892` `topaz_id` lines and `4,892` generated-file lines.
- Code path references:
  - Per-topaz and per-burn INFO logging in remap loop: `disturbed.py:1247`, `disturbed.py:1251`, `disturbed.py:1257`, `disturbed.py:1263`.
  - Per-topaz INFO logging in `modify_mofe_soils()`: `disturbed.py:1691-1692`.
  - Per-hillslope file generation INFO logging: `disturbed.py:1905-1910`.

3. Expensive MOFE pair-count work is inside `build_managements()` and therefore repeated with each rebuild.
- Evidence from code + timing context:
  - `count_intersecting_raster_key_pairs(...)` is executed in `build_managements()` for multi-OFE: `landuse.py:1853-1860`.
  - Given item-level MOFE synthesis compute is only ~`17.7s` per full pass while repeated build-complete spans are `323s` and `352s`, repeated non-synthesis work is likely dominating wall time.
- Code path references:
  - `build_managements()` body and completion trigger: `landuse.py:1795-1891`.
  - Repeated call sites listed in item 1.

## Ranked candidates

| Rank | Candidate | Expected impact | Risk | Complexity | Validation notes |
|---|---|---|---|---|---|
| 1 | Consolidate to one `build_managements()` pass per DOMLC cycle (remove redundant invocations across `Landuse.build()` + disturbed remap functions) | High. Likely largest single wall-time reduction in the 5-6 minute post-remap spans; expected to remove duplicate `LANDUSE_BUILD_COMPLETE` emissions. | Medium (event ordering/state assumptions) | Medium | Validate that each DOMLC cycle emits one `LANDUSE_BUILD_COMPLETE`, and compare cycle span reduction vs baseline `323s`/`352s`. |
| 2 | Reduce INFO logging granularity in remap/MOFE loops (batch progress summaries, keep detailed logging behind DEBUG) | Medium to high. Reduces log I/O pressure and improves observability signal quality; may shave seconds from remap windows. | Low | Low | Compare line counts in remap windows and total stage times (`Remapping landuse... done`, `Modifying MOFE soils... done`). |
| 3 | Cache/reuse MOFE pair-count results when `subwta`/`mofe_map` inputs are unchanged across same-cycle rebuilds | Medium. Targets repeated heavy geospatial counting in `build_managements()`. | Medium (cache invalidation correctness) | Medium | Add timing around `count_intersecting_raster_key_pairs`; verify cache hit ratio and unchanged coverage outputs. |

## Diagnostics kept separate from optimization
- No warning/error indicators were found in `landuse.log`, `disturbed.log`, or `rq.log` for the analyzed run window.
- The optimization list above is based on timing structure and call-path duplication, not on error recovery behavior.
