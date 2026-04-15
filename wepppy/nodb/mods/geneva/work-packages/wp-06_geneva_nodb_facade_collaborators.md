# WP-06 Evidence: Geneva NoDb Facade + Collaborators
Status: done  
Last Updated: 2026-04-15  
Work-Package: `WP-06`  
Owner: `codex`

References:
- Plan: `/workdir/wepppy/wepppy/nodb/mods/geneva/implementation-plan.md`
- Spec: `/workdir/wepppy/wepppy/nodb/mods/geneva/specification.md`
- Prior package evidence: `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp-05_scs_uh_hydrograph_kernel.md`
- NoDb facade standard: `/workdir/wepppy/docs/standards/nodb-facade-collaborator-pattern.md`

## 1. Scope Implemented
Implemented WP-06 Geneva NoDb orchestration in `/workdir/wepppy`:
- Added Geneva facade controller in `wepppy/nodb/mods/geneva/geneva.py` with thin delegation and NoDb lock/persistence boundaries.
- Added collaborator modules for:
  - config management,
  - guard/domain + input reference resolution,
  - HRU preparation orchestration,
  - frequency panel build orchestration,
  - batch-run orchestration,
  - results/status aggregation,
  - run-scoped artifact I/O.
- Added schema modules for config/run-batch/results contracts.
- Wired Rust kernel calls via boundary gateway to:
  - `geneva_prepare_hrus`,
  - `geneva_build_frequency_panel`,
  - `geneva_run_batch`.
- Implemented lifecycle persistence states:
  - `idle|prepared|running|completed|completed_with_gaps|failed`.
- Persisted Geneva artifacts under `<run>/geneva/*` (including per-storm outputs).
- Implemented NoDb guardrails:
  - non-WBT rejection with canonical envelope,
  - non-US/non-NLCD-HSG-incompatible rejection with `unsupported_domain`.

## 2. Code Changes
### Repo: `/workdir/wepppy`
- `wepppy/nodb/mods/geneva/__init__.py`
- `wepppy/nodb/mods/geneva/errors.py`
- `wepppy/nodb/mods/geneva/geneva.py`
- `wepppy/nodb/mods/geneva/collaborators/__init__.py`
- `wepppy/nodb/mods/geneva/collaborators/artifact_io.py`
- `wepppy/nodb/mods/geneva/collaborators/config_service.py`
- `wepppy/nodb/mods/geneva/collaborators/hsg_assignment_service.py`
- `wepppy/nodb/mods/geneva/collaborators/kernel_gateway.py`
- `wepppy/nodb/mods/geneva/collaborators/hru_preparation_service.py`
- `wepppy/nodb/mods/geneva/collaborators/frequency_panel_service.py`
- `wepppy/nodb/mods/geneva/collaborators/batch_run_service.py`
- `wepppy/nodb/mods/geneva/collaborators/results_service.py`
- `wepppy/nodb/mods/geneva/schemas/__init__.py`
- `wepppy/nodb/mods/geneva/schemas/config_schema.py`
- `wepppy/nodb/mods/geneva/schemas/run_batch_schema.py`
- `wepppy/nodb/mods/geneva/schemas/results_schema.py`
- `tests/nodb/mods/geneva/test_geneva_collaborators.py`
- `tests/nodb/mods/geneva/test_geneva_facade.py`
- `tests/nodb/mods/geneva/test_geneva_guardrails.py`
- `wepppy/nodb/mods/geneva/work-packages/wp-06_geneva_nodb_facade_collaborators.md`
- `wepppy/nodb/mods/geneva/implementation-plan.md`

## 3. Tests Added/Extended
Added/extended WP-06 coverage for:
- facade delegation + state/lifecycle transitions,
- collaborator responsibilities (config/artifact I/O/kernel boundary/HRU prep),
- guardrail negatives (non-WBT + unsupported domain),
- typed error behavior,
- persistence round-trip (`.nodb` reload reflects saved Geneva state).

New test modules:
- `tests/nodb/mods/geneva/test_geneva_collaborators.py`
- `tests/nodb/mods/geneva/test_geneva_facade.py`
- `tests/nodb/mods/geneva/test_geneva_guardrails.py`

## 4. Required Gates
Executed from `/workdir/wepppy`.

1. `wctl run-pytest tests/nodb/mods/geneva --maxfail=1`
- Result: **pass** (`14 passed`)

2. `wctl run-pytest tests/nodb --maxfail=1`
- Result: **pass** (`949 passed, 4 skipped`)

3. `wctl doc-lint --path wepppy/nodb/mods/geneva`
- Result: **pass** (`12 files validated, 0 errors, 0 warnings`)

