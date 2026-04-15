# WP-03 Evidence: Rust CN Rainfall-Excess Kernel
Status: done  
Last Updated: 2026-04-15  
Work-Package: `WP-03`  
Owner: `codex`

References:
- Plan: `/workdir/wepppy/wepppy/nodb/mods/geneva/implementation-plan.md`
- Spec: `/workdir/wepppy/wepppy/nodb/mods/geneva/specification.md`
- Prior package evidence: `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp-02_rust_hru_hsg_kernel_prepare_hrus.md`

## 1. Scope Implemented
- Implemented CN rainfall-excess kernel in `/workdir/wepppyo3/geneva_core/src/cn.rs` with typed request/response contracts:
  - CN transforms (`S`, `Ia`, `Q`) for `lambda=0.20` and `lambda=0.05`,
  - `CN_0.05` conversion cap behavior (`CN_0.05 = CN_0.20` when `CN_0.20 > 98.5`),
  - per-HRU cumulative excess from cumulative rainfall,
  - cumulative-to-incremental excess conversion with closure validation,
  - area-weighted composite excess hyetograph and closure diagnostics,
  - typed validation for non-physical inputs (negative rainfall, invalid timestep ordering, invalid CN domain).
- Added boundary hardening in CN request validation:
  - strict schema gate (`kernel_schema_version == 1`),
  - non-negative time validation,
  - monotonic tolerance consistency for cumulative rainfall (`FLOAT_TOLERANCE` aware),
  - payload size/work caps (`time_minutes`, `hru_rows`, `hru_rows * time_minutes`),
  - identifier-length caps (`storm_id`, `hru_id`).
- Kept adapter thin:
  - `cli_revision/src/geneva/mod.rs` now parses payload, invokes kernel, serializes response,
  - no algorithm body added to `cli_revision/src/lib.rs`.
- Aligned HRU-side CN conversion cap output in `geneva_core/src/hru.rs` so `cn_lambda_005` preserves `cn_lambda_020` above the `98.5` threshold.
- Added near-100 CN cap parity behavior in `geneva_core/src/cn.rs` (`>= 100 - tol` snaps to `100.0`) to match HRU-side handling.

## 2. Code Changes
### Repo: `/workdir/wepppyo3`
- `geneva_core/src/cn.rs`
- `geneva_core/src/hru.rs`
- `cli_revision/src/geneva/convert.rs`
- `cli_revision/src/geneva/mod.rs`

### Repo: `/workdir/wepppy`
- `wepppy/nodb/mods/geneva/work-packages/wp-03_rust_cn_rainfall_excess_kernel.md`
- `wepppy/nodb/mods/geneva/implementation-plan.md`

## 3. Tests Added/Extended
Added/extended coverage in `geneva_core/src/cn.rs`, `geneva_core/src/hru.rs`, and `cli_revision/src/geneva/*` for:
- scalar CN parity vectors (both lambda modes) with absolute tolerance `<= 1e-6` for `S`, `Ia`, `Q`,
- `CN_0.05` cap behavior for `CN_0.20 > 98.5`,
- cumulative-to-incremental excess non-negativity and closure,
- area-weighted composite excess closure,
- deterministic repeated-run response stability,
- invalid input rejection for:
  - negative rainfall depth,
  - non-increasing timesteps,
  - invalid CN domain values.
- additional hardening regressions:
  - unsupported schema version rejection,
  - negative timestamp rejection,
  - epsilon cumulative dip tolerance and clamp behavior,
  - oversized workload rejection (`hru_rows * time_minutes`),
  - overlong identifier rejection.
- run-batch `lambda_mode=0.05` path (including `CN_0.05` cap) at both kernel and adapter layers.

## 4. Required Gates
### 4.1 Kernel repo gates (`/workdir/wepppyo3`)
1. `cd /workdir/wepppyo3 && cargo fmt --check`
   - Result: **pass**
2. `cd /workdir/wepppyo3 && cargo clippy --all-targets -- -D warnings`
   - Result: **pass**
3. `cd /workdir/wepppyo3 && cargo test -p geneva_core`
   - Result: **pass** (`28 passed; 0 failed`)
4. `cd /workdir/wepppyo3 && cargo test -p cli_revision_rust --lib`
   - Result: **pass** (`14 passed; 0 failed`)

### 4.2 Core repo gates (`/workdir/wepppy`)
5. `cd /workdir/wepppy && wctl doc-lint --path wepppy/nodb/mods/geneva`
   - Result: **pass** (`9 files validated, 0 errors, 0 warnings`)
