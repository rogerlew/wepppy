# Phase 8A WEPP NoDir Read Touchpoints Inventory

Date captured: 2026-02-17 (UTC)

## Scope

This inventory maps WEPP prep/read paths that touch `landuse`, `soils`, `watershed`, or `climate` inputs in `wepppy/nodb/core/wepp.py` and the read-stage wrappers in `wepppy/rq/wepp_rq.py`.

Classification labels:
- `archive-native safe now`: path no longer needs a real directory after refactor.
- `needs materialize_file`: downstream consumer requires a real file path.
- `requires refactor`: current implementation assumes directory/glob semantics and must be rewritten.

## WEPP Prep Read Touchpoints

| Method | File reference | Root(s) | Current read behavior | Classification | Owner milestone |
|---|---|---|---|---|---|
| `prep_and_run_flowpaths` | `wepppy/nodb/core/wepp.py:1992` | `watershed` | `glob(WD/watershed/slope_files/flowpaths/*.slps)` and pass absolute paths to `extract_slps_fn` | requires refactor | 8C |
| `_prep_slopes_peridot` | `wepppy/nodb/core/wepp.py:2136` | `watershed` | reads `slope_files/hillslopes/hill_<id>.slp`; clip path API expects source path | needs materialize_file (clip path) + archive-native copy fallback | 8C |
| `_prep_slopes` | `wepppy/nodb/core/wepp.py:2157` | `watershed` | reads `hill_<id>.slp`; clip path API expects source path | needs materialize_file (clip path) + archive-native copy fallback | 8C |
| `_prep_multi_ofe` slopes | `wepppy/nodb/core/wepp.py:2204` | `watershed` | copies `slope_files/hillslopes/hill_<id>.mofe.slp` with `_copyfile` | archive-native safe after helper copy | 8C |
| `_prep_multi_ofe` soils | `wepppy/nodb/core/wepp.py:2209` | `soils` | `WeppSoilUtil(src_fn)` consumes real source path | needs materialize_file | 8C |
| `_prep_multi_ofe` management | `wepppy/nodb/core/wepp.py:2248` | `landuse` | `Management(..., ManagementDir=lc_dir)` loads `.man` via filesystem path | needs materialize_file | 8C |
| `_prep_managements` | `wepppy/nodb/core/wepp.py:2312` | `landuse` (implicit), `soils` data | `man_summary.get_management()` loads `.man` from `man_dir` | needs materialize_file for archive landuse | 8C |
| `_prep_soils` | `wepppy/nodb/core/wepp.py:2435` | `soils` | worker arg `src_fn=WD/soils/<soil.fname>` for `prep_soil` | needs materialize_file | 8C |
| `_prep_climates` | `wepppy/nodb/core/wepp.py:2657` | `climate` | copies `WD/climate/<cli_fn>` to runs | archive-native safe after helper copy | 8C |
| `_prep_climates_ss_batch` | `wepppy/nodb/core/wepp.py:2681` | `climate` | copies `WD/climate/<cli_fn>` to runs | archive-native safe after helper copy | 8C |
| `_prep_channel_slopes` | `wepppy/nodb/core/wepp.py:2947` | `watershed` | opens `slope_files/channels.slp` or fallback `channels.slp` directly | requires refactor | 8C |
| `_prep_channel_climate` | `wepppy/nodb/core/wepp.py:3245` | `climate` | copies `WD/climate/<cli_fn>` to runs | archive-native safe after helper copy | 8C |
| `_prep_structure` minimal-check read | `wepppy/nodb/core/wepp.py:2898` | `watershed` | checks `exists(WD/watershed/network.txt)` to gate 1-hillslope minimal structure path | requires refactor (archive-aware existence check) | 8C |

## RQ Read-Only Wrapper Inventory (Baseline)

| Stage function | File reference | Current wrapper | Roots thawed/frozen solely for reads? | Planned Phase 8D action |
|---|---|---|---|---|
| `_prep_multi_ofe_rq` | `wepppy/rq/wepp_rq.py:1272` | `mutate_roots(... _NODIR_PREP_MULTI_OFE_ROOTS ...)` | Yes | Remove wrapper after 8C |
| `_prep_slopes_rq` | `wepppy/rq/wepp_rq.py:1303` | `mutate_root(... 'watershed' ...)` | Yes | Remove wrapper after 8C |
| `_run_flowpaths_rq` | `wepppy/rq/wepp_rq.py:1358` | `mutate_root(... 'watershed' ...)` | Yes | Remove wrapper after 8C |
| `_prep_managements_rq` | `wepppy/rq/wepp_rq.py:1387` | `mutate_roots(... _NODIR_PREP_MANAGEMENTS_ROOTS ...)` | Yes | Remove wrapper after 8C |
| `_prep_soils_rq` | `wepppy/rq/wepp_rq.py:1418` | `mutate_roots(... _NODIR_PREP_SOILS_ROOTS ...)` | Yes | Remove wrapper after 8C |
| `_prep_climates_rq` | `wepppy/rq/wepp_rq.py:1449` | `mutate_roots(... _NODIR_PREP_CLIMATES_ROOTS ...)` | Yes | Remove wrapper after 8C |
| `_prep_watershed_rq` | `wepppy/rq/wepp_rq.py:1550` | `mutate_roots(... _NODIR_PREP_WATERSHED_ROOTS ...)` | Yes | Remove wrapper after 8C |

## Baseline Reliability/Perf Snapshot (Pre-Refactor)

### Method

A synthetic benchmark was executed inside the `weppcloud` container (`source /opt/venv/bin/activate && python ...`) using `mutate_roots(...)` on archive-backed roots with a no-op callback.

- Working directory: temporary run under `/tmp`.
- Roots archived: `watershed.nodir`, `soils.nodir`, `landuse.nodir`, `climate.nodir`.
- Redis lock backend replaced with in-memory lock stub (same API as NoDir tests).
- Iterations: 40 per stage-root shape.
- Measurement: wall time of one wrapper call (`thaw + callback + freeze`).

### Results

| Wrapper root shape | Analog stage(s) | Mean (ms) | Median (ms) | p95 (ms) |
|---|---|---:|---:|---:|
| `('watershed',)` | `_prep_slopes_rq`, `_run_flowpaths_rq` | 12.006 | 10.914 | 13.522 |
| `('soils', 'watershed')` | `_prep_soils_rq` | 19.328 | 19.473 | 20.666 |
| `('climate', 'watershed')` | `_prep_climates_rq` | 18.794 | 18.720 | 19.836 |
| `('climate', 'landuse', 'soils', 'watershed')` | `_prep_multi_ofe_rq`, `_prep_managements_rq`, `_prep_watershed_rq` | 35.654 | 35.526 | 36.741 |

Observed lock acquisitions during the run: `360` (`40 * (1 + 2 + 2 + 4)`), confirming lock churn scales with root count even for read-only callbacks.

### Reliability Baseline Notes

- Current WEPP prep code contains directory-form assumptions (`glob`, direct `open`, path-only consumers) for `watershed`, `soils`, and `landuse` inputs.
- RQ read-only prep stages currently avoid immediate `FileNotFoundError` on archive-backed roots by thawing roots first, but this creates avoidable lock contention and transitional-state windows.
- Phase 8C/8D will replace this with archive-native reads and file-level materialization only where required.

## Phase 8A Exit Check

- Every listed WEPP read touchpoint is mapped to milestone 8C.
- Every listed RQ read-wrapper stage is mapped to milestone 8D.
- Baseline reliability/perf method and measurements are captured for before/after comparison.