4. `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- Result: **pass** (`Changed Python files scanned: 0`, `Result: PASS`)

Conditional queue wiring gate:
- `wctl check-rq-graph`: **not required** (no queue wiring changes in WP-06 scope).

## 5. Manual Integration Protocol Evidence
Manual NoDb facade harness scenarios executed using the built Geneva-enabled Rust extension (`/workdir/wepppyo3/target/release/libcli_revision_rust.so`) and synthetic fixture rasters.

### Scenario A: Happy-path with partial availability (`completed_with_gaps`)
- Run dir: `/tmp/geneva_wp06_manual_c14t_wlh`
- Flow: enable -> prepare_hrus -> build_frequency_panel (NOAA missing) -> run_batch
- Observed:
  - `prepare_hru_count = 12`
  - `panel_cells = 2`
  - final `status = completed_with_gaps`
  - `storm_count_total = 2`
  - `storm_count_completed = 1`
  - `storm_count_unavailable = 1`
  - `geneva/batch_summary.json` persisted

### Scenario B: Happy-path with full availability (`completed`)
- Run dir: `/tmp/geneva_wp06_manual_m1jjykus`
- Flow: enable -> prepare_hrus -> build_frequency_panel (NOAA present) -> run_batch
- Observed:
  - `prepare_hru_count = 12`
  - `panel_cells = 2`
  - final `status = completed`
  - `storm_count_total = 2`
  - `storm_count_completed = 2`
  - `storm_count_unavailable = 0`
  - per-storm summaries persisted:
    - `/tmp/geneva_wp06_manual_m1jjykus/geneva/storms/cligen_10m_1y/summary.json`
    - `/tmp/geneva_wp06_manual_m1jjykus/geneva/storms/noaa14_10m_1y/summary.json`

### Scenario C: Guardrails
- Non-WBT enable attempt returned code: `unsupported_backend`
- Non-US/non-NLCD-HSG-compatible enable attempt returned code: `unsupported_domain`

## 6. Review Workflow
### 6.1 Code Review (`reviewer` pass, manual)
Checklist outcomes:
- Pass: facade remains thin and delegates to collaborator services.
- Pass: collaborator responsibilities are cohesive and non-overlapping.
- Pass: boundary calls are centralized through typed kernel gateway.

### 6.2 QA Review (`qa_reviewer` pass, manual)
Checklist outcomes:
- Pass: lifecycle transitions and persistence round-trip behavior are covered.
- Pass: guardrail negative paths are covered with explicit stable error codes.
- Pass: artifact persistence under `<run>/geneva/*` is exercised in tests and manual harness.

### 6.3 Security Review (`security_reviewer` pass, manual)
Checklist outcomes:
- Pass: no broad exception handlers remain in Geneva production paths.
- Pass: artifact IO enforces relative-path traversal protection.
- Pass: guardrail and kernel boundary failures use explicit typed error payloads.

## 7. QA Review Checklist
- [x] Collaborator extraction follows NoDb facade/collaborator standard.
- [x] Facade API and side effects remain contract-consistent.
- [x] Lifecycle/status payload behavior matches required transitions.
- [x] Guardrail errors use canonical envelope and stable error codes.

## 8. Security Review Checklist
- [x] No broad exception swallowing on production paths.
- [x] Locking/state serialization boundaries remain explicit.
- [x] Kernel-boundary payloads validated and error-mapped.
- [x] Artifact path handling prevents traversal/injection behavior.

## 9. Findings and Disposition
- Finding ID: `WP06-CODE-BROAD-CATCH-BATCH`
  - Severity: medium
  - Disposition: resolved_fix_now
  - Action/Notes: removed broad per-storm `except Exception` catch and narrowed handling to typed Geneva errors.

- Finding ID: `WP06-QA-LIFECYCLE-PERSISTENCE-COVERAGE`
  - Severity: low
  - Disposition: resolved_fix_now
  - Action/Notes: added integration test covering `idle -> prepared -> running -> completed_with_gaps` and reload round-trip persistence.

- Finding ID: `WP06-SEC-KERNEL-BOUNDARY-FAILURE-CONTRACT`
  - Severity: medium
  - Disposition: resolved_fix_now
  - Action/Notes: kernel gateway now enforces explicit missing-dependency and typed ValueError code mapping contracts.

- Finding ID: `WP06-DEP-WP02-INREVIEW`
  - Severity: low
  - Disposition: accepted_risk
  - Action/Notes: dependency waiver recorded for WP-02 board state (`in_review`) because WP-06 gates/reviews/manual checks are fully passing and WP-06 scope does not modify WP-02 kernel internals.

## 10. Exit-Criteria Check
- [x] Geneva NoDb facade + collaborators implemented.
- [x] Rust kernel wiring for HRU prep/panel/run-batch implemented.
- [x] Required artifacts and lifecycle persistence implemented.
- [x] Guardrail negative tests implemented and passing.
- [x] Required tests added/updated and passing.
- [x] Required gates all passing.
- [x] Manual integration evidence captured.
- [x] Code/QA/security reviews completed and findings dispositioned.
- [x] Board row updated to `done` with evidence link.
