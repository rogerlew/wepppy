# WP-05 Evidence: SCS UH + Hydrograph Kernel
Status: done  
Last Updated: 2026-04-15  
Work-Package: `WP-05`  
Owner: `codex`

References:
- Plan: `/workdir/wepppy/wepppy/nodb/mods/geneva/implementation-plan.md`
- Spec: `/workdir/wepppy/wepppy/nodb/mods/geneva/specification.md`
- Prior package evidence: `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp-04_frequency_panel_neh4_type_b_kernel.md`

## 1. Scope Implemented
Implemented WP-05 kernel scope in `/workdir/wepppyo3`:
- Added SCS unit-hydrograph kernel in `geneva_core/src/uh.rs`:
  - methods: `scs_triangular`, `scs_curvilinear`,
  - triangular relations: `tp = 0.6 * tc`, `tb = 2.667 * tp`,
  - curvilinear interpolation from Wildcat/RMRS dimensionless ordinates (`t/tp`, `q/qp`),
  - UH closure enforcement: `|integral(UH)-1| <= 0.005`,
  - provenance fields persisted: `uh_unit_system`, `hf_constant`, `qp_equation_id`.
- Added hydrograph convolution kernel in `geneva_core/src/convolution.rs`:
  - excess-to-hydrograph convolution,
  - summary metrics: `peak_discharge`, `time_to_peak`, `runoff_volume`, `runoff_depth`,
  - hydrograph volume closure enforcement against excess volume (`<= 1%` relative),
  - deterministic hydrograph series output (`q_cms`, `q_cfs`, `runoff_cum_mm`, `runoff_volume_m3`).
- Wired `run_batch` in `geneva_core/src/cn.rs` to call UH + convolution kernels:
  - request now includes `uh_method` and `tc_hours`,
  - response now includes `unit_hydrograph`, `hydrograph`, `summary_metrics`, and `hydrograph_diagnostics`.
- Kept adapter thin:
  - `cli_revision/src/geneva/mod.rs` and `cli_revision/src/geneva/convert.rs` only parse/validate/call/serialize,
  - no algorithm body added to `cli_revision/src/lib.rs`.

## 2. Code Changes
### Repo: `/workdir/wepppyo3`
- `geneva_core/src/uh.rs`
- `geneva_core/src/convolution.rs`
- `geneva_core/src/cn.rs`
- `cli_revision/src/geneva/convert.rs`
- `cli_revision/src/geneva/mod.rs`

### Repo: `/workdir/wepppy`
- `wepppy/nodb/mods/geneva/work-packages/wp-05_scs_uh_hydrograph_kernel.md`
- `wepppy/nodb/mods/geneva/implementation-plan.md`

## 3. Tests Added/Extended
Added/extended coverage for WP-05 acceptance behavior:
- UH kernel tests (`geneva_core/src/uh.rs`):
  - triangular relation parity (`tp`, `tb`) and closure,
  - curvilinear interpolation path and closure,
  - deterministic repeated-run behavior,
  - invalid input validation (`tc_hours`, area, timestep) and strict method IDs.
- Convolution tests (`geneva_core/src/convolution.rs`):
  - fixed regression vector with expected hydrograph metrics,
  - volume closure and determinism checks,
  - invalid-input rejection and closure-failure behavior.
- Run-batch integration tests (`geneva_core/src/cn.rs`):
  - both UH methods exercised via run-batch,
  - UH closure and hydrograph volume closure assertions,
  - invalid timing input behavior (`tc_hours`, non-uniform timestep).
- Adapter boundary tests (`cli_revision/src/geneva/*`):
  - valid run-batch returns hydrograph/summary/provenance payload,
  - invalid UH method handling with typed mapped errors,
  - parse-level request validation for canonical UH IDs.

## 4. Required Gates
### 4.1 Kernel repo gates (`/workdir/wepppyo3`)
1. `cd /workdir/wepppyo3 && cargo fmt --check`
   - Result: **pass** (no formatting diffs)
2. `cd /workdir/wepppyo3 && cargo clippy --all-targets -- -D warnings`
   - Result: **pass** (`geneva_core` and `cli_revision_rust` checked; no warnings)
3. `cd /workdir/wepppyo3 && cargo test -p geneva_core`
   - Result: **pass** (`53 passed; 0 failed`)
4. `cd /workdir/wepppyo3 && cargo test -p cli_revision_rust --lib`
   - Result: **pass** (`20 passed; 0 failed`)

### 4.2 Core repo gates (`/workdir/wepppy`)
5. `cd /workdir/wepppy && wctl doc-lint --path wepppy/nodb/mods/geneva`
   - Result: **pass** (`11 files validated, 0 errors, 0 warnings`)
