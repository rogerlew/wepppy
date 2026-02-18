# Phase 8 WEPP NoDir Perf Results

Date captured: 2026-02-17 (UTC)

## Scope

Phase 8 performance evidence tracks WEPP prep-stage orchestration overhead that previously came from root-level thaw/freeze wrappers in `wepppy/rq/wepp_rq.py`, then compares it against refactored direct archive-first read stages.

## Method

### Baseline (pre-refactor)

- Run in `weppcloud` container with venv active.
- Create a synthetic temporary run with archived `watershed`, `soils`, `landuse`, and `climate` roots.
- Use an in-memory lock stub and call `mutate_roots(...)` with a no-op callback for 40 iterations per root-set shape.
- Measure wall time per call and report mean/median/p95.

### Post-refactor (Phase 8)

- Run in the same container.
- Benchmark actual stage functions (`_prep_slopes_rq`, `_prep_managements_rq`, `_prep_soils_rq`, etc.) after wrapper removal.
- Stub `Wepp.getInstance(...)`, `Watershed.getInstance(...)`, `get_wd(...)`, and status publishing so measured time isolates RQ stage orchestration overhead.
- Iterations: 1000 per stage.
- Measure wall time per call and report mean/median/p95.

Note: these measurements isolate orchestration/locking overhead, not full WEPP model runtime.

## Baseline Results (Before Phase 8 Refactor)

| Wrapper root shape | Analog stage(s) | Mean (ms) | Median (ms) | p95 (ms) |
|---|---|---:|---:|---:|
| `('watershed',)` | `_prep_slopes_rq`, `_run_flowpaths_rq` | 12.0060 | 10.9140 | 13.5220 |
| `('soils', 'watershed')` | `_prep_soils_rq` | 19.3280 | 19.4730 | 20.6660 |
| `('climate', 'watershed')` | `_prep_climates_rq` | 18.7940 | 18.7200 | 19.8360 |
| `('climate', 'landuse', 'soils', 'watershed')` | `_prep_multi_ofe_rq`, `_prep_managements_rq`, `_prep_watershed_rq` | 35.6540 | 35.5260 | 36.7410 |

Observed lock acquisitions: `360` across `160` wrapper invocations.

## Post-Refactor Results (After Phase 8)

| Stage | Mean (ms) | Median (ms) | p95 (ms) |
|---|---:|---:|---:|
| `_prep_slopes_rq` | 0.0028 | 0.0025 | 0.0028 |
| `_prep_managements_rq` | 0.0027 | 0.0025 | 0.0028 |
| `_prep_soils_rq` | 0.0028 | 0.0025 | 0.0028 |
| `_prep_climates_rq` | 0.0027 | 0.0025 | 0.0027 |
| `_prep_multi_ofe_rq` | 0.0027 | 0.0025 | 0.0027 |
| `_run_flowpaths_rq` | 0.0024 | 0.0023 | 0.0024 |
| `_prep_watershed_rq` | 0.0025 | 0.0023 | 0.0024 |

Read-only stages no longer invoke `mutate_root(s)` wrappers, so root maintenance lock time for these stages is effectively zero in the measured path.

## Target Evaluation

| Target | Before p95 (ms) | After p95 (ms) | Improvement | Status |
|---|---:|---:|---:|---|
| `_prep_slopes_rq` p95 >= 20% faster | 13.5220 | 0.0028 | 99.98% | pass |
| `_prep_managements_rq` p95 >= 15% faster | 36.7410 | 0.0028 | 99.99% | pass |
| `_prep_soils_rq` p95 >= 15% faster | 20.6660 | 0.0028 | 99.99% | pass |
| Read-only stage root lock time near zero | non-zero lock/thaw/freeze overhead | near-zero | achieved | pass |

## Artifacts Cross-Reference

- Touchpoint inventory + baseline context: `docs/work-packages/20260214_nodir_archives/artifacts/wepp_nodir_read_touchpoints_phase8a.md`
- Reliability delta/runbook: `docs/work-packages/20260214_nodir_archives/artifacts/phase8_wepp_nodir_reliability_runbook.md`
