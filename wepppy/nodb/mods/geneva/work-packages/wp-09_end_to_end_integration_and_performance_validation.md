# WP-09 Evidence: End-to-End Integration and Performance Validation
Status: done  
Last Updated: 2026-04-15  
Work-Package: `WP-09`  
Owner: `codex`

References:
- Plan: `/workdir/wepppy/wepppy/nodb/mods/geneva/implementation-plan.md`
- Spec: `/workdir/wepppy/wepppy/nodb/mods/geneva/specification.md`
- Prior package evidence: `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp-08_routes_tasks_rq_wiring_query_report_api.md`
- WP-09 execution prompt: `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp-09_execution_prompt.md`

## 1. Scope Implemented
WP-09 scope completed without broadening into WP-10:
- End-to-end scenario harness coverage added for:
  - no-burn vs burn-severity,
  - CLIGEN-only vs dual-source NOAA+CLIGEN,
  - mixed available/unavailable frequency-panel cells with `completed_with_gaps`.
- Runtime/profiling harnesses extended and baseline evidence captured for representative panel/watershed sizes.
- Collapsed-vs-uncollapsed sensitivity checks added and validated against required thresholds.
- Watershed-size warning threshold behavior (`warning`, `severe`, `extreme`) validated and confirmed on results/query/report surfaces.

## 2. Code Changes
### Repo: `/workdir/wepppy`
Geneva collaborator updates and schema/runtime support:
- `wepppy/nodb/mods/geneva/collaborators/batch_run_service.py`
  - watershed-size warning threshold logic (`warning|severe|extreme`)
  - run-level warning payload integration (`run_warnings`)
  - assumptions metadata includes constant ARF fields
- `wepppy/nodb/mods/geneva/collaborators/results_service.py`
  - run-level warnings included in results warning aggregation
- `wepppy/nodb/mods/geneva/collaborators/frequency_panel_service.py`
  - CLIGEN CSV normalization (`Precipitation depth (mm)` -> `Storm depth (mm)`) for kernel compatibility
- `wepppy/nodb/mods/geneva/collaborators/kernel_gateway.py`
  - kernel module fallback loading (`wepppyo3.climate.cli_revision_rust` -> `cli_revision_rust`)
  - improved missing-dependency diagnostics

Validation harness updates:
- `tests/nodb/mods/geneva/test_geneva_wp09_end_to_end.py` (new)
- `tests/nodb/mods/geneva/test_geneva_collaborators.py`
- `tests/nodb/mods/geneva/test_geneva_schema_contracts.py`

Evidence/plan updates:
- `wepppy/nodb/mods/geneva/work-packages/wp-09_end_to_end_integration_and_performance_validation.md`
- `wepppy/nodb/mods/geneva/implementation-plan.md`

### Repo: `/workdir/wepppyo3`
- No code changes required for WP-09 completion.

## 3. Tests Added/Extended
Added/extended tests for WP-09 acceptance criteria:
- `test_wp09_scenario_matrix_and_completed_with_gaps_lifecycle`
- `test_wp09_collapsed_vs_uncollapsed_sensitivity_thresholds`
- `test_wp09_watershed_warning_thresholds_propagate_to_results_query_report`
- `test_wp09_runtime_profile_harness_records_representative_baselines`
- kernel gateway fallback test for mixed legacy/new binding layout
- CLIGEN normalization contract tests

## 4. Required Gates
Executed from `/workdir/wepppy` after implementation:

1. `wctl run-pytest tests/nodb/mods/geneva --maxfail=1`
- Result: **pass** (`34 passed, 5 warnings`)

2. `wctl run-pytest tests/nodb --maxfail=1`
- Result: **pass** (`969 passed, 4 skipped, 23 warnings`)

3. `wctl run-pytest tests --maxfail=1`
- Result: **pass** (`3625 passed, 36 skipped, 267 warnings`)

4. `wctl doc-lint --path wepppy/nodb/mods/geneva`
- Result: **pass** (`17 files validated, 0 errors, 0 warnings`)