6. `cd /workdir/wepppy && python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
   - Result: **pass** (`Changed Python files scanned: 0`, `Result: PASS`)

## 5. Manual Integration Protocol Evidence
Adapter-path manual integration executed via release extension:
- `cd /workdir/wepppyo3 && cargo build -p cli_revision_rust --release --features extension-module`
- Python loaded `/workdir/wepppyo3/target/release/libcli_revision_rust.so` and called `geneva_run_batch(...)` for both UH methods.

Manual scenario outcomes:
- `scs_triangular`:
  - `uh_closure_error = 2.220446049250313e-16` (within tolerance),
  - `hydrograph_volume_closure_relative = 2.0409627099410482e-16` (within tolerance),
  - summary metrics present (`peak_discharge`, `time_to_peak`, `runoff_volume`, `runoff_depth`),
  - provenance present: `uh_unit_system=si_km2_mm_hr_to_cms`, `hf_constant=0.208`, `qp_equation_id=qp_hf_a_re_over_tp`.
- `scs_curvilinear`:
  - `uh_closure_error = 1.1102230246251565e-16` (within tolerance),
  - `hydrograph_volume_closure_relative = 2.0409627099410482e-16` (within tolerance),
  - summary metrics present and populated,
  - provenance fields present and canonical.
- Determinism check:
  - repeated `scs_curvilinear` adapter call with identical payload returned byte-identical JSON (`true`).

## 6. Review Workflow
### 6.1 Code Review (`reviewer` pass, manual)
Checklist outcomes:
- Pass: UH and convolution algorithm bodies are in `geneva_core` (`uh.rs`, `convolution.rs`).
- Pass: run-batch wiring preserves CN behavior and extends outputs with hydrograph/summary/provenance fields.
- Pass: adapter remains glue-only.

### 6.2 QA Review (`qa_reviewer` pass, manual)
Checklist outcomes:
- Pass: both v1 UH methods are implemented and covered.
- Pass: UH and hydrograph closure tolerances are validated in unit tests and manual integration.
- Pass: regression-vector coverage exists for convolution and summary metrics.

### 6.3 Security Review (`security_reviewer` pass, manual)
Checklist outcomes:
- Pass: invalid timing inputs and malformed method IDs fail with typed errors.
- Pass: divide-by-zero/invalid-domain paths are guarded by explicit validation.
- Pass: workload bounds added for UH discretization (`tc_hours` max + max step count) to limit untrusted payload amplification.
- Pass: no panic-based control flow added on user payload paths.

Open findings:
- None.

## 7. QA Review Checklist
- [x] UH algorithm bodies reside in `geneva_core` (`uh.rs`, `convolution.rs`), not adapter glue.
- [x] Both v1 UH methods (`scs_triangular`, `scs_curvilinear`) are implemented and covered.
- [x] UH mass closure and hydrograph volume closure tolerances are validated by tests.
- [x] Provenance metadata fields are emitted and contract-consistent.

## 8. Security Review Checklist
- [x] Timing and timestep inputs are bounded and validated.
- [x] Divide-by-zero and invalid-domain math paths fail explicitly with typed errors.
- [x] Convolution input dimensions are bounded against untrusted payload DoS.
- [x] No panic-based control flow on user payloads.

## 9. Findings and Disposition
- Finding ID: `WP05-SEC-UH-WORKLOAD-BOUND`
  - Severity: medium
  - Disposition: resolved_fix_now
  - Action/Notes: added explicit `tc_hours` upper bound and `MAX_UH_STEPS` guard in `uh.rs` to constrain discretization size.
- Finding ID: `WP05-QA-METHOD-ID-COVERAGE`
  - Severity: low
  - Disposition: resolved_fix_now
  - Action/Notes: added parse and adapter-path invalid UH method tests for typed error behavior.
- Finding ID: `WP05-CODE-CONVOLUTION-REGRESSION-VECTOR`
  - Severity: low
  - Disposition: resolved_fix_now
  - Action/Notes: added fixed-vector convolution regression test with asserted summary metrics and closure.

## 10. Exit-Criteria Check
- [x] `scs_triangular` and `scs_curvilinear` UH kernel implementation complete.
- [x] Excess-to-hydrograph convolution and summary metrics complete.
- [x] UH mass closure and hydrograph volume closure tolerances met and evidenced.
- [x] Required tests added/updated and passing.
- [x] Required gates all passing.
- [x] Manual integration evidence captured.
- [x] Code/QA/security reviews completed and findings dispositioned.
- [x] Board row updated to `done` with evidence link.