6. `cd /workdir/wepppy && python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
   - Result: **pass** (`Result: PASS`)

## 5. Manual Integration Check
Commands executed:
- `cd /workdir/wepppyo3 && cargo build -p cli_revision_rust --release --features extension-module`
- Python import via `/workdir/wepppyo3/target/release/libcli_revision_rust.so`
- `geneva_run_batch(...)` called twice with identical payload (single storm, two HRUs, `lambda_mode=0.05`).
- adapter-level golden-series comparison executed against fixed expected vectors.

Observed results:
- deterministic repeated-run output ordering/content: `True`
- golden-series comparison results (`tol=1e-9`):
  - `golden_incremental_match = True`
  - `golden_cumulative_match = True`
- HRU excess arrays present and shape-consistent:
  - `hru_a`: cumulative/incremental lengths `(5, 5)`
  - `hru_b`: cumulative/incremental lengths `(5, 5)`
- composite excess arrays present and shape-consistent: `(5, 5)`
- closure check:
  - `abs(sum(composite_incremental_excess_mm) - final_composite_cumulative_excess_mm) = 0.0`
- golden composite vectors validated:
  - incremental: `[0.0, 0.0, 0.047169887339, 0.690535847893, 2.113062642737]`
  - cumulative: `[0.0, 0.0, 0.047169887339, 0.737705735232, 2.85076837797]`
- invalid-input probe (`cumulative_rainfall_mm` contains negative value) returned typed reason code:
  - `invalid_input: invalid input: cumulative_rainfall_mm must not contain negative depths`

## 6. QA Review
Checklist outcomes:
- Pass: CN algorithm body resides in `geneva_core/src/cn.rs`; adapter remains boundary-only.
- Pass: repeated-run deterministic output validated in manual integration and unit tests.
- Pass: scalar parity vectors and tolerances are tied to specification equations and thresholds.

Open QA findings:
- None.

## 7. Security Review
Checklist outcomes:
- Pass: non-physical values are rejected with typed errors (no silent coercion).
- Pass: closure/consistency checks use explicit contract-violation errors rather than panic-based flow.
- Pass: invalid CN/rainfall/timestep payloads fail fast with actionable diagnostics.

Open security findings:
- None.

## 8. Findings and Disposition
- Finding ID: `WP03-QA-LAMBDA005-BATCH-COVERAGE`
  - Severity: medium
  - Disposition: resolved_fix_now
  - Action: added kernel and adapter tests for `lambda_mode=0.05` batch path and cap behavior.
- Finding ID: `WP03-SEC-INPUT-DIMENSIONS-DOS`
  - Severity: medium
  - Disposition: resolved_fix_now
  - Action: added bounded validation for `time_minutes`, `hru_rows`, `hru_rows * time_minutes`, and ID lengths.
- Finding ID: `WP03-SEC-SCHEMA-GATE`
  - Severity: low
  - Disposition: resolved_fix_now
  - Action: enforced `kernel_schema_version == 1` with typed rejection for unsupported versions.
- Finding ID: `WP03-CODE-MONOTONIC-TOLERANCE-DRIFT`
  - Severity: medium
  - Disposition: resolved_fix_now
  - Action: aligned cumulative-rainfall monotonic validation to the same epsilon tolerance used in execution path and added regression coverage.
- Finding ID: `WP03-CODE-NEGATIVE-TIME-VALIDATION`
  - Severity: low
  - Disposition: resolved_fix_now
  - Action: rejected negative `time_minutes` values with explicit typed input errors.
- Finding ID: `WP03-CODE-CN-CAP-PARITY-DRIFT`
  - Severity: low
  - Disposition: resolved_fix_now
  - Action: aligned near-100 CN cap behavior in `cn.rs` with HRU-side logic and added near-100 parity test.
- Finding ID: `WP03-SEC-ERROR-DETAIL-LEAKAGE`
  - Severity: low
  - Disposition: deferred_followup
  - Note: boundary message sanitization will be addressed with API-layer error-contract hardening in later package(s) where user-facing route contracts are finalized.
- Finding ID: `WP03-QA-ARTIFACT-LEVEL-GATE-LOGGING`
  - Severity: low
  - Disposition: deferred_followup
  - Note: current package stores concrete gate outcomes in evidence; artifact-level log archival/hashing will be handled as a process enhancement.

## 9. Exit-Criteria Check
- [x] CN kernel equations and transforms implemented for `lambda 0.20/0.05`.
- [x] Required tests added/updated and passing with tolerance evidence.
- [x] Required gates all passing.
- [x] Manual integration evidence captured.
- [x] Board row updated with gate statuses and evidence link.
