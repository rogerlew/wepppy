# Phase 9 Projection Sessions Reliability Runbook

Date captured: 2026-02-18 (UTC)

## Purpose

This runbook captures Phase 9E reliability outcomes after projection-session adoption and defines operational checks for mixed-state handling, lock contention, and fallback observability behavior.

## Validation Evidence

Required Phase 9E gates:

1. `wctl run-pytest tests/nodir/test_projections.py tests/nodir/test_wepp_inputs.py`
   - Result: `38 passed, 2 warnings in 8.25s`
2. `wctl run-pytest tests/nodb/test_wepp_nodir_read_paths.py tests/rq/test_wepp_rq_nodir.py`
   - Result: `27 passed, 5 warnings in 10.43s`
3. `wctl run-pytest tests/rq tests/microservices/test_rq_engine_wepp_routes.py`
   - Result: `52 passed, 10 warnings in 15.32s`
4. `wctl run-pytest tests --maxfail=1`
   - Result: `1619 passed, 27 skipped, 53 warnings in 331.57s (0:05:31)`
5. `wctl doc-lint --path docs/work-packages/20260214_nodir_archives`
   - Result: `47 files validated, 0 errors, 0 warnings`

## Reliability Outcomes

### 1) Mixed-State Behavior

Outcome:
- Unmanaged mixed root collisions (`WD/<root>/` + `WD/<root>.nodir`) remain fail-fast with canonical `409 NODIR_MIXED_STATE`.
- Stage projection wrappers in `wepp_rq` reject unmanaged mixed-state before projection acquisition.

Primary regression coverage:
- `tests/rq/test_wepp_rq_nodir.py::test_stage_projection_wrapper_raises_mixed_state_when_unmanaged_root_exists`
- `tests/rq/test_wepp_rq_nodir.py::test_prep_watershed_projection_wrapper_raises_mixed_state_when_unmanaged_root_exists`
- `tests/nodir/test_wepp_inputs.py::test_with_input_file_path_mixed_state_preserves_canonical_error`
- `tests/nodir/test_projections.py::test_projection_rejects_unmanaged_mixed_directory`

### 2) Lock Contention and Transition Locks

Outcome:
- Projection contention and transition lock paths remain canonical `503 NODIR_LOCKED`.
- Cross-mode managed-session collisions are treated as lock contention, not mixed unmanaged state.

Primary regression coverage:
- `tests/nodir/test_projections.py::test_projection_lock_contention_without_metadata_returns_locked`
- `tests/nodir/test_projections.py::test_projection_preserves_transition_lock_error`
- `tests/nodir/test_projections.py::test_projection_cross_mode_conflict_returns_locked`
- `tests/nodir/test_wepp_inputs.py::test_with_input_file_path_projection_error_without_fallback_raises`

### 3) Fallback Observability

Outcome:
- Projection fallback to per-file materialization remains explicit and observable by warnings in helper-layer logs.
- Fallback behavior stays opt-in (`allow_materialize_fallback=True`) and does not silently mask lock errors by default.

Primary regression coverage:
- `tests/nodir/test_wepp_inputs.py::test_with_input_file_path_projection_disabled_fallback_logs_warning`
- `tests/nodir/test_wepp_inputs.py::test_with_input_file_path_projection_error_fallback_logs_warning`
- `tests/nodir/test_wepp_inputs.py::test_with_input_file_path_projection_error_can_fallback_to_materialize`

### 4) Canonical NoDir Status Semantics

Outcome:
- Canonical error families remain stable for projection-era read and mutation paths:
  - `409 NODIR_MIXED_STATE`
  - `500 NODIR_INVALID_ARCHIVE`
  - `503 NODIR_LOCKED`
  - `413 NODIR_LIMIT_EXCEEDED`

Validation support:
- Helper/projection suites explicitly assert `409/500/503` mappings.
- Full suite gate (`1619 passed`) shows no broad regression in NoDir error-code behavior.

## Operational Checks

If a projection-era incident is reported:

1. Identify failing stage/job and capture NoDir status code + error code.
2. Inspect root-state shape:
   - `WD/<root>/`
   - `WD/<root>.nodir`
   - `WD/.nodir/projections/<root>/...`
3. For `503 NODIR_LOCKED`, check active projection metadata and lock ownership before retry.
4. For `409 NODIR_MIXED_STATE`, treat as unmanaged collision and recover archive-authoritatively per runbook policy.
5. For fallback-driven paths, confirm warning logs are present and whether fallback was explicitly enabled.

## Residual Risks

- New path consumers that call projection helpers during active projection sessions must preserve mixed-state tolerance settings (`tolerate_mixed=True, mixed_prefer="archive"`) as used by migrated WEPP callsites.
- Runtime variance under large real runs is still environment-sensitive; continue monitoring stage timings during rollout even though contract/reliability gates are green.

## Cross-Reference

- Phase 8 runbook baseline: `docs/work-packages/20260214_nodir_archives/artifacts/phase8_wepp_nodir_reliability_runbook.md`
- Phase 9 perf evidence: `docs/work-packages/20260214_nodir_archives/artifacts/phase9_projection_sessions_perf_results.md`