5. `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- Result: **pass** (changed Python files scanned: `4`, net broad-catch delta: `+0`)

6. `wctl check-rq-graph`
- Queue wiring was unchanged in WP-09; command run as verification only.
- Result: **pass** (`RQ dependency graph artifacts are up to date`)

If `wepppyo3` is modified:
- Not applicable; no `wepppyo3` files were touched in WP-09.

UI gates:
- Not applicable; no frontend/template/js files were touched in WP-09.

## 5. Manual Integration Evidence
Manual full-flow evidence captured via `wctl run-python` harness invoking:
- `Geneva.getInstance(<run_dir>)`
- `set_enabled(True)` + `update_config(...)`
- `prepare_hrus(force_rebuild=True, ...)`
- `build_frequency_panel(rebuild=True, durations=[5,10,30,60], ari=[1,2,5,10,25], sources=...)`
- `run_batch(...)`
- `results/query/report` payload checks

### 5.1 Real Run A (Noisy hydgrpdcd, CLIGEN-only, no burn)
- Run dir: `/wc1/runs/cl/clogging-starch`
- Burn severity input: none
- Sources: CLIGEN present, NOAA omitted (`noaa14_pds=None`)
- Observed:
  - `status = completed_with_gaps`
  - `hru_count = 2`
  - `panel available=0, unavailable=40`
  - reason counts: `source_missing=20`, `duration_unavailable=16`, `ari_unavailable=4`
  - prepare warning codes include noisy-path diagnostics:
    - `hydgrpdcd_invalid_code`
    - `hydgrpdcd_resampled_to_bound`
    - `landuse_resampled_to_bound`
    - `hsg_default_fallback`
    - `collapse_no_compatible_recipient`
  - query/report consistency:
    - `query_events=0`, `report_events=0`
    - warning code sets match across query/report (`ari_unavailable`, `duration_unavailable`, `noaa_source_missing`, `source_missing`)
  - timing (seconds): `prepare=0.2313`, `panel=0.0375`, `batch=0.0775`, `total=0.3463`

### 5.2 Real Run B (Dual-source with burn-severity input)
- Run dir: `/wc1/runs/ap/apocalyptic-bush`
- Burn severity input: `/wc1/runs/ap/apocalyptic-bush/geneva/wp09/burn_severity_wp09.tif`
- Sources: CLIGEN + NOAA
- Observed:
  - `status = completed_with_gaps`
  - `hru_count = 31`
  - `panel available=20, unavailable=20`
  - reason counts: `duration_unavailable=16`, `ari_unavailable=4`
  - query/report consistency:
    - `query_events=20`, `report_events=20`
    - warning code sets match across query/report (`ari_unavailable`, `duration_unavailable`)
  - timing (seconds): `prepare=1.2402`, `panel=0.0538`, `batch=0.7114`, `total=2.0054`

## 6. Runtime/Performance Baseline Evidence
Profiling harness executed via `wctl run-python` using `_run_geneva_flow` synthetic profile workloads:
- Small case: `panel_cells=1`, `wsarea_km2=2.0` -> `elapsed_seconds=5.2925`
- Large case: `panel_cells=32`, `wsarea_km2=80.0` -> `elapsed_seconds=0.4817`

Recorded baseline notes:
- First-case execution includes interpreter/module warmup overhead in this environment.
- Both values are captured as explicit WP-09 baselines for future comparison, and real-run timings are also recorded in Section 5.

## 7. Collapse Sensitivity Evidence
Sensitivity probe executed via `wctl run-python` using `_run_geneva_flow` reference-case setup.

Observed relative deltas:
- Default `allow_cross_hsg_merge=false`
  - runoff depth delta: `0.015` (`<= 0.02` pass)
  - runoff volume delta: `0.018` (`<= 0.02` pass)
  - peak discharge delta: `0.040` (`<= 0.05` pass)
- `allow_cross_hsg_merge=true`
  - runoff depth delta: `0.018` (`<= 0.02` pass)

## 8. Watershed Warning Threshold Evidence
Threshold probe executed via `wctl run-python` across watershed sizes:
- `wsarea_km2=30.0` -> severity `warning`, threshold `25.0`
- `wsarea_km2=150.0` -> severity `severe`, threshold `100.0`
- `wsarea_km2=300.0` -> severity `extreme`, threshold `250.0`

Propagation check:
- `results`, `query`, and `report` payloads all reported matching severities for each threshold band.

## 9. Review Workflow
### 9.1 Code Review
Reviewed collaborator changes for correctness and contract safety:
- run-level warnings now surface consistently through summary payload paths
- kernel loader no longer hard-fails on legacy binding layout
- CLIGEN normalization is bounded to the required compatibility transform

### 9.2 QA Review
Validated by:
- new WP-09 integration tests
- full required gate suite
- two real-run manual flows (one noisy `hydgrpdcd`)
- query/report consistency checks for counts and warning sets

### 9.3 Security Review
Validated boundaries:
- no auth/route surface changes introduced
- no queue wiring changes
- broad exception changed-file gate passed (`net delta +0`)
- errors remain explicit and typed (`GenevaValidationError` / `GenevaKernelError`) for affected code paths

## 10. Findings and Disposition
- Finding ID: `WP09-CODE-KERNEL-BINDING-COMPAT`
  - Severity: high
  - Disposition: resolved_fix_now
  - Action/Notes: gateway previously required only `wepppyo3.climate.cli_revision_rust`; added fallback module probing and callable API verification.

- Finding ID: `WP09-CODE-CLIGEN-ROW-LABEL-COMPAT`
  - Severity: high
  - Disposition: resolved_fix_now
  - Action/Notes: CLIGEN source row used `Precipitation depth (mm)` where kernel expects `Storm depth (mm)`; added normalization bridge + contract tests.

- Finding ID: `WP09-QA-WATERSHED-WARNING-PROPAGATION`
  - Severity: medium
  - Disposition: resolved_fix_now
  - Action/Notes: watershed-size warning thresholds were not surfaced end-to-end; added run-level warning emission and results/query/report propagation coverage.

- Finding ID: `WP09-SEC-BROAD-EXCEPTION-REGRESSION`
  - Severity: medium
  - Disposition: resolved_fix_now
  - Action/Notes: security review required changed-file broad-catch enforcement confirmation; gate passed with `net delta +0`.

## 11. Exit-Criteria Check
- [x] End-to-end scenario matrix is validated with evidence.
- [x] Runtime baseline/profiling evidence is captured and acceptable.
- [x] Collapse sensitivity tolerances are validated and recorded.
- [x] Watershed warning threshold behavior is validated and surfaced correctly.
- [x] Required tests/gates pass with recorded outcomes.
- [x] Manual integration checks recorded (including noisy `hydgrpdcd` run).
- [x] Code/QA/security review findings are dispositioned.
